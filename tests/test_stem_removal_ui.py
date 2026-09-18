"""실제 모델이나 파일 대화상자를 열지 않고 악기 제거 GUI 연결을 검증한다."""

from __future__ import annotations

import queue
import sys
import tempfile
import threading
import tkinter as tk
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import Mock, patch


MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from app import REMOVABLE_STEMS, ToneMatchApp  # noqa: E402
from i18n import LANGUAGE_LABELS, tr  # noqa: E402
from stem_removal import StemRemovalCancelled, StemRemovalError  # noqa: E402


@contextmanager
def hidden_application(data_root: Path, width: int = 960, height: int = 600):
    """장치 검사·예약 콜백을 막은 숨은 최소 크기 앱을 테스트에 제공한다."""
    root = tk.Tk()
    root.withdraw()
    try:
        with (
            patch.object(ToneMatchApp, "_load_settings"),
            patch.object(ToneMatchApp, "_save_settings"),
            patch.object(ToneMatchApp, "_refresh_capture_devices"),
            patch.object(root, "after"),
            patch("app._runtime_data_root", return_value=data_root),
            patch("app._window_work_area", return_value=(0, 0, width + 32, height + 64)),
        ):
            application = ToneMatchApp(root)
            application.hardware_probe_active = False
            application._update_analysis_availability()
            root.update_idletasks()
            yield root, application
    finally:
        try:
            root.update_idletasks()
            root.destroy()
        except tk.TclError:
            pass


