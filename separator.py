"""Demucs 6-stem 모델로 밴드 믹스에서 일렉기타만 분리한다.

분리 모델 가중치는 프로그램 ZIP에 포함하지 않는다. 사용자가 AI 기타 분리를
처음 실행할 때 Demucs의 공식 저장소에서 내려받아 사용자 캐시에 보관한다.
"""

from __future__ import annotations

import math
import os
import time
import wave
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np

from i18n import tr


SEPARATOR_MODEL = "htdemucs_6s"
SEPARATOR_SAMPLE_RATE = 44_100
SEPARATION_CHUNK_SECONDS = 30.0


class SeparationError(RuntimeError):
    """AI 기타 분리 단계에서 사용자에게 보여 줄 수 있는 오류를 나타낸다."""


class SeparationCancelled(SeparationError):
    """사용자가 실행 중인 기타 분리를 취소했음을 나타낸다."""


@dataclass(frozen=True)
class SeparationInfo:
    """결과 파일과 함께 저장할 기타 분리 진단 정보를 정의한다."""

    model: str
    backend: str
    sample_rate: int
    source_duration_seconds: float
    processed_chunks: int
    guitar_rms_dbfs: float
    guitar_peak_dbfs: float
    model_downloaded_during_run: bool
    requested_device: str
    resolved_device: str
    inference_total_seconds: float
    inference_seconds_per_chunk: float
    realtime_factor: float
    peak_gpu_memory_bytes: int | None


def _hf_model_cache_root() -> Path:
    """Hugging Face가 사용하는 기본 Demucs 모델 캐시 경로를 계산한다."""
    explicit = os.environ.get("HF_HOME", "").strip()
    if explicit:
        return Path(explicit) / "hub" / "models--adefossez--HTDemucs-6s"
    return Path.home() / ".cache" / "huggingface" / "hub" / "models--adefossez--HTDemucs-6s"


def separator_model_is_cached() -> bool:
    """공식 6-stem 모델 가중치가 사용자 캐시에 있는지 가볍게 확인한다."""
    root = _hf_model_cache_root()
    return root.is_dir() and any(root.rglob("*.safetensors"))


def _normalize_compute_preference(compute_preference: str) -> str:
    """사용자가 선택한 연산 장치 값을 검사하고 소문자 표준값으로 바꾼다."""
    preference = str(compute_preference or "auto").strip().lower()
    if preference not in {"auto", "cpu", "cuda"}:
        raise SeparationError(
            "지원하지 않는 연산 장치 설정입니다. auto, cpu, cuda 중에서 선택하세요. "
            "/ Unsupported compute preference; choose auto, cpu, or cuda."
        )
    return preference


def _torch_cuda_is_available(torch_module: Any) -> bool:
    """PyTorch가 현재 시스템에서 CUDA 추론을 실제로 사용할 수 있는지 안전하게 확인한다."""
    try:
        return bool(torch_module.cuda.is_available())
    except Exception:
        return False


def resolve_compute_device(compute_preference: str = "auto", torch_module: Any | None = None) -> str:
    """auto·cpu·cuda 설정을 실제 Demucs 실행 장치인 cpu 또는 cuda로 결정한다."""
    preference = _normalize_compute_preference(compute_preference)
    if preference == "cpu":
        return "cpu"
    if torch_module is None:
        try:
            import torch as torch_module
        except Exception as exc:
            if preference == "auto":
                return "cpu"
            raise SeparationError(
                "CUDA가 요청되었지만 PyTorch를 불러올 수 없습니다. "
                f"/ CUDA was requested, but PyTorch could not be loaded: {exc}"
            ) from exc
    if _torch_cuda_is_available(torch_module):
        return "cuda"
    if preference == "cuda":
        cuda_build = getattr(getattr(torch_module, "version", None), "cuda", None)
        build_detail = cuda_build or "CPU-only"
        raise SeparationError(
            "CUDA가 요청되었지만 호환되는 NVIDIA GPU·드라이버 또는 CUDA PyTorch 빌드를 "
            f"사용할 수 없습니다 (PyTorch CUDA build: {build_detail}). "
            "/ CUDA was requested, but no compatible NVIDIA GPU, driver, or CUDA-enabled "
            "PyTorch build is available."
        )
    return "cpu"


