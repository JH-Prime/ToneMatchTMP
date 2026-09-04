"""결정론적 DSP 분석과 Tone Master Pro 레시피 생성 엔진.

오디오는 로컬 FFmpeg로 표준 PCM으로 바꾼 뒤 NumPy만으로 분석한다. 각 추천값은
공식 장비 측정값이 아니라, 설명 가능한 특징량에서 계산한 안전한 시작점이다.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import tempfile
import wave
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Iterable

import numpy as np

from catalog import APP_VERSION, MODEL_GUIDE_REVISION, TARGET_FIRMWARE, TEMPLATES
from devices import device_by_id, device_label, is_supported_device
from i18n import choice_code, choice_label, tr
from separator import (
    SEPARATOR_SAMPLE_RATE,
    SeparationError,
    separate_guitar_wav,
    separation_info_dict,
)
from voicing import analyze_voicings, voicing_analysis_dict


SAMPLE_RATE = 22_050
MAX_ANALYSIS_SECONDS = 20 * 60.0
MIN_ANALYSIS_SECONDS = 3.0
MAX_ENVELOPE_FRAMES = 6_000


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """실수 값을 지정 범위(기본 0~1) 안으로 제한한다."""
    return max(low, min(high, float(value)))


def pct(value: float) -> int:
    """0~1 값을 반올림한 0~100 정수 백분율로 바꾼다."""
    return int(round(clamp(value) * 100))


def db(value: float) -> float:
    """양의 선형 진폭 비율을 로그 dB 값으로 변환한다."""
    return 20.0 * math.log10(max(float(value), 1e-12))


@dataclass
class ToneFeatures:
    saturation: float
    brightness: float
    body: float
    compression: float
    ambience: float
    modulation: float
    delay_strength: float
    delay_ms: int
    bpm: int
    stereo_width: float
    mix_contamination: float
    analysis_confidence: float
    spectral_centroid_hz: float
    spectral_rolloff_hz: float
    spectral_flatness: float
    dynamic_range_db: float
    crest_factor_db: float
    rms_dbfs: float
    peak_dbfs: float
    clipping_percent: float
    active_audio_percent: float


class AnalysisError(RuntimeError):
    """입력·디코딩·분석 단계의 사용자용 오류를 나타낸다."""


def bundled_path(name: str) -> Path:
    """소스 실행과 PyInstaller 실행 모두에서 번들 리소스 경로를 찾는다."""
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    candidates = [
        root / "resources" / name,
        root / name,
        Path(__file__).resolve().parent / "resources" / name,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def ffmpeg_path() -> Path:
    """앱과 함께 배포된 FFmpeg 실행 파일 경로를 반환한다."""
    return bundled_path("ffmpeg.exe")


def _hidden_process_flags() -> int:
    """Windows에서 FFmpeg 콘솔 창이 잠깐 나타나지 않도록 실행 플래그를 만든다."""
    return subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def decode_to_pcm_wav(
    source: str | Path,
    start_seconds: float,
    end_seconds: float,
    destination: str | Path,
    sample_rate: int,
    progress: Callable[[int, str], None] | None = None,
    language: str = "ko",
) -> float:
    """선택 구간 또는 최대 20분 전체를 표준 PCM WAV로 디코딩한다."""
    source_path = Path(source)
    if not source_path.is_file():
        raise AnalysisError(tr("error.file_missing", language))
    start = max(0.0, float(start_seconds))
    requested = float(end_seconds) - start if float(end_seconds) > start else MAX_ANALYSIS_SECONDS
    duration = min(MAX_ANALYSIS_SECONDS, requested)
    if duration < MIN_ANALYSIS_SECONDS:
        raise AnalysisError(tr("error.minimum_segment", language))
    converter = ffmpeg_path()
    if not converter.exists():
        raise AnalysisError(tr("error.decoder_missing", language))
    if progress:
        progress(10, tr("progress.decode", language))
    wav_path = Path(destination)
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(converter),
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-ss",
        f"{start:.3f}",
        "-i",
        str(source_path),
        "-t",
        f"{duration:.3f}",
        "-vn",
        "-ac",
        "2",
        "-ar",
        str(int(sample_rate)),
        "-c:a",
        "pcm_s16le",
        "-y",
        str(wav_path),
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=_hidden_process_flags(),
        timeout=max(180, int(duration * 1.5)),
        check=False,
    )
    if completed.returncode != 0 or not wav_path.exists():
        detail = (completed.stderr or tr("error.audio_read", language)).strip().splitlines()
        raise AnalysisError(
            tr(
                "error.decode_failed",
                language,
                detail=detail[-1] if detail else tr("error.unknown", language),
            )
        )
    try:
        with wave.open(str(wav_path), "rb") as decoded:
            actual_duration = decoded.getnframes() / decoded.getframerate()
    except (OSError, wave.Error) as exc:
        raise AnalysisError(tr("error.audio_read", language)) from exc
    if actual_duration < MIN_ANALYSIS_SECONDS:
        raise AnalysisError(tr("error.too_short", language))
    return actual_duration


def decode_segment(
    source: str | Path,
    start_seconds: float,
    end_seconds: float,
    progress: Callable[[int, str], None] | None = None,
    language: str = "ko",
) -> tuple[np.ndarray, int, float]:
    """선택 구간 또는 전체 곡을 22.05 kHz 스테레오 배열로 디코딩한다."""
    with tempfile.TemporaryDirectory(prefix="tonematch_tmp_") as tmp_dir:
        wav_path = Path(tmp_dir) / "segment.wav"
        duration = decode_to_pcm_wav(
            source,
            start_seconds,
            end_seconds,
            wav_path,
            SAMPLE_RATE,
            progress,
            language,
        )
        samples, sample_rate = read_pcm_wav(wav_path, language)
    return samples, sample_rate, duration


def read_pcm_wav(path: str | Path, language: str = "ko") -> tuple[np.ndarray, int]:
    """8/16/24/32-bit PCM WAV를 -1~1 범위의 스테레오 float 배열로 읽는다."""
    with wave.open(str(path), "rb") as wav_file:
        channels = wav_file.getnchannels()
        width = wav_file.getsampwidth()
        sample_rate = wav_file.getframerate()
        frame_count = wav_file.getnframes()
        raw = wav_file.readframes(frame_count)
    if width == 1:
        audio = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    elif width == 2:
        audio = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    elif width == 3:
        octets = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
        values = octets[:, 0].astype(np.int32) | (octets[:, 1].astype(np.int32) << 8) | (octets[:, 2].astype(np.int32) << 16)
        values = np.where(values & 0x800000, values - 0x1000000, values)
        audio = values.astype(np.float32) / 8_388_608.0
    elif width == 4:
        audio = np.frombuffer(raw, dtype="<i4").astype(np.float32) / 2_147_483_648.0
    else:
        raise AnalysisError(tr("error.bit_depth", language, bits=width * 8))
    if channels < 1:
        raise AnalysisError(tr("error.no_channels", language))
    audio = audio.reshape(-1, channels)
    if channels == 1:
        audio = np.repeat(audio, 2, axis=1)
    elif channels > 2:
        audio = audio[:, :2]
    return np.nan_to_num(audio, copy=False), sample_rate


def _frames(signal: np.ndarray, frame_length: int, hop: int) -> np.ndarray:
    """1차원 신호를 겹치는 고정 길이 프레임의 2차원 뷰로 나눈다."""
    if len(signal) < frame_length:
        signal = np.pad(signal, (0, frame_length - len(signal)))
    count = 1 + (len(signal) - frame_length) // hop
    shape = (count, frame_length)
    strides = (signal.strides[0] * hop, signal.strides[0])
    return np.lib.stride_tricks.as_strided(signal, shape=shape, strides=strides)


def _frame_rms(framed: np.ndarray, batch_size: int = 256) -> np.ndarray:
    """긴 곡에서도 메모리가 급증하지 않도록 프레임 RMS를 묶음 단위로 계산한다."""
    values = np.empty(len(framed), dtype=np.float64)
    for start in range(0, len(framed), batch_size):
        end = min(len(framed), start + batch_size)
        batch = framed[start:end].astype(np.float64, copy=False)
        values[start:end] = np.sqrt(np.mean(np.square(batch), axis=1) + 1e-12)
    return values


def _band_ratio(power: np.ndarray, frequencies: np.ndarray, low: float, high: float) -> float:
    """전체 스펙트럼 파워 중 지정 주파수 대역이 차지하는 비율을 구한다."""
    mask = (frequencies >= low) & (frequencies < high)
    if not np.any(mask):
        return 0.0
    return float(np.sum(power[:, mask]) / (np.sum(power) + 1e-12))


def _autocorrelation_metrics(onset: np.ndarray, frame_rate: float) -> tuple[float, int, int]:
    """온셋 엔벨로프 자기상관으로 반복 강도, 딜레이 후보와 BPM을 추정한다."""
    centered = onset.astype(np.float64) - float(np.mean(onset))
    if len(centered) < 8 or float(np.dot(centered, centered)) < 1e-12:
        return 0.0, 0, 0
    size = 1 << (2 * len(centered) - 1).bit_length()
    spectrum = np.fft.rfft(centered, n=size)
    corr = np.fft.irfft(spectrum * np.conj(spectrum), n=size)[: len(centered)]
    corr /= max(float(corr[0]), 1e-12)
    delay_lo = max(2, int(round(0.08 * frame_rate)))
    delay_hi = min(len(corr) - 1, int(round(0.80 * frame_rate)))
    if delay_hi <= delay_lo:
        return 0.0, 0, 0
    delay_slice = corr[delay_lo : delay_hi + 1]
    delay_index = int(np.argmax(delay_slice)) + delay_lo
    delay_strength = clamp((float(corr[delay_index]) - 0.08) / 0.42)
    tempo_lo = max(delay_lo, int(round(frame_rate * 60.0 / 200.0)))
    tempo_hi = min(delay_hi, int(round(frame_rate * 60.0 / 60.0)))
    tempo_index = int(np.argmax(corr[tempo_lo : tempo_hi + 1])) + tempo_lo
    bpm = int(round(60.0 * frame_rate / max(1, tempo_index)))
    while bpm < 70:
        bpm *= 2
    while bpm > 190:
        bpm //= 2
    delay_ms = int(round(delay_index * 1000.0 / frame_rate))
    return delay_strength, delay_ms, bpm


def extract_features(samples: np.ndarray, sample_rate: int = SAMPLE_RATE, language: str = "ko") -> ToneFeatures:
    """PCM에서 포화도·밝기·바디·다이내믹·공간 및 오염 특징을 계산한다."""
    if samples.ndim != 2 or samples.shape[1] < 2:
        raise AnalysisError(tr("error.pcm_shape", language))
    original_peak = float(np.max(np.abs(samples)))
    rms_original = float(np.sqrt(np.mean(np.square(samples, dtype=np.float64)) + 1e-12))
    clipping = float(np.mean(np.abs(samples) >= 0.999))
    mid = np.mean(samples[:, :2], axis=1, dtype=np.float32)
    side = (samples[:, 0] - samples[:, 1]) * 0.5
    mid -= float(np.mean(mid))
    mid_rms = float(np.sqrt(np.mean(np.square(mid, dtype=np.float64)) + 1e-12))
    side_rms = float(np.sqrt(np.mean(np.square(side, dtype=np.float64)) + 1e-12))
    stereo_width = clamp(side_rms / (mid_rms + side_rms + 1e-12))
    if mid_rms < 1e-5:
        raise AnalysisError(tr("error.silence", language))
    normalized = mid / max(float(np.max(np.abs(mid))), 1e-9)

    frame_length = 2048
    # 5~20분 전체 곡도 일정한 메모리에서 다루도록 최대 프레임 수를 제한한다.
    hop = max(512, int(math.ceil(max(1, len(normalized) - frame_length) / MAX_ENVELOPE_FRAMES)))
    framed = _frames(normalized, frame_length, hop)
    frame_rms = _frame_rms(framed)
    active_threshold = max(0.008, float(np.percentile(frame_rms, 35)) * 0.55)
    active_mask = frame_rms >= active_threshold
    active_percent = float(np.mean(active_mask))
    if int(np.sum(active_mask)) < 4:
        active_mask[:] = True

    spectral_frames = framed[active_mask]
    if len(spectral_frames) > 1200:
        indices = np.linspace(0, len(spectral_frames) - 1, 1200, dtype=int)
        spectral_frames = spectral_frames[indices]
    window = np.hanning(frame_length).astype(np.float32)
    magnitude = np.abs(np.fft.rfft(spectral_frames * window, axis=1)) + 1e-10
    power = np.square(magnitude)
    frequencies = np.fft.rfftfreq(frame_length, 1.0 / sample_rate)
    frame_power = np.sum(power, axis=1) + 1e-12
    centroids = np.sum(power * frequencies[None, :], axis=1) / frame_power
    centroid = float(np.median(centroids))
    cumulative = np.cumsum(power, axis=1)
    roll_indices = np.argmax(cumulative >= (frame_power * 0.85)[:, None], axis=1)
    rolloff = float(np.median(frequencies[roll_indices]))
    flatness_frames = np.exp(np.mean(np.log(power), axis=1)) / (np.mean(power, axis=1) + 1e-12)
    flatness = float(np.median(flatness_frames))

    sub = _band_ratio(power, frequencies, 30, 110)
    low = _band_ratio(power, frequencies, 110, 250)
    low_mid = _band_ratio(power, frequencies, 250, 700)
    mid_band = _band_ratio(power, frequencies, 700, 1500)
    presence = _band_ratio(power, frequencies, 1500, 4000)
    air = _band_ratio(power, frequencies, 4000, 8000)
    cymbal = _band_ratio(power, frequencies, 8000, min(11000, sample_rate / 2))

    signs = np.signbit(framed[active_mask])
    zcr = float(np.mean(signs[:, 1:] != signs[:, :-1]))
    active_rms = frame_rms[active_mask]
    p20, p90 = np.percentile(active_rms, [20, 90])
    dynamic_range = max(0.0, db(float(p90) / max(float(p20), 1e-9)))
    crest = db(float(np.percentile(np.abs(normalized), 99.9)) / max(float(np.sqrt(np.mean(normalized**2))), 1e-9))

    smooth_rms = np.convolve(frame_rms, np.ones(3) / 3.0, mode="same")
    onset = np.maximum(0.0, np.diff(smooth_rms, prepend=smooth_rms[0]))
    onset /= float(np.percentile(onset, 95) + 1e-9)
    onset = np.clip(onset, 0.0, 3.0)
    onset_density = clamp(float(np.mean(onset > 0.28)) / 0.22)
    frame_rate = sample_rate / hop
    delay_strength, delay_ms, bpm = _autocorrelation_metrics(onset, frame_rate)

    envelope = smooth_rms / max(float(np.mean(smooth_rms)), 1e-9)
    envelope_centered = envelope - np.mean(envelope)
    mod_spectrum = np.abs(np.fft.rfft(envelope_centered * np.hanning(len(envelope_centered))))
    mod_freqs = np.fft.rfftfreq(len(envelope_centered), 1.0 / frame_rate)
    mod_mask = (mod_freqs >= 0.2) & (mod_freqs <= 3.5)
    if np.any(mod_mask):
        mod_values = mod_spectrum[mod_mask]
        modulation_peak = float(np.max(mod_values) / (np.mean(mod_values) + 1e-9))
    else:
        modulation_peak = 0.0

    # 온셋 뒤 꼬리 비율은 룸/리버브의 거친 단서이므로 의도적으로 가중치를 낮춘다.
    peak_indices = np.flatnonzero(onset > 0.65)
    tail_ratios: list[float] = []
    tail_start = max(1, int(0.18 * frame_rate))
    tail_end = max(tail_start + 1, int(0.55 * frame_rate))
    guard = max(1, int(0.08 * frame_rate))
    last = -tail_end
    for index in peak_indices:
        if index - last < tail_end or index + tail_end >= len(smooth_rms):
            continue
        early = float(np.mean(smooth_rms[index : index + guard]))
        late = float(np.mean(smooth_rms[index + tail_start : index + tail_end]))
        if early > 1e-5:
            tail_ratios.append(late / early)
            last = int(index)
    tail_ratio = float(np.median(tail_ratios)) if tail_ratios else 0.30

    # 기타의 기본음이 낮아도 배음 분포 차이가 보이도록 중심 주파수와 대역 기울기를 함께 쓴다.
    centroid_norm = clamp((centroid - 150.0) / 1200.0)
    spectral_tilt = math.log10((presence + air + 0.01) / (low + low_mid + 0.01))
    brightness = clamp(0.55 * centroid_norm + 0.45 * clamp((spectral_tilt + 2.2) / 1.6))
    body = clamp(0.10 + 0.75 * (low + low_mid) - 0.40 * (presence + air))
    flatness_norm = clamp((math.log10(max(flatness, 1e-7)) + 4.0) / 3.2)
    zcr_norm = clamp((zcr - 0.018) / 0.16)
    harmonic_broadness = clamp((presence + air - 0.08) / 0.42)
    compression = clamp(0.58 * (1.0 - dynamic_range / 22.0) + 0.42 * (1.0 - crest / 18.0))
    saturation = clamp(0.42 * flatness_norm + 0.27 * zcr_norm + 0.19 * harmonic_broadness + 0.12 * compression)
    modulation = clamp((modulation_peak - 3.0) / 14.0) * (1.0 - 0.35 * onset_density)
    ambience = clamp(0.46 * clamp((tail_ratio - 0.20) / 0.70) + 0.31 * stereo_width + 0.23 * delay_strength)

    mix_contamination = clamp(
        0.34 * clamp((sub - 0.025) / 0.13)
        + 0.23 * clamp((cymbal - 0.015) / 0.10)
        + 0.25 * onset_density
        + 0.18 * stereo_width
    )
    duration = len(samples) / sample_rate
    analysis_confidence = clamp(
        0.42
        + 0.23 * clamp((duration - 3.0) / 17.0)
        + 0.18 * clamp(active_percent / 0.65)
        + 0.12 * (1.0 - mix_contamination)
        + 0.05 * (1.0 - clamp(clipping / 0.02))
    )

    return ToneFeatures(
        saturation=saturation,
        brightness=brightness,
        body=body,
        compression=compression,
        ambience=ambience,
        modulation=modulation,
        delay_strength=delay_strength,
        delay_ms=delay_ms,
        bpm=bpm,
        stereo_width=stereo_width,
        mix_contamination=mix_contamination,
        analysis_confidence=analysis_confidence,
        spectral_centroid_hz=centroid,
        spectral_rolloff_hz=rolloff,
        spectral_flatness=flatness,
        dynamic_range_db=dynamic_range,
        crest_factor_db=crest,
        rms_dbfs=db(rms_original),
        peak_dbfs=db(original_peak),
        clipping_percent=clipping * 100.0,
        active_audio_percent=active_percent * 100.0,
    )


PICKUP_CORRECTIONS = {
    "strat_bridge": {"gain": 5, "treble": -4, "bass": 2, "note_key": "pickup_note.strat_bridge"},
    "strat_neck": {"gain": 5, "treble": 2, "bass": -3, "note_key": "pickup_note.strat_neck"},
    "tele_bridge": {"gain": 5, "treble": -6, "bass": 3, "note_key": "pickup_note.tele_bridge"},
    "p90": {"gain": 1, "treble": -1, "bass": 0, "note_key": "pickup_note.p90"},
    "humbucker_bridge": {"gain": -5, "treble": 4, "bass": -3, "note_key": "pickup_note.humbucker_bridge"},
    "humbucker_neck": {"gain": -6, "treble": 7, "bass": -6, "note_key": "pickup_note.humbucker_neck"},
    "unknown": {"gain": 0, "treble": 0, "bass": 0, "note_key": "pickup_note.unknown"},
}


def _parameter(value: float, correction: int = 0) -> str:
    """정규화된 파라미터에 보정치를 적용하고 TMP 표시용 백분율로 만든다."""
    return f"{int(round(clamp(value + correction / 100.0) * 100))}%"


def _amp_parameters(model: str, f: ToneFeatures, correction: dict, language: str = "ko") -> dict[str, str]:
    """앰프 모델별 실제 컨트롤 이름에 맞춘 게인·EQ 시작값을 만든다."""
    gain = clamp(0.18 + 0.62 * f.saturation + correction["gain"] / 100.0)
    bass = clamp(0.35 + 0.34 * f.body + correction["bass"] / 100.0)
    treble = clamp(0.30 + 0.44 * f.brightness + correction["treble"] / 100.0)
    middle = clamp(0.58 - 0.16 * f.brightness + 0.08 * f.body)
    presence = clamp(0.34 + 0.35 * f.brightness)
    if model == "Fender '65 Twin Reverb":
        return {
            "BRIGHT SWITCH": "ON" if f.brightness > 0.74 else "OFF",
            "VOLUME": _parameter(0.20 + 0.42 * f.saturation, correction["gain"]),
            "TREBLE": _parameter(treble),
            "MIDDLE": _parameter(middle),
            "BASS": _parameter(bass),
        }
    if model == "Fender '65 Deluxe Reverb Blonde NBC":
        return {
            "VOLUME": _parameter(0.20 + 0.42 * f.saturation, correction["gain"]),
            "TREBLE": _parameter(treble),
            "BASS": _parameter(bass),
        }
    if model == "JC Clean":
        return {
            "BRIGHT SWITCH": "ON" if f.brightness > 0.78 else "OFF",
            "VOLUME": _parameter(0.32 + 0.18 * f.saturation, correction["gain"]),
            "TREBLE": _parameter(treble),
            "MIDDLE": _parameter(0.48 + 0.08 * f.body),
            "BASS": _parameter(bass),
        }
    if model == "Fender '59 Bassman Custom":
        return {
            "VOL NORMAL": _parameter(0.28 + 0.35 * f.body, correction["gain"]),
            "VOL BRIGHT": _parameter(0.24 + 0.45 * f.saturation + 0.10 * f.brightness, correction["gain"]),
            "TREBLE": _parameter(treble),
            "MIDDLE": _parameter(middle),
            "BASS": _parameter(bass),
            "PRESENCE": _parameter(presence),
        }
    if model == "UK 30 Brilliant":
        return {
            "VOLUME": _parameter(0.25 + 0.55 * f.saturation, correction["gain"]),
            "TREBLE": _parameter(treble),
            "BASS": _parameter(bass),
            "CUT": _parameter(clamp(0.66 - 0.42 * f.brightness - correction["treble"] / 100.0)),
        }
    if model in {"British Plexi", "British 45"}:
        return {
            "VOLUME I": _parameter(gain),
            "VOLUME II": _parameter(clamp(0.22 + 0.42 * f.body + correction["gain"] / 200.0)),
            "TREBLE": _parameter(treble),
            "MIDDLE": _parameter(middle),
            "BASS": _parameter(bass),
            "PRESENCE": _parameter(presence),
        }
    if model.startswith("EVH 5150"):
        return {
            "GAIN": _parameter(gain),
            "VOLUME": tr("value.level_match", language, value="50%"),
            "LOW": _parameter(bass),
            "MID": _parameter(middle),
            "HIGH": _parameter(treble),
            "PRESENCE": _parameter(presence),
            "RESONANCE": _parameter(0.32 + 0.34 * f.body),
        }
    if model in {"British 800", "British Jubilee Lead", "Solo 100 Overdrive", "Double Wreck", "Petrol"}:
        params = {
            "GAIN": _parameter(gain),
            "MASTER": tr("value.level_match", language, value="50%"),
            "TREBLE": _parameter(treble),
            "MIDDLE": _parameter(middle),
            "BASS": _parameter(bass),
            "PRESENCE": _parameter(presence),
        }
        if model == "Solo 100 Overdrive":
            params["DEPTH"] = _parameter(0.30 + 0.38 * f.body)
        return params
    return {"GAIN": _parameter(gain), "TREBLE": _parameter(treble), "MIDDLE": _parameter(middle), "BASS": _parameter(bass)}


def _drive_parameters(model: str, f: ToneFeatures) -> dict[str, str]:
    """드라이브·부스트·퍼즈 모델별 컨트롤 시작값을 계산한다."""
    drive = clamp(0.08 + 0.60 * f.saturation)
    tone = clamp(0.34 + 0.42 * f.brightness)
    if model == "Lightyear":
        return {"DRIVE": _parameter(drive * 0.55), "LOUDNESS": "58%", "FREQ": _parameter(tone)}
    if model == "Blues Maker":
        return {"GAIN": _parameter(drive * 0.70), "TONE": _parameter(tone), "VOLUME": "58%", "VERSION SWITCH": "Version 1" if f.brightness < 0.58 else "Version 2"}
    if model in {"Greenbox 8", "Greenbox 10"}:
        params = {"DRIVE": _parameter(0.08 + 0.22 * f.saturation), "TONE": _parameter(tone), "LEVEL": _parameter(0.62 + 0.18 * f.saturation), "BLEND": "100%"}
        if model == "Greenbox 10":
            params["BASS SWITCH"] = "OFF" if f.body > 0.48 else "ON"
        return params
    if model == "Mythic Drive" or model == "Mythic Drive II":
        return {"GAIN": _parameter(drive * 0.58), "TREBLE": _parameter(tone), "OUTPUT": "58%"}
    if model == "Integrator Boost":
        return {"TREBLE": _parameter(0.48 + 0.20 * f.brightness), "BASS": _parameter(0.28 + 0.20 * f.body), "VOLUME": _parameter(0.62 + 0.16 * f.saturation)}
    if model == "Grunt Boost":
        return {"GRUNT": _parameter(0.58 + 0.20 * f.saturation)}
    if model == "Round Fuzz (Germanium)":
        return {"FUZZ": _parameter(0.48 + 0.42 * f.saturation), "VOLUME": "52%"}
    if model == "Big Apple Fuzz":
        return {"SUSTAIN": _parameter(0.42 + 0.50 * f.saturation), "LEVEL": "50%", "TONE": _parameter(tone), "BLEND": "100%", "MIDS": "FLAT" if f.body > 0.42 else "BOOST"}
    if model == "Rockbox 100":
        if f.saturation < 0.25:
            mode = "Clean 1"
        elif f.saturation < 0.45:
            mode = "Edge"
        else:
            mode = "Distortion"
        effect = "Chorus + Echo" if f.ambience > 0.45 else "Chorus"
        return {"MODE": mode, "VOLUME": "50%", "INPUT GAIN": _parameter(0.28 + 0.45 * f.compression), "EFFECTS": effect}
    return {"DRIVE": _parameter(drive), "TONE": _parameter(tone), "LEVEL": "55%"}


def _reverb_parameters(model: str, f: ToneFeatures) -> dict[str, str]:
    """리버브 모델 유형에 맞춰 믹스·감쇠·댐핑 등 공간 파라미터를 만든다."""
    mix = clamp(0.06 + 0.40 * f.ambience)
    decay = clamp(0.18 + 0.68 * f.ambience)
    if model == "'65 Spring Reverb":
        return {"REVERB": _parameter(mix), "TONE": _parameter(0.38 + 0.25 * f.brightness), "SPILLOVER SWITCH": "ON"}
    if model in {"Small Room Reverb", "Small Hall Reverb"}:
        size_name = "ROOM SIZE" if "Room" in model else "HALL SIZE"
        return {
            "MIX": _parameter(min(mix, 0.24)),
            "PRE-DELAY": f"{int(8 + 28 * f.ambience)} ms",
            "DECAY": _parameter(min(decay, 0.52)),
            "DAMPING": _parameter(0.46 + 0.25 * (1.0 - f.brightness)),
            "DIFFUSE": _parameter(0.46 + 0.28 * f.ambience),
            size_name: _parameter(0.24 + 0.38 * f.ambience),
            "SPILLOVER SWITCH": "ON",
        }
    if model in {"Large Plate Reverb", "Small Plate Reverb"}:
        params = {
            "MIX": _parameter(mix),
            "DECAY": _parameter(decay),
            "DIFFUSE": _parameter(0.48 + 0.30 * f.ambience),
            "HIGH DAMP": _parameter(0.45 + 0.28 * (1.0 - f.brightness)),
            "LOW DAMP": _parameter(0.38 + 0.18 * f.body),
            "HI TONE" if model == "Small Plate Reverb" else "HIGH TONE": _parameter(0.40 + 0.22 * f.brightness),
            "LOW TONE": _parameter(0.40 + 0.22 * f.body),
            "BALANCE": "55%",
            "SPILLOVER" if model == "Small Plate Reverb" else "SPILLOVER SWITCH": "ON",
        }
        return params
    if model == "Modulated Large Hall Reverb" or model == "Large Hall Reverb":
        params = {
            "MIX" if model == "Large Hall Reverb" else "LEVEL": _parameter(max(mix, 0.24)),
            "DECAY": _parameter(max(decay, 0.58)),
            "DIFFUSE": _parameter(0.58 + 0.30 * f.ambience),
            "SPILLOVER SWITCH": "ON",
        }
        if model == "Large Hall Reverb":
            params.update({"PRE-DELAY": f"{int(18 + 42 * f.ambience)} ms", "DAMPING": "58%", "HALL SIZE": _parameter(0.55 + 0.35 * f.ambience), "MOD DEPTH": _parameter(0.15 + 0.28 * f.modulation)})
        else:
            params.update({"DWELL": "55%", "RATE": _parameter(0.12 + 0.18 * f.modulation), "DEPTH": _parameter(0.16 + 0.32 * f.modulation), "HIGH CUT": "58%", "LOW CUT": "38%"})
        return params
    return {"MIX": _parameter(mix), "DECAY": _parameter(decay), "SPILLOVER SWITCH": "ON"}


def _parse_mic_position(value: object) -> tuple[str, str]:
    """카탈로그의 위치·거리·축 문자열을 검증해 TMP 표시값과 축 값으로 분리한다."""
    parts = [part.strip() for part in str(value or "").split("/")]
    if len(parts) != 3 or not parts[0] or not parts[1]:
        raise ValueError(f"잘못된 캐비닛 마이크 위치 형식입니다: {value!r}")
    axis_code = parts[2].lower()
    if axis_code not in {"on-axis", "off-axis"}:
        raise ValueError(f"지원하지 않는 캐비닛 마이크 축입니다: {parts[2]!r}")
    distance_text = parts[1].lower().removesuffix("in").strip()
    try:
        distance = float(distance_text)
    except ValueError as exc:
        raise ValueError(f"잘못된 캐비닛 마이크 거리입니다: {parts[1]!r}") from exc
    if not math.isfinite(distance) or distance < 0:
        raise ValueError(f"캐비닛 마이크 거리는 0 이상이어야 합니다: {parts[1]!r}")
    return f"{parts[0]} / {parts[1]}", "ON AXIS" if axis_code == "on-axis" else "OFF AXIS"


def _cabinet_parameters(template: dict, f: ToneFeatures) -> dict[str, str]:
    """검증한 TMP 캐비닛 마이크 위치·축과 톤 기반 컷 필터 시작값을 만든다."""
    position, axis = _parse_mic_position(template["mic_position"])
    high_cut = int(round(6800 + 3000 * (1.0 - f.brightness)))
    low_cut = int(round(68 + 35 * (1.0 - f.body)))
    return {
        "MIC": template["mic"],
        "MIC POSITION": position,
        "AXIS": axis,
        "LOW CUT FILTER": f"{low_cut} Hz",
        "HIGH CUT FILTER": f"{high_cut} Hz",
    }


def _make_block(
    category: str,
    model: str,
    parameters: dict[str, str],
    reason_key: str,
    language: str,
) -> dict:
    """화면과 내보내기에서 공통으로 쓰는 단일 TMP 블록 사전을 만든다."""
    return {
        "category": category,
        "category_label": tr(f"category.{category}", language),
        "model": model,
        "parameters": parameters,
        "reason": tr(reason_key, language),
    }


def _recipe_from_template(
    template: dict,
    f: ToneFeatures,
    pickup: str,
    output_mode: str,
    score: float,
    language: str = "ko",
) -> dict:
    """한 톤 템플릿을 순서가 지정된 TMP 블록 레시피로 확장한다."""
    correction = PICKUP_CORRECTIONS.get(pickup, PICKUP_CORRECTIONS["unknown"])
    blocks: list[dict] = []
    if f.saturation > 0.66 and template["drive"] != "Rockbox 100":
        blocks.append(_make_block("Dynamics", "Metal Gate", {"THRESHOLD": _parameter(0.26 + 0.34 * f.saturation), "ATTENUATION": "100%"}, "reason.gate", language))
    elif f.saturation < 0.38 and f.compression > 0.30:
        blocks.append(_make_block("Dynamics", "Pedal Comp", {"COMP": _parameter(0.16 + 0.36 * f.compression), "ATTACK": _parameter(0.55 + 0.22 * (1.0 - f.compression)), "TONE": _parameter(0.42 + 0.16 * f.brightness), "LEVEL": "50%"}, "reason.compressor", language))
    if template["drive"]:
        blocks.append(_make_block("Stompbox", template["drive"], _drive_parameters(template["drive"], f), "reason.drive", language))

    use_amp = output_mode != "amp_front"
    use_cab = output_mode == "frfr"
    if template["amp"] and use_amp:
        # 콤보/스택의 내장 캐비닛이 중복되지 않도록 공식 Amp Only 변형을 선택한다.
        blocks.append(_make_block("Amp Head", f"{template['amp']} (Amp Only)", _amp_parameters(template["amp"], f, correction, language), "reason.amp", language))
    if template["cab"] and use_cab:
        blocks.append(
            _make_block(
                "Cabinet",
                template["cab"],
                _cabinet_parameters(template, f),
                "reason.cab",
                language,
            )
        )
    if template["mod"] and (f.modulation > 0.12 or template["id"] in {"ambient_clean", "shoegaze_fuzz", "jc_wide_clean"}):
        blocks.append(
            _make_block(
                "Modulation",
                template["mod"],
                {
                    "RATE": f"{0.25 + 1.35 * f.modulation:.2f} Hz",
                    "DEPTH": _parameter(0.16 + 0.48 * f.modulation),
                    "MIX": _parameter(0.10 + 0.34 * f.modulation),
                    "LOW CUT": "120 Hz",
                    "HIGH CUT": "7.5 kHz",
                    "WIDTH": _parameter(0.55 + 0.38 * f.stereo_width),
                },
                "reason.mod",
                language,
            )
        )
    if template["delay"] and (f.delay_strength > 0.10 or f.ambience > 0.26 or "lead" in template["id"]):
        time_ms = int(np.clip(f.delay_ms if f.delay_strength > 0.20 else round(45_000 / max(f.bpm, 70)), 90, 750))
        delay_params = {
            "TIME": f"{time_ms} ms",
            "FEEDBACK": _parameter(0.12 + 0.46 * f.delay_strength + 0.16 * f.ambience),
            "MIX": _parameter(0.08 + 0.34 * max(f.delay_strength, f.ambience)),
            "TAP DIVISION": "1/8 dotted" if time_ms < 520 else "1/4",
            "SPILLOVER SWITCH": "ON",
        }
        if template["delay"] == "Stereo Memory Delay":
            division = delay_params.pop("TAP DIVISION")
            delay_params.update(
                {
                    "TIME LEFT": delay_params.pop("TIME"),
                    "TIME RIGHT": f"{int(time_ms * 1.06)} ms",
                    "TAP DIVISION LEFT": division,
                    "TAP DIVISION RIGHT": division,
                    "DEPTH": _parameter(0.14 + 0.34 * f.modulation),
                    "GAIN": "0 dB",
                    "GRIT": _parameter(0.12 + 0.20 * f.saturation),
                    "MODE SWITCH": "CHORUS",
                }
            )
        blocks.append(_make_block("Delay", template["delay"], delay_params, "reason.delay", language))
    if template["reverb"]:
        blocks.append(_make_block("Reverb", template["reverb"], _reverb_parameters(template["reverb"], f), "reason.reverb", language))
    for index, block in enumerate(blocks, start=1):
        block["order"] = index

    confidence = clamp((0.42 + 0.58 * score) * (0.62 + 0.38 * f.analysis_confidence))
    if f.mix_contamination > 0.58:
        confidence *= 0.82
    limitations = []
    if f.mix_contamination > 0.52:
        limitations.append(tr("limit.full_mix", language))
    if output_mode == "power_amp_cab":
        limitations.append(tr("limit.real_cab", language))
        if template.get("cab"):
            limitations.append(tr("limit.reference_cab", language, cabinet=template["cab"]))
    if output_mode == "amp_front":
        limitations.append(tr("limit.amp_front", language))
    applicability = "high" if output_mode == "frfr" else "medium" if output_mode == "power_amp_cab" else "low"
    return {
        "template_id": template["id"],
        "name": template["name_en"] if language == "en" else template["name"],
        "archetype": template["archetype_en"] if language == "en" else template["archetype"],
        "description": template["description_en"] if language == "en" else template["description"],
        "match_percent": int(round(confidence * 100)),
        "tags": template["tags"],
        "pickup_correction": tr(correction["note_key"], language),
        "output_mode": output_mode,
        "output_mode_label": choice_label("output", output_mode, language),
        "route_applicability": applicability,
        "route_applicability_label": tr(f"route.{applicability}", language),
        "reference_amp": template.get("amp"),
        "reference_cabinet": template.get("cab"),
        "amp_included": bool(template.get("amp") and use_amp),
        "cabinet_included": bool(template.get("cab") and use_cab),
        "omitted_reference_amp": template.get("amp") if template.get("amp") and not use_amp else None,
        "omitted_reference_cabinet": template.get("cab") if template.get("cab") and not use_cab else None,
        "blocks": blocks,
        "limitations": limitations,
    }


def _template_score(template: dict, f: ToneFeatures) -> float:
    """측정 특징과 템플릿 목표의 가중 제곱 거리를 0~1 유사도로 바꾼다."""
    weights = {"saturation": 0.30, "brightness": 0.17, "body": 0.15, "compression": 0.14, "ambience": 0.16, "modulation": 0.08}
    distance = 0.0
    for key, weight in weights.items():
        distance += weight * (getattr(f, key) - template["target"][key]) ** 2
    return math.exp(-distance / 0.10)


def _adjust_for_mix(features: ToneFeatures, mix_mode: str) -> ToneFeatures:
    """단독 기타 또는 풀믹스 선택에 따라 오염도와 핵심 특징을 보수적으로 보정한다."""
    values = asdict(features)
    contamination = features.mix_contamination
    if mix_mode == "isolated":
        values["mix_contamination"] = min(contamination, 0.18)
        values["analysis_confidence"] = clamp(features.analysis_confidence + 0.08)
    elif mix_mode == "full_mix":
        values["mix_contamination"] = max(contamination, 0.62)
        values["saturation"] = clamp(features.saturation * 0.78)
        values["ambience"] = clamp(features.ambience * 0.82)
        values["brightness"] = clamp(features.brightness * 0.94)
        values["analysis_confidence"] = clamp(features.analysis_confidence - 0.12)
    elif contamination > 0.45:
        values["saturation"] = clamp(features.saturation * (1.0 - 0.22 * contamination))
        values["ambience"] = clamp(features.ambience * (1.0 - 0.15 * contamination))
        values["analysis_confidence"] = clamp(features.analysis_confidence - 0.10 * contamination)
    return ToneFeatures(**values)


def _application_steps(output_mode: str, language: str) -> list[str]:
    """실제 출력 연결에서 포함되는 앰프·캐비닛 블록과 일치하는 적용 순서를 만든다."""
    route_step = {
        "frfr": "step.amp_only",
        "power_amp_cab": "step.power_amp_real_cab",
        "amp_front": "step.amp_front",
    }.get(output_mode, "step.amp_only")
    comparison_step = {
        "frfr": "step.ab",
        "power_amp_cab": "step.ab_power_amp",
        "amp_front": "step.ab_amp_front",
    }.get(output_mode, "step.ab")
    return [
        tr("step.new_preset", language),
        tr("step.series", language),
        tr(route_step, language),
        tr("step.parameters", language),
        tr(comparison_step, language),
    ]


def analyze_file(
    source: str | Path,
    start_seconds: float,
    end_seconds: float,
    pickup: str,
    mix_mode: str,
    output_mode: str,
    reference_url: str = "",
    progress: Callable[[int, str], None] | None = None,
    device_id: str = "tone_master_pro",
    language: str = "ko",
    cancel_requested: Callable[[], bool] | None = None,
    compute_backend: str = "auto",
) -> dict:
    """디코딩·기타 분리·DSP 분석·장치 레시피 조립의 전체 순서를 실행한다."""
    if not is_supported_device(device_id):
        raise AnalysisError(tr("error.unsupported_device", language))
    pickup_code = choice_code("pickup", pickup)
    mix_code = choice_code("mix", mix_mode)
    output_code = choice_code("output", output_mode)
    compute_code = choice_code("compute", compute_backend)
    separation_requested = mix_code != "isolated"
    separation_data: dict[str, object] = {
        "used": False,
        "mode": mix_code,
        "model": None,
        "requested_device": compute_code,
        "resolved_device": None,
    }
    if separation_requested:
        with tempfile.TemporaryDirectory(prefix="tonematch_isolate_") as tmp_dir:
            temporary = Path(tmp_dir)
            mixture_wav = temporary / "selected_mix.wav"
            guitar_wav = temporary / "guitar.wav"
            analysis_wav = temporary / "guitar_analysis.wav"
            duration = decode_to_pcm_wav(
                source,
                start_seconds,
                end_seconds,
                mixture_wav,
                SEPARATOR_SAMPLE_RATE,
                progress,
                language,
            )
            try:
                separation = separate_guitar_wav(
                    mixture_wav,
                    guitar_wav,
                    progress,
                    cancel_requested,
                    language,
                    compute_code,
                )
            except SeparationError as exc:
                raise AnalysisError(str(exc)) from exc
            decode_to_pcm_wav(guitar_wav, 0, 0, analysis_wav, SAMPLE_RATE, None, language)
            samples, sample_rate = read_pcm_wav(analysis_wav, language)
            separation_data = {"used": True, "mode": mix_code, **separation_info_dict(separation)}
    else:
        samples, sample_rate, duration = decode_segment(
            source,
            start_seconds,
            end_seconds,
            progress,
            language,
        )
        if progress:
            progress(68, tr("progress.separation_skipped", language))
    if progress:
        progress(70, tr("progress.decode_done", language))
        progress(72, tr("progress.features", language))
    raw_features = extract_features(samples, sample_rate, language)
    if progress:
        progress(80, tr("progress.features_done", language))
        progress(82, tr("progress.voicing", language))
    voicing_analysis = analyze_voicings(samples, sample_rate)
    if progress:
        progress(85, tr("progress.voicing_done", language))
    # 분리를 마친 오디오와 이미 기타 단독인 파일은 모두 isolated 보정을 적용한다.
    features = _adjust_for_mix(raw_features, "isolated")
    if progress:
        progress(87, tr("progress.correction", language))
        progress(90, tr("progress.matching", language))
    ranked = sorted(((template, _template_score(template, features)) for template in TEMPLATES), key=lambda item: item[1], reverse=True)
    if progress:
        progress(94, tr("progress.recipe", language))
    recipes = [
        _recipe_from_template(template, features, pickup_code, output_code, score, language)
        for template, score in ranked[:3]
    ]
    warnings: list[str] = [
        tr("warning.inference", language),
        tr("warning.manual_apply", language),
    ]
    if separation_requested:
        warnings.append(tr("warning.separation_experimental", language))
    elif features.mix_contamination > 0.52:
        warnings.append(tr("warning.full_mix", language))
    if raw_features.clipping_percent > 0.5:
        warnings.append(tr("warning.clipping", language))
    if duration < 8:
        warnings.append(tr("warning.short", language))
    if progress:
        progress(97, tr("progress.assembling", language))
    profile = device_by_id(device_id)
    result = {
        "schema": "tonematch-tmp-recipe/v1",
        "app_version": APP_VERSION,
        "language": language,
        "device_id": device_id,
        "device": device_label(device_id, language),
        "device_name": profile["name"],
        "target_firmware": TARGET_FIRMWARE,
        "model_guide": MODEL_GUIDE_REVISION,
        "source": {
            "file_name": Path(source).name,
            "reference_url": reference_url.strip(),
            "start_seconds": round(float(start_seconds), 3),
            "end_seconds": round(float(start_seconds) + duration, 3),
            "duration_seconds": round(duration, 3),
            "analysis_audio": "guitar_stem",
        },
        "source_separation": separation_data,
        "input_profile": {
            "pickup": pickup_code,
            "pickup_label": choice_label("pickup", pickup_code, language),
            "mix_mode": mix_code,
            "mix_mode_label": choice_label("mix", mix_code, language),
            "output_mode": output_code,
            "output_mode_label": choice_label("output", output_code, language),
            "compute_backend": compute_code,
            "compute_backend_label": choice_label("compute", compute_code, language),
        },
        "features": asdict(features),
        "raw_features": asdict(raw_features),
        "chord_voicing": voicing_analysis_dict(voicing_analysis),
        "recipes": recipes,
        "warnings": warnings,
        "application_steps": _application_steps(output_code, language),
    }
    if progress:
        progress(100, tr("progress.complete", language))
    return result


def save_json(result: dict, path: str | Path) -> None:
    """분석 결과를 한글이 보존되는 들여쓰기 JSON 파일로 저장한다."""
    Path(path).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


def relocalize_result(result: dict, language: str) -> dict:
    """이미 계산한 수치는 유지하고 레시피·경고·적용 문구만 새 언어로 다시 만든다."""
    updated = dict(result)
    features = ToneFeatures(**result["features"])
    profile = result["input_profile"]
    templates_by_id = {template["id"]: template for template in TEMPLATES}
    localized_recipes: list[dict] = []
    for previous in result["recipes"]:
        template = templates_by_id[previous["template_id"]]
        localized = _recipe_from_template(
            template,
            features,
            profile["pickup"],
            profile["output_mode"],
            1.0,
            language,
        )
        localized["match_percent"] = previous["match_percent"]
        localized_recipes.append(localized)
    warnings = [tr("warning.inference", language), tr("warning.manual_apply", language)]
    if result.get("source_separation", {}).get("used"):
        warnings.append(tr("warning.separation_experimental", language))
    elif features.mix_contamination > 0.52:
        warnings.append(tr("warning.full_mix", language))
    if result.get("raw_features", {}).get("clipping_percent", 0.0) > 0.5:
        warnings.append(tr("warning.clipping", language))
    if result["source"].get("duration_seconds", 0.0) < 8.0:
        warnings.append(tr("warning.short", language))
    pickup_code = profile["pickup"]
    mix_code = profile["mix_mode"]
    output_code = profile["output_mode"]
    compute_code = profile.get("compute_backend", "auto")
    updated["language"] = language
    updated["device"] = device_label(result.get("device_id", "tone_master_pro"), language)
    updated["recipes"] = localized_recipes
    updated["warnings"] = warnings
    updated["input_profile"] = {
        **profile,
        "pickup_label": choice_label("pickup", pickup_code, language),
        "mix_mode_label": choice_label("mix", mix_code, language),
        "output_mode_label": choice_label("output", output_code, language),
        "compute_backend_label": choice_label("compute", compute_code, language),
    }
    updated["application_steps"] = _application_steps(output_code, language)
    return updated


def human_feature_rows(features: dict, language: str = "ko") -> Iterable[tuple[str, str]]:
    """원시 특징 사전을 GUI와 HTML 표에서 읽기 쉬운 언어별 행으로 변환한다."""
    labels = [
        ("feature.saturation", "saturation", "%"),
        ("feature.brightness", "brightness", "%"),
        ("feature.body", "body", "%"),
        ("feature.compression", "compression", "%"),
        ("feature.ambience", "ambience", "%"),
        ("feature.modulation", "modulation", "%"),
        ("feature.delay", "delay_strength", "%"),
        ("feature.stereo_width", "stereo_width", "%"),
        ("feature.contamination", "mix_contamination", "%"),
        ("feature.confidence", "analysis_confidence", "%"),
    ]
    for label_key, key, suffix in labels:
        yield tr(label_key, language), f"{int(round(features[key] * 100))}{suffix}"
    yield tr("feature.bpm", language), str(features["bpm"])
    yield tr("feature.delay_ms", language), f"{features['delay_ms']} ms"
    yield tr("feature.centroid", language), f"{features['spectral_centroid_hz']:.0f} Hz"
    yield tr("feature.dynamic_range", language), f"{features['dynamic_range_db']:.1f} dB"
    yield tr("feature.rms", language), f"{features['rms_dbfs']:.1f} dBFS"
    yield tr("feature.peak", language), f"{features['peak_dbfs']:.1f} dBFS"
