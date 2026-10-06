"""분리 모델 없이 실제 PCM 파일로 믹서의 정렬·레벨·안전 저장을 검증한다."""

from pathlib import Path
import tempfile
import unittest
import wave
import threading
from unittest.mock import patch

import numpy as np
from stem_mixer import StemBank, MixState, MixReader
from separator import SEPARATOR_STEMS


def fake_decode(source, destination, *args):
    """입력 대신 3초 PCM을 만들어 분리 경계 밖을 재현한다."""
    with wave.open(str(destination), "wb") as output:
        output.setparams((2, 2, 44100, 0, "NONE", "not compressed"))
        output.writeframes(np.zeros((132300, 2), dtype="<i2").tobytes())
    return 3.0


def fake_separate(source, stems, consume, *args, **kwargs):
    """서로 다른 고정값의 정렬된 6 stem을 두 조각으로 전달한다."""
    for length in (65536, 66764):
        consume({name: np.full((2, length), (index + 1) * .01, np.float32)
                 for index, name in enumerate(stems)})
    return None


class StemMixerTests(unittest.TestCase):
    def test_separator_cancellation_is_normalized_and_temp_files_cleaned(self):
        """실제 모델의 취소 예외를 UI가 오류로 오인하지 않고 임시 파일도 회수한다."""
        from separator import SeparationCancelled
        from stem_removal import StemRemovalCancelled
        closed = []
        original_close = StemBank.close
        def close(bank):
            """실제 정리 뒤 경로만 남겨 파일 수명을 검사한다."""
            closed.append(bank.directory)
            original_close(bank)
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.mp3"
            source.touch()
            with (patch("stem_mixer._decode_input", side_effect=fake_decode),
                  patch("stem_mixer.separate_stem_chunks", side_effect=SeparationCancelled("cancelled")),
                  patch.object(StemBank, "close", close)):
                with self.assertRaises(StemRemovalCancelled):
                    StemBank.prepare(source)
            self.assertEqual(len(closed), 1)
            self.assertFalse(closed[0].exists())

    def test_session_prepares_once_exports_and_retires_resources(self):
        """비동기 세션은 fader마다 재추론하지 않고 내보내기와 종료를 기다린다."""
        from stem_mixer import MixerSession
        from tests.test_playback import wait_for
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.mp3"
            source.touch()
            session = MixerSession()
            try:
                with (patch("stem_mixer._decode_input", side_effect=fake_decode),
                      patch("stem_mixer.separate_stem_chunks", side_effect=fake_separate) as inference):
                    session.prepare(source)
                    wait_for(lambda: (session.poll(), session.bank is not None)[1])
                    self.assertIsNone(session.player)
                    session.state.update({"guitar": {"solo": True, "gain": .5}})
                    destination = Path(folder) / "mix.wav"
                    session.export(destination)
                    wait_for(lambda: (session.poll(), not session.busy)[1])
                    self.assertTrue(destination.exists())
                    self.assertEqual(inference.call_count, 1)
                    self.assertEqual(session.saved_path, destination)
                    directory = session.bank.directory
                session.clear()
                wait_for(session.is_closed)
                self.assertFalse(directory.exists())
            finally:
                session.clear()
                wait_for(session.is_closed)

    def test_session_cancelled_late_preparation_cannot_replace_state(self):
        """취소 후 도착한 모델 결과는 표시하거나 재생하지 않고 회수한다."""
        from stem_mixer import MixerSession
        from tests.test_playback import wait_for
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.mp3"
            source.touch()
            bank = self.prepare(source)
            entered, finish = threading.Event(), threading.Event()
            def slow(*args, **kwargs):
                entered.set()
                if not finish.wait(2):
                    raise TimeoutError("test preparation blocked")
                return bank
            session = MixerSession()
            try:
                with patch("stem_mixer.StemBank.prepare", side_effect=slow):
                    session.prepare(source)
                    self.assertTrue(entered.wait(2))
                    session.clear()
                    finish.set()
                    wait_for(session.is_closed)
                self.assertIsNone(session.bank)
                self.assertFalse(bank.directory.exists())
            finally:
                finish.set()
                session.clear()
                wait_for(session.is_closed)

    def test_player_uses_mixer_pcm_without_an_extra_wav(self):
        """실제 재생 작업자가 믹서 reader를 소비하고 명시적 요청 전 출력하지 않는다."""
        from playback import WavPlayer
        from tests.test_playback import SilentOutput, wait_for
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.mp3"
            source.touch()
            bank = self.prepare(source)
            player = None
            try:
                state = MixState()
                state.update({"guitar": {"solo": True}})
                output = SilentOutput()
                player = WavPlayer(bank.original_path, source_factory=lambda: MixReader(bank, state),
                                   output_factory=lambda **kwargs: output)
                self.assertFalse(output.blocks)
                player.play()
                wait_for(lambda: player.snapshot()["state"] == "finished")
                pcm = np.concatenate(output.blocks)
                self.assertEqual(len(pcm), bank.frames)
                expected = (SEPARATOR_STEMS.index("guitar") + 1) * .01
                self.assertAlmostEqual(float(pcm[0, 0]), expected, places=3)
            finally:
                if player:
                    player.close()
                    self.assertTrue(player.wait_closed(2))
                bank.close()

    def prepare(self, source):
        """모델 실행만 대체하고 임시 파일·믹싱·내보내기는 실제 구현을 쓴다."""
        with (patch("stem_mixer._decode_input", side_effect=fake_decode),
              patch("stem_mixer.separate_stem_chunks", side_effect=fake_separate)):
            return StemBank.prepare(source)

    def test_gain_mute_solo_and_reader_reuse(self):
        """분리 한 번 이후 상태 변경만으로 같은 파일의 믹스를 바꾼다."""
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.mp3"
            source.touch()
            bank = self.prepare(source)
            try:
                state = MixState()
                with MixReader(bank, state) as reader:
                    baseline = np.frombuffer(reader.readframes(10), "<i2") / 32768
                    self.assertAlmostEqual(baseline[0], .21, places=3)
                    state.update({SEPARATOR_STEMS[0]: {"gain": .5, "solo": True}})
                    reader.setpos(0)
                    self.assertAlmostEqual(np.frombuffer(reader.readframes(10), "<i2")[0] / 32768, .005, places=3)
                    state.update({SEPARATOR_STEMS[0]: {"gain": .5, "solo": True, "mute": True}})
                    reader.setpos(0)
                    self.assertFalse(np.frombuffer(reader.readframes(10), "<i2").any())
            finally:
                directory = bank.directory
                bank.close()
            self.assertFalse(directory.exists())

    def test_export_is_aligned_and_does_not_overwrite(self):
        """개별·믹스 WAV 길이와 기존 파일·원본 보호를 확인한다."""
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.mp3"
            source.touch()
            bank = self.prepare(source)
            try:
                destination = Path(folder) / "guitar.wav"
                bank.export(destination, MixState(), stem="guitar")
                with wave.open(str(destination)) as audio:
                    self.assertEqual(audio.getnframes(), bank.frames)
                    self.assertEqual(audio.getframerate(), 44100)
                before = destination.read_bytes()
                with self.assertRaises(Exception):
                    bank.export(destination, MixState())
                self.assertEqual(destination.read_bytes(), before)
                with self.assertRaises(Exception):
                    bank.export(Path(folder) / "cancel.wav", MixState(), cancel_requested=lambda: True)
                self.assertFalse((Path(folder) / "cancel.wav").exists())
            finally:
                bank.close()

    def test_invalid_levels_and_stem_alignment_are_rejected(self):
        """범위를 벗어난 gain과 모델의 누락·길이 불일치는 즉시 거절한다."""
        state = MixState()
        for update in ({"guitar": {"gain": float("nan")}}, {"guitar": {"gain": 3}}, {"bad": {}}):
            with self.assertRaises(ValueError):
                state.update(update)
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.mp3"
            source.touch()
            def invalid(source, stems, consume, *args):
                """정렬되지 않은 모델 결과를 재현한다."""
                data = {name: np.zeros((2, 30), np.float32) for name in stems}
                data[stems[0]] = np.zeros((2, 31), np.float32)
                consume(data)
            with (patch("stem_mixer._decode_input", side_effect=fake_decode),
                  patch("stem_mixer.separate_stem_chunks", side_effect=invalid)):
                with self.assertRaises(ValueError):
                    StemBank.prepare(source)
