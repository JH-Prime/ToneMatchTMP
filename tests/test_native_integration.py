"""실제 오디오 장치를 열지 않고 C++ 스트리밍 DSP의 앱 연결과 수명 관리를 검증한다."""

from __future__ import annotations

import queue
import sys
import threading
import tkinter as tk
import tkinter.font as tkfont
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np


MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from app import ToneMatchApp, _self_test_native_dsp  # noqa: E402
from debug_info import code_for_block, source_file_path  # noqa: E402
from i18n import LANGUAGE_LABELS, tr  # noqa: E402
from native_dsp import create_spectrum_engine, native_runtime_info  # noqa: E402


def _application() -> ToneMatchApp:
    """Tk 창이나 오디오 장치 없이 작업자와 이벤트에 필요한 최소 앱 상태를 만든다."""
    application = ToneMatchApp.__new__(ToneMatchApp)
    application.events = queue.Queue()
    application.spectrum_frames = queue.Queue(maxsize=1)
    application.spectrum_session_id = 7
    application.spectrum_worker = Mock()
    application.spectrum_stop_event = threading.Event()
    application.spectrum_stop_requested = False
    application.spectrum_backend = None
    application.spectrum_fallback_reason = None
    application.spectrum_backend_var = Mock()
    application._append_debug_log = Mock()
    application.root = Mock()
    application.closing = False
    application.language = "ko"
    return application


def _events(application: ToneMatchApp) -> list[tuple]:
    """작업자 이벤트를 순서대로 회수해 중복 종료와 잘못된 갱신을 검사한다."""
    result = []
    while not application.events.empty():
        result.append(application.events.get_nowait())
    return result


