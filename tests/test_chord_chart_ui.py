"""숨겨진 실제 Tk 위젯으로 16마디 페이지·안전 표시·수동 격자·고배율 배치를 검증한다."""

from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import fields
import json
from pathlib import Path
import sys
import tempfile
import tkinter as tk
import unittest
from unittest.mock import Mock, patch


MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from app import ToneMatchApp, _self_test_chord_chart  # noqa: E402
from engine import TEMPLATES, ToneFeatures, relocalize_result, save_json  # noqa: E402
from i18n import LANGUAGE_LABELS, tr  # noqa: E402


def chart_result(source: str = "guitar_stem") -> dict:
    """실제 음원을 포함하지 않는 긴 합성 코드열과 완전한 화면용 결과를 만든다."""
    events = []
    for index in range(101):
        events.append({
            "start_seconds": index * 0.4, "end_seconds": (index + 1) * 0.4,
            "symbol": "Cmaj7#11/E" if index % 3 else "G6/9",
            "chord_type": "major", "confidence": 0.7, "pitch_classes": [0, 4, 7],
            "candidate_shapes": [{"label": "Legacy shape", "frets_low_e_to_high_e": [8, 10, 10, 9, 8, 8]}],
        })
    events[2].update(chord_type="unknown", symbol="SHOULD_NOT_SHOW")
    values = {field.name: 0.5 for field in fields(ToneFeatures)}
    values["bpm"] = 120
    result = {
        "features": values, "source": {"duration_seconds": 75.0, "start_seconds": 30.0},
        "input_profile": {"pickup": "unknown", "mix_mode": "isolated", "output_mode": "frfr"},
        "recipes": [{"template_id": template["id"], "match_percent": 80} for template in TEMPLATES[:3]],
        "chord_voicing": {"analysis_source": source, "source_start_seconds": 30.0, "events": events},
    }
    return relocalize_result(result, "ko")


@contextmanager
def hidden_chart_application(data_root: Path, size: tuple[int, int] = (960, 600), scaling: float = 1.6):
    """창 표시·장치 접근·예약 작업을 막고 실제 최소 창 크기와 DPI를 적용한다."""
    root = tk.Tk()
    root.withdraw()
    original_scaling = float(root.tk.call("tk", "scaling"))
    try:
        root.tk.call("tk", "scaling", scaling)
        with (
            patch.object(ToneMatchApp, "_load_settings"),
            patch.object(ToneMatchApp, "_save_settings"),
            patch.object(ToneMatchApp, "_refresh_capture_devices"),
            patch.object(root, "after"),
            patch("app._runtime_data_root", return_value=data_root),
            patch("app._window_work_area", return_value=(0, 0, size[0] + 32, size[1] + 64)),
        ):
            application = ToneMatchApp(root)
            application.notebook.select(application.voicing_tab)
            root.update_idletasks()
            yield root, application
    finally:
        root.tk.call("tk", "scaling", original_scaling)
        root.destroy()


def chart_text(application: ToneMatchApp, tag: str = "all") -> list[str]:
    """실제 캔버스 텍스트를 태그별로 읽어 표시된 코드와 출처를 검사한다."""
    canvas = application.chart_canvas
    return [canvas.itemcget(item, "text") for item in canvas.find_withtag(tag) if canvas.type(item) == "text"]


def widget_offset(widget: tk.Misc, root: tk.Tk) -> tuple[int, int]:
    """숨긴 Canvas의 미생성 네이티브 창 좌표 대신 실제 부모 배치 좌표를 누적한다."""
    x = y = 0
    while widget is not root:
        x += widget.winfo_x()
        y += widget.winfo_y()
        widget = widget.nametowidget(widget.winfo_parent())
    return x, y


