"""실제 소리를 내지 않고 재생 범위·반복·중단과 PCM 읽기를 검증한다."""

from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
import wave
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playback import Transport, read_pcm_block, PreparedAudio, WavPlayer, PlaybackSession


def write_test_wav(path, frames=400, rate=100):
    """재생 경계를 구별할 수 있는 작은 stereo PCM을 만든다."""
    samples = np.column_stack((np.arange(frames) % 200, -(np.arange(frames) % 200))).astype('<i2')
    with wave.open(str(path), 'wb') as target:
        target.setparams((2, 2, rate, 0, 'NONE', 'not compressed'))
        target.writeframes(samples.tobytes())
    return samples


def wait_for(predicate):
    """시간 제한 안에서 작업자 상태 전이를 기다려 멈춤을 검출한다."""
    deadline = time.monotonic() + 2
    while not predicate() and time.monotonic() < deadline:
        threading.Event().wait(0.005)
    if not predicate():
        raise AssertionError('Playback did not reach expected state')


class SilentOutput:
    """장치 대신 PCM과 drain/abort 경계를 기록하는 무음 출력이다."""

    def __init__(self, gate=None, **kwargs):
        """선택적으로 첫 쓰기를 고정해 동시 명령을 재현한다."""
        self.gate = gate
        self.entered = threading.Event()
        self.blocks = []
        self.drained = False
        self.aborted = False
        self.closed = False

    def start(self):
        """가짜 장치는 별도 준비가 필요 없다."""

    def write(self, block):
        """실제 전달 PCM을 복사하고 테스트 요청에 따라 잠깐 기다린다."""
        self.blocks.append(block.copy())
        self.entered.set()
        if self.gate and not self.gate.wait(2):
            raise TimeoutError('Test gate timed out')

    def stop(self):
        """곡 끝의 대기 오디오가 보존되었음을 기록한다."""
        self.drained = True

    def abort(self):
        """탐색/중단 시 대기 오디오 폐기를 기록한다."""
        self.aborted = True

    def close(self):
        """출력 자원이 해제되었음을 기록한다."""
        self.closed = True


class PlayerTests(unittest.TestCase):
    """파일 기반 출력의 중단·재시작·장치 오류와 자원 수명을 검증한다."""

    def test_explicit_play_drains_exact_pcm_at_eof(self):
        """명령 전 장치는 열지 않고 마지막 짧은 블록도 정확히 전달한다."""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'audio.wav'
            samples = write_test_wav(path)
            output = SilentOutput()
            with patch('playback.default_output', return_value=output) as factory:
                player = WavPlayer(path, block_frames=128)
                self.addCleanup(player.close)
                factory.assert_not_called()
                player.play()
                wait_for(lambda: player.snapshot()['state'] == 'finished')
                np.testing.assert_array_equal(np.concatenate(output.blocks), samples.astype(np.float32) / 32768)
                self.assertTrue(output.drained)
                self.assertTrue(output.closed)
                player.close()
                self.assertTrue(player.wait_closed(2))

    def test_stop_during_write_cannot_advance_or_restart(self):
        """멈춘 뒤 도착한 이전 쓰기 완료가 새 위치를 오염시키지 않는다."""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'audio.wav'
            write_test_wav(path)
            gate = threading.Event()
            output = SilentOutput(gate)
            player = WavPlayer(path, output_factory=lambda **kwargs: output, block_frames=128)
            self.addCleanup(player.close)
            player.play()
            self.assertTrue(output.entered.wait(2))
            player.stop()
            gate.set()
            wait_for(lambda: not player.snapshot()['output_active'])
            self.assertEqual(player.snapshot()['position'], 0)
            self.assertEqual(player.snapshot()['state'], 'ready')
            self.assertEqual(len(output.blocks), 1)
            self.assertTrue(output.aborted)
            player.close()
            self.assertTrue(player.wait_closed(2))

    def test_seek_during_write_discards_stale_position(self):
        """탐색 전 블록 완료가 도착해도 새 위치의 PCM부터 재생한다."""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'audio.wav'
            samples = write_test_wav(path)
            gate = threading.Event()
            first, second = SilentOutput(gate), SilentOutput()
            outputs = iter((first, second))
            player = WavPlayer(path, output_factory=lambda **kwargs: next(outputs), block_frames=128)
            self.addCleanup(player.close)
            player.play()
            self.assertTrue(first.entered.wait(2))
            player.seek(3)
            gate.set()
            wait_for(lambda: player.snapshot()['state'] == 'finished')
            np.testing.assert_array_equal(np.concatenate(second.blocks), samples[300:].astype(np.float32) / 32768)
            self.assertTrue(first.aborted)
            player.close()
            self.assertTrue(player.wait_closed(2))

    def test_device_failure_is_visible_and_retry_is_explicit(self):
        """장치 실패는 오류 상태로 노출하며 자동 재생 재시도하지 않는다."""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'audio.wav'
            write_test_wav(path)
            with patch('playback.default_output', side_effect=RuntimeError('No output device')) as factory:
                player = WavPlayer(path)
                self.addCleanup(player.close)
                player.play()
                wait_for(lambda: player.snapshot()['state'] == 'error')
                self.assertIn('No output device', player.snapshot()['error'])
                self.assertEqual(factory.call_count, 1)
                player.close()
                self.assertTrue(player.wait_closed(2))

    def test_preparation_decodes_range_and_owns_only_temporary_output(self):
        """실제 FFmpeg 구간 변환과 임시 PCM 정리를 확인한다."""
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'source.wav'
            write_test_wav(source, frames=220500, rate=44100)
            original = source.read_bytes()
            prepared = PreparedAudio.decode(source, 1, 4)
            with wave.open(str(prepared.path), 'rb') as pcm:
                self.assertEqual(pcm.getnframes(), 132300)
            prepared.close()
            self.assertFalse(prepared.path.exists())
            self.assertEqual(source.read_bytes(), original)

    def test_cancelled_preparation_has_no_owned_output(self):
        """준비 시작 전에 취소되면 원본만 남는다."""
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'source.wav'
            write_test_wav(source)
            with self.assertRaises(RuntimeError):
                PreparedAudio.decode(source, 0, 4, cancel_requested=lambda: True)
            self.assertEqual(list(Path(folder).iterdir()), [source])

    def test_stale_preparation_is_cleaned_without_playing(self):
        """이전 파일의 늦은 준비 결과는 채택하거나 소리 내지 않는다."""
        session = PlaybackSession()
        session.set_source('first.wav', 0, 4)
        generation = session._generation
        prepared = PreparedAudio()
        write_test_wav(prepared.path)
        session.set_source('second.wav', 0, 4)
        session._events.put((generation, prepared, ''))
        with patch('playback.default_output') as output:
            session.poll()
            output.assert_not_called()
        self.assertIsNone(session.player)
        self.assertFalse(prepared.path.exists())
        session.clear()
        self.assertTrue(session.is_closed())

    def test_stop_cancels_decode_autoplay_intent(self):
        """준비 중 정지를 누르면 완료 이벤트가 와도 재생하지 않는다."""
        session = PlaybackSession()
        session.set_source('first.wav', 0, 4)
        generation = session._generation
        session.preparing = True
        prepared = PreparedAudio()
        write_test_wav(prepared.path)
        session.stop()
        session._events.put((generation, prepared, ''))
        session.poll()
        self.assertIsNone(session.player)
        self.assertFalse(prepared.path.exists())
        session.clear()


