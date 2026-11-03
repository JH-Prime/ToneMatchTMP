"""CQT harmonic rejection paired with independently played power-chord controls."""
import unittest

import numpy as np

from song_chords import analyze_song_chords


RATE = 22050
DURATION = 2.4


def tone_audio(notes, weights=None, cents=0., harmonics=1, peak=.2, phase_seed=None):
    """Equal-tempered notes with distinct fundamentals, never exact 3:1 tuning."""
    axis = np.arange(round(RATE * DURATION)) / RATE
    weights = np.ones(len(notes)) if weights is None else weights
    mono = np.zeros_like(axis)
    random = np.random.default_rng(phase_seed)
    for note, strength in zip(notes, weights):
        frequency = 440 * 2 ** ((note - 69 + cents / 100) / 12)
        mono += strength * sum(np.sin(2 * np.pi * frequency * partial * axis
                                     + (random.uniform(-np.pi, np.pi) if phase_seed is not None else 0)) / partial ** 1.5
                               for partial in range(1, harmonics + 1))
    mono *= peak / np.max(np.abs(mono))
    return np.column_stack((mono, -mono)).astype(np.float32)


def resonant_audio(note, shape='formant', peak=.2):
    """One fundamental with a resonant third or every-third-partial envelope."""
    axis = np.arange(round(RATE * DURATION)) / RATE
    frequency = 440 * 2 ** ((note - 69) / 12)
    mono = np.zeros_like(axis)
    for partial in range(1, 25):
        if frequency * partial >= RATE / 2:
            break
        strength = ((1 + 8 * np.exp(-((partial - 3) / 1.1) ** 2)) / partial
                    if shape == 'formant' else (8 if partial % 3 == 0 else 1) / partial)
        mono += strength * np.sin(2 * np.pi * frequency * partial * axis)
    mono *= peak / np.max(np.abs(mono))
    return np.column_stack((mono, -mono)).astype(np.float32)


