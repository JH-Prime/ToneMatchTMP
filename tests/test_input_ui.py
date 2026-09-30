"""참고용 URL UI 제거와 허용된 로컬·녹음 입력의 분석 연결을 검증한다."""

from __future__ import annotations

import sys
import tempfile
import tkinter as tk
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import Mock, patch


MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from app import INPUT_METHODS, ToneMatchApp, _self_test_voicing  # noqa: E402
from i18n import LANGUAGE_LABELS, tr  # noqa: E402


@contextmanager
def hidden_input_application(data_root: Path):
    """실제 창·장치 검사·예약 작업을 사용하지 않고 입력 화면을 검사한다."""
    root = tk.Tk()
    root.withdraw()
    try:
        with (
            patch.object(ToneMatchApp, "_load_settings"),
            patch.object(ToneMatchApp, "_save_settings"),
            patch.object(ToneMatchApp, "_refresh_capture_devices"),
            patch.object(root, "after"),
            patch("app._runtime_data_root", return_value=data_root),
        ):
            application = ToneMatchApp(root)
            application.hardware_probe_active = False
            root.update_idletasks()
            yield root, application
    finally:
        root.destroy()


def widget_texts(widget: tk.Misc) -> list[str]:
    """하위 위젯의 표시 문자열을 재귀 수집해 제거된 컨트롤을 확인한다."""
    result = []
    if "text" in widget.keys():
        result.append(str(widget.cget("text")))
    for child in widget.winfo_children():
        result.extend(widget_texts(child))
    return result


class InputUiTests(unittest.TestCase):
    """두 언어 모두 실제 지원 입력만 노출하고 URL 없이 분석 요청을 만든다."""

    def test_frozen_chord_self_test_checks_evidence_without_accuracy_claims(self) -> None:
        """EXE 진단은 확장화음과 대안·단음 거부를 확인하되 실제 곡 정확도를 주장하지 않는다."""
        result = _self_test_voicing()
        self.assertTrue(result["ok"])
        self.assertEqual(result["template_count"], 20)
        self.assertTrue(result["single_note_rejected"])
        self.assertFalse(result["real_song_accuracy_measured"])

    def test_reference_only_url_controls_are_absent_in_both_languages(self) -> None:
        """언어를 바꿔도 URL 칸·브라우저 버튼·YouTube 재생 유도가 재생성되지 않는다."""
        with tempfile.TemporaryDirectory() as temporary:
            with hidden_input_application(Path(temporary)) as (root, application):
                for language in ("ko", "en"):
                    with self.subTest(language=language):
                        application.language_var.set(LANGUAGE_LABELS[language])
                        application._change_language()
                        root.update_idletasks()
                        labels = "\n".join(widget_texts(root))
                        self.assertNotIn("YouTube", labels)
                        self.assertNotIn("Open in browser", labels)
                        self.assertNotIn("브라우저로 열기", labels)
                        self.assertFalse(hasattr(application, "url_var"))
                        self.assertFalse(hasattr(application, "_open_reference"))
                        self.assertEqual(INPUT_METHODS, ("local", "record"))
                        self.assertEqual(len(application.input_combo.cget("values")), 2)
                        self.assertIn(tr("ui.tip", language), labels)
                        self.assertNotIn("Experimental", application.notebook.tab(application.voicing_tab, "text"))
                        self.assertNotIn("실험", application.notebook.tab(application.voicing_tab, "text"))

    def test_analysis_dispatch_does_not_require_or_forward_url_state(self) -> None:
        """URL 상태 없이 분석이 시작되고 과거 상태가 남아도 작업 요청에 전달하지 않는다."""
        with tempfile.TemporaryDirectory() as temporary:
            with hidden_input_application(Path(temporary)) as (_root, application):
                for legacy_state in (False, True):
                    with self.subTest(legacy_state=legacy_state):
                        if legacy_state:
                            application.url_var = Mock()
                            application.url_var.get.return_value = "https://example.invalid/legacy"
                        application.worker = None
                        with (
                            patch.object(application, "_parse_inputs", return_value=("permitted.wav", 3.0, 8.0)),
                            patch("app.threading.Thread") as thread,
                        ):
                            application._start_analysis()
                        request = thread.call_args.kwargs["args"][0]
                        self.assertEqual(request["source"], "permitted.wav")
                        self.assertEqual(request["start_seconds"], 3.0)
                        self.assertEqual(request["end_seconds"], 8.0)
                        self.assertNotIn("reference_url", request)
                        thread.return_value.start.assert_called_once()
                        if legacy_state:
                            application.url_var.get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