def _cuda_runtime_details(torch_module: Any) -> dict[str, object]:
    """개발자 진단에 필요한 CUDA 빌드와 첫 번째 GPU의 메모리·연산 정보를 수집한다."""
    available = _torch_cuda_is_available(torch_module)
    details: dict[str, object] = {
        "cuda_available": available,
        "cuda_build": getattr(getattr(torch_module, "version", None), "cuda", None),
        "cuda_device_count": 0,
        "gpu_name": None,
        "gpu_vram_total_bytes": None,
        "gpu_vram_free_bytes": None,
        "compute_capability": None,
    }
    try:
        details["cuda_device_count"] = int(torch_module.cuda.device_count())
    except Exception:
        pass
    if not available:
        return details
    try:
        properties = torch_module.cuda.get_device_properties(0)
        gpu_name = getattr(properties, "name", None)
        if gpu_name is None:
            gpu_name = torch_module.cuda.get_device_name(0)
        details["gpu_name"] = str(gpu_name)
        details["gpu_vram_total_bytes"] = int(getattr(properties, "total_memory"))
        major = int(getattr(properties, "major"))
        minor = int(getattr(properties, "minor"))
        details["compute_capability"] = f"{major}.{minor}"
    except Exception as exc:
        details["gpu_detail_error"] = str(exc)
    try:
        free_bytes, total_bytes = torch_module.cuda.mem_get_info(0)
        details["gpu_vram_free_bytes"] = int(free_bytes)
        if details["gpu_vram_total_bytes"] is None:
            details["gpu_vram_total_bytes"] = int(total_bytes)
    except Exception:
        pass
    return details


def separator_runtime_status(compute_preference: str = "auto") -> dict[str, object]:
    """개발자 진단에 표시할 Demucs·PyTorch·CUDA 런타임 상태를 반환한다."""
    requested_device = _normalize_compute_preference(compute_preference)
    status: dict[str, object] = {
        "available": False,
        "model": SEPARATOR_MODEL,
        "model_cached": separator_model_is_cached(),
        "cache_path": str(_hf_model_cache_root()),
        "requested_device": requested_device,
        "resolved_device": "unavailable",
        "device": "unavailable",
        "cuda_available": False,
        "cuda_build": None,
        "cuda_device_count": 0,
        "gpu_name": None,
        "gpu_vram_total_bytes": None,
        "gpu_vram_free_bytes": None,
        "compute_capability": None,
    }
    try:
        import torch

        status.update(_cuda_runtime_details(torch))
        try:
            resolved_device = resolve_compute_device(requested_device, torch)
        except SeparationError as exc:
            status["device_resolution_error"] = str(exc)
        else:
            status["resolved_device"] = resolved_device
            status["device"] = resolved_device
        status["torch_version"] = getattr(torch, "__version__", "unknown")
    except Exception as exc:
        status["error"] = str(exc)
        return status
    try:
        import demucs

        status["available"] = True
        status["demucs_version"] = getattr(demucs, "__version__", "unknown")
    except Exception as exc:
        status["error"] = str(exc)
    return status


def _safe_cuda_synchronize(torch_module: Any, resolved_device: str) -> None:
    """CUDA 비동기 작업의 정확한 시간 측정을 위해 동기화하되 진단 실패는 무시한다."""
    if resolved_device != "cuda":
        return
    try:
        torch_module.cuda.synchronize()
    except Exception:
        pass


def _safe_cuda_reset_peak_memory(torch_module: Any, resolved_device: str) -> None:
    """이번 추론에 사용된 GPU 최대 메모리를 측정할 수 있도록 누적 통계를 초기화한다."""
    if resolved_device != "cuda":
        return
    try:
        torch_module.cuda.reset_peak_memory_stats()
    except Exception:
        pass


def _safe_cuda_peak_memory(torch_module: Any, resolved_device: str) -> int | None:
    """CUDA 추론 중 최대 할당 메모리를 바이트 단위로 반환하고 조회 실패 시 None을 돌려준다."""
    if resolved_device != "cuda":
        return None
    try:
        return int(torch_module.cuda.max_memory_allocated())
    except Exception:
        return None


