"""개발자 옵션의 블록 매핑, 번들 소스, 한글 함수 설명을 검증한다."""

from __future__ import annotations

import ast
import re
import subprocess
import sys
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np


MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

import catalog  # noqa: E402
import debug_info  # noqa: E402
from app import ToneMatchApp, _center_window  # noqa: E402
from i18n import LANGUAGE_LABELS, tr  # noqa: E402
from reference_compare import build_reference_profile  # noqa: E402
from spectrum import analyze_spectrum_frame  # noqa: E402


class DeveloperModeTests(unittest.TestCase):
    """개발자 화면이 약속한 코드와 설명을 실제로 제공하는지 확인한다."""

    def test_version_and_latest_changelog_match(self) -> None:
        """앱 버전은 두 자리 패치 규칙이며 최신 변경 기록과 같아야 한다."""
        self.assertRegex(catalog.APP_VERSION, r"^0\.0\.\d{2}$")
        self.assertEqual(catalog.CHANGELOG[0]["version"], catalog.APP_VERSION)
        self.assertTrue(catalog.CHANGELOG[0]["changes"])

    def test_pipeline_order_and_source_links_are_complete(self) -> None:
        """블록 번호가 연속이고 각 클릭 대상에서 실제 코드가 추출되는지 검사한다."""
        blocks = debug_info.PIPELINE_BLOCKS
        self.assertEqual([block["order"] for block in blocks], list(range(1, len(blocks) + 1)))
        self.assertEqual(blocks[0]["id"], "boot")
        self.assertEqual(blocks[-1]["id"], "export")
        for block in blocks:
            code = debug_info.code_for_block(block["id"])
            self.assertIn("def ", code, block["id"])
            self.assertNotIn("소스 위치를 찾지 못했습니다", code, block["id"])

    def test_every_function_has_korean_docstring(self) -> None:
        """배포 소스의 모든 함수가 개발자에게 보이는 한글 설명을 갖는지 검사한다."""
        korean = re.compile(r"[가-힣]")
        source_files = (
            "app.py",
            "catalog.py",
            "debug_info.py",
            "devices.py",
            "engine.py",
            "i18n.py",
            "recorder.py",
            "reference_compare.py",
            "report.py",
            "separator.py",
            "spectrum.py",
            "voicing.py",
            "tests/test_developer_mode.py",
            "tests/test_engine.py",
            "tests/test_recorder.py",
            "tests/test_reference_compare.py",
            "tests/test_separator.py",
            "tests/test_spectrum.py",
            "tests/test_voicing.py",
            "tools/collect_licenses.py",
            "tools/generate_function_reference.py",
            "tools/write_manifest.py",
        )
        missing: list[str] = []
        non_korean: list[str] = []
        for file_name in source_files:
            path = MODULE_DIR / file_name
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                description = ast.get_docstring(node)
                label = f"{file_name}:{node.lineno}:{node.name}"
                if not description:
                    missing.append(label)
                elif not korean.search(description):
                    non_korean.append(label)
        self.assertEqual(missing, [], f"함수 설명 누락: {missing}")
        self.assertEqual(non_korean, [], f"한글 함수 설명 누락: {non_korean}")

    def test_progress_maps_to_sequence_blocks(self) -> None:
        """대표 진행률이 입력부터 결과까지 순서대로 해당 블록을 가리키는지 확인한다."""
        checkpoints = [(2, "input"), (10, "decode"), (36, "separation"), (72, "features"), (82, "voicing"), (87, "correction"), (90, "matching"), (94, "recipe"), (97, "result")]
        for progress, expected in checkpoints:
            self.assertEqual(debug_info.block_for_progress(progress), expected)

    def test_windowed_import_repairs_missing_standard_streams(self) -> None:
        """콘솔 없는 실행 환경도 출력 가능한 스트림을 만들고 기존 스트림은 유지해야 한다."""
        script = "\n".join((
            "import importlib, sys",
            "sys.stdout = None",
            "sys.stderr = None",
            "import app",
            "assert sys.stdout is not None and sys.stderr is not None",
            "assert sys.stdout.write('model download output') >= 0",
            "assert sys.stderr.write('model download progress') >= 0",
            "sys.stdout.flush()",
            "sys.stderr.flush()",
            "old_stdout, old_stderr = sys.stdout, sys.stderr",
            "importlib.reload(app)",
            "assert sys.stdout is old_stdout and sys.stderr is old_stderr",
        ))
        completed = subprocess.run(
            [sys.executable, "-W", "error", "-c", script],
            cwd=MODULE_DIR,
            capture_output=True,
            text=True,
            timeout=90,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_analysis_progress_accepts_floats_without_regressing(self) -> None:
        """실수 진행률은 표시되며 지연·잘못된 콜백에도 뒤로 가거나 범위를 벗어나지 않아야 한다."""
        root = tk.Tk()
        root.withdraw()
        try:
            application = ToneMatchApp(root)
            root.update_idletasks()
            application.language = "ko"
            application.analysis_started_at = 100.0
            with patch("app.time.monotonic", return_value=165.25), patch.object(root, "after"):
                application.events.put(("progress", 23.75, "모델 다운로드"))
                application._drain_events()
                self.assertEqual(application.analysis_progress_percent, 23.75)
                self.assertEqual(application.progress_var.get(), 23.75)
                self.assertIn("23.8%", application.progress_detail_var.get())
                self.assertIn("01:05", application.progress_detail_var.get())
                self.assertIn("23.8%", application.debug_log_lines[-1])
                for value in (18.0, -5.0, float("nan"), float("inf")):
                    application.events.put(("progress", value, "지연된 콜백"))
                    application._drain_events()
                    self.assertEqual(application.progress_var.get(), 23.75)
                application.analysis_cancel_event.set()
                application.status_var.set("취소 대기 중")
                application.events.put(("progress", 42.125, "기타 분리"))
                application._drain_events()
                self.assertEqual(application.status_var.get(), "취소 대기 중")
                self.assertEqual(application.progress_var.get(), 42.125)
                application.events.put(("progress", 110.0, "범위 밖 콜백"))
                application._drain_events()
                self.assertEqual(application.progress_var.get(), 100.0)
        finally:
            root.destroy()

    def test_analysis_timer_refreshes_and_stops_on_error_or_cancellation(self) -> None:
        """콜백이 없어도 경과 시간만 갱신하고 오류·취소 이후에는 마지막 값이 유지돼야 한다."""
        root = tk.Tk()
        root.withdraw()
        try:
            application = ToneMatchApp(root)
            root.update_idletasks()
            application.language = "ko"
            application.analysis_started_at = 100.0
            application.analysis_progress_percent = 18.5
            application.progress_var.set(18.5)
            with patch("app.time.monotonic", return_value=107.9), patch.object(root, "after") as schedule:
                application._tick_analysis_progress()
                self.assertIn("18.5%", application.progress_detail_var.get())
                self.assertIn("00:07", application.progress_detail_var.get())
                self.assertEqual(application.progress_var.get(), 18.5)
                schedule.assert_called_once_with(250, application._tick_analysis_progress)
            with patch("app.time.monotonic", return_value=112.5), patch("app.messagebox.showerror") as show_error:
                application._show_error(RuntimeError("model unavailable"), "test diagnostic")
                show_error.assert_called_once()
            self.assertIsNone(application.analysis_started_at)
            self.assertEqual(application.analysis_elapsed_seconds, 12.5)
            self.assertEqual(application.progress_var.get(), 18.5)
            stopped_text = application.progress_detail_var.get()
            with patch("app.time.monotonic", return_value=900.0), patch.object(root, "after"):
                application._tick_analysis_progress()
            self.assertEqual(application.progress_detail_var.get(), stopped_text)
            application.analysis_started_at = 200.0
            with patch("app.time.monotonic", return_value=204.0), patch("app.messagebox.showerror") as show_error:
                application._show_error(RuntimeError("cancelled by user"), "")
                show_error.assert_not_called()
            self.assertIsNone(application.analysis_started_at)
            self.assertEqual(application.analysis_elapsed_seconds, 4.0)
            application.closing = True
            with patch.object(root, "after") as schedule:
                application._tick_analysis_progress()
                schedule.assert_not_called()
        finally:
            root.destroy()

    def test_analysis_completion_preserves_final_elapsed_time(self) -> None:
        """완료 이벤트는 전체 진행률을 100%로 만들고 결과 화면에서도 소요 시간을 보존해야 한다."""
        root = tk.Tk()
        root.withdraw()
        try:
            application = ToneMatchApp(root)
            root.update_idletasks()
            application.language = "en"
            application.analysis_started_at = 100.0
            application.analysis_progress_percent = 97.5
            result = {
                "features": dict.fromkeys(("saturation", "brightness", "body", "ambience", "analysis_confidence"), 0.5),
                "recipes": [{"name": "Test chain", "match_percent": 80}],
            }
            with (
                patch("app.time.monotonic", return_value=172.9),
                patch.object(root, "after"),
                patch.object(application, "_render_recipe"),
                patch.object(application, "_render_voicing"),
                patch.object(application, "_populate_diagnostics"),
                patch.object(application, "_refresh_reference_profile"),
            ):
                application.events.put(("done", result))
                application._drain_events()
            self.assertIs(application.result, result)
            self.assertIsNone(application.analysis_started_at)
            self.assertEqual(application.analysis_progress_percent, 100.0)
            self.assertEqual(application.progress_var.get(), 100.0)
            self.assertAlmostEqual(application.analysis_elapsed_seconds, 72.9)
            self.assertIn("100.0%", application.progress_detail_var.get())
            self.assertIn("Elapsed 01:12", application.progress_detail_var.get())
            with patch("app.time.monotonic", return_value=999.0):
                application._refresh_analysis_progress()
            self.assertIn("Elapsed 01:12", application.progress_detail_var.get())
        finally:
            root.destroy()

    def test_analysis_progress_footer_stays_visible_when_options_scroll(self) -> None:
        """최소 크기의 한·영 화면에서 긴 상태와 진행률이 입력 스크롤 밖에 고정돼야 한다."""
        root = tk.Tk()
        root.withdraw()
        try:
            with (
                patch.object(ToneMatchApp, "_load_settings"),
                patch.object(ToneMatchApp, "_save_settings"),
                patch.object(root, "after"),
                patch("app._window_work_area", return_value=(0, 0, 1112, 784)),
            ):
                application = ToneMatchApp(root)
                for language in ("ko", "en"):
                    application.language_var.set(LANGUAGE_LABELS[language])
                    application._change_language()
                    application.analysis_progress_percent = 23.75
                    application.analysis_elapsed_seconds = 125.0
                    application._refresh_analysis_progress()
                    statuses = (
                        tr(
                            "progress.separator_download", language,
                            filename="htdemucs_6s-large-model-checkpoint.safetensors",
                            downloaded_mb="1234.5", total_mb="2345.6", percent="52.6",
                        ),
                        tr(
                            "error.separator_network", language,
                            detail="HTTPSConnectionPool: model-download.example.test:443; certificate verification failed",
                        ),
                    )
                    for status in statuses:
                        with self.subTest(language=language, status=status):
                            application.status_var.set(status)
                            application.left_canvas.yview_moveto(0.0)
                            root.update_idletasks()
                            footer = application.progress.master
                            self.assertIs(footer.master, application.left_canvas.master)
                            self.assertEqual(footer.grid_info()["row"], 1)
                            self.assertEqual(application.left_canvas.grid_info()["row"], 0)
                            detail_label = footer.grid_slaves(row=2, column=0)[0]
                            status_area = footer.grid_slaves(row=3, column=0)[0]
                            self.assertEqual(str(detail_label.cget("textvariable")), str(application.progress_detail_var))
                            self.assertEqual(application.status_text.get("1.0", "end-1c"), application.status_var.get())
                            fixed_widgets = (
                                footer, application.analyze_button, application.cancel_button,
                                application.progress, detail_label, status_area, application.status_text,
                            )
                            original_positions = []
                            for widget in fixed_widgets:
                                x = widget.winfo_rootx() - root.winfo_rootx()
                                y = widget.winfo_rooty() - root.winfo_rooty()
                                original_positions.append((widget.winfo_rootx(), widget.winfo_rooty()))
                                self.assertGreaterEqual(x, 0)
                                self.assertGreaterEqual(y, 0)
                                self.assertLessEqual(x + widget.winfo_width(), 1080)
                                self.assertLessEqual(y + widget.winfo_height(), 720)
                                self.assertGreaterEqual(widget.winfo_height(), widget.winfo_reqheight())
                            self.assertGreater(application.left_canvas.winfo_height(), 0)
                            self.assertEqual(root.state(), "withdrawn")
                            self.assertEqual((root.winfo_width(), root.winfo_height()), (1080, 720))
                            top_view = application.left_canvas.yview()
                            application.left_canvas.yview_moveto(1.0)
                            root.update_idletasks()
                            self.assertGreater(application.left_canvas.yview()[0], top_view[0])
                            self.assertEqual(
                                [(widget.winfo_rootx(), widget.winfo_rooty()) for widget in fixed_widgets],
                                original_positions,
                            )
        finally:
            root.destroy()

    def test_initial_window_and_minimum_fit_the_usable_work_area(self) -> None:
        """작업 표시줄과 제목 표시줄 여유를 뺀 화면보다 초기·최소 창이 커지면 안 된다."""
        root = Mock()
        for work_area in ((0, 0, 1280, 680), (0, 0, 1024, 728), (0, 40, 960, 640)):
            with self.subTest(work_area=work_area), patch("app._window_work_area", return_value=work_area):
                _center_window(root, 1320, 880)
                geometry = root.geometry.call_args.args[0]
                match = re.fullmatch(r"(\d+)x(\d+)\+(\d+)\+(\d+)", geometry)
                self.assertIsNotNone(match)
                width, height, x, y = map(int, match.groups())
                min_width, min_height = root.minsize.call_args.args
                left, top, right, bottom = work_area
                self.assertLessEqual(min_width, width)
                self.assertLessEqual(min_height, height)
                self.assertGreaterEqual(x, left)
                self.assertGreaterEqual(y, top)
                self.assertLessEqual(x + width + 8, right)
                self.assertLessEqual(y + height + 32, bottom)

    def test_small_scaled_layout_does_not_grow_after_result_or_long_status(self) -> None:
        """작은 고배율 화면에서도 긴 결과·오류가 입력 영역과 고정 진행 영역을 밀어내지 않아야 한다."""
        for width, height in ((960, 600), (1024, 688), (1280, 640)):
            root = tk.Tk()
            root.withdraw()
            original_scaling = float(root.tk.call("tk", "scaling"))
            try:
                root.tk.call("tk", "scaling", 2.0)
                with (
                    patch.object(ToneMatchApp, "_load_settings"),
                    patch.object(ToneMatchApp, "_save_settings"),
                    patch.object(root, "after"),
                    patch("app._window_work_area", return_value=(0, 0, width + 32, height + 64)),
                ):
                    application = ToneMatchApp(root)
                    for language in ("ko", "en"):
                        application.language_var.set(LANGUAGE_LABELS[language])
                        application._change_language()
                        application.result_title_var.set("Room 335 · Clean fusion guitar · 78%")
                        application.summary_var.set(tr("result.feature_summary", language, sat=23, bright=45, body=8, amb=59, conf=100))
                        application.analysis_progress_percent = 100.0
                        application.analysis_elapsed_seconds = 105.0
                        application._refresh_analysis_progress()
                        footer_geometry = None
                        for status in (tr("status.complete", language), "HTTPS error\n" * 100):
                            with self.subTest(size=(width, height), language=language, status=status[:30]):
                                application.status_var.set(status)
                                application.left_canvas.yview_moveto(0.0)
                                root.update_idletasks()
                                self.assertEqual(root.state(), "withdrawn")
                                self.assertEqual((root.winfo_width(), root.winfo_height()), (width, height))
                                self.assertEqual(application.status_text.get("1.0", "end-1c"), status)
                                self.assertGreater(application.left_canvas.winfo_height(), 100)
                                self.assertAlmostEqual(application.left_canvas.yview()[0], 0.0)
                                footer = application.progress.master
                                geometry = (footer.winfo_x(), footer.winfo_y(), footer.winfo_width(), footer.winfo_height())
                                if footer_geometry is None:
                                    footer_geometry = geometry
                                self.assertEqual(geometry, footer_geometry)
                                self.assertGreaterEqual(application.status_text.winfo_height(), application.status_text.winfo_reqheight())
                                visible_widgets = (
                                    footer, application.analyze_button, application.cancel_button,
                                    application.progress, application.status_text,
                                    application.result_title_label, application.result_summary_label,
                                    application.export_json_button, application.export_html_button,
                                    application.copy_button, application.notebook,
                                )
                                for widget in visible_widgets:
                                    x = widget.winfo_rootx() - root.winfo_rootx()
                                    y = widget.winfo_rooty() - root.winfo_rooty()
                                    self.assertGreaterEqual(x, 0)
                                    self.assertGreaterEqual(y, 0)
                                    self.assertLessEqual(x + widget.winfo_width(), width)
                                    self.assertLessEqual(y + widget.winfo_height(), height)
                                self.assertGreater(application.notebook.winfo_height(), 100)
                                self.assertLess(application.result_title_label.winfo_rooty(), application.export_json_button.winfo_rooty())
                                if status.startswith("HTTPS"):
                                    self.assertLess(application.status_text.yview()[1], 1.0)
                                    application.status_text.yview_moveto(1.0)
                                    self.assertAlmostEqual(application.status_text.yview()[1], 1.0)
            finally:
                root.tk.call("tk", "scaling", original_scaling)
                root.destroy()

    def test_input_scroll_clamps_after_content_becomes_shorter(self) -> None:
        """입력 카드 내용이 줄면 예전 맨 아래 위치나 빈 스크롤 여백이 남지 않아야 한다."""
        root = tk.Tk()
        root.withdraw()
        try:
            with (
                patch.object(root, "after"),
                patch.object(ToneMatchApp, "_load_settings"),
                patch("app._window_work_area", return_value=(0, 0, 1112, 784)),
            ):
                application = ToneMatchApp(root)
                root.update_idletasks()
                self.assertEqual((root.winfo_width(), root.winfo_height()), (1080, 720))
                application.left_canvas.yview_moveto(1.0)
                self.assertGreater(application.left_canvas.yview()[0], 0.0)
                content = application.root.nametowidget(application.left_canvas.itemcget(application.left_canvas_window, "window"))
                for widget in content.winfo_children():
                    widget.grid_remove()
                content.configure(height=30)
                root.update_idletasks()
                application._sync_left_scroll_region()
                root.update_idletasks()
                self.assertEqual(application.left_canvas.yview(), (0.0, 1.0))
                application.left_canvas.yview_moveto(1.0)
                self.assertEqual(application.left_canvas.yview(), (0.0, 1.0))
        finally:
            root.destroy()

    def test_debug_diagram_fits_and_displays_source(self) -> None:
        """개발자 탭의 모든 블록이 화면 안에 들어오고 코드 내용이 표시되는지 확인한다."""
        root = tk.Tk()
        root.withdraw()
        try:
            application = ToneMatchApp(root)
            root.update_idletasks()
            application.developer_var.set(True)
            application._toggle_developer_mode()
            root.update_idletasks()
            bounds = application.debug_canvas.bbox("all")
            self.assertIsNotNone(bounds)
            self.assertEqual(len(application.debug_nodes), len(debug_info.PIPELINE_BLOCKS))
            self.assertLessEqual(bounds[3], application.debug_canvas.winfo_height())
            self.assertIn("def ", application.debug_code.get("1.0", "end-1c"))
        finally:
            root.destroy()

    def test_live_spectrum_tab_renders_latest_frame_without_hardware(self) -> None:
        """실제 장치 없이 합성 FFT 프레임이 탭 수치와 두 캔버스에 표시돼야 한다."""
        sample_rate = 48_000
        fft_size = 2_048
        time_axis = np.arange(fft_size, dtype=np.float64) / sample_rate
        samples = 0.5 * np.sin(2.0 * np.pi * 1_125.0 * time_axis)
        frame = analyze_spectrum_frame(samples, sample_rate, fft_size=fft_size)
        root = tk.Tk()
        root.withdraw()
        try:
            application = ToneMatchApp(root)
            root.update_idletasks()
            application.waveform_canvas.winfo_width = lambda: 800
            application.waveform_canvas.winfo_height = lambda: 130
            application.spectrum_canvas.winfo_width = lambda: 800
            application.spectrum_canvas.winfo_height = lambda: 250
            application._apply_spectrum_frame(frame)
            root.update_idletasks()
            self.assertIn("dBFS", application.spectrum_rms_var.get())
            self.assertIn("Hz", application.spectrum_centroid_var.get())
            self.assertTrue(application.waveform_canvas.find_withtag("dynamic"))
            self.assertTrue(application.spectrum_canvas.find_withtag("dynamic"))

            application._offer_latest_spectrum(application.spectrum_session_id, frame)
            application._offer_latest_spectrum(application.spectrum_session_id, frame)
            self.assertEqual(application.spectrum_frames.qsize(), 1)
        finally:
            root.destroy()

    def test_reference_compare_tab_renders_six_bands_without_hardware(self) -> None:
        """숨긴 Tk 화면에서 기준 프로필과 합성 라이브 차이 여섯 대역을 표시해야 한다."""
        sample_rate = 48_000
        fft_size = 2_048
        reference_axis = np.arange(fft_size * 6, dtype=np.float64) / sample_rate
        live_axis = np.arange(fft_size, dtype=np.float64) / sample_rate
        reference_samples = (
            0.42 * np.sin(2.0 * np.pi * 750.0 * reference_axis)
            + 0.12 * np.sin(2.0 * np.pi * 3_000.0 * reference_axis)
        ).astype(np.float32)
        live_samples = (
            0.25 * np.sin(2.0 * np.pi * 750.0 * live_axis)
            + 0.25 * np.sin(2.0 * np.pi * 3_000.0 * live_axis)
        ).astype(np.float32)
        root = tk.Tk()
        root.withdraw()
        try:
            application = ToneMatchApp(root)
            root.update_idletasks()
            application.reference_canvas.winfo_width = lambda: 800
            application.reference_canvas.winfo_height = lambda: 250
            application.waveform_canvas.winfo_width = lambda: 800
            application.waveform_canvas.winfo_height = lambda: 130
            application.spectrum_canvas.winfo_width = lambda: 800
            application.spectrum_canvas.winfo_height = lambda: 250
            application.result = {
                "source": {"file_name": "reference.wav"},
                "reference_spectrum": build_reference_profile(reference_samples, sample_rate),
            }
            application._refresh_reference_profile(reset_comparison=True)
            application._apply_spectrum_frame(analyze_spectrum_frame(live_samples, sample_rate))

            rows = application.reference_tree.get_children()
            self.assertEqual(len(rows), 6)
            self.assertTrue(all("dB" in application.reference_tree.item(row, "values")[1] for row in rows))
            self.assertTrue(all("dB" in application.reference_tree.item(row, "values")[2] for row in rows))
            self.assertTrue(all("dB" in application.reference_tree.item(row, "values")[3] for row in rows))
            self.assertIsNotNone(application.last_reference_comparison)
            self.assertTrue(application.reference_canvas.find_withtag("dynamic"))

            previous = application.last_reference_comparison
            silence = analyze_spectrum_frame(np.zeros(fft_size, dtype=np.float32), sample_rate)
            application._apply_spectrum_frame(silence)
            self.assertIs(application.last_reference_comparison, previous)
            application.language = "en"
            application._refresh_reference_profile()
            self.assertIn("Comparison stopped", application.reference_status_var.get())

            application.spectrum_worker = Mock()
            application.spectrum_stop_requested = True
            application._offer_latest_spectrum(application.spectrum_session_id, silence)
            application._drain_spectrum_frames()
            self.assertIs(application.last_reference_comparison, previous)
            application.spectrum_worker = None
            application._refresh_reference_profile(reset_comparison=True)
            self.assertIsNone(application.last_reference_comparison)
            application._offer_latest_spectrum(application.spectrum_session_id, frame := analyze_spectrum_frame(live_samples, sample_rate))
            application._drain_spectrum_frames()
            self.assertIsNone(application.last_reference_comparison)
            application.spectrum_worker = Mock()
            application.spectrum_stop_requested = False
            application._offer_latest_spectrum(application.spectrum_session_id - 1, frame)
            application._drain_spectrum_frames()
            self.assertIsNone(application.last_reference_comparison)
            application._offer_latest_spectrum(application.spectrum_session_id, frame)
            application._drain_spectrum_frames()
            self.assertIsNotNone(application.last_reference_comparison)
            application.spectrum_worker = None
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
