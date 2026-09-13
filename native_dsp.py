"""검증된 C ABI 실시간 DSP와 동일한 NumPy 스트리밍 대체 경로를 제공한다."""

from __future__ import annotations

import ctypes
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from spectrum import SpectrumFrame, SpectrumSmoother, analyze_spectrum_frame


NATIVE_ABI_VERSION = 1
NATIVE_LIBRARY_NAME = "tonematch_dsp.dll"
MAX_FRAMES_PER_PUSH = 10_000_000
_DOUBLE_POINTER = ctypes.POINTER(ctypes.c_double)


class NativeDspError(RuntimeError):
    """네이티브 DSP의 선택·초기화·실행 실패를 안전한 메시지로 전달한다."""


@dataclass(frozen=True)
class _Configuration:
    """두 DSP 백엔드가 공유하는 불변 스트리밍 설정을 보관한다."""

    sample_rate: int
    channels: int
    fft_size: int
    history_size: int
    min_hz: float
    max_hz: float


def _integer(value: object, name: str, minimum: int) -> int:
    """불리언이 아닌 정수 설정과 공통 최소 범위를 검증한다."""

    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise ValueError(f"{name} must be an integer")
    checked = int(value)
    if checked < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return checked


def _frequency(value: object, name: str) -> float:
    """주파수 설정을 유한한 실수로 변환하고 불리언을 거부한다."""

    if isinstance(value, (bool, np.bool_)):
        raise ValueError(f"{name} must be a finite number")
    try:
        checked = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not np.isfinite(checked):
        raise ValueError(f"{name} must be a finite number")
    return checked


def _configuration(
    sample_rate: int, channels: int, fft_size: int, history_size: int, min_hz: float, max_hz: float
) -> _Configuration:
    """공통 설정을 검증하고 실제 선택 가능한 FFT bin이 있는지 확인한다."""

    rate = _integer(sample_rate, "sample_rate", 8_000)
    channel_count = _integer(channels, "channels", 1)
    size = _integer(fft_size, "fft_size", 3)
    history = _integer(history_size, "history_size", 1)
    minimum = _frequency(min_hz, "min_hz")
    maximum = _frequency(max_hz, "max_hz")
    if minimum <= 0.0 or maximum <= minimum:
        raise ValueError("frequency range must be positive and increasing")
    frequencies = np.fft.rfftfreq(size, 1.0 / rate)
    if not np.any((frequencies >= minimum) & (frequencies <= min(maximum, rate / 2.0))):
        raise ValueError("frequency range contains no FFT bins")
    return _Configuration(rate, channel_count, size, history, minimum, maximum)


def _prepare_block(samples: np.ndarray, channels: int) -> np.ndarray:
    """호출자 PCM을 검증하고 C ABI용 연속 float64 채널 배열로 준비한다."""

    try:
        source = np.asarray(samples)
    except (TypeError, ValueError) as exc:
        raise ValueError("samples must contain rectangular numeric PCM values") from exc
    if source.ndim not in (1, 2) or source.size == 0 or source.shape[0] == 0:
        raise ValueError("samples must be non-empty mono or frames-by-channels PCM")
    if source.ndim == 1:
        if channels != 1:
            raise ValueError("samples channel count does not match the stream")
        source = source[:, None]
    if source.shape[1] != channels:
        raise ValueError("samples channel count does not match the stream")
    if np.iscomplexobj(source) or source.dtype.kind not in "biuf":
        raise ValueError("samples must contain real numeric PCM values")
    if source.shape[0] > MAX_FRAMES_PER_PUSH:
        raise ValueError(f"a PCM block must contain at most {MAX_FRAMES_PER_PUSH} frames")
    return np.ascontiguousarray(source, dtype=np.float64)


