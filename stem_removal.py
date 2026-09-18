"""로컬 Demucs 6-stem 모델로 선택 악기를 제외한 stereo WAV를 만든다.

원본 파일과 개별 stem은 보존하거나 덮어쓰지 않는다. 선택 구간을 앱에 포함된
FFmpeg로 PCM 변환한 뒤 stem 조각을 즉시 합산하고, 최종 피크가 0 dBFS를 넘을
때만 전체 결과를 같은 비율로 낮춰 PCM16 WAV로 확정한다.
"""

from __future__ import annotations

import math
import os
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path
from typing import Callable, Iterable

import numpy as np

from separator import (
    SEPARATOR_MODEL,
    SEPARATOR_SAMPLE_RATE,
    SEPARATOR_STEMS,
    SeparationCancelled,
    SeparationError,
    StemSeparationInfo,
    separate_stem_chunks,
)


MIN_REMOVAL_SECONDS = 3.0
MAX_REMOVAL_SECONDS = 20 * 60.0
OUTPUT_CHANNELS = 2
OUTPUT_SAMPLE_WIDTH = 2
NORMALIZED_PEAK = 0.999


class StemRemovalError(RuntimeError):
    """사용자에게 보여 줄 수 있는 stem 제거 입력·처리 오류를 나타낸다."""


class StemRemovalCancelled(StemRemovalError):
    """사용자가 stem 제거를 취소했음을 나타낸다."""


def _message(korean: str, english: str, language: str) -> str:
    """선택 언어 문장을 우선하고 오류 로그를 위해 다른 언어도 함께 보존한다."""
    return f"{english} / {korean}" if str(language).lower().startswith("en") else f"{korean} / {english}"


def _report(progress: Callable[[float, str], None] | None, value: float, message: str) -> None:
    """진행 콜백에 유효한 0~100 범위 값만 전달한다."""
    if progress:
        progress(max(0.0, min(100.0, float(value))), message)


def _check_cancelled(cancel_requested: Callable[[], bool] | None, language: str) -> None:
    """단계 경계에서 취소 요청을 동일한 공개 예외로 변환한다."""
    if cancel_requested and cancel_requested():
        raise StemRemovalCancelled(_message("스템 제거가 취소되었습니다.", "Stem removal was cancelled.", language))


def _normalize_removed_stems(removed_stems: Iterable[str]) -> tuple[str, ...]:
    """제거할 stem 이름을 고정 순서로 정규화하고 빈 값·전체 제거를 거부한다."""
    if isinstance(removed_stems, (str, bytes)):
        selected = {str(removed_stems).strip().lower()}
    else:
        selected = {str(name).strip().lower() for name in removed_stems}
    selected.discard("")
    unknown = sorted(selected.difference(SEPARATOR_STEMS))
    if unknown:
        detail = ", ".join(unknown)
        raise StemRemovalError(f"지원하지 않는 stem입니다: {detail}. / Unsupported stem: {detail}.")
    normalized = tuple(name for name in SEPARATOR_STEMS if name in selected)
    if not normalized:
        raise StemRemovalError(
            "제거할 stem을 하나 이상 선택하세요. / Select at least one stem to remove."
        )
    if len(normalized) == len(SEPARATOR_STEMS):
        raise StemRemovalError(
            "6개 stem을 모두 제거할 수 없습니다. 하나 이상 남겨 주세요. "
            "/ All six stems cannot be removed; keep at least one."
        )
    return normalized


