"""Signal-level regressions for guide tones in a full mix with a strong bass."""
import unittest

import numpy as np

from song_chords import _harmonic_change_times, analyze_song_chords
from voicing import _classify_window


RATE = 22050


def sine(note, time):
    return np.sin(2 * np.pi * 440 * 2 ** ((note - 69) / 12) * time)


def bass_pedal_change():
    time = np.arange(3 * RATE) / RATE
    seventh = np.where(time < 1.5, sine(71, time), sine(70, time))
    signal = .55 * sine(36, time) + .035 * (sine(60, time) + sine(64, time) + sine(67, time) + seventh)
    return np.column_stack((signal, -signal)).astype(np.float32)


class DefiningToneTests(unittest.TestCase):
    def test_seventh_change_over_a_bass_pedal_has_a_local_boundary(self):
        boundaries = _harmonic_change_times(bass_pedal_change(), RATE)
        self.assertTrue(any(abs(t - 1.5) < .09 for t in boundaries), boundaries)

    def test_bass_does_not_mask_a_sustained_major_to_dominant_seventh_change(self):
        events = analyze_song_chords(bass_pedal_change(), RATE)['events']
        correct = sum(max(0, min(e['end_seconds'], end) - max(e['start_seconds'], start))
                      for start, end, chord in [(0, 1.5, 'Cmaj7'), (1.5, 3, 'C7')]
                      for e in events if e['symbol'] == chord)
        self.assertGreater(correct, 2.6, [(e['symbol'], e['start_seconds']) for e in events])

    def test_resolved_competing_guide_tones_keep_both_candidates(self):
        for tones, degree, expected in (
                ((0, 3, 4, 7), 'third', {'major', 'minor'}),
                ((0, 3, 6, 7, 10), 'fifth', {'min7b5', 'min7'}),
                ((0, 4, 7, 10, 11), 'seventh', {'maj7', '7'})):
            with self.subTest(degree=degree):
                chroma = np.zeros(12)
                chroma[list(tones)] = 1
                chroma[0] = 1.4
                pitches = np.zeros(60)
                pitches[0] = 1
                window = _classify_window(chroma / chroma.sum(), pitches, pitches, .1, np.arange(36, 96))
                self.assertEqual(window['symbol'], '?')
                self.assertEqual(window['evidence']['uncertainty_reason'], 'conflicting_' + degree)
                self.assertEqual({x['chord_type'] for x in window['alternatives']}, expected)

    def test_one_low_note_with_odd_partials_does_not_supply_a_seventh_chord(self):
        time = np.arange(2 * RATE) / RATE
        for root in (36, 43):
            frequency = 440 * 2 ** ((root - 69) / 12)
            signal = sum(np.sin(2 * np.pi * h * frequency * time) / h for h in range(1, 30, 2)) * .2
            events = analyze_song_chords(np.column_stack((signal, -signal)), RATE)['events']
            self.assertTrue(all(e['symbol'] == '?' and not e['alternatives'] for e in events))
