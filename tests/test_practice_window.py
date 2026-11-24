"""창·장치 없이 연습 반주 준비와 재생 종료의 소유권을 확인한다."""

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from practice_ui import PracticeWindow, _PracticeSession


def project(bpm=110):
    return SimpleNamespace(bars=(), bpm=bpm, count_in=1, style='Pop', loop=True)


class PracticeSessionTests(TestCase):
    def setUp(self):
        self.rendered = Mock(rate=22050, frames=44100, start_frame=22050)
        self.player = Mock()
        self.player.wait_closed.return_value = True
        self.player.snapshot.return_value = {'state': 'ready', 'output_active': False}
        self.can_play = Mock(return_value=True)
        self.renderer = Mock(return_value=self.rendered)
        self.player_factory = Mock(return_value=self.player)
        self.session = _PracticeSession(self.can_play, render=self.renderer, player=self.player_factory)
        self.addCleanup(self.session.close)

    def finish_job(self):
        self.session._job.thread.join(timeout=2)
        self.assertFalse(self.session._job.thread.is_alive())
        self.session.poll()

    def test_count_in_plays_once_before_loop_and_reuses_render(self):
        self.session.play(project())
        self.finish_job()
        self.player.set_loop.assert_called_once_with(1.0, 2.0, pre_roll=True)
        self.player.play.assert_called_once()
        self.session.play(project())
        self.renderer.assert_called_once()

    def test_cancelled_pending_play_never_starts_a_device(self):
        self.session.play(project())
        self.session._job.thread.join(timeout=2)
        self.assertTrue(self.session.playback_active)
        self.assertTrue(self.session.suspend())
        self.assertFalse(self.session.playback_active)
        self.finish_job()
        self.player_factory.assert_not_called()
        self.rendered.close.assert_called_once()

    def test_audio_arbitration_is_checked_again_after_render(self):
        self.session.play(project())
        self.can_play.return_value = False
        self.finish_job()
        self.player_factory.assert_not_called()
        self.assertEqual(self.session.notice, 'audio_busy')

    def test_close_keeps_rendered_pcm_until_player_releases_it(self):
        self.session.play(project())
        self.finish_job()
        self.player.wait_closed.return_value = False
        self.session.close()
        self.assertFalse(self.session.wait_closed())
        self.rendered.close.assert_not_called()
        self.player.wait_closed.return_value = True
        self.assertTrue(self.session.wait_closed())
        self.rendered.close.assert_called_once()

    def test_export_passes_explicit_mix_and_part_without_player(self):
        mix = self.session.mix
        self.session.export(project(), 'chords.wav', part='chords')
        self.finish_job()
        arguments = self.rendered.export.call_args
        self.assertEqual(arguments.args, ('chords.wav', mix))
        self.assertEqual(arguments.kwargs['part'], 'chords')
        self.player_factory.assert_not_called()

    def test_stop_after_export_commits_still_reports_saved(self):
        self.session.export(project(), 'mix.wav')
        self.session._job.thread.join(timeout=2)
        self.rendered.export.assert_called_once()
        self.session.cancel()
        self.session.poll()
        self.assertEqual(self.session.notice, 'exported')
        self.player_factory.assert_not_called()


class PracticeDraftTests(TestCase):
    def test_cadence_replacement_preserves_draft_on_cancel_and_settings_on_accept(self):
        window = PracticeWindow.__new__(PracticeWindow)
        window.language = 'en'
        window.window = Mock()
        window._session = Mock()
        window._show_project = Mock()
        window.chart = Mock()
        window.chart.compare.return_value = True
        window.tabs, window.chart_tab = Mock(), Mock()
        for name, value in (('cadence_tonic', 'Gb'), ('title', 'Practice'),
                            ('bpm', '144'), ('style', 'Jazz Swing'), ('count_in', '2'), ('loop', False)):
            setattr(window, name, Mock(get=Mock(return_value=value)))
        window.cadence_minor = Mock(get=Mock(return_value=True))
        window.cadence_cycle = Mock(get=Mock(return_value=True))
        with patch('practice_ui.messagebox.askyesno', return_value=False) as confirm:
            window._apply_cadence()
            confirm.assert_called_once()
            window._show_project.assert_not_called()
            window._session.cancel.assert_not_called()
        with patch('practice_ui.messagebox.askyesno', return_value=True):
            window._apply_cadence()
            generated = window._show_project.call_args.args[0]
            self.assertEqual((generated.key, generated.title, generated.bpm, generated.style),
                             ('Gb Minor', 'Practice', 144, 'Jazz Swing'))
            self.assertEqual((len(generated.bars), generated.count_in, generated.loop), (48, 2, False))
        window._session.play.assert_not_called()

    def test_invalid_paste_cannot_replace_the_previous_project_or_preview(self):
        window = PracticeWindow.__new__(PracticeWindow)
        window.project = previous = object()
        window._session = Mock()
        window._show_project = Mock()
        window.chart = Mock()
        window.chart.compare.return_value = False
        window.chart.get.return_value = 'Prose instead of chords'
        window.bpm = Mock()
        window.bpm.get.return_value = '110'
        window.count_in = Mock()
        window.count_in.get.return_value = '1'
        window._preview()
        self.assertIs(window.project, previous)
        window._show_project.assert_not_called()
        self.assertTrue(window._message)

    def test_oversized_draft_is_rejected_before_copying_editor_text(self):
        window = PracticeWindow.__new__(PracticeWindow)
        window.language = 'en'
        window.chart = Mock()
        window.chart.compare.return_value = True
        with self.assertRaisesRegex(ValueError, 'too long'):
            window._read_project()
        window.chart.get.assert_not_called()
