"""Precision regressions: retain actual notes without inventing absent harmony."""
import unittest

import numpy as np

import voicing


SAMPLE_RATE = 22_050


def sine_notes(notes, duration=2.4, strengths=None):
    time = np.arange(round(SAMPLE_RATE * duration)) / SAMPLE_RATE
    strengths = strengths if strengths is not None else np.ones(len(notes))
    signal = sum(strength * np.sin(2 * np.pi * 440 * 2 ** ((note - 69) / 12) * time)
                 for note, strength in zip(notes, strengths)) * .1
    return np.column_stack((signal, -signal)).astype(np.float32)


class ChordPrecisionTests(unittest.TestCase):
    def test_low_bass_harmonic_overlap_preserves_conservative_unknown(self):
        # G3 lies close to C2's third harmonic. Until that ambiguity is resolved,
        # preserve v0.1.05's abstention instead of inventing independent evidence.
        for root in (0, 2, 5, 7, 9):
            with self.subTest(root=root):
                result = voicing.analyze_voicings(sine_notes((36 + root, 52 + root, 55 + root)), SAMPLE_RATE)
                self.assertTrue(result.events)
                self.assertEqual(result.tonal_coverage, 0)
                self.assertTrue(all((event.root_pc, event.chord_type) == (None, 'unknown')
                                    for event in result.events), result.events)

    def test_weak_unrelated_note_does_not_turn_formant_harmonics_into_chords(self):
        time = np.arange(round(SAMPLE_RATE * 2.4)) / SAMPLE_RATE
        fundamental = 440 * 2 ** ((36 - 69) / 12)
        signal = sum((1 + 8 * np.exp(-((harmonic - 3) / 1.1) ** 2)) / harmonic
                     * np.sin(2 * np.pi * fundamental * harmonic * time)
                     for harmonic in range(1, 25))
        signal *= .2 / np.max(np.abs(signal))
        source = np.column_stack((signal, -signal)).astype(np.float32)
        # Bb3, C#4 and D3 do not make the resonant third harmonic an independent G.
        for weak_note in (58, 61, 50):
            weak = .006 * np.sin(2 * np.pi * 440 * 2 ** ((weak_note - 69) / 12) * time)
            with self.subTest(weak_note=weak_note):
                result = voicing.analyze_voicings(source + np.column_stack((weak, -weak)), SAMPLE_RATE)
                self.assertTrue(result.events)
                self.assertEqual(result.tonal_coverage, 0, result.events)
                self.assertTrue(all((event.root_pc, event.chord_type) == (None, 'unknown')
                                    for event in result.events), result.events)

    def test_harmonic_single_note_stays_unknown(self):
        time = np.arange(SAMPLE_RATE * 2) / SAMPLE_RATE
        for note in (28, 36, 40, 48, 57):
            fundamental = 440 * 2 ** ((note - 69) / 12)
            signal = sum(np.sin(2 * np.pi * fundamental * harmonic * time) / harmonic
                         for harmonic in range(1, 25) if fundamental * harmonic < SAMPLE_RATE / 2)
            source = np.column_stack((signal, -signal)).astype(np.float32) * .1
            with self.subTest(note=note):
                result = voicing.analyze_voicings(source, SAMPLE_RATE)
                self.assertEqual(result.tonal_coverage, 0)

    def test_supported_seventh_can_omit_only_the_perfect_fifth(self):
        for kind in ('7', 'maj7', 'min7', '9', 'maj9', 'min9'):
            for root in range(12):
                pcs = [(root + interval) % 12 for interval in voicing.CHORD_INTERVALS[kind] if interval != 7]
                chroma = np.zeros(12)
                chroma[pcs] = 1 / len(pcs)
                with self.subTest(root=root, kind=kind):
                    self.assertGreater(voicing._score_chord(chroma, root, kind), 0)
                    scores = {(candidate_root, candidate_kind): score for score, candidate_root, candidate_kind
                              in voicing._template_scores(chroma)}
                    self.assertEqual(scores[root, kind], voicing._score_chord(chroma, root, kind))

    def test_bright_odd_harmonic_single_notes_do_not_become_chords(self):
        # Clarinet-like odd partials need not follow a steep 1/h roll-off.
        # Missing even partials are not evidence for independent chord tones.
        time = np.arange(SAMPLE_RATE * 2) / SAMPLE_RATE
        for note in (36, 48, 57):
            for decay in (0., .3, .6):
                fundamental = 440 * 2 ** ((note - 69) / 12)
                signal = sum(np.sin(2 * np.pi * fundamental * harmonic * time) / harmonic ** decay
                             for harmonic in range(1, 25, 2) if fundamental * harmonic < SAMPLE_RATE / 2)
                signal *= .2 / np.max(np.abs(signal))
                with self.subTest(note=note, decay=decay):
                    result = voicing.analyze_voicings(np.column_stack((signal, -signal)), SAMPLE_RATE)
                    self.assertEqual(result.tonal_coverage, 0, result.events)

    def test_omitted_fifth_result_does_not_claim_it_was_observed(self):
        midi, _ = voicing._guitar_midi_frequencies()
        chroma = np.zeros(12)
        chroma[[0, 4, 10]] = 1 / 3
        notes = np.where(np.isin(midi, (48, 52, 58)), 1., 0.)
        result = voicing._classify_window(chroma, notes, notes, .1)
        self.assertEqual((result['root_pc'], result['chord_type']), (0, '7'))
        self.assertEqual(set(result['pitch_classes']), {0, 4, 10})
        self.assertEqual(set(result['evidence']['required_pitch_classes']), {0, 4, 10})
        self.assertEqual(set(result['evidence']['observed_pitch_classes']), {0, 4, 10})

    def test_resonant_and_comb_harmonics_remain_single_notes(self):
        # A resonant partial can exceed its neighbors without being another
        # instrument/note. Every frequency here is from one measured fundamental.
        time = np.arange(round(SAMPLE_RATE * 2.4)) / SAMPLE_RATE
        for note in (28, 36, 48, 57):
            fundamental = 440 * 2 ** ((note - 69) / 12)
            for timbre in ('formant', 'comb3', 'comb4'):
                signal = np.zeros_like(time)
                for harmonic in range(1, 25):
                    if fundamental * harmonic >= SAMPLE_RATE / 2:
                        continue
                    if timbre == 'formant':
                        strength = (1 + 8 * np.exp(-((harmonic - 3) / 1.1) ** 2)) / harmonic
                    else:
                        strength = (8 if harmonic % int(timbre[-1]) == 0 else 1) / harmonic
                    signal += strength * np.sin(2 * np.pi * fundamental * harmonic * time)
                signal *= .2 / np.max(np.abs(signal))
                with self.subTest(note=note, timbre=timbre):
                    result = voicing.analyze_voicings(np.column_stack((signal, -signal)), SAMPLE_RATE)
                    self.assertEqual(result.tonal_coverage, 0, result.events)

    def test_diagnostics_disclose_optional_fifth_policy(self):
        result = voicing.analyze_voicings(sine_notes((48, 52, 58)), SAMPLE_RATE)
        self.assertEqual(result.diagnostics['template_tone_policy'],
                         'selected_seventh_ninth_perfect_fifth_optional_all_other_tones_required')
        self.assertIn('selected_seventh_ninth_chords_may_omit_perfect_fifth', result.limitations)
        self.assertNotIn('full_extension_templates_require_each_listed_pitch_class', result.limitations)

    def test_bare_thirds_and_missing_extensions_are_not_completed(self):
        for pcs, root, kind in (((0, 4), 0, 'major'), ((0, 3), 0, 'minor'),
                                ((0, 4, 10), 0, '9'), ((4, 7, 10), 0, '7'),
                                ((0, 4, 10), 0, '7b5'), ((0, 4, 11), 0, 'maj7sharp5')):
            chroma = np.zeros(12)
            chroma[list(pcs)] = 1 / len(pcs)
            with self.subTest(pcs=pcs, kind=kind):
                self.assertEqual(voicing._score_chord(chroma, root, kind), -1)


if __name__ == '__main__':
    unittest.main()
