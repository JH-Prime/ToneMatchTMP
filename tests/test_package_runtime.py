"""Windows package identity and writable state, without installing a package."""
import builtins
import ctypes
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import package_runtime as runtime


FAMILY = 'ToneMatchTMP.Test_123456789abcd'


class PackageRuntimeTests(unittest.TestCase):
    def setUp(self):
        runtime.package_identity.cache_clear()
        self.addCleanup(runtime.package_identity.cache_clear)

    def kernel(self, *, full_result=122, family=FAMILY, family_result=0,
               family_length=None):
        kernel = Mock()
        kernel.GetCurrentPackageFullName.return_value = full_result

        def get_family(length, buffer):
            if buffer is None:
                ctypes.cast(length, ctypes.POINTER(ctypes.c_uint32))[0] = (
                    len(family) + 1 if family_length is None else family_length)
                return 122
            if family_result == 0:
                buffer.value = family
            return family_result

        kernel.GetCurrentPackageFamilyName.side_effect = get_family
        return kernel

    def detect(self, kernel):
        with patch.object(runtime.sys, 'platform', 'win32'), \
                patch.object(runtime.ctypes, 'WinDLL', return_value=kernel, create=True):
            return runtime.package_identity()

    def test_native_no_package_is_the_only_windows_portable_result(self):
        kernel = self.kernel(full_result=15700)
        self.assertEqual(self.detect(kernel).status, 'unpackaged')
        kernel.GetCurrentPackageFamilyName.assert_not_called()

    def test_native_package_uses_family_and_caches_process_identity(self):
        kernel = self.kernel()
        identity = self.detect(kernel)
        self.assertEqual(identity.status, 'packaged')
        self.assertEqual(identity.family_name, FAMILY)
        self.assertIs(self.detect(kernel), identity)
        self.assertEqual(kernel.GetCurrentPackageFullName.call_count, 1)

    def test_nonwindows_does_not_load_windows_library(self):
        with patch.object(runtime.sys, 'platform', 'linux'), \
                patch.object(runtime.ctypes, 'WinDLL', create=True) as load:
            self.assertEqual(runtime.package_identity().status, 'unpackaged')
        load.assert_not_called()

    def test_native_errors_never_become_portable_identity(self):
        for result in (0, 5, 87):
            with self.subTest(result=result):
                runtime.package_identity.cache_clear()
                identity = self.detect(self.kernel(full_result=result))
                self.assertEqual(identity.status, 'unknown')
                self.assertIsNotNone(identity.error_code)

    def test_missing_api_and_os_failure_are_unknown(self):
        for error in (AttributeError('missing entry point'), OSError('unavailable')):
            with self.subTest(error=error), patch.object(runtime.sys, 'platform', 'win32'), \
                    patch.object(runtime.ctypes, 'WinDLL', side_effect=error, create=True):
                runtime.package_identity.cache_clear()
                self.assertEqual(runtime.package_identity().status, 'unknown')

    def test_programming_errors_are_not_silently_hidden(self):
        kernel = self.kernel()
        kernel.GetCurrentPackageFullName.side_effect = TypeError('bad binding')
        with self.assertRaises(TypeError):
            self.detect(kernel)

    def test_os_failure_during_native_call_keeps_original_error_code(self):
        kernel = self.kernel()
        error = OSError('native call failed')
        error.winerror = 5
        kernel.GetCurrentPackageFullName.side_effect = error
        identity = self.detect(kernel)
        self.assertEqual(identity.status, 'unknown')
        self.assertEqual(identity.error_code, 5)

    def test_failed_family_size_query_does_not_allocate_or_retry(self):
        kernel = self.kernel()
        kernel.GetCurrentPackageFamilyName.side_effect = None
        kernel.GetCurrentPackageFamilyName.return_value = 5
        identity = self.detect(kernel)
        self.assertEqual(identity.status, 'unknown')
        self.assertEqual(identity.error_code, 5)
        self.assertEqual(kernel.GetCurrentPackageFamilyName.call_count, 1)

    def test_family_read_errors_and_invalid_sizes_fail_closed(self):
        for kernel in (self.kernel(family_result=5), self.kernel(family_length=0),
                       self.kernel(family_length=1000000)):
            with self.subTest(kernel=kernel):
                runtime.package_identity.cache_clear()
                self.assertEqual(self.detect(kernel).status, 'unknown')

    def test_family_name_cannot_escape_user_package_directory(self):
        for family in ('../escape', r'C:\\evil', r'name\\evil_123456789abcd',
                       'bad/name_123456789abcd', '', 'name_..'):
            with self.subTest(family=family):
                runtime.package_identity.cache_clear()
                self.assertEqual(self.detect(self.kernel(family=family)).status, 'unknown')

    def test_packaged_data_and_cache_use_localstate(self):
        with tempfile.TemporaryDirectory() as temporary, \
                patch.dict(runtime.os.environ, {'LOCALAPPDATA': temporary,
                                               'NUMBA_CACHE_DIR': 'installed/cache'}), \
                patch.object(runtime, 'package_identity', return_value=runtime.PackageIdentity('packaged', FAMILY)):
            expected = Path(temporary) / 'Packages' / FAMILY / 'LocalState'
            self.assertEqual(runtime.managed_data_root(), expected)
            runtime.configure_runtime_cache()
            self.assertEqual(runtime.os.environ['NUMBA_CACHE_DIR'], str(expected / 'cache' / 'numba'))

    def test_unknown_identity_uses_user_data_without_package_name(self):
        with tempfile.TemporaryDirectory() as temporary, \
                patch.dict(runtime.os.environ, {'LOCALAPPDATA': temporary}), \
                patch.object(runtime, 'package_identity', return_value=runtime.PackageIdentity('unknown', error_code=5)):
            expected = Path(temporary) / 'ToneMatchTMP'
            self.assertEqual(runtime.managed_data_root(), expected)
            runtime.configure_runtime_cache()
            self.assertEqual(runtime.os.environ['NUMBA_CACHE_DIR'], str(expected / 'cache' / 'numba'))

    def test_missing_or_relative_localappdata_uses_user_home(self):
        with tempfile.TemporaryDirectory() as temporary, \
                patch.object(runtime.Path, 'home', return_value=Path(temporary)), \
                patch.object(runtime, 'package_identity', return_value=runtime.PackageIdentity('packaged', FAMILY)):
            for value in ('', 'relative/path'):
                with self.subTest(value=value), patch.dict(runtime.os.environ, {'LOCALAPPDATA': value}):
                    expected = Path(temporary) / 'AppData' / 'Local' / 'Packages' / FAMILY / 'LocalState'
                    self.assertEqual(runtime.managed_data_root(), expected)

    def test_portable_data_and_cache_policy_are_unchanged(self):
        with patch.dict(runtime.os.environ, {'NUMBA_CACHE_DIR': 'custom/cache'}), \
                patch.object(runtime, 'package_identity', return_value=runtime.PackageIdentity('unpackaged')):
            self.assertIsNone(runtime.managed_data_root())
            runtime.configure_runtime_cache()
            self.assertEqual(runtime.os.environ['NUMBA_CACHE_DIR'], 'custom/cache')

    def test_app_managed_data_never_writes_beside_executable(self):
        import app
        for identity in (runtime.PackageIdentity('packaged', FAMILY),
                         runtime.PackageIdentity('unknown', error_code=5)):
            with self.subTest(status=identity.status), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                installed = root / 'installed'
                installed.mkdir()
                local = root / 'local'
                with patch.object(runtime, 'package_identity', return_value=identity), \
                        patch.dict(runtime.os.environ, {'LOCALAPPDATA': str(local)}), \
                        patch.object(app.sys, 'frozen', True, create=True), \
                        patch.object(app.sys, 'executable', str(installed / 'ToneMatchTMP.exe')):
                    expected = runtime.managed_data_root()
                    self.assertEqual(app._runtime_data_root(), expected)
                    self.assertTrue(expected.is_dir())
                    self.assertFalse((installed / 'data').exists())

    def test_packaged_diagnostics_do_not_create_tk_or_run_updater(self):
        import app
        import update_startup
        with patch.object(runtime, 'package_identity', return_value=runtime.PackageIdentity('packaged', FAMILY)), \
                patch.object(app.tk, 'Tk', side_effect=AssertionError('Tk is forbidden')), \
                patch.object(app.multiprocessing, 'freeze_support'), \
                patch.object(update_startup, 'run_startup', side_effect=AssertionError('startup UI is forbidden')):
            with patch.object(app.sys, 'argv', ['app', '--self-test-output', 'result.json']), \
                    patch.object(app, 'run_self_test', return_value=0) as diagnostic:
                self.assertEqual(app.main(), 0)
                diagnostic.assert_called_once_with('result.json')
            with patch.object(app.sys, 'argv', ['app', '--stem-self-test-output', 'result.json']), \
                    patch('stem_diagnostics.stem_self_test_cli', return_value=0) as diagnostic:
                self.assertEqual(app.main(), 0)
                diagnostic.assert_called_once_with(['--stem-self-test-output', 'result.json'])

    def test_app_sets_cache_before_first_numpy_import(self):
        class ReachedNumpy(Exception):
            pass

        original_import = builtins.__import__
        with tempfile.TemporaryDirectory() as temporary, \
                patch.dict(runtime.os.environ, {'LOCALAPPDATA': temporary}), \
                patch.object(runtime, 'package_identity', return_value=runtime.PackageIdentity('packaged', FAMILY)):
            expected = Path(temporary) / 'Packages' / FAMILY / 'LocalState' / 'cache' / 'numba'

            def guarded_import(name, *args, **kwargs):
                if name == 'numpy':
                    self.assertEqual(runtime.os.environ.get('NUMBA_CACHE_DIR'), str(expected))
                    raise ReachedNumpy()
                return original_import(name, *args, **kwargs)

            source = Path(__file__).resolve().parents[1] / 'app.py'
            with patch('builtins.__import__', side_effect=guarded_import), self.assertRaises(ReachedNumpy):
                exec(compile(source.read_text(encoding='utf-8'), str(source), 'exec'),
                     {'__name__': 'cache_order_probe', '__file__': str(source)})


if __name__ == '__main__':
    unittest.main()
