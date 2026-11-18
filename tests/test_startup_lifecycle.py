"""Startup transitions with an inert event loop, no GUI, network or processes."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import update_startup as startup


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now


class FakeRoot:
    def __init__(self, clock):
        self.clock = clock
        self.pending = {}
        self.retained = {}
        self.external = set()
        self.sequence = 0
        self.close_handler = 'existing-close-command'
        self.quit_count = 0
        self.on_enter = lambda: None

    def after(self, milliseconds, callback, *arguments):
        self.sequence += 1
        identifier = f'after-{self.sequence}'
        invocation = lambda: callback(*arguments)
        self.pending[identifier] = (self.clock.now + milliseconds / 1000, self.sequence, invocation)
        self.retained[identifier] = invocation
        return identifier

    def external_after(self, milliseconds, callback):
        identifier = self.after(milliseconds, callback)
        self.external.add(identifier)
        return identifier

    def after_cancel(self, identifier):
        self.pending.pop(identifier, None)

    def protocol(self, name, callback=None):
        assert name == 'WM_DELETE_WINDOW'
        if callback is None:
            return self.close_handler
        self.close_handler = callback

    def quit(self):
        self.quit_count += 1

    def mainloop(self):
        self.on_enter()
        for _ in range(300):
            if self.quit_count:
                return
            if not self.pending:
                raise AssertionError('Startup did not finish and left no scheduled work')
            identifier = min(self.pending, key=lambda item: self.pending[item][:2])
            due, _, callback = self.pending.pop(identifier)
            self.clock.now = max(self.clock.now, due)
            callback()
        raise AssertionError('Startup event loop did not finish within 300 callbacks')


class FakeView:
    def __init__(self):
        self.button = Mock()
        self.command = None
        self.button.configure.side_effect = self.configure_button
        self.progress_calls = []
        self.destroy_count = 0

    def configure_button(self, **options):
        if 'command' in options:
            self.command = options['command']

    def progress(self, *arguments):
        if self.destroy_count:
            raise AssertionError('Progress touched a destroyed startup view')
        self.progress_calls.append(arguments)

    def destroy(self):
        self.destroy_count += 1


class StartupLifecycleTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.clock = FakeClock()
        self.root = FakeRoot(self.clock)
        self.view = FakeView()
        self.controllers = []
        self.worker_started_at = []
        self.real_controller = startup.StartupController
        self.real_check = startup.should_check_for_updates
        self.replace('tkinter.Tk', side_effect=AssertionError('Native UI forbidden'))
        self.replace('tkinter.Toplevel', side_effect=AssertionError('Native UI forbidden'))
        self.replace('update_startup.time', self.clock, create=True)
        self.view_factory = self.replace('update_startup._StartupView', return_value=self.view)
        self.check = self.replace('update_startup.should_check_for_updates', return_value=False)
        self.controller_factory = self.replace('update_startup.StartupController',
                                               side_effect=AssertionError('Updater forbidden'))

    def replace(self, target, *arguments, **keywords):
        replacement = patch(target, *arguments, **keywords)
        self.addCleanup(replacement.stop)
        return replacement.start()

    def enable_update(self, *, target=None, delay_ms=0, error=None, launch=None):
        self.check.return_value = True
        self.prepare = Mock(return_value=target, side_effect=error)
        self.launch = launch if launch is not None else Mock()

        def controller(*arguments, **keywords):
            instance = self.real_controller(*arguments, **keywords,
                                            prepare=self.prepare, launch=self.launch)
            self.controllers.append(instance)
            return instance

        self.controller_factory.side_effect = controller
        root, started = self.root, self.worker_started_at

        class ScheduledWorker:
            def __init__(self, target, **_keywords):
                self.target = target

            def start(self):
                started.append(root.clock.now)
                root.external_after(delay_ms, self.target)

        self.replace('update_startup.threading.Thread', ScheduledWorker)

    def run_startup(self):
        return startup.run_startup(self.root, '0.1.10', self.directory, self.directory)

    def assert_clean(self):
        self.assertEqual(self.root.close_handler, 'existing-close-command')
        self.assertEqual(self.view.destroy_count, 1)
        self.assertFalse(set(self.root.pending) - self.root.external)

    def test_animation_only_waits_briefly_without_constructing_updater(self):
        self.assertFalse(self.run_startup())
        self.assertGreaterEqual(self.clock.now, 0.65)
        self.assertLessEqual(self.clock.now, 0.8)
        self.view_factory.assert_called_once_with(self.root, 'ko', '0.1.10')
        self.controller_factory.assert_not_called()
        self.assert_clean()

    def test_expired_intro_still_finishes_after_event_loop_starts(self):
        def delayed_policy():
            self.clock.now = 0.8
            return False
        self.check.side_effect = delayed_policy
        # Tk resets an earlier quit flag on entry to its main loop.
        self.root.on_enter = lambda: setattr(self.root, 'quit_count', 0)
        self.assertFalse(self.run_startup())
        self.assertAlmostEqual(self.clock.now, 0.8)
        self.assertEqual(self.root.quit_count, 1)
        self.assert_clean()

    def test_actual_bypass_policies_never_construct_an_update_worker(self):
        self.check.side_effect = self.real_check
        for status, arguments in (('packaged', []), ('unknown', []),
                                  ('unpackaged', ['--skip-update'])):
            with self.subTest(status=status, arguments=arguments), \
                    patch.object(startup.sys, 'frozen', True, create=True), \
                    patch.object(startup.sys, 'platform', 'win32'), \
                    patch.object(startup.sys, 'argv', ['app', *arguments]), \
                    patch.object(startup, 'package_identity', return_value=Mock(status=status)):
                self.clock.now = 0
                self.root = FakeRoot(self.clock)
                self.view = FakeView()
                self.view_factory.return_value = self.view
                self.assertTrue(startup.should_show_startup())
                self.assertFalse(self.run_startup())
                self.controller_factory.assert_not_called()
                self.assert_clean()

    def test_current_result_overlaps_intro_instead_of_adding_another_delay(self):
        self.enable_update(delay_ms=400)
        self.assertFalse(self.run_startup())
        self.assertEqual(self.worker_started_at, [0.0])
        self.assertGreaterEqual(self.clock.now, 0.65)
        self.assertLessEqual(self.clock.now, 0.8)
        self.launch.assert_not_called()
        self.assertTrue(self.controllers[0].cancel_event.is_set())
        self.assert_clean()

    def test_slow_update_result_does_not_add_an_intro_after_completion(self):
        self.enable_update(delay_ms=1000)
        self.assertFalse(self.run_startup())
        self.assertGreaterEqual(self.clock.now, 1.0)
        self.assertLessEqual(self.clock.now, 1.1)
        self.assert_clean()

    def test_successful_handoff_finishes_before_intro_deadline(self):
        executable = self.directory / 'new.exe'
        self.enable_update(target=executable, delay_ms=100)
        self.assertTrue(self.run_startup())
        self.assertLess(self.clock.now, 0.3)
        self.launch.assert_called_once_with(executable, self.directory, self.directory)
        self.assert_clean()

    def test_offline_and_failed_launch_fall_back_after_only_the_remaining_intro(self):
        self.enable_update(error=OSError('offline'), delay_ms=100)
        self.assertFalse(self.run_startup())
        self.assertIn(('unavailable', 0, 0), self.view.progress_calls)
        self.assertLessEqual(self.clock.now, 0.8)
        self.assert_clean()

    def test_failed_handoff_keeps_the_current_application(self):
        self.enable_update(target=self.directory / 'new.exe', delay_ms=100,
                           launch=Mock(side_effect=OSError('denied')))
        self.assertFalse(self.run_startup())
        self.assertIn(('unavailable', 0, 0), self.view.progress_calls)
        self.assertLessEqual(self.clock.now, 0.8)
        self.assert_clean()

    def test_continue_during_animation_only_is_immediate(self):
        self.root.external_after(100, lambda: self.view.command())
        self.assertFalse(self.run_startup())
        self.assertAlmostEqual(self.clock.now, 0.1)
        self.assert_clean()

    def test_close_during_animation_only_exits_immediately(self):
        self.root.external_after(100, lambda: self.root.close_handler())
        self.assertTrue(self.run_startup())
        self.assertAlmostEqual(self.clock.now, 0.1)
        self.assert_clean()

    def test_close_after_update_has_finished_still_exits_during_intro(self):
        self.enable_update()
        self.root.external_after(200, lambda: self.root.close_handler())
        self.assertTrue(self.run_startup())
        self.assertAlmostEqual(self.clock.now, 0.2)
        self.launch.assert_not_called()
        self.assert_clean()

    def test_continue_after_update_has_finished_skips_remaining_intro(self):
        self.enable_update()
        self.root.external_after(200, lambda: self.view.command())
        self.assertFalse(self.run_startup())
        self.assertAlmostEqual(self.clock.now, 0.2)
        self.assert_clean()

    def test_cancelled_worker_and_late_callbacks_cannot_launch_or_touch_destroyed_view(self):
        self.enable_update(target=self.directory / 'new.exe', delay_ms=500)
        self.root.external_after(100, lambda: self.view.command())
        self.assertFalse(self.run_startup())
        self.assertAlmostEqual(self.clock.now, 0.1)
        self.assertTrue(self.controllers[0].cancel_event.is_set())
        self.assert_clean()
        retained = tuple(self.root.retained.items())
        for identifier, callback in retained:
            if identifier in self.root.external:
                callback()
        for identifier, callback in retained:
            if identifier not in self.root.external:
                callback()
        self.launch.assert_not_called()
        self.assertEqual(self.root.quit_count, 1)
        self.assert_clean()

    def test_event_loop_failure_restores_handler_and_cancels_owned_timers(self):
        self.enable_update(delay_ms=500)

        def fail():
            raise RuntimeError('event loop failed')

        self.root.on_enter = fail
        with self.assertRaisesRegex(RuntimeError, 'event loop failed'):
            self.run_startup()
        self.assertTrue(self.controllers[0].cancel_event.is_set())
        self.assert_clean()

    def test_cleanup_preserves_unrelated_scheduled_work(self):
        unrelated = self.root.external_after(10000, lambda: None)
        self.assertFalse(self.run_startup())
        self.assertIn(unrelated, self.root.pending)
        self.assert_clean()

    def test_saved_english_setting_reaches_view(self):
        (self.directory / 'settings.json').write_text('{"language":"en"}', encoding='utf-8')
        self.assertFalse(self.run_startup())
        self.view_factory.assert_called_once_with(self.root, 'en', '0.1.10')
        self.assert_clean()

    def test_malformed_settings_do_not_prevent_startup(self):
        (self.directory / 'settings.json').write_text('{broken', encoding='utf-8')
        self.assertFalse(self.run_startup())
        self.view_factory.assert_called_once_with(self.root, 'ko', '0.1.10')
        self.assert_clean()


if __name__ == '__main__':
    unittest.main()
