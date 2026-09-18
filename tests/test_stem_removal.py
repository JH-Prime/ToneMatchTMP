"""6-stem 선택 제거의 합산·정규화·경로 보호·정리 동작을 검증한다."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

import numpy as np


MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

import separator  # noqa: E402
import stem_removal  # noqa: E402


def _write_source(path: Path) -> None:
    """경로 검증에 사용할 작은 입력 파일을 만든다."""
    path.write_bytes(b"test source")


def _fake_decode(
    _source: Path,
    destination: Path,
    _start: float,
    _requested: float,
    _progress: object,
    _cancel: object,
    _language: str,
) -> float:
    """FFmpeg 없이 분리기에 전달할 최소 stereo PCM 파일을 만든다."""
    with wave.open(str(destination), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(separator.SEPARATOR_SAMPLE_RATE)
        output.writeframes(np.zeros((8, 2), dtype="<i2").tobytes())
    return 8 / separator.SEPARATOR_SAMPLE_RATE


def _separation_info(requested: tuple[str, ...], chunks: int, frames: int) -> separator.StemSeparationInfo:
    """공개 결과 사전에 옮겨지는 가상 분리 진단 정보를 만든다."""
    duration = frames / separator.SEPARATOR_SAMPLE_RATE
    return separator.StemSeparationInfo(
        model=separator.SEPARATOR_MODEL,
        backend="Demucs test / PyTorch CPU",
        sample_rate=separator.SEPARATOR_SAMPLE_RATE,
        channels=2,
        source_duration_seconds=duration,
        processed_chunks=chunks,
        available_stems=separator.SEPARATOR_STEMS,
        requested_stems=requested,
        model_downloaded_during_run=False,
        requested_device="auto",
        resolved_device="cpu",
        inference_total_seconds=0.25,
        inference_seconds_per_chunk=0.25 / chunks,
        realtime_factor=0.25 / max(duration, 1e-12),
        peak_gpu_memory_bytes=None,
    )


def _fake_chunk_separator(
    values: dict[str, float],
    frames_per_chunk: int = 4,
    chunks: int = 2,
    calls: list[tuple[str, ...]] | None = None,
):
    """한 번의 모델 실행에서 결정론적인 6-stem 조각을 전달하는 가짜 함수를 만든다."""
    def run(
        _source: Path,
        stem_names: object,
        consume_chunk: object,
        progress: object = None,
        _cancel: object = None,
        _language: str = "ko",
        _compute: str = "auto",
    ) -> separator.StemSeparationInfo:
        """선택된 stem의 결정론적인 조각을 콜백에 전달하고 가상 진단을 반환한다."""
        requested = tuple(stem_names)
        if calls is not None:
            calls.append(requested)
        if progress:
            progress(18, "model")
        for _index in range(chunks):
            stems = {
                name: np.full((2, frames_per_chunk), values[name], dtype=np.float32)
                for name in requested
            }
            consume_chunk(stems)
        if progress:
            progress(68, "done")
        return _separation_info(requested, chunks, frames_per_chunk * chunks)

    return run


def _read_pcm(path: Path) -> tuple[np.ndarray, int, int, int]:
    """결과 WAV의 float 환산 샘플과 기본 PCM 형식을 읽는다."""
    with wave.open(str(path), "rb") as source:
        channels = source.getnchannels()
        width = source.getsampwidth()
        rate = source.getframerate()
        values = np.frombuffer(source.readframes(source.getnframes()), dtype="<i2")
    return values.astype(np.float64) / 32_767.0, channels, width, rate


class StemRemovalMixTests(unittest.TestCase):
    """선택한 stem만 빠지고 남은 stem이 한 번의 추론 결과로 정확히 합쳐지는지 검증한다."""

    def test_selected_stems_are_removed_in_one_pass_and_result_is_json_safe(self) -> None:
        """기타·피아노를 제외한 네 stem의 정확한 합을 새 PCM16 WAV로 기록해야 한다."""
        values = {"vocals": 0.05, "drums": 0.04, "bass": 0.03,
                  "guitar": 0.20, "piano": 0.10, "other": 0.02}
        calls: list[tuple[str, ...]] = []
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, destination = root / "input.mp3", root / "without-guitar-piano.wav"
            _write_source(source)
            with (patch.object(stem_removal, "_decode_input", side_effect=_fake_decode),
                  patch.object(stem_removal, "separate_stem_chunks",
                               side_effect=_fake_chunk_separator(values, calls=calls))):
                result = stem_removal.remove_stems_from_file(
                    source, destination, ["piano", "guitar", "GUITAR"])
            samples, channels, width, rate = _read_pcm(destination)
            self.assertTrue(np.allclose(samples, 0.14, atol=1 / 32_767.0))
            self.assertEqual((channels, width, rate), (2, 2, separator.SEPARATOR_SAMPLE_RATE))
            self.assertEqual(calls, [("vocals", "drums", "bass", "other")])
            self.assertEqual(result["removed_stems"], ["guitar", "piano"])
            self.assertEqual(result["kept_stems"], ["vocals", "drums", "bass", "other"])
            self.assertFalse(result["normalized"])
            self.assertEqual(result["normalization_gain"], 1.0)
            self.assertEqual(result["sample_format"], "PCM16LE")
            json.dumps(result)
            self.assertEqual(list(root.glob(".*.partial.wav")), [])

    def test_clipping_mix_is_normalized_once_without_changing_balance(self) -> None:
        """남은 stem 합이 0 dBFS를 넘을 때만 동일 게인으로 낮춰 클리핑을 막아야 한다."""
        values = {name: 0.30 for name in separator.SEPARATOR_STEMS}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, destination = root / "input.wav", root / "normalized.wav"
            _write_source(source)
            with (patch.object(stem_removal, "_decode_input", side_effect=_fake_decode),
                  patch.object(stem_removal, "separate_stem_chunks",
                               side_effect=_fake_chunk_separator(values))):
                result = stem_removal.remove_stems_from_file(source, destination, ["guitar"])
            samples, _channels, _width, _rate = _read_pcm(destination)
            self.assertTrue(result["normalized"])
            self.assertAlmostEqual(result["peak_before_normalization"], 1.5, places=6)
            self.assertAlmostEqual(result["normalization_gain"], 0.999 / 1.5, places=6)
            self.assertAlmostEqual(float(np.max(np.abs(samples))), 0.999, places=4)

    def test_progress_is_monotonic_and_finishes_at_one_hundred(self) -> None:
        """디코딩·분리·출력 진행률은 뒤로 가지 않고 성공 시 100으로 끝나야 한다."""
        events: list[float] = []
        values = {name: 0.02 for name in separator.SEPARATOR_STEMS}

        def decode_with_progress(*args: object) -> float:
            """실제 디코더와 같은 3·12 진행 이벤트를 기록한다."""
            progress = args[4]
            if progress:
                progress(3, "decode")
            duration = _fake_decode(*args)
            if progress:
                progress(12, "decoded")
            return duration

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, destination = root / "input.mp3", root / "output.wav"
            _write_source(source)
            with (patch.object(stem_removal, "_decode_input", side_effect=decode_with_progress),
                  patch.object(stem_removal, "separate_stem_chunks",
                               side_effect=_fake_chunk_separator(values))):
                stem_removal.remove_stems_from_file(
                    source, destination, ["vocals"], progress=lambda value, _message: events.append(value))
        self.assertEqual(events, sorted(events))
        self.assertEqual(events[0], 0)
        self.assertEqual(events[-1], 100)
        self.assertTrue(any(15 <= value <= 85 for value in events))


class StemRemovalSafetyTests(unittest.TestCase):
    """사용자 파일 보호와 취소·실패 시 임시 출력 정리를 검증한다."""

    def test_dangling_destination_entry_is_not_followed(self) -> None:
        """존재 여부는 링크 대상이 아니라 지정한 파일 이름 자체에서 검사해야 한다."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, destination = root / "source.mp3", root / "dangling.wav"
            _write_source(source)
            with patch.object(stem_removal.os.path, "lexists", return_value=True) as exists:
                with self.assertRaisesRegex(stem_removal.StemRemovalError, "already exists"):
                    stem_removal._normalized_paths(source, destination, "en")
            exists.assert_called_once_with(root.resolve() / destination.name)
            self.assertFalse(destination.exists())

    def test_invalid_stem_selections_are_rejected_before_processing(self) -> None:
        """빈 목록·알 수 없는 이름·전체 제거는 유용한 출력이 없어 거부해야 한다."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.mp3"
            _write_source(source)
            cases = ([], ["sax"], list(separator.SEPARATOR_STEMS))
            for index, removed in enumerate(cases):
                with self.subTest(removed=removed), self.assertRaises(stem_removal.StemRemovalError):
                    stem_removal.remove_stems_from_file(source, root / f"out-{index}.wav", removed)

    def test_source_and_existing_destination_are_never_overwritten(self) -> None:
        """원본과 기존 사용자 파일을 출력 대상으로 지정해도 바이트가 바뀌지 않아야 한다."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, existing = root / "source.wav", root / "existing.wav"
            source.write_bytes(b"original")
            existing.write_bytes(b"keep me")
            with self.assertRaises(stem_removal.StemRemovalError):
                stem_removal.remove_stems_from_file(source, source, ["guitar"])
            with self.assertRaises(stem_removal.StemRemovalError):
                stem_removal.remove_stems_from_file(source, existing, ["guitar"])
            self.assertEqual(source.read_bytes(), b"original")
            self.assertEqual(existing.read_bytes(), b"keep me")

    def test_non_wav_destination_and_short_or_invalid_ranges_are_rejected(self) -> None:
        """출력 형식과 3초 미만·역방향·비정상 시간은 FFmpeg 실행 전에 실패해야 한다."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.mp3"
            _write_source(source)
            with self.assertRaises(stem_removal.StemRemovalError):
                stem_removal.remove_stems_from_file(source, root / "output.mp3", ["guitar"])
            for start, end in ((1, 2), (5, 4), (-1, 5), (float("nan"), 5)):
                with self.subTest(start=start, end=end), self.assertRaises(stem_removal.StemRemovalError):
                    stem_removal.remove_stems_from_file(
                        source, root / f"range-{str(start)}.wav", ["guitar"], start, end)

    def test_request_is_capped_at_twenty_minutes_and_parent_is_created(self) -> None:
        """긴 끝 시간은 20분으로 제한하고 명시한 새 출력 폴더를 안전하게 만들어야 한다."""
        requested: list[float] = []
        values = {name: 0.02 for name in separator.SEPARATOR_STEMS}

        def capture_decode(*args: object) -> float:
            """디코더로 전달된 제한 시간을 기록한다."""
            requested.append(float(args[3]))
            return _fake_decode(*args)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, destination = root / "input.mp3", root / "new" / "nested" / "output.wav"
            _write_source(source)
            with (patch.object(stem_removal, "_decode_input", side_effect=capture_decode),
                  patch.object(stem_removal, "separate_stem_chunks",
                               side_effect=_fake_chunk_separator(values))):
                stem_removal.remove_stems_from_file(source, destination, ["piano"], 5, 5_000)
            self.assertEqual(requested, [stem_removal.MAX_REMOVAL_SECONDS])
            self.assertTrue(destination.is_file())

    def test_cancellation_removes_partial_output_and_preserves_no_final_file(self) -> None:
        """첫 합산 조각 뒤 취소되어도 최종·partial WAV가 남지 않아야 한다."""
        values = {name: 0.02 for name in separator.SEPARATOR_STEMS}

        def cancelling_separator(
            _source: Path, stem_names: object, consume_chunk: object, *_args: object
        ) -> separator.StemSeparationInfo:
            """한 조각을 전달한 뒤 Demucs 취소 예외를 발생시킨다."""
            requested = tuple(stem_names)
            consume_chunk({name: np.full((2, 4), values[name], dtype=np.float32) for name in requested})
            raise separator.SeparationCancelled("cancelled")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, destination = root / "input.mp3", root / "cancelled.wav"
            _write_source(source)
            with (patch.object(stem_removal, "_decode_input", side_effect=_fake_decode),
                  patch.object(stem_removal, "separate_stem_chunks", side_effect=cancelling_separator)):
                with self.assertRaises(stem_removal.StemRemovalCancelled):
                    stem_removal.remove_stems_from_file(source, destination, ["drums"])
            self.assertFalse(destination.exists())
            self.assertEqual(list(root.glob(".*.partial.wav")), [])

    def test_output_failure_removes_the_adjacent_partial_file(self) -> None:
        """PCM 기록 실패 시 같은 폴더의 partial 파일을 지우고 최종 파일을 만들지 않아야 한다."""
        values = {name: 0.02 for name in separator.SEPARATOR_STEMS}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, destination = root / "input.mp3", root / "failed.wav"
            _write_source(source)
            with (patch.object(stem_removal, "_decode_input", side_effect=_fake_decode),
                  patch.object(stem_removal, "separate_stem_chunks",
                               side_effect=_fake_chunk_separator(values)),
                  patch.object(stem_removal, "_write_pcm16_output",
                               side_effect=stem_removal.StemRemovalError("failed"))):
                with self.assertRaises(stem_removal.StemRemovalError):
                    stem_removal.remove_stems_from_file(source, destination, ["bass"])
            self.assertFalse(destination.exists())
            self.assertEqual(list(root.glob(".*.partial.wav")), [])

    def test_destination_race_uses_atomic_create_and_preserves_the_new_file(self) -> None:
        """처리 도중 같은 목적지가 생겨도 원자적 확정 연산이 이를 덮어쓰지 않아야 한다."""
        values = {name: 0.02 for name in separator.SEPARATOR_STEMS}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, destination = root / "input.mp3", root / "raced.wav"
            _write_source(source)

            def destination_appears(_partial: object, target: object) -> None:
                """다른 프로세스가 먼저 사용자 파일을 만든 경쟁 상황을 흉내 낸다."""
                Path(target).write_bytes(b"created by another process")
                raise FileExistsError(str(target))

            with (patch.object(stem_removal, "_decode_input", side_effect=_fake_decode),
                  patch.object(stem_removal, "separate_stem_chunks",
                               side_effect=_fake_chunk_separator(values)),
                  patch.object(stem_removal.os, "rename" if os.name == "nt" else "link",
                               side_effect=destination_appears)):
                with self.assertRaises(stem_removal.StemRemovalError) as context:
                    stem_removal.remove_stems_from_file(source, destination, ["other"])
            self.assertIn("not overwritten", str(context.exception))
            self.assertEqual(destination.read_bytes(), b"created by another process")
            self.assertEqual(list(root.glob(".*.partial.wav")), [])

    @unittest.skipUnless(os.name == "nt", "Windows no-overwrite rename contract")
    def test_windows_commit_needs_no_hard_links_and_refuses_existing_file(self) -> None:
        """Windows에서는 하드 링크를 지원하지 않는 저장소에도 기존 파일 보호를 유지한다."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            partial, destination = root / "partial.wav", root / "output.wav"
            partial.write_bytes(b"complete WAV")
            with patch.object(stem_removal.os, "link", side_effect=OSError("unsupported")):
                stem_removal._commit_new_output(partial, destination, "en")
            self.assertEqual(destination.read_bytes(), b"complete WAV")
            self.assertFalse(partial.exists())
            partial.write_bytes(b"different WAV")
            with self.assertRaises(stem_removal.StemRemovalError):
                stem_removal._commit_new_output(partial, destination, "en")
            self.assertEqual(destination.read_bytes(), b"complete WAV")
            self.assertEqual(partial.read_bytes(), b"different WAV")

    def test_temporary_cleanup_finishes_before_final_output_is_committed(self) -> None:
        """임시 오디오 정리에 실패하면 저장 성공을 실패로 뒤집거나 최종 파일을 남기지 않는다."""
        values = {name: 0.02 for name in separator.SEPARATOR_STEMS}
        original_exit = tempfile.TemporaryDirectory.__exit__

        def cleanup_fails_after_removing_files(instance: object, *args: object) -> None:
            """실제 임시 파일을 정리한 뒤 파일 시스템 오류를 흉내 낸다."""
            original_exit(instance, *args)
            raise PermissionError("cleanup blocked")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, destination = root / "input.mp3", root / "output.wav"
            _write_source(source)
            with (patch.object(stem_removal, "_decode_input", side_effect=_fake_decode),
                  patch.object(stem_removal, "separate_stem_chunks",
                               side_effect=_fake_chunk_separator(values)),
                  patch.object(tempfile.TemporaryDirectory, "__exit__", autospec=True,
                               side_effect=cleanup_fails_after_removing_files)):
                with self.assertRaises(stem_removal.StemRemovalError):
                    stem_removal.remove_stems_from_file(source, destination, ["guitar"])
            self.assertFalse(destination.exists())
            self.assertEqual(list(root.glob(".*.partial.wav")), [])

    def test_final_progress_callback_failure_does_not_hide_saved_output(self) -> None:
        """결과 확정 이후 UI 알림 오류가 나도 이미 저장한 파일과 성공 결과를 유지한다."""
        values = {name: 0.02 for name in separator.SEPARATOR_STEMS}

        def failing_completion(value: float, _message: str) -> None:
            """완료 이벤트 처리에서만 예외를 발생시킨다."""
            if value == 100:
                raise RuntimeError("UI is closing")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, destination = root / "input.mp3", root / "output.wav"
            _write_source(source)
            with (patch.object(stem_removal, "_decode_input", side_effect=_fake_decode),
                  patch.object(stem_removal, "separate_stem_chunks",
                               side_effect=_fake_chunk_separator(values))):
                result = stem_removal.remove_stems_from_file(
                    source, destination, ["guitar"], progress=failing_completion)
            self.assertEqual(result["output_path"], str(destination))
            self.assertTrue(destination.is_file())
            self.assertEqual(list(root.glob(".*.partial.wav")), [])

    def test_cancellation_during_wav_write_removes_adjacent_partial(self) -> None:
        """합산 완료 뒤 WAV 저장 중 취소도 미완성 출력과 최종 파일을 모두 남기지 않는다."""
        values = {name: 0.02 for name in separator.SEPARATOR_STEMS}
        cancelled = False

        def cancel_while_writing(value: float, _message: str) -> None:
            """PCM 블록 기록이 시작되면 취소 상태로 바꾼다."""
            nonlocal cancelled
            if value >= 90:
                cancelled = True

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, destination = root / "input.mp3", root / "output.wav"
            _write_source(source)
            with (patch.object(stem_removal, "_decode_input", side_effect=_fake_decode),
                  patch.object(stem_removal, "separate_stem_chunks",
                               side_effect=_fake_chunk_separator(values))):
                with self.assertRaises(stem_removal.StemRemovalCancelled):
                    stem_removal.remove_stems_from_file(
                        source, destination, ["guitar"], progress=cancel_while_writing,
                        cancel_requested=lambda: cancelled)
            self.assertFalse(destination.exists())
            self.assertEqual(list(root.glob(".*.partial.wav")), [])

    def test_finite_stem_sum_cannot_overflow_the_float32_temporary_mix(self) -> None:
        """비정상적으로 큰 유한 모델 출력도 float32 무한대로 저장되기 전에 거부한다."""
        values = {name: np.finfo(np.float32).max for name in separator.SEPARATOR_STEMS}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, destination = root / "input.mp3", root / "output.wav"
            _write_source(source)
            with (patch.object(stem_removal, "_decode_input", side_effect=_fake_decode),
                  patch.object(stem_removal, "separate_stem_chunks",
                               side_effect=_fake_chunk_separator(values))):
                with self.assertRaises(stem_removal.StemRemovalError):
                    stem_removal.remove_stems_from_file(source, destination, ["guitar"])
            self.assertFalse(destination.exists())

    def test_parent_creation_error_respects_the_requested_language(self) -> None:
        """출력 폴더 생성 오류는 영어 UI에서 영어 문장을 먼저 보여야 한다."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.mp3"
            _write_source(source)
            with patch.object(Path, "mkdir", side_effect=PermissionError("denied")):
                with self.assertRaises(stem_removal.StemRemovalError) as context:
                    stem_removal.remove_stems_from_file(
                        source, root / "new" / "output.wav", ["guitar"], language="en")
            self.assertTrue(str(context.exception).startswith("Could not create"))


class StemRemovalDecodeTests(unittest.TestCase):
    """번들 FFmpeg의 실제 구간·PCM 변환과 잘못된 입력 정리를 검증한다."""

    @unittest.skipUnless(stem_removal._ffmpeg_path().is_file(), "Bundled FFmpeg is unavailable")
    def test_bundled_ffmpeg_decodes_selected_segment_to_stereo_pcm16(self) -> None:
        """모노 48kHz 입력의 선택 구간은 정확한 44.1kHz 스테레오 PCM16이 되어야 한다."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, decoded = root / "source.wav", root / "decoded.wav"
            with wave.open(str(source), "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(48_000)
                output.writeframes(np.zeros(4 * 48_000, dtype="<i2").tobytes())
            duration = stem_removal._decode_input(source, decoded, 0.5, 3.0, None, None, "en")
            _values, channels, width, rate = _read_pcm(decoded)
            self.assertEqual((channels, width, rate), (2, 2, 44_100))
            self.assertAlmostEqual(duration, 3.0, places=4)

    @unittest.skipUnless(stem_removal._ffmpeg_path().is_file(), "Bundled FFmpeg is unavailable")
    def test_invalid_input_leaves_no_decoded_output(self) -> None:
        """디코딩할 수 없는 파일은 명확한 오류를 주고 임시 WAV를 남기지 않는다."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, decoded = root / "invalid.mp3", root / "decoded.wav"
            _write_source(source)
            with self.assertRaises(stem_removal.StemRemovalError):
                stem_removal._decode_input(source, decoded, 0, 3, None, None, "en")
            self.assertFalse(decoded.exists())


if __name__ == "__main__":
    unittest.main()
