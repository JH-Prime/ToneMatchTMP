"""Abstentions retain local evidence, never silently become chord claims."""
import unittest
from dataclasses import replace

import numpy as np

from voicing import (_classify_window, _unknown_window, _smooth_labels,
                     _merge_events, _limit_timeline_events, CHORD_INTERVALS)


def classify(chroma, rms=.1):
    pitches = np.ones(49)
    return _classify_window(np.asarray(chroma), pitches, pitches, rms, np.arange(36, 85))


class UncertainChordTests(unittest.TestCase):
    def test_weak_match_retains_only_locally_supported_candidates(self):
        chroma = np.array([.278364, .415352, .003702, .071642, .079295, .000182,
                           .044274, .009158, .006422, .058444, .022301, .010864])
        item = classify(chroma)
        self.assertEqual(item['symbol'], '?')
        self.assertEqual(item['confidence'], 0)
        self.assertEqual(item['evidence']['uncertainty_reason'], 'weak_match')
        self.assertGreater(len(item['alternatives']), 0)
        self.assertLessEqual(len(item['alternatives']), 3)
        observed = set(item['evidence']['observed_pitch_classes'])
        for candidate in item['alternatives']:
            required = {(candidate['root_pc'] + n) % 12 for n in CHORD_INTERVALS[candidate['chord_type']]}
            self.assertTrue(required <= observed)

    def test_low_signal_flat_profile_and_single_note_have_no_candidates(self):
        single = np.zeros(12)
        single[0] = 1
        for chroma, rms, reason in ((single, 0, 'low_signal'),
                                     (single, .1, 'insufficient_tonal_evidence'),
                                     (np.ones(12) / 12, .1, 'insufficient_tonal_evidence')):
            with self.subTest(reason=reason, rms=rms):
                item = classify(chroma, rms)
                self.assertEqual(item['symbol'], '?')
                self.assertFalse(item['alternatives'])
                self.assertEqual(item['evidence']['uncertainty_reason'], reason)

    def test_temporal_rejection_retains_local_candidate_not_neighbor(self):
        chroma = np.zeros(12)
        chroma[[0, 4, 7]] = 1 / 3
        known = classify(chroma)
        known['_start_seconds'] = .6
        rows = [_unknown_window({}), known, _unknown_window({'_start_seconds': 1.2})]
        result = _smooth_labels(rows)[1]
        self.assertEqual(result['symbol'], '?')
        self.assertEqual(result['evidence']['uncertainty_reason'], 'temporal_instability')
        self.assertEqual(result['alternatives'][0]['symbol'], 'C')
        self.assertEqual(set(result['evidence']['observed_pitch_classes']), {0, 4, 7})
        self.assertEqual(result['_start_seconds'], .6)

    def test_unknown_groups_do_not_merge_different_local_explanations(self):
        chroma = np.zeros(12)
        chroma[[0, 4, 7]] = 1 / 3
        candidate = _unknown_window(classify(chroma))
        silence = classify(np.zeros(12), 0)
        rows = [dict(candidate, _start_seconds=0), dict(candidate, _start_seconds=.6),
                dict(silence, _start_seconds=1.2), dict(silence, _start_seconds=1.8)]
        events = _merge_events(rows, .6, 1.2, 3.0, include_shapes=False)
        self.assertEqual(len(events), 2)
        self.assertTrue(events[0].alternatives)
        self.assertFalse(events[1].alternatives)
        self.assertEqual(events[0].end_seconds, events[1].start_seconds)
        self.assertEqual(events[-1].end_seconds, 3)

    def test_output_budget_has_distinct_reason_and_no_candidate_claim(self):
        rows = []
        for i, root in enumerate((0, 2, 5, 7)):
            chroma = np.zeros(12)
            chroma[[(root + n) % 12 for n in (0, 4, 7)]] = 1 / 3
            rows.append(dict(classify(chroma), _start_seconds=i * .6))
        events = _limit_timeline_events(_merge_events(rows, .6, 1.2, 3), 1)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].evidence.get('uncertainty_reason'), 'output_limit')
        self.assertFalse(events[0].alternatives)

    def test_budget_greedy_choice_matches_independent_full_scan(self):
        chroma = np.zeros(12)
        chroma[[0, 4, 7]] = 1 / 3
        prototype = _merge_events([classify(chroma)], .6, 1.2, 1, include_shapes=False)[0]
        rng = np.random.default_rng(5105)
        for _ in range(100):
            count = int(rng.integers(2, 100))
            limit = int(rng.integers(1, count))
            events = [replace(prototype, start_seconds=float(i), end_seconds=float(i + 1),
                              confidence=float(rng.choice([.3, .5, .9])),
                              chord_type='major' if rng.random() > .25 else 'unknown')
                      for i in range(count)]
            ranked = sorted((i for i, event in enumerate(events) if event.chord_type != 'unknown'),
                            key=lambda i: events[i].confidence, reverse=True)
            kept = set()
            for index in ranked:
                trial = sorted(kept | {index})
                gaps = int(trial[0] > 0) + int(trial[-1] < count - 1)
                gaps += sum(after > before + 1 for before, after in zip(trial, trial[1:]))
                if len(trial) + gaps <= limit:
                    kept.add(index)
            actual = _limit_timeline_events(events, limit)
            self.assertEqual({int(e.start_seconds) for e in actual if e.chord_type != 'unknown'}, kept)
            self.assertLessEqual(len(actual), limit)
            self.assertEqual(actual[0].start_seconds, 0)
            self.assertEqual(actual[-1].end_seconds, count)


if __name__ == '__main__':
    unittest.main()
