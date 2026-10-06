"""16마디 표시 격자가 코드 시점·공백·분석 출처를 보존하는지 검증한다."""

from __future__ import annotations

import copy
import math
from pathlib import Path
import sys
import unittest


MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from chord_chart import build_chord_chart, initial_chart_settings  # noqa: E402


def _event(start: float, end: float, symbol: str = "C", chord_type: str = "major") -> dict:
    """표시 검증에 필요한 최소 분석 이벤트를 만든다."""
    return {"start_seconds": start, "end_seconds": end, "symbol": symbol,
            "chord_type": chord_type, "root_pc": 0, "candidate_shapes": [], "confidence": 0.7}


def _bars(chart: dict) -> list[dict]:
    """모든 페이지의 마디를 순서대로 모아 테스트 가독성을 높인다."""
    return [bar for page in chart["pages"] for bar in page["bars"]]


class ChordChartTests(unittest.TestCase):
    """수동 격자의 안전한 페이지화와 원본 시간 보존을 확인한다."""

    def test_sixteen_bar_pages_have_four_bar_rows(self) -> None:
        """16마디 페이지와 4마디 행을 만들고 마지막 부분 페이지도 유지한다."""
        chart = build_chord_chart({"events": [_event(0, 66)]}, bpm=120)
        self.assertEqual(chart["bar_count"], 33)
        self.assertEqual([len(page["bars"]) for page in chart["pages"]], [16, 16, 1])
        self.assertEqual([len(row) for row in chart["pages"][0]["rows"]], [4, 4, 4, 4])
        self.assertEqual(chart["pages"][1]["first_bar_number"], 17)
        self.assertEqual(chart["pages"][2]["last_bar_number"], 33)
        self.assertFalse(chart["automatic_downbeat"])
        self.assertEqual(chart["grid_mode"], "manual_constant_tempo")

    def test_changes_gaps_continuations_and_absolute_times_are_preserved(self) -> None:
        """한 마디 안의 코드 변경·미상 공백·다음 마디 지속을 모두 보존한다."""
        voicing = {"source_start_seconds": 90, "analysis_source": "guitar_stem", "events": [
            _event(0.25, 0.75), _event(1.0, 2.7, "Dm", "minor"), _event(2.7, 3.0, "?", "unknown")]}
        chart = build_chord_chart(voicing, bpm=120, duration_seconds=4)
        bars = _bars(chart)
        self.assertEqual([item["label"] for item in bars[0]["segments"]], ["?", "C", "?", "Dm"])
        self.assertEqual([item["label"] for item in bars[1]["segments"]], ["Dm", "?", "?"])
        c = bars[0]["segments"][1]
        self.assertEqual((c["start_seconds"], c["end_seconds"]), (0.25, 0.75))
        self.assertEqual((c["absolute_start_seconds"], c["absolute_end_seconds"]), (90.25, 90.75))
        self.assertEqual((c["start_beat"], c["end_beat"]), (1.5, 2.5))
        self.assertEqual((c["start_fraction"], c["end_fraction"]), (0.125, 0.375))
        self.assertTrue(bars[0]["segments"][-1]["continues_to_next"])
        self.assertTrue(bars[1]["segments"][0]["continues_from_previous"])
        self.assertFalse(bars[1]["segments"][0]["continues_to_next"])
        self.assertIsNone(bars[0]["segments"][0]["event_index"])
        self.assertEqual(bars[1]["segments"][1]["event_index"], 2)
        self.assertEqual(c["source_kind"], "guitar_stem")

    def test_pickup_and_multiple_preroll_bars_are_not_dropped(self) -> None:
        """첫 강박 이전 구간을 0 또는 음수 마디로 표시해 못갖춘마디를 보존한다."""
        chart = build_chord_chart({"events": [_event(0, 8)]}, bpm=120, first_downbeat_seconds=5)
        bars = _bars(chart)
        self.assertEqual([bar["number"] for bar in bars], [-2, -1, 0, 1, 2])
        self.assertEqual([bar["is_pickup"] for bar in bars], [True, True, True, False, False])
        self.assertEqual(bars[0]["start_seconds"], 0)
        self.assertEqual(bars[0]["end_seconds"], 1)
        self.assertEqual(bars[0]["segments"][0]["start_beat"], 3)
        self.assertTrue(bars[0]["is_partial"])
        self.assertEqual(sum(bar["end_seconds"] - bar["start_seconds"] for bar in bars), 8)

    def test_first_downbeat_before_segment_keeps_bar_number(self) -> None:
        """첫 강박이 분석 구간 앞에 있으면 해당 원래 마디 번호를 유지한다."""
        bars = _bars(build_chord_chart({"events": [_event(0, 3)]}, bpm=120, first_downbeat_seconds=-3))
        self.assertEqual([bar["number"] for bar in bars], [2, 3])
        self.assertEqual(bars[0]["segments"][0]["start_fraction"], 0.5)
        self.assertFalse(any(bar["is_pickup"] for bar in bars))

    def test_exact_boundaries_do_not_make_empty_bars_or_segments(self) -> None:
        """마디 끝에 맞는 코드가 다음 마디에 길이 0인 구간으로 중복되지 않는다."""
        for bpm in (120, 137.3, 300):
            duration = 60 / bpm * 4 * 32
            boundary = duration / 2
            with self.subTest(bpm=bpm):
                chart = build_chord_chart({"events": [_event(0, boundary), _event(boundary, duration, "G")]}, bpm=bpm)
                self.assertEqual(chart["bar_count"], 32)
                self.assertEqual(len(chart["pages"]), 2)
                self.assertTrue(all(len(bar["segments"]) == 1 for bar in _bars(chart)))
                self.assertTrue(all(item["end_seconds"] > item["start_seconds"] for bar in _bars(chart) for item in bar["segments"]))

    def test_more_than_ninety_six_events_and_truncation_notice_survive(self) -> None:
        """기존 96개 한도를 넘는 이벤트와 이전 분석의 축약 경고를 그대로 유지한다."""
        events = [_event(index / 4, (index + 1) / 4, "C" if index % 2 else "G") for index in range(257)]
        chart = build_chord_chart({"events": events, "diagnostics": {"events_truncated": True, "event_count_before_limit": 301}}, bpm=120)
        observed = {item["event_index"] for bar in _bars(chart) for item in bar["segments"]}
        self.assertEqual(observed, set(range(257)))
        self.assertTrue(chart["diagnostics"]["events_truncated"])
        self.assertEqual(chart["diagnostics"]["event_count_before_limit"], 301)
        self.assertEqual(chart["event_count"], 257)

    def test_original_mix_keeps_slash_bass_without_guitar_shapes(self) -> None:
        """원본 믹스도 분수코드는 보존하고 기타 운지는 표시하지 않는다."""
        event = _event(0, 2, "C6/9/E", "6add9")
        event["candidate_shapes"] = [{"frets_low_e_to_high_e": [-1, 3, 2, 0, 1, 0]}]
        voicing = {"analysis_source": "original_mix", "events": [event]}
        before = copy.deepcopy(voicing)
        segment = _bars(build_chord_chart(voicing, bpm=120))[0]["segments"][0]
        self.assertEqual(segment["label"], "C6/9/E")
        self.assertEqual(segment["candidate_shapes"], [])
        self.assertEqual(segment["source_kind"], "original_mix")
        self.assertEqual(voicing, before)

    def test_legacy_shapes_are_hidden_without_mutating_analysis(self) -> None:
        """구형 기타 분석도 운지는 숨기고 원본 자료는 보존한다."""
        event = _event(0, 4)
        event["candidate_shapes"] = [{"frets_low_e_to_high_e": [-1, 3, 2, 0, 1, 0], "detected": False}]
        segment = _bars(build_chord_chart({"events": [event]}, bpm=120))[0]["segments"][0]
        self.assertEqual(segment["candidate_shapes"], [])
        self.assertEqual(event["candidate_shapes"][0]["frets_low_e_to_high_e"][1], 3)

    def test_missing_events_show_unknown_and_empty_results_stay_empty(self) -> None:
        """분석 이벤트가 없을 때만 전체 길이만큼 미상 구간을 표시한다."""
        empty = build_chord_chart({}, bpm=120)
        self.assertEqual(empty["pages"], [])
        self.assertEqual((empty["page_count"], empty["segment_count"]), (0, 0))
        bars = _bars(build_chord_chart({}, bpm=120, duration_seconds=5))
        self.assertEqual(len(bars), 3)
        self.assertTrue(all(item["unknown"] for bar in bars for item in bar["segments"]))
        self.assertTrue(all(item["event_index"] is None for bar in bars for item in bar["segments"]))

    def test_short_duration_is_extended_instead_of_dropping_events(self) -> None:
        """이벤트보다 짧은 오래된 길이 값 때문에 후반 코드가 사라지지 않게 한다."""
        chart = build_chord_chart({"events": [_event(0, 5)]}, bpm=120, duration_seconds=2)
        self.assertEqual(chart["duration_seconds"], 5)
        self.assertTrue(chart["diagnostics"]["duration_extended_for_events"])
        self.assertEqual(_bars(chart)[-1]["end_seconds"], 5)

    def test_overlaps_and_unsorted_input_preserve_original_event_indexes(self) -> None:
        """겹치거나 정렬되지 않은 입력을 버리지 않고 원래 인덱스와 경고를 유지한다."""
        chart = build_chord_chart({"events": [_event(1, 3, "G"), _event(0, 2, "C")]}, bpm=120)
        self.assertTrue(chart["diagnostics"]["overlapping_events"])
        first = _bars(chart)[0]["segments"]
        self.assertEqual([item["event_index"] for item in first], [1, 0])
        self.assertEqual([item["label"] for item in first], ["C", "G"])

    def test_configuration_ranges_and_finite_values_are_validated(self) -> None:
        """잘못된 수치와 과도한 할당 요청을 명확한 오류로 거절한다."""
        invalid = [{"bpm": value} for value in (0, 19.9, 301, math.nan, math.inf, None, True)]
        invalid += [{"bpm": 120, "beats_per_bar": value} for value in (1, 13, 3.5, False)]
        invalid += [{"bpm": 120, "page_size": value} for value in (0, 17, 2.5)]
        invalid += [{"bpm": 120, "first_downbeat_seconds": value} for value in (math.nan, math.inf, 1e10)]
        invalid += [{"bpm": 120, "duration_seconds": value} for value in (-1, math.nan, math.inf, 20_002, 1e308)]
        for options in invalid:
            with self.subTest(options=options), self.assertRaises(ValueError):
                build_chord_chart({}, **options)
        for event in (_event(-1, 2), _event(2, 2), _event(2, 1), _event(0, math.inf)):
            with self.subTest(event=event), self.assertRaises(ValueError):
                build_chord_chart({"events": [event]}, bpm=120)

    def test_meter_and_partial_final_bar_are_supported(self) -> None:
        """지원 박자의 마디 길이를 사용하고 끝의 불완전 마디도 표시한다."""
        chart = build_chord_chart({"events": [_event(0, 4)]}, bpm=120, beats_per_bar=3)
        self.assertEqual(chart["seconds_per_bar"], 1.5)
        self.assertEqual([bar["end_seconds"] for bar in _bars(chart)], [1.5, 3, 4])
        self.assertTrue(_bars(chart)[-1]["is_partial"])

    def test_every_event_duration_survives_many_grid_settings(self) -> None:
        """다양한 템포·박자·시작 위치로 나눈 모든 조각의 길이가 원래 이벤트와 같다."""
        events = [_event(index * 0.37, index * 0.37 + 0.29, "C" if index % 2 else "G") for index in range(321)]
        for tempo in (20, 99.7, 137.3, 300):
            for meter in (2, 3, 4, 6, 12):
                for first in (-3.17, 0.0, 2.19):
                    with self.subTest(tempo=tempo, meter=meter, first=first):
                        chart = build_chord_chart({"events": events}, bpm=tempo, beats_per_bar=meter, first_downbeat_seconds=first)
                        durations = [0.0] * len(events)
                        for bar in _bars(chart):
                            for segment in bar["segments"]:
                                if segment["event_index"] is not None:
                                    durations[segment["event_index"]] += segment["end_seconds"] - segment["start_seconds"]
                        for index, duration in enumerate(durations):
                            self.assertAlmostEqual(duration, events[index]["end_seconds"] - events[index]["start_seconds"], places=10)

    def test_initial_settings_use_existing_hint_and_safe_fallback(self) -> None:
        """기존 BPM 초깃값과 구간 길이를 읽되 잘못된 값은 안전한 기본값으로 바꾼다."""
        settings = initial_chart_settings({"features": {"bpm": 98.5}, "source": {"duration_seconds": 252.61}})
        self.assertEqual(settings, {"bpm": 98.5, "beats_per_bar": 4, "first_downbeat_seconds": 0.0,
                                   "page_size": 16, "duration_seconds": 252.61})
        for bpm in (None, math.nan, 0, 301, "unknown", True):
            with self.subTest(bpm=bpm):
                settings = initial_chart_settings({"features": {"bpm": bpm}, "source": {"duration_seconds": -2}})
                self.assertEqual(settings["bpm"], 120)
                self.assertIsNone(settings["duration_seconds"])
        self.assertEqual(initial_chart_settings({"features": None, "source": None})["bpm"], 120)


if __name__ == "__main__":
    unittest.main()
