"""Demucs 6-stem 모델로 밴드 믹스에서 일렉기타만 분리한다.

분리 모델 가중치는 프로그램 ZIP에 포함하지 않는다. 사용자가 AI 기타 분리를
처음 실행할 때 Demucs의 공식 저장소에서 내려받아 사용자 캐시에 보관한다.
"""

from __future__ import annotations

import math
import os
import wave
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

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


def separator_runtime_status() -> dict[str, object]:
    """개발자 진단에 표시할 Demucs·PyTorch 런타임 상태를 반환한다."""
    status: dict[str, object] = {
        "available": False,
        "model": SEPARATOR_MODEL,
        "model_cached": separator_model_is_cached(),
        "cache_path": str(_hf_model_cache_root()),
    }
    try:
        import demucs
        import torch

        status.update(
            {
                "available": True,
                "demucs_version": getattr(demucs, "__version__", "unknown"),
                "torch_version": getattr(torch, "__version__", "unknown"),
                "device": "cpu",
            }
        )
    except Exception as exc:
        status["error"] = str(exc)
    return status


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
) -> SeparationInfo:
    """44.1 kHz PCM 원본을 작은 조각으로 나눠 guitar stem WAV만 기록한다."""
    source_path = Path(source_wav)
    destination_path = Path(destination_wav)
    if not source_path.is_file():
        raise SeparationError(tr("error.file_missing", language))
    was_cached = separator_model_is_cached()
    if progress:
        progress(18, tr("progress.separator_model", language))
    try:
        import torch
        from demucs.api import Separator
    except Exception as exc:
        raise SeparationError(tr("error.separator_runtime", language, detail=exc)) from exc

    # CPU를 모두 점유하지 않도록 한 코어를 남기고 상한을 둔다.
    processor_count = os.cpu_count() or 2
    torch.set_num_threads(max(1, min(8, processor_count - 1)))
    try:
        separator = Separator(
            model=SEPARATOR_MODEL,
            device="cpu",
            shifts=0,
            split=True,
            overlap=0.15,
            jobs=0,
            progress=False,
        )
    except Exception as exc:
        raise SeparationError(tr("error.separator_model", language, detail=exc)) from exc

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
                        _origin, stems = separator.separate_tensor(mixture, sr=sample_rate)
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
    info = SeparationInfo(
        model=SEPARATOR_MODEL,
        backend="Demucs 4.1 / PyTorch CPU",
        sample_rate=SEPARATOR_SAMPLE_RATE,
        source_duration_seconds=total_frames / sample_rate,
        processed_chunks=processed_chunks,
        guitar_rms_dbfs=rms_dbfs,
        guitar_peak_dbfs=peak_dbfs,
        model_downloaded_during_run=not was_cached and separator_model_is_cached(),
    )
    return info


def separation_info_dict(info: SeparationInfo) -> dict[str, object]:
    """불변 진단 객체를 JSON 저장에 알맞은 일반 사전으로 바꾼다."""
    return asdict(info)