class StemRemovalLayoutTests(unittest.TestCase):
    """새 작업 탭이 기본값·한영 상태·최소 창 접근성을 지키는지 검사한다."""

    def test_every_stem_control_fits_canvas_width_in_both_languages(self) -> None:
        """최소 창에서 파일 버튼·여섯 선택 항목·범위·가속 입력이 가로로 잘리지 않아야 한다."""
        with tempfile.TemporaryDirectory() as temporary:
            with hidden_application(Path(temporary)) as (root, application):
                for language in ("ko", "en"):
                    application.language_var.set(LANGUAGE_LABELS[language])
                    application._change_language()
                    application.workspace_notebook.select(application.stem_tab)
                    root.update_idletasks()
                    left = application.stem_canvas.winfo_rootx()
                    right = left + application.stem_canvas.winfo_width()
                    content = application.stem_canvas.nametowidget(
                        application.stem_canvas.itemcget(application.stem_scroll_window, "window")
                    )
                    footer_y = application.stem_footer.winfo_rooty()
                    for widget in (*application.stem_control_widgets, application.stem_compute_combo):
                        with self.subTest(language=language, widget=str(widget)):
                            self.assertGreater(widget.winfo_width(), 1)
                            self.assertGreaterEqual(widget.winfo_rootx(), left)
                            self.assertLessEqual(widget.winfo_rootx() + widget.winfo_width(), right)
                            self.assertGreaterEqual(widget.winfo_x(), 0)
                            self.assertGreaterEqual(widget.winfo_y(), 0)
                            self.assertLessEqual(widget.winfo_x() + widget.winfo_width(), widget.master.winfo_width())
                            self.assertLessEqual(widget.winfo_y() + widget.winfo_height(), widget.master.winfo_height())
                            if widget.winfo_class() in ("TButton", "TCheckbutton"):
                                self.assertGreaterEqual(widget.winfo_width(), widget.winfo_reqwidth())
                            # 가로 경계만 맞아도 스크롤 범위가 짧으면 아래 입력은 사용할 수 없다.
                            position = widget.winfo_rooty() - content.winfo_rooty()
                            viewport_height = application.stem_canvas.winfo_height()
                            application.stem_canvas.yview_moveto(
                                max(0.0, (position - viewport_height / 2) / content.winfo_height())
                            )
                            root.update_idletasks()
                            # 숨겨진 창에서는 화면 좌표 이동이 지연되므로 캔버스 논리 좌표로 확인한다.
                            top = application.stem_canvas.canvasy(0)
                            self.assertGreaterEqual(position, top)
                            self.assertLessEqual(position + widget.winfo_height(), top + viewport_height)
                            self.assertEqual(application.stem_footer.winfo_rooty(), footer_y)
                    for widget in (
                        application.stem_start_button,
                        application.stem_cancel_button,
                        application.stem_progress,
                        application.stem_status_text,
                    ):
                        with self.subTest(language=language, action=str(widget)):
                            self.assertGreaterEqual(widget.winfo_rootx(), root.winfo_rootx())
                            self.assertLessEqual(widget.winfo_rootx() + widget.winfo_width(), root.winfo_rootx() + 960)
                            self.assertGreaterEqual(widget.winfo_rooty(), footer_y)
                            self.assertLessEqual(widget.winfo_rooty() + widget.winfo_height(), root.winfo_rooty() + 600)
                            self.assertGreaterEqual(widget.winfo_width(), widget.winfo_reqwidth())
                    self.assertEqual(root.state(), "withdrawn")

    def test_outer_workspace_keeps_existing_result_tabs_uncluttered_at_960x600(self) -> None:
        """악기 제거는 상위 작업 탭에 두고 긴 폼은 내부 스크롤로 접근 가능해야 한다."""
        with tempfile.TemporaryDirectory() as temporary:
            with hidden_application(Path(temporary)) as (root, application):
                self.assertEqual(len(application.workspace_notebook.tabs()), 2)
                self.assertEqual(application.workspace_notebook.tab(0, "text"), tr("ui.tone_analysis_tab", "ko"))
                self.assertEqual(application.workspace_notebook.tab(1, "text"), tr("ui.stem_removal_tab", "ko"))
                self.assertEqual(application.stem_tab.master, application.workspace_notebook)
                self.assertEqual(application.spectrum_tab.master, application.notebook)
                self.assertNotIn(str(application.stem_tab), application.notebook.tabs())
                self.assertTrue(all(not variable.get() for variable in application.stem_remove_vars.values()))

                application.workspace_notebook.select(application.stem_tab)
                root.update_idletasks()
                self.assertEqual((root.winfo_width(), root.winfo_height()), (960, 600))
                for widget in (application.workspace_notebook, application.stem_canvas, application.stem_footer, application.stem_progress, application.stem_cancel_button):
                    x = widget.winfo_rootx() - root.winfo_rootx()
                    y = widget.winfo_rooty() - root.winfo_rooty()
                    self.assertGreaterEqual(x, 0)
                    self.assertGreaterEqual(y, 0)
                    self.assertLessEqual(x + widget.winfo_width(), 960)
                    self.assertLessEqual(y + widget.winfo_height(), 600)
                bounds = application.stem_canvas.bbox(application.stem_scroll_window)
                self.assertIsNotNone(bounds)
                self.assertGreater(bounds[3], application.stem_canvas.winfo_height())
                top = application.stem_canvas.yview()[0]
                progress_y = application.stem_progress.winfo_rooty()
                self.assertTrue(application.stem_source_entry.bind("<MouseWheel>"))
                application._scroll_stem_tab(Mock(delta=-120))
                self.assertGreater(application.stem_canvas.yview()[0], top)
                application.stem_canvas.yview_moveto(1.0)
                root.update_idletasks()
                self.assertGreater(application.stem_canvas.yview()[0], top)
                self.assertEqual(application.stem_progress.winfo_rooty(), progress_y)
                self.assertEqual(root.state(), "withdrawn")

    def test_language_rebuild_preserves_stem_form_result_and_selected_workspace(self) -> None:
        """한영 전환이 경로·제거 선택·결과와 현재 악기 제거 탭을 잃지 않아야 한다."""
        with tempfile.TemporaryDirectory() as temporary:
            root_path = Path(temporary)
            source = root_path / "song.mp3"
            source.write_bytes(b"test")
            destination = root_path / "song-removed.wav"
            with hidden_application(root_path) as (root, application):
                application.stem_source_var.set(str(source))
                application.stem_destination_var.set(str(destination))
                application.stem_remove_vars["guitar"].set(True)
                application.stem_remove_vars["piano"].set(True)
                application.stem_result = {
                    "output_path": str(destination),
                    "removed_stems": ["guitar", "piano"],
                    "kept_stems": ["vocals", "drums", "bass", "other"],
                    "duration_seconds": 42.5,
                    "inference_total_seconds": 7.25,
                    "resolved_device": "cpu",
                }
                application._set_stem_status("status.stem_complete", file=destination.name)
                application._render_stem_summary()
                application.workspace_notebook.select(application.stem_tab)

                application.language_var.set(LANGUAGE_LABELS["en"])
                application._change_language()
                root.update_idletasks()
                self.assertEqual(application.workspace_notebook.select(), str(application.stem_tab))
                self.assertEqual(application.workspace_notebook.tab(application.stem_tab, "text"), "Stem removal")
                self.assertEqual(application.stem_source_var.get(), str(source))
                self.assertEqual(application.stem_destination_var.get(), str(destination))
                self.assertTrue(application.stem_remove_vars["guitar"].get())
                self.assertTrue(application.stem_remove_vars["piano"].get())
                self.assertIn("Removed · Guitar, Piano", application.stem_summary_var.get())
                self.assertIn("Stem removal complete", application.stem_status_var.get())

                application.language_var.set(LANGUAGE_LABELS["ko"])
                application._change_language()
                self.assertEqual(application.workspace_notebook.select(), str(application.stem_tab))
                self.assertIn("제거 · 기타, 피아노", application.stem_summary_var.get())
                self.assertIn("악기 제거 완료", application.stem_status_var.get())
                self.assertEqual(len(application.stem_status_var.trace_info()), 1)