def _library_candidates() -> tuple[Path, ...]:
    """현재 모듈 및 동결 번들의 절대 리소스 경로만 DLL 후보로 반환한다."""

    roots = [Path(__file__).resolve().parent]
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root is not None:
        candidate = Path(frozen_root)
        if candidate.is_absolute():
            roots.append(candidate.resolve())
    return tuple(dict.fromkeys(root / "resources" / NATIVE_LIBRARY_NAME for root in roots))


def _load_library() -> Any:
    """신뢰할 수 있는 절대 경로에서 DLL을 열고 ABI와 모든 함수 서명을 확인한다."""

    library_path = next((path for path in _library_candidates() if path.is_file()), None)
    if library_path is None:
        raise NativeDspError("Native DSP DLL is not installed; using the NumPy backend is supported.")
    try:
        library = ctypes.CDLL(str(library_path))
    except OSError as exc:
        raise NativeDspError("Native DSP DLL could not be loaded (incompatible architecture or runtime).") from exc
    try:
        library.tm_dsp_abi_version.argtypes = []
        library.tm_dsp_abi_version.restype = ctypes.c_uint32
        actual_abi = int(library.tm_dsp_abi_version())
        if actual_abi != NATIVE_ABI_VERSION:
            raise NativeDspError(f"Native DSP ABI mismatch: expected {NATIVE_ABI_VERSION}, received {actual_abi}.")
        library.tm_dsp_create.argtypes = [
            ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32,
            ctypes.c_double, ctypes.c_double,
        ]
        library.tm_dsp_create.restype = ctypes.c_void_p
        library.tm_dsp_destroy.argtypes = [ctypes.c_void_p]
        library.tm_dsp_destroy.restype = None
        library.tm_dsp_reset.argtypes = [ctypes.c_void_p]
        library.tm_dsp_reset.restype = ctypes.c_int32
        library.tm_dsp_bin_count.argtypes = [ctypes.c_void_p]
        library.tm_dsp_bin_count.restype = ctypes.c_uint32
        library.tm_dsp_frequencies.argtypes = [ctypes.c_void_p, _DOUBLE_POINTER, ctypes.c_uint32]
        library.tm_dsp_frequencies.restype = ctypes.c_int32
        library.tm_dsp_push.argtypes = [
            ctypes.c_void_p, _DOUBLE_POINTER, ctypes.c_uint32,
            _DOUBLE_POINTER, ctypes.c_uint32, _DOUBLE_POINTER, ctypes.c_uint32,
            _DOUBLE_POINTER, ctypes.c_uint32,
        ]
        library.tm_dsp_push.restype = ctypes.c_int32
    except AttributeError as exc:
        raise NativeDspError("Native DSP DLL is missing required ABI functions.") from exc
    return library


def _double_pointer(values: np.ndarray) -> Any:
    """연속 float64 배열을 C ABI에서 읽고 쓸 수 있는 double 포인터로 바꾼다."""

    return values.ctypes.data_as(_DOUBLE_POINTER)


