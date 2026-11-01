"""A successful benchmark run must not hide individual timing regressions."""
from copy import deepcopy
import unittest

from tools.verify_chord_trace import RATE, regression_failures, signal


class TraceMetricsTests(unittest.TestCase):
    def test_annotations_use_exact_frame_boundaries_not_cumulative_float_time(self):
        audio, truth = signal([([48, 52, 55], 'C', 2.13), ([52, 56, 59], 'E', .8),
                               ([45, 48, 52], 'Am', 2.2), ([42, 49, 57], 'F♯m', 2.1)])
        self.assertEqual(truth[-1][1], len(audio) / RATE)
        for left, right in zip(truth, truth[1:]):
            self.assertEqual(left[1], right[0])

    def row(self):
        metrics = {'correctly_labeled_seconds': 3.9,
                   'missing_expected_transitions': 0,
                   'boundary_errors_seconds': [.01, .02]}
        return {'case': 'example', 'baseline': metrics, 'current': deepcopy(metrics)}

    def test_unchanged_trace_passes(self):
        self.assertEqual(regression_failures([self.row()]), [])

    def test_one_regression_is_not_hidden_by_another_improvement(self):
        worse, better = self.row(), self.row()
        worse['current']['correctly_labeled_seconds'] -= .2
        better['current']['correctly_labeled_seconds'] += .3
        self.assertIn('example: correctly labeled duration decreased', regression_failures([worse, better]))

    def test_lost_transition_fails(self):
        row = self.row()
        row['current']['missing_expected_transitions'] = 1
        row['current']['boundary_errors_seconds'][0] = None
        self.assertIn('example: expected transition lost', regression_failures([row]))

    def test_worse_boundary_fails(self):
        row = self.row()
        row['current']['boundary_errors_seconds'][1] = .04
        self.assertIn('example: boundary error increased', regression_failures([row]))

    def test_recovered_transition_is_allowed(self):
        row = self.row()
        row['baseline']['missing_expected_transitions'] = 1
        row['baseline']['boundary_errors_seconds'][0] = None
        self.assertEqual(regression_failures([row]), [])