class StemRemovalValidationTests(unittest.TestCase):
    """원본 보호, 새 WAV, 시간 범위와 1~5개 제거 규칙을 GUI 경계에서 검사한다."""

    def test_validation_blocks_unsafe_paths_and_invalid_stem_counts(self) -> None:
        """원본·기존 출력 덮어쓰기와 0개·6개 선택을 코어 호출 전에 거부해야 한다."""
        with tempfile.TemporaryDirectory() as temporary:
            root_path = Path(temporary)
            source = root_path / "source.wav"
            source.write_bytes(b"RIFFtest")
            with hidden_application(root_path) as (_root, application):
                with self.assertRaisesRegex(StemRemovalError, tr("error.stem_choose_source", "ko")):
                    application._parse_stem_removal_inputs()

                application.stem_source_var.set(str(source))
                application.stem_destination_var.set(str(root_path / "new.wav"))
                with self.assertRaisesRegex(StemRemovalError, tr("error.stem_select_one", "ko")):
                    application._parse_stem_removal_inputs()

                for variable in application.stem_remove_vars.values():
                    variable.set(True)
                with self.assertRaisesRegex(StemRemovalError, tr("error.stem_keep_one", "ko")):
                    application._parse_stem_removal_inputs()

                for variable in application.stem_remove_vars.values():
                    variable.set(False)
                application.stem_remove_vars["guitar"].set(True)
                application.stem_destination_var.set(str(source))
                with self.assertRaisesRegex(StemRemovalError, tr("error.stem_same_file", "ko")):
                    application._parse_stem_removal_inputs()

                existing = root_path / "existing.wav"
                existing.write_bytes(b"existing")
                application.stem_destination_var.set(str(existing))
                with self.assertRaisesRegex(StemRemovalError, tr("error.stem_output_exists", "ko")):
                    application._parse_stem_removal_inputs()

                application.stem_destination_var.set(str(root_path / "output.mp3"))
                with self.assertRaisesRegex(StemRemovalError, tr("error.stem_output_wav", "ko")):
                    application._parse_stem_removal_inputs()

    def test_valid_request_clamps_explicit_range_to_twenty_minutes(self) -> None:
        """유효한 새 WAV 요청은 안정적인 stem 코드와 최대 20분 범위로 전달돼야 한다."""
        with tempfile.TemporaryDirectory() as temporary:
            root_path = Path(temporary)
            source = root_path / "source.mp3"
            source.write_bytes(b"test")
            with hidden_application(root_path) as (_root, application):
                application.stem_source_var.set(str(source))
                application.stem_destination_var.set(str(root_path / "output.wav"))
                application.stem_start_var.set("10")
                application.stem_end_var.set("9999")
                application.stem_remove_vars["guitar"].set(True)
                application.stem_remove_vars["piano"].set(True)
                request = application._parse_stem_removal_inputs()
                self.assertEqual(request["removed_stems"], ["guitar", "piano"])
                self.assertEqual(request["start_seconds"], 10.0)
                self.assertEqual(request["end_seconds"], 1210.0)
                self.assertEqual(application.stem_end_var.get(), "1210")
                self.assertEqual(request["compute_preference"], "auto")
                self.assertEqual(request["language"], "ko")


