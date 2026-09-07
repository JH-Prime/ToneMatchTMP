"""Demucs 6-stem 모델로 밴드 믹스에서 일렉기타만 분리한다.

분리 모델 가중치는 프로그램 ZIP에 포함하지 않는다. 사용자가 AI 기타 분리를
처음 실행할 때 Demucs의 공식 저장소에서 내려받아 사용자 캐시에 보관한다.
"""

from __future__ import annotations

import io
import math
import os
import re
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
SEPARATION_OVERLAP = 0.15


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
    for name in ("HF_HUB_CACHE", "HUGGINGFACE_HUB_CACHE"):
        explicit = os.environ.get(name, "").strip()
        if explicit:
            return Path(explicit) / "models--adefossez--HTDemucs-6s"
    explicit = os.environ.get("HF_HOME", "").strip()
    if explicit:
        return Path(explicit) / "hub" / "models--adefossez--HTDemucs-6s"
    cache_home = Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache")))
    return cache_home / "huggingface" / "hub" / "models--adefossez--HTDemucs-6s"


def separator_model_is_cached() -> bool:
    """공식 6-stem 모델 가중치가 사용자 캐시에 있는지 가볍게 확인한다."""
    root = _hf_model_cache_root()
    return root.is_dir() and any(root.rglob("*.safetensors"))


def _check_cancelled(cancel_requested: Callable[[], bool] | None, language: str) -> None:
    """다운로드·모델 준비·추론의 경계에서 사용자의 취소 요청을 확인한다."""
    if cancel_requested and cancel_requested():
        raise SeparationCancelled(tr("error.cancelled", language))


def _download_progress_class(
    progress: Callable[[float, str], None] | None,
    cancel_requested: Callable[[], bool] | None,
    language: str,
    filename: str,
    start_percent: float,
    end_percent: float,
) -> type:
    """터미널 없이 실제 Hugging Face 수신 바이트를 앱 콜백으로 전달하는 tqdm을 만든다."""
    from tqdm import tqdm
    display_state = {"percent": float(start_percent)}

    class DownloadProgress(tqdm):
        """stdout·stderr가 없는 EXE에서도 파일 수신량만 기록하는 진행 표시기다."""

        def __init__(self, *args: object, **kwargs: Any) -> None:
            """출력 대상을 메모리로 지정하고 다운로드의 실제 초기 수신량을 기록한다."""
            kwargs.pop("name", None)
            kwargs.update(file=io.StringIO(), disable=False, mininterval=0.25)
            self._last_report_at = 0.0
            self._is_transfer = "downloading bytes" in str(kwargs.get("desc", ""))
            super().__init__(*args, **kwargs)
            self._report(force=True)

        def display(self, *args: object, **kwargs: object) -> bool:
            """콘솔 그리기를 생략해 진행률 때문에 GUI 실행이 실패하지 않도록 한다."""
            return True

        def update(self, n: float = 1) -> bool | None:
            """Hugging Face가 보고한 증가량만 반영하고 취소와 UI 알림을 처리한다."""
            if cancel_requested and cancel_requested():
                raise KeyboardInterrupt
            updated = super().update(n)
            self._report()
            return updated

        def _report(self, force: bool = False) -> None:
            """알려진 파일 크기로만 백분율을 계산하고 총량이 없으면 바이트만 알린다."""
            if not progress:
                return
            now = time.monotonic()
            if not force and now - self._last_report_at < 0.25 and (not self.total or self.n < self.total):
                return
            self._last_report_at = now
            downloaded_mb = f"{max(0, self.n) / 1024**2:.1f}"
            if self._is_transfer:
                progress(display_state["percent"], tr("progress.separator_download_bytes", language,
                                                      filename=filename, downloaded_mb=downloaded_mb))
                return
            if self.total and self.total > 0:
                fraction = min(1.0, max(0.0, self.n / self.total))
                display_state["percent"] = start_percent + (end_percent - start_percent) * fraction
                progress(
                    display_state["percent"],
                    tr("progress.separator_download", language, filename=filename,
                       downloaded_mb=downloaded_mb, total_mb=f"{self.total / 1024**2:.1f}",
                       percent=f"{fraction * 100:.1f}"),
                )
            else:
                progress(start_percent, tr("progress.separator_download_bytes", language,
                                               filename=filename, downloaded_mb=downloaded_mb))

    return DownloadProgress


