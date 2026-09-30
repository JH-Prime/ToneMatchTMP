"""화면 없는 실제 스템 진단의 보고·개인정보·기존 파일 보호 경계를 검증한다."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
import wave
from unittest.mock import patch

import numpy as np

MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

import stem_diagnostics as diagnostics
from stem_removal import StemRemovalCancelled


def fake_removal(source, destination, removed_stems, **kwargs):
    """실제 모델 없이 진행률·취소·유효한 3초 WAV를 진단 함수에 제공한다."""
    for value in (0, 12, 70):
        kwargs["progress"](value, str(source))
        if kwargs["cancel_requested"]():
            raise StemRemovalCancelled("private path is not for the report")
    with wave.open(str(destination), "wb") as stream:
        stream.setnchannels(2)
        stream.setsampwidth(2)
        stream.setframerate(44100)
        stream.writeframes(np.full((3 * 44100, 2), 3273, dtype="<i2").tobytes())
    kwargs["progress"](100, str(destination))
    return {"duration_seconds": 3.0, "processed_chunks": 1,
            "model_downloaded_during_run": False, "inference_total_seconds": 0.01,
            "normalization_gain": 1, "normalized": False, "peak_before_normalization": 0.1,
            "removed_stems": list(removed_stems), "kept_stems": ["vocals", "drums", "bass", "other"],
            "output_path": str(destination)}


class StemDiagnosticsTests(unittest.TestCase):
    """진단 CLI와 보고서가 사용자 파일을 보존하고 실제 실패를 감추지 않는지 확인한다."""

    def setUp(self) -> None:
        """각 테스트에 새 입력·보고서 경로와 캐시된 가상 런타임을 준비한다."""
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "private-song.mp3"
        self.source.write_bytes(b"original source")
        self.output = self.root / "report.json"
        self.runtime = patch.object(diagnostics, "separator_runtime_status", return_value={
            "available": True, "model_cached": True, "cache_path": str(self.root),
        })
        self.runtime.start()
        self.addCleanup(self.runtime.stop)

    def report(self) -> dict:
        """생성된 JSON 진단을 읽어 검증할 수 있게 반환한다."""
        return json.loads(self.output.read_text(encoding="utf-8"))

    def test_success_checks_pcm_and_cleans_temporary_audio(self) -> None:
        """정상 출력 전체 길이·피크·진행률을 검증하고 테스트 WAV는 지워야 한다."""
        with patch.object(diagnostics, "remove_stems_from_file", side_effect=fake_removal) as remove:
            self.assertEqual(diagnostics.run_stem_self_test(self.source, self.output), 0)
        report = self.report()
        self.assertTrue(report["ok"])
        self.assertEqual(report["status"], "completed")
        self.assertEqual(report["wav"]["frames"], 132300)
        self.assertEqual(report["wav"]["peak_pcm16"], 3273)
        self.assertEqual(report["progress_updates"], 4)
        self.assertEqual(report["progress_percent"], 100)
        self.assertTrue(report["temporary_audio_cleaned"])
        self.assertTrue(report["source_unchanged"])
        self.assertFalse(Path(remove.call_args.args[1]).parent.exists())
        self.assertTrue(remove.call_args.kwargs["require_cached_model"])
        serialized = self.output.read_text(encoding="utf-8")
        self.assertNotIn("private-song", serialized)
        self.assertNotIn(str(self.root), serialized)
        self.assertNotIn("output_path", serialized)
        self.assertFalse(report["gui_tested"])

    def test_expected_cancel_is_verified_and_no_audio_remains(self) -> None:
        """요청한 실제 진행 경계에서 취소되면 출력이 없고 성공한 취소 진단이어야 한다."""
        with patch.object(diagnostics, "remove_stems_from_file", side_effect=fake_removal):
            self.assertEqual(diagnostics.run_stem_self_test(self.source, self.output, cancel_at=20), 0)
        report = self.report()
        self.assertEqual(report["status"], "cancelled_as_requested")
        self.assertTrue(report["cancelled_output_absent"])
        self.assertTrue(report["temporary_audio_cleaned"])
        self.assertEqual(report["progress_percent"], 70)

    def test_existing_report_and_source_are_not_overwritten(self) -> None:
        """기존 JSON과 입력을 보고서 경로로 지정해도 내용이 바뀌지 않아야 한다."""
        self.output.write_bytes(b"keep report")
        with patch.object(diagnostics, "remove_stems_from_file") as remove:
            self.assertEqual(diagnostics.run_stem_self_test(self.source, self.output), 2)
            self.assertEqual(diagnostics.run_stem_self_test(self.source, self.source), 2)
            remove.assert_not_called()
        self.assertEqual(self.output.read_bytes(), b"keep report")
        self.assertEqual(self.source.read_bytes(), b"original source")

    def test_invalid_ranges_do_not_start_or_create_report(self) -> None:
        """유한하지 않은 시간·취소율과 허용 범위 밖 입력은 진단 시작 전에 거부한다."""
        for seconds, cancel in ((1, None), (1201, None), (float("nan"), None),
                                (0, 0), (0, 100), (0, float("inf"))):
            with self.subTest(seconds=seconds, cancel=cancel):
                self.assertEqual(diagnostics.run_stem_self_test(self.source, self.output, seconds, cancel), 2)
                self.assertFalse(self.output.exists())

    def test_missing_cache_does_not_download_or_start_inference(self) -> None:
        """캐시가 없는 진단은 모델 다운로드를 시도하지 않고 필요한 조건을 기록한다."""
        with patch.object(diagnostics, "separator_runtime_status", return_value={"available": True, "model_cached": False}), \
             patch.object(diagnostics, "remove_stems_from_file") as remove:
            self.assertEqual(diagnostics.run_stem_self_test(self.source, self.output), 2)
            remove.assert_not_called()
        self.assertEqual(self.report()["status"], "cached_model_required")

    def test_error_message_never_leaks_private_paths(self) -> None:
        """실패 예외 메시지의 개인 경로를 기록하지 않고 오류 타입과 정리 여부만 남긴다."""
        with patch.object(diagnostics, "remove_stems_from_file", side_effect=RuntimeError(str(self.source))):
            self.assertEqual(diagnostics.run_stem_self_test(self.source, self.output), 1)
        report = self.report()
        self.assertEqual(report["error_type"], "RuntimeError")
        self.assertFalse(report["ok"])
        self.assertTrue(report["temporary_audio_cleaned"])
        self.assertNotIn("private-song", self.output.read_text(encoding="utf-8"))

    def test_progress_regression_cannot_pass(self) -> None:
        """유효한 WAV가 만들어져도 진행률이 역행하면 진단이 실패해야 한다."""
        def regress(*args, **kwargs):
            """초기 진행을 먼저 보내 정상 경로의 0퍼센트가 역행하도록 만든다."""
            kwargs["progress"](50, "private")
            return fake_removal(*args, **kwargs)
        with patch.object(diagnostics, "remove_stems_from_file", side_effect=regress):
            self.assertEqual(diagnostics.run_stem_self_test(self.source, self.output), 1)
        self.assertFalse(self.report()["progress_monotonic"])

    def test_truncated_wav_output_cannot_pass(self) -> None:
        """헤더는 정상이지만 실제 PCM이 잘린 결과는 실패하고 임시 출력도 정리한다."""
        def truncate(*args, **kwargs):
            """정상 가상 결과의 마지막 PCM 프레임을 제거한다."""
            result = fake_removal(*args, **kwargs)
            destination = Path(args[1])
            with destination.open("r+b") as stream:
                stream.truncate(destination.stat().st_size - 4)
            return result
        with patch.object(diagnostics, "remove_stems_from_file", side_effect=truncate):
            self.assertEqual(diagnostics.run_stem_self_test(self.source, self.output), 1)
        self.assertEqual(self.report()["status"], "failed")
        self.assertTrue(self.report()["temporary_audio_cleaned"])

    def test_unrequested_cancellation_is_not_success(self) -> None:
        """정상 완료 진단에서 뜻하지 않은 취소가 나면 성공으로 표시하지 않는다."""
        with patch.object(diagnostics, "remove_stems_from_file", side_effect=StemRemovalCancelled("cancel")):
            self.assertEqual(diagnostics.run_stem_self_test(self.source, self.output), 1)
        self.assertFalse(self.report()["ok"])

    def test_cli_options_route_without_gui(self) -> None:
        """실행 파일 진입점에서 진단 인수를 전달할 때 Tk 창을 만들지 않아야 한다."""
        import app
        arguments = ["app.py", "--stem-self-test-source", str(self.source),
                     "--stem-self-test-output", str(self.output), "--stem-self-test-seconds", "3"]
        with patch.object(sys, "argv", arguments), patch.object(app.tk, "Tk") as window, \
             patch.object(diagnostics, "remove_stems_from_file", side_effect=fake_removal):
            self.assertEqual(app.main(), 0)
            window.assert_not_called()
        self.assertEqual(self.report()["requested_seconds"], 3)

    def test_incomplete_cli_options_do_not_open_gui(self) -> None:
        """필수 인수가 빠진 진단 호출도 GUI로 잘못 전환하지 않는다."""
        import app
        with patch.object(sys, "argv", ["app.py", "--stem-self-test-source"]), \
             patch.object(app.tk, "Tk") as window, patch.object(sys, "stderr"):
            self.assertEqual(app.main(), 2)
            window.assert_not_called()


if __name__ == "__main__":
    unittest.main()
