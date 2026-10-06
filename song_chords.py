"""원본 믹스에서 CQT·크로마와 시간 문맥으로 악기 독립적인 코드를 추정한다."""

from dataclasses import asdict
import math
from typing import Callable

import numpy as np

from voicing import CHORD_INTERVALS, _classify_window, _merge_events, _smooth_labels


class ChordAnalysisCancelled(Exception):
    """코드 분석의 사용자 취소를 일반 신호 오류와 구분한다."""


def _check_cancelled(cancel_requested):
    """작은 분석 작업 사이에서 취소를 전달한다."""
    if cancel_requested and cancel_requested():
        raise ChordAnalysisCancelled()


def _cqt_magnitudes(audio, sample_rate, midi):
    """위상이 반대인 채널도 소실시키지 않는 실제 상수 Q 스펙트럼을 만든다."""
    import librosa
    # 최저음의 긴 필터와 재귀 다운샘플링에 필요한 길이를 보장한다.
    padded = np.pad(audio, ((0, max(0, sample_rate * 4 - len(audio))), (0, 0)))
    frequency = 440 * 2 ** ((int(midi[0]) - 69) / 12)
    spectrum = librosa.cqt(
        np.ascontiguousarray(padded.T, dtype=np.float32), sr=sample_rate,
        hop_length=512, fmin=frequency, n_bins=len(midi) * 3,
        bins_per_octave=36, tuning=0, scale=False, sparsity=0.01,
    )
    return np.sqrt(np.mean(np.abs(spectrum) ** 2, axis=0))


def _pitch_profile(magnitude):
    """국소 잡음 바닥을 낮추되 작은 구성음을 평균 문턱으로 삭제하지 않는다."""
    from scipy.ndimage import median_filter
    # 시간 방향의 지속 성분을 우선하고 수직으로 넓은 타격 성분을 감쇠한다.
    harmonic = median_filter(magnitude, size=(1, 9), mode="nearest")
    percussive = median_filter(magnitude, size=(15, 1), mode="nearest")
    weight = harmonic ** 2 / (harmonic ** 2 + percussive ** 2 + 1e-20)
    return magnitude * weight


