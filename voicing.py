"""guitar stem에서 코드와 보이싱 특성을 보수적으로 추정한다.

오디오만으로 동일 음높이의 정확한 현·프렛 조합을 유일하게 복원할 수 없으므로,
검출 결과는 구성음·베이스/역위·음역·간격과 별도의 연주 후보 운지로 구분한다.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field, replace
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
    diagnostics: dict = field(default_factory=dict)


def _next_power_of_two(value: int) -> int:
    """FFT 효율을 위해 입력 이상인 가장 작은 2의 거듭제곱을 구한다."""
    return 1 << max(1, int(value - 1).bit_length())


@lru_cache(maxsize=8)
def _guitar_midi_frequencies(tuning_reference_hz: float = 440.0) -> tuple[np.ndarray, np.ndarray]:
    """기타 기본음과 주요 배음을 포괄하는 MIDI 번호와 주파수를 만든다."""
    midi = np.arange(28, 89, dtype=np.int16)
    frequencies = tuning_reference_hz * np.power(2.0, (midi.astype(np.float64) - 69.0) / 12.0)
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


def _independent_pitch_peaks(
    magnitude: np.ndarray, frequencies: np.ndarray, sample_rate: int, fft_size: int
) -> np.ndarray:
    """국소 잡음보다 뚜렷한 기본음만 남기고 낮은 음의 정수배 배음 중복을 억제한다."""
    resolution = sample_rate / fft_size
    amplitudes = np.zeros(len(frequencies), dtype=np.float64)
    measured = np.zeros(len(frequencies), dtype=np.float64)
    for note_index, frequency in enumerate(frequencies):
        center = int(round(frequency / resolution))
        radius = max(1, int(math.ceil(frequency * 0.027 / resolution)))
        low, high = max(1, center - radius), min(len(magnitude) - 1, center + radius + 1)
        if high <= low:
            continue
        peak = low + int(np.argmax(magnitude[low:high]))
        if peak <= 0 or peak >= len(magnitude) - 1:
            continue
        value = float(magnitude[peak])
        if value <= 0 or value < max(float(magnitude[peak - 1]), float(magnitude[peak + 1])):
            continue
        # 로그 포물선 보간으로 인접 MIDI bin이 같은 저음 피크를 중복 채택하지 않는다.
        triple = np.log(np.maximum(magnitude[peak - 1 : peak + 2], np.finfo(float).tiny))
        denominator = float(triple[0] - 2.0 * triple[1] + triple[2])
        offset = float(np.clip(0.5 * (triple[0] - triple[2]) / denominator, -0.5, 0.5)) if denominator < -1e-12 else 0.0
        actual_frequency = (peak + offset) * resolution
        if abs(1200.0 * math.log2(actual_frequency / frequency)) > 42.0:
            continue
        noise_radius = max(12, int(round(frequency * 0.16 / resolution)))
        neighborhood = magnitude[max(1, peak - noise_radius) : min(len(magnitude), peak + noise_radius + 1)]
        noise_floor = float(np.median(neighborhood))
        if value < 4.5 * max(noise_floor, np.finfo(float).tiny):
            continue
        amplitudes[note_index] = max(0.0, value - noise_floor)
        measured[note_index] = actual_frequency
    # 분명한 낮은 기본음과 같은 배음열에 속하는 피크는 독립적인 기타 음의 증거가 아니다.
    # 낮은 음이 없는 높은 음은 그대로 남기며, 누락된 기본음을 가정해 새 음을 만들지 않는다.
    strongest = float(np.max(amplitudes)) if amplitudes.size else 0.0
    if strongest <= 0:
        return amplitudes
    amplitudes[amplitudes < strongest * 0.055] = 0.0
    for lower in range(len(amplitudes)):
        if amplitudes[lower] <= 0:
            continue
        for upper in range(lower + 1, len(amplitudes)):
            if amplitudes[upper] <= 0 or amplitudes[lower] < amplitudes[upper] * 0.18:
                continue
            ratio = measured[upper] / measured[lower]
            harmonic = int(round(ratio))
            if 2 <= harmonic <= 32 and abs(measured[upper] - harmonic * measured[lower]) <= max(resolution * 0.65, measured[upper] * 0.0018):
                amplitudes[upper] = 0.0
    return amplitudes


def _window_pitch_profile(window: np.ndarray, sample_rate: int, tuning_reference_hz: float = 440.0) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    """채널 위상을 섞지 않는 스펙트럼에서 독립 기본음 chroma와 실제 RMS를 계산한다."""
    channel_samples = window[:, None] if window.ndim == 1 else window
    centered = channel_samples.astype(np.float64, copy=False) - np.mean(channel_samples, axis=0, dtype=np.float64)
    rms = math.sqrt(float(np.mean(centered * centered))) if centered.size else 0.0
    fft_size = _next_power_of_two(len(centered))
    tapered = centered * _analysis_window(len(centered))[:, None]
    spectrum = np.fft.rfft(tapered, n=fft_size, axis=0)
    magnitude = np.sqrt(np.mean(np.abs(spectrum) ** 2, axis=1))
    midi, frequencies = _guitar_midi_frequencies(tuning_reference_hz)
    fundamentals = _independent_pitch_peaks(magnitude, frequencies, sample_rate, fft_size)
    salience = fundamentals.copy()
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
    if np.any(chroma[included] < max(float(np.max(chroma)) * 0.12, 1e-12)):
        return -1.0
    weights = np.array([1.0, 0.88, 0.72, 0.62][: len(included)], dtype=np.float64)
    present = float(np.dot(chroma[included], weights) / np.sum(weights))
    outside_mask = np.ones(12, dtype=bool)
    outside_mask[included] = False
    if chord_type == "power5" and float(np.sum(chroma[outside_mask])) > 0.18:
        return -1.0
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
    if rms < 1e-5 or float(np.max(chroma)) < 0.10 or int(np.count_nonzero(chroma >= float(np.max(chroma)) * 0.12)) < 2:
        return {"root_pc": None, "chord_type": "unknown", "symbol": "?", "bass_pc": None, "inversion": "unknown", "pitch_classes": (), "register": "unknown", "spacing": "unknown", "confidence": 0.0}
    candidates = sorted(
        ((_score_chord(chroma, root, chord_type), root, chord_type) for root in range(12) for chord_type in CHORD_INTERVALS),
        reverse=True,
    )
    best_score, root, chord_type = candidates[0]
    if best_score < 0:
        return {"root_pc": None, "chord_type": "unknown", "symbol": "?", "bass_pc": None, "inversion": "unknown", "pitch_classes": (), "register": "unknown", "spacing": "unknown", "confidence": 0.0}
    # 거부한 템플릿의 -1 센티널은 경쟁 점수가 아니다. 이를 차감하면 대안이
    # 없는 두 음만으로도 100%가 되므로 유효 점수의 하한인 0에서 비교한다.
    runner_score = max(0.0, candidates[1][0])
    intervals = CHORD_INTERVALS[chord_type]
    coverage = float(np.sum(chroma[[(root + interval) % 12 for interval in intervals]]))
    # 대안이 적은 템플릿의 큰 수치 차이도 확률적 확신은 아니므로 기여를 제한한다.
    margin = min(0.15, max(0.0, best_score - runner_score))
    confidence = float(np.clip(0.18 + 1.7 * margin + 0.70 * max(0.0, coverage - 0.38), 0.0, 1.0))
    pitch_classes, register, spacing = _voicing_profile(midi, salience)
    bass_pc = _infer_bass_pc(midi, fundamentals)
    if confidence < 0.34 or coverage < 0.60:
        return _unknown_window({})
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
    result = {"root_pc": root_value, "chord_type": chord_type, "symbol": symbol, "bass_pc": bass_pc, "inversion": inversion, "pitch_classes": pitch_classes, "register": register, "spacing": spacing, "confidence": confidence}
    # 이 창 자체에 모든 구성음과 충분한 설명력이 있는 근접 후보만 시간 문맥에
    # 제공한다. 이웃 코드의 음을 빌려 오거나 무음에 새 코드를 채우지 않는다.
    alternatives = []
    if chord_type != "unknown":
        for score, candidate_root, candidate_type in candidates:
            if score < max(0.0, best_score - 0.035):
                break
            candidate_pcs = tuple((candidate_root + interval) % 12 for interval in CHORD_INTERVALS[candidate_type])
            candidate_coverage = float(np.sum(chroma[list(candidate_pcs)]))
            if candidate_coverage < 0.60:
                continue
            candidate = dict(result)
            candidate["root_pc"] = candidate_root
            candidate["chord_type"] = candidate_type
            candidate["pitch_classes"] = candidate_pcs
            candidate["symbol"] = NOTE_NAMES[candidate_root] + CHORD_SUFFIX[candidate_type]
            candidate["inversion"] = "root" if bass_pc == candidate_root else "inversion" if bass_pc in candidate_pcs else "uncertain"
            if candidate["inversion"] == "inversion":
                candidate["symbol"] += f"/{NOTE_NAMES[bass_pc]}"
            candidate["confidence"] = min(confidence, float(np.clip(0.18 + 1.7 * min(0.15, max(0.0, score - runner_score)) + 0.70 * max(0.0, candidate_coverage - 0.38), 0.0, 1.0)))
            if candidate["confidence"] < 0.34:
                continue
            candidate["_score"] = score
            alternatives.append(candidate)
    result["_candidates"] = alternatives
    return result


def _unknown_window(window: dict) -> dict:
    """원래 시간 좌표만 보존하고 근거가 불충분한 창의 모든 코드 주장을 지운다."""
    return {"root_pc": None, "chord_type": "unknown", "symbol": "?", "bass_pc": None,
            "inversion": "unknown", "pitch_classes": (), "register": "unknown",
            "spacing": "unknown", "confidence": 0.0,
            "_start_seconds": window.get("_start_seconds", 0.0)}


def _smooth_labels(windows: list[dict]) -> list[dict]:
    """각 창에서 이미 입증된 근접 후보만 연결하고 반복 증거 없는 단발 라벨은 거부한다."""
    if not windows:
        return []
    candidates = [item.get("_candidates") or [item] for item in windows]
    costs: list[list[float]] = []
    previous_indexes: list[list[int]] = []
    for index, options in enumerate(candidates):
        current_costs, current_previous = [], []
        for option in options:
            emission = float(option.get("_score", 0.0))
            if index == 0:
                current_costs.append(emission)
                current_previous.append(-1)
                continue
            label = (option["root_pc"], option["chord_type"])
            transitions = [value - (0.045 if label != (before["root_pc"], before["chord_type"]) else 0.0)
                           for value, before in zip(costs[-1], candidates[index - 1])]
            best_previous = int(np.argmax(transitions))
            current_costs.append(transitions[best_previous] + emission)
            current_previous.append(best_previous)
        costs.append(current_costs)
        previous_indexes.append(current_previous)
    selected: list[dict] = []
    chosen = int(np.argmax(costs[-1]))
    for index in range(len(windows) - 1, -1, -1):
        result = dict(candidates[index][chosen])
        result["_start_seconds"] = windows[index].get("_start_seconds", 0.0)
        selected.append(result)
        chosen = previous_indexes[index][chosen]
    selected.reverse()
    # 하나의 1.2초 창에서만 나타나는 라벨은 순간적인 멜로디/배음 조합일 수 있다.
    # 인접 창의 같은 코드 증거를 요구하되, 분석창 하나뿐인 짧은 입력은 예외다.
    if len(selected) > 1:
        labels = [(item["root_pc"], item["chord_type"]) for item in selected]
        for index, label in enumerate(labels):
            supported = (index > 0 and labels[index - 1] == label) or (index + 1 < len(labels) and labels[index + 1] == label)
            if label[1] != "unknown" and not supported:
                selected[index] = _unknown_window(selected[index])
    return selected


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


def _limit_timeline_events(events: list[VoicingEvent], max_events: int) -> list[VoicingEvent]:
    """표시 상한을 넘는 약한 후보는 미확정으로 합치되 전체 시간대와 무음 간격을 보존한다."""
    if len(events) <= max_events:
        return events

    def retained_timeline(keep: set[int]) -> list[VoicingEvent]:
        """선택하지 않은 후보와 기존 미확정 구간을 연속 미확정 구간으로 모은다."""
        timeline: list[VoicingEvent] = []
        for index, event in enumerate(events):
            if index in keep:
                timeline.append(event)
                continue
            unknown = replace(event, root_pc=None, chord_type="unknown", symbol="?", bass_pc=None,
                              inversion="unknown", pitch_classes=(), register="unknown", spacing="unknown",
                              confidence=0.0, candidate_shapes=())
            if timeline and timeline[-1].chord_type == "unknown":
                timeline[-1] = replace(timeline[-1], end_seconds=unknown.end_seconds)
            else:
                timeline.append(unknown)
        return timeline

    ranked = sorted((index for index, event in enumerate(events) if event.chord_type != "unknown"),
                    key=lambda index: (events[index].end_seconds - events[index].start_seconds) * events[index].confidence,
                    reverse=True)
    kept: set[int] = set()
    for index in ranked:
        candidate_indexes = sorted(kept | {index})
        # 이벤트 사본을 매번 만들지 않고 선택 구간 사이의 미확정 구간 수만 센다.
        unknown_runs = int(candidate_indexes[0] > 0) + int(candidate_indexes[-1] < len(events) - 1)
        unknown_runs += sum(after > before + 1 for before, after in zip(candidate_indexes, candidate_indexes[1:]))
        if len(candidate_indexes) + unknown_runs <= max_events:
            kept.add(index)
    return retained_timeline(kept)


def analyze_voicings(
    samples: np.ndarray,
    sample_rate: int,
    tuning_reference_hz: float = 440.0,
    max_events: int = 96,
) -> VoicingAnalysis:
    """guitar stem 전체에서 시간대별 코드와 보이싱 프로필을 결정론적으로 추정한다."""
    if samples.ndim != 2 or samples.shape[1] < 1 or sample_rate < 8_000:
        raise ValueError("스테레오 또는 모노 PCM과 8 kHz 이상의 샘플레이트가 필요합니다.")
    if not np.all(np.isfinite(samples)):
        raise ValueError("PCM에는 NaN 또는 무한대가 포함될 수 없습니다.")
    if not 420.0 <= float(tuning_reference_hz) <= 460.0:
        raise ValueError("튜닝 기준은 420~460 Hz 범위여야 합니다.")
    max_events = int(max_events)
    if max_events < 1:
        raise ValueError("최대 이벤트 수는 1 이상이어야 합니다.")
    channels = samples[:, : min(2, samples.shape[1])]
    input_rms = math.sqrt(float(np.einsum("ij,ij->", channels, channels, dtype=np.float64)) / channels.size) if channels.size else 0.0
    input_peak = max(abs(float(np.min(channels))), abs(float(np.max(channels)))) if channels.size else 0.0
    duration = len(channels) / sample_rate
    window_seconds = 1.20
    hop_seconds = 0.60
    window_frames = max(4096, int(round(window_seconds * sample_rate)))
    hop_frames = max(1024, int(round(hop_seconds * sample_rate)))
    if len(channels) < window_frames:
        channels = np.pad(channels, ((0, window_frames - len(channels)), (0, 0)))
    starts = list(range(0, max(1, len(channels) - window_frames + 1), hop_frames))
    final_start = max(0, len(channels) - window_frames)
    if not starts or starts[-1] != final_start:
        starts.append(final_start)
    windows: list[dict] = []
    active_frame_count = 0
    polyphonic_frame_count = 0
    for start in starts:
        chroma, salience, fundamentals, rms = _window_pitch_profile(channels[start : start + window_frames], sample_rate, float(tuning_reference_hz))
        active_frame_count += int(rms >= 1e-5)
        polyphonic_frame_count += int(rms >= 1e-5 and np.count_nonzero(chroma >= max(float(np.max(chroma)) * 0.12, 1e-12)) >= 2)
        classified = _classify_window(chroma, salience, fundamentals, rms)
        classified["_start_seconds"] = start / sample_rate
        windows.append(classified)
    raw_candidate_frame_count = sum(item["chord_type"] != "unknown" for item in windows)
    windows = _smooth_labels(windows)
    events = _merge_events(windows, hop_seconds, window_seconds, duration)
    event_count_before_limit = len(events)
    events = _limit_timeline_events(events, max_events)
    tonal_coverage = float(np.mean([item["chord_type"] != "unknown" for item in windows])) if windows else 0.0
    reliable_frame_count = sum(item["chord_type"] != "unknown" for item in windows)
    reason = "detected" if reliable_frame_count else "silent_or_very_quiet" if not active_frame_count else "insufficient_polyphonic_evidence" if not polyphonic_frame_count else "ambiguous_harmony"
    diagnostics = {
        "status": "detected" if reliable_frame_count else "no_reliable_chords",
        "reason": reason,
        "input_rms_dbfs": round(20.0 * math.log10(max(input_rms, 1e-12)), 3),
        "input_peak_dbfs": round(20.0 * math.log10(max(input_peak, 1e-12)), 3),
        "input_level": "silent" if input_rms < 1e-5 else "very_quiet" if input_rms < 10.0 ** (-55.0 / 20.0) else "normal",
        "analyzed_frame_count": len(windows),
        "active_frame_count": active_frame_count,
        "polyphonic_frame_count": polyphonic_frame_count,
        "raw_candidate_frame_count": raw_candidate_frame_count,
        "reliable_frame_count": reliable_frame_count,
        "unknown_frame_count": len(windows) - reliable_frame_count,
        "channel_policy": "first_two_channels_rms_spectrum_no_phase_cancellation",
        "tuning_reference_hz": float(tuning_reference_hz),
        "event_count_before_limit": event_count_before_limit,
        "events_truncated": event_count_before_limit > max_events,
        "temporal_policy": "local_evidence_candidates_with_adjacent_window_support",
        "timeline_limit_policy": "omitted_candidates_become_unknown_without_time_gaps",
    }
    limitations = (
        "exact_string_fret_not_identifiable_from_audio",
        "candidate_shapes_are_playable_suggestions_not_detections",
        "source_separation_bleed_and_distortion_can_change_results",
        "capo_drop_tuning_pitch_effects_and_fast_riffs_need_manual_review",
        "confidence_is_template_margin_not_statistical_accuracy",
        "harmonically_overlapping_notes_and_missing_fundamentals_can_remain_unknown",
        "isolated_short_chords_without_repeated_evidence_remain_unknown",
    )
    return VoicingAnalysis(
        schema="tonematch-voicing/v1",
        method="NumPy phase-safe independent-pitch chroma + locally evidenced temporal chord templates",
        window_seconds=window_seconds,
        hop_seconds=hop_seconds,
        event_count=len(events),
        tonal_coverage=round(tonal_coverage, 4),
        events=tuple(events),
        limitations=limitations,
        diagnostics=diagnostics,
    )


def voicing_analysis_dict(analysis: VoicingAnalysis) -> dict:
    """불변 보이싱 분석 객체와 이벤트를 JSON 직렬화 가능한 사전으로 바꾼다."""
    return asdict(analysis)


def pitch_class_names(values: Iterable[int]) -> str:
    """pitch class 정수 모음을 사람이 읽는 음이름 문자열로 바꾼다."""
    return " · ".join(NOTE_NAMES[int(value) % 12] for value in values)
