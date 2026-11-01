"""CQT precision controls: temporal evidence must not invent missing tones."""
import unittest

import numpy as np

from song_chords import _classify_cqt_region, analyze_song_chords


RATE = 22050


def picked_triad(notes=(48, 52, 55), interval=.15, duration=4.0):
    mono = np.zeros(round(duration * RATE))
    for index, onset in enumerate(np.arange(0, duration, interval)):
        start = round(onset * RATE)
        elapsed = np.arange(len(mono) - start) / RATE
        frequency = 440 * 2 ** ((notes[index % len(notes)] - 69) / 12)
        mono[start:] += .12 * np.sin(2 * np.pi * frequency * elapsed) * np.exp(-6 * elapsed)
    return np.column_stack((mono, mono)).astype(np.float32)


class CqtPrecisionTests(unittest.TestCase):
    def test_quiet_region_with_transform_bleed_stays_low_signal(self):
        midi = np.arange(24, 108)
        magnitude = np.zeros((3 * len(midi), 30))
        for note in (48, 52, 55):
            magnitude[(note - midi[0]) * 3, :] = 1
        duration = 30 * 512 / RATE
        # Neighboring audible regions can leave CQT energy across a quiet
        # boundary. Low-signal abstentions intentionally have no observed notes.
        for level in (0., 1e-7):
            audio = np.full((round(duration * RATE), 2), level)
            with self.subTest(level=level):
                result = _classify_cqt_region(audio, magnitude, midi, RATE, (0, duration))
                self.assertEqual(result['symbol'], '?')
                self.assertEqual(result['evidence']['uncertainty_reason'], 'low_signal')
                self.assertFalse(result['evidence'].get('observed_pitch_classes'))

    def test_minority_melody_does_not_extend_a_supported_chord(self):
        midi = np.arange(24, 108)
        magnitude = np.zeros((3 * len(midi), 30))
        for note in (48, 52, 55):
            magnitude[(note - midi[0]) * 3, :] = 1
        magnitude[(62 - midi[0]) * 3, 10:20] = 1
        duration = 30 * 512 / RATE
        audio = np.full((round(duration * RATE), 2), .1)
        result = _classify_cqt_region(audio, magnitude, midi, RATE, (0, duration))
        self.assertEqual(result['symbol'], 'C')
        self.assertEqual(set(result['evidence']['observed_pitch_classes']), {0, 4, 7})

    def test_minority_note_does_not_complete_a_sustained_dyad(self):
        midi = np.arange(24, 108)
        magnitude = np.zeros((3 * len(midi), 30))
        for note in (48, 52):
            magnitude[(note - midi[0]) * 3, :] = 1
        magnitude[(55 - midi[0]) * 3, 10:20] = 1
        duration = 30 * 512 / RATE
        audio = np.full((round(duration * RATE), 2), .1)
        result = _classify_cqt_region(audio, magnitude, midi, RATE, (0, duration))
        self.assertEqual(result['symbol'], '?')
        self.assertEqual(set(result['evidence']['observed_pitch_classes']), {0, 4})

    def test_isolated_transient_notes_do_not_form_a_chord(self):
        midi = np.arange(24, 108)
        magnitude = np.zeros((3 * len(midi), 30))
        for index, note in enumerate((48, 52, 55)):
            magnitude[(note - midi[0]) * 3, index * 10:index * 10 + 2] = 1
        duration = 30 * 512 / RATE
        audio = np.full((round(duration * RATE), 2), .1)
        result = _classify_cqt_region(audio, magnitude, midi, RATE, (0, duration))
        self.assertEqual(result['symbol'], '?')

    def test_cqt_filter_shoulders_do_not_create_neighboring_notes(self):
        midi = np.arange(24, 108)
        magnitude = np.zeros((3 * len(midi), 30))
        # A resolved peak's neighboring filter responses are not extra notes.
        for note in (48, 52, 55):
            peak = (note - midi[0]) * 3
            for distance, weight in ((0, 1), (1, .7), (2, .3), (3, .15)):
                magnitude[peak + distance, :] = weight
                magnitude[peak - distance, :] = weight
        duration = 30 * 512 / RATE
        audio = np.full((round(duration * RATE), 2), .1)
        result = _classify_cqt_region(audio, magnitude, midi, RATE, (0, duration))
        self.assertEqual(result['symbol'], 'C')
        self.assertEqual(set(result['evidence']['observed_pitch_classes']), {0, 4, 7})

    def test_sequential_note_evidence_survives_inside_one_region(self):
        midi = np.arange(24, 108)
        magnitude = np.zeros((3 * len(midi), 30))
        for index, note in enumerate((48, 52, 55)):
            magnitude[(note - midi[0]) * 3, index * 10:(index + 1) * 10] = 1
        duration = 30 * 512 / RATE
        audio = np.full((round(duration * RATE), 2), .1)
        result = _classify_cqt_region(audio, magnitude, midi, RATE, (0, duration))
        self.assertEqual(result['symbol'], 'C')
        self.assertEqual(set(result['evidence']['observed_pitch_classes']), {0, 4, 7})

    def test_decaying_pcm_arpeggio_keeps_its_triad_without_spurious_extensions(self):
        result = analyze_song_chords(picked_triad(), RATE)
        rows = result['events']
        correct = sum(max(0, row['end_seconds'] - max(.45, row['start_seconds']))
                      for row in rows if row['symbol'] in ('C', 'C/E', 'C/G'))
        self.assertGreater(correct, 2.5)
        self.assertTrue(all(row['symbol'] in ('?', 'C', 'C/E', 'C/G') for row in rows))


if __name__ == '__main__':
    unittest.main()