def analyze_song_chords(
    samples: np.ndarray, sample_rate: int, *,
    progress: Callable[[float], None] | None = None,
    cancel_requested: Callable[[], bool] | None = None,
) -> dict:
    """최대 20분 원본 PCM을 겹치는 구간으로 처리하고 근거·대안을 남긴다."""
    _check_cancelled(cancel_requested)
    if (not isinstance(samples, np.ndarray) or samples.ndim != 2
            or samples.shape[1] not in (1, 2) or not isinstance(sample_rate, int)
            or isinstance(sample_rate, bool) or not 8000 <= sample_rate <= 192000):
        raise ValueError("Expected mono/stereo PCM and an 8–192 kHz sample rate")
    if len(samples) > sample_rate * 1200 or not len(samples) or not np.all(np.isfinite(samples)):
        raise ValueError("Expected nonempty finite PCM, at most 20 minutes")
    duration = len(samples) / sample_rate
    window_seconds, hop_seconds = 1.2, 0.6
    window_frames, hop_frames = round(window_seconds * sample_rate), round(hop_seconds * sample_rate)
    starts = list(range(0, max(1, len(samples) - window_frames + 1), hop_frames))
    final_start = max(0, len(samples) - window_frames)
    if starts[-1] != final_start:
        starts.append(final_start)
    midi = np.arange(24, 108 if sample_rate >= 11025 else 96)
    windows = []
    active = 0
    input_rms = math.sqrt(float(np.einsum("ij,ij->", samples, samples, dtype=np.float64)) / samples.size)
    for offset in range(0, len(starts), 10):
        _check_cancelled(cancel_requested)
        batch = starts[offset:offset + 10]
        # 곡 전체 CQT를 보관하지 않고 저음 필터용 앞뒤 여백만 공유한다.
        left = max(0, batch[0] - sample_rate) // 512 * 512
        right = min(len(samples), batch[-1] + window_frames + sample_rate)
        audio = samples[left:right]
        magnitude = None
        if np.max(np.abs(audio)) >= 1e-5:
            magnitude = _pitch_profile(_cqt_magnitudes(audio, sample_rate, midi))
        for start in batch:
            _check_cancelled(cancel_requested)
            clip = samples[start:min(len(samples), start + window_frames)]
            rms = math.sqrt(float(np.einsum("ij,ij->", clip, clip, dtype=np.float64)) / clip.size)
            active += int(rms >= 1e-5)
            salience = np.zeros(len(midi))
            if magnitude is not None:
                first = max(0, int((start - left) / 512))
                last = min(magnitude.shape[1], int((start - left + len(clip)) / 512) + 1)
                profile = np.median(magnitude[:, first:last], axis=1)
                # 각 반음의 중심과 ±1/3반음만 결합하며 옥타브 가중치를 두지 않는다.
                padded = np.pad(profile, (1, 1))
                salience = np.maximum.reduce([padded[0:-2:3], padded[1:-1:3], padded[2::3]])
                floor = float(np.median(salience))
                salience = np.maximum(0, salience - floor)
            chroma = np.bincount(midi % 12, weights=salience, minlength=12)
            total = float(np.sum(chroma))
            if total:
                chroma /= total
            # 넓게 분포하는 비주기 잡음을 7음 확장화음으로 억지 분류하지 않는다.
            flatness = float(np.exp(np.mean(np.log(np.maximum(chroma, 1e-12))))) / max(float(np.mean(chroma)), 1e-12)
            if flatness > 0.85:
                chroma[:] = 0
            item = _classify_window(chroma, salience, salience, rms, midi=midi)
            item["_start_seconds"] = start / sample_rate
            windows.append(item)
        if progress:
            progress(min(1.0, (offset + len(batch)) / len(starts)))
    _check_cancelled(cancel_requested)
    windows = _smooth_labels(windows)
    events = _merge_events(windows, hop_seconds, window_seconds, duration, include_shapes=False)
    reliable = sum(item["chord_type"] != "unknown" for item in windows)
    rows = []
    for event in events:
        row = asdict(event)
        row["register"] = row["spacing"] = "unknown"
        if row["chord_type"] != "unknown":
            row["evidence"]["pitch_method"] = "CQT"
            row["evidence"]["bass_pitch_class"] = row["bass_pc"]
        rows.append(row)
    return {
        "schema": "tonematch-voicing/v1", "method": "CQT (36 bins/octave) + harmonic weighting + chroma + temporal templates",
        "analysis_source": "original_mix", "window_seconds": window_seconds,
        "hop_seconds": hop_seconds, "event_count": len(rows), "events": rows,
        "tonal_coverage": round(reliable / len(windows), 4),
        "diagnostics": {
            "status": "detected" if reliable else "no_reliable_chords",
            "reason": "detected" if reliable else "silent_or_very_quiet" if not active else "ambiguous_harmony",
            "input_rms_dbfs": round(20 * math.log10(max(input_rms, 1e-12)), 3),
            "analyzed_frame_count": len(windows), "active_frame_count": active,
            "reliable_frame_count": reliable, "unknown_frame_count": len(windows) - reliable,
            "score_semantics": "heuristic_evidence_not_accuracy_probability",
            "chord_template_count": len(CHORD_INTERVALS), "cqt_bins_per_octave": 36,
            "pitch_range_midi": [int(midi[0]), int(midi[-1])],
            "channel_policy": "channel_magnitude_rms_no_phase_cancellation",
            "temporal_policy": "locally_supported_candidates_with_transition_cost",
        },
        "limitations": ["identical_pitch_sets_can_have_multiple_names",
                        "missing_notes_melody_percussion_and_overtones_can_confuse_templates",
                        "evidence_score_is_not_calibrated_accuracy"],
    }