class NativeWorkerIntegrationTests(unittest.TestCase):
    """동일한 단일 캡처를 유지하면서 DSP 엔진이 모든 종료 경로에서 정리되는지 검사한다."""

    def test_actual_cpp_auto_factory_receives_mock_capture_stream(self) -> None:
        """실제 DLL과 자동 선택 경로를 통과한 합성 캡처 스트림이 NumPy 기준과 같아야 한다."""
        if not (MODULE_DIR / "resources" / "tonematch_dsp.dll").is_file():
            self.skipTest("Native DSP DLL has not been built in this source checkout")
        self.assertTrue(native_runtime_info()["available"], "The existing native DSP DLL must load successfully")
        application = _application()
        axis = np.arange(4096) / 44_100
        mono = 0.3 * np.sin(2 * np.pi * 440 * axis)
        samples = np.column_stack((mono, -mono))
        reference = create_spectrum_engine(44_100, 2, backend="numpy")
        try:
            expected = reference.push(samples)
        finally:
            reference.close()

        def capture(device: str, stop: threading.Event, callback: object, language: str) -> None:
            """실제 장치 접근 없이 역상 PCM을 불규칙한 마지막 블록과 함께 공급한다."""
            for start in range(0, len(samples), 127):
                callback(samples[start : start + 127], 44_100)

        with patch("app.monitor_capture_device", side_effect=capture):
            application._spectrum_monitor_worker(7, "synthetic-device", application.spectrum_stop_event, "ko")
        events = _events(application)
        self.assertEqual(events, [("spectrum_backend", 7, "cpp", None), ("spectrum_finished", 7)])
        session, actual = application.spectrum_frames.get_nowait()
        self.assertEqual(session, 7)
        np.testing.assert_allclose(actual.magnitudes_dbfs, expected.magnitudes_dbfs, rtol=0, atol=1e-6)
        self.assertAlmostEqual(actual.rms_dbfs, expected.rms_dbfs, places=9)

    def test_irregular_blocks_use_one_engine_and_latest_frame_queue(self) -> None:
        """작은 PCM 조각이 누적되고 여러 FFT 구간의 최신 결과 하나만 UI 큐에 남아야 한다."""
        application = _application()
        samples = np.random.default_rng(808).normal(0, 0.1, (8192 + 91, 2))
        sizes = (17, 1000, 31, 3000, 2048, len(samples) - 6096)
        engine = create_spectrum_engine(48_000, 2, backend="numpy")
        tracked = Mock(wraps=engine, backend="numpy", fallback_reason="Native DSP DLL is not installed.")
        reference = create_spectrum_engine(48_000, 2, backend="numpy")
        expected = None
        cursor = 0
        for size in sizes:
            frame = reference.push(samples[cursor : cursor + size])
            cursor += size
            if frame is not None:
                expected = frame
        reference.close()

        def capture(device: str, stop: threading.Event, callback: object, language: str) -> None:
            """장치 대신 결정론적인 불규칙 PCM 조각을 기존 콜백으로 전달한다."""
            self.assertEqual((device, language), ("synthetic-device", "ko"))
            cursor = 0
            for size in sizes:
                callback(samples[cursor : cursor + size], 48_000)
                cursor += size
            tracked.close.assert_not_called()

        with patch("app.monitor_capture_device", side_effect=capture) as capture_mock, patch("app.create_spectrum_engine", return_value=tracked) as factory:
            application._spectrum_monitor_worker(7, "synthetic-device", application.spectrum_stop_event, "ko")
        capture_mock.assert_called_once()
        factory.assert_called_once_with(48_000, 2, backend="auto", fft_size=2048, history_size=4)
        tracked.close.assert_called_once()
        self.assertEqual(application.spectrum_frames.qsize(), 1)
        session, actual = application.spectrum_frames.get_nowait()
        self.assertEqual(session, 7)
        np.testing.assert_allclose(actual.magnitudes_dbfs, expected.magnitudes_dbfs, atol=1e-12)
        self.assertEqual([event[0] for event in _events(application)], ["spectrum_backend", "spectrum_finished"])
        application.spectrum_backend_var.set.assert_not_called()

    def test_configuration_change_closes_old_engine_and_discards_partial_pcm(self) -> None:
        """입력 채널과 표본율이 바뀌면 이전 부분 PCM을 섞지 않고 새 컨텍스트를 만들어야 한다."""
        application = _application()
        first = Mock(wraps=create_spectrum_engine(44_100, 1, backend="numpy"), backend="numpy", fallback_reason=None)
        second = Mock(wraps=create_spectrum_engine(48_000, 2, backend="numpy"), backend="numpy", fallback_reason=None)

        def capture(device: str, stop: threading.Event, callback: object, language: str) -> None:
            """서로 다른 스트림 설정의 합성 블록을 순차적으로 입력한다."""
            callback(np.ones(100) * 0.5, 44_100)
            callback(np.zeros((2048, 2)), 48_000)

        with patch("app.monitor_capture_device", side_effect=capture), patch("app.create_spectrum_engine", side_effect=[first, second]) as factory:
            application._spectrum_monitor_worker(7, "synthetic-device", application.spectrum_stop_event, "ko")
        self.assertEqual(factory.call_count, 2)
        first.close.assert_called_once()
        second.close.assert_called_once()
        self.assertEqual(application.spectrum_frames.get_nowait()[1].rms_dbfs, -120.0)
        self.assertEqual([event[0] for event in _events(application)], ["spectrum_backend", "spectrum_backend", "spectrum_finished"])

    def test_capture_failure_closes_engine_before_terminal_event(self) -> None:
        """캡처 예외에서도 컨텍스트를 해제하고 종료 대신 오류 이벤트 하나만 보내야 한다."""
        application = _application()
        engine = Mock(backend="cpp", fallback_reason=None)
        engine.push.return_value = None

        def capture(device: str, stop: threading.Event, callback: object, language: str) -> None:
            """첫 블록 뒤 장치 연결 해제를 흉내 낸다."""
            callback(np.zeros((100, 2)), 48_000)
            raise RuntimeError("synthetic device disconnected")

        with patch("app.monitor_capture_device", side_effect=capture), patch("app.create_spectrum_engine", return_value=engine):
            application._spectrum_monitor_worker(7, "synthetic-device", application.spectrum_stop_event, "ko")
        engine.close.assert_called_once()
        events = _events(application)
        self.assertEqual([event[0] for event in events], ["spectrum_backend", "spectrum_error"])
        self.assertIsInstance(events[-1][2], RuntimeError)

    def test_engine_failure_and_close_failure_emit_only_one_error(self) -> None:
        """DSP 처리와 정리가 모두 실패해도 최초 오류를 보존하고 종료 이벤트를 중복하지 않는다."""
        application = _application()
        engine = Mock(backend="cpp", fallback_reason=None)
        engine.push.side_effect = ValueError("synthetic DSP failure")
        engine.close.side_effect = RuntimeError("synthetic cleanup failure")

        def capture(device: str, stop: threading.Event, callback: object, language: str) -> None:
            """처리 오류를 유발하는 합성 입력을 캡처 콜백에 보낸다."""
            callback(np.zeros((2048, 2)), 48_000)

        with patch("app.monitor_capture_device", side_effect=capture), patch("app.create_spectrum_engine", return_value=engine):
            application._spectrum_monitor_worker(7, "synthetic-device", application.spectrum_stop_event, "ko")
        engine.close.assert_called_once()
        events = _events(application)
        self.assertEqual([event[0] for event in events], ["spectrum_backend", "spectrum_error"])
        self.assertIsInstance(events[-1][2], ValueError)

    def test_stop_during_push_prevents_late_output_and_frees_engine(self) -> None:
        """진행 중인 DSP에서 중지 요청을 받으면 완료 프레임을 UI에 넣지 않고 정리한다."""
        application = _application()
        engine = Mock(backend="cpp", fallback_reason=None)

        def push(samples: np.ndarray) -> object:
            """DSP 작업 도중 중지 요청이 들어온 상황을 재현한다."""
            application.spectrum_stop_event.set()
            return object()

        def capture(device: str, stop: threading.Event, callback: object, language: str) -> None:
            """중지 직후 도착한 콜백이 추가 DSP에 진입하지 않는지 검사한다."""
            callback(np.zeros((2048, 2)), 48_000)
            callback(np.zeros((2048, 2)), 48_000)

        engine.push.side_effect = push
        with patch("app.monitor_capture_device", side_effect=capture), patch("app.create_spectrum_engine", return_value=engine):
            application._spectrum_monitor_worker(7, "synthetic-device", application.spectrum_stop_event, "ko")
        engine.push.assert_called_once()
        engine.close.assert_called_once()
        self.assertTrue(application.spectrum_frames.empty())

    def test_no_pcm_does_not_initialize_dsp(self) -> None:
        """첫 PCM 없이 종료된 세션에는 불필요한 네이티브 컨텍스트를 만들지 않는다."""
        application = _application()
        with patch("app.monitor_capture_device"), patch("app.create_spectrum_engine") as factory:
            application._spectrum_monitor_worker(7, "synthetic-device", application.spectrum_stop_event, "ko")
        factory.assert_not_called()
        self.assertEqual(_events(application), [("spectrum_finished", 7)])


