"""Real completion/availability handlers with no Tk windows or audio devices."""
import queue
from pathlib import Path
import types
import unittest
from unittest.mock import Mock, patch

from app import ToneMatchApp
from devices import device_label
from engine import AnalysisError
from i18n import tr


class Value:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class Control(dict):
    def configure(self, **options):
        self.update(options)


def application(chords_only=False):
    # Only rendering, scheduling, persistence and audio boundaries are mocked.
    view = Mock()
    for name in ('_drain_events', '_show_result', '_show_error',
                 '_recording_completed', '_recording_failed', '_toggle_recording',
                 '_update_analysis_availability', '_change_device'):
        setattr(view, name, types.MethodType(getattr(ToneMatchApp, name), view))
    view.closing = False
    view.events = queue.Queue()
    view.language = 'ko'
    view.device_id = 'tone_master_pro'
    view.device_var = Value(device_label(view.device_id, view.language))
    view.chords_only_var = Value(chords_only)
    view.chord_method_var = Value('CQT')
    view.file_var = Value('local-test.wav')
    view.start_var = Value('10')
    view.end_var = Value('20')
    view.status_var = Value('')
    view.device_description_var = Value('')
    view.recipe_texts = []
    view.purpose_buttons = [Control(), Control()]
    view.worker = None
    view.record_worker = None
    view.hardware_probe_active = False
    view._stem_is_running.return_value = False
    view._spectrum_is_running.return_value = False
    for name in ('device_combo', 'pickup_combo', 'mix_combo', 'output_combo',
                 'compute_combo', 'analyze_button', 'language_combo',
                 'chord_method_combo', 'qc_firmware_combo', 'cancel_button', 'record_button'):
        setattr(view, name, Control())
    return view


def chord_result():
    return {'features': {}, 'recipes': [], 'analysis_kind': 'chords',
            'model_guide': 'CQT', 'chord_voicing': {'events': []}, 'source': {}}