def _normalized_paths(
    source: str | Path,
    destination: str | Path,
    language: str,
) -> tuple[Path, Path]:
    """입출력 경로를 검증하고 기존 파일 또는 원본 덮어쓰기를 차단한다."""
    source_path = Path(source).expanduser()
    destination_path = Path(destination).expanduser()
    if not source_path.is_file():
        raise StemRemovalError(
            "입력 오디오/영상 파일을 찾을 수 없습니다. / The input audio/video file was not found."
        )
    if destination_path.suffix.lower() != ".wav":
        raise StemRemovalError(
            "출력 파일은 .wav 확장자를 사용해야 합니다. / The output file must use the .wav extension."
        )
    source_resolved = source_path.resolve()
    # 마지막 경로 요소는 따라가지 않아 끊어진 심볼릭 링크도 기존 출력으로 보호한다.
    destination_resolved = destination_path.parent.resolve(strict=False) / destination_path.name
    source_key = os.path.normcase(str(source_resolved))
    destination_key = os.path.normcase(str(destination_resolved))
    if source_key == destination_key:
        raise StemRemovalError(
            "원본 파일을 출력 대상으로 사용할 수 없습니다. / The source file cannot be used as the destination."
        )
    if os.path.lexists(destination_resolved):
        raise StemRemovalError(
            "출력 파일이 이미 있습니다. 원본 보호를 위해 새 파일 이름을 선택하세요. "
            "/ The output file already exists; choose a new name to protect existing data."
        )
    parent = destination_resolved.parent
    if parent.exists() and not parent.is_dir():
        raise StemRemovalError(
            "출력 폴더 경로가 디렉터리가 아닙니다. / The output parent path is not a directory."
        )
    try:
        parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise StemRemovalError(
            _message("출력 폴더를 만들 수 없습니다.", "Could not create the output directory.", language)
        ) from exc
    return source_resolved, destination_resolved


def _segment_request(start_seconds: float, end_seconds: float) -> tuple[float, float]:
    """시작·끝 값을 유한한 초 단위로 검사하고 최대 20분 구간을 계산한다."""
    try:
        start = float(start_seconds)
        end = float(end_seconds)
    except (TypeError, ValueError) as exc:
        raise StemRemovalError(
            "시작·끝 시간은 숫자여야 합니다. / Start and end times must be numeric."
        ) from exc
    if not math.isfinite(start) or not math.isfinite(end) or start < 0 or end < 0:
        raise StemRemovalError(
            "시작·끝 시간은 0 이상의 유한한 값이어야 합니다. "
            "/ Start and end times must be finite non-negative values."
        )
    if end and end <= start:
        raise StemRemovalError(
            "끝 시간은 시작 시간보다 커야 합니다. / End time must be greater than start time."
        )
    requested = end - start if end else MAX_REMOVAL_SECONDS
    if requested < MIN_REMOVAL_SECONDS:
        raise StemRemovalError(
            "선택 구간은 최소 3초여야 합니다. / The selected segment must be at least 3 seconds."
        )
    return start, min(requested, MAX_REMOVAL_SECONDS)


