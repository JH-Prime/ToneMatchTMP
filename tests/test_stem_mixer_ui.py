"""별도 믹서 창의 명시적 작업·fader·종료를 숨은 실제 Tk로 검증한다."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock

from test_chord_chart_ui import hidden_chart_application
from test_stem_mixer import fake_decode, fake_separate
from test_playback import wait_for
from i18n import LANGUAGE_LABELS


class StemMixerUiTests(unittest.TestCase):
    def test_mixer_output_excludes_original_transport_but_still_allows_pause(self):
        """출력 해제 전 원본 재생을 막아도 믹서 일시정지 버튼은 동작해야 한다."""
        with tempfile.TemporaryDirectory() as folder, hidden_chart_application(Path(folder)) as (_root, app):
            player = Mock()
            player.snapshot.return_value = {"state": "playing", "output_active": True}
            app.mixer.player = player
            self.assertFalse(app._can_play_audio())
            self.assertTrue(app._can_start_mixer())
            player.stop.assert_not_called()
            app.mixer.player = None

    def test_prepare_controls_export_language_and_close(self):
        """창을 열기만 해서는 추론·재생하지 않으며 준비 후 재사용과 저장이 가능하다."""
        with tempfile.TemporaryDirectory() as folder, hidden_chart_application(Path(folder)) as (root, app):
            source = Path(folder) / "source.mp3"
            source.touch()
            app.stem_source_var.set(str(source))
            with (patch("stem_mixer._decode_input", side_effect=fake_decode),
                  patch("stem_mixer.separate_stem_chunks", side_effect=fake_separate) as inference,
                  patch("playback.default_output") as output):
                view = app._open_mixer()
                view.withdraw()
                inference.assert_not_called()
                output.assert_not_called()
                view.prepare()
                wait_for(lambda: (view.refresh(), app.mixer.bank is not None)[1])
                self.assertEqual(len(view.channels), 6)
                view.channels["guitar"]["gain"].set(.5)
                view.channels["guitar"]["solo"].set(True)
                view.change_mix()
                self.assertEqual(app.mixer.state.controls()[0]["guitar"]["gain"], .5)
                destination = Path(folder) / "guitar.wav"
                with patch("stem_mixer_ui.filedialog.asksaveasfilename", return_value=str(destination)):
                    view.export("guitar")
                wait_for(lambda: (view.refresh(), not app.mixer.busy)[1])
                self.assertTrue(destination.exists())
                self.assertEqual(inference.call_count, 1)
                output.assert_not_called()
                app.language_var.set(LANGUAGE_LABELS["en"])
                app._change_language()
                reopened = app._open_mixer()
                reopened.withdraw()
                self.assertEqual(reopened.channels["guitar"]["gain"].get(), .5)
                self.assertTrue(reopened.channels["guitar"]["solo"].get())
                reopened.close()
                app.mixer.clear()
                wait_for(app.mixer.is_closed)

    def test_busy_mixer_blocks_other_audio_and_closing_is_nonblocking(self):
        """악기 분리 중에는 다른 작업이 장치·모델을 열 수 없다."""
        with tempfile.TemporaryDirectory() as folder, hidden_chart_application(Path(folder)) as (_root, app):
            app.mixer.operation = "prepare"
            self.assertFalse(app._can_play_audio())
            self.assertFalse(app._suspend_playback())
            app.mixer.operation = ""
            self.assertTrue(app._suspend_playback())
