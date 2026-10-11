"""Run non-GUI regressions with a hard Tk guard; disclose all deferred cases."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from catalog import APP_VERSION

GUI_MODULES = {'test_chord_controls', 'test_developer_mode', 'test_native_integration'}


def cases(suite):
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            yield from cases(test)
        else:
            yield test


def verify():
    selected, deferred = [], []
    with patch('tkinter.Tk', side_effect=AssertionError('GUI forbidden in headless verification')), \
            patch('tkinter.Toplevel', side_effect=AssertionError('GUI forbidden in headless verification')):
        suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'))
        for test in cases(suite):
            module = test.id().split('.')[0]
            (deferred if module.endswith('_ui') or module in GUI_MODULES else selected).append(test)
        print(f'Headless: {len(selected)} tests; {len(deferred)} GUI-containing tests deferred.', flush=True)
        began = time.perf_counter()
        result = unittest.TextTestRunner(verbosity=1).run(unittest.TestSuite(selected))
        elapsed = time.perf_counter() - began
    inputs = {}
    for pattern in ('*.py', 'tests/*.py', 'tools/*.py'):
        for path in sorted(ROOT.glob(pattern)):
            inputs[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {'app_version': APP_VERSION, 'ok': result.wasSuccessful(),
            'tests': result.testsRun, 'seconds': round(elapsed, 3),
            'failures': len(result.failures), 'errors': len(result.errors), 'skipped': len(result.skipped),
            'gui_creation_guard': True, 'native_ui_tested': False,
            'deferred_gui_tests': [test.id() for test in deferred], 'source_sha256': inputs}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    receipt = verify()
    args.output.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    raise SystemExit(not receipt['ok'])
