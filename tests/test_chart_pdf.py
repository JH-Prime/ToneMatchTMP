"""PDF를 다시 열어 마디·수정·한글·밀집 이벤트와 안전한 저장을 검증한다."""

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pypdf import PdfReader
from chord_edits import set_correction


def pdf_result(language="ko", dense=False):
    """저작권 음원 없이 코드 후보와 긴 페이지를 재현한다."""
    events = [
        {"start_seconds": float(i), "end_seconds": i + 1., "symbol": "Cmaj7/E",
         "chord_type": "major7", "confidence": .72, "pitch_classes": [0, 4, 7, 11],
         "evidence": {"observed_pitch_classes": [0, 4, 7, 11], "bass_pc": 4},
         "alternatives": [{"symbol": "Em/C"}]}
        for i in range(35)
    ]
    if dense:
        events = [{**events[0], "start_seconds": i / 40, "end_seconds": (i + 1) / 40,
                   "symbol": "G7sus4" if i % 2 else "Cmaj7/E"} for i in range(80)]
    return {"language": language, "source": {"file_name": "한글 샘플.wav", "start_seconds": 30.,
            "duration_seconds": 35.}, "features": {"bpm": 120},
            "chord_voicing": {"analysis_source": "original_mix", "source_start_seconds": 30., "events": events}}


class ChartPdfTests(unittest.TestCase):
    def test_a4_pages_manual_edits_korean_evidence_and_no_fingering(self):
        from chart_pdf import save_chart_pdf
        with tempfile.TemporaryDirectory() as folder:
            result = set_correction(pdf_result(), 0, "Dm9")
            original = deepcopy(result)
            path = Path(folder) / "chart.pdf"
            metadata = save_chart_pdf(result, path)
            pages = PdfReader(path).pages
            text = "\n".join(page.extract_text() for page in pages)
            self.assertEqual(metadata["chart_pages"], 2)
            self.assertEqual(metadata["page_count"], len(pages))
            self.assertIn("한글 샘플.wav", text)
            self.assertIn("Dm9 *", text)
            self.assertIn("Cmaj7/E", text)
            self.assertIn("Em/C", text)
            self.assertIn("30.00", text)
            self.assertNotIn("frets", text.lower())
            self.assertEqual(result, original)
            for page in pages:
                self.assertAlmostEqual(float(page.mediabox.width), 595.28, places=1)
                self.assertAlmostEqual(float(page.mediabox.height), 841.89, places=1)

    def test_dense_events_survive_in_linked_details(self):
        from chart_pdf import save_chart_pdf
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "dense.pdf"
            metadata = save_chart_pdf(pdf_result("en", dense=True), path)
            text = "\n".join(page.extract_text() for page in PdfReader(path).pages)
            self.assertGreater(metadata["detail_pages"], 0)
            for index in range(80):
                self.assertIn(f"#{index + 1} ", text)
            self.assertIn("G7sus4", text)
            self.assertIn("?", text)

    def test_existing_destination_cancel_and_partial_cleanup(self):
        from chart_pdf import save_chart_pdf, PdfExportCancelled
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "chart.pdf"
            path.write_bytes(b"existing")
            with self.assertRaises(FileExistsError):
                save_chart_pdf(pdf_result(), path)
            self.assertEqual(path.read_bytes(), b"existing")
            target = Path(folder) / "cancel.pdf"
            with self.assertRaises(PdfExportCancelled):
                save_chart_pdf(pdf_result(), target, cancel_requested=lambda: True)
            self.assertFalse(target.exists())
            with patch("chart_pdf._draw_chart_page", side_effect=RuntimeError("render failed")):
                with self.assertRaises(RuntimeError):
                    save_chart_pdf(pdf_result(), target)
            self.assertEqual(list(Path(folder).iterdir()), [path])