def _safe_cuda_empty_cache(torch_module: Any, resolved_device: str) -> None:
    """CUDA 실행 뒤 재사용 가능한 캐시를 안전하게 비워 다른 작업의 GPU 메모리를 확보한다."""
    if resolved_device != "cuda":
        return
    try:
        torch_module.cuda.empty_cache()
    except Exception:
        pass


def _pcm16_chunk(raw: bytes, channels: int) -> np.ndarray:
    """16-bit PCM 바이트를 Demucs가 받는 채널 우선 float32 배열로 바꾼다."""
    values = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    if not len(values):
        return np.empty((2, 0), dtype=np.float32)
    values = values.reshape(-1, channels)
    if channels == 1:
        values = np.repeat(values, 2, axis=1)
    elif channels > 2:
        values = values[:, :2]
    return np.ascontiguousarray(values.T)


def _tensor_to_pcm16(waveform: object) -> tuple[bytes, float, float, int]:
    """분리된 PyTorch 텐서를 클리핑한 PCM과 레벨 통계로 변환한다."""
    # torch는 큰 선택 의존성이므로 모듈을 불러올 때가 아니라 실제 분리 시점에만 쓴다.
    array = waveform.detach().to("cpu").numpy().T.astype(np.float32, copy=False)
    if array.ndim == 1:
        array = np.column_stack((array, array))
    peak = float(np.max(np.abs(array))) if array.size else 0.0
    square_sum = float(np.sum(np.square(array, dtype=np.float64)))
    sample_count = int(array.size)
    pcm = np.round(np.clip(array, -0.999, 0.999) * 32767.0).astype("<i2")
    return pcm.tobytes(), square_sum, peak, sample_count


