"""창을 표시하지 않고 코드·스케일 사전의 선택·건반·언어·최소 크기를 검증한다."""

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

from app import COLORS, ToneMatchApp, _self_test_harmony_reference  # noqa: E402
from harmony_reference import chord_options, scale_options  # noqa: E402
from i18n import LANGUAGE_LABELS, tr  # noqa: E402


@contextmanager
def hidden_harmony_application(data_root: Path):
    """장치 접근·창 표시·예약 작업 없이 960×600 앱의 사전 탭을 준비한다."""
    root = tk.Tk()
    root.withdraw()
    try:
        with (
            patch.object(ToneMatchApp, "_load_settings"),
            patch.object(ToneMatchApp, "_save_settings"),
            patch.object(ToneMatchApp, "_refresh_capture_devices"),
            patch.object(root, "after"),
            patch("app._runtime_data_root", return_value=data_root),
            patch("app._window_work_area", return_value=(0, 0, 992, 664)),
        ):
            application = ToneMatchApp(root)
            application.workspace_notebook.select(application.harmony_tab)
            root.update_idletasks()
            yield root, application
    finally:
        root.update_idletasks()
        root.destroy()


def choose_category(application: ToneMatchApp, category: str) -> None:
    """사용자 콤보 선택과 동일한 경로로 사전 분류를 전환한다."""
    application.harmony_category_combo.current(("chord", "scale", "diatonic").index(category))
    application._change_harmony_category()


def choose_type(application: ToneMatchApp, key: str) -> None:
    """화음 또는 음계의 영속 키에 해당하는 표시 항목을 선택한다."""
    keys = [item["key"] for item in application.harmony_options]
    application.harmony_type_combo.current(keys.index(key))
    application._change_harmony_type()


def active_keyboard_keys(application: ToneMatchApp) -> set[int]:
    """건반 캔버스에서 실제 색칠된 음정 위치를 읽어 이론 자료와 비교한다."""
    canvas = application.harmony_keyboard
    return {
        int(tag.removeprefix("key_"))
        for item in canvas.find_withtag("active")
        for tag in canvas.gettags(item)
        if tag.startswith("key_")
    }


