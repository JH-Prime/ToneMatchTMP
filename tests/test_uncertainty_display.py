"""미확정 근거를 실제 렌더러로 검사하되 창·브라우저·오디오를 열지 않는다."""

from copy import deepcopy
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from app import ToneMatchApp
from chord_chart import build_chord_chart
from chord_edits import effective_voicing, set_correction
from chart_pdf import _detail_lines, _font
from i18n import tr
from report import save_html


def uncertain_result(language="en", reason="weak_match"):
    """후보는 보유하지만 어떤 코드도 확정하지 않은 합성 분석 결과."""
    return {
        "analysis_kind": "chords", "language": language, "features": {}, "recipes": [],
        "warnings": [], "application_steps": [], "model_guide": "CQT",
        "source": {"file_name": "synthetic.wav", "start_seconds": 0.,
                   "end_seconds": 1., "duration_seconds": 1.},
        "chord_voicing": {"analysis_source": "original_mix", "events": [{
            "start_seconds": 0., "end_seconds": 1., "symbol": "?", "chord_type": "unknown",
            "confidence": 0., "pitch_classes": [],
            "evidence": {"uncertainty_reason": reason, "observed_pitch_classes": [0, 4, 7, 11]},
            "alternatives": [{"symbol": "Cmaj7", "root_pc": 0, "chord_type": "major7", "score": .65}],
        }]},
    }


def ui_text(result):
    """생산 렌더러의 위젯 경계만 가짜 객체로 대체한다."""
    view = SimpleNamespace(language=result["language"], result=result, voicing_text=Mock(),
                           _format_time=ToneMatchApp._format_time)
    ToneMatchApp._render_voicing(view, effective_voicing(result))
    return "".join(call.args[1] for call in view.voicing_text.insert.call_args_list)


def html_text(result):
    """HTML 저장 경계만 가로채고 실제 문서 생성 경로를 검사한다."""
    with patch("pathlib.Path.write_text") as write:
        save_html(result, "not-written.html")
    return write.call_args.args[0]


def pdf_detail_text(result):
    """PDF의 실제 줄바꿈·상세 생성 경로를 사용하되 파일은 생성하지 않는다."""
    _font()
    analysis = effective_voicing(result)
    chart = build_chord_chart(analysis, bpm=120, duration_seconds=1.)
    return "\n".join(_detail_lines(chart["pages"][0], analysis["events"], result["language"]))


class UncertaintyDisplayTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch("tkinter.Tk", side_effect=AssertionError("No windows allowed")))
        self.enterContext(patch("tkinter.Toplevel", side_effect=AssertionError("No windows allowed")))

    def test_unknown_ui_shows_candidates_and_observed_notes_below_unresolved_label(self):
        for language in ("ko", "en"):
            with self.subTest(language=language):
                result = uncertain_result(language)
                text = ui_text(result)
                self.assertIn("Cmaj7", text)
                self.assertIn(tr("ui.voicing_observed_notes", language), text)
                self.assertLess(text.index(tr("ui.voicing_unknown", language)), text.index("Cmaj7"))
                self.assertNotIn(tr("ui.voicing_empty", language), text)
                self.assertIn(tr("ui.voicing_candidates_available", language), text)

    def test_unknown_html_shows_candidates_and_evidence_without_promoting_primary_symbol(self):
        text = html_text(uncertain_result())
        self.assertIn("Cmaj7", text)
        self.assertIn(tr("ui.voicing_observed_notes", "en"), text)
        self.assertIn("<b>?</b>", text)
        self.assertNotIn("<b>Cmaj7</b>", text)

    def test_weak_match_reason_is_consistent_in_all_details(self):
        result = uncertain_result()
        expected = "Chord candidates have weak or competing evidence."
        for render in (ui_text, html_text, pdf_detail_text):
            with self.subTest(renderer=render.__name__):
                self.assertIn(expected, render(result))

    def test_silent_unknown_has_reason_but_no_invented_chord(self):
        result = uncertain_result(reason="low_signal")
        event = result["chord_voicing"]["events"][0]
        event["alternatives"] = []
        event["evidence"]["observed_pitch_classes"] = []
        for render in (ui_text, html_text, pdf_detail_text):
            with self.subTest(renderer=render.__name__):
                text = render(result)
                self.assertIn("The signal is too quiet to identify a chord.", text)
                self.assertNotIn("Cmaj7", text)
                self.assertNotIn("N.C.", text)

    def test_legacy_unknown_does_not_invent_a_specific_reason(self):
        result = uncertain_result()
        result["chord_voicing"]["events"][0]["evidence"] = {}
        result["chord_voicing"]["events"][0]["alternatives"] = []
        for render in (ui_text, html_text, pdf_detail_text):
            with self.subTest(renderer=render.__name__):
                text = render(result)
                self.assertIn("There is not enough evidence to identify a chord.", text)
                self.assertNotIn("too quiet", text)

    def test_html_escapes_unknown_candidate_names(self):
        result = uncertain_result()
        result["chord_voicing"]["events"][0]["alternatives"][0]["symbol"] = "<script>bad</script>"
        text = html_text(result)
        self.assertIn("&lt;script&gt;bad&lt;/script&gt;", text)
        self.assertNotIn("<script>bad</script>", text)

    def test_unknown_template_notes_are_not_claimed_as_observations(self):
        result = uncertain_result()
        event = result["chord_voicing"]["events"][0]
        event["pitch_classes"] = [2, 6, 9]
        event["evidence"].pop("observed_pitch_classes")
        for render in (ui_text, html_text, pdf_detail_text):
            with self.subTest(renderer=render.__name__):
                self.assertNotIn("D · F♯ · A", render(result))

    def test_manual_correction_hides_stale_uncertainty_and_restoration_keeps_it(self):
        original = uncertain_result()
        snapshot = deepcopy(original)
        corrected = set_correction(original, 0, "Dm")
        for render in (ui_text, html_text, pdf_detail_text):
            with self.subTest(renderer=render.__name__):
                text = render(corrected)
                self.assertIn("Dm", text)
                self.assertNotIn("Cmaj7", text)
                self.assertNotIn("weak or competing", text)
                restored = render(set_correction(corrected, 0, None))
                self.assertIn("Cmaj7", restored)
        self.assertEqual(original, snapshot)


if __name__ == "__main__":
    unittest.main()
