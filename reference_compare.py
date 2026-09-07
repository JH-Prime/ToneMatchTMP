"""오프라인 기준 음색과 실시간 스펙트럼을 레벨 독립적으로 비교한다."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np

from spectrum import DBFS_FLOOR, SpectrumFrame


REFERENCE_PROFILE_SCHEMA = "tonematch.reference-spectrum.v1"
REFERENCE_COMPARE_SCHEMA = "tonematch.reference-compare.v1"
FFT_SIZE = 2_048
MAX_REFERENCE_FRAMES = 384
PROFILE_BIN_COUNT = 192
MIN_FREQUENCY_HZ = 20.0
MAX_FREQUENCY_HZ = 20_000.0
DB_FLOOR = -120.0
MIN_INPUT_RMS_DBFS = -75.0
SILENCE_RMS = 10.0 ** (MIN_INPUT_RMS_DBFS / 20.0)
SPECTRAL_DYNAMIC_RANGE_DB = 80.0
RELATIVE_POWER_FLOOR = 10.0 ** (-SPECTRAL_DYNAMIC_RANGE_DB / 10.0)

BANDS: tuple[tuple[str, str, float, float], ...] = (
    ("low", "Low", 60.0, 250.0),
    ("low_mid", "Low Mid", 250.0, 500.0),
    ("mid", "Mid", 500.0, 1_500.0),
    ("presence", "Presence", 1_500.0, 4_000.0),
    ("treble", "Treble", 4_000.0, 8_000.0),
    ("air", "Air", 8_000.0, 20_000.0),
)


class ReferenceCompareError(ValueError):
    """기준 프로필 생성이나 실시간 비교 입력이 유효하지 않을 때 발생한다."""


def _checked_integer(value: object, name: str, minimum: int, maximum: int | None = None) -> int:
    """불리언을 제외한 정수 설정값과 허용 범위를 검증한다."""

    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise ReferenceCompareError(f"{name} must be an integer")
    checked = int(value)
    if checked < minimum or (maximum is not None and checked > maximum):
        suffix = f" and at most {maximum}" if maximum is not None else ""
        raise ReferenceCompareError(f"{name} must be at least {minimum}{suffix}")
    return checked


def _prepare_pcm(samples: np.ndarray) -> np.ndarray:
    """실수 mono 또는 frames-by-channels PCM을 유한한 2차원 배열로 준비한다."""

    try:
        source = np.asarray(samples)
    except (TypeError, ValueError) as exc:
        raise ReferenceCompareError("samples must contain rectangular numeric PCM values") from exc
    if source.ndim not in (1, 2) or source.size == 0 or source.shape[0] == 0:
        raise ReferenceCompareError("samples must be non-empty mono or frames-by-channels PCM")
    if source.ndim == 2 and source.shape[1] == 0:
        raise ReferenceCompareError("samples must contain at least one channel")
    if np.iscomplexobj(source) or source.dtype.kind not in "biuf":
        raise ReferenceCompareError("samples must contain real numeric PCM values")
    try:
        pcm = source.astype(np.float64, copy=True)
    except (TypeError, ValueError) as exc:
        raise ReferenceCompareError("samples must contain real numeric PCM values") from exc
    if not np.all(np.isfinite(pcm)):
        raise ReferenceCompareError("samples must contain only finite PCM values")
    if pcm.ndim == 1:
        pcm = pcm[:, None]
    np.clip(pcm, -1.0, 1.0, out=pcm)
    return pcm


def _sample_frames(pcm: np.ndarray, fft_size: int, max_frames: int) -> tuple[np.ndarray, int]:
    """곡 전체에서 최대 프레임 수만큼 균등 표본을 뽑고 활성 프레임만 반환한다."""

    frame_count = min(max_frames, max(1, int(np.ceil(len(pcm) / fft_size))))
    if len(pcm) <= fft_size:
        starts = np.zeros(1, dtype=np.int64)
    else:
        starts = np.linspace(0, len(pcm) - fft_size, frame_count, dtype=np.int64)
        starts = np.unique(starts)

    framed = np.zeros((len(starts), fft_size, pcm.shape[1]), dtype=np.float64)
    for index, start in enumerate(starts):
        available = min(fft_size, len(pcm) - int(start))
        framed[index, :available] = pcm[int(start) : int(start) + available]

    rms = np.sqrt(np.mean(np.square(framed), axis=(1, 2), dtype=np.float64))
    peak_rms = float(np.max(rms))
    if peak_rms <= SILENCE_RMS:
        raise ReferenceCompareError("reference PCM is silent or below the -75 dBFS comparison threshold")
    active = rms >= max(SILENCE_RMS, peak_rms * 0.01)
    return framed[active], int(len(starts))


def _log_grid(maximum_hz: float) -> tuple[np.ndarray, np.ndarray]:
    """20 Hz부터 유효 상한까지 고정 개수의 로그 주파수 셀을 만든다."""

    if not np.isfinite(maximum_hz) or maximum_hz <= MIN_FREQUENCY_HZ:
        raise ReferenceCompareError("sample rate does not provide a usable frequency range")
    edges = np.geomspace(MIN_FREQUENCY_HZ, maximum_hz, PROFILE_BIN_COUNT + 1, dtype=np.float64)
    centers = np.sqrt(edges[:-1] * edges[1:])
    return edges, centers


def _source_edges(frequencies_hz: np.ndarray) -> np.ndarray:
    """주파수 중심점 배열을 파워 적분용 셀 경계 배열로 변환한다."""

    if len(frequencies_hz) < 2:
        raise ReferenceCompareError("spectrum must contain at least two frequency bins")
    edges = np.empty(len(frequencies_hz) + 1, dtype=np.float64)
    edges[1:-1] = (frequencies_hz[:-1] + frequencies_hz[1:]) * 0.5
    edges[0] = max(0.0, frequencies_hz[0] - (frequencies_hz[1] - frequencies_hz[0]) * 0.5)
    edges[-1] = frequencies_hz[-1] + (frequencies_hz[-1] - frequencies_hz[-2]) * 0.5
    return edges


def _integrated_power_at(edges: np.ndarray, power: np.ndarray, points: np.ndarray) -> np.ndarray:
    """셀 안에서 일정한 파워 밀도를 가정해 임의 경계의 누적 파워를 구한다."""

    widths = np.diff(edges)
    if np.any(widths <= 0.0):
        raise ReferenceCompareError("spectrum frequencies must be strictly increasing")
    cumulative = np.concatenate((np.zeros(1, dtype=np.float64), np.cumsum(power, dtype=np.float64)))
    clipped = np.clip(points, edges[0], edges[-1])
    indexes = np.searchsorted(edges, clipped, side="right") - 1
    indexes = np.clip(indexes, 0, len(power) - 1)
    fraction = (clipped - edges[indexes]) / widths[indexes]
    result = cumulative[indexes] + power[indexes] * fraction
    result = np.where(points <= edges[0], 0.0, result)
    result = np.where(points >= edges[-1], cumulative[-1], result)
    return result


def _rebin_power(frequencies_hz: np.ndarray, power: np.ndarray, target_edges_hz: np.ndarray) -> np.ndarray:
    """서로 다른 선형 주파수 격자의 파워를 공통 로그 셀에 보존적으로 투영한다."""

    source_edges = _source_edges(frequencies_hz)
    integrated = _integrated_power_at(source_edges, power, target_edges_hz)
    rebinned = np.maximum(0.0, np.diff(integrated))
    if not np.all(np.isfinite(rebinned)):
        raise ReferenceCompareError("rebinned spectrum contains non-finite values")
    return rebinned


def _normalize_power(power: np.ndarray, label: str) -> np.ndarray:
    """주파수 파워 합을 1로 맞춰 전체 입력 게인의 영향을 제거한다."""

    values = np.asarray(power, dtype=np.float64)
    if not np.all(np.isfinite(values)) or np.any(values < 0.0):
        raise ReferenceCompareError(f"{label} spectrum contains invalid power values")
    peak = float(np.max(values, initial=0.0))
    if peak <= 1e-24:
        raise ReferenceCompareError(f"{label} spectrum is silent")
    scaled = values / peak
    total = float(np.sum(scaled, dtype=np.float64))
    normalized = scaled / total
    if not np.all(np.isfinite(normalized)):
        raise ReferenceCompareError(f"{label} spectrum contains non-finite values")
    return normalized


def _mask_relative_noise(power: np.ndarray) -> np.ndarray:
    """양쪽 FFT에 동일한 peak 대비 80 dB 범위를 적용해 수치잡음을 제외한다."""

    values = np.asarray(power, dtype=np.float64)
    peak = float(np.max(values, initial=0.0))
    if peak <= 0.0:
        return np.zeros_like(values)
    scaled = values / peak
    return np.where(scaled >= RELATIVE_POWER_FLOOR, scaled, 0.0)


def _power_to_relative_db(power: np.ndarray, floor_power: np.ndarray | float = RELATIVE_POWER_FLOOR) -> np.ndarray:
    """총 파워 대비 80 dB 또는 공통 관측 하한으로 양쪽 상대 레벨을 제한한다."""

    values = np.asarray(power, dtype=np.float64)
    floor = np.maximum(RELATIVE_POWER_FLOOR, np.asarray(floor_power, dtype=np.float64))
    return 10.0 * np.log10(np.maximum(values, floor))


def _band_power(power: np.ndarray, edges_hz: np.ndarray, low_hz: float, high_hz: float) -> float:
    """로그 셀과 대역 경계의 겹침 비율을 반영해 한 대역의 파워를 합산한다."""

    widths = np.diff(edges_hz)
    overlap = np.maximum(0.0, np.minimum(edges_hz[1:], high_hz) - np.maximum(edges_hz[:-1], low_hz))
    return float(np.sum(power * (overlap / widths), dtype=np.float64))


def _single_band_rows(power: np.ndarray, edges_hz: np.ndarray) -> list[dict[str, Any]]:
    """기준 프로필에 넣을 여섯 고정 대역의 상대 레벨 행을 만든다."""

    maximum_hz = float(edges_hz[-1])
    rows: list[dict[str, Any]] = []
    for band_id, name, low_hz, nominal_high_hz in BANDS:
        high_hz = max(low_hz, min(nominal_high_hz, maximum_hz))
        available = high_hz > low_hz
        band_value = _band_power(power, edges_hz, low_hz, high_hz) if available else 0.0
        level_db = float(_power_to_relative_db(np.asarray((band_value,), dtype=np.float64))[0])
        rows.append(
            {
                "id": band_id,
                "name": name,
                "low_hz": float(low_hz),
                "high_hz": float(high_hz),
                "available": available,
                "relative_db": level_db,
            }
        )
    return rows


def _comparison_band_rows(
    reference_power: np.ndarray,
    current_power: np.ndarray,
    edges_hz: np.ndarray,
    floor_power: np.ndarray,
) -> list[dict[str, Any]]:
    """기준·현재·차이를 포함한 여섯 고정 대역 비교 행을 만든다."""

    maximum_hz = float(edges_hz[-1])
    rows: list[dict[str, Any]] = []
    for band_id, name, low_hz, nominal_high_hz in BANDS:
        high_hz = max(low_hz, min(nominal_high_hz, maximum_hz))
        available = high_hz > low_hz
        if available:
            reference_value = _band_power(reference_power, edges_hz, low_hz, high_hz)
            current_value = _band_power(current_power, edges_hz, low_hz, high_hz)
            band_floor = _band_power(floor_power, edges_hz, low_hz, high_hz)
        else:
            reference_value = current_value = 0.0
            band_floor = RELATIVE_POWER_FLOOR
        levels = _power_to_relative_db(
            np.asarray((reference_value, current_value), dtype=np.float64), band_floor
        )
        reference_db = float(levels[0])
        current_db = float(levels[1])
        rows.append(
            {
                "id": band_id,
                "name": name,
                "low_hz": float(low_hz),
                "high_hz": float(high_hz),
                "available": available,
                "reference_db": reference_db,
                "current_db": current_db,
                "delta_db": float(current_db - reference_db),
            }
        )
    return rows


def build_reference_profile(
    samples: np.ndarray,
    sample_rate: int,
    *,
    fft_size: int = FFT_SIZE,
    max_frames: int = MAX_REFERENCE_FRAMES,
) -> dict[str, Any]:
    """오프라인 PCM의 활성 구간에서 레벨 정규화 기준 음색 프로필을 만든다."""

    checked_rate = _checked_integer(sample_rate, "sample_rate", 8_000)
    checked_fft_size = _checked_integer(fft_size, "fft_size", 128)
    checked_max_frames = _checked_integer(max_frames, "max_frames", 1, MAX_REFERENCE_FRAMES)
    pcm = _prepare_pcm(samples)
    frames, sampled_frames = _sample_frames(pcm, checked_fft_size, checked_max_frames)

    centered = frames - np.mean(frames, axis=1, keepdims=True, dtype=np.float64)
    window = np.hanning(checked_fft_size).astype(np.float64)
    transformed = np.fft.rfft(centered * window[None, :, None], axis=1)
    power = np.mean(np.square(np.abs(transformed)), axis=(0, 2), dtype=np.float64)
    # SpectrumFrame과 동일한 단측 진폭 규칙을 사용한다. 공통 배율은 정규화로
    # 사라지지만 DC/Nyquist의 절반 진폭 보정은 유지해야 한다.
    power[0] *= 0.25
    if checked_fft_size % 2 == 0:
        power[-1] *= 0.25
    if not np.all(np.isfinite(power)):
        raise ReferenceCompareError("reference spectrum contains non-finite values")

    frequencies_hz = np.fft.rfftfreq(checked_fft_size, 1.0 / checked_rate).astype(np.float64)
    maximum_hz = min(MAX_FREQUENCY_HZ, checked_rate / 2.0)
    selected = (frequencies_hz >= MIN_FREQUENCY_HZ) & (frequencies_hz <= maximum_hz)
    frequencies_hz = frequencies_hz[selected]
    power = _mask_relative_noise(power[selected])
    target_edges_hz, target_centers_hz = _log_grid(maximum_hz)
    normalized_power = _normalize_power(
        _rebin_power(frequencies_hz, power, target_edges_hz),
        "reference",
    )
    relative_db = _power_to_relative_db(normalized_power)

    return {
        "schema": REFERENCE_PROFILE_SCHEMA,
        "sample_rate_hz": checked_rate,
        "fft_size": checked_fft_size,
        "sampled_frames": sampled_frames,
        "active_frames": int(len(frames)),
        "minimum_rms_dbfs": MIN_INPUT_RMS_DBFS,
        "spectral_dynamic_range_db": SPECTRAL_DYNAMIC_RANGE_DB,
        "frequencies_hz": target_centers_hz.tolist(),
        "frequency_edges_hz": target_edges_hz.tolist(),
        "normalized_power": normalized_power.tolist(),
        "relative_db": relative_db.tolist(),
        "bands": _single_band_rows(normalized_power, target_edges_hz),
    }


def _profile_arrays(reference_profile: Mapping[str, Any]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """직렬화된 기준 프로필의 schema와 로그 격자·파워 배열을 엄격히 검증한다."""

    if not isinstance(reference_profile, Mapping):
        raise ReferenceCompareError("reference_profile must be a mapping")
    if reference_profile.get("schema") != REFERENCE_PROFILE_SCHEMA:
        raise ReferenceCompareError("reference_profile has an unsupported schema")
    try:
        frequencies = np.asarray(reference_profile["frequencies_hz"], dtype=np.float64)
        edges = np.asarray(reference_profile["frequency_edges_hz"], dtype=np.float64)
        power = np.asarray(reference_profile["normalized_power"], dtype=np.float64)
    except (KeyError, TypeError, ValueError) as exc:
        raise ReferenceCompareError("reference_profile arrays are invalid") from exc
    if frequencies.ndim != 1 or edges.ndim != 1 or power.ndim != 1:
        raise ReferenceCompareError("reference_profile arrays must be one-dimensional")
    if len(frequencies) != PROFILE_BIN_COUNT or len(power) != len(frequencies) or len(edges) != len(power) + 1:
        raise ReferenceCompareError("reference_profile arrays have an invalid shape")
    if not (np.all(np.isfinite(frequencies)) and np.all(np.isfinite(edges)) and np.all(np.isfinite(power))):
        raise ReferenceCompareError("reference_profile arrays must contain only finite values")
    if np.any(np.diff(frequencies) <= 0.0) or np.any(np.diff(edges) <= 0.0) or np.any(power < 0.0):
        raise ReferenceCompareError("reference_profile frequency grid or power is invalid")
    if not np.all((frequencies > edges[:-1]) & (frequencies < edges[1:])):
        raise ReferenceCompareError("reference_profile centers must lie inside their cells")
    return frequencies, edges, _normalize_power(power, "reference")


def _frame_arrays(frame: SpectrumFrame) -> tuple[np.ndarray, np.ndarray]:
    """공개 SpectrumFrame에서 유효한 주파수와 선형 파워 배열을 읽는다."""

    if not isinstance(frame, SpectrumFrame):
        raise ReferenceCompareError("frame must be a SpectrumFrame")
    try:
        waveform = np.asarray(frame.waveform, dtype=np.float64)
        frequencies = np.asarray(frame.frequencies_hz)
        magnitudes = np.asarray(frame.magnitudes_dbfs)
        rms_dbfs = float(frame.rms_dbfs)
        peak_dbfs = float(frame.peak_dbfs)
        centroid_hz = float(frame.spectral_centroid_hz)
    except (TypeError, ValueError) as exc:
        raise ReferenceCompareError("SpectrumFrame values must be numeric") from exc
    if waveform.ndim != 1 or not np.all(np.isfinite(waveform)):
        raise ReferenceCompareError("SpectrumFrame waveform must be a finite one-dimensional array")
    if frequencies.ndim != 1 or magnitudes.ndim != 1 or len(frequencies) < 2 or frequencies.shape != magnitudes.shape:
        raise ReferenceCompareError("SpectrumFrame frequency and magnitude arrays are invalid")
    try:
        frequencies = frequencies.astype(np.float64, copy=False)
        magnitudes = magnitudes.astype(np.float64, copy=False)
    except (TypeError, ValueError) as exc:
        raise ReferenceCompareError("SpectrumFrame arrays must be numeric") from exc
    scalar_values = (rms_dbfs, peak_dbfs, centroid_hz)
    if not np.all(np.isfinite(frequencies)) or not np.all(np.isfinite(magnitudes)) or not np.all(np.isfinite(scalar_values)):
        raise ReferenceCompareError("SpectrumFrame values must be finite")
    if np.any(np.diff(frequencies) <= 0.0) or np.any(frequencies <= 0.0):
        raise ReferenceCompareError("SpectrumFrame frequencies must be positive and strictly increasing")
    if rms_dbfs <= MIN_INPUT_RMS_DBFS:
        raise ReferenceCompareError("current spectrum is silent or below the -75 dBFS comparison threshold")
    peak_spectrum_db = float(np.max(magnitudes))
    if peak_spectrum_db <= DBFS_FLOOR:
        raise ReferenceCompareError("current spectrum is silent")
    relative_db = magnitudes - peak_spectrum_db
    power = np.where(
        magnitudes > DBFS_FLOOR,
        np.power(10.0, np.clip(relative_db, -SPECTRAL_DYNAMIC_RANGE_DB, 0.0) / 10.0),
        0.0,
    )
    power[relative_db < -SPECTRAL_DYNAMIC_RANGE_DB] = 0.0
    return frequencies, _mask_relative_noise(power)


def compare_live_frame(reference_profile: Mapping[str, Any], frame: SpectrumFrame) -> dict[str, Any]:
    """실시간 프레임을 기준 로그 격자에 투영해 주파수별·대역별 상대 차이를 반환한다."""

    frequencies, edges, reference_power = _profile_arrays(reference_profile)
    live_frequencies, live_power = _frame_arrays(frame)
    current_power = _rebin_power(live_frequencies, live_power, edges)

    live_edges = _source_edges(live_frequencies)
    common_low = max(float(edges[0]), float(live_edges[0]))
    common_high = min(float(edges[-1]), float(live_edges[-1]))
    common_mask = (edges[:-1] >= common_low) & (edges[1:] <= common_high)
    if int(np.count_nonzero(common_mask)) < 2:
        raise ReferenceCompareError("reference and current spectra do not share a usable frequency range")

    first = int(np.flatnonzero(common_mask)[0])
    last = int(np.flatnonzero(common_mask)[-1]) + 1
    common_edges = edges[first : last + 1].copy()
    common_frequencies = frequencies[first:last].copy()
    common_reference = _normalize_power(reference_power[first:last], "reference")
    common_current = _normalize_power(current_power[first:last], "current")
    # 실시간 dBFS 표시 하한(-120)에 묻힌 정보는 복원할 수 없다. 그 최대
    # 미관측 파워를 같은 로그 셀에 투영해 양쪽에 동일한 비교 하한을 적용한다.
    # 약한 입력에서 절대 표시 하한을 음색 차이로 오인하는 일을 방지한다.
    live_floor = 10.0 ** ((DBFS_FLOOR - float(np.max(frame.magnitudes_dbfs))) / 10.0)
    projected_floor = _rebin_power(live_frequencies, np.full_like(live_power, live_floor), common_edges)
    observable_floor = projected_floor / float(np.sum(current_power[first:last], dtype=np.float64))
    reference_db = _power_to_relative_db(common_reference, observable_floor)
    current_db = _power_to_relative_db(common_current, observable_floor)
    delta_db = current_db - reference_db

    return {
        "schema": REFERENCE_COMPARE_SCHEMA,
        "frequencies_hz": common_frequencies.tolist(),
        "reference_relative_db": reference_db.tolist(),
        "current_relative_db": current_db.tolist(),
        "delta_db": delta_db.tolist(),
        "bands": _comparison_band_rows(common_reference, common_current, common_edges, observable_floor),
    }
