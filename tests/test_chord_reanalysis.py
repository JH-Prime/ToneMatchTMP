"""Bounded CQT recovery requires agreement and never replaces good results."""
import unittest
from unittest.mock import patch

import numpy as np
import song_chords
from voicing import _classify_window, _unknown_window


def chord(root=0):
    profile = np.zeros(12)
    profile[[(root + step) % 12 for step in (0, 4, 7)]] = 1 / 3
    pitches = np.ones(49)
    return _classify_window(profile, pitches, pitches, .1, np.arange(36, 85))


class ChordReanalysisTests(unittest.TestCase):
    def run_review(self, primary, reviews, changes=(), cancel=None):
        with patch('song_chords._classify_cqt_region', side_effect=reviews, create=True) as classify:
            result, attempted = song_chords._recover_cqt_window(
                primary, 1.0, np.ones((3000, 2)), np.ones((252, 8)),
                np.arange(24, 108), np.asarray(changes), 1000, cancel)
            return result, attempted, classify.call_args_list

    def test_agreement_promotes_only_locally_evidenced_original_candidate(self):
        original = _unknown_window(chord(), 'weak_match')
        result, attempted, calls = self.run_review(original, [chord(), chord()])
        self.assertTrue(attempted)
        self.assertEqual(result['symbol'], 'C')
        self.assertTrue(result['evidence']['reanalysis_recovered'])
        self.assertNotIn('uncertainty_reason', result['evidence'])
        self.assertEqual(len(calls), 2)

    def test_disagreement_or_missing_original_tones_does_not_promote(self):
        original = _unknown_window(chord(), 'weak_match')
        for reviews in ([chord(), chord(2)], [chord(2), chord(2)]):
            with self.subTest(symbols=[r['symbol'] for r in reviews]):
                result, attempted, _ = self.run_review(original, reviews)
                self.assertEqual(result, original)
                self.assertTrue(attempted)

    def test_good_or_candidateless_or_silent_window_is_not_retried(self):
        for original in (chord(), _unknown_window({}, 'low_signal'),
                         _unknown_window({}, 'insufficient_tonal_evidence')):
            result, attempted, calls = self.run_review(original, [])
            self.assertIs(result, original)
            self.assertFalse(attempted)
            self.assertFalse(calls)

    def test_tiny_harmonic_region_does_not_count_same_evidence_twice(self):
        original = _unknown_window(chord(), 'weak_match')
        result, attempted, calls = self.run_review(original, [], changes=(.9, 1.1))
        self.assertEqual(result, original)
        self.assertFalse(attempted)
        self.assertFalse(calls)

    def test_weak_review_does_not_promote_and_cancellation_is_checked(self):
        original = _unknown_window(chord(), 'weak_match')
        weak = chord()
        weak['confidence'] = .4
        result, _, _ = self.run_review(original, [weak, weak])
        self.assertEqual(result, original)
        with self.assertRaises(song_chords.ChordAnalysisCancelled):
            self.run_review(original, [chord(), chord()], cancel=lambda: True)

    def test_dense_uncertainty_timeline_stays_reopenable_without_time_loss(self):
        from chord_edits import effective_voicing
        candidates = [_unknown_window(chord(root), 'weak_match') for root in (0, 2)]
        counter = iter(range(20000))
        def alternating(*args):
            return dict(candidates[next(counter) % 2])
        with patch('song_chords._classify_cqt_region', side_effect=alternating), \
                patch('song_chords._estimate_tuning', return_value=(0., 'insufficient_tonal_evidence')):
            result = song_chords.analyze_song_chords(np.zeros((8000 * 501, 1), np.float32), 8000)
        self.assertLessEqual(result['event_count'], 10000)
        self.assertTrue(result['diagnostics']['events_truncated'])
        self.assertEqual(result['events'][0]['start_seconds'], 0)
        self.assertEqual(result['events'][-1]['end_seconds'], 501)
        self.assertEqual(result['events'][0]['evidence']['uncertainty_reason'], 'output_limit')
        effective_voicing({'chord_voicing': result})


if __name__ == '__main__':
    unittest.main()
