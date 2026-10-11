"""Known audio and exact annotations: timing accuracy is not detected coverage."""
import unittest

import numpy as np

from song_chords import analyze_song_chords
from test_song_chords import chord_audio


RATE = 22050


def sequence(parts, cents=0):
    audio, annotations, position = [], [], 0.0
    for notes, symbol, duration in parts:
        samples = (chord_audio([note + cents / 100 for note in notes], duration)
                   if notes else np.zeros((round(duration * RATE), 2), np.float32))
        end = position + len(samples) / RATE
        audio.append(samples)
        annotations.append((position, end, symbol))
        position = end
    return np.concatenate(audio), annotations


def agreement(events, annotations):
    correct = sum(max(0.0, min(row['end_seconds'], end) - max(row['start_seconds'], start))
                  for row in events for start, end, symbol in annotations if row['symbol'] == symbol)
    return correct / annotations[-1][1]


class ChordTraceTests(unittest.TestCase):
    def test_fast_changes_at_song_start_and_end_are_not_lost(self):
        beat = 60 / 180
        audio, expected = sequence([([60, 64, 67], 'C', beat),
                                    ([62, 66, 69], 'D', 2), ([55, 59, 62], 'G', beat)])
        rows = analyze_song_chords(audio, RATE)['events']
        self.assertEqual([row['symbol'] for row in rows], ['C', 'D', 'G'])
        self.assertGreaterEqual(agreement(rows, expected), .94)

    def test_tiny_input_does_not_fail_in_boundary_transform(self):
        for rate, length in ((8000, 1), (22050, 100), (44100, 2000)):
            samples = np.full((length, 1), .01, np.float32)
            result = analyze_song_chords(samples, rate)
            self.assertTrue(result['events'])
            self.assertAlmostEqual(result['events'][-1]['end_seconds'], length / rate, delta=.001)

    def test_low_note_beating_is_not_a_harmonic_change(self):
        from song_chords import _harmonic_change_times
        audio = chord_audio([36, 40, 43], 3)
        changes = _harmonic_change_times(audio, RATE)
        self.assertFalse(any(.2 < time < 2.8 for time in changes))

    def test_low_register_transition_does_not_invent_an_altered_extension(self):
        audio, expected = sequence([([36, 40, 43], 'C', 3.17), ([33, 36, 40], 'Am', 2.53)])
        rows = analyze_song_chords(audio, RATE)['events']
        self.assertTrue(all(row['symbol'] in ('C', 'Am', '?') for row in rows))
        self.assertGreaterEqual(agreement(rows, expected), .95)

    def test_fast_quarter_note_changes_are_measured_in_beats(self):
        # At 180 BPM, a 170 ms error is over half a beat, not a small error.
        beat = 60 / 180
        audio, expected = sequence([([60, 64, 67], 'C', 1.77),
                                    ([62, 66, 69], 'D', beat),
                                    ([55, 59, 62], 'G', beat),
                                    ([57, 60, 64], 'Am', 1.8)])
        rows = analyze_song_chords(audio, RATE)['events']
        self.assertEqual([row['symbol'] for row in rows], ['C', 'D', 'G', 'Am'])
        for row, (_, end, _) in zip(rows[:-1], expected[:-1]):
            self.assertLessEqual(abs(row['end_seconds'] - end) / beat, .18)

    def test_clean_change_is_not_quantized_to_two_hundred_milliseconds(self):
        for onset in (1.73, 2.09):
            audio, _ = sequence([([48, 52, 55], 'C', onset), ([42, 49, 57], 'F♯m', 2.37)])
            rows = analyze_song_chords(audio, RATE)['events']
            self.assertEqual([row['symbol'] for row in rows], ['C', 'F♯m'])
            self.assertAlmostEqual(rows[0]['end_seconds'], onset, delta=.06)

    def test_brief_real_chord_and_modulation_are_not_smoothed_away(self):
        audio, expected = sequence([([48, 52, 55], 'C', 2.13),
                                    ([52, 56, 59], 'E', .8),
                                    ([45, 48, 52], 'Am', 2.2),
                                    ([42, 49, 57], 'F♯m', 2.1)])
        rows = analyze_song_chords(audio, RATE)['events']
        self.assertEqual([row['symbol'] for row in rows], ['C', 'E', 'Am', 'F♯m'])
        self.assertGreaterEqual(agreement(rows, expected), .92)
        for row, (_, end, _) in zip(rows[:-1], expected[:-1]):
            self.assertAlmostEqual(row['end_seconds'], end, delta=.16)

    def test_transition_timing_including_batch_seam_and_detuning(self):
        for onset, cents in ((1.73, 0), (6.13, 30), (6.37, -30)):
            with self.subTest(onset=onset, cents=cents):
                audio, expected = sequence([([48, 52, 55], 'C', onset),
                                            ([42, 49, 57], 'F♯m', 2.37)], cents)
                result = analyze_song_chords(audio, RATE)
                rows = result['events']
                self.assertEqual([row['symbol'] for row in rows], ['C', 'F♯m'])
                self.assertAlmostEqual(rows[0]['end_seconds'], onset, delta=.16)
                self.assertGreaterEqual(agreement(rows, expected), .96)

    def test_passing_melody_does_not_become_a_new_chord(self):
        audio = chord_audio([48, 52, 55], 5)
        melody = chord_audio([74], .3) * .45
        start = round(2.1 * RATE)
        audio[start:start + len(melody)] += melody
        rows = analyze_song_chords(audio, RATE)['events']
        self.assertEqual([row['symbol'] for row in rows], ['C'])

    def test_sustained_extension_and_slash_bass_survive_context(self):
        audio, expected = sequence([([48, 52, 55], 'C', 2),
                                    ([48, 52, 55, 62], 'Cadd9', 2),
                                    ([40, 48, 55], 'C/E', 2)])
        rows = analyze_song_chords(audio, RATE)['events']
        self.assertEqual([row['symbol'] for row in rows], ['C', 'Cadd9', 'C/E'])
        self.assertGreaterEqual(agreement(rows, expected), .93)
        self.assertTrue(all(not row['candidate_shapes'] for row in rows))

    def test_short_silent_gap_stays_unknown_and_timeline_is_contiguous(self):
        audio, expected = sequence([([48, 52, 55], 'C', 2.03),
                                    ([], '?', .8), ([45, 48, 52], 'Am', 2)])
        rows = analyze_song_chords(audio, RATE)['events']
        self.assertEqual([row['symbol'] for row in rows], ['C', '?', 'Am'])
        self.assertGreaterEqual(agreement(rows, expected), .94)
        self.assertEqual(rows[0]['start_seconds'], 0)
        self.assertAlmostEqual(rows[-1]['end_seconds'], len(audio) / RATE, places=3)
        for left, right in zip(rows, rows[1:]):
            self.assertEqual(left['end_seconds'], right['start_seconds'])
            self.assertGreater(left['end_seconds'], left['start_seconds'])
