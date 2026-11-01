"""Precision reporting must distinguish correctness from mere coverage."""
import unittest
from unittest.mock import patch

from tools import verify_chord_precision as precision
from tools.verify_chord_precision import fixtures, precision_metrics, regression_failures, validate_annotations


def event(start, end, symbol, alternatives=()):
    return {'start_seconds': start, 'end_seconds': end, 'symbol': symbol,
            'chord_type': 'unknown' if symbol == '?' else 'recognized',
            'alternatives': [{'symbol': value} for value in alternatives]}


class PrecisionMetricTests(unittest.TestCase):
    def test_wrong_unknown_and_correct_seconds_are_separate(self):
        result = {'events': [event(0, 1, 'C'), event(1, 2, 'G'),
                             event(2, 3, '?', ['C']), event(3, 4, '?')]}
        actual = precision_metrics(result, [(0, 4, ['C'])], 4)
        self.assertEqual(actual['correct_recognized_seconds'], 1)
        self.assertEqual(actual['incorrect_recognized_seconds'], 1)
        self.assertEqual(actual['scored_unknown_seconds'], 2)
        self.assertEqual(actual['unknown_with_correct_candidate_seconds'], 1)

    def test_ambiguous_truth_accepts_each_declared_label_without_double_count(self):
        result = {'events': [event(0, 1, 'C6'), event(1, 2, 'Am7/C')]}
        actual = precision_metrics(result, [(0, 2, ['C6', 'Am7/C'])], 2)
        self.assertEqual(actual['correct_recognized_seconds'], 2)
        self.assertEqual(actual['root_correct_seconds'], 2)
        self.assertEqual(actual['triad_correct_seconds'], 2)
        self.assertEqual(actual['bass_correct_seconds'], 2)

    def test_harmonic_components_do_not_hide_wrong_extension_or_bass(self):
        result = {'events': [event(0, 1, 'C'), event(1, 2, 'C7/E')]}
        actual = precision_metrics(result, [(0, 2, ['C7'])], 2)
        self.assertEqual(actual['correct_recognized_seconds'], 0)
        self.assertEqual(actual['incorrect_recognized_seconds'], 2)
        self.assertEqual(actual['root_correct_seconds'], 2)
        self.assertEqual(actual['triad_correct_seconds'], 2)
        self.assertEqual(actual['bass_correct_seconds'], 1)

    def test_arpeggio_warmup_is_unscored_not_incorrect(self):
        result = {'events': [event(0, 1, 'G'), event(1, 2, '?')]}
        actual = precision_metrics(result, [(1, 2, ['C'])], 2)
        self.assertEqual(actual['scored_seconds'], 1)
        self.assertEqual(actual['unscored_seconds'], 1)
        self.assertEqual(actual['incorrect_recognized_seconds'], 0)
        self.assertEqual(actual['scored_unknown_seconds'], 1)

    def test_negative_truth_penalizes_any_named_chord(self):
        actual = precision_metrics({'events': [event(0, 1, 'C'), event(1, 2, '?')]},
                                   [(0, 2, [])], 2)
        self.assertEqual(actual['incorrect_recognized_seconds'], 1)
        self.assertEqual(actual['root_correct_seconds'], 0)
        self.assertEqual(actual['chord_truth_seconds'], 0)

    def test_malformed_annotation_intervals_are_rejected(self):
        result = {'events': [event(0, 2, '?')]}
        for truth in ([(0, 1.5, ['C']), (1, 2, ['C'])],
                      [(-1, 2, ['C'])], [(0, 3, ['C'])],
                      [(0, float('nan'), ['C'])], [(1, 1, ['C'])]):
            with self.subTest(truth=truth), self.assertRaises(ValueError):
                precision_metrics(result, truth, 2)

    def test_malformed_prediction_and_annotation_labels_are_rejected(self):
        for result in ({'events': [event(0, float('nan'), 'C')]},
                       {'events': [event(0, 1, 'C'), event(.5, 2, 'C')]},
                       {'events': [event(0, 2, 'not-a-chord')]}):
            with self.subTest(result=result), self.assertRaises(ValueError):
                precision_metrics(result, [(0, 2, ['C'])], 2)
        for labels in ('C', ['?'], ['unknown']):
            with self.subTest(labels=labels), self.assertRaises(ValueError):
                precision_metrics({'events': [event(0, 2, '?')]}, [(0, 2, labels)], 2)

    def test_six_nine_suffix_is_not_mistaken_for_a_slash_bass(self):
        actual = precision_metrics({'events': [event(0, 1, 'C6/9/E')]},
                                   [(0, 1, ['C6/9'])], 1)
        self.assertEqual(actual['root_correct_seconds'], 1)
        self.assertEqual(actual['triad_correct_seconds'], 1)
        self.assertEqual(actual['bass_correct_seconds'], 0)

    def test_triad_component_includes_root_and_quality(self):
        actual = precision_metrics({'events': [event(0, 1, 'Cm'), event(1, 2, 'G')]},
                                   [(0, 2, ['C'])], 2)
        self.assertEqual(actual['root_correct_seconds'], 1)
        self.assertEqual(actual['triad_correct_seconds'], 0)

    def test_gate_rejects_wrong_promotion_even_if_aggregate_error_decreases(self):
        before = {'incorrect_recognized_seconds': 2, 'correct_recognized_seconds': 1,
                  'unknown_candidate_negative_seconds': 0}
        after = {**before, 'incorrect_recognized_seconds': 1,
                 'correct_recognized_seconds': 3}
        changes = {'incorrect_newly_recognized_seconds': .05}
        self.assertIn('incorrect promotion in baseline unknown',
                      regression_failures(before, after, changes))

    def test_gate_does_not_accept_coverage_gain_with_new_wrong_seconds(self):
        before = {'incorrect_recognized_seconds': 0, 'correct_recognized_seconds': 1,
                  'unknown_candidate_negative_seconds': 0}
        after = {**before, 'incorrect_recognized_seconds': .2,
                 'correct_recognized_seconds': 2}
        self.assertIn('increased incorrect_recognized_seconds',
                      regression_failures(before, after,
                                          {'incorrect_newly_recognized_seconds': 0}))

    def test_gate_retains_correctness_and_negative_candidate_guards(self):
        before = {'incorrect_recognized_seconds': 0, 'correct_recognized_seconds': 1,
                  'unknown_candidate_negative_seconds': 0}
        after = {**before, 'correct_recognized_seconds': .5,
                 'unknown_candidate_negative_seconds': .1}
        failures = regression_failures(before, after, {'incorrect_newly_recognized_seconds': 0})
        self.assertIn('recognized correctness regressed', failures)
        self.assertIn('increased unknown_candidate_negative_seconds', failures)

    def test_fixture_annotations_are_valid_and_audio_is_repeatable(self):
        import numpy as np
        first, second = fixtures(), fixtures()
        self.assertEqual(len(first), 31)
        self.assertEqual(len({case['name'] for case in first}), len(first))
        for left, right in zip(first, second):
            with self.subTest(case=left['name']):
                validate_annotations(left['truth'], len(left['audio']) / 22050)
                self.assertTrue(np.isfinite(left['audio']).all())
                np.testing.assert_array_equal(left['audio'], right['audio'])

    def test_resonant_and_comb_singletons_remain_negative_truth(self):
        import numpy as np
        cases = {case['name']: case for case in fixtures()}
        for shape in ('formant', 'comb3', 'comb4'):
            for note in (36, 48, 57):
                with self.subTest(shape=shape, note=note):
                    case = cases[f'{shape}_singleton_midi_{note}']
                    self.assertEqual(case['truth'], [(0., 2.4, [])])
                    self.assertAlmostEqual(float(np.max(np.abs(case['audio']))), .2)
                    np.testing.assert_array_equal(case['audio'][:, 0], -case['audio'][:, 1])

    def test_weak_unrelated_anchor_cannot_justify_an_unplayed_harmonic(self):
        cases = {case['name']: case for case in fixtures()}
        for note in (50, 58, 61):
            case = cases[f'formant_with_weak_anchor_midi_{note}']
            self.assertEqual(case['truth'], [(0., 2.4, [])])

    def test_passing_melody_and_brief_modulation_have_explicit_truth(self):
        cases = {case['name']: case for case in fixtures()}
        melody = cases['passing_melody_over_C']
        self.assertEqual(melody['truth'], [(0., 5., ['C'])])
        modulation = cases['brief_secondary_dominant']
        self.assertEqual([labels for _, _, labels in modulation['truth']],
                         [['C'], ['E'], ['Am'], ['F♯m']])
        for (start, end, _), duration in zip(modulation['truth'], (2.13, .8, 2.2, 2.1)):
            self.assertAlmostEqual(end - start, round(duration * 22050) / 22050)

    def test_changed_shared_baseline_dependency_is_rejected_before_loading(self):
        # The isolated baseline loader replaces only voicing/song_chords; its
        # guitar_shapes import is shared with the current checkout.
        current = {name: 'current-digest' for name in precision.SOURCE_FILES}
        with patch.object(precision, 'IMPORT_HASHES', current), \
                patch.object(precision, 'source_hashes', return_value=current), \
                patch.object(precision.subprocess, 'check_output', side_effect=[
                    precision.BASELINE_COMMIT, b'old-voicing', b'old-song', b'old-shapes']), \
                patch.object(precision, 'baseline_modules', side_effect=AssertionError(
                    'Baseline must not load with a changed shared dependency')) as load:
            with self.assertRaisesRegex(RuntimeError, 'Shared baseline dependency differs'):
                precision.compare(methods=('fft',))
            load.assert_not_called()


if __name__ == '__main__':
    unittest.main()