class ChordChartUiTests(unittest.TestCase):
    """코드표를 분석 근거와 혼동하지 않으면서 모든 변화와 사용자 설정을 보존한다."""

    def test_frozen_self_test_checks_chart_and_shape_semantics(self) -> None:
        """배포 자체 진단은 페이지·미확정·믹스 안전 표시·이론 운지를 실제 계산한다."""
        result = _self_test_chord_chart()
        self.assertTrue(result["ok"])
        self.assertEqual((result["bar_count"], result["page_count"]), (20, 2))
        for key in ("pagination_ok", "changes_and_unknowns_ok", "original_mix_guard_ok", "theoretical_shapes_ok"):
            self.assertTrue(result[key])
        self.assertFalse(result["automatic_downbeat"])

    def test_pages_preserve_all_changes_unknowns_and_details(self) -> None:
        """16마디 페이지가 짧은 변화·빈 구간을 생략하지 않고 전체 근거로 연결된다."""
        with tempfile.TemporaryDirectory() as temporary:
            with hidden_chart_application(Path(temporary)) as (root, application):
                result = chart_result()
                application._show_result(result)
                application.notebook.select(application.voicing_tab)
                root.update_idletasks()
                self.assertEqual([len(page["bars"]) for page in application.chart_data["pages"]], [16, 16, 6])
                self.assertEqual(application.chart_data["event_count"], 101)
                self.assertEqual(len(application.chart_canvas.find_withtag("chart_bar")), 16)
                self.assertEqual(len(chart_text(application, "chord_label")), sum(len(bar["segments"]) for bar in application.chart_data["pages"][0]["bars"]))
                self.assertIn("?", chart_text(application, "unknown_chord"))
                self.assertNotIn("SHOULD_NOT_SHOW", " ".join(chart_text(application)))
                self.assertTrue(application.chart_canvas.find_withtag("fret_diagram"))
                application._show_chart_bar_details(6)
                self.assertEqual(application.voicing_views.select(), str(application.voicing_details_tab))
                self.assertIn("chart_event_6", application.voicing_text.mark_names())
                self.assertEqual(application.voicing_text.cget("state"), "disabled")
                application._next_chart_page()
                self.assertIn("17–32", application.chart_page_var.get())
                application._next_chart_page()
                application._next_chart_page()
                self.assertEqual(application.chart_page_index, 2)
                self.assertEqual(len(application.chart_canvas.find_withtag("chart_bar")), 6)
                application._previous_chart_page()
                self.assertEqual(application.chart_page_index, 1)
                self.assertEqual(root.state(), "withdrawn")

    def test_original_mix_hides_shapes_and_bass_but_preserves_six_nine(self) -> None:
        """믹스의 기타 운지·역위를 숨기되 6/9 화음 기호와 입력 자료는 유지한다."""
        with tempfile.TemporaryDirectory() as temporary:
            with hidden_chart_application(Path(temporary)) as (root, application):
                result = chart_result("original_mix")
                original = deepcopy(result["chord_voicing"])
                application._show_result(result)
                for language in ("en", "ko"):
                    application.language_var.set(LANGUAGE_LABELS[language])
                    application._change_language()
                    root.update_idletasks()
                    text = chart_text(application)
                    self.assertIn("G6/9", text)
                    self.assertIn("Cmaj7#11", text)
                    self.assertNotIn("Cmaj7#11/E", text)
                    self.assertFalse(application.chart_canvas.find_withtag("fret_diagram"))
                    self.assertIn(tr("ui.chart_source_original_mix", language), text)
                    self.assertEqual(application.result["chord_voicing"], original)

    def test_manual_settings_reject_invalid_input_without_changing_chart(self) -> None:
        """잘못된 격자는 이전 설정으로 돌리고 유효한 보정은 재분석 없이 JSON에 저장한다."""
        with tempfile.TemporaryDirectory() as temporary:
            with hidden_chart_application(Path(temporary)) as (_root, application):
                application._show_result(chart_result())
                application.chart_bpm_var.set("90")
                application.chart_meter_var.set("3")
                application.chart_downbeat_var.set("1.5")
                with patch("app.analyze_file") as analyze:
                    application._apply_chart_settings()
                    analyze.assert_not_called()
                expected = {"bpm": 90.0, "beats_per_bar": 3, "first_downbeat_seconds": 1.5}
                self.assertEqual(application.result["chord_chart_settings"], expected)
                previous = application.chart_data
                for field, value in (("bpm", "nan"), ("bpm", "0"), ("meter", "3.5"), ("meter", "13"), ("downbeat", "inf"), ("downbeat", "99999999")):
                    with self.subTest(field=field, value=value):
                        getattr(application, f"chart_{field}_var").set(value)
                        application._apply_chart_settings()
                        self.assertIs(application.chart_data, previous)
                        self.assertEqual(application.chart_settings, expected)
                        self.assertEqual(application.chart_notice_var.get(), tr("ui.chart_invalid", "ko"))
                        self.assertEqual(application.chart_bpm_var.get(), "90")
                        self.assertEqual(application.chart_meter_var.get(), "3")
                        self.assertEqual(application.chart_downbeat_var.get(), "1.5")
                destination = Path(temporary) / "result.json"
                save_json(application.result, destination)
                self.assertEqual(json.loads(destination.read_text(encoding="utf-8"))["chord_chart_settings"], expected)

    def test_language_rebuild_preserves_chart_page_settings_and_selected_view(self) -> None:
        """언어 변경 뒤 두 번째 페이지·보정 격자·근거 탭 선택을 모두 보존한다."""
        with tempfile.TemporaryDirectory() as temporary:
            with hidden_chart_application(Path(temporary)) as (root, application):
                application._show_result(chart_result())
                application.chart_bpm_var.set("110")
                application.chart_meter_var.set("6")
                application.chart_downbeat_var.set("-0.5")
                application._apply_chart_settings()
                application._next_chart_page()
                application.notebook.select(application.voicing_tab)
                application.voicing_views.select(application.voicing_details_tab)
                settings = deepcopy(application.chart_settings)
                for language in ("en", "ko"):
                    application.language_var.set(LANGUAGE_LABELS[language])
                    application._change_language()
                    root.update_idletasks()
                    self.assertEqual(application.chart_page_index, 1)
                    self.assertEqual(application.chart_settings, settings)
                    self.assertEqual(application.result["chord_chart_settings"], settings)
                    self.assertEqual(application.notebook.select(), str(application.voicing_tab))
                    self.assertEqual(application.voicing_views.select(), str(application.voicing_details_tab))
                    self.assertEqual(root.state(), "withdrawn")

    def test_saved_settings_are_normalized_or_fall_back_safely(self) -> None:
        """문자열 숫자 설정을 정규화하고 손상된 저장 설정은 초기값으로 복구한다."""
        with tempfile.TemporaryDirectory() as temporary:
            with hidden_chart_application(Path(temporary)) as (_root, application):
                for saved in ({"bpm": "125", "beats_per_bar": "3", "first_downbeat_seconds": "1"}, ["invalid"], {"bpm": "nan"}):
                    result = chart_result()
                    result["chord_chart_settings"] = saved
                    application._show_result(result)
                    self.assertIsInstance(application.chart_settings["bpm"], float)
                    self.assertIsInstance(application.chart_settings["beats_per_bar"], int)
                    self.assertEqual(application.chart_bpm_var.get(), "125" if isinstance(saved, dict) and saved["bpm"] == "125" else "120")

    def test_legacy_diagram_uses_actual_fret_range_when_base_is_missing(self) -> None:
        """구형 운지에도 실제 최소 프렛을 표기하여 높은 위치 점이 그림 밖으로 나가지 않는다."""
        with tempfile.TemporaryDirectory() as temporary:
            with hidden_chart_application(Path(temporary)) as (_root, application):
                canvas = application.chart_canvas
                canvas.delete("all")
                application._draw_chart_shape({"frets_low_e_to_high_e": [8, 10, 10, 9, 8, 8]}, 30, 30, "shape")
                self.assertIn("8", chart_text(application, "shape"))
                dots = [item for item in canvas.find_withtag("shape") if canvas.type(item) == "oval"]
                self.assertEqual(len(dots), 6)
                for dot in dots:
                    self.assertGreaterEqual(canvas.bbox(dot)[1], 30)
                    self.assertLessEqual(canvas.bbox(dot)[3], 74)

    def test_dense_chart_fits_window_and_items_do_not_overlap_at_high_dpi(self) -> None:
        """최소·중간 창의 120·150% 배율에서 긴 코드명·박·운지를 겹침 없이 스크롤한다."""
        with tempfile.TemporaryDirectory() as temporary:
            for size in ((960, 600), (1080, 720)):
                for scaling in (1.6, 2.0):
                    with hidden_chart_application(Path(temporary), size, scaling) as (root, application):
                        application._show_result(chart_result())
                        application.notebook.select(application.voicing_tab)
                        for language in ("ko", "en"):
                            with self.subTest(size=size, scaling=scaling, language=language):
                                application.language_var.set(LANGUAGE_LABELS[language])
                                application._change_language()
                                root.update()
                                self.assertEqual((root.winfo_width(), root.winfo_height()), size)
                                canvas = application.chart_canvas
                                self.assertGreaterEqual(canvas.winfo_height(), 80)
                                for widget in (canvas, application.chart_previous, application.chart_next, application.chart_settings_button):
                                    x, y = widget_offset(widget, root)
                                    self.assertGreaterEqual(x, 0)
                                    self.assertGreaterEqual(y, 0)
                                    self.assertLessEqual(x + widget.winfo_width(), size[0])
                                    self.assertLessEqual(y + widget.winfo_height(), size[1])
                                for rectangle in canvas.find_withtag("chart_bar"):
                                    left, top, right, bottom = canvas.coords(rectangle)
                                    tag = next(tag for tag in canvas.gettags(rectangle) if tag.startswith("chart_bar_"))
                                    previous_bottom = top
                                    for item in canvas.find_withtag(tag):
                                        if item == rectangle:
                                            continue
                                        box = canvas.bbox(item)
                                        self.assertGreaterEqual(box[0], left)
                                        self.assertLessEqual(box[2], right)
                                        self.assertGreaterEqual(box[1], top)
                                        self.assertLessEqual(box[3], bottom)
                                        if canvas.type(item) == "text" and "fret_diagram" not in canvas.gettags(item):
                                            self.assertGreaterEqual(box[1], previous_bottom)
                                            previous_bottom = box[3]
                                canvas.yview_moveto(0)
                                self.assertEqual(application._scroll_chart(Mock(delta=-120)), "break")
                                self.assertGreater(canvas.yview()[0], 0)
                                application._toggle_chart_settings()
                                root.update()
                                self.assertGreaterEqual(canvas.winfo_height(), 80)
                                for widget in application.chart_controls.winfo_children():
                                    x, y = widget_offset(widget, root)
                                    self.assertGreaterEqual(x, 0)
                                    self.assertGreaterEqual(y, 0)
                                    self.assertLessEqual(x + widget.winfo_width(), size[0])
                                    self.assertLessEqual(y + widget.winfo_height(), size[1])
                                application._toggle_chart_settings()
                                root.update()
                                application.notebook.select(0)
                                root.update()
                                self.assertTrue(application.result_title_label.grid_info())
                                self.assertTrue(application.result_summary_label.grid_info())
                                application.notebook.select(application.voicing_tab)
                                root.update()
                                self.assertEqual(root.state(), "withdrawn")


if __name__ == "__main__":
    unittest.main()