class PythonSpectrumEngine:
    """임의 길이 PCM 블록을 고정 FFT 구간으로 모으는 NumPy 대체 엔진이다."""

    backend = "numpy"

    def __init__(
        self, sample_rate: int, channels: int, *, fft_size: int = 2_048,
        history_size: int = 4, min_hz: float = 20.0, max_hz: float = 20_000.0,
        fallback_reason: str | None = None,
    ) -> None:
        """설정과 bounded 부분 블록 및 평활화 이력을 준비한다."""

        self._config = _configuration(sample_rate, channels, fft_size, history_size, min_hz, max_hz)
        self.fallback_reason = fallback_reason
        self._lock = threading.RLock()
        self._closed = False
        self._pending = np.empty((0, channels), dtype=np.float64)
        self._smoother = SpectrumSmoother(history_size)

    def _require_open(self) -> None:
        """닫힌 스트림을 다시 사용하는 호출을 명확한 오류로 거부한다."""

        if self._closed:
            raise NativeDspError("Spectrum engine is closed.")

    def push(self, samples: np.ndarray) -> SpectrumFrame | None:
        """완전한 FFT 구간을 모두 처리하고 최신 결과 또는 대기 상태를 반환한다."""

        with self._lock:
            self._require_open()
            block = _prepare_block(samples, self._config.channels)
            combined = np.concatenate((self._pending, block), axis=0) if len(self._pending) else block
            complete = len(combined) // self._config.fft_size
            result = None
            for index in range(complete):
                start = index * self._config.fft_size
                frame = analyze_spectrum_frame(
                    combined[start : start + self._config.fft_size], self._config.sample_rate,
                    fft_size=self._config.fft_size, min_hz=self._config.min_hz, max_hz=self._config.max_hz,
                )
                result = self._smoother.push(frame)
            self._pending = combined[complete * self._config.fft_size :].copy()
            return result

    def reset(self) -> None:
        """부분 PCM과 모든 평활화 이력을 함께 비운다."""

        with self._lock:
            self._require_open()
            self._pending = np.empty((0, self._config.channels), dtype=np.float64)
            self._smoother.reset()

    def close(self) -> None:
        """여러 번 호출해도 안전하게 버퍼를 비우고 엔진을 닫는다."""

        with self._lock:
            if not self._closed:
                self._pending = np.empty((0, self._config.channels), dtype=np.float64)
                self._smoother.reset()
                self._closed = True


class NativeSpectrumEngine:
    """명시적 C ABI와 잠금으로 C++ 스트리밍 FFT 컨텍스트 수명을 관리한다."""

    backend = "cpp"
    fallback_reason = None

    def __init__(
        self, sample_rate: int, channels: int, *, fft_size: int = 2_048,
        history_size: int = 4, min_hz: float = 20.0, max_hz: float = 20_000.0,
    ) -> None:
        """C++ 지원 범위와 ABI를 검증한 뒤 컨텍스트 및 출력 버퍼를 만든다."""

        self._context = None
        self._lock = threading.RLock()
        self._config = _configuration(sample_rate, channels, fft_size, history_size, min_hz, max_hz)
        config = self._config
        if not (config.sample_rate <= 192_000 and config.channels <= 32 and config.history_size <= 64):
            raise NativeDspError("Native DSP supports sample rates up to 192000 Hz, 1–32 channels and 1–64 history frames.")
        if not (128 <= config.fft_size <= 32_768 and config.fft_size & (config.fft_size - 1) == 0):
            raise NativeDspError("Native DSP FFT size must be a power of two from 128 to 32768.")
        self._library = _load_library()
        handle = self._library.tm_dsp_create(
            config.sample_rate, config.channels, config.fft_size, config.history_size,
            config.min_hz, config.max_hz,
        )
        if not handle:
            raise NativeDspError("Native DSP could not create the requested spectrum context.")
        self._context = ctypes.c_void_p(handle)
        try:
            count = int(self._library.tm_dsp_bin_count(self._context))
            if not 1 <= count <= config.fft_size // 2 + 1:
                raise NativeDspError("Native DSP returned an invalid frequency-bin count.")
            self._frequencies = np.empty(count, dtype=np.float64)
            if self._library.tm_dsp_frequencies(self._context, _double_pointer(self._frequencies), count) != count:
                raise NativeDspError("Native DSP could not read its frequency grid.")
            expected = np.fft.rfftfreq(config.fft_size, 1.0 / config.sample_rate)
            expected = expected[(expected >= config.min_hz) & (expected <= min(config.max_hz, config.sample_rate / 2.0))]
            if expected.shape != self._frequencies.shape or not np.allclose(expected, self._frequencies, rtol=1e-12, atol=1e-10):
                raise NativeDspError("Native DSP frequency grid does not match the requested configuration.")
            self._waveform = np.empty(config.fft_size, dtype=np.float64)
            self._magnitudes = np.empty(count, dtype=np.float64)
            self._statistics = np.empty(3, dtype=np.float64)
        except Exception:
            self.close()
            raise

    def _require_open(self) -> None:
        """해제된 C++ 컨텍스트로 진입하는 호출을 거부한다."""

        if self._context is None:
            raise NativeDspError("Spectrum engine is closed.")

    def push(self, samples: np.ndarray) -> SpectrumFrame | None:
        """PCM을 C++에 전달하고 독립 배열을 가진 최신 완성 프레임을 반환한다."""

        with self._lock:
            self._require_open()
            block = _prepare_block(samples, self._config.channels)
            emitted = int(self._library.tm_dsp_push(
                self._context, _double_pointer(block), len(block),
                _double_pointer(self._waveform), len(self._waveform),
                _double_pointer(self._magnitudes), len(self._magnitudes),
                _double_pointer(self._statistics), len(self._statistics),
            ))
            if emitted < 0:
                raise NativeDspError(f"Native DSP processing failed (status {emitted}).")
            if emitted == 0:
                return None
            if not all(np.all(np.isfinite(values)) for values in (self._waveform, self._magnitudes, self._statistics)):
                raise NativeDspError("Native DSP returned non-finite output.")
            return SpectrumFrame(
                waveform=self._waveform.astype(np.float32, copy=True),
                frequencies_hz=self._frequencies.copy(),
                magnitudes_dbfs=self._magnitudes.copy(),
                rms_dbfs=float(self._statistics[0]), peak_dbfs=float(self._statistics[1]),
                spectral_centroid_hz=float(self._statistics[2]),
            )

    def reset(self) -> None:
        """C++의 부분 PCM과 평활화 이력을 하나의 잠금 안에서 초기화한다."""

        with self._lock:
            self._require_open()
            if self._library.tm_dsp_reset(self._context) < 0:
                raise NativeDspError("Native DSP reset failed.")

    def close(self) -> None:
        """진행 중인 push와 경합하지 않도록 C++ 컨텍스트를 한 번만 해제한다."""

        with self._lock:
            if self._context is not None:
                context, self._context = self._context, None
                self._library.tm_dsp_destroy(context)

    def __del__(self) -> None:
        """초기화 실패나 사용자 미해제 경우에도 가능한 컨텍스트를 정리한다."""

        try:
            self.close()
        except Exception:
            pass