class NativeBackendDisplayTests(unittest.TestCase):
    """스레드 이벤트와 표시 문구가 실제 현재 백엔드만 드러내는지 확인한다."""

    def test_backend_event_is_applied_only_on_ui_drain(self) -> None:
        """큐에 넣는 동작은 Tk 변수를 건드리지 않고 UI 이벤트 처리에서만 선택을 표시한다."""
        application = _application()
        application.events.put(("spectrum_backend", 7, "cpp", None))
        application.spectrum_backend_var.set.assert_not_called()
        application._drain_events()
        self.assertEqual(application.spectrum_backend, "cpp")
        self.assertIn("C++ PCM/FFT", application.spectrum_backend_var.set.call_args.args[0])

    def test_stale_stopping_closed_and_invalid_backend_events_are_ignored(self) -> None:
        """이전 세션·중지 이후·창 종료·잘못된 엔진 명칭이 현재 화면을 덮지 않아야 한다."""
        for scenario in ("stale", "stopping", "closed", "finished", "invalid"):
            with self.subTest(scenario=scenario):
                application = _application()
                application.spectrum_stop_requested = scenario == "stopping"
                application.closing = scenario == "closed"
                if scenario == "finished":
                    application.spectrum_worker = None
                application._apply_spectrum_backend(6 if scenario == "stale" else 7, "invalid" if scenario == "invalid" else "cpp", None)
                application.spectrum_backend_var.set.assert_not_called()
                self.assertIsNone(application.spectrum_backend)

    def test_fallback_labels_are_localized_and_do_not_expose_raw_errors(self) -> None:
        """대체 경로는 한영의 짧은 범주만 보여 주며 예외 속 개인 경로를 노출하지 않는다."""
        application = _application()
        for language in ("ko", "en"):
            application.language = language
            for reason in ("Native DSP DLL is not installed.", "ABI mismatch", "Private path C:/Users/secret/private.dll\nlong error"):
                application._apply_spectrum_backend(7, "numpy", reason)
                label = application.spectrum_backend_var.set.call_args.args[0]
                self.assertIn("NumPy", label)
                self.assertNotIn("secret", label)
                self.assertNotIn("\n", label)
                self.assertLess(len(label), 60)
                self.assertNotIn("secret", application._append_debug_log.call_args.args[0])

    def test_restart_clears_previous_backend_before_first_pcm(self) -> None:
        """재시작 후 첫 입력을 받기 전에는 지난 세션의 C++ 사용 표시를 남기지 않는다."""
        application = _application()
        application.spectrum_worker = None
        application.spectrum_backend = "cpp"
        application.spectrum_fallback_reason = None
        application.worker = None
        application.record_worker = None
        application.hardware_probe_active = False
        application.capture_device_id = "synthetic-device"
        application.result = None
        application._populate_reference_rows = Mock()
        application.reference_canvas = Mock()
        application.spectrum_status_var = Mock()
        application._update_analysis_availability = Mock()
        with patch("app.threading.Thread") as thread:
            application._toggle_spectrum_monitor()
        self.assertEqual(application.spectrum_session_id, 8)
        self.assertIsNone(application.spectrum_backend)
        self.assertNotIn("C++", application.spectrum_backend_var.set.call_args.args[0])
        thread.return_value.start.assert_called_once()