class CqtHarmonicTests(unittest.TestCase):
    def assert_unknown(self, audio):
        result = analyze_song_chords(audio, RATE, method='cqt')
        self.assertEqual(result['method_id'], 'cqt')
        self.assertTrue(result['events'])
        self.assertTrue(all(row['chord_type'] == 'unknown' and row['symbol'] == '?'
                            for row in result['events']), result['events'])
        self.assertTrue(all(not row.get('alternatives') for row in result['events']), result['events'])
        self.assertAlmostEqual(result['events'][-1]['end_seconds'], DURATION, places=3)

    def assert_power(self, audio, root):
        result = analyze_song_chords(audio, RATE, method='cqt')
        self.assertEqual(result['method_id'], 'cqt')
        self.assertTrue(result['events'])
        self.assertTrue(all((row['root_pc'], row['chord_type']) == (root, 'power5')
                            for row in result['events']), result['events'])
        # Preserving one tiny event is insufficient: the original steady chord
        # is correct over the complete input, including its opening and ending.
        correct_seconds = sum(row['end_seconds'] - row['start_seconds']
                              for row in result['events'])
        self.assertAlmostEqual(correct_seconds, DURATION, places=3)

    def test_resonant_singletons_are_not_power_chords(self):
        for note in (36, 48, 57):
            for shape in ('formant', 'comb3'):
                with self.subTest(note=note, shape=shape):
                    self.assert_unknown(resonant_audio(note, shape))

    def test_weak_unrelated_note_does_not_validate_a_harmonic_fifth(self):
        source = resonant_audio(36)
        axis = np.arange(len(source)) / RATE
        for weak_note in (50, 58, 61):
            weak = .006 * np.sin(2 * np.pi * 440 * 2 ** ((weak_note - 69) / 12) * axis)
            with self.subTest(weak_note=weak_note):
                self.assert_unknown(source + np.column_stack((weak, -weak)))

    def test_resonant_rejection_is_not_specific_to_C_A_or_one_gain(self):
        for note, peak, shape in ((39, .04, 'formant'), (53, .35, 'comb3')):
            with self.subTest(note=note, peak=peak, shape=shape):
                self.assert_unknown(resonant_audio(note, shape, peak))

    def test_equal_tempered_close_and_wide_fifths_remain_power_chords(self):
        # The wide fifth is near, but not exactly on, the bass's third partial.
        # Reusing a blanket FFT harmonic veto would erase this valid control.
        for notes in ((36, 55), (48, 55), (45, 52), (41, 48)):
            with self.subTest(notes=notes):
                self.assert_power(tone_audio(notes), notes[0] % 12)

    def test_root_fifth_octave_voicings_keep_their_power_chord(self):
        for notes in ((36, 43, 48), (45, 52, 57)):
            with self.subTest(notes=notes):
                self.assert_power(tone_audio(notes), notes[0] % 12)

    def test_quiet_independently_played_fifth_is_not_erased(self):
        self.assert_power(tone_audio((48, 55), weights=(1., .3)), 0)

    def test_detuned_power_chords_are_not_rejected_as_harmonics(self):
        for cents in (-23., 27.):
            with self.subTest(cents=cents):
                self.assert_power(tone_audio((48, 55), cents=cents), 0)

    def test_harmonic_rich_independently_played_fifths_survive(self):
        for notes in ((48, 55), (36, 55), (45, 52)):
            with self.subTest(notes=notes):
                self.assert_power(tone_audio(notes, harmonics=8), notes[0] % 12)

    def test_weak_root_or_fifth_with_independent_partial_phases_survives(self):
        for notes, weights, seed in (((36, 55), (.3, 1.), 41), ((48, 55), (1., .3), 19)):
            with self.subTest(notes=notes, weights=weights, seed=seed):
                self.assert_power(tone_audio(notes, weights=weights, harmonics=8, phase_seed=seed), notes[0] % 12)

    def test_high_rate_input_keeps_rejection_and_independent_fifth(self):
        from scipy.signal import resample_poly
        for source, expected in ((resonant_audio(48), '?'), (tone_audio((36, 55), harmonics=8), 'C5')):
            with self.subTest(expected=expected):
                result = analyze_song_chords(resample_poly(source, 2, 1, axis=0), RATE * 2, method='cqt')
                self.assertTrue(all(row['symbol'] == expected for row in result['events']), result['events'])

    def test_plain_and_ordinary_harmonic_single_notes_remain_unknown(self):
        for harmonics in (1, 8):
            with self.subTest(harmonics=harmonics):
                self.assert_unknown(tone_audio((48,), harmonics=harmonics))

    def test_noise_does_not_reintroduce_isolated_rejected_harmonic_alternatives(self):
        source = resonant_audio(36)
        noise = np.random.default_rng(107).normal(0, .002, source.shape).astype(np.float32)
        result = analyze_song_chords(source + noise, RATE, method='cqt')
        # No guarantee that noisy singletons are all rejected. When neighboring
        # vetoes make a lone C5 temporally unsupported, it must not return as a
        # display candidate despite that repeated negative evidence.
        unknown = [row for row in result['events'] if row['chord_type'] == 'unknown']
        self.assertTrue(unknown)
        self.assertTrue(all(not row['alternatives'] for row in unknown), unknown)

    def test_candidate_filter_needs_two_matching_rejections(self):
        from song_chords import _smooth_cqt_labels
        from voicing import _unknown_window
        candidate = {'root_pc': 0, 'chord_type': 'power5', 'symbol': 'C5',
                     'bass_pc': 0, 'inversion': 'root', 'pitch_classes': (0, 7),
                     'register': 'unknown', 'spacing': 'unknown', 'confidence': .8,
                     'alternatives': (), 'evidence': {'observed_pitch_classes': [0, 7]},
                     '_score': 1.0}
        for left, right, expected in ((0, 0, False), (0, None, True),
                                     (None, 0, True), (0, 2, True), (2, 2, True)):
            with self.subTest(left=left, right=right):
                neighbors = []
                for root in (left, right):
                    row = _unknown_window(candidate, 'insufficient_tonal_evidence')
                    row.update(alternatives=(), _harmonic_rejected_root=root)
                    neighbors.append(row)
                neighbors[0]['_start_seconds'] = 0.
                candidate['_start_seconds'] = .05
                neighbors[1]['_start_seconds'] = .1
                result = _smooth_cqt_labels([neighbors[0], candidate, neighbors[1]])
                self.assertEqual(result[1]['symbol'], '?')
                self.assertEqual(bool(result[1]['alternatives']), expected)
                self.assertEqual(result[1]['evidence']['observed_pitch_classes'], [0, 7])
                self.assertEqual(result[1]['evidence']['uncertainty_reason'], 'temporal_instability')

    def test_rejection_does_not_cross_missing_observations(self):
        from song_chords import _smooth_cqt_labels
        from unittest.mock import patch
        candidate = {'root_pc': 0, 'chord_type': 'power5', 'symbol': 'C5'}
        raw = [{'_start_seconds': 0., '_harmonic_rejected_root': 0},
               {'_start_seconds': .5},
               {'_start_seconds': 1., '_harmonic_rejected_root': 0}]
        uncertain = {'chord_type': 'unknown', 'alternatives': (candidate,),
                     'evidence': {'uncertainty_reason': 'temporal_instability'}}
        with patch('song_chords._smooth_labels', return_value=[{}, uncertain, {}]):
            self.assertEqual(_smooth_cqt_labels(raw)[1]['alternatives'], (candidate,))


if __name__ == '__main__':
    unittest.main()
