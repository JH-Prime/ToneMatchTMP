"""실시간 UI와 분리된 결정론적 스펙트럼 프레임 분석과 평활화를 제공한다."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

import numpy as np


DBFS_FLOOR = -120.0
MIN_SAMPLE_RATE = 8_000


@dataclass(frozen=True)
class SpectrumFrame:
    """파형과 주파수별 레벨 및 대표 레벨 통계를 한 프레임으로 보관한다."""

    waveform: np.ndarray
    frequencies_hz: np.ndarray
    magnitudes_dbfs: np.ndarray
    rms_dbfs: float
    peak_dbfs: float
    spectral_centroid_hz: float


def _validate_integer(value: object, name: str, minimum: int) -> int:
    """불리언을 제외한 정수 설정값인지 확인하고 최소 범위를 적용한다."""

    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise ValueError(f"{name} must be an integer")
    result = int(value)
    if result < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return result


def _validate_frequency(value: object, name: str) -> float:
    """주파수 설정을 유한한 실수로 변환한다."""

    if isinstance(value, (bool, np.bool_)):
        raise ValueError(f"{name} must be a finite number")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not np.isfinite(result):
        raise ValueError(f"{name} must be a finite number")
    return result


def _prepare_pcm(samples: np.ndarray, fft_size: int) -> tuple[np.ndarray, np.ndarray]:
    """정규화 PCM과 왼쪽 0으로 채운 마지막 FFT 프레임을 함께 반환한다."""

    source = np.asarray(samples)
    if source.ndim not in (1, 2):
        raise ValueError("samples must be mono or frames-by-channels PCM")
    if source.size == 0 or source.shape[0] == 0:
        raise ValueError("samples must not be empty")
    if source.ndim == 2 and source.shape[1] == 0:
        raise ValueError("samples must contain at least one channel")
    if np.iscomplexobj(source) or source.dtype.kind not in "biuf":
        raise ValueError("samples must contain real numeric PCM values")

    try:
        pcm = source.astype(np.float64, copy=True)
    except (TypeError, ValueError) as exc:
        raise ValueError("samples must contain real numeric PCM values") from exc
    if pcm.ndim == 1:
        pcm = pcm[:, None]
    pcm = np.nan_to_num(pcm, copy=False, nan=0.0, posinf=1.0, neginf=-1.0)
    np.clip(pcm, -1.0, 1.0, out=pcm)

    level_pcm = pcm[-fft_size:]
    if len(level_pcm) >= fft_size:
        return level_pcm, level_pcm
    padded = np.zeros((fft_size, pcm.shape[1]), dtype=np.float64)
    padded[-len(level_pcm) :] = level_pcm
    return level_pcm, padded


def _power_to_dbfs(power: np.ndarray | float) -> np.ndarray | float:
    """선형 파워를 유한한 dBFS 값으로 바꾸고 표시 하한을 적용한다."""

    values = np.asarray(power, dtype=np.float64)
    converted = np.full(values.shape, DBFS_FLOOR, dtype=np.float64)
    positive = values > 0.0
    converted[positive] = np.maximum(DBFS_FLOOR, 10.0 * np.log10(values[positive]))
    if values.ndim == 0:
        return float(converted)
    return converted


def _dbfs_to_power(levels_dbfs: np.ndarray | float) -> np.ndarray:
    """표시 하한의 무음을 0으로 유지하며 dBFS를 선형 파워로 되돌린다."""

    levels = np.asarray(levels_dbfs, dtype=np.float64)
    return np.where(levels > DBFS_FLOOR, np.power(10.0, levels / 10.0), 0.0)


def _spectral_centroid(frequencies_hz: np.ndarray, power: np.ndarray) -> float:
    """주파수별 선형 파워의 무게중심을 계산하고 무음이면 0을 반환한다."""

    total = float(np.sum(power, dtype=np.float64))
    if total <= 1e-24:
        return 0.0
    return float(np.dot(frequencies_hz.astype(np.float64, copy=False), power) / total)


def analyze_spectrum_frame(
    samples: np.ndarray,
    sample_rate: int,
    *,
    fft_size: int = 2048,
    min_hz: float = 20.0,
    max_hz: float = 20_000.0,
) -> SpectrumFrame:
    """정규화 PCM 한 구간에서 파형, 채널 파워 스펙트럼과 dBFS 통계를 계산한다."""

    checked_rate = _validate_integer(sample_rate, "sample_rate", MIN_SAMPLE_RATE)
    checked_size = _validate_integer(fft_size, "fft_size", 2)
    checked_min = _validate_frequency(min_hz, "min_hz")
    checked_max = _validate_frequency(max_hz, "max_hz")
    if checked_min <= 0.0:
        raise ValueError("min_hz must be greater than zero")
    if checked_max <= checked_min:
        raise ValueError("max_hz must be greater than min_hz")

    nyquist = checked_rate / 2.0
    capped_max = min(checked_max, nyquist)
    if checked_min > capped_max:
        raise ValueError("frequency range must intersect the FFT Nyquist range")

    level_pcm, pcm = _prepare_pcm(samples, checked_size)
    waveform = np.mean(pcm, axis=1, dtype=np.float64)
    np.clip(waveform, -1.0, 1.0, out=waveform)

    # FFT용 왼쪽 패딩은 짧은 실제 블록의 레벨 통계를 낮추면 안 된다.
    mean_square = float(np.mean(np.square(level_pcm), dtype=np.float64))
    peak_amplitude = float(np.max(np.abs(level_pcm)))
    rms_dbfs = float(_power_to_dbfs(mean_square))
    peak_dbfs = float(_power_to_dbfs(peak_amplitude * peak_amplitude))

    centered = pcm - np.mean(pcm, axis=0, keepdims=True, dtype=np.float64)
    window = np.hanning(checked_size).astype(np.float64)
    coherent_gain = float(np.sum(window))
    if coherent_gain <= 0.0:
        raise ValueError("fft_size is too small for a Hann analysis window")
    transformed = np.fft.rfft(centered * window[:, None], axis=0)
    amplitudes = np.abs(transformed) * (2.0 / coherent_gain)
    amplitudes[0] *= 0.5
    if checked_size % 2 == 0:
        amplitudes[-1] *= 0.5
    power = np.mean(np.square(amplitudes), axis=1, dtype=np.float64)
    frequencies = np.fft.rfftfreq(checked_size, 1.0 / checked_rate)
    mask = (frequencies >= checked_min) & (frequencies <= capped_max)
    if not np.any(mask):
        raise ValueError("frequency range contains no FFT bins")
    selected_frequencies = frequencies[mask].astype(np.float64, copy=True)
    selected_power = power[mask].astype(np.float64, copy=True)
    magnitudes_dbfs = np.asarray(_power_to_dbfs(selected_power), dtype=np.float64)

    return SpectrumFrame(
        waveform=waveform.astype(np.float32, copy=False),
        frequencies_hz=selected_frequencies,
        magnitudes_dbfs=magnitudes_dbfs,
        rms_dbfs=rms_dbfs,
        peak_dbfs=peak_dbfs,
        spectral_centroid_hz=_spectral_centroid(selected_frequencies, selected_power),
    )


class SpectrumSmoother:
    """최근 프레임의 선형 파워를 유한 창으로 평균해 표시 흔들림을 줄인다."""

    def __init__(self, history_size: int = 4) -> None:
        """유지할 프레임 수를 검증하고 비어 있는 평활화 이력을 준비한다."""

        self.history_size = _validate_integer(history_size, "history_size", 1)
        self._history: deque[SpectrumFrame] = deque(maxlen=self.history_size)

    def reset(self) -> None:
        """장치나 주파수 격자가 바뀔 때 이전 평활화 이력을 모두 지운다."""

        self._history.clear()

    @staticmethod
    def _validate_frame(frame: SpectrumFrame) -> None:
        """평활화할 프레임의 배열 크기와 모든 통계값이 유효한지 확인한다."""

        if not isinstance(frame, SpectrumFrame):
            raise ValueError("frame must be a SpectrumFrame")
        waveform = np.asarray(frame.waveform)
        frequencies = np.asarray(frame.frequencies_hz)
        magnitudes = np.asarray(frame.magnitudes_dbfs)
        if waveform.ndim != 1 or frequencies.ndim != 1 or magnitudes.ndim != 1:
            raise ValueError("SpectrumFrame arrays must be one-dimensional")
        if len(frequencies) == 0 or frequencies.shape != magnitudes.shape:
            raise ValueError("frequency and magnitude arrays must have the same non-zero shape")
        if not (
            np.all(np.isfinite(waveform))
            and np.all(np.isfinite(frequencies))
            and np.all(np.isfinite(magnitudes))
            and np.isfinite(frame.rms_dbfs)
            and np.isfinite(frame.peak_dbfs)
            and np.isfinite(frame.spectral_centroid_hz)
        ):
            raise ValueError("SpectrumFrame values must be finite")
        if np.any(np.diff(frequencies) <= 0.0):
            raise ValueError("SpectrumFrame frequencies must be strictly increasing")

    @staticmethod
    def _copy_frame(frame: SpectrumFrame) -> SpectrumFrame:
        """호출자가 나중에 배열을 바꿔도 이력이 흔들리지 않도록 프레임을 복사한다."""

        return SpectrumFrame(
            waveform=np.asarray(frame.waveform, dtype=np.float32).copy(),
            frequencies_hz=np.asarray(frame.frequencies_hz, dtype=np.float64).copy(),
            magnitudes_dbfs=np.asarray(frame.magnitudes_dbfs, dtype=np.float64).copy(),
            rms_dbfs=float(frame.rms_dbfs),
            peak_dbfs=float(frame.peak_dbfs),
            spectral_centroid_hz=float(frame.spectral_centroid_hz),
        )

    def push(self, frame: SpectrumFrame) -> SpectrumFrame:
        """새 프레임을 이력에 넣고 최신 파형과 롤링 스펙트럼을 결합해 반환한다."""

        self._validate_frame(frame)
        if self._history:
            previous = self._history[-1]
            same_grid = (
                previous.frequencies_hz.shape == frame.frequencies_hz.shape
                and np.array_equal(previous.frequencies_hz, frame.frequencies_hz)
            )
            if not same_grid:
                self.reset()
        current = self._copy_frame(frame)
        self._history.append(current)

        spectrum_power = np.mean(
            np.stack([_dbfs_to_power(item.magnitudes_dbfs) for item in self._history]),
            axis=0,
            dtype=np.float64,
        )
        rms_power = float(
            np.mean([float(_dbfs_to_power(item.rms_dbfs)) for item in self._history], dtype=np.float64)
        )
        peak_dbfs = max(item.peak_dbfs for item in self._history)
        smoothed_magnitudes = np.asarray(_power_to_dbfs(spectrum_power), dtype=np.float64)

        return SpectrumFrame(
            waveform=current.waveform.copy(),
            frequencies_hz=current.frequencies_hz.copy(),
            magnitudes_dbfs=smoothed_magnitudes,
            rms_dbfs=float(_power_to_dbfs(rms_power)),
            peak_dbfs=float(peak_dbfs),
            spectral_centroid_hz=_spectral_centroid(current.frequencies_hz, spectrum_power),
        )