def create_spectrum_engine(
    sample_rate: int, channels: int, *, backend: str = "auto", fft_size: int = 2_048,
    history_size: int = 4, min_hz: float = 20.0, max_hz: float = 20_000.0,
) -> NativeSpectrumEngine | PythonSpectrumEngine:
    """요청한 DSP를 선택하고 자동 모드의 초기화 실패에만 NumPy로 대체한다."""

    if backend not in ("auto", "cpp", "numpy"):
        raise ValueError("backend must be 'auto', 'cpp' or 'numpy'")
    _configuration(sample_rate, channels, fft_size, history_size, min_hz, max_hz)
    options = dict(fft_size=fft_size, history_size=history_size, min_hz=min_hz, max_hz=max_hz)
    if backend == "numpy":
        return PythonSpectrumEngine(sample_rate, channels, **options)
    try:
        return NativeSpectrumEngine(sample_rate, channels, **options)
    except NativeDspError as exc:
        if backend == "cpp":
            raise
        return PythonSpectrumEngine(sample_rate, channels, fallback_reason=str(exc), **options)


def native_runtime_info() -> dict[str, Any]:
    """개인 경로 없이 네이티브 DLL 사용 가능 여부와 ABI 정보를 보고한다."""

    try:
        _load_library()
    except NativeDspError as exc:
        return {"available": False, "backend": "numpy", "abi_version": None, "library": NATIVE_LIBRARY_NAME, "error": str(exc)}
    return {"available": True, "backend": "cpp", "abi_version": NATIVE_ABI_VERSION, "library": NATIVE_LIBRARY_NAME, "error": None}