class NativeSelfTestIntegrationTests(unittest.TestCase):
    """자체 진단과 개발자 소스가 C++ 통합 여부를 실제로 검증하는지 확인한다."""

    def test_self_test_reports_explicit_fallback_without_claiming_native_parity(self) -> None:
        """DLL 없는 소스 실행은 대체 smoke를 검사하되 네이티브 동등성 통과라고 쓰지 않는다."""
        unavailable = {"available": False, "backend": "numpy", "abi_version": None, "library": "tonematch_dsp.dll", "error": "Native DLL missing"}
        with patch("app.native_runtime_info", return_value=unavailable):
            status = _self_test_native_dsp()
        self.assertFalse(status["available"])
        self.assertEqual(status["backend"], "numpy")
        self.assertTrue(status["smoke_ok"])
        self.assertFalse(status["parity_ok"])
        self.assertTrue(status["partial_buffer_reset_ok"])
        self.assertFalse(status["capture_device_tested"])

    def test_actual_native_self_test_checks_cpp_when_library_is_present(self) -> None:
        """실제 DLL이 제공된 환경에서는 자체 진단이 C++ 경로와 NumPy의 수치를 비교한다."""
        if not (MODULE_DIR / "resources" / "tonematch_dsp.dll").is_file():
            self.skipTest("Native DSP DLL has not been built in this source checkout")
        self.assertTrue(native_runtime_info()["available"], "The existing native DSP DLL must load successfully")
        status = _self_test_native_dsp()
        self.assertEqual(status["backend"], "cpp")
        self.assertTrue(status["available"])
        self.assertTrue(status["smoke_ok"])
        self.assertTrue(status["parity_ok"])
        self.assertGreater(status["frames_checked"], 0)

    def test_developer_block_includes_native_cpp_and_header(self) -> None:
        """개발자 DSP 블록에 Python 연결부와 실제 C++ 원문 및 공개 ABI가 포함돼야 한다."""
        code = code_for_block("features")
        self.assertIn("native_dsp.py", code)
        self.assertIn("tm_dsp_push", code)
        self.assertIn("native/tonematch_dsp.cpp", code)
        self.assertIn("native/tonematch_dsp.h", code)
        self.assertEqual(source_file_path("native/tonematch_dsp.cpp"), MODULE_DIR / "native" / "tonematch_dsp.cpp")


