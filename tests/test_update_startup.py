"""Startup update lifecycle without windows, network or subprocess execution."""
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

import update_startup as startup


class ImmediateThread:
    def __init__(self, target, **_kwargs):
        self.target = target

    def start(self):
        self.target()


class StartupTests(unittest.TestCase):
    def controller(self, prepare, launch=None):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        view = Mock()
        finish = Mock()
        launch = launch or Mock()
        controller = startup.StartupController(
            '0.1.07', root / 'origin', root / 'data', root / 'cache',
            view, finish, prepare=prepare, launch=launch)
        return controller, view, finish, launch

    def start(self, controller):
        with patch.object(startup.threading, 'Thread', ImmediateThread):
            controller.start()

    def test_source_nonwindows_and_explicit_bypass_never_check(self):
        with patch.object(startup.sys, 'frozen', False, create=True), \
                patch.object(startup.sys, 'platform', 'win32'):
            self.assertFalse(startup.should_check_for_updates([]))
        with patch.object(startup.sys, 'frozen', True, create=True):
            with patch.object(startup.sys, 'platform', 'linux'):
                self.assertFalse(startup.should_check_for_updates([]))
            with patch.object(startup.sys, 'platform', 'win32'):
                self.assertTrue(startup.should_check_for_updates([]))
                self.assertFalse(startup.should_check_for_updates(['--skip-update']))
                self.assertFalse(startup.should_check_for_updates(['--self-test-output', 'x']))
                self.assertFalse(startup.should_check_for_updates(['--stem-self-test-output', 'x']))

    def test_worker_only_queues_progress_until_main_thread_polls(self):
        def prepare(_version, _origin, _cache, _cancel, progress):
            progress('downloading', 15, 100)
            return None
        controller, view, finish, launch = self.controller(prepare)
        self.start(controller)
        view.progress.assert_not_called()
        finish.assert_not_called()
        self.assertFalse(controller.poll())
        view.progress.assert_called_once_with('downloading', 15, 100)
        finish.assert_called_once_with(False)
        launch.assert_not_called()

    def test_verified_update_launches_with_original_data_context(self):
        path = Path('newer.exe')
        controller, view, finish, launch = self.controller(Mock(return_value=path))
        self.start(controller)
        controller.poll()
        launch.assert_called_once_with(path, controller.installation_root, controller.data_root)
        finish.assert_called_once_with(True)
        self.assertTrue(controller.finished)

    def test_cancel_wins_over_already_queued_ready_result(self):
        controller, view, finish, launch = self.controller(Mock(return_value=Path('newer.exe')))
        self.start(controller)
        controller.cancel()
        controller.poll()
        self.assertTrue(controller.cancel_event.is_set())
        launch.assert_not_called()
        finish.assert_called_once_with(False)

    def test_close_does_not_open_current_app_or_launch_update(self):
        controller, view, finish, launch = self.controller(Mock(return_value=Path('newer.exe')))
        controller.cancel(exit_application=True)
        self.start(controller)
        controller.poll()
        finish.assert_called_once_with(True)
        launch.assert_not_called()

    def test_network_failure_or_failed_launch_keeps_original_app(self):
        for prepare, launch in ((Mock(side_effect=OSError('offline')), Mock()),
                                (Mock(return_value=Path('newer.exe')), Mock(side_effect=OSError('denied')))):
            with self.subTest(prepare=prepare):
                controller, view, finish, launch = self.controller(prepare, launch)
                self.start(controller)
                controller.poll()
                finish.assert_called_once_with(False)
                self.assertTrue(controller.finished)

    def test_progress_mailbox_stays_bounded(self):
        def prepare(_version, _origin, _cache, _cancel, progress):
            for number in range(10000):
                progress('verifying', number, 10000)
        controller, view, finish, launch = self.controller(prepare)
        self.start(controller)
        self.assertEqual(controller.progress_queue.qsize(), 1)
        controller.poll()
        view.progress.assert_called_once_with('verifying', 9999, 10000)

    def test_inherited_origin_only_accepted_for_managed_target(self):
        from auto_update import installation_cache
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            origin = root / 'portable'
            origin.mkdir()
            data = origin / 'data'
            cache = root / 'local' / 'ToneMatchTMP' / 'updates'
            managed = installation_cache(origin, cache) / 'versions' / 'ToneMatchTMP-v0.1.08'
            managed.mkdir(parents=True)
            executable = managed / 'ToneMatchTMP-v0.1.08.exe'
            executable.write_bytes(b'fixture')
            environment = {'LOCALAPPDATA': str(root / 'local'),
                           'TONEMATCH_UPDATE_ORIGIN': str(origin),
                           'TONEMATCH_UPDATE_DATA': str(data),
                           'TONEMATCH_UPDATE_TARGET': str(executable)}
            with patch.object(startup.sys, 'frozen', True, create=True), \
                    patch.object(startup.sys, 'executable', str(executable)), \
                    patch.dict(startup.os.environ, environment, clear=True):
                self.assertEqual(startup.inherited_context(), (origin.resolve(), data.resolve()))
                with patch.dict(startup.os.environ, {'TONEMATCH_UPDATE_DATA': str(root / 'unrelated')}):
                    self.assertIsNone(startup.inherited_context())
                with patch.dict(startup.os.environ, {'TONEMATCH_UPDATE_TARGET': str(origin / 'other.exe')}):
                    self.assertIsNone(startup.inherited_context())
                with patch.object(startup.sys, 'executable', str(root / 'outside.exe')):
                    self.assertIsNone(startup.inherited_context())

    def test_launch_uses_argument_list_reset_environment_and_no_shell(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / 'new release' / 'ToneMatchTMP-v0.1.08.exe'
            origin = root / 'original'
            data = origin / 'data'
            with patch.object(startup.subprocess, 'Popen') as popen, \
                    patch.object(startup, '_windows_dll_directory') as dll, \
                    patch.object(startup.sys, '_MEIPASS', str(root / 'old' / '_internal'), create=True), \
                    patch.dict(startup.os.environ, {'PATH': str(root / 'old' / '_internal') + ';C:\\Windows'}):
                startup.launch_update(target, origin, data)
            args, kwargs = popen.call_args
            self.assertEqual(args[0], [str(target.resolve()), '--skip-update'])
            self.assertFalse(kwargs['shell'])
            self.assertEqual(kwargs['env']['PYINSTALLER_RESET_ENVIRONMENT'], '1')
            self.assertEqual(kwargs['env']['TONEMATCH_UPDATE_ORIGIN'], str(origin.resolve()))
            self.assertEqual(kwargs['env']['TONEMATCH_UPDATE_DATA'], str(data.resolve()))
            self.assertEqual(kwargs['env']['TONEMATCH_UPDATE_TARGET'], str(target.resolve()))
            self.assertEqual(kwargs['env']['NUMBA_CACHE_DIR'], str(data.resolve() / 'cache' / 'numba'))
            self.assertNotIn(str(root / 'old' / '_internal'), kwargs['env']['PATH'])
            self.assertEqual(dll.call_count, 2)

    def test_launch_restores_dll_directory_when_process_start_fails(self):
        with patch.object(startup.subprocess, 'Popen', side_effect=OSError('failed')), \
                patch.object(startup, '_windows_dll_directory') as dll, \
                patch.object(startup.sys, '_MEIPASS', 'old-runtime', create=True):
            with self.assertRaises(OSError):
                startup.launch_update(Path('new.exe'), Path('old'), Path('data'))
        self.assertEqual(dll.call_args_list[-1].args, ('old-runtime',))

    def test_app_diagnostic_path_does_not_construct_startup_or_gui(self):
        import app
        with patch.object(app.sys, 'argv', ['app', '--self-test-output', 'diagnostic.json']), \
                patch.object(app.multiprocessing, 'freeze_support'), \
                patch.object(app, 'run_self_test', return_value=0) as diagnostic, \
                patch.object(app.tk, 'Tk') as tk, \
                patch.object(startup, 'run_startup_update') as update:
            self.assertEqual(app.main(), 0)
        diagnostic.assert_called_once_with('diagnostic.json')
        tk.assert_not_called()
        update.assert_not_called()

    def test_app_normal_start_routes_handoff_fallback_and_bypass(self):
        import app
        for check, handed_off in ((True, True), (True, False), (False, False)):
            with self.subTest(check=check, handed_off=handed_off), \
                    patch.object(app.sys, 'argv', ['app']), \
                    patch.object(app.multiprocessing, 'freeze_support'), \
                    patch.object(app.tk, 'Tk') as tk, \
                    patch.object(app, '_portable_root', return_value=Path('origin')), \
                    patch.object(app, '_runtime_data_root', return_value=Path('data')), \
                    patch.object(app, 'ToneMatchApp') as application, \
                    patch.object(startup, 'should_check_for_updates', return_value=check), \
                    patch.object(startup, 'run_startup_update', return_value=handed_off) as update:
                self.assertEqual(app.main(), 0)
                if check:
                    update.assert_called_once_with(tk.return_value, app.APP_VERSION, Path('origin'), Path('data'))
                else:
                    update.assert_not_called()
                if check and handed_off:
                    application.assert_not_called()
                    tk.return_value.destroy.assert_called_once()
                    tk.return_value.mainloop.assert_not_called()
                else:
                    application.assert_called_once_with(tk.return_value)
                    tk.return_value.mainloop.assert_called_once()

    def test_updated_app_reuses_original_writable_data(self):
        import app
        with tempfile.TemporaryDirectory() as temporary:
            origin = Path(temporary) / 'original'
            data = origin / 'data'
            data.mkdir(parents=True)
            (data / 'settings.json').write_text('{"language":"en"}')
            with patch.object(startup, 'inherited_context', return_value=(origin, data)), \
                    patch.object(app.sys, 'frozen', True, create=True):
                self.assertEqual(app._portable_root(), origin)
                self.assertEqual(app._runtime_data_root(), data)
            self.assertEqual((data / 'settings.json').read_text(), '{"language":"en"}')


if __name__ == '__main__':
    unittest.main()