class HarmonyReferenceUiTests(unittest.TestCase):
    """이론 사전을 분석 결과와 분리하고 모든 선택 조합을 유효한 건반으로 표시한다."""

    def test_frozen_reference_self_test_computes_intervals_spelling_and_harmony(self) -> None:
        """EXE 자체 진단이 소스 존재 확인을 넘어 사전 계산과 종류 수를 검증해야 한다."""
        result = _self_test_harmony_reference()
        self.assertTrue(result["ok"])
        self.assertEqual(result["chord_type_count"], len(chord_options()))
        self.assertEqual(result["scale_type_count"], len(scale_options()))
        self.assertEqual(result["diatonic_scale_count"], 2)
        self.assertEqual(result["root_count"], 12)
        self.assertTrue(result["compound_intervals_ok"])
        self.assertTrue(result["enharmonic_spelling_ok"])
        self.assertTrue(result["pentatonic_ok"])
        self.assertTrue(result["diatonic_rows_ok"])
        self.assertFalse(result["automatic_audio_key_detection"])

    def test_guide_is_available_without_audio_and_does_not_start_analysis(self) -> None:
        """파일이 없어도 사전이 열리며 선택 변경은 음원 분석이나 장치 캡처를 시작하지 않는다."""
        with tempfile.TemporaryDirectory() as temporary:
            with hidden_harmony_application(Path(temporary)) as (root, application):
                self.assertIsNone(application.result)
                self.assertEqual(application.file_var.get(), "")
                self.assertEqual(application.harmony_tab.master, application.workspace_notebook)
                self.assertNotIn(str(application.harmony_tab), application.notebook.tabs())
                self.assertEqual(application.workspace_notebook.tab(application.harmony_tab, "text"), tr("ui.harmony_tab", "ko"))
                with patch("app.analyze_file") as analyze, patch("app.threading.Thread") as thread:
                    for category in ("chord", "scale", "diatonic"):
                        choose_category(application, category)
                    analyze.assert_not_called()
                    thread.assert_not_called()
                self.assertIsNone(application.result)
                self.assertEqual(root.state(), "withdrawn")

    def test_every_root_chord_and_scale_draws_exact_theoretical_intervals(self) -> None:
        """12개 기준음과 모든 코드·스케일의 색칠 음수가 구성음과 같고 상위 확장음도 보존된다."""
        with tempfile.TemporaryDirectory() as temporary:
            with hidden_harmony_application(Path(temporary)) as (_root, application):
                for category, provider in (("chord", chord_options), ("scale", scale_options)):
                    choose_category(application, category)
                    for root_pc in range(12):
                        application.harmony_root_combo.current(root_pc)
                        application._change_harmony_root()
                        for option in provider():
                            with self.subTest(category=category, root=root_pc, key=option["key"]):
                                choose_type(application, option["key"])
                                reference = application.harmony_keyboard_reference
                                self.assertEqual(active_keyboard_keys(application), {root_pc + interval for interval in reference["intervals"]})
                                root_items = application.harmony_keyboard.find_withtag("root")
                                self.assertEqual(len(root_items), 1)
                                self.assertEqual(application.harmony_keyboard.itemcget(root_items[0], "fill"), COLORS["accent"])
                                self.assertEqual(len(active_keyboard_keys(application)), len(reference["note_names"]))
                choose_category(application, "chord")
                choose_type(application, "13")
                self.assertIn(32, active_keyboard_keys(application))
                choose_category(application, "scale")
                choose_type(application, "minor_pentatonic")
                self.assertEqual(len(active_keyboard_keys(application)), 5)

    def test_diatonic_rows_select_triad_or_seventh_and_preserve_spelling(self) -> None:
        """장조·자연단조의 일곱 행과 7화음 전환 및 이명동음 철자를 실제 위젯에서 검사한다."""
        with tempfile.TemporaryDirectory() as temporary:
            with hidden_harmony_application(Path(temporary)) as (_root, application):
                choose_category(application, "diatonic")
                self.assertEqual(len(application.harmony_diatonic_tree.get_children()), 7)
                self.assertEqual(application.harmony_diatonic_tree.item("4", "values"), ("V", "G", "G7"))
                application.harmony_diatonic_tree.selection_set("4")
                application._select_harmony_degree()
                self.assertEqual(application.harmony_keyboard_reference["symbol"], "G")
                application.harmony_size_combo.current(1)
                application._change_harmony_size()
                self.assertEqual(application.harmony_keyboard_reference["symbol"], "G7")
                self.assertEqual(len(active_keyboard_keys(application)), 4)
                choose_type(application, "natural_minor")
                self.assertEqual(application.harmony_diatonic_tree.item("4", "values"), ("v", "Gm", "Gm7"))
                application.harmony_root_combo.current(1)
                application._change_harmony_root()
                choose_type(application, "major")
                application.harmony_diatonic_tree.selection_set("6")
                application._select_harmony_degree()
                self.assertEqual(application.harmony_keyboard_reference["root_name"], "B♯")
                self.assertEqual(application.harmony_keyboard_reference["note_names"], ["B♯", "D♯", "F♯", "A♯"])

    def test_language_rebuild_preserves_root_category_choices_and_selected_row(self) -> None:
        """한영 전환 뒤에도 사전 탭·기준음·종류·도수·7화음 선택이 그대로 유지된다."""
        with tempfile.TemporaryDirectory() as temporary:
            with hidden_harmony_application(Path(temporary)) as (root, application):
                application.harmony_root_combo.current(9)
                application._change_harmony_root()
                choose_type(application, "min11")
                choose_category(application, "scale")
                choose_type(application, "minor_pentatonic")
                choose_category(application, "diatonic")
                choose_type(application, "natural_minor")
                application.harmony_diatonic_tree.selection_set("2")
                application._select_harmony_degree()
                application.harmony_size_combo.current(1)
                application._change_harmony_size()
                for language in ("en", "ko"):
                    application.language_var.set(LANGUAGE_LABELS[language])
                    application._change_language()
                    root.update_idletasks()
                    self.assertEqual(application.workspace_notebook.select(), str(application.harmony_tab))
                    self.assertEqual(application.harmony_root_pc, 9)
                    self.assertEqual(application.harmony_choices, {"chord": "min11", "scale": "minor_pentatonic", "diatonic": "natural_minor"})
                    self.assertEqual(application.harmony_degree_index, 2)
                    self.assertEqual(application.harmony_chord_size, "seventh")
                    self.assertEqual(application.harmony_keyboard_reference["symbol"], "Cmaj7")
                    self.assertEqual(application.harmony_category_combo.get(), tr("ui.harmony_diatonic", language))
                    self.assertEqual(root.state(), "withdrawn")

    def test_small_window_keyboard_controls_and_table_fit_with_vertical_scroll(self) -> None:
        """최소 창에서 한영 컨트롤·건반·표가 가로로 넘치지 않고 긴 설명은 스크롤 가능하다."""
        with tempfile.TemporaryDirectory() as temporary:
            with hidden_harmony_application(Path(temporary)) as (root, application):
                for language in ("ko", "en"):
                    application.language_var.set(LANGUAGE_LABELS[language])
                    application._change_language()
                    choose_category(application, "diatonic")
                    root.update_idletasks()
                    self.assertEqual((root.winfo_width(), root.winfo_height()), (960, 600))
                    for widget in (application.harmony_canvas, application.harmony_root_combo, application.harmony_category_combo,
                                   application.harmony_type_combo, application.harmony_keyboard, application.harmony_diatonic_tree):
                        with self.subTest(language=language, widget=str(widget)):
                            x = widget.winfo_rootx() - root.winfo_rootx()
                            self.assertGreaterEqual(x, 0)
                            self.assertLessEqual(x + widget.winfo_width(), 960)
                    bounds = application.harmony_canvas.bbox(application.harmony_scroll_window)
                    self.assertGreater(bounds[3], application.harmony_canvas.winfo_height())
                    application.harmony_canvas.yview_moveto(0)
                    self.assertEqual(application._scroll_harmony_reference(Mock(delta=-120)), "break")
                    self.assertGreater(application.harmony_canvas.yview()[0], 0)
                    self.assertTrue(application.harmony_type_combo.bind("<MouseWheel>"))
                    self.assertEqual(root.state(), "withdrawn")


if __name__ == "__main__":
    unittest.main()
