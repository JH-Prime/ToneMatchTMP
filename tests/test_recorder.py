"""실시간 캡처 블록과 WAV 녹음을 실제 오디오 장치 없이 검증한다."""

from __future__ import annotations

import sys
import tempfile
import threading
import types
import unittest
import wave
from pathlib import Path
from typing import Callable
from unittest import mock

import numpy as np


MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

import recorder  # noqa: E402


class _FakeRecorder:
    """SoundCard 연속 녹음 컨텍스트의 최소 동작을 대신한다."""

    def __init__(
        self,
        block_factory: Callable[[int], np.ndarray],
        *,
        on_record: Callable[[], None] | None = None,
        failure: Exception | None = None,
    ) -> None:
        """반환 블록 생성기와 선택적인 중지·실패 동작을 저장한다."""
        self.block_factory = block_factory
        self.on_record = on_record
        self.failure = failure
        self.record_requests: list[int] = []
        self.entered = False
        self.exited = False

    def __enter__(self) -> _FakeRecorder:
        """가짜 녹음 컨텍스트가 열렸음을 기록한다."""
        self.entered = True
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        """오류 유무와 관계없이 가짜 녹음 컨텍스트가 닫혔음을 기록한다."""
        self.exited = True

    def record(self, numframes: int) -> np.ndarray:
        """요청 프레임 수를 기록하고 구성된 블록 또는 오류를 반환한다."""
        self.record_requests.append(numframes)
        if self.on_record:
            self.on_record()
        if self.failure:
            raise self.failure
        return self.block_factory(numframes)


class _FakeMicrophone:
    """SoundCard 마이크의 recorder 생성 호출을 대신한다."""

    def __init__(self, capture: _FakeRecorder) -> None:
        """테스트에서 돌려줄 가짜 녹음 컨텍스트를 저장한다."""
        self.capture = capture
        self.recorder_options: list[dict[str, int]] = []

    def recorder(self, *, samplerate: int, channels: int, blocksize: int) -> _FakeRecorder:
        """요청된 스트림 설정을 기록하고 가짜 컨텍스트를 반환한다."""
        self.recorder_options.append(
            {"samplerate": samplerate, "channels": channels, "blocksize": blocksize}
        )
        return self.capture


def _fake_soundcard(
    microphone: _FakeMicrophone | None = None,
    *,
    failure: Exception | None = None,
) -> tuple[types.ModuleType, list[tuple[str, bool]]]:
    """get_microphone 호출을 추적하는 가짜 soundcard 모듈을 만든다."""
    calls: list[tuple[str, bool]] = []
    module = types.ModuleType("soundcard")

    def get_microphone(device_id: str, include_loopback: bool = False) -> _FakeMicrophone | None:
        """장치 조회 인자를 기록하고 지정된 마이크 또는 오류를 돌려준다."""
        calls.append((device_id, include_loopback))
        if failure:
            raise failure
        return microphone

    module.get_microphone = get_microphone  # type: ignore[attr-defined]
    return module, calls