class NativeBackendLayoutTests(unittest.TestCase):
    """숨긴 최소 크기 화면에서 새 DSP 표시가 기존 레이아웃과 언어 전환을 망치지 않는지 검사한다."""

    def test_backend_labels_fit_minimum_window_without_clipping_heading_or_footer(self) -> None:
        """960×600 한영 화면에서 C++와 긴 대체 문구 전체가 제목 및 고정 진행 영역과 함께 보여야 한다."""
        root = tk.Tk()
        root.withdraw()
        try:
            with (
                patch.object(ToneMatchApp, "_load_settings"),
                patch.object(ToneMatchApp, "_save_settings"),
                patch.object(ToneMatchApp, "_refresh_capture_devices"),
                patch.object(root, "after"),
                patch("app._window_work_area", return_value=(0, 0, 992, 664)),
            ):
                application = ToneMatchApp(root)
                for language in ("ko", "en"):
                    application.language_var.set(LANGUAGE_LABELS[language])
                    application._change_language()
                    application.notebook.select(application.spectrum_tab)
                    for backend, reason in (("cpp", None), ("numpy", "Native DSP DLL is not installed."), ("numpy", "C++ initialization failed")):
                        with self.subTest(language=language, backend=backend, reason=reason):
                            application.spectrum_backend = backend
                            application.spectrum_fallback_reason = reason
                            application.spectrum_backend_var.set(application._spectrum_backend_text())
                            application.analysis_progress_percent = 100.0
                            application.analysis_elapsed_seconds = 105.0
                            application._refresh_analysis_progress()
                            application.status_var.set(tr("status.complete", language))
                            root.update_idletasks()
                            self.assertEqual(root.state(), "withdrawn")
                            self.assertEqual((root.winfo_width(), root.winfo_height()), (960, 600))
                            heading = application.spectrum_tab.grid_slaves(row=3, column=0)[0]
                            heading_label = heading.grid_slaves(row=0, column=0)[0]
                            backend_label = heading.grid_slaves(row=0, column=1)[0]
                            font = tkfont.Font(root=root, font=backend_label.cget("font"))
                            self.assertLessEqual(font.measure(application.spectrum_backend_var.get()) + 2, backend_label.winfo_width())
                            self.assertGreaterEqual(heading_label.winfo_height(), heading_label.winfo_reqheight())
                            self.assertGreaterEqual(heading_label.winfo_width(), heading_label.winfo_reqwidth())
                            self.assertLessEqual(heading_label.winfo_rootx() + heading_label.winfo_width(), backend_label.winfo_rootx())
                            footer = application.progress.master
                            for widget in (heading, heading_label, backend_label, footer, application.progress, application.status_text, application.result_title_label, application.result_summary_label):
                                x = widget.winfo_rootx() - root.winfo_rootx()
                                y = widget.winfo_rooty() - root.winfo_rooty()
                                self.assertGreaterEqual(x, 0)
                                self.assertGreaterEqual(y, 0)
                                self.assertLessEqual(x + widget.winfo_width(), 960)
                                self.assertLessEqual(y + widget.winfo_height(), 600)
                            self.assertGreaterEqual(application.status_text.winfo_height(), application.status_text.winfo_reqheight())
        finally:
            root.destroy()

    def test_language_rebuild_preserves_last_backend_and_localizes_reason(self) -> None:
        """캡처 종료 뒤 언어 전환으로 UI를 다시 만들어도 마지막 엔진과 대체 이유가 보존돼야 한다."""
        root = tk.Tk()
        root.withdraw()
        try:
            with (
                patch.object(ToneMatchApp, "_load_settings"),
                patch.object(ToneMatchApp, "_save_settings"),
                patch.object(ToneMatchApp, "_refresh_capture_devices"),
                patch.object(root, "after"),
                patch("app._window_work_area", return_value=(0, 0, 992, 664)),
            ):
                application = ToneMatchApp(root)
                for backend, reason, key in (
                    ("cpp", None, "status.spectrum_backend_cpp"),
                    ("numpy", "Native DSP DLL is not installed.", "status.spectrum_backend_numpy_missing"),
                    ("numpy", "ABI mismatch", "status.spectrum_backend_numpy_abi"),
                    ("numpy", "C++ initialization failed", "status.spectrum_backend_numpy_unavailable"),
                ):
                    application.spectrum_backend = backend
                    application.spectrum_fallback_reason = reason
                    for language in ("en", "ko"):
                        with self.subTest(language=language, backend=backend, reason=reason):
                            previous_variable = application.spectrum_backend_var
                            application.language_var.set(LANGUAGE_LABELS[language])
                            application._change_language()
                            root.update_idletasks()
                            self.assertIsNot(application.spectrum_backend_var, previous_variable)
                            self.assertEqual(application.spectrum_backend, backend)
                            self.assertEqual(application.spectrum_fallback_reason, reason)
                            self.assertEqual(application.spectrum_backend_var.get(), tr(key, language))
                            self.assertEqual(root.state(), "withdrawn")
        finally:
            root.destroy()

    def test_failure_status_does_not_only_blame_input_connection(self) -> None:
        """DSP 오류도 같은 실패 이벤트를 쓰므로 안내가 장치 연결만 원인으로 단정하지 않아야 한다."""
        for language in ("ko", "en"):
            with self.subTest(language=language):
                self.assertIn("DSP", tr("status.spectrum_failed", language))


if __name__ == "__main__":
    unittest.main()
