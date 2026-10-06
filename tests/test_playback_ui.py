"""실제 숨은 Tk 코드표와 무음 재생 컨트롤의 연결을 검증한다."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_chord_chart_ui import hidden_chart_application, chart_result, chart_text


class PlaybackUiTests(unittest.TestCase):
    """원본 오프셋과 마디 선택·페이지 따라가기·작업 배제를 확인한다."""

    def test_analysis_does_not_autoplay_and_bar_seek_is_relative(self):
        """30초 원본 오프셋이 있어도 선택 마디의 구간 상대 시각으로 탐색한다."""
        with tempfile.TemporaryDirectory() as folder, hidden_chart_application(Path(folder)) as (root, app):
            app._analysis_source_path = str(Path(folder) / 'private.mp3')
            with patch('playback.default_output') as output:
                app._show_result(chart_result())
                root.update_idletasks()
                output.assert_not_called()
            self.assertEqual(app.playback.source[1:], (30.0, 105.0))
            bar = app.chart_data['pages'][0]['bars'][2]
            app._select_chart_bar(bar)
            self.assertEqual(app.playback.position, 4.0)
            self.assertEqual(app.selected_chart_bar['number'], 3)
            self.assertTrue(app.chart_canvas.find_withtag('selected_bar'))
            self.assertEqual(app.voicing_views.select(), str(app.chart_tab))
            app.playback_controls.loop_var.set(True)
            app.playback_controls.change_loop()
            self.assertEqual(app.playback.loop, (4.0, 6.0))
            app.playback.clear()

    def test_following_playhead_changes_page_without_losing_labels(self):
        """재생 마디가 다음 페이지로 넘어가도 모든 코드와 근거를 유지한다."""
        with tempfile.TemporaryDirectory() as folder, hidden_chart_application(Path(folder)) as (_root, app):
            app._show_result(chart_result())
            app._follow_playback(35.0, True)
            self.assertEqual(app.chart_page_index, 1)
            self.assertTrue(app.chart_canvas.find_withtag('playing_bar'))
            count = sum(len(bar['segments']) for bar in app.chart_data['pages'][1]['bars'])
            self.assertEqual(len(chart_text(app, 'chord_label')), count)
            app._follow_playback(1.0, False)
            self.assertEqual(app.chart_page_index, 1)

    def test_missing_source_controls_and_work_exclusion(self):
        """원본 연결이 없으면 재생은 비활성화하고 다른 작업 중에는 시작하지 않는다."""
        with tempfile.TemporaryDirectory() as folder, hidden_chart_application(Path(folder)) as (_root, app):
            app._show_result(chart_result())
            app.playback_controls.refresh()
            self.assertEqual(str(app.playback_controls.play_button.cget('state')), 'disabled')
            app.hardware_probe_active = True
            self.assertFalse(app._can_play_audio())
            app.hardware_probe_active = False
            self.assertTrue(app._can_play_audio())

    def test_grid_edit_clears_obsolete_loop_and_selection(self):
        """마디 격자를 바꾸면 예전 마디 시간으로 반복하지 않는다."""
        with tempfile.TemporaryDirectory() as folder, hidden_chart_application(Path(folder)) as (_root, app):
            app._show_result(chart_result())
            app._select_chart_bar(app.chart_data['pages'][0]['bars'][2])
            app.playback_controls.loop_var.set(True)
            app.playback_controls.change_loop()
            app.chart_bpm_var.set('90')
            app._apply_chart_settings()
            self.assertIsNone(app.playback.loop)
            self.assertIsNone(app.selected_chart_bar)

    def test_connected_transport_retains_chart_height_with_expanded_settings(self):
        """원본이 연결된 최소 창·150% 배율에서도 설정과 악보 공간을 유지한다."""
        with tempfile.TemporaryDirectory() as folder, hidden_chart_application(Path(folder), scaling=2.0) as (root, app):
            app._analysis_source_path = str(Path(folder) / 'song.wav')
            app._show_result(chart_result())
            app.notebook.select(app.voicing_tab)
            root.update()
            self.assertGreaterEqual(app.chart_canvas.winfo_height(), 80)
            app._toggle_chart_settings()
            root.update()
            self.assertGreaterEqual(app.chart_canvas.winfo_height(), 80)
            self.assertFalse(app.playback_controls.grid_info())
            app._toggle_chart_settings()
            root.update()
            self.assertTrue(app.playback_controls.grid_info())
            app.playback.clear()


if __name__ == '__main__':
    unittest.main()