class RecorderTests(unittest.TestCase):
    """채널 정규화와 실시간 장치 수명 주기의 회귀를 검사한다."""

    def test_normalize_capture_block_makes_stereo_float32(self) -> None:
        """1차원·모노·다채널 입력을 예측 가능한 스테레오 float32로 바꾼다."""
        one_dimensional = recorder._normalize_capture_block(np.array([0.25, -0.5]))
        single_channel = recorder._normalize_capture_block(np.array([[0.1], [0.2]], dtype=np.float64))
        many_channels = recorder._normalize_capture_block(
            np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]], dtype=np.float64)
        )

        self.assertEqual(one_dimensional.dtype, np.float32)
        self.assertTrue(one_dimensional.flags.c_contiguous)
        np.testing.assert_array_equal(one_dimensional[:, 0], one_dimensional[:, 1])
        np.testing.assert_allclose(single_channel, [[0.1, 0.1], [0.2, 0.2]])
        np.testing.assert_allclose(many_channels, [[1.0, 2.0], [4.0, 5.0]])

    def test_normalize_capture_block_rejects_invalid_shapes(self) -> None:
        """프레임·채널 형태가 아닌 배열과 채널 없는 배열을 명확히 거부한다."""
        with self.assertRaisesRegex(ValueError, "one- or two-dimensional"):
            recorder._normalize_capture_block(np.zeros((1, 2, 3), dtype=np.float32))
        with self.assertRaisesRegex(ValueError, "at least one channel"):
            recorder._normalize_capture_block(np.empty((4, 0), dtype=np.float32))

    def test_monitor_delivers_normalized_block_and_stops_from_callback(self) -> None:
        """실시간 모니터는 정규화 블록과 샘플률을 전달하고 중지 뒤 스트림을 닫는다."""
        stop_event = threading.Event()
        capture = _FakeRecorder(lambda frames: np.linspace(-1.0, 1.0, frames, dtype=np.float64))
        microphone = _FakeMicrophone(capture)
        soundcard, calls = _fake_soundcard(microphone)
        received: list[tuple[np.ndarray, int]] = []

        def receive(block: np.ndarray, sample_rate: int) -> None:
            """첫 블록을 보관한 뒤 모니터 루프에 중지를 요청한다."""
            received.append((block, sample_rate))
            stop_event.set()

        with mock.patch.dict(sys.modules, {"soundcard": soundcard}):
            recorder.monitor_capture_device(
                "loopback-id",
                stop_event,
                receive,
                "en",
                sample_rate=48_000,
                block_frames=4,
            )

        self.assertEqual(calls, [("loopback-id", True)])
        self.assertEqual(
            microphone.recorder_options,
            [{"samplerate": 48_000, "channels": 2, "blocksize": 4}],
        )
        self.assertEqual(capture.record_requests, [4])
        self.assertTrue(capture.entered)
        self.assertTrue(capture.exited)
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0][0].shape, (4, 2))
        self.assertEqual(received[0][0].dtype, np.float32)
        self.assertEqual(received[0][1], 48_000)

    def test_monitor_drops_block_when_cancelled_during_blocking_read(self) -> None:
        """record 대기 중 들어온 중지 요청은 낡은 블록 콜백을 발생시키지 않는다."""
        stop_event = threading.Event()
        capture = _FakeRecorder(
            lambda frames: np.ones((frames, 2), dtype=np.float32),
            on_record=stop_event.set,
        )
        soundcard, _calls = _fake_soundcard(_FakeMicrophone(capture))
        received: list[np.ndarray] = []

        def receive(block: np.ndarray, _sample_rate: int) -> None:
            """취소 뒤 잘못 전달된 블록이 있는지 확인하도록 목록에 추가한다."""
            received.append(block)

        with mock.patch.dict(sys.modules, {"soundcard": soundcard}):
            recorder.monitor_capture_device("device-id", stop_event, receive, block_frames=8)

        self.assertEqual(received, [])
        self.assertTrue(capture.exited)

    def test_monitor_with_preexisting_stop_does_not_open_device(self) -> None:
        """이미 중지된 모니터 요청은 오디오 장치를 열지 않고 즉시 끝난다."""
        stop_event = threading.Event()
        stop_event.set()
        soundcard, calls = _fake_soundcard()

        def receive(_block: np.ndarray, _sample_rate: int) -> None:
            """사전 중지된 호출에서는 실행되면 안 되는 콜백이다."""
            self.fail("callback must not run")

        with mock.patch.dict(sys.modules, {"soundcard": soundcard}):
            recorder.monitor_capture_device("device-id", stop_event, receive)

        self.assertEqual(calls, [])

    def test_monitor_reports_missing_and_unopenable_devices(self) -> None:
        """사라진 장치와 장치 조회 실패를 번역된 RecordingError로 구분한다."""
        missing_soundcard, missing_calls = _fake_soundcard(None)
        with mock.patch.dict(sys.modules, {"soundcard": missing_soundcard}):
            with self.assertRaisesRegex(recorder.RecordingError, "no longer available"):
                recorder.monitor_capture_device("missing", threading.Event(), lambda _b, _r: None, "en")
        self.assertEqual(missing_calls, [("missing", True)])

        unavailable_soundcard, unavailable_calls = _fake_soundcard(failure=RuntimeError("WASAPI unavailable"))
        with mock.patch.dict(sys.modules, {"soundcard": unavailable_soundcard}):
            with self.assertRaisesRegex(recorder.RecordingError, "Could not open.*WASAPI unavailable") as raised:
                recorder.monitor_capture_device("broken", threading.Event(), lambda _b, _r: None, "en")
        self.assertIsInstance(raised.exception.__cause__, RuntimeError)
        self.assertEqual(unavailable_calls, [("broken", True)])

        indexed_soundcard, indexed_calls = _fake_soundcard(failure=IndexError("missing device id"))
        with mock.patch.dict(sys.modules, {"soundcard": indexed_soundcard}):
            with self.assertRaisesRegex(recorder.RecordingError, "no longer available") as indexed:
                recorder.monitor_capture_device("unplugged", threading.Event(), lambda _b, _r: None, "en")
        self.assertIsInstance(indexed.exception.__cause__, IndexError)
        self.assertEqual(indexed_calls, [("unplugged", True)])

        with tempfile.TemporaryDirectory() as temporary:
            with mock.patch.dict(sys.modules, {"soundcard": indexed_soundcard}):
                with self.assertRaisesRegex(recorder.RecordingError, "no longer available"):
                    recorder.record_device_to_wav(
                        "unplugged",
                        Path(temporary) / "capture.wav",
                        3.0,
                        threading.Event(),
                        language="en",
                    )

    def test_monitor_wraps_stream_failure_and_closes_context(self) -> None:
        """스트림 읽기 오류를 사용자용 실패로 감싸면서 컨텍스트를 반드시 닫는다."""
        capture = _FakeRecorder(
            lambda frames: np.zeros((frames, 2), dtype=np.float32),
            failure=RuntimeError("device disconnected"),
        )
        soundcard, _calls = _fake_soundcard(_FakeMicrophone(capture))

        with mock.patch.dict(sys.modules, {"soundcard": soundcard}):
            with self.assertRaisesRegex(recorder.RecordingError, "Recording failed.*device disconnected") as raised:
                recorder.monitor_capture_device("device-id", threading.Event(), lambda _b, _r: None, "en")

        self.assertIsInstance(raised.exception.__cause__, RuntimeError)
        self.assertTrue(capture.exited)

    def test_wav_recording_reuses_mono_normalization(self) -> None:
        """기존 WAV 녹음도 모노 블록을 스테레오 PCM으로 쓰는 공통 경로를 사용한다."""
        capture = _FakeRecorder(lambda frames: np.full(frames, 0.25, dtype=np.float32))
        microphone = _FakeMicrophone(capture)
        soundcard, _calls = _fake_soundcard(microphone)

        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "capture.wav"
            with mock.patch.dict(sys.modules, {"soundcard": soundcard}):
                duration = recorder.record_device_to_wav(
                    "microphone-id",
                    destination,
                    3.0,
                    threading.Event(),
                    language="en",
                )
            with wave.open(str(destination), "rb") as recorded:
                self.assertEqual(recorded.getnchannels(), 2)
                self.assertEqual(recorded.getframerate(), recorder.RECORD_SAMPLE_RATE)
                self.assertEqual(recorded.getnframes(), int(duration * recorder.RECORD_SAMPLE_RATE))

        self.assertAlmostEqual(duration, 3.0)
        self.assertEqual(
            microphone.recorder_options,
            [
                {
                    "samplerate": recorder.RECORD_SAMPLE_RATE,
                    "channels": 2,
                    "blocksize": recorder.RECORD_BLOCK_FRAMES,
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
