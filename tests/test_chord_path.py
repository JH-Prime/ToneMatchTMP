"""Duration consistency and exact path selection without an audio model."""
import unittest
import numpy as np

from voicing import _smooth_labels, _unknown_window


def option(root, kind, score):
    return dict(_unknown_window({}), root_pc=root, chord_type=kind,
                symbol=f'{root}:{kind}', _score=score, confidence=.6)


def reference_path(windows):
    """Independent, deliberately quadratic form of the declared objective."""
    pools = [w.get('_temporal_candidates') or w.get('_candidates') or [w] for w in windows]
    labels = [set((c['root_pc'], c['chord_type']) for c in pool) for pool in pools]
    if len(pools) > 1:
        pools = [[c for c in pool if c['chord_type'] == 'unknown'
                  or (c['root_pc'], c['chord_type']) in
                  ((labels[i - 1] if i else set()) | (labels[i + 1] if i + 1 < len(pools) else set()))]
                 or [_unknown_window(windows[i])] for i, pool in enumerate(pools)]
    scores, paths = [], []
    for i, pool in enumerate(pools):
        next_scores, next_paths = [], []
        weight = windows[i].get('_evidence_seconds', .6) / .6
        for c in pool:
            if not i:
                next_scores.append(c.get('_score', 0) * weight)
                next_paths.append([c])
                continue
            values = [s - (.045 if (p['root_pc'], p['chord_type']) != (c['root_pc'], c['chord_type']) else 0)
                      for s, p in zip(scores, pools[i - 1])]
            best = int(np.argmax(values))
            next_scores.append(values[best] + c.get('_score', 0) * weight)
            next_paths.append(paths[best] + [c])
        scores, paths = next_scores, next_paths
    result = paths[int(np.argmax(scores))]
    labels = [(c['root_pc'], c['chord_type']) for c in result]
    if len(labels) > 1:
        result = [c if (i and labels[i - 1] == labels[i]) or (i + 1 < len(labels) and labels[i + 1] == labels[i])
                  or c['chord_type'] == 'unknown' else _unknown_window(windows[i])
                  for i, c in enumerate(result)]
    return [(c['root_pc'], c['chord_type']) for c in result]


class ChordPathTests(unittest.TestCase):
    def test_more_observations_do_not_make_a_brief_extension_more_certain(self):
        core = option(0, 'major', .8)
        extra = option(0, 'add9', .86)
        def track(extension_frames):
            pools = [[core]] * 6 + [[extra, core]] * extension_frames + [[core]] * 6
            return [dict(pool[0], _temporal_candidates=pool, _start_seconds=i * .2,
                         _evidence_seconds=.2) for i, pool in enumerate(pools)]
        short = _smooth_labels(track(2))
        self.assertTrue(all(c['chord_type'] == 'major' for c in short))
        sustained = _smooth_labels(track(8))
        self.assertIn('add9', [c['chord_type'] for c in sustained])

    def test_path_agrees_with_reference_including_ties_and_unknowns(self):
        rng = np.random.default_rng(104)
        for trial in range(100):
            windows = []
            for i in range(24):
                roots = rng.choice(12, size=int(rng.integers(1, 13)), replace=False)
                pool = [option(int(root), 'major', float(rng.choice([0, .045, .5, .8, .9]))) for root in roots]
                if i == 12 and trial % 2:
                    pool = [_unknown_window({})]
                windows.append(dict(pool[0], _candidates=pool, _start_seconds=i * .2,
                                    _evidence_seconds=.2 if trial % 2 else .6))
            with self.subTest(trial=trial):
                actual = _smooth_labels(windows)
                self.assertEqual([(c['root_pc'], c['chord_type']) for c in actual], reference_path(windows))
                self.assertEqual([c['_start_seconds'] for c in actual], [w['_start_seconds'] for w in windows])