class StemRemovalWorkerTests(unittest.TestCase):
    """백그라운드 호출, 이벤트 적용, 취소와 다른 작업의 상호 배제를 검사한다."""

    def test_worker_only_queues_progress_and_main_thread_renders_result(self) -> None:
        """모델 작업자는 Tk를 만지지 않고 메인 이벤트 처리 뒤에만 화면을 바꿔야 한다."""
        with tempfile.TemporaryDirectory() as temporary:
            root_path = Path(temporary)
            destination = root_path / "result.wav"
            request = {
                "source": str(root_path / "source.mp3"),
                "destination": str(destination),
                "removed_stems": ["guitar", "piano"],
                "start_seconds": 0.0,
                "end_seconds": 30.0,
                "compute_preference": "cpu",
                "language": "ko",
            }
            result = {
                "output_path": str(destination),
                "removed_stems": ["guitar", "piano"],
                "kept_stems": ["vocals", "drums", "bass", "other"],
                "duration_seconds": 30.0,
                "inference_total_seconds": 8.5,
                "resolved_device": "cpu",
            }

            with hidden_application(root_path) as (_root, application):
                application.stem_started_at = 100.0
                application.stem_worker = Mock()
                application.stem_worker.is_alive.return_value = True

                def remove(**kwargs: object) -> dict[str, object]:
                    """두 진행 콜백 뒤 결정론적인 성공 결과를 반환한다."""
                    kwargs["progress"](12.5, "준비")
                    kwargs["progress"](65.0, "분리")
                    self.assertTrue(callable(kwargs["cancel_requested"]))
                    return result

                with patch("app.remove_stems_from_file", side_effect=remove) as core:
                    application._stem_removal_worker(request)
                self.assertEqual(application.stem_progress_var.get(), 0.0)
                self.assertEqual(
                    [application.events.get_nowait()[0] for _ in range(3)],
                    ["stem_progress", "stem_progress", "stem_done"],
                )
                core.assert_called_once()

                # 같은 이벤트를 다시 넣어 실제 Tk 이벤트 처리 경계를 검증한다.
                application.events.put(("stem_progress", 12.5, "준비"))
                application.events.put(("stem_progress", 65.0, "분리"))
                application.events.put(("stem_done", result))
                with patch("app.time.monotonic", return_value=160.0), patch("app.messagebox.showerror") as show_error:
                    application._drain_events()
                show_error.assert_not_called()
                self.assertIsNone(application.stem_worker)
                self.assertEqual(application.stem_progress_percent, 100.0)
                self.assertEqual(application.stem_progress_var.get(), 100.0)
                self.assertEqual(application.stem_elapsed_seconds, 60.0)
                self.assertIn("제거 · 기타, 피아노", application.stem_summary_var.get())
                self.assertIn(destination.name, application.stem_status_var.get())

    def test_start_cancel_and_every_other_long_task_are_mutually_exclusive(self) -> None:
        """악기 제거와 분석·녹음·스펙트럼·하드웨어 검사가 동시에 시작되지 않아야 한다."""
        with tempfile.TemporaryDirectory() as temporary:
            root_path = Path(temporary)
            source = root_path / "source.mp3"
            source.write_bytes(b"test")
            with hidden_application(root_path) as (_root, application):
                application.stem_source_var.set(str(source))
                application.stem_destination_var.set(str(root_path / "output.wav"))
                application.stem_remove_vars["guitar"].set(True)
                with patch("app.threading.Thread") as thread:
                    thread.return_value.is_alive.return_value = True
                    application._start_stem_removal()
                    thread.assert_called_once()
                    self.assertEqual(str(application.stem_start_button.cget("state")), "disabled")
                    self.assertEqual(str(application.stem_cancel_button.cget("state")), "normal")
                    self.assertEqual(str(application.analyze_button.cget("state")), "disabled")
                    self.assertEqual(str(application.language_combo.cget("state")), "disabled")
                    application._cancel_stem_removal()
                    self.assertTrue(application.stem_cancel_event.is_set())
                    self.assertEqual(str(application.stem_cancel_button.cget("state")), "disabled")
                    self.assertIn("취소", application.stem_status_var.get())

                active_stem = Mock()
                active_stem.is_alive.return_value = True
                application.stem_worker = active_stem
                application.spectrum_worker = None
                application.hardware_probe_active = False
                with patch("app.messagebox.showinfo") as wait, patch("app.threading.Thread") as thread:
                    application._start_analysis()
                    application._toggle_recording()
                    application._toggle_spectrum_monitor()
                    application._start_hardware_probe()
                self.assertEqual(wait.call_count, 3)
                thread.assert_not_called()

                application.stem_worker = None
                application.worker = Mock()
                application.worker.is_alive.return_value = True
                with patch("app.messagebox.showinfo") as wait:
                    application._start_stem_removal()
                wait.assert_called_once()

    def test_cancel_event_is_silent_and_close_signals_stem_worker(self) -> None:
        """사용자 취소는 오류 팝업을 띄우지 않고 창 닫기도 같은 취소 신호를 보내야 한다."""
        with tempfile.TemporaryDirectory() as temporary:
            root_path = Path(temporary)
            with hidden_application(root_path) as (root, application):
                application.stem_started_at = 100.0
                application.stem_worker = Mock()
                application.stem_worker.is_alive.return_value = False
                application.events.put(("stem_error", StemRemovalCancelled("cancelled"), "trace"))
                with patch("app.time.monotonic", return_value=105.0), patch("app.messagebox.showerror") as show_error:
                    application._drain_events()
                show_error.assert_not_called()
                self.assertEqual(application.stem_status_var.get(), tr("status.stem_cancelled", "ko"))
                self.assertEqual(application.stem_elapsed_seconds, 5.0)

                application.stem_cancel_event.clear()
                with patch.object(root, "destroy"):
                    application._on_close()
                self.assertTrue(application.stem_cancel_event.is_set())

    def test_finished_worker_stays_busy_until_ui_applies_terminal_event(self) -> None:
        """완료 큐를 읽기 전 새 작업이 이전 결과에 덮이는 경쟁을 막아야 한다."""
        with tempfile.TemporaryDirectory() as temporary:
            with hidden_application(Path(temporary)) as (_root, application):
                application.stem_worker = Mock()
                application.stem_worker.is_alive.return_value = False
                application._update_analysis_availability()
                self.assertTrue(application._stem_is_running())
                self.assertEqual(str(application.stem_start_button.cget("state")), "disabled")
                with patch("app.threading.Thread") as thread:
                    application._start_stem_removal()
                thread.assert_not_called()
                application.events.put(("stem_error", StemRemovalCancelled("cancelled"), ""))
                application._drain_events()
                self.assertFalse(application._stem_is_running())
                self.assertEqual(str(application.stem_start_button.cget("state")), "normal")

    def test_close_waits_for_worker_cleanup_without_processing_late_ui_events(self) -> None:
        """창을 숨긴 뒤 작업자의 임시 파일 정리가 끝나야 프로세스가 종료돼야 한다."""
        with tempfile.TemporaryDirectory() as temporary:
            with hidden_application(Path(temporary)) as (root, application):
                application.stem_worker = Mock()
                application.stem_worker.is_alive.return_value = True
                application.events.put(("stem_error", RuntimeError("late error"), ""))
                with patch.object(root, "destroy") as destroy, patch("app.messagebox.showerror") as show_error:
                    application._on_close()
                    self.assertTrue(application.stem_cancel_event.is_set())
                    self.assertEqual(root.state(), "withdrawn")
                    root.after.assert_called_with(80, application._finish_close_after_stem_cleanup)
                    destroy.assert_not_called()
                    application._drain_events()
                    show_error.assert_not_called()
                    self.assertFalse(application.events.empty())
                    application.stem_worker.is_alive.return_value = False
                    application._finish_close_after_stem_cleanup()
                    destroy.assert_called_once()


