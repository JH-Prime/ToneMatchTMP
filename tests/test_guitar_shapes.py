"""기타 운지 후보의 구성음 완전성·물리적 제한·캐시 독립성을 검증한다."""

from __future__ import annotations

import sys
import unittest
from itertools import product
from pathlib import Path


MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from guitar_shapes import MAX_FRET, MAX_FRET_SPAN, STANDARD_TUNING_MIDI, _finger_count, _search_shapes, _shape_rank, candidate_shapes  # noqa: E402
from voicing import CHORD_INTERVALS, candidate_guitar_shapes  # noqa: E402


class GuitarShapeTests(unittest.TestCase):
    """실제 검출과 구분되는 모든 구성음 포함 운지 후보를 검사한다."""

    def test_all_chord_roots_have_only_complete_playable_candidates(self) -> None:
        """41종·12근음에서 반환한 모든 후보가 제한과 정확한 구성음 집합을 지킨다."""
        covered = set()
        covered_pairs = 0
        for chord_type, intervals in CHORD_INTERVALS.items():
            for root in range(12):
                with self.subTest(chord_type=chord_type, root=root):
                    required = {(root + interval) % 12 for interval in intervals}
                    shapes = candidate_shapes(root, chord_type, intervals)
                    self.assertLessEqual(len(shapes), 2)
                    if len(required) > 6:
                        self.assertEqual(shapes, ())
                    if shapes:
                        covered.add(chord_type)
                        covered_pairs += 1
                    self.assertEqual(len({tuple(shape["frets_low_e_to_high_e"]) for shape in shapes}), len(shapes))
                    for shape in shapes:
                        frets = shape["frets_low_e_to_high_e"]
                        self.assertEqual(len(frets), 6)
                        numeric = tuple(-1 if fret == "x" else fret for fret in frets)
                        self.assertTrue(all(-1 <= fret <= MAX_FRET for fret in numeric))
                        actual = {(midi + fret) % 12 for midi, fret in
                                  zip(STANDARD_TUNING_MIDI, numeric) if fret >= 0}
                        self.assertEqual(actual, required)
                        positive = [fret for fret in numeric if fret > 0]
                        if positive:
                            self.assertLessEqual(max(positive) - min(positive), MAX_FRET_SPAN)
                            self.assertEqual(shape["base_fret"], min(positive))
                        self.assertLessEqual(_finger_count(numeric), 4)
                        self.assertFalse(shape["detected"])
                        self.assertTrue(shape["theoretical"])
                        self.assertEqual(shape["completeness"], "all_pitch_classes")
                        self.assertNotIn("finger_numbers", shape)
        self.assertEqual(covered, set(CHORD_INTERVALS) - {"13", "maj13", "min13"})
        self.assertEqual(covered_pairs, 38 * 12)

    def test_extended_chords_and_common_chords_have_candidates(self) -> None:
        """기존 여섯 계열 밖의 서스·식스·나인·변화 화음에서도 운지 후보를 찾는다."""
        for chord_type in ("major", "minor", "sus2", "sus4", "dim", "aug", "6", "min6", "min7b5",
                           "dim7", "add9", "minadd9", "9", "maj9", "min9", "7b5", "7sharp5"):
            for root in range(12):
                with self.subTest(chord_type=chord_type, root=root):
                    self.assertTrue(candidate_shapes(root, chord_type, CHORD_INTERVALS[chord_type]))

    def test_voicing_wrapper_preserves_complete_tones_for_all_templates(self) -> None:
        """실제 분석기 래퍼의 기존 E·A형과 신규 탐색 모두 41종·12근음의 구성음을 보존한다."""
        for chord_type, intervals in CHORD_INTERVALS.items():
            for root in range(12):
                with self.subTest(chord_type=chord_type, root=root):
                    required = {(root + interval) % 12 for interval in intervals}
                    shapes = candidate_guitar_shapes(root, chord_type)
                    self.assertEqual(bool(shapes), len(required) <= 6)
                    for shape in shapes:
                        frets = tuple(-1 if fret == "x" else fret for fret in shape["frets_low_e_to_high_e"])
                        actual = {(midi + fret) % 12 for midi, fret in
                                  zip(STANDARD_TUNING_MIDI, frets) if fret >= 0}
                        self.assertEqual(actual, required)
                        self.assertLessEqual(_finger_count(frets), 4)
                        self.assertFalse(shape["detected"])

    def test_seven_tone_thirteenths_never_silently_omit_notes(self) -> None:
        """일곱 구성음을 여섯 현에 억지로 넣거나 생략한 완전 운지로 표시하지 않는다."""
        for chord_type in ("13", "maj13", "min13"):
            for root in range(12):
                self.assertEqual(candidate_shapes(root, chord_type, CHORD_INTERVALS[chord_type]), ())

    def test_bars_do_not_cover_open_or_muted_or_lower_fretted_strings(self) -> None:
        """바레 근사는 개방·뮤트·더 낮은 프렛을 넘겨 손가락 수를 부당하게 줄이지 않는다."""
        self.assertEqual(_finger_count((1, 3, 3, 2, 1, 1)), 3)
        self.assertEqual(_finger_count((1, 0, 1, 0, 1, 0)), 3)
        self.assertEqual(_finger_count((1, -1, 1, -1, 1, -1)), 3)
        self.assertEqual(_finger_count((2, 1, 2, 1, 2, 1)), 4)
        self.assertEqual(_finger_count((1, 2, 3, 4, 5, 6)), 6)

    def test_results_are_deterministic_and_cache_cannot_be_mutated(self) -> None:
        """반환 사전·리스트를 수정해도 캐시된 다음 결과는 변하지 않는다."""
        expected = candidate_shapes(0, "add9", CHORD_INTERVALS["add9"])
        result = candidate_shapes(0, "add9", CHORD_INTERVALS["add9"])
        result[0]["frets_low_e_to_high_e"][0] = 999
        result[0]["pitch_classes"].clear()
        result[0]["detected"] = True
        self.assertEqual(candidate_shapes(0, "add9", CHORD_INTERVALS["add9"]), expected)

    def test_repeated_requests_use_bounded_cache(self) -> None:
        """반복된 화음 분석은 512개 이하 불변 결과 캐시를 재사용한다."""
        candidate_shapes(0, "major", CHORD_INTERVALS["major"])
        before = _search_shapes.cache_info()
        for _ in range(100):
            candidate_shapes(0, "major", CHORD_INTERVALS["major"])
        after = _search_shapes.cache_info()
        self.assertEqual(after.hits - before.hits, 100)
        self.assertLessEqual(after.currsize, 512)

    def test_pruned_search_matches_independent_unpruned_enumeration(self) -> None:
        """감7의 모든 0~15프렛 조합을 별도로 열거해 DFS 가지치기가 최선 후보를 놓치지 않는다."""
        required = {0, 3, 6, 9}
        options = [tuple([-1] + [fret for fret in range(MAX_FRET + 1)
                                if (midi + fret) % 12 in required]) for midi in STANDARD_TUNING_MIDI]
        valid = []
        for frets in product(*options):
            actual = {(midi + fret) % 12 for midi, fret in zip(STANDARD_TUNING_MIDI, frets) if fret >= 0}
            if actual != required:
                continue
            positive = [fret for fret in frets if fret > 0]
            if positive and max(positive) - min(positive) > MAX_FRET_SPAN:
                continue
            if _finger_count(frets) <= 4:
                valid.append(frets)
        expected = tuple(sorted(valid, key=lambda frets: _shape_rank(frets, 0))[:2])
        self.assertEqual(_search_shapes(0, tuple(sorted(required))), expected)

    def test_unknown_empty_and_invalid_inputs_are_not_fabricated(self) -> None:
        """미상·빈 구성음에는 후보가 없고 유효하지 않은 근음·간격은 명시적으로 거절한다."""
        self.assertEqual(candidate_shapes(None, "major", (0, 4, 7)), ())
        self.assertEqual(candidate_shapes(0, "unknown", (0, 4, 7)), ())
        self.assertEqual(candidate_shapes(0, "major", ()), ())
        self.assertEqual(candidate_shapes(0, "major", (4, 7)), ())
        for root in (-1, 12, 1.0, True, "C"):
            with self.subTest(root=root), self.assertRaises(ValueError):
                candidate_shapes(root, "major", (0, 4, 7))
        for intervals in ((0, 4.5, 7), (0, True, 7), (0, "4", 7)):
            with self.subTest(intervals=intervals), self.assertRaises(ValueError):
                candidate_shapes(0, "major", intervals)


if __name__ == "__main__":
    unittest.main()