def _ffmpeg_path() -> Path:
    """소스·PyInstaller 실행에서 앱에 포함된 FFmpeg만 찾아 반환한다."""
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    candidates = (
        root / "resources" / "ffmpeg.exe",
        root / "ffmpeg.exe",
        Path(__file__).resolve().parent / "resources" / "ffmpeg.exe",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[0]


def _stop_process(process: subprocess.Popen[str]) -> None:
    """취소·시간 초과 시 FFmpeg 자식 프로세스를 끝까지 회수한다."""
    try:
        process.terminate()
        process.communicate(timeout=2.0)
    except (OSError, subprocess.TimeoutExpired):
        try:
            process.kill()
        except OSError:
            pass
        try:
            process.communicate(timeout=2.0)
        except (OSError, subprocess.TimeoutExpired):
            pass


def _decode_input(
    source: Path,
    destination_wav: Path,
    start_seconds: float,
    requested_seconds: float,
    progress: Callable[[float, str], None] | None,
    cancel_requested: Callable[[], bool] | None,
    language: str,
) -> float:
    """로컬 FFmpeg를 폴링해 선택 구간을 취소 가능한 stereo PCM16으로 변환한다."""
    converter = _ffmpeg_path()
    if not converter.is_file():
        raise StemRemovalError(
            _message("앱에 포함된 FFmpeg를 찾을 수 없습니다.", "Bundled FFmpeg was not found.", language)
        )
    _check_cancelled(cancel_requested, language)
    _report(progress, 3, _message("입력 오디오를 준비하는 중입니다.", "Preparing input audio.", language))
    command = [
        str(converter),
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-ss",
        f"{start_seconds:.3f}",
        "-i",
        str(source),
        "-t",
        f"{requested_seconds:.3f}",
        "-vn",
        "-ac",
        str(OUTPUT_CHANNELS),
        "-ar",
        str(SEPARATOR_SAMPLE_RATE),
        "-c:a",
        "pcm_s16le",
        "-y",
        str(destination_wav),
    ]
    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creation_flags,
        )
    except OSError as exc:
        raise StemRemovalError(
            _message("FFmpeg를 실행할 수 없습니다.", "Could not start FFmpeg.", language)
        ) from exc
    deadline = time.monotonic() + max(180.0, requested_seconds * 1.5)
    stderr = ""
    while True:
        if cancel_requested and cancel_requested():
            _stop_process(process)
            destination_wav.unlink(missing_ok=True)
            raise StemRemovalCancelled(
                _message("스템 제거가 취소되었습니다.", "Stem removal was cancelled.", language)
            )
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            _stop_process(process)
            destination_wav.unlink(missing_ok=True)
            raise StemRemovalError(
                _message("오디오 변환 시간이 초과되었습니다.", "Audio decoding timed out.", language)
            )
        try:
            _stdout, stderr = process.communicate(timeout=min(0.2, remaining))
            break
        except subprocess.TimeoutExpired:
            continue
    if process.returncode != 0 or not destination_wav.is_file():
        destination_wav.unlink(missing_ok=True)
        details = (stderr or "").strip().splitlines()
        detail = details[-1] if details else "unknown FFmpeg error"
        raise StemRemovalError(
            _message(f"입력 오디오 변환에 실패했습니다: {detail}", f"Input audio decoding failed: {detail}", language)
        )
    try:
        with wave.open(str(destination_wav), "rb") as decoded:
            channels = decoded.getnchannels()
            width = decoded.getsampwidth()
            sample_rate = decoded.getframerate()
            frame_count = decoded.getnframes()
    except (OSError, wave.Error) as exc:
        destination_wav.unlink(missing_ok=True)
        raise StemRemovalError(
            _message("변환된 오디오를 읽을 수 없습니다.", "Decoded audio could not be read.", language)
        ) from exc
    if channels != OUTPUT_CHANNELS or width != OUTPUT_SAMPLE_WIDTH or sample_rate != SEPARATOR_SAMPLE_RATE:
        destination_wav.unlink(missing_ok=True)
        raise StemRemovalError(
            _message("FFmpeg가 예상한 PCM 형식을 만들지 못했습니다.", "FFmpeg produced an unexpected PCM format.", language)
        )
    actual_duration = frame_count / sample_rate
    if actual_duration < MIN_REMOVAL_SECONDS:
        destination_wav.unlink(missing_ok=True)
        raise StemRemovalError(
            "입력의 남은 오디오가 3초보다 짧습니다. / Remaining input audio is shorter than 3 seconds."
        )
    _report(progress, 12, _message("입력 오디오 준비가 완료되었습니다.", "Input audio is ready.", language))
    return actual_duration


def _write_pcm16_output(
    raw_mix: Path,
    partial_wav: Path,
    frame_count: int,
    gain: float,
    progress: Callable[[float, str], None] | None,
    cancel_requested: Callable[[], bool] | None,
    language: str,
) -> None:
    """임시 float32 합산 결과를 취소 가능한 PCM16 stereo WAV로 변환한다."""
    expected_bytes = frame_count * OUTPUT_CHANNELS * np.dtype("<f4").itemsize
    if raw_mix.stat().st_size != expected_bytes:
        raise StemRemovalError(
            "임시 합산 오디오 크기가 올바르지 않습니다. / Temporary mixed audio has an invalid size."
        )
    completed_frames = 0
    frames_per_block = 65_536
    with raw_mix.open("rb") as source_handle, wave.open(str(partial_wav), "wb") as output:
        output.setnchannels(OUTPUT_CHANNELS)
        output.setsampwidth(OUTPUT_SAMPLE_WIDTH)
        output.setframerate(SEPARATOR_SAMPLE_RATE)
        while True:
            _check_cancelled(cancel_requested, language)
            raw = source_handle.read(frames_per_block * OUTPUT_CHANNELS * 4)
            if not raw:
                break
            values = np.frombuffer(raw, dtype="<f4")
            if values.size % OUTPUT_CHANNELS:
                raise StemRemovalError(
                    "임시 합산 오디오가 손상되었습니다. / Temporary mixed audio is corrupt."
                )
            scaled = values.astype(np.float64) * gain
            pcm = np.rint(np.clip(scaled, -1.0, 1.0) * 32_767.0).astype("<i2")
            output.writeframes(pcm.tobytes())
            completed_frames += values.size // OUTPUT_CHANNELS
            _report(
                progress,
                90 + 9 * min(1.0, completed_frames / max(frame_count, 1)),
                _message("WAV 결과를 기록하는 중입니다.", "Writing the WAV result.", language),
            )
    if completed_frames != frame_count:
        raise StemRemovalError(
            "완성된 WAV 길이가 예상과 다릅니다. / Completed WAV length does not match the expected length."
        )


