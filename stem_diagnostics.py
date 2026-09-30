"""화면과 장치 캡처 없이 실제 CPU 스템 제거·취소를 검증하는 로컬 진단이다."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import tempfile
import time
import wave

import numpy as np

from catalog import APP_VERSION
from separator import separator_runtime_status
from stem_removal import MAX_REMOVAL_SECONDS, StemRemovalCancelled, remove_stems_from_file


def _digest(path: Path) -> str:
    """원본 보존 비교용 해시를 메모리에서 계산하고 보고서에는 저장하지 않는다."""
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _inspect_wav(path: Path, duration: float) -> dict[str, object]:
    """WAV 전체의 프레임 수·형식·최대 레벨을 제한된 메모리로 검증한다."""
    frames_read = 0
    peak = 0
    with wave.open(str(path), "rb") as stream:
        if (stream.getnchannels(), stream.getsampwidth(), stream.getframerate()) != (2, 2, 44100):
            raise ValueError("Unexpected WAV format")
        expected = round(duration * 44100)
        if stream.getnframes() != expected:
            raise ValueError("Unexpected WAV duration")
        while raw := stream.readframes(65536):
            if len(raw) % 4:
                raise ValueError("Truncated stereo frame")
            frames_read += len(raw) // 4
            values = np.frombuffer(raw, dtype="<i2").astype(np.int32)
            peak = max(peak, int(np.max(np.abs(values))))
        if frames_read != expected:
            raise ValueError("Truncated WAV output")
    return {"frames": frames_read, "sample_rate": 44100, "channels": 2,
            "sample_format": "PCM16LE", "peak_pcm16": peak}


def run_stem_self_test(
    source: str | Path,
    output: str | Path,
    seconds: float = 0,
    cancel_at: float | None = None,
) -> int:
    """캐시된 CPU 모델로 기타·피아노 제거 또는 취소를 실행하고 경로 없는 JSON을 쓴다.

    seconds=0은 최대 20분의 전체 입력이다. 기존 JSON은 덮어쓰지 않으며 임시 WAV는
    성공·오류·취소 모두 정리한다. 청감 품질이나 GUI 검증을 대신하지 않는다.
    """
    try:
        seconds = float(seconds)
        if not math.isfinite(seconds) or (seconds != 0 and not 3 <= seconds <= MAX_REMOVAL_SECONDS):
            return 2
        if cancel_at is not None:
            cancel_at = float(cancel_at)
            if not math.isfinite(cancel_at) or not 0 < cancel_at < 100:
                return 2
        source_path = Path(source).expanduser().resolve(strict=True)
        if not source_path.is_file():
            return 2
        destination = Path(output).expanduser()
        if destination.suffix.lower() != ".json":
            return 2
        destination.parent.mkdir(parents=True, exist_ok=True)
        report = destination.open("x", encoding="utf-8")
    except (OSError, ValueError, TypeError):
        return 2

    started = time.perf_counter()
    payload: dict[str, object] = {
        "schema": "tonematch-stem-self-test/v1", "app_version": APP_VERSION,
        "ok": False, "status": "running", "mode": "cancel" if cancel_at is not None else "complete",
        "requested_seconds": seconds, "cancel_at_percent": cancel_at,
        "compute_device": "cpu", "progress_updates": 0, "progress_percent": 0.0,
        "progress_monotonic": True, "source_unchanged": False,
        "temporary_audio_cleaned": False, "gui_tested": False, "listening_quality_assessed": False,
    }
    cancellation_requested = False

    def write_report() -> None:
        """명시적으로 새로 만든 진단 파일에 숫자 중심 상태만 갱신한다."""
        payload["elapsed_seconds"] = time.perf_counter() - started
        report.seek(0)
        report.write(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False))
        report.truncate()
        report.flush()

    def progress(value: float, _message: str) -> None:
        """경로나 다운로드 메시지를 기록하지 않고 실제 진행값과 취소 조건을 수집한다."""
        nonlocal cancellation_requested
        value = float(value)
        if not math.isfinite(value) or not 0 <= value <= 100:
            raise ValueError("Invalid progress")
        payload["progress_monotonic"] = bool(payload["progress_monotonic"]) and value >= float(payload["progress_percent"])
        payload["progress_percent"] = value
        payload["progress_updates"] = int(payload["progress_updates"]) + 1
        if cancel_at is not None and value >= cancel_at:
            cancellation_requested = True
        write_report()

    with report:
        write_report()
        try:
            runtime = separator_runtime_status()
            if not runtime.get("available") or not runtime.get("model_cached"):
                payload["status"] = "cached_model_required"
                write_report()
                return 2
            original_digest = _digest(source_path)
            with tempfile.TemporaryDirectory(prefix="tonematch_stem_diagnostic_") as temporary:
                temporary_path = Path(temporary)
                wav = temporary_path / "removed.wav"
                try:
                    result = remove_stems_from_file(
                        source_path, wav, ("guitar", "piano"), end_seconds=seconds,
                        compute_preference="cpu", language="en", progress=progress,
                        require_cached_model=True,
                        cancel_requested=lambda: cancellation_requested,
                    )
                    if cancel_at is not None:
                        raise ValueError("Expected cancellation did not occur")
                    payload["wav"] = _inspect_wav(wav, float(result["duration_seconds"]))
                    payload["result"] = {key: result[key] for key in (
                        "duration_seconds", "processed_chunks", "model_downloaded_during_run",
                        "inference_total_seconds", "normalization_gain", "normalized",
                        "peak_before_normalization", "removed_stems", "kept_stems",
                    )}
                    payload["status"] = "completed"
                except StemRemovalCancelled:
                    if cancel_at is None or not cancellation_requested:
                        raise
                    payload["status"] = "cancelled_as_requested"
                    payload["cancelled_output_absent"] = not wav.exists()
                payload["partial_files_absent"] = not any(temporary_path.glob("*.partial.wav"))
            payload["temporary_audio_cleaned"] = not temporary_path.exists()
            payload["source_unchanged"] = _digest(source_path) == original_digest
            payload["ok"] = all((
                payload["source_unchanged"], payload["temporary_audio_cleaned"],
                payload["partial_files_absent"], payload["progress_monotonic"],
                payload.get("cancelled_output_absent", True),
                cancel_at is not None or payload["progress_percent"] == 100,
            ))
        except Exception as exc:
            # 예외 메시지는 파일명·캐시 경로를 담을 수 있어 타입만 공개 진단에 보존한다.
            payload["status"] = "failed"
            payload["error_type"] = type(exc).__name__
            payload["temporary_audio_cleaned"] = "temporary_path" in locals() and not temporary_path.exists()
        write_report()
        return 0 if payload["ok"] else 1


def stem_self_test_cli(arguments: list[str]) -> int:
    """명시적인 진단 인수만 처리하고 잘못된 인수에서는 GUI를 열지 않는다."""
    parser = argparse.ArgumentParser(description="Local cached-CPU stem self-test (no GUI)")
    parser.add_argument("--stem-self-test-source", required=True)
    parser.add_argument("--stem-self-test-output", required=True)
    parser.add_argument("--stem-self-test-seconds", type=float, default=0)
    parser.add_argument("--stem-self-test-cancel-at", type=float)
    try:
        args = parser.parse_args(arguments)
    except SystemExit as exc:
        return int(exc.code)
    return run_stem_self_test(args.stem_self_test_source, args.stem_self_test_output,
                              args.stem_self_test_seconds, args.stem_self_test_cancel_at)
