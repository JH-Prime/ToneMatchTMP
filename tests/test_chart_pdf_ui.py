"""앱의 비동기 PDF 저장과 사용자 요청에 한정된 인쇄 미리보기를 확인한다."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pypdf import PdfReader
from test_chord_chart_ui import hidden_chart_application, chart_result
from test_playback import wait_for


class ChartPdfUiTests(unittest.TestCase):
    def test_save_and_explicit_preview_do_not_send_a_print_job(self):
        with tempfile.TemporaryDirectory() as folder, hidden_chart_application(Path(folder)) as (_root, app):
            app._show_result(chart_result())
            app._apply_chord_edit(0, "Dm9")
            path = Path(folder) / "saved.pdf"
            with (patch("app.filedialog.asksaveasfilename", return_value=str(path)),
                  patch("app.os.startfile") as launch):
                app._export_chart_pdf()
                wait_for(lambda: (app._drain_events(), app.pdf_worker is None)[1])
                launch.assert_not_called()
                self.assertIn("Dm9 *", "\n".join(page.extract_text() for page in PdfReader(path).pages))
                preview_path = Path(folder) / "preview.pdf"
                with patch("app.filedialog.asksaveasfilename", return_value=str(preview_path)):
                    app._export_chart_pdf(preview=True)
                    wait_for(lambda: (app._drain_events(), app.pdf_worker is None)[1])
                launch.assert_called_once_with(str(preview_path))

    def test_error_does_not_launch_preview_or_leave_a_busy_worker(self):
        with tempfile.TemporaryDirectory() as folder, hidden_chart_application(Path(folder)) as (_root, app):
            app._show_result(chart_result())
            path = Path(folder) / "existing.pdf"
            path.write_bytes(b"old")
            with (patch("app.filedialog.asksaveasfilename", return_value=str(path)),
                  patch("app.os.startfile") as launch,
                  patch("app.messagebox.showerror") as error):
                app._export_chart_pdf(preview=True)
                wait_for(lambda: (app._drain_events(), app.pdf_worker is None)[1])
                launch.assert_not_called()
                error.assert_called_once()
                self.assertEqual(path.read_bytes(), b"old")