def _load_hf_separator_model(
    progress: Callable[[float, str], None] | None,
    cancel_requested: Callable[[], bool] | None,
    language: str,
) -> Any:
    """공식 safetensors 모델을 캐시 우선으로 준비하고 다운로드·로딩 단계를 구분한다."""
    from huggingface_hub import hf_hub_download
    from huggingface_hub.errors import LocalEntryNotFoundError
    from demucs.apply import BagOfModels
    from demucs.hf import load_safetensors_model
    import yaml

    def download(filename: str, start: float, end: float) -> Path:
        """캐시 파일을 먼저 찾고 없을 때만 공식 저장소에서 진행률과 함께 받는다."""
        _check_cancelled(cancel_requested, language)
        options = {"repo_id": "adefossez/HTDemucs-6s", "filename": filename}
        try:
            path = hf_hub_download(**options, local_files_only=True)
        except LocalEntryNotFoundError:
            path = hf_hub_download(
                **options,
                tqdm_class=_download_progress_class(progress, cancel_requested, language, filename, start, end),
            )
        _check_cancelled(cancel_requested, language)
        return Path(path)

    yaml_path = download(f"{SEPARATOR_MODEL}.yaml", 18, 18)
    with yaml_path.open("r", encoding="utf-8") as handle:
        bag = yaml.safe_load(handle)
    signatures = bag.get("models", []) if isinstance(bag, dict) else []
    if not isinstance(signatures, list) or not signatures or any(
        not isinstance(signature, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", signature)
        for signature in signatures
    ):
        raise ValueError("Invalid Demucs model manifest: expected safe model signatures")
    paths = [
        download(f"{signature}.safetensors", 18 + 5 * index / len(signatures),
                 18 + 5 * (index + 1) / len(signatures))
        for index, signature in enumerate(signatures)
    ]
    if progress:
        progress(23, tr("progress.separator_loading", language))
    models = []
    for path in paths:
        _check_cancelled(cancel_requested, language)
        models.append(load_safetensors_model(path))
    _check_cancelled(cancel_requested, language)
    model = BagOfModels(models, bag.get("weights"), bag.get("segment"))
    model.eval()
    return model


def _model_error_key(exc: Exception) -> str:
    """예외 체인을 확인해 모델 준비 실패를 네트워크·캐시·메모리 원인으로 분류한다."""
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        name = type(current).__name__.lower()
        if isinstance(current, MemoryError) or "outofmemory" in name:
            return "error.separator_memory"
        if isinstance(current, PermissionError) or (isinstance(current, OSError) and current.errno in {13, 28, 30}):
            return "error.separator_cache"
        if isinstance(current, (ConnectionError, TimeoutError)) or any(
            marker in name for marker in ("connecterror", "timeout", "httperror", "offline", "localentrynotfound")
        ):
            return "error.separator_network"
        current = current.__cause__ or current.__context__
    return "error.separator_model"


class _SeparationProgress:
    """Demucs의 내부 분할 콜백을 전체 음원의 완료 분량으로 변환한다."""

    def __init__(self, progress: Callable[[float, str], None] | None,
                 cancel_requested: Callable[[], bool] | None, language: str) -> None:
        """실행 콜백과 아직 시작하지 않은 조각의 상태를 저장한다."""
        self.progress = progress
        self.cancel_requested = cancel_requested
        self.language = language
        self.chunk_index = 0
        self.total_chunks = 1
        self.total_frames = 1
        self.completed_frames = 0
        self.chunk_frames = 0
        self.strides: list[int] = []
        self.completed_segments: set[tuple[int, int]] = set()

    def begin_chunk(self, model: Any, chunk_index: int, total_chunks: int,
                    total_frames: int, completed_frames: int, chunk_frames: int) -> None:
        """현재 모델의 실제 segment와 overlap으로 조각별 추론 블록 수를 계산한다."""
        self.chunk_index, self.total_chunks = chunk_index, total_chunks
        self.total_frames, self.completed_frames = max(total_frames, 1), completed_frames
        self.chunk_frames = chunk_frames
        self.completed_segments.clear()
        submodels = list(getattr(model, "models", [model]))
        self.strides = []
        for submodel in submodels:
            segment = getattr(submodel, "segment", None)
            sample_rate = getattr(submodel, "samplerate", SEPARATOR_SAMPLE_RATE)
            stride = int((1 - SEPARATION_OVERLAP) * int(segment * sample_rate)) if segment else 0
            self.strides.append(stride)
        self._report(0.0)

    def __call__(self, event: dict[str, Any]) -> None:
        """실제로 끝난 추론 블록만 누적하고 블록 시작·종료 시 취소 요청을 처리한다."""
        if self.cancel_requested and self.cancel_requested():
            # Demucs가 대기 중인 내부 작업까지 중단하는 공식 콜백 취소 규약이다.
            raise KeyboardInterrupt
        if event.get("state") != "end" or not self.strides or not all(self.strides):
            return
        model_index = int(event.get("model_idx_in_bag", 0))
        offset = int(event.get("segment_offset", 0))
        if not 0 <= model_index < len(self.strides) or not 0 <= offset < self.chunk_frames:
            return
        self.completed_segments.add((model_index, offset))
        completed = sum(min(self.strides[index], self.chunk_frames - position)
                        for index, position in self.completed_segments)
        self._report(min(1.0, completed / max(1, self.chunk_frames * len(self.strides))))

    def _report(self, fraction: float) -> None:
        """모델 블록 완료 비율을 오디오 처리 초와 전체 단계 백분율로 알린다."""
        if self.progress:
            completed = self.completed_frames + self.chunk_frames * fraction
            self.progress(
                24 + 42 * min(1.0, completed / self.total_frames),
                tr("progress.separating_segment", self.language, current=self.chunk_index + 1,
                   total=self.total_chunks, completed_seconds=f"{completed / SEPARATOR_SAMPLE_RATE:.1f}",
                   total_seconds=f"{self.total_frames / SEPARATOR_SAMPLE_RATE:.1f}"),
            )

    def finish_chunk(self) -> None:
        """콜백이 없는 호환 분리기에서도 실제 조각 완료 후 진행률을 확정한다."""
        self._report(1.0)


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
    progress: Callable[[float, str], None] | None = None,
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
    _check_cancelled(cancel_requested, language)
    was_cached = separator_model_is_cached()
    if progress:
        progress(18, tr("progress.separator_cache", language))
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
    tracker = _SeparationProgress(progress, cancel_requested, language)

    class ProgressSeparator(Separator):
        """Demucs 4.1의 모델 로딩 지점에 앱 전용 다운로드 진행률을 연결한다."""

        def _load_model(self) -> None:
            """검증된 safetensors 모델을 주입하고 Demucs API의 입력 형식을 초기화한다."""
            self._model = _load_hf_separator_model(progress, cancel_requested, language)
            self._audio_channels = self._model.audio_channels
            self._samplerate = self._model.samplerate

    try:
        separator = ProgressSeparator(
            model=SEPARATOR_MODEL,
            device=resolved_device,
            shifts=0,
            split=True,
            overlap=SEPARATION_OVERLAP,
            jobs=0,
            progress=False,
            callback=tracker,
        )
        _check_cancelled(cancel_requested, language)
    except (SeparationCancelled, KeyboardInterrupt) as exc:
        _safe_cuda_empty_cache(torch, resolved_device)
        raise SeparationCancelled(tr("error.cancelled", language)) from exc
    except Exception as exc:
        _safe_cuda_empty_cache(torch, resolved_device)
        detail = f"{type(exc).__name__}: {exc}"
        raise SeparationError(tr(_model_error_key(exc), language, detail=detail)) from exc

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
                        chunk_frames = len(raw) // (sample_width * channels)
                        tracker.begin_chunk(separator.model, chunk_index, total_chunks, total_frames,
                                            chunk_index * frames_per_chunk, chunk_frames)
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
                        _check_cancelled(cancel_requested, language)
                        pcm, chunk_square, chunk_peak, chunk_samples = _tensor_to_pcm16(stems["guitar"])
                        output.writeframes(pcm)
                        square_sum += chunk_square
                        peak = max(peak, chunk_peak)
                        sample_count += chunk_samples
                        processed_chunks += 1
                        tracker.finish_chunk()
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
