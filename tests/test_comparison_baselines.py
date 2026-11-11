"""Pinned release comparison contracts without Git or actual audio analysis."""
from contextlib import ExitStack
import hashlib
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import verify_chord_precision as precision
import verify_cqt_harmonics as harmonics


COMMITS = {'v0.1.06': '7563242b054065f8893a6c6e344046e188e0b947',
           'v0.1.07': 'e8142f80151d5d92b05bc6c3e5c091934e63a093'}


class ComparisonBaselineTests(unittest.TestCase):
    def test_unapproved_refs_are_rejected_before_git_access(self):
        for module in (precision, harmonics):
            with self.subTest(module=module.__name__), \
                    patch.object(module.subprocess, 'check_output') as git, \
                    self.assertRaisesRegex(ValueError, 'Unsupported'):
                module.compare('HEAD')
            git.assert_not_called()

    def test_moved_release_tags_are_rejected_before_loading_analyzers(self):
        for module in (precision, harmonics):
            for ref in COMMITS:
                with self.subTest(module=module.__name__, ref=ref), \
                        patch.object(module, 'source_hashes', return_value=module.IMPORT_HASHES), \
                        patch.object(module.subprocess, 'check_output', return_value='0' * 40), \
                        patch.object(module, 'baseline_modules') as loader, \
                        self.assertRaisesRegex(ValueError, 'immutable'):
                    module.compare(ref)
                loader.assert_not_called()

    def test_precision_accepts_pinned_v107_before_reading_source(self):
        class SourceReadReached(Exception):
            pass
        with patch.object(precision, 'source_hashes', return_value=precision.IMPORT_HASHES), \
                patch.object(precision.subprocess, 'check_output',
                             side_effect=[COMMITS['v0.1.07'], SourceReadReached]), \
                self.assertRaises(SourceReadReached):
            precision.compare('v0.1.07')

    def harmonic_report(self, ref, *, current_known=False, baseline_known=False, root=None):
        audio = np.zeros((harmonics.RATE, 2), dtype=np.float32)
        def result(known):
            return {'method_id': 'cqt', 'events': [{
                'start_seconds': 0., 'end_seconds': 1.,
                'chord_type': 'power5' if known else 'unknown',
                'symbol': 'C5' if known else '?'}]}
        source = b'shared source fixture'
        hashes = {'guitar_shapes.py': hashlib.sha256(source).hexdigest()}
        case = {'name': 'controlled_evaluation', 'audio': audio, 'root': root,
                'labels': [] if root is None else ['C5'],
                'require_unknown': root is None, 'limitation': False}
        def git(args, **_kwargs):
            return COMMITS[ref] if args[1] == 'rev-parse' else source
        with ExitStack() as stack:
            for target, name, value in (
                    (harmonics, 'IMPORT_HASHES', hashes),
                    (harmonics, 'source_hashes', Mock(return_value=hashes)),
                    (harmonics.subprocess, 'check_output', Mock(side_effect=git)),
                    (harmonics, 'fixtures', Mock(return_value=[case])),
                    (harmonics, 'tone_audio', Mock(return_value=audio)),
                    (harmonics, 'baseline_modules', Mock(return_value={'song_chords':
                        SimpleNamespace(analyze_song_chords=Mock(return_value=result(baseline_known)))})),
                    (harmonics.song_chords, 'analyze_song_chords', Mock(return_value=result(current_known)))):
                stack.enter_context(patch.object(target, name, value))
            return harmonics.compare(ref)

    def test_v106_still_requires_improvement_but_v107_allows_equal_correctness(self):
        older = self.harmonic_report('v0.1.06')
        self.assertFalse(older['passed'])
        self.assertIn('No false-recognition improvement', older['failures'])
        current = self.harmonic_report('v0.1.07')
        self.assertTrue(current['passed'], current['failures'])
        self.assertEqual(current['baseline_commit'], COMMITS['v0.1.07'])

    def test_v107_still_rejects_new_false_chords(self):
        report = self.harmonic_report('v0.1.07', current_known=True)
        self.assertFalse(report['passed'])
        self.assertTrue(any('incorrect promotion' in failure for failure in report['failures']))
        self.assertTrue(any('targeted singleton' in failure for failure in report['failures']))

    def test_v107_still_protects_correct_power_chords(self):
        report = self.harmonic_report('v0.1.07', baseline_known=True, root=0)
        self.assertFalse(report['passed'])
        self.assertTrue(any('recognized correctness regressed' in failure for failure in report['failures']))
        self.assertTrue(any('independent fifth' in failure for failure in report['failures']))


if __name__ == '__main__':
    unittest.main()
