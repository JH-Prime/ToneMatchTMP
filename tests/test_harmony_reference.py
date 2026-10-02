"""코드·음계·다이어토닉 참고표의 도수, 이명동음 철자와 엔진 동기화를 검증한다."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from harmony_reference import (  # noqa: E402
    CHORD_DEGREES, CHORD_NAMES, ROOT_NAMES, SCALE_DEGREES, SCALE_NAMES,
    chord_options, diatonic_options, get_chord_reference, get_diatonic_reference,
    get_scale_reference, scale_options,
)
from voicing import CHORD_INTERVALS, CHORD_SUFFIX  # noqa: E402


EXPECTED_SCALES = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "natural_minor": [0, 2, 3, 5, 7, 8, 10],
    "major_pentatonic": [0, 2, 4, 7, 9],
    "minor_pentatonic": [0, 3, 5, 7, 10],
    "harmonic_minor": [0, 2, 3, 5, 7, 8, 11],
    "melodic_minor": [0, 2, 3, 5, 7, 9, 11],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "lydian": [0, 2, 4, 6, 7, 9, 11],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "locrian": [0, 1, 3, 5, 6, 8, 10],
    "minor_blues": [0, 3, 5, 6, 7, 10],
}


def _note_pitch_class(note: str) -> int:
    """테스트에서 음이름을 독립적으로 해석해 건반 음고 번호로 바꾼다."""
    naturals = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
    return (naturals[note[0]] + note.count("♯") - note.count("♭")) % 12


class HarmonyReferenceTests(unittest.TestCase):
    """참고 자료의 모든 근음·코드와 스케일이 일관되고 사실에 맞는지 확인한다."""

    def test_catalog_covers_every_engine_chord_and_twelve_roots(self) -> None:
        """41개 코드의 이름·도수 정의와 12개 근음이 엔진 목록에서 빠지지 않아야 한다."""
        self.assertEqual(len(CHORD_INTERVALS), 41)
        self.assertEqual(set(CHORD_INTERVALS), set(CHORD_DEGREES))
        self.assertEqual(set(CHORD_INTERVALS), set(CHORD_NAMES))
        self.assertEqual(set(CHORD_INTERVALS), set(CHORD_SUFFIX) - {"unknown"})
        self.assertEqual(len(ROOT_NAMES), 12)
        self.assertEqual([_note_pitch_class(note) for note in ROOT_NAMES], list(range(12)))
        self.assertEqual([option["key"] for option in chord_options()], list(CHORD_INTERVALS))

    def test_all_492_chord_definitions_match_engine_and_keyboard(self) -> None:
        """모든 근음의 코드 도수가 엔진 구성음과 음이름 및 상위 옥타브에 일치해야 한다."""
        count = 0
        for root in range(12):
            for key, pitch_offsets in CHORD_INTERVALS.items():
                with self.subTest(root=root, key=key):
                    result = get_chord_reference(root, key)
                    self.assertEqual(result["kind"], "chord")
                    self.assertEqual([step % 12 for step in result["intervals"]], list(pitch_offsets))
                    self.assertEqual(result["pitch_classes"], [(root + step) % 12 for step in pitch_offsets])
                    self.assertEqual([_note_pitch_class(note) for note in result["note_names"]], result["pitch_classes"])
                    self.assertEqual(result["symbol"], ROOT_NAMES[root] + CHORD_SUFFIX[key])
                    self.assertEqual(result["intervals"], sorted(result["intervals"]))
                    self.assertEqual(len(result["degree_labels"]), len(result["note_names"]))
                    self.assertEqual(json.loads(json.dumps(result)), result)
                    count += 1
        self.assertEqual(count, 492)

    def test_extended_degrees_stay_in_the_upper_octave(self) -> None:
        """9·11·13 코드의 참고 건반이 2·4·6도의 낮은 옥타브로 접히지 않아야 한다."""
        cases = {
            "9": [0, 4, 7, 10, 14], "11": [0, 4, 7, 10, 14, 17],
            "13": [0, 4, 7, 10, 14, 17, 21], "maj13": [0, 4, 7, 11, 14, 17, 21],
            "min13": [0, 3, 7, 10, 14, 17, 21], "6add9": [0, 4, 7, 9, 14],
            "add11": [0, 4, 7, 17], "7b9": [0, 4, 7, 10, 13],
            "7sharp9": [0, 4, 7, 10, 15], "7sharp11": [0, 4, 7, 10, 18],
            "7b13": [0, 4, 7, 10, 20],
        }
        for key, intervals in cases.items():
            with self.subTest(key=key):
                self.assertEqual(get_chord_reference(0, key)["intervals"], intervals)

    def test_chord_spelling_preserves_altered_degree_identity(self) -> None:
        """감7·증5·증9·감13처럼 같은 건반이라도 다른 도수인 음은 알맞게 표기한다."""
        cases = {
            "dim7": ["C", "E♭", "G♭", "B♭♭"],
            "7sharp5": ["C", "E", "G♯", "B♭"],
            "7sharp9": ["C", "E", "G", "B♭", "D♯"],
            "7b13": ["C", "E", "G", "B♭", "A♭"],
            "7sharp11": ["C", "E", "G", "B♭", "F♯"],
        }
        for key, names in cases.items():
            with self.subTest(key=key):
                self.assertEqual(get_chord_reference(0, key)["note_names"], names)
        self.assertEqual(get_chord_reference(1, "aug")["note_names"], ["C♯", "E♯", "G♯♯"])

    def test_twelve_scales_are_separate_from_chord_catalog(self) -> None:
        """펜타토닉과 모드가 코드 유형에 잘못 등록되지 않고 음계 참고에만 있어야 한다."""
        self.assertEqual(set(SCALE_DEGREES), set(EXPECTED_SCALES))
        self.assertEqual(set(SCALE_NAMES), set(EXPECTED_SCALES))
        self.assertEqual([item["key"] for item in scale_options()], list(EXPECTED_SCALES))
        self.assertNotIn("major_pentatonic", CHORD_INTERVALS)
        self.assertNotIn("minor_pentatonic", CHORD_INTERVALS)
        self.assertNotIn("diatonic", CHORD_INTERVALS)
        self.assertEqual([item["key"] for item in diatonic_options()], ["major", "natural_minor"])

    def test_all_144_scales_have_exact_intervals_and_spelling(self) -> None:
        """12개 근음의 12개 음계가 정의된 반음 간격을 유지하고 중복 근음을 넣지 않아야 한다."""
        count = 0
        for root in range(12):
            for key, offsets in EXPECTED_SCALES.items():
                with self.subTest(root=root, key=key):
                    result = get_scale_reference(root, key)
                    self.assertEqual(result["kind"], "scale")
                    self.assertEqual(result["intervals"], offsets)
                    self.assertEqual(result["pitch_classes"], [(root + step) % 12 for step in offsets])
                    self.assertEqual([_note_pitch_class(note) for note in result["note_names"]], result["pitch_classes"])
                    self.assertEqual(len(set(result["pitch_classes"])), len(offsets))
                    self.assertEqual(json.loads(json.dumps(result)), result)
                    count += 1
        self.assertEqual(count, 144)

    def test_sharp_major_and_flat_minor_keep_each_scale_letter(self) -> None:
        """C♯ 장음계의 E♯·B♯와 E♭ 자연단음계의 C♭을 이론에 맞게 보존한다."""
        self.assertEqual(get_scale_reference(1, "major")["note_names"], ["C♯", "D♯", "E♯", "F♯", "G♯", "A♯", "B♯"])
        self.assertEqual(get_scale_reference(3, "natural_minor")["note_names"], ["E♭", "F", "G♭", "A♭", "B♭", "C♭", "D♭"])
        self.assertEqual(get_scale_reference(0, "minor_pentatonic")["note_names"], ["C", "E♭", "F", "G", "B♭"])
        self.assertEqual(get_scale_reference(0, "minor_blues")["note_names"], ["C", "E♭", "F", "G♭", "G", "B♭"])

    def test_c_major_diatonic_chords_and_roman_numerals(self) -> None:
        """C 장음계의 7개 3화음과 7화음 및 로마숫자가 정확해야 한다."""
        result = get_diatonic_reference(0, "major")
        rows = result["rows"]
        self.assertEqual([row["degree"] for row in rows], list(range(1, 8)))
        self.assertEqual([row["degree_label"] for row in rows], ["I", "ii", "iii", "IV", "V", "vi", "vii°"])
        self.assertEqual([row["triad"]["symbol"] for row in rows], ["C", "Dm", "Em", "F", "G", "Am", "Bdim"])
        self.assertEqual([row["seventh"]["symbol"] for row in rows], ["Cmaj7", "Dm7", "Em7", "Fmaj7", "G7", "Am7", "Bm7♭5"])
        self.assertEqual([row["seventh_degree_label"] for row in rows], ["Imaj7", "ii7", "iii7", "IVmaj7", "V7", "vi7", "viiø7"])

    def test_a_natural_minor_diatonic_does_not_raise_leading_note(self) -> None:
        """A 자연단음계의 v는 Em이며 화성단음계의 E 장3화음으로 바뀌지 않아야 한다."""
        result = get_diatonic_reference(9, "natural_minor")
        rows = result["rows"]
        self.assertEqual([row["degree_label"] for row in rows], ["i", "ii°", "III", "iv", "v", "VI", "VII"])
        self.assertEqual([row["triad"]["symbol"] for row in rows], ["Am", "Bdim", "C", "Dm", "Em", "F", "G"])
        self.assertEqual([row["seventh"]["symbol"] for row in rows], ["Am7", "Bm7♭5", "Cmaj7", "Dm7", "Em7", "Fmaj7", "G7"])
        self.assertEqual([row["seventh_degree_label"] for row in rows], ["i7", "iiø7", "IIImaj7", "iv7", "v7", "VImaj7", "VII7"])

    def test_diatonic_chords_use_only_scale_notes_in_all_keys(self) -> None:
        """모든 조의 다이어토닉 3·7화음이 해당 음계의 격음쌓기 및 철자와 같아야 한다."""
        checked_chords = 0
        for root in range(12):
            for key in ("major", "natural_minor"):
                result = get_diatonic_reference(root, key)
                self.assertEqual(result["kind"], "diatonic")
                self.assertEqual(len(result["rows"]), 7)
                self.assertEqual(json.loads(json.dumps(result)), result)
                for index, row in enumerate(result["rows"]):
                    for chord_kind, voice_count in (("triad", 3), ("seventh", 4)):
                        with self.subTest(root=root, key=key, degree=index + 1, kind=chord_kind):
                            chord = row[chord_kind]
                            indexes = [(index + 2 * voice) % 7 for voice in range(voice_count)]
                            self.assertEqual(chord["pitch_classes"], [result["pitch_classes"][i] for i in indexes])
                            self.assertEqual(chord["note_names"], [result["note_names"][i] for i in indexes])
                            self.assertEqual(chord["root_name"], result["note_names"][index])
                            self.assertEqual(chord["pitch_classes"], [(chord["root_pc"] + interval) % 12 for interval in chord["intervals"]])
                            checked_chords += 1
        self.assertEqual(checked_chords, 336)

    def test_diatonic_preserves_theoretical_root_spelling(self) -> None:
        """다이어토닉 근음도 B♯·C♭처럼 음계 문맥의 철자를 유지해야 한다."""
        sharp_rows = get_diatonic_reference(1, "major")["rows"]
        flat_rows = get_diatonic_reference(3, "natural_minor")["rows"]
        self.assertEqual(sharp_rows[6]["triad"]["symbol"], "B♯dim")
        self.assertEqual(sharp_rows[6]["seventh"]["note_names"], ["B♯", "D♯", "F♯", "A♯"])
        self.assertEqual(flat_rows[5]["triad"]["symbol"], "C♭")
        self.assertEqual(flat_rows[5]["seventh"]["note_names"], ["C♭", "E♭", "G♭", "B♭"])

    def test_options_and_results_are_independent_mutable_copies(self) -> None:
        """UI에서 반환값을 편집해도 이후 참고표나 공통 정의가 바뀌지 않아야 한다."""
        chord = get_chord_reference(0, "major")
        chord["note_names"][0] = "bad"
        chord["intervals"].append(999)
        chord["limitations"].clear()
        scale = get_scale_reference(0, "major")
        scale["pitch_classes"].clear()
        diatonic = get_diatonic_reference(0)
        diatonic["rows"][0]["triad"]["note_names"].clear()
        options = chord_options()
        options[0]["name"] = "bad"
        self.assertEqual(get_chord_reference(0, "major")["note_names"], ["C", "E", "G"])
        self.assertEqual(get_chord_reference(0, "major")["intervals"], [0, 4, 7])
        self.assertTrue(get_chord_reference(0, "major")["limitations"])
        self.assertEqual(get_scale_reference(0, "major")["pitch_classes"], EXPECTED_SCALES["major"])
        self.assertEqual(get_diatonic_reference(0)["rows"][0]["triad"]["note_names"], ["C", "E", "G"])
        self.assertNotEqual(chord_options()[0]["name"], "bad")

    def test_reference_explanations_are_localized_and_not_detection_claims(self) -> None:
        """한국어·영어 설명이 참고표와 검출 결과를 구분하고 상행 단음계를 명시해야 한다."""
        for language in ("ko", "en"):
            for options in (chord_options(language), scale_options(language), diatonic_options(language)):
                self.assertTrue(all(item["key"] and item["name"] for item in options))
            definitions = [get_chord_reference(0, "major", language), get_scale_reference(0, "major", language), get_diatonic_reference(0, "major", language)]
            for result in definitions:
                self.assertTrue(result["explanation"])
                self.assertIn("검출 결과가 아닙니다" if language == "ko" else "not a detected", result["limitations"][0])
            self.assertIn("상행형" if language == "ko" else "ascending", get_scale_reference(0, "melodic_minor", language)["explanation"])
        self.assertNotEqual(chord_options("ko"), chord_options("en"))
        self.assertEqual(chord_options("en-US"), chord_options("en"))

    def test_invalid_roots_and_unknown_types_are_rejected(self) -> None:
        """잘못된 근음·유형은 다른 음으로 조용히 대체하지 않고 오류로 처리해야 한다."""
        for root in (-1, 12, 128, 0.0, "0", None, True):
            for function in (get_chord_reference, get_scale_reference, get_diatonic_reference):
                with self.subTest(root=root, function=function.__name__):
                    with self.assertRaises(ValueError):
                        function(root, "major")
        for function in (get_chord_reference, get_scale_reference, get_diatonic_reference):
            with self.assertRaises(KeyError):
                function(0, "not_a_definition")
        with self.assertRaises(KeyError):
            get_diatonic_reference(0, "harmonic_minor")


if __name__ == "__main__":
    unittest.main()