def _commit_new_output(partial_wav: Path, destination_wav: Path, language: str) -> None:
    """같은 폴더의 완성 파일을 기존 이름을 덮어쓰지 않는 원자적 연산으로 확정한다."""
    try:
        if os.name == "nt":
            # Windows rename은 목적지가 있으면 실패하며 exFAT에도 하드 링크가 필요 없다.
            os.rename(partial_wav, destination_wav)
        else:
            # POSIX rename은 기존 파일을 교체하므로 새 링크의 배타적 생성만 허용한다.
            os.link(partial_wav, destination_wav)
    except FileExistsError as exc:
        raise StemRemovalError(
            _message(
                "처리 중 출력 파일이 생성되어 덮어쓰지 않았습니다.",
                "The destination appeared during processing and was not overwritten.",
                language,
            )
        ) from exc
    except OSError as exc:
        raise StemRemovalError(
            _message(
                "이 저장 위치에서는 기존 파일을 보호하는 원자적 저장을 사용할 수 없습니다.",
                "Atomic no-overwrite saving is unavailable at this destination.",
                language,
            )
        ) from exc


def remove_stems_from_file(
    source: str | Path,
    destination: str | Path,
    removed_stems: Iterable[str],
    start_seconds: float = 0,
    end_seconds: float = 0,
    compute_preference: str = "auto",
    progress: Callable[[float, str], None] | None = None,
    cancel_requested: Callable[[], bool] | None = None,
    language: str = "ko",
) -> dict[str, object]:
    """입력의 선택 stem을 제외한 나머지를 새 PCM16 stereo WAV로 안전하게 저장한다.

    출력 경로에 파일이 이미 있으면 덮어쓰지 않고 실패한다. 성공 직전까지는 같은
    폴더의 ``.partial.wav``만 사용하며 취소·오류 시 이를 제거한다.
    """
    started_at = time.perf_counter()
    removed = _normalize_removed_stems(removed_stems)
    kept = tuple(name for name in SEPARATOR_STEMS if name not in removed)
    start, requested_duration = _segment_request(start_seconds, end_seconds)
    source_path, destination_path = _normalized_paths(source, destination, language)
    _check_cancelled(cancel_requested, language)
    _report(progress, 0, _message("스템 제거를 준비하는 중입니다.", "Preparing stem removal.", language))

    partial_path: Path | None = None
    try:
        with tempfile.TemporaryDirectory(prefix="tonematch_stem_remove_") as temporary_directory:
            temporary = Path(temporary_directory)
            decoded_wav = temporary / "input.wav"
            raw_mix = temporary / "kept_mix.float32le"
            duration = _decode_input(
                source_path,
                decoded_wav,
                start,
                requested_duration,
                progress,
                cancel_requested,
                language,
            )
            frame_count = 0
            peak_before_normalization = 0.0

            def consume_chunk(stems: dict[str, np.ndarray]) -> None:
                """남길 stem만 즉시 합산해 개별 stem의 디스크 저장과 전체 메모리 보관을 피한다."""
                nonlocal frame_count, peak_before_normalization
                _check_cancelled(cancel_requested, language)
                arrays = [stems[name] for name in kept]
                shapes = {array.shape for array in arrays}
                if len(shapes) != 1:
                    raise StemRemovalError(
                        "stem 조각의 채널 또는 길이가 서로 다릅니다. / Stem chunk shapes do not match."
                    )
                mixed = np.zeros(arrays[0].shape, dtype=np.float64)
                for array in arrays:
                    mixed += array
                if not np.all(np.isfinite(mixed)):
                    raise StemRemovalError(
                        "합산 결과에 유효하지 않은 숫자가 있습니다. / Mixed output contains non-finite samples."
                    )
                chunk_peak = float(np.max(np.abs(mixed))) if mixed.size else 0.0
                if chunk_peak > float(np.finfo(np.float32).max):
                    raise StemRemovalError(
                        "합산 결과가 지원하는 오디오 숫자 범위를 넘었습니다. "
                        "/ Mixed output exceeds the supported audio sample range."
                    )
                peak_before_normalization = max(peak_before_normalization, chunk_peak)
                interleaved = np.asarray(mixed.T, dtype="<f4")
                with raw_mix.open("ab") as raw_output:
                    raw_output.write(interleaved.tobytes())
                frame_count += mixed.shape[1]

            def separation_progress(value: float, message: str) -> None:
                """기존 분리기의 18~68 단계를 이 작업의 15~85 구간으로 변환한다."""
                fraction = (max(18.0, min(68.0, float(value))) - 18.0) / 50.0
                _report(progress, 15 + 70 * fraction, message)

            try:
                separation_info: StemSeparationInfo = separate_stem_chunks(
                    decoded_wav,
                    kept,
                    consume_chunk,
                    separation_progress,
                    cancel_requested,
                    language,
                    compute_preference,
                )
            except SeparationCancelled as exc:
                raise StemRemovalCancelled(
                    _message("스템 제거가 취소되었습니다.", "Stem removal was cancelled.", language)
                ) from exc
            except SeparationError as exc:
                raise StemRemovalError(str(exc)) from exc
            _check_cancelled(cancel_requested, language)
            if frame_count < 1 or not raw_mix.is_file():
                raise StemRemovalError(
                    "남은 stem 합산 결과가 비어 있습니다. / The kept-stem mixture is empty."
                )
            normalization_gain = (
                NORMALIZED_PEAK / peak_before_normalization
                if peak_before_normalization > 1.0
                else 1.0
            )
            normalized = normalization_gain < 1.0
            _report(
                progress,
                88,
                _message(
                    "클리핑을 확인하고 출력 레벨을 계산하는 중입니다.",
                    "Checking clipping and calculating output level.",
                    language,
                ),
            )
            descriptor, partial_name = tempfile.mkstemp(
                prefix=f".{destination_path.stem}.",
                suffix=".partial.wav",
                dir=destination_path.parent,
            )
            os.close(descriptor)
            partial_path = Path(partial_name)
            _write_pcm16_output(
                raw_mix,
                partial_path,
                frame_count,
                normalization_gain,
                progress,
                cancel_requested,
                language,
            )
            _check_cancelled(cancel_requested, language)
            total_seconds = time.perf_counter() - started_at
            result: dict[str, object] = {
                "schema": "tonematch-tmp-stem-removal/v1",
                "model": SEPARATOR_MODEL,
                "backend": separation_info.backend,
                "removed_stems": list(removed),
                "kept_stems": list(kept),
                "start_seconds": start,
                "end_seconds": start + duration,
                "duration_seconds": duration,
                "sample_rate": separation_info.sample_rate,
                "channels": OUTPUT_CHANNELS,
                "sample_format": "PCM16LE",
                "output_path": str(destination_path),
                "requested_device": separation_info.requested_device,
                "resolved_device": separation_info.resolved_device,
                "processed_chunks": separation_info.processed_chunks,
                "model_downloaded_during_run": separation_info.model_downloaded_during_run,
                "inference_total_seconds": separation_info.inference_total_seconds,
                "total_seconds": total_seconds,
                "peak_before_normalization": peak_before_normalization,
                "normalized": normalized,
                "normalization_gain": normalization_gain,
            }
        # 디코딩·합산 임시 파일을 모두 정리한 뒤 결과를 확정한다. 정리 실패를
        # 이미 저장된 최종 파일의 처리 실패로 잘못 보고하지 않도록 순서를 보장한다.
        _check_cancelled(cancel_requested, language)
        _commit_new_output(partial_path, destination_path, language)
        result["total_seconds"] = time.perf_counter() - started_at
        try:
            _report(progress, 100, _message("스템 제거가 완료되었습니다.", "Stem removal is complete.", language))
        except Exception:
            # 출력이 원자적으로 확정된 뒤 UI 콜백 문제로 성공 결과를 실패로 바꾸지 않는다.
            pass
        return result
    except StemRemovalCancelled:
        raise
    except StemRemovalError:
        raise
    except OSError as exc:
        raise StemRemovalError(
            _message("WAV 결과를 저장하지 못했습니다.", "Could not save the WAV result.", language)
        ) from exc
    finally:
        if partial_path is not None:
            try:
                partial_path.unlink(missing_ok=True)
            except OSError:
                # 완성 파일의 성공 여부를 보조 이름 정리 실패로 뒤집지 않는다.
                pass
