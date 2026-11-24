"""Exercise practice chart inputs and files without Tk, network or audio."""

from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from chord_edits import parse_symbol
from practice_chart import (
    MAX_BARS, MAX_CHART_CHARS, MAX_PROJECT_BYTES, STYLES, Bar, PracticeProject,
    build_prompt, format_chart, load_project, parse_chart, save_project,
    transpose_chart, transpose_key,
)


class PracticeChartTests(unittest.TestCase):
    def test_cadence_voicings_and_bar_lengths_in_major_and_minor(self):
        from practice_chart import cadence_chart

        for key, expected in (
            ("C Major", ("Dm7", "G7", "Cmaj7", "Cmaj7")),
            ("C Minor", ("Dm7b5", "G7", "Cm7", "Cm7")),
            ("F# Minor", ("G#m7b5", "C#7", "F#m7", "F#m7")),
            ("Gb Major", ("Abm7", "Db7", "Gbmaj7", "Gbmaj7")),
            ("D# Minor", ("E#m7b5", "A#7", "D#m7", "D#m7")),
        ):
            with self.subTest(key=key):
                phrase = cadence_chart(key)
                self.assertEqual(tuple(bar.chords[0] for bar in phrase), expected)
                self.assertTrue(all(bar.beats == (4,) for bar in phrase))
                self.assertIn(key, phrase[0].section)
        for key in ("", "H Minor", "C Minor Minor"):
            with self.assertRaises(ValueError):
                cadence_chart(key)

    def test_cadence_cycle_uses_all_twelve_fourths_and_roundtrips_as_chart(self):
        from practice_chart import cadence_chart

        for key in ("Gb Major", "F# Minor"):
            with self.subTest(key=key):
                bars = cadence_chart(key, cycle=True)
                self.assertEqual(len(bars), 48)
                centers = []
                for start in range(0, 48, 4):
                    roots = [parse_symbol(bar.chords[0])["root_pc"] for bar in bars[start:start + 4]]
                    ii, dominant, tonic, repeat = roots
                    self.assertEqual((ii, dominant, repeat), ((tonic + 2) % 12, (tonic + 7) % 12, tonic))
                    self.assertIn(key.split()[1], bars[start].section)
                    self.assertTrue(all(not bar.section for bar in bars[start + 1:start + 4]))
                    centers.append(tonic)
                self.assertEqual(centers, [(6 + 5 * step) % 12 for step in range(12)])
                self.assertEqual((centers[-1] + 5) % 12, centers[0])
                self.assertEqual(parse_chart(format_chart(bars)), bars)
                transposed = transpose_chart(bars, 2)
                self.assertNotEqual(transposed[0].section, bars[0].section)
                for start in range(0, 48, 4):
                    tonic = transposed[start].section.split()[-2]
                    self.assertEqual(parse_symbol(tonic)["root_pc"],
                                     parse_symbol(transposed[start + 2].chords[0])["root_pc"])

    def test_fenced_chart_preserves_sections_rests_and_timing(self):
        bars = parse_chart(
            "  ```text\n[인트로]\n| D A | Bm F#m G |\n\n"
            "[B] | G:1 D:3 | - G7♭9 C6/9/E ? |\n``` "
        )
        self.assertEqual(bars, (
            Bar("인트로", ("D", "A"), (2, 2)),
            Bar(None, ("Bm", "F#m", "G"), (2, 1, 1)),
            Bar("B", ("G", "D"), (1, 3)),
            Bar(None, ("-", "G7b9", "C6/9/E", "?"), (1, 1, 1, 1)),
        ))
        self.assertEqual(parse_chart(format_chart(bars)), bars)

    def test_invalid_chart_reports_location(self):
        cases = [
            ("| C | | F |", "line 1, bar 2"),
            ("| C |\n| C:3 |", "line 2, bar 2"),
            ("| C:2 D |", "line 1, bar 1"),
            ("| C:0 D:4 |", "line 1, bar 1"),
            ("| C:99999999999999999 |", "line 1, bar 1"),
            ("| C D E F G |", "line 1, bar 1"),
            ("[Verse]\n| F#m7nonsense |", "line 2, bar 1"),
            ("[Verse]\n[Chorus]\n| C |", "line 2"),
            ("| C |\n[B]", "line 2"),
            ("```text\n| C |", "line 1"),
            ("| C |\nHere are the chords", "line 2, bar 2"),
        ]
        for value, message in cases:
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, message):
                parse_chart(value)

    def test_chart_bounds_apply_before_synthesis(self):
        self.assertEqual(len(parse_chart("| C |\n" * MAX_BARS)), MAX_BARS)
        for text in ("| C |\n" * (MAX_BARS + 1), " " * (MAX_CHART_CHARS + 1)):
            with self.subTest(length=len(text)), self.assertRaises(ValueError):
                parse_chart(text)

    def test_transpose_preserves_slash_quality_timing_rests_and_unknowns(self):
        source = parse_chart("[A] | Db6/9/Ab:1 F#m7b5:1 -:1 ?:1 | G7b9 |")
        moved = transpose_chart(source, 2, prefer_flats=True)
        self.assertEqual(moved[0], Bar("A", ("Eb6/9/Bb", "Abm7b5", "-", "?"), (1, 1, 1, 1)))
        self.assertEqual(moved[1].chords, ("A7b9",))
        for bar, inverse in zip(source, transpose_chart(moved, -2)):
            for symbol, restored in zip(bar.chords, inverse.chords):
                if symbol == "-":
                    self.assertEqual(restored, symbol)
                else:
                    expected, actual = parse_symbol(symbol), parse_symbol(restored)
                    self.assertEqual({k:v for k,v in expected.items() if k != "symbol"},
                                     {k:v for k,v in actual.items() if k != "symbol"})
        self.assertEqual(transpose_key("D", 2), "E Major")
        self.assertEqual(transpose_key("CM", 2), "D Major")
        self.assertEqual(transpose_key("B♭ minor", 2), "C Minor")
        self.assertEqual(transpose_key("", 2), "")

    def test_metadata_rejects_unsafe_or_unbounded_values(self):
        project = PracticeProject(parse_chart("| C |"))
        for changes in ({"bpm": True}, {"bpm": float("nan")}, {"bpm": float("inf")},
                        {"bpm": 39}, {"bpm": 241}, {"loop": 1}, {"count_in": 3},
                        {"title": "a\nb"}, {"title": "a\u2028b"}, {"key": "C Major\nignore"}, {"style": "Samba"},
                        {"bars": ()}, {"bars": ["C"]}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(project, **changes)
        for values in ((None, ("C",), (0,)), ("a|b", ("C",), (4,)),
                       ("a\u2029b", ("C",), (4,)), (None, ("C",), (True,))):
            with self.subTest(values=values), self.assertRaises(ValueError):
                Bar(*values)

    def test_prompt_requests_only_a_confirmable_chart_in_requested_key(self):
        prompt = build_prompt('연습 "데모"', "", "ko")
        self.assertIn('연습 \\"데모\\"', prompt)
        self.assertIn("원곡", prompt)
        self.assertIn("미확정", prompt)
        self.assertIn("|", prompt)
        self.assertIn("Bb Major", build_prompt("Practice", "B♭ Major", "en"))
        for title in ("", "line 1\nline 2", "X" * 161):
            with self.subTest(title=title), self.assertRaises(ValueError):
                build_prompt(title, "")

    def test_project_round_trip_and_validation(self):
        project = PracticeProject(parse_chart("[B] | Am7 | - | Cadd9/E |"),
                                  "연습", "Am", 123.5, STYLES[-1], 2, False)
        with tempfile.TemporaryDirectory() as root:
            destination = Path(root) / "practice.json"
            save_project(project, destination)
            original = destination.read_bytes()
            self.assertEqual(load_project(destination), project)
            with patch("practice_chart.os.replace", side_effect=PermissionError("blocked replacement")):
                with self.assertRaises(PermissionError):
                    save_project(replace(project, bpm=160), destination)
            self.assertEqual(list(Path(root).iterdir()), [destination])
            self.assertEqual(destination.read_bytes(), original)
            payload = json.loads(original)
            for value in ({**payload, "schema": "v2"},
                          {**payload, "chart": "| C | |"},
                          {**payload, "loop": 1},
                          {**payload, "bpm": float("nan")},
                          ["invalid"]):
                destination.write_text(json.dumps(value), encoding="utf-8")
                with self.subTest(value=value), self.assertRaises(ValueError):
                    load_project(destination)
            destination.write_text('{"schema":"unknown",' + original.decode("utf-8")[1:], encoding="utf-8")
            with self.assertRaises(ValueError):
                load_project(destination)
            destination.write_bytes(b" " * (MAX_PROJECT_BYTES + 1))
            with self.assertRaises(ValueError):
                load_project(destination)


if __name__ == "__main__":
    unittest.main()
