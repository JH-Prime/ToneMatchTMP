"""guitar stem에서 코드와 보이싱 특성을 보수적으로 추정한다.

오디오만으로 동일 음높이의 정확한 현·프렛 조합을 유일하게 복원할 수 없으므로,
검출 결과는 구성음·베이스/역위·음역·간격과 별도의 연주 후보 운지로 구분한다.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from functools import lru_cache
from typing import Iterable

import numpy as np


NOTE_NAMES = ("C", "C♯", "D", "E♭", "E", "F", "F♯", "G", "A♭", "A", "B♭", "B")
CHORD_INTERVALS: dict[str, tuple[int, ...]] = {
    "power5": (0, 7),
    "major": (0, 4, 7),
    "minor": (0, 3, 7),
    "sus2": (0, 2, 7),
    "sus4": (0, 5, 7),
    "dim": (0, 3, 6),
    "7": (0, 4, 7, 10),
    "maj7": (0, 4, 7, 11),
    "min7": (0, 3, 7, 10),
}
CHORD_SUFFIX = {
    "power5": "5",
    "major": "",
    "minor": "m",
    "sus2": "sus2",
    "sus4": "sus4",
    "dim": "dim",
    "7": "7",
    "maj7": "maj7",
    "min7": "m7",
    "unknown": "?",
}


@dataclass(frozen=True)
class VoicingEvent:
    """하나로 합쳐진 시간 구간의 코드·보이싱 추정값을 정의한다."""

    start_seconds: float
    end_seconds: float
    root_pc: int | None
    chord_type: str
    symbol: str
    bass_pc: int | None
    inversion: str
    pitch_classes: tuple[int, ...]
    register: str
    spacing: str
    confidence: float
    candidate_shapes: tuple[dict, ...]


@dataclass(frozen=True)
class VoicingAnalysis:
    """전체 코드 보이싱 분석의 설정·통계·시간 이벤트를 정의한다."""

    schema: str
    method: str
    window_seconds: float
    hop_seconds: float
    event_count: int
    tonal_coverage: float
    events: tuple[VoicingEvent, ...]
    limitations: tuple[str, ...]


def _next_power_of_two(value: int) -> int:
    """FFT 효율을 위해 입력 이상인 가장 작은 2의 거듭제곱을 구한다."""
    return 1 << max(1, int(value - 1).bit_length())


@lru_cache(maxsize=1)
def _guitar_midi_frequencies() -> tuple[np.ndarray, np.ndarray]:
    """기타 기본음과 주요 배음을 포괄하는 MIDI 번호와 주파수를 만든다."""
    midi = np.arange(28, 89, dtype=np.int16)
    frequencies = 440.0 * np.power(2.0, (midi.astype(np.float64) - 69.0) / 12.0)
    return midi, frequencies


@lru_cache(maxsize=8)
def _analysis_window(length: int) -> np.ndarray:
    """같은 길이의 보이싱 창이 반복될 때 재사용할 Hann 창을 만든다."""
    return np.hanning(int(length))


def _local_spectral_peak(magnitude: np.ndarray, frequency: float, sample_rate: int, fft_size: int) -> float:
    """목표 주파수 부근 세 FFT bin 중 가장 큰 크기를 반환한다."""
    index = int(round(frequency * fft_size / sample_rate))
    if index < 1 or index >= len(magnitude) - 1:
        return 0.0
    return float(np.max(magnitude[index - 1 : index + 2]))


def _spectral_peaks(
    magnitude: np.ndarray,
    frequencies: np.ndarray,
    sample_rate: int,
    fft_size: int,
) -> np.ndarray:
    """여러 목표 주파수 주변의 세 FFT bin 최댓값을 네이티브 NumPy 연산으로 함께 구한다."""
    indexes = np.rint(frequencies * fft_size / sample_rate).astype(np.int64)
    valid = (indexes >= 1) & (indexes < len(magnitude) - 1)
    safe = np.clip(indexes, 1, max(1, len(magnitude) - 2))
    peaks = np.maximum.reduce((magnitude[safe - 1], magnitude[safe], magnitude[safe + 1]))
    return np.where(valid, peaks, 0.0).astype(np.float64, copy=False)


def _window_pitch_profile(window: np.ndarray, sample_rate: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    """한 시간창에서 HPCP형 chroma, 음별 salience, 기본음 크기와 RMS를 계산한다."""
    centered = window.astype(np.float64, copy=False) - float(np.mean(window))
    rms = math.sqrt(float(np.dot(centered, centered)) / max(len(centered), 1) + 1e-12)
    fft_size = _next_power_of_two(len(centered))
    tapered = centered * _analysis_window(len(centered))
    magnitude = np.abs(np.fft.rfft(tapered, n=fft_size))
    midi, frequencies = _guitar_midi_frequencies()
    fundamentals = _spectral_peaks(magnitude, frequencies, sample_rate, fft_size)
    salience = fundamentals.copy()
    for harmonic, weight in ((2, 0.42), (3, 0.24), (4, 0.12)):
        harmonic_frequencies = frequencies * harmonic
        harmonic_values = _spectral_peaks(magnitude, harmonic_frequencies, sample_rate, fft_size)
        harmonic_values = np.where(harmonic_frequencies < sample_rate / 2, harmonic_values, 0.0)
        salience += weight * harmonic_values
    salience = np.sqrt(np.maximum(salience, 0.0))
    chroma = np.zeros(12, dtype=np.float64)
    octave_weights = np.where((midi >= 40) & (midi <= 76), 1.0, 0.72)
    np.add.at(chroma, midi.astype(np.int64) % 12, salience * octave_weights)
    if float(np.sum(chroma)) > 0:
        chroma /= float(np.sum(chroma))
    return chroma, salience, fundamentals, rms


def _score_chord(chroma: np.ndarray, root: int, chord_type: str) -> float:
    """구성음 보상과 비구성음 벌점을 조합해 한 코드 템플릿 점수를 만든다."""
    intervals = CHORD_INTERVALS[chord_type]
    included = np.array([(root + interval) % 12 for interval in intervals], dtype=int)
    weights = np.array([1.0, 0.88, 0.72, 0.62][: len(included)], dtype=np.float64)
    present = float(np.dot(chroma[included], weights) / np.sum(weights))
    outside_mask = np.ones(12, dtype=bool)
    outside_mask[included] = False
    outside = float(np.sum(np.sort(chroma[outside_mask])[-3:]))
    score = present - 0.16 * outside
    # 7th는 실제 7음이 충분히 들릴 때만 3화음보다 높은 점수를 받는다.
    if len(intervals) == 4:
        seventh = float(chroma[(root + intervals[-1]) % 12])
        score += 0.25 * seventh - 0.018
    if chord_type == "power5":
        third_energy = max(float(chroma[(root + 3) % 12]), float(chroma[(root + 4) % 12]))
        score += 0.025 if third_energy < 0.55 * max(float(chroma[root]), 1e-9) else -0.045
    return score


def _infer_bass_pc(midi: np.ndarray, fundamentals: np.ndarray) -> int | None:
    """충분히 강한 가장 낮은 기타 음을 찾아 베이스 pitch class로 사용한다."""
    if not fundamentals.size or float(np.max(fundamentals)) <= 0:
        return None
    threshold = float(np.max(fundamentals)) * 0.16
    candidates = np.flatnonzero((fundamentals >= threshold) & (midi <= 67))
    return int(midi[int(candidates[0])] % 12) if len(candidates) else None


def _voicing_profile(midi: np.ndarray, salience: np.ndarray) -> tuple[tuple[int, ...], str, str]:
    """활성 음들의 pitch class, 평균 음역과 음 간격 폭을 보수적으로 분류한다."""
    if not salience.size or float(np.max(salience)) <= 0:
        return (), "unknown", "unknown"
    active = salience >= float(np.max(salience)) * 0.28
    active_midi = midi[active]
    active_salience = salience[active]
    if not len(active_midi):
        return (), "unknown", "unknown"
    pitch_strength: dict[int, float] = {}
    for note, strength in zip(active_midi, active_salience):
        pitch_class = int(note) % 12
        pitch_strength[pitch_class] = pitch_strength.get(pitch_class, 0.0) + float(strength)
    ordered = tuple(key for key, _value in sorted(pitch_strength.items(), key=lambda item: item[1], reverse=True)[:6])
    center = float(np.average(active_midi, weights=active_salience))
    register = "low" if center < 50 else "mid" if center < 65 else "high"
    span = int(np.max(active_midi) - np.min(active_midi))
    spacing = "close" if span <= 12 else "medium" if span <= 24 else "wide"
    return ordered, register, spacing


def _barre_shape(root_pc: int, chord_type: str, sixth_string: bool) -> dict | None:
    """검출값과 별개로 연주해 볼 수 있는 E형 또는 A형 바레 후보를 만든다."""
    if sixth_string:
        fret = (root_pc - 4) % 12
        relative = {
            "major": (0, 2, 2, 1, 0, 0),
            "minor": (0, 2, 2, 0, 0, 0),
            "7": (0, 2, 0, 1, 0, 0),
            "maj7": (0, 2, 1, 1, 0, 0),
            "min7": (0, 2, 0, 0, 0, 0),
            "power5": (0, 2, 2, -1, -1, -1),
        }.get(chord_type)
        label = "E-shape barre"
    else:
        fret = (root_pc - 9) % 12
        relative = {
            "major": (-1, 0, 2, 2, 2, 0),
            "minor": (-1, 0, 2, 2, 1, 0),
            "7": (-1, 0, 2, 0, 2, 0),
            "maj7": (-1, 0, 2, 1, 2, 0),
            "min7": (-1, 0, 2, 0, 1, 0),
            "power5": (-1, 0, 2, 2, -1, -1),
        }.get(chord_type)
        label = "A-shape barre"
    if relative is None:
        return None
    frets: list[int | str] = ["x" if value < 0 else int(fret + value) for value in relative]
    return {"label": label, "frets_low_e_to_high_e": frets, "detected": False}


def candidate_guitar_shapes(root_pc: int | None, chord_type: str) -> tuple[dict, ...]:
    """코드 이름을 실제로 시험할 수 있는 최대 두 개의 일반 운지 후보로 바꾼다."""
    if root_pc is None or chord_type == "unknown":
        return ()
    shapes = [
        shape
        for shape in (
            _barre_shape(root_pc, chord_type, True),
            _barre_shape(root_pc, chord_type, False),
        )
        if shape is not None
    ]
    return tuple(shapes[:2])


def _classify_window(chroma: np.ndarray, salience: np.ndarray, fundamentals: np.ndarray, rms: float) -> dict:
    """한 분석창을 코드, 베이스/역위, 음역, 간격과 신뢰도로 분류한다."""
    midi, _frequencies = _guitar_midi_frequencies()
    if rms < 1e-5 or float(np.max(chroma)) < 0.10:
        return {"root_pc": None, "chord_type": "unknown", "symbol": "?", "bass_pc": None, "inversion": "unknown", "pitch_classes": (), "register": "unknown", "spacing": "unknown", "confidence": 0.0}
    candidates = sorted(
        ((_score_chord(chroma, root, chord_type), root, chord_type) for root in range(12) for chord_type in CHORD_INTERVALS),
        reverse=True,
    )
    best_score, root, chord_type = candidates[0]
    runner_score = next(score for score, candidate_root, _kind in candidates[1:] if candidate_root != root)
    intervals = CHORD_INTERVALS[chord_type]
    coverage = float(np.sum(chroma[[(root + interval) % 12 for interval in intervals]]))
    margin = max(0.0, best_score - runner_score)
    confidence = float(np.clip(0.18 + 1.7 * margin + 0.70 * max(0.0, coverage - 0.38), 0.0, 1.0))
    pitch_classes, register, spacing = _voicing_profile(midi, salience)
    bass_pc = _infer_bass_pc(midi, fundamentals)
    if confidence < 0.34 or coverage < 0.43:
        root_value: int | None = None
        chord_type = "unknown"
        symbol = "?"
        inversion = "unknown"
    else:
        root_value = int(root)
        symbol = NOTE_NAMES[root] + CHORD_SUFFIX[chord_type]
        chord_pcs = {(root + interval) % 12 for interval in intervals}
        if bass_pc == root:
            inversion = "root"
        elif bass_pc in chord_pcs:
            inversion = "inversion"
            symbol += f"/{NOTE_NAMES[bass_pc]}"
        else:
            inversion = "uncertain"
        # 표시 구성음은 고조파로 생긴 여분 pitch class가 아니라 채택한 코드 템플릿을 따른다.
        pitch_classes = tuple((root + interval) % 12 for interval in intervals)
    return {"root_pc": root_value, "chord_type": chord_type, "symbol": symbol, "bass_pc": bass_pc, "inversion": inversion, "pitch_classes": pitch_classes, "register": register, "spacing": spacing, "confidence": confidence}


def _smooth_labels(windows: list[dict]) -> list[dict]:
    """앞뒤 두 창이 같은 코드일 때 가운데의 짧은 오검출을 그 코드로 평활화한다."""
    if len(windows) < 3:
        return windows
    smoothed = [dict(item) for item in windows]
    for index in range(1, len(windows) - 1):
        before, current, after = windows[index - 1], windows[index], windows[index + 1]
        before_label = (before["root_pc"], before["chord_type"])
        after_label = (after["root_pc"], after["chord_type"])
        current_label = (current["root_pc"], current["chord_type"])
        if before_label == after_label and current_label != before_label:
            replacement = dict(before if before["confidence"] >= after["confidence"] else after)
            replacement["confidence"] = min(before["confidence"], after["confidence"]) * 0.92
            # 라벨만 바꾸고 가운데 창의 실제 시간 위치는 그대로 유지한다.
            if "_start_seconds" in current:
                replacement["_start_seconds"] = current["_start_seconds"]
            smoothed[index] = replacement
    return smoothed


def _merge_events(windows: list[dict], hop_seconds: float, window_seconds: float, duration: float) -> list[VoicingEvent]:
    """연속해서 같은 코드로 분류된 시간창을 하나의 타임라인 이벤트로 합친다."""
    if not windows:
        return []
    groups: list[list[dict]] = []
    start_index = 0
    for index in range(1, len(windows) + 1):
        previous = windows[index - 1]
        boundary = index == len(windows) or (windows[index]["root_pc"], windows[index]["chord_type"]) != (previous["root_pc"], previous["chord_type"])
        if not boundary:
            continue
        groups.append(windows[start_index:index])
        start_index = index

    events: list[VoicingEvent] = []
    for group_index, group in enumerate(groups):
        representative = max(group, key=lambda item: item["confidence"])
        confidence = float(np.mean([item["confidence"] for item in group]))
        # 인접한 겹침 창 중심의 중간점을 코드 전환점으로 삼아 이벤트가 겹치거나
        # 마지막 비정규 창 때문에 뒤로 밀리지 않게 한다.
        if group_index == 0:
            start_time = 0.0
        else:
            previous_group = groups[group_index - 1]
            previous_start = float(previous_group[-1].get("_start_seconds", 0.0))
            current_start = float(group[0].get("_start_seconds", previous_start + hop_seconds))
            start_time = (previous_start + current_start + window_seconds) * 0.5
        if group_index == len(groups) - 1:
            end_time = duration
        else:
            next_group = groups[group_index + 1]
            current_start = float(group[-1].get("_start_seconds", 0.0))
            next_start = float(next_group[0].get("_start_seconds", current_start + hop_seconds))
            end_time = (current_start + next_start + window_seconds) * 0.5
        start_time = min(max(0.0, start_time), duration)
        end_time = min(max(start_time, end_time), duration)
        events.append(
            VoicingEvent(
                start_seconds=round(start_time, 3),
                end_seconds=round(end_time, 3),
                root_pc=representative["root_pc"],
                chord_type=representative["chord_type"],
                symbol=representative["symbol"],
                bass_pc=representative["bass_pc"],
                inversion=representative["inversion"],
                pitch_classes=tuple(representative["pitch_classes"]),
                register=representative["register"],
                spacing=representative["spacing"],
                confidence=round(confidence, 4),
                candidate_shapes=candidate_guitar_shapes(representative["root_pc"], representative["chord_type"]),
            )
        )
    return events


def analyze_voicings(
    samples: np.ndarray,
    sample_rate: int,
    tuning_reference_hz: float = 440.0,
    max_events: int = 96,
) -> VoicingAnalysis:
    """guitar stem 전체에서 시간대별 코드와 보이싱 프로필을 결정론적으로 추정한다."""
    if samples.ndim != 2 or samples.shape[1] < 1 or sample_rate < 8_000:
        raise ValueError("스테레오 또는 모노 PCM과 8 kHz 이상의 샘플레이트가 필요합니다.")
    if not 420.0 <= float(tuning_reference_hz) <= 460.0:
        raise ValueError("튜닝 기준은 420~460 Hz 범위여야 합니다.")
    max_events = int(max_events)
    if max_events < 1:
        raise ValueError("최대 이벤트 수는 1 이상이어야 합니다.")
    # 현재 프리뷰는 A=440 Hz 기준이며 인자는 향후 자동 튜닝 추정을 위한 스키마를 유지한다.
    _ = tuning_reference_hz
    mono = np.mean(samples[:, : min(2, samples.shape[1])], axis=1, dtype=np.float32)
    duration = len(mono) / sample_rate
    window_seconds = 1.20
    hop_seconds = 0.60
    window_frames = max(4096, int(round(window_seconds * sample_rate)))
    hop_frames = max(1024, int(round(hop_seconds * sample_rate)))
    if len(mono) < window_frames:
        mono = np.pad(mono, (0, window_frames - len(mono)))
    starts = list(range(0, max(1, len(mono) - window_frames + 1), hop_frames))
    final_start = max(0, len(mono) - window_frames)
    if not starts or starts[-1] != final_start:
        starts.append(final_start)
    windows: list[dict] = []
    for start in starts:
        chroma, salience, fundamentals, rms = _window_pitch_profile(mono[start : start + window_frames], sample_rate)
        classified = _classify_window(chroma, salience, fundamentals, rms)
        classified["_start_seconds"] = start / sample_rate
        windows.append(classified)
    windows = _smooth_labels(windows)
    events = _merge_events(windows, hop_seconds, window_seconds, duration)
    if len(events) > max_events:
        # 전체 시간 순서를 유지하면서 매우 짧은 이벤트보다 대표 구간을 우선한다.
        ranked_indices = sorted(range(len(events)), key=lambda index: ((events[index].end_seconds - events[index].start_seconds) * events[index].confidence), reverse=True)[:max_events]
        events = [events[index] for index in sorted(ranked_indices)]
    tonal_coverage = float(np.mean([item["chord_type"] != "unknown" for item in windows])) if windows else 0.0
    limitations = (
        "exact_string_fret_not_identifiable_from_audio",
        "candidate_shapes_are_playable_suggestions_not_detections",
        "source_separation_bleed_and_distortion_can_change_results",
        "capo_drop_tuning_pitch_effects_and_fast_riffs_need_manual_review",
        "confidence_is_template_margin_not_statistical_accuracy",
    )
    return VoicingAnalysis(
        schema="tonematch-voicing/v1",
        method="NumPy HPCP-like chroma + conservative chord templates",
        window_seconds=window_seconds,
        hop_seconds=hop_seconds,
        event_count=len(events),
        tonal_coverage=round(tonal_coverage, 4),
        events=tuple(events),
        limitations=limitations,
    )


def voicing_analysis_dict(analysis: VoicingAnalysis) -> dict:
    """불변 보이싱 분석 객체와 이벤트를 JSON 직렬화 가능한 사전으로 바꾼다."""
    return asdict(analysis)


def pitch_class_names(values: Iterable[int]) -> str:
    """pitch class 정수 모음을 사람이 읽는 음이름 문자열로 바꾼다."""
    return " · ".join(NOTE_NAMES[int(value) % 12] for value in values)
