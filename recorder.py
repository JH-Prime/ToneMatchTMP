"""Windows 오디오 장치와 PC 재생음(WASAPI loopback)을 WAV로 녹음한다."""

from __future__ import annotations

import threading
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np

from i18n import tr


RECORD_SAMPLE_RATE = 44_100
RECORD_BLOCK_FRAMES = 4_410
MAX_RECORD_SECONDS = 20 * 60


class RecordingError(RuntimeError):
    """녹음 장치 또는 녹음 데이터 문제를 사용자용 오류로 전달한다."""


@dataclass(frozen=True)
class CaptureDevice:
    """오디오 장치 선택 상자에 필요한 식별자와 표시 정보를 보관한다."""

    id: str
    name: str
    is_loopback: bool


def list_capture_devices() -> list[CaptureDevice]:
    """마이크·오디오 인터페이스와 PC 출력 loopback 장치를 함께 나열한다."""
    try:
        import soundcard as sc

        microphones = sc.all_microphones(include_loopback=True)
    except Exception as exc:
        raise RecordingError(str(exc)) from exc
    devices: list[CaptureDevice] = []
    seen: set[str] = set()
    for microphone in microphones:
        identifier = str(microphone.id)
        if identifier in seen:
            continue
        seen.add(identifier)
        devices.append(
            CaptureDevice(
                id=identifier,
                name=str(microphone.name),
                is_loopback=bool(getattr(microphone, "isloopback", False)),
            )
        )
    devices.sort(key=lambda item: (not item.is_loopback, item.name.casefold()))
    return devices


def capture_device_label(device: CaptureDevice, language: str = "ko") -> str:
    """장치 종류가 드러나는 언어별 콤보박스 라벨을 만든다."""
    kind = tr("record.loopback", language) if device.is_loopback else tr("record.input", language)
    return f"{kind} · {device.name}"


def record_device_to_wav(
    device_id: str,
    destination_wav: str | Path,
    maximum_seconds: float,
    stop_event: threading.Event,
    progress: Callable[[float, str], None] | None = None,
    language: str = "ko",
) -> float:
    """선택 장치를 중지 요청 또는 제한 시간까지 PCM16 스테레오 WAV로 녹음한다."""
    duration_limit = max(3.0, min(float(maximum_seconds), float(MAX_RECORD_SECONDS)))
    try:
        import soundcard as sc

        microphone = sc.get_microphone(device_id, include_loopback=True)
    except Exception as exc:
        raise RecordingError(tr("error.record_device", language, detail=exc)) from exc
    if microphone is None:
        raise RecordingError(tr("error.record_device_missing", language))

    destination_path = Path(destination_wav)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    written_frames = 0
    try:
        with wave.open(str(destination_path), "wb") as output:
            output.setnchannels(2)
            output.setsampwidth(2)
            output.setframerate(RECORD_SAMPLE_RATE)
            with microphone.recorder(
                samplerate=RECORD_SAMPLE_RATE,
                channels=2,
                blocksize=RECORD_BLOCK_FRAMES,
            ) as recorder:
                while not stop_event.is_set() and written_frames < int(duration_limit * RECORD_SAMPLE_RATE):
                    remaining = int(duration_limit * RECORD_SAMPLE_RATE) - written_frames
                    frame_count = min(RECORD_BLOCK_FRAMES, remaining)
                    block = np.asarray(recorder.record(numframes=frame_count), dtype=np.float32)
                    if block.ndim == 1:
                        block = np.column_stack((block, block))
                    elif block.shape[1] == 1:
                        block = np.repeat(block, 2, axis=1)
                    elif block.shape[1] > 2:
                        block = block[:, :2]
                    pcm = np.round(np.clip(block, -0.999, 0.999) * 32767.0).astype("<i2")
                    output.writeframes(pcm.tobytes())
                    written_frames += len(block)
                    elapsed = written_frames / RECORD_SAMPLE_RATE
                    if progress:
                        progress(elapsed, tr("progress.recording", language, elapsed=elapsed, limit=duration_limit))
    except Exception as exc:
        destination_path.unlink(missing_ok=True)
        if isinstance(exc, RecordingError):
            raise
        raise RecordingError(tr("error.record_failed", language, detail=exc)) from exc

    duration = written_frames / RECORD_SAMPLE_RATE
    if duration < 3.0:
        destination_path.unlink(missing_ok=True)
        raise RecordingError(tr("error.record_too_short", language))
    return duration