class StemRemovalTranslationTests(unittest.TestCase):
    """새 UI에서 사용한 모든 핵심 문자열이 한국어와 영어로 실제 번역되는지 검사한다."""

    def test_core_stem_labels_and_safety_notices_are_bilingual(self) -> None:
        """버튼·악기명·로컬 처리·실험 한계가 어느 언어에서도 키로 노출되면 안 된다."""
        keys = (
            "ui.tone_analysis_tab",
            "ui.stem_removal_tab",
            "ui.stem_start",
            "ui.stem_cancel",
            "ui.stem_local_notice",
            "ui.stem_experimental_notice",
            "status.stem_ready",
            "error.stem_same_file",
            "error.stem_output_exists",
            *(f"stem.{stem}" for stem in REMOVABLE_STEMS),
        )
        for language in ("ko", "en"):
            for key in keys:
                with self.subTest(language=language, key=key):
                    self.assertNotEqual(tr(key, language), key)
                    self.assertNotIn("{", tr(key, language))
        self.assertIn("업로드하지", tr("ui.stem_local_notice", "ko"))
        self.assertIn("no upload", tr("ui.stem_local_notice", "en"))
        self.assertIn("실험", tr("ui.stem_experimental_notice", "ko"))
        self.assertIn("Experimental", tr("ui.stem_experimental_notice", "en"))


if __name__ == "__main__":
    unittest.main()
