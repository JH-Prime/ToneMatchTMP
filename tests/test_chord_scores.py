"""Vectorized scoring must preserve the established scalar template contract."""
import unittest
from unittest.mock import patch
import numpy as np
import voicing


class ChordScoreTests(unittest.TestCase):
    def test_all_template_scores_match_scalar_reference(self):
        rng = np.random.default_rng(4104)
        examples = [np.zeros(12), np.ones(12) / 12]
        examples += [rng.dirichlet(np.ones(12) * .4) for _ in range(64)]
        for root in range(12):
            for intervals in voicing.CHORD_INTERVALS.values():
                chroma = np.zeros(12)
                chroma[[(root + value) % 12 for value in intervals]] = 1 / len(intervals)
                examples.append(chroma)
        for chroma in examples:
            actual = voicing._template_scores(chroma)
            expected = [(voicing._score_chord(chroma, root, kind), root, kind)
                        for root in range(12) for kind in voicing.CHORD_INTERVALS]
            self.assertEqual(sorted(actual), sorted(expected))

    def test_classifier_keeps_scalar_result_and_alternatives(self):
        def scalar(chroma):
            return [(voicing._score_chord(chroma, root, kind), root, kind)
                    for root in range(12) for kind in voicing.CHORD_INTERVALS]
        rng = np.random.default_rng(14104)
        pitches = np.ones(49)
        midi = np.arange(36, 85)
        for _ in range(96):
            chroma = rng.dirichlet(np.ones(12) * .2)
            actual = voicing._classify_window(chroma, pitches, pitches, .1, midi)
            with patch('voicing._template_scores', side_effect=scalar):
                expected = voicing._classify_window(chroma, pitches, pitches, .1, midi)
            self.assertEqual(actual, expected)