class DeviceLifecycleTests(unittest.TestCase):
    def test_recording_restart_waits_for_pending_terminal_event(self):
        for kind in ('record_done', 'record_error'):
            with self.subTest(event=kind), patch('app.messagebox.showerror'), \
                    patch('pathlib.Path.mkdir'), patch('app.threading.Thread') as create_thread:
                view = application(True)
                old_worker = Mock()
                old_worker.is_alive.return_value = True
                view.record_worker = old_worker
                view._update_analysis_availability()
                old_worker.is_alive.return_value = False
                view._suspend_playback.return_value = True
                view.capture_device_id = 'fake-capture-device'
                view.record_limit_var = Value('3')
                view.data_root = Path('not-created')
                view.temporary_recordings = set()
                next_worker = create_thread.return_value
                next_worker.is_alive.return_value = True
                event = ((kind, Path('previous.wav'), 3.0) if kind == 'record_done'
                         else (kind, ValueError('recording failed'), 'test detail'))
                view.events.put(event)

                # The thread exited, but its terminal event still owns this job.
                view._toggle_recording()
                create_thread.assert_not_called()
                self.assertIs(view.record_worker, old_worker)
                self.assertEqual(view.device_combo['state'], 'disabled')
                view._drain_events()
                self.assertIsNone(view.record_worker)

                view._toggle_recording()
                create_thread.assert_called_once()
                next_worker.start.assert_called_once_with()
                view._drain_events()
                self.assertIs(view.record_worker, next_worker)
                self.assertEqual(view.device_combo['state'], 'disabled')
                self.assertEqual(view.analyze_button['state'], 'disabled')
                # Stop still targets the newly tracked active job.
                view._toggle_recording()
                view.record_stop_event.set.assert_called_once_with()
                self.assertIs(view.record_worker, next_worker)
                create_thread.assert_called_once()

    def test_recording_terminal_events_unlock_before_thread_returns(self):
        for only in (False, True):
            for kind in ('record_done', 'record_error'):
                with self.subTest(chords_only=only, event=kind), patch('app.messagebox.showerror') as dialog:
                    view = application(only)
                    worker = Mock()
                    worker.is_alive.return_value = True
                    view.record_worker = worker
                    view._update_analysis_availability()
                    self.assertEqual(view.device_combo['state'], 'disabled')
                    event = ((kind, Path('recorded.wav'), 3.0) if kind == 'record_done'
                             else (kind, ValueError('recording failed'), 'test detail'))
                    view.events.put(event)
                    view._drain_events()
                    self.assertIsNone(view.record_worker)
                    for finished in (False, True):
                        worker.is_alive.return_value = not finished
                        view._drain_events()
                        self.assertEqual(view.device_combo['state'], 'readonly')
                        self.assertEqual(view.analyze_button['state'], 'normal')
                        self.assertEqual(view.language_combo['state'], 'readonly')
                        self.assertEqual(view.record_button['state'], 'normal')
                    if kind == 'record_done':
                        self.assertEqual(view.file_var.get(), 'recorded.wav')
                        self.assertEqual((view.start_var.get(), view.end_var.get()), ('0', '0'))
                    else:
                        self.assertEqual(view.file_var.get(), 'local-test.wav')
                    self.assertEqual(dialog.call_count, int(kind == 'record_error'))

    def test_other_busy_operations_stay_locked_after_recording_completion(self):
        for kind in ('record_done', 'record_error'):
            for activity in ('analysis', 'stem', 'spectrum', 'hardware'):
                with self.subTest(event=kind, activity=activity), patch('app.messagebox.showerror'):
                    view = application(True)
                    view.record_worker = Mock()
                    view.record_worker.is_alive.return_value = True
                    if activity == 'analysis':
                        view.worker = Mock()
                        view.worker.is_alive.return_value = True
                    elif activity == 'hardware':
                        view.hardware_probe_active = True
                    else:
                        getattr(view, '_' + activity + '_is_running').return_value = True
                    event = ((kind, Path('recorded.wav'), 3.0) if kind == 'record_done'
                             else (kind, ValueError('recording failed'), 'test detail'))
                    view.events.put(event)
                    view._drain_events()
                    self.assertIsNone(view.record_worker)
                    self.assertEqual(view.device_combo['state'], 'disabled')
                    self.assertEqual(view.analyze_button['state'], 'disabled')
                    self.assertEqual(view.language_combo['state'], 'disabled')

    def test_empty_queue_does_not_unlock_active_recording(self):
        view = application(True)
        view.record_worker = Mock()
        view.record_worker.is_alive.return_value = True
        view._update_analysis_availability()
        view._drain_events()
        self.assertEqual(view.device_combo['state'], 'disabled')
        self.assertEqual(view.analyze_button['state'], 'disabled')
        self.assertEqual(view.language_combo['state'], 'disabled')

    def test_done_unlocks_even_before_worker_thread_returns(self):
        for only in (False, True):
            with self.subTest(chords_only=only):
                view = application(only)
                worker = Mock()
                worker.is_alive.return_value = True
                view.worker = worker
                view._update_analysis_availability()
                self.assertEqual(view.device_combo['state'], 'disabled')
                view.events.put(('done', chord_result()))
                view._drain_events()
                self.assertEqual(view.device_combo['state'], 'readonly')
                self.assertEqual(view.analyze_button['state'], 'normal')
                self.assertIsNone(view.worker)
                # An empty poll after thread return must not leave a sticky lock.
                worker.is_alive.return_value = False
                view._drain_events()
                self.assertEqual(view.device_combo['state'], 'readonly')

    def test_failure_and_cancellation_unlock_without_waiting_for_thread_exit(self):
        for only in (False, True):
            for error in (AnalysisError('invalid audio'), AnalysisError('cancelled')):
                with self.subTest(chords_only=only, error=str(error)), patch('app.messagebox.showerror') as dialog:
                    view = application(only)
                    view.worker = Mock()
                    view.worker.is_alive.return_value = True
                    view.events.put(('error', error, 'test detail'))
                    view._drain_events()
                    self.assertEqual(view.device_combo['state'], 'readonly')
                    self.assertEqual(view.analyze_button['state'], 'normal')
                    self.assertEqual(view.cancel_button['state'], 'disabled')
                    self.assertIsNone(view.worker)
                    self.assertEqual(dialog.call_count, int(str(error) != 'cancelled'))

    def test_idle_chord_mode_allows_device_selection_but_not_tone_controls(self):
        view = application(True)
        view._update_analysis_availability()
        self.assertEqual(view.device_combo['state'], 'readonly')
        for widget in (view.pickup_combo, view.mix_combo, view.output_combo, view.compute_combo):
            self.assertEqual(widget['state'], 'disabled')
        self.assertEqual(view.analyze_button['state'], 'normal')

    def test_device_choice_preserves_chord_mode_and_existing_result(self):
        for device in ('quad_cortex', 'line6_helix'):
            with self.subTest(device=device):
                view = application(True)
                previous_result = {'device_id': 'tone_master_pro'}
                view.result = previous_result
                view.device_var.set(device_label(device, 'ko'))
                view._change_device()
                self.assertEqual(view.device_id, device)
                self.assertTrue(view.chords_only_var.get())
                self.assertIs(view.result, previous_result)
                self.assertEqual(view.status_var.get(), tr('status.ready', 'ko'))
                self.assertEqual(view.analyze_button['state'], 'normal')
                self.assertIn('CQT', view.device_description_var.get())

    def test_unsupported_device_still_disables_tone_analysis(self):
        view = application(False)
        view.device_var.set(device_label('line6_helix', 'ko'))
        view._change_device()
        self.assertEqual(view.analyze_button['state'], 'disabled')
        self.assertEqual(view.device_combo['state'], 'readonly')
        self.assertEqual(view.status_var.get(), tr('status.unsupported_device', 'ko'))

    def test_other_busy_operations_still_lock_device_after_analysis_completion(self):
        for activity in ('record', 'stem', 'spectrum', 'hardware'):
            with self.subTest(activity=activity):
                view = application(True)
                view.worker = Mock()
                view.worker.is_alive.return_value = True
                if activity == 'record':
                    view.record_worker = Mock()
                    view.record_worker.is_alive.return_value = True
                elif activity == 'hardware':
                    view.hardware_probe_active = True
                else:
                    getattr(view, '_' + activity + '_is_running').return_value = True
                view.events.put(('done', chord_result()))
                view._drain_events()
                self.assertEqual(view.device_combo['state'], 'disabled')
                self.assertEqual(view.analyze_button['state'], 'disabled')

    def test_result_refresh_does_not_retire_an_active_analysis(self):
        view = application(True)
        worker = Mock()
        worker.is_alive.return_value = True
        view.worker = worker
        view._show_result(chord_result(), reset_notebook=False)
        self.assertIs(view.worker, worker)
        self.assertEqual(view.device_combo['state'], 'disabled')

    def test_empty_queue_does_not_unlock_active_analysis(self):
        view = application(True)
        view.worker = Mock()
        view.worker.is_alive.return_value = True
        view._update_analysis_availability()
        view._drain_events()
        self.assertEqual(view.device_combo['state'], 'disabled')
        self.assertEqual(view.analyze_button['state'], 'disabled')


if __name__ == '__main__':
    unittest.main()
