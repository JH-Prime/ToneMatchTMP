"""실제 창을 열지 않고 코드 타임라인의 출처·미확정·보조 분석 표시를 검증한다."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest


MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from app import ToneMatchApp  # noqa: E402
from i18n import tr, voicing_context_lines  # noqa: E402


class RecordingText:
    """Tk 창 대신 삽입 문자열과 태그·읽기 전용 상태를 기록한다."""

    def __init__(self) -> None:
        """문자열 조각과 위젯 호출 기록을 빈 상태로 준비한다."""
        self.fragments: list[tuple[str, str]] = []
        self.calls: list[tuple] = []
        self.state = "disabled"

    def configure(self, *, state: str) -> None:
        """편집 가능 상태 변경을 기록한다."""
        self.state = state
        self.calls.append(("configure", state))

    def delete(self, start: str, end: str) -> None:
        """새 분석이 이전 타임라인을 제거하는지 확인하도록 내용을 비운다."""
        self.calls.append(("delete", start, end))
        self.fragments.clear()

    def insert(self, position: str, text: str, tag: str = "") -> None:
        """문자열과 표시 태그를 원문 그대로 보존한다."""
        self.calls.append(("insert", position, tag))
        self.fragments.append((text, tag))

    def see(self, position: str) -> None:
        """완료 후 화면을 처음으로 되돌리는 요청을 기록한다."""
        self.calls.append(("see", position))

    def text(self, tag: str | None = None) -> str:
        """전체 또는 특정 태그로 표시한 문자열만 결합한다."""
        return "".join(text for text, item_tag in self.fragments if tag is None or item_tag == tag)


def _known_event() -> dict:
    """역위와 운지 후보를 가진 명확한 테스트 이벤트를 만든다."""
    return {
        "start_seconds": 1.0,
        "end_seconds": 3.0,
        "chord_type": "major",
        "symbol": "C/E",
        "confidence": 0.81,
        "pitch_classes": [0, 4, 7],
        "bass_pc": 4,
        "register": "low",
        "spacing": "close",
        "inversion": "inversion",
        "candidate_shapes": [{"label": "TEST_SHAPE_ONLY", "frets_low_e_to_high_e": [0, 3, 2, 0, 1, 0]}],
    }


def _render(analysis: dict, language: str = "ko", result: dict | None = None) -> RecordingText:
    """앱 생성이나 장치 접근 없이 실제 렌더 함수에 기록 위젯을 주입한다."""
    widget = RecordingText()
    application = SimpleNamespace(
        result=result,
        language=language,
        voicing_text=widget,
        _format_time=ToneMatchApp._format_time,
    )
    ToneMatchApp._render_voicing(application, analysis)
    return widget


class VoicingDisplayTests(unittest.TestCase):
    """보조 믹스 분석이 실제 기타 운지나 확정 코드로 오인되지 않도록 검사한다."""

    def test_original_mix_hides_guitar_shapes_and_slash_bass_without_mutation(self) -> None:
        """원본 믹스에 남은 구형 역위·운지 정보도 표시하지 않고 입력 결과는 보존해야 한다."""
        analysis = {
            "analysis_source": "original_mix",
            "source_start_seconds": 60.0,
            "fallback": {"selected": True, "attempted": True},
            "events": [_known_event()],
        }
        original = deepcopy(analysis)
        for language in ("ko", "en"):
            with self.subTest(language=language):
                widget = _render(analysis, language)
                self.assertIn("01:01–01:03   C   81%", widget.text("event"))
                self.assertNotIn("C/E", widget.text())
                self.assertNotIn("TEST_SHAPE_ONLY", widget.text())
                self.assertNotIn("E A D G B e", widget.text())
                self.assertIn(tr("ui.voicing_source_original_mix", language), widget.text("intro"))
                self.assertIn(tr("ui.voicing_fallback_selected", language), widget.text("intro"))
                self.assertIn(tr("ui.voicing_mix_profile", language), widget.text("detail"))
                self.assertNotIn(tr("ui.playable_shapes", language), widget.text())
        self.assertEqual(analysis, original)

    def test_guitar_source_retains_inversion_and_playable_candidates(self) -> None:
        """실제 기타 입력에서 구한 역위와 운지 후보는 보조 믹스 규칙으로 지우지 않아야 한다."""
        for source in ("guitar_stem", "provided_audio"):
            with self.subTest(source=source):
                widget = _render({"analysis_source": source, "events": [_known_event()]})
                self.assertIn("00:01–00:03   C/E   81%", widget.text("event"))
                self.assertIn("TEST_SHAPE_ONLY · E A D G B e = 0 3 2 0 1 0", widget.text("detail"))
                self.assertIn(tr("ui.playable_shapes", "ko"), widget.text("warning"))

    def test_unknown_intervals_have_no_fake_confidence_or_shapes(self) -> None:
        """미확정 이벤트에 잘못 남은 신뢰도·코드·운지도 확정 결과로 표시하지 않아야 한다."""
        event = _known_event()
        event.update(chord_type="unknown", confidence=1.0, symbol="FAKE_CHORD")
        for language in ("ko", "en"):
            with self.subTest(language=language):
                widget = _render({"source_start_seconds": 90.0, "events": [event]}, language)
                self.assertIn("01:31–01:33   " + tr("ui.voicing_unknown", language), widget.text("warning"))
                self.assertIn(tr("ui.voicing_empty", language), widget.text("warning"))
                self.assertEqual(widget.text("event"), "")
                self.assertNotIn("100%", widget.text())
                self.assertNotIn("FAKE_CHORD", widget.text())
                self.assertNotIn("TEST_SHAPE_ONLY", widget.text())

    def test_legacy_source_offset_and_separation_are_normalized_without_mutation(self) -> None:
        """출처 필드가 없는 이전 결과도 원본 구간 시작과 기타 분리 여부를 복사본에만 반영해야 한다."""
        analysis = {"events": [_known_event()]}
        original_analysis = deepcopy(analysis)
        for used, source in ((True, "guitar_stem"), (False, "provided_audio")):
            with self.subTest(used=used):
                result = {"source": {"start_seconds": 120.0}, "source_separation": {"used": used}, "chord_voicing": analysis}
                original_result = deepcopy(result)
                widget = _render(analysis, result=result)
                self.assertIn("02:01–02:03", widget.text("event"))
                self.assertIn(tr(f"ui.voicing_source_{source}", "ko"), widget.text("intro"))
                self.assertIn(tr("ui.voicing_time_note", "ko", start=120.0), widget.text("intro"))
                self.assertEqual(analysis, original_analysis)
                self.assertEqual(result, original_result)

    def test_explicit_chord_metadata_takes_precedence_over_legacy_result(self) -> None:
        """코드 전용 출처와 선택 구간 정보가 있으면 외부 결과의 기본값으로 덮어쓰지 않아야 한다."""
        widget = _render(
            {"analysis_source": "original_mix", "source_start_seconds": 30.0, "events": [_known_event()]},
            result={"source": {"start_seconds": 120.0}, "source_separation": {"used": False}},
        )
        self.assertIn("00:31–00:33   C   81%", widget.text("event"))
        self.assertIn(tr("ui.voicing_source_original_mix", "ko"), widget.text("intro"))
        self.assertNotIn(tr("ui.voicing_source_provided_audio", "ko"), widget.text("intro"))

    def test_bilingual_diagnostics_and_truncated_timeline_notice_are_rendered(self) -> None:
        """검출 프레임·입력 크기·타임라인 생략 안내는 두 언어에서 같은 실제 수치를 보여야 한다."""
        analysis = {
            "analysis_source": "guitar_stem",
            "source_start_seconds": 15.0,
            "diagnostics": {
                "reliable_frame_count": 6,
                "analyzed_frame_count": 10,
                "active_frame_count": 8,
                "input_rms_dbfs": -63.245,
                "events_truncated": True,
                "event_count_before_limit": 102,
            },
            "events": [_known_event()],
        }
        for language in ("ko", "en"):
            with self.subTest(language=language):
                expected = tr("ui.voicing_diagnostics", language, reliable=6, total=10, active=8, rms="-63.2")
                warning = tr("ui.voicing_truncated", language, total=102, shown=1)
                lines = voicing_context_lines(analysis, language)
                self.assertIn(expected, lines)
                self.assertIn(warning, lines)
                widget = _render(analysis, language)
                self.assertIn(expected, widget.text("intro"))
                self.assertIn(warning, widget.text("intro"))
                self.assertIn(tr("ui.voicing_time_note", language, start=15.0), widget.text("intro"))

    def test_fallback_failure_and_empty_hints_are_truthful_in_both_languages(self) -> None:
        """보조 분석 실패·더 나은 근거 없음·무음과 일반 미확정 안내를 구분해야 한다."""
        for language in ("ko", "en"):
            for reason, key in (("fallback_unavailable", "ui.voicing_fallback_unavailable"), ("no_better_harmony", "ui.voicing_fallback_no_better")):
                with self.subTest(language=language, reason=reason):
                    analysis = {
                        "analysis_source": "guitar_stem",
                        "fallback": {"attempted": True, "selected": False, "reason": reason, "primary_input_rms_dbfs": -63.0},
                        "diagnostics": {"active_frame_count": 0, "reason": "silent_or_very_quiet"},
                        "events": [],
                    }
                    lines = voicing_context_lines(analysis, language)
                    self.assertIn(tr(key, language), lines)
                    self.assertIn(tr("ui.voicing_weak_stem", language), lines)
                    self.assertIn(tr("ui.voicing_hint_quiet", language), lines)
                    self.assertNotIn(tr("ui.voicing_fallback_selected", language), lines)
                    analysis["diagnostics"] = {"active_frame_count": 7, "reason": "insufficient_polyphonic_evidence"}
                    self.assertIn(tr("ui.voicing_hint_generic", language), voicing_context_lines(analysis, language))

    def test_nonfinite_level_and_unrecognized_source_use_safe_display(self) -> None:
        """유한하지 않은 음량이나 알 수 없는 출처가 있어도 잘못된 숫자와 기타 출처를 만들지 않아야 한다."""
        for level in (float("nan"), float("inf"), -float("inf")):
            with self.subTest(level=level):
                analysis = {"analysis_source": "future_source", "diagnostics": {"input_rms_dbfs": level}, "events": []}
                lines = voicing_context_lines(analysis, "en")
                self.assertEqual(lines[0], tr("ui.voicing_source_provided_audio", "en"))
                self.assertIn(tr("ui.voicing_diagnostics", "en", reliable=0, total=0, active=0, rms="—"), lines)

    def test_renderer_replaces_content_then_returns_to_read_only_top(self) -> None:
        """이전 타임라인을 비우고 새 결과 끝에서 읽기 전용·맨 위 스크롤 상태로 복귀해야 한다."""
        widget = _render({"events": [_known_event()]})
        self.assertEqual(widget.calls[:2], [("configure", "normal"), ("delete", "1.0", "end")])
        self.assertEqual(widget.calls[-2:], [("configure", "disabled"), ("see", "1.0")])
        self.assertEqual(widget.state, "disabled")
        self.assertIn(tr("ui.voicing_limit", "ko"), widget.text("warning"))


if __name__ == "__main__":
    unittest.main()