def separate_guitar_wav(
    source_wav: str | Path,
    destination_wav: str | Path,
    progress: Callable[[int, str], None] | None = None,
    cancel_requested: Callable[[], bool] | None = None,
    language: str = "ko",
    compute_preference: str = "auto",
) -> SeparationInfo:
    """선택한 CPU·CUDA 장치로 44.1 kHz PCM에서 guitar stem WAV만 분리해 기록한다."""
    source_path = Path(source_wav)
    destination_path = Path(destination_wav)
    if not source_path.is_file():
        raise SeparationError(tr("error.file_missing", language))
    requested_device = _normalize_compute_preference(compute_preference)
    was_cached = separator_model_is_cached()
    if progress:
        progress(18, tr("progress.separator_model", language))
    try:
        import torch
        from demucs.api import Separator
    except Exception as exc:
        raise SeparationError(tr("error.separator_runtime", language, detail=exc)) from exc

    resolved_device = resolve_compute_device(requested_device, torch)
    # CPU 추론 때 시스템을 모두 점유하지 않도록 한 코어를 남기고 상한을 둔다.
    if resolved_device == "cpu":
        processor_count = os.cpu_count() or 2
        torch.set_num_threads(max(1, min(8, processor_count - 1)))
    try:
        separator = Separator(
            model=SEPARATOR_MODEL,
            device=resolved_device,
            shifts=0,
            split=True,
            overlap=0.15,
            jobs=0,
            progress=False,
        )
    except Exception as exc:
        _safe_cuda_empty_cache(torch, resolved_device)
        raise SeparationError(tr("error.separator_model", language, detail=exc)) from exc

    try:
        if "guitar" not in separator.model.sources:
            raise SeparationError(tr("error.separator_no_guitar", language))
        try:
            source_handle = wave.open(str(source_path), "rb")
        except (OSError, wave.Error) as exc:
            raise SeparationError(tr("error.audio_read", language)) from exc

        with source_handle:
            channels = source_handle.getnchannels()
            sample_width = source_handle.getsampwidth()
            sample_rate = source_handle.getframerate()
            total_frames = source_handle.getnframes()
            if sample_width != 2 or sample_rate != SEPARATOR_SAMPLE_RATE:
                raise SeparationError(tr("error.separator_format", language))
            if channels < 1:
                raise SeparationError(tr("error.no_channels", language))

            destination_path.parent.mkdir(parents=True, exist_ok=True)
            frames_per_chunk = int(round(SEPARATION_CHUNK_SECONDS * sample_rate))
            total_chunks = max(1, math.ceil(total_frames / frames_per_chunk))
            square_sum = 0.0
            peak = 0.0
            sample_count = 0
            processed_chunks = 0
            inference_total_seconds = 0.0
            _safe_cuda_reset_peak_memory(torch, resolved_device)

            try:
                with wave.open(str(destination_path), "wb") as output:
                    output.setnchannels(2)
                    output.setsampwidth(2)
                    output.setframerate(SEPARATOR_SAMPLE_RATE)
                    for chunk_index in range(total_chunks):
                        if cancel_requested and cancel_requested():
                            raise SeparationCancelled(tr("error.cancelled", language))
                        raw = source_handle.readframes(frames_per_chunk)
                        if not raw:
                            break
                        fraction = chunk_index / total_chunks
                        if progress:
                            progress(
                                24 + int(42 * fraction),
                                tr(
                                    "progress.separating_chunk",
                                    language,
                                    current=chunk_index + 1,
                                    total=total_chunks,
                                ),
                            )
                        mixture = torch.from_numpy(_pcm16_chunk(raw, channels))
                        try:
                            _safe_cuda_synchronize(torch, resolved_device)
                            inference_started = time.perf_counter()
                            with torch.inference_mode():
                                _origin, stems = separator.separate_tensor(mixture, sr=sample_rate)
                            _safe_cuda_synchronize(torch, resolved_device)
                            inference_total_seconds += time.perf_counter() - inference_started
                        except KeyboardInterrupt as exc:
                            raise SeparationCancelled(tr("error.cancelled", language)) from exc
                        except Exception as exc:
                            raise SeparationError(tr("error.separation_failed", language, detail=exc)) from exc
                        pcm, chunk_square, chunk_peak, chunk_samples = _tensor_to_pcm16(stems["guitar"])
                        output.writeframes(pcm)
                        square_sum += chunk_square
                        peak = max(peak, chunk_peak)
                        sample_count += chunk_samples
                        processed_chunks += 1
                        del mixture, stems, _origin
            except Exception:
                destination_path.unlink(missing_ok=True)
                raise

        if not destination_path.is_file() or sample_count == 0:
            raise SeparationError(tr("error.separation_empty", language))
        rms = math.sqrt(square_sum / max(sample_count, 1))
        rms_dbfs = 20.0 * math.log10(max(rms, 1e-12))
        peak_dbfs = 20.0 * math.log10(max(peak, 1e-12))
        if rms_dbfs < -65.0:
            destination_path.unlink(missing_ok=True)
            raise SeparationError(tr("error.guitar_not_found", language))
        if progress:
            progress(68, tr("progress.separation_done", language))
        source_duration_seconds = total_frames / sample_rate
        peak_gpu_memory_bytes = _safe_cuda_peak_memory(torch, resolved_device)
        return SeparationInfo(
            model=SEPARATOR_MODEL,
            backend=f"Demucs 4.1 / PyTorch {resolved_device.upper()}",
            sample_rate=SEPARATOR_SAMPLE_RATE,
            source_duration_seconds=source_duration_seconds,
            processed_chunks=processed_chunks,
            guitar_rms_dbfs=rms_dbfs,
            guitar_peak_dbfs=peak_dbfs,
            model_downloaded_during_run=not was_cached and separator_model_is_cached(),
            requested_device=requested_device,
            resolved_device=resolved_device,
            inference_total_seconds=inference_total_seconds,
            inference_seconds_per_chunk=inference_total_seconds / max(processed_chunks, 1),
            realtime_factor=inference_total_seconds / max(source_duration_seconds, 1e-12),
            peak_gpu_memory_bytes=peak_gpu_memory_bytes,
        )
    finally:
        _safe_cuda_empty_cache(torch, resolved_device)


def separation_info_dict(info: SeparationInfo) -> dict[str, object]:
    """불변 진단 객체를 JSON 저장에 알맞은 일반 사전으로 바꾼다."""
    return asdict(info)