class TransportTests(unittest.TestCase):
    """샘플 위치를 기준으로 탐색·재생·반복 상태를 확인한다."""

    def test_initial_state_never_autoplays(self):
        """준비 완료만으로 소리가 나지 않는다."""
        transport = Transport(1000, 100)
        self.assertEqual(transport.state, "ready")
        self.assertEqual(transport.position, 0)
        self.assertIsNone(transport.next_span(64))

    def test_pause_seek_and_stop(self):
        """일시정지는 위치를 보존하고 정지는 맨 앞으로 돌아간다."""
        transport = Transport(1000, 100)
        transport.seek(2.5)
        transport.play()
        self.assertEqual(transport.next_span(64), (250, 314))
        transport.advance(64)
        transport.pause()
        self.assertAlmostEqual(transport.seconds, 3.14)
        self.assertIsNone(transport.next_span(64))
        transport.stop()
        self.assertEqual((transport.position, transport.state), (0, "ready"))

    def test_loop_is_half_open_and_never_overreads(self):
        """반복 끝을 넘지 않는 블록만 읽고 정확한 시작으로 돌아간다."""
        transport = Transport(1000, 100)
        transport.set_loop(2, 3)
        transport.play()
        self.assertEqual(transport.next_span(64), (200, 264))
        transport.advance(64)
        self.assertEqual(transport.next_span(64), (264, 300))
        transport.advance(36)
        self.assertEqual(transport.next_span(64), (200, 264))

    def test_eof_finishes_and_play_restarts(self):
        """곡 끝은 한 번 종료하고 재생 요청 시 처음부터 시작한다."""
        transport = Transport(1000, 100)
        transport.seek(9.9)
        transport.play()
        self.assertEqual(transport.next_span(64), (990, 1000))
        transport.advance(10)
        self.assertEqual(transport.state, "finished")
        self.assertIsNone(transport.next_span(64))
        transport.play()
        self.assertEqual(transport.position, 0)

    def test_seek_to_eof_while_playing_finishes_without_empty_block(self):
        """재생 중 맨 끝 탐색은 길이 0인 오디오 블록을 만들지 않는다."""
        transport = Transport(1000, 100)
        transport.play()
        transport.seek(10)
        self.assertIsNone(transport.next_span(64))
        self.assertEqual(transport.state, 'finished')

    def test_invalid_commands_preserve_state(self):
        """잘못된 시간과 반복 범위는 이전 재생 상태를 변경하지 않는다."""
        transport = Transport(1000, 100)
        transport.seek(4)
        for value in (float("nan"), float("inf"), -1, 11):
            with self.subTest(value=value), self.assertRaises(ValueError):
                transport.seek(value)
        for start, end in ((3, 3), (4, 2), (-1, 2), (1, 11)):
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                transport.set_loop(start, end)
        self.assertEqual(transport.position, 400)

    def test_pcm_block_preserves_stereo_and_bounds(self):
        """실제 WAV에서 지정된 프레임만 float32로 읽는다."""
        samples = np.array([[100, -100], [200, -200], [300, -300]], dtype="<i2")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "stereo.wav"
            with wave.open(str(path), "wb") as target:
                target.setparams((2, 2, 44100, 0, "NONE", "not compressed"))
                target.writeframes(samples.tobytes())
            with wave.open(str(path), "rb") as source:
                block = read_pcm_block(source, 1, 3)
                np.testing.assert_array_equal(block, samples[1:].astype(np.float32) / 32768)
                self.assertEqual(block.dtype, np.float32)
                with self.assertRaises(ValueError):
                    read_pcm_block(source, 2, 4)


if __name__ == "__main__":
    unittest.main()
