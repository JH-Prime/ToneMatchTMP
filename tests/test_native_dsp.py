"""C++ DSP 브리지·안전한 대체 경로·스트리밍 FFT 수치 일치를 검증한다."""

from __future__ import annotations

import math
import ctypes
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np


MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

import native_dsp  # noqa: E402
from native_dsp import (  # noqa: E402
    NativeDspError, NativeSpectrumEngine, PythonSpectrumEngine,
    create_spectrum_engine, native_runtime_info,
)
from spectrum import SpectrumFrame, SpectrumSmoother, analyze_spectrum_frame  # noqa: E402


def _signal(frames: int, channels: int = 2, rate: int = 44_100) -> np.ndarray:
    """사인과 약한 광대역 성분이 섞인 재현 가능한 PCM을 만든다."""

    axis = np.arange(frames, dtype=np.float64) / rate
    mono = 0.35 * np.sin(2 * np.pi * 750 * axis) + 0.13 * np.sin(2 * np.pi * 3_000 * axis)
    noise = np.random.default_rng(9827).normal(0.0, 0.008, (frames, channels))
    return (mono[:, None] + noise).astype(np.float64)


def _assert_frame(test: unittest.TestCase, actual: SpectrumFrame, expected: SpectrumFrame) -> None:
    """독립 FFT 구현의 반올림을 허용하며 모든 공개 프레임 값을 비교한다."""

    np.testing.assert_allclose(actual.waveform, expected.waveform, atol=6e-8, rtol=0.0)
    np.testing.assert_allclose(actual.frequencies_hz, expected.frequencies_hz, atol=1e-10, rtol=1e-12)
    np.testing.assert_allclose(actual.magnitudes_dbfs, expected.magnitudes_dbfs, atol=2e-5, rtol=0.0)
    test.assertAlmostEqual(actual.rms_dbfs, expected.rms_dbfs, delta=1e-9)
    test.assertAlmostEqual(actual.peak_dbfs, expected.peak_dbfs, delta=1e-9)
    test.assertAlmostEqual(actual.spectral_centroid_hz, expected.spectral_centroid_hz, delta=1e-7)


class InputPreparationTests(unittest.TestCase):
    """ABI 2 입력의 정밀도·정렬·소유권과 float32 무변환 경로를 검증한다."""

    def test_aligned_contiguous_float32_does_not_allocate_input_sized_copy(self) -> None:
        """캡처의 native float32 배열은 읽기 전용인 경우에도 같은 메모리로 전달한다."""
        for mono in (False, True):
            source = _signal(128, 1 if mono else 2).astype(np.float32)
            if mono:
                source = source[:, 0]
            source.flags.writeable = False
            actual = native_dsp._prepare_block(source, 1 if mono else 2, native_float32=True)
            self.assertEqual(actual.dtype, np.dtype(np.float32))
            self.assertEqual(actual.ctypes.data, source.ctypes.data)
            self.assertTrue(np.shares_memory(actual, source))
            self.assertTrue(actual.flags.c_contiguous and actual.flags.aligned)
            self.assertFalse(actual.flags.writeable)

    def test_strided_and_unaligned_float32_are_copied_to_safe_layout(self) -> None:
        """stride와 정렬이 맞지 않는 float32는 정밀도를 유지하며 안전한 배열로 준비한다."""
        unaligned = np.ndarray((128, 2), dtype=np.float32,
                               buffer=np.zeros(128 * 2 * 4 + 1, dtype=np.uint8), offset=1)
        unaligned[:] = _signal(128)
        self.assertFalse(unaligned.flags.aligned)
        for source in (_signal(256).astype(np.float32)[::2], unaligned,
                       _signal(128).astype(np.float32)[:, ::-1]):
            with self.subTest(strides=source.strides, aligned=source.flags.aligned):
                actual = native_dsp._prepare_block(source, 2, native_float32=True)
                self.assertEqual(actual.dtype, np.dtype(np.float32))
                self.assertTrue(actual.flags.c_contiguous and actual.flags.aligned)
                self.assertFalse(np.shares_memory(actual, source))
                np.testing.assert_array_equal(actual, source)

    def test_other_dtypes_and_non_native_endian_keep_double_conversion(self) -> None:
        """기존 float64 정밀도를 낮추지 않고 다른 dtype도 기존 double 경로로 보낸다."""
        opposite_endian = ">f4" if sys.byteorder == "little" else "<f4"
        source64 = np.array([[0.123456789012345, -0.123456789012345]])
        sources = (source64, source64.astype(opposite_endian), source64.astype(np.float16),
                   np.array([[1, -1]], dtype=np.int16), np.array([[True, False]]))
        for source in sources:
            with self.subTest(dtype=source.dtype):
                actual = native_dsp._prepare_block(source, 2, native_float32=True)
                self.assertEqual(actual.dtype, np.dtype(np.float64))
                self.assertTrue(actual.flags.c_contiguous and actual.flags.aligned)
                np.testing.assert_array_equal(actual, source.astype(np.float64))
        self.assertIs(native_dsp._prepare_block(source64, 2, native_float32=True), source64)


class PythonStreamingTests(unittest.TestCase):
    """DLL 없이도 동작하는 bounded PCM 누적 및 평활화 계약을 검증한다."""

    def test_arbitrary_chunks_match_every_complete_fft_window(self) -> None:
        """부분 블록을 잃지 않고 완성된 모든 구간을 순서대로 평활화해야 한다."""

        size = 128
        samples = _signal(size * 9 + 17)
        engine = PythonSpectrumEngine(44_100, 2, fft_size=size)
        smoother = SpectrumSmoother(4)
        expected = [smoother.push(analyze_spectrum_frame(samples[index : index + size], 44_100, fft_size=size))
                    for index in range(0, size * 9, size)]
        consumed = completed = 0
        for length in (13, 37, 400, 5, 450, len(samples) - 905):
            previous = completed
            result = engine.push(samples[consumed : consumed + length])
            consumed += length
            completed = consumed // size
            if completed == previous:
                self.assertIsNone(result)
            else:
                _assert_frame(self, result, expected[completed - 1])
            self.assertLess(len(engine._pending), size)
        engine.close()

    def test_partial_buffer_copies_input_and_reset_clears_it(self) -> None:
        """호출자 배열 수정이나 reset 이전 부분 데이터가 다음 구간에 섞이면 안 된다."""

        source = _signal(128)
        engine = PythonSpectrumEngine(44_100, 2, fft_size=128)
        first = source[:64].copy()
        self.assertIsNone(engine.push(first))
        first[:] = 0.0
        expected = SpectrumSmoother(4).push(analyze_spectrum_frame(source, 44_100, fft_size=128))
        _assert_frame(self, engine.push(source[64:]), expected)
        engine.push(source[:20])
        engine.reset()
        self.assertIsNone(engine.push(source[20:]))
        engine.reset()
        _assert_frame(self, engine.push(source), expected)
        engine.close()

    def test_close_is_idempotent_and_rejects_future_work(self) -> None:
        """중복 close는 안전하지만 닫힌 엔진의 push와 reset은 거부해야 한다."""

        engine = PythonSpectrumEngine(44_100, 2)
        engine.close()
        engine.close()
        with self.assertRaises(NativeDspError):
            engine.push(_signal(2_048))
        with self.assertRaises(NativeDspError):
            engine.reset()
        with self.assertRaises(NativeDspError):
            engine.stream_stats()

    def test_stream_counters_track_partial_multiple_windows_reset_and_ownership(self) -> None:
        """입력 수와 실제 완성 창 수는 반환 프레임 수와 구분하고 reset에서 함께 비운다."""
        engine = PythonSpectrumEngine(44_100, 2, fft_size=128)
        accepted = 0
        try:
            for size in (13, 115, 400, 1, 19):
                engine.push(_signal(size).astype(np.float32))
                accepted += size
                expected = {"input_frames": accepted, "completed_windows": accepted // 128,
                            "pending_frames": accepted % 128}
                actual = engine.stream_stats()
                self.assertEqual(actual, expected)
                actual["input_frames"] = -1
                self.assertEqual(engine.stream_stats(), expected)
            with self.assertRaises(ValueError):
                engine.push(np.zeros((10, 1)))
            self.assertEqual(engine.stream_stats(), expected)
            engine.reset()
            self.assertEqual(engine.stream_stats(), dict.fromkeys(expected, 0))
        finally:
            engine.close()

    def test_counter_overflow_preserves_pending_history_and_statistics(self) -> None:
        """거대한 실행 없이 uint64 카운터 경계를 설정해 overflow 사전 거부를 검증한다."""
        engine = PythonSpectrumEngine(44_100, 2, fft_size=128)
        try:
            engine.push(_signal(127))
            engine._input_frames = native_dsp.MAX_STREAM_FRAMES
            saved = engine.stream_stats()
            pending = engine._pending.copy()
            with self.assertRaisesRegex(NativeDspError, "counter would overflow"):
                engine.push(_signal(1))
            self.assertEqual(engine.stream_stats(), saved)
            np.testing.assert_array_equal(engine._pending, pending)
            engine._input_frames = 127
            engine._completed_windows = native_dsp.MAX_STREAM_FRAMES
            saved = engine.stream_stats()
            with self.assertRaisesRegex(NativeDspError, "counter would overflow"):
                engine.push(_signal(1))
            self.assertEqual(engine.stream_stats(), saved)
            np.testing.assert_array_equal(engine._pending, pending)
            engine.reset()
            self.assertEqual(engine.stream_stats(), dict.fromkeys(saved, 0))
        finally:
            engine.close()

    def test_invalid_shapes_and_types_do_not_consume_pending_pcm(self) -> None:
        """잘못된 PCM을 거부한 뒤에도 이미 모은 유효 부분 블록을 보존해야 한다."""

        engine = PythonSpectrumEngine(44_100, 2, fft_size=128)
        source = _signal(128)
        engine.push(source[:64])
        invalid = (np.array([]), np.zeros(3), np.zeros((3, 1)), np.zeros((2, 2, 2)),
                   np.ones((2, 2), dtype=complex), np.full((2, 2), "bad"), [[1], [1, 2]])
        for samples in invalid:
            with self.subTest(samples=type(samples)), self.assertRaises(ValueError):
                engine.push(samples)
        expected = SpectrumSmoother().push(analyze_spectrum_frame(source, 44_100, fft_size=128))
        _assert_frame(self, engine.push(source[64:]), expected)
        engine.close()

    def test_oversized_block_is_rejected_before_contiguous_allocation(self) -> None:
        """큰 broadcast 배열은 C ABI 상한 검사로 즉시 거부하고 부분 PCM을 보존해야 한다."""

        engine = PythonSpectrumEngine(44_100, 2, fft_size=128)
        source = _signal(128)
        try:
            self.assertIsNone(engine.push(source[:64]))
            oversized = np.broadcast_to(np.zeros((1, 2)), (native_dsp.MAX_FRAMES_PER_PUSH + 1, 2))
            with patch.object(native_dsp.np, "ascontiguousarray", side_effect=AssertionError("must not allocate")):
                with self.assertRaisesRegex(ValueError, "10000000"):
                    engine.push(oversized)
            expected = SpectrumSmoother().push(analyze_spectrum_frame(source, 44_100, fft_size=128))
            _assert_frame(self, engine.push(source[64:]), expected)
        finally:
            engine.close()


class NativeSelectionTests(unittest.TestCase):
    """DLL 검색·ABI 검증·자동 대체 및 개인정보 없는 진단을 검증한다."""

    def test_auto_missing_library_falls_back_and_explicit_cpp_fails(self) -> None:
        """자동 선택만 DLL 실패를 NumPy로 대체하고 명시적 C++ 요청은 오류를 알려야 한다."""

        with patch.object(native_dsp, "_load_library", side_effect=NativeDspError("DLL unavailable")):
            engine = create_spectrum_engine(44_100, 2)
            self.assertEqual(engine.backend, "numpy")
            self.assertEqual(engine.fallback_reason, "DLL unavailable")
            engine.close()
            with self.assertRaisesRegex(NativeDspError, "DLL unavailable"):
                create_spectrum_engine(44_100, 2, backend="cpp")

    def test_unsupported_native_fft_retains_general_numpy_support(self) -> None:
        """기존 NumPy가 허용하는 홀수 FFT 설정은 자동 대체 후에도 사용할 수 있어야 한다."""

        with patch.object(native_dsp, "_load_library") as loader:
            engine = create_spectrum_engine(48_000, 1, fft_size=255)
            self.assertEqual(engine.backend, "numpy")
            self.assertIn("power of two", engine.fallback_reason)
            self.assertIsNotNone(engine.push(np.ones(255)))
            engine.close()
            loader.assert_not_called()

    def test_explicit_numpy_does_not_load_native_library(self) -> None:
        """명시적 NumPy 선택은 DLL 검색과 로드를 전혀 수행하지 않아야 한다."""

        with patch.object(native_dsp, "_load_library") as loader:
            engine = create_spectrum_engine(48_000, 2, backend="numpy")
            self.assertIsNone(engine.fallback_reason)
            engine.close()
            loader.assert_not_called()

    def test_common_invalid_configurations_are_not_silently_repaired(self) -> None:
        """불리언·빈 주파수 구간 등 공통 입력 오류는 자동 모드에서도 거부해야 한다."""

        cases = (
            dict(sample_rate=True, channels=2), dict(sample_rate=4_000, channels=2),
            dict(sample_rate=44_100, channels=0), dict(sample_rate=44_100, channels=2, fft_size=2),
            dict(sample_rate=44_100, channels=2, history_size=0),
            dict(sample_rate=44_100, channels=2, min_hz=float("nan")),
            dict(sample_rate=44_100, channels=2, min_hz=1_001, max_hz=1_002),
            dict(sample_rate=44_100, channels=2, backend="unknown"),
        )
        for options in cases:
            with self.subTest(options=options), self.assertRaises(ValueError):
                create_spectrum_engine(**options)

    def test_dll_search_uses_only_absolute_trusted_resource_paths(self) -> None:
        """검색 후보는 모듈 또는 동결 번들의 resources 안에만 있어야 한다."""

        with patch.object(sys, "_MEIPASS", "relative-untrusted", create=True):
            candidates = native_dsp._library_candidates()
        self.assertTrue(candidates)
        for candidate in candidates:
            self.assertTrue(candidate.is_absolute())
            self.assertEqual(candidate.name, "tonematch_dsp.dll")
            self.assertEqual(candidate.parent.name, "resources")
            self.assertEqual(candidate.parent.parent, Path(native_dsp.__file__).resolve().parent)

    def test_load_errors_do_not_expose_private_paths(self) -> None:
        """운영체제 로더의 개인 경로는 공개 런타임 진단에 복사하지 않아야 한다."""

        with tempfile.TemporaryDirectory(prefix="tonematch_dsp_test_") as temporary:
            placeholder = Path(temporary) / "tonematch_dsp.dll"
            placeholder.touch()
            with patch.object(native_dsp, "_library_candidates", return_value=(placeholder,)), \
                 patch.object(native_dsp.ctypes, "CDLL", side_effect=OSError("C:/Users/private/person.dll failed")):
                info = native_runtime_info()
        self.assertFalse(info["available"])
        self.assertEqual(info["backend"], "numpy")
        self.assertNotIn("private", str(info))
        self.assertNotIn(temporary, str(info))
        self.assertEqual(info["library"], "tonematch_dsp.dll")

    def test_abi_mismatch_and_missing_symbols_are_rejected(self) -> None:
        """다른 ABI 또는 불완전한 내보내기를 가진 DLL을 사용하지 않아야 한다."""

        with tempfile.TemporaryDirectory(prefix="tonematch_dsp_abi_") as temporary:
            placeholder = Path(temporary) / "tonematch_dsp.dll"
            placeholder.touch()
            wrong = Mock()
            wrong.tm_dsp_abi_version.return_value = 1
            with patch.object(native_dsp, "_library_candidates", return_value=(placeholder,)), \
                 patch.object(native_dsp.ctypes, "CDLL", return_value=wrong):
                with self.assertRaisesRegex(NativeDspError, "ABI mismatch"):
                    native_dsp._load_library()
            with patch.object(native_dsp, "_library_candidates", return_value=(placeholder,)), \
                 patch.object(native_dsp.ctypes, "CDLL", return_value=object()):
                with self.assertRaisesRegex(NativeDspError, "required ABI functions"):
                    native_dsp._load_library()

    def test_failed_native_output_initialization_releases_context_once(self) -> None:
        """컨텍스트 생성 후 잘못된 bin 수나 짧은 격자 복사는 핸들을 한 번만 해제해야 한다."""

        for count, written in ((0, 0), (100_000, 100_000), (8, 0), (8, -1)):
            with self.subTest(count=count, written=written):
                library = Mock()
                library.tm_dsp_create.return_value = 1234
                library.tm_dsp_bin_count.return_value = count
                library.tm_dsp_frequencies.return_value = written
                with patch.object(native_dsp, "_load_library", return_value=library):
                    with self.assertRaises(NativeDspError):
                        NativeSpectrumEngine(44_100, 2, fft_size=128)
                library.tm_dsp_destroy.assert_called_once()
                self.assertEqual(library.tm_dsp_destroy.call_args.args[0].value, 1234)

    def test_abi_one_library_is_explicitly_rejected_and_auto_uses_numpy(self) -> None:
        """ABI 1 DLL에 새 함수를 호출하지 않고 strict 오류와 자동 대체를 구분한다."""
        with tempfile.TemporaryDirectory(prefix="tonematch_dsp_abi1_") as temporary:
            placeholder = Path(temporary) / "tonematch_dsp.dll"
            placeholder.touch()
            old = Mock()
            old.tm_dsp_abi_version.return_value = 1
            with patch.object(native_dsp, "_library_candidates", return_value=(placeholder,)), \
                 patch.object(native_dsp.ctypes, "CDLL", return_value=old):
                with self.assertRaisesRegex(NativeDspError, "expected 2, received 1"):
                    create_spectrum_engine(44_100, 2, backend="cpp")
                engine = create_spectrum_engine(44_100, 2, backend="auto")
                try:
                    self.assertEqual(engine.backend, "numpy")
                    self.assertIn("expected 2, received 1", engine.fallback_reason)
                    engine.push(_signal(2048))
                    self.assertEqual(engine.stream_stats(), {"input_frames": 2048, "completed_windows": 1,
                                                             "pending_frames": 0})
                finally:
                    engine.close()
            old.tm_dsp_create.assert_not_called()

    def test_abi_two_library_requires_all_new_symbols(self) -> None:
        """ABI 번호만 올리고 float32·통계 함수를 누락한 DLL도 안전하게 거부한다."""
        names = ("tm_dsp_abi_version", "tm_dsp_create", "tm_dsp_destroy", "tm_dsp_reset",
                 "tm_dsp_bin_count", "tm_dsp_frequencies", "tm_dsp_push", "tm_dsp_push_f32",
                 "tm_dsp_stream_stats")
        with tempfile.TemporaryDirectory(prefix="tonematch_dsp_symbols_") as temporary:
            placeholder = Path(temporary) / "tonematch_dsp.dll"
            placeholder.touch()
            for missing in ("tm_dsp_push_f32", "tm_dsp_stream_stats"):
                library = Mock(spec=[name for name in names if name != missing])
                library.tm_dsp_abi_version.return_value = 2
                with self.subTest(missing=missing), \
                     patch.object(native_dsp, "_library_candidates", return_value=(placeholder,)), \
                     patch.object(native_dsp.ctypes, "CDLL", return_value=library):
                    with self.assertRaisesRegex(NativeDspError, "required ABI functions"):
                        native_dsp._load_library()


@unittest.skipUnless(any(path.is_file() for path in native_dsp._library_candidates()), "Native DSP DLL is not built")
class NativeParityTests(unittest.TestCase):
    """DLL이 존재하면 실제 C++ 실행으로 스트리밍 수치와 수명을 검증한다."""

    def test_native_runtime_reports_verified_abi(self) -> None:
        """빌드된 DLL은 fallback이 아닌 실제 C++ ABI로 보고되어야 한다."""

        info = native_runtime_info()
        self.assertTrue(info["available"], info)
        self.assertEqual(info["backend"], "cpp")
        self.assertEqual(info["abi_version"], 2)

    def test_float32_direct_pointer_and_caller_pcm_are_preserved(self) -> None:
        """정렬된 float32는 원본 포인터를 사용하고 C++ 정규화는 호출자 PCM을 바꾸지 않는다."""
        source = _signal(2048).astype(np.float32)
        source[:3] = [[np.nan, np.inf], [-np.inf, 2.0], [-2.0, 0.0]]
        snapshot = source.copy()
        source.flags.writeable = False
        engine = NativeSpectrumEngine(44_100, 2)
        reference = PythonSpectrumEngine(44_100, 2)
        try:
            with patch.object(engine._library, "tm_dsp_push_f32", wraps=engine._library.tm_dsp_push_f32) as push32, \
                 patch.object(engine._library, "tm_dsp_push", wraps=engine._library.tm_dsp_push) as push64:
                actual = engine.push(source)
                self.assertEqual(ctypes.cast(push32.call_args.args[1], ctypes.c_void_p).value, source.ctypes.data)
                push32.assert_called_once()
                push64.assert_not_called()
            _assert_frame(self, actual, reference.push(source))
            np.testing.assert_array_equal(source, snapshot)
        finally:
            engine.close()
            reference.close()

    def test_float32_layouts_and_mixed_precision_stream_match_numpy(self) -> None:
        """부분 창 사이 dtype 전환과 endian·정렬·stride의 차이가 같은 수치를 내야 한다."""
        unaligned = np.ndarray((160, 2), dtype=np.float32,
                               buffer=np.zeros(160 * 2 * 4 + 1, dtype=np.uint8), offset=1)
        unaligned[:] = _signal(160)
        opposite_endian = ">f4" if sys.byteorder == "little" else "<f4"
        blocks = (_signal(13).astype(np.float32), _signal(115), _signal(320).astype(np.float32)[::2],
                  unaligned, _signal(256).astype(opposite_endian), _signal(128).astype(np.float16),
                  _signal(128).astype(np.float32)[:, ::-1], np.full((128, 2), 2, dtype=np.int16))
        native = NativeSpectrumEngine(44_100, 2, fft_size=128)
        python = PythonSpectrumEngine(44_100, 2, fft_size=128)
        accepted = 0
        try:
            for source in blocks:
                snapshot = source.copy()
                actual, expected = native.push(source), python.push(source)
                if expected is None:
                    self.assertIsNone(actual)
                else:
                    _assert_frame(self, actual, expected)
                accepted += len(source)
                counters = {"input_frames": accepted, "completed_windows": accepted // 128,
                            "pending_frames": accepted % 128}
                self.assertEqual(native.stream_stats(), counters)
                self.assertEqual(python.stream_stats(), counters)
                np.testing.assert_array_equal(source, snapshot)
        finally:
            native.close()
            python.close()

    def test_stream_counters_reset_query_ownership_and_close(self) -> None:
        """실제 native 누적량은 완성 창 여러 개와 꼬리를 세고 조회 결과를 재사용하지 않는다."""
        engine = NativeSpectrumEngine(44_100, 2, fft_size=128)
        try:
            self.assertEqual(engine.stream_stats(), {"input_frames": 0, "completed_windows": 0, "pending_frames": 0})
            engine.push(_signal(128 * 7 + 19).astype(np.float32))
            expected = {"input_frames": 915, "completed_windows": 7, "pending_frames": 19}
            counters = engine.stream_stats()
            self.assertEqual(counters, expected)
            counters["input_frames"] = -1
            self.assertEqual(engine.stream_stats(), expected)
            with self.assertRaises(ValueError):
                engine.push(np.zeros((32, 1), dtype=np.float32))
            self.assertEqual(engine.stream_stats(), expected)
            engine.reset()
            self.assertEqual(engine.stream_stats(), dict.fromkeys(expected, 0))
            self.assertIsNone(engine.push(_signal(127).astype(np.float32)))
            self.assertEqual(engine.stream_stats()["pending_frames"], 127)
        finally:
            engine.close()
        with self.assertRaises(NativeDspError):
            engine.stream_stats()

    def test_float32_c_abi_rejections_stats_capacity_and_mixed_pushes(self) -> None:
        """새 C 진입점도 모든 사전 거부에서 PCM·이력·카운터·출력 경계를 보존해야 한다."""
        library = native_dsp._load_library()
        handle = library.tm_dsp_create(44_100, 2, 128, 4, 20.0, 20_000.0)
        self.assertTrue(handle)
        count = library.tm_dsp_bin_count(handle)
        waveform, magnitudes, stats = (np.full(length + 2, 123_456.0) for length in (128, count, 3))
        outputs = (waveform, magnitudes, stats)
        pointers = tuple(native_dsp._double_pointer(values) for values in outputs)
        counters = np.full(5, 123_456, dtype=np.uint64)
        counter_pointer = counters.ctypes.data_as(native_dsp._UINT64_POINTER)
        source = _signal(256).astype(np.float32)
        reference = PythonSpectrumEngine(44_100, 2, fft_size=128)
        try:
            for arguments in ((None, counter_pointer, 3), (handle, None, 3), (handle, counter_pointer, 2)):
                self.assertEqual(library.tm_dsp_stream_stats(*arguments), -1)
                np.testing.assert_array_equal(counters, 123_456)
            first = source[:192]
            options = [handle, first.ctypes.data_as(native_dsp._FLOAT_POINTER), len(first),
                       pointers[0], 128, pointers[1], count, pointers[2], 3]
            self.assertEqual(library.tm_dsp_push_f32(*options), 1)
            reference.push(first)
            self.assertEqual(library.tm_dsp_stream_stats(handle, counter_pointer, 3), 3)
            np.testing.assert_array_equal(counters, [192, 1, 64, 123_456, 123_456])
            for values in outputs:
                values[:] = 123_456.0
            options[2] = 64
            for index, value in ((0, None), (1, None), (2, 10_000_001), (3, None), (4, 127),
                                 (5, None), (6, count - 1), (7, None), (8, 2)):
                rejected = options.copy()
                rejected[index] = value
                with self.subTest(index=index, value=value):
                    self.assertEqual(library.tm_dsp_push_f32(*rejected), -1)
                    for values in outputs:
                        np.testing.assert_array_equal(values, 123_456.0)
                    self.assertEqual(library.tm_dsp_stream_stats(handle, counter_pointer, 3), 3)
                    np.testing.assert_array_equal(counters, [192, 1, 64, 123_456, 123_456])
            empty = options.copy()
            empty[1], empty[2] = None, 0
            self.assertEqual(library.tm_dsp_push_f32(*empty), 0)
            for values in outputs:
                np.testing.assert_array_equal(values, 123_456.0)
            # float32로 모은 부분 창을 기존 double 진입점으로 완성해 같은 상태 공유를 검증한다.
            tail = source[192:].astype(np.float64)
            options[1] = native_dsp._double_pointer(tail)
            self.assertEqual(library.tm_dsp_push(*options), 1)
            expected = reference.push(tail)
            actual = SpectrumFrame(waveform[:128].astype(np.float32), expected.frequencies_hz,
                                   magnitudes[:count], *stats[:3])
            _assert_frame(self, actual, expected)
            self.assertEqual(library.tm_dsp_stream_stats(handle, counter_pointer, 3), 3)
            np.testing.assert_array_equal(counters, [256, 2, 0, 123_456, 123_456])
            for values, length in zip(outputs, (128, count, 3)):
                np.testing.assert_array_equal(values[length:], 123_456.0)
            self.assertEqual(library.tm_dsp_reset(handle), 0)
            self.assertEqual(library.tm_dsp_stream_stats(handle, counter_pointer, 3), 3)
            np.testing.assert_array_equal(counters, [0, 0, 0, 123_456, 123_456])
        finally:
            library.tm_dsp_destroy(handle)
            reference.close()

    def test_multichannel_rates_history_and_multiple_windows_match_numpy(self) -> None:
        """여러 설정과 임의 블록 경계에서도 native와 NumPy 결과가 일치해야 한다."""

        for rate, channels, size, history in ((8_000, 1, 128, 1), (44_100, 2, 2_048, 4), (48_000, 3, 1_024, 2), (192_000, 2, 128, 4)):
            with self.subTest(rate=rate, channels=channels, fft_size=size, history=history):
                native = NativeSpectrumEngine(rate, channels, fft_size=size, history_size=history)
                python = PythonSpectrumEngine(rate, channels, fft_size=size, history_size=history)
                source = _signal(size * 9 + 19, channels, rate)
                cursor = 0
                try:
                    for length in (13, size - 13, size * 3 + 7, size - 7, size * 4 + 19):
                        block = source[cursor : cursor + length]
                        cursor += length
                        actual, expected = native.push(block), python.push(block)
                        if expected is None:
                            self.assertIsNone(actual)
                        else:
                            _assert_frame(self, actual, expected)
                finally:
                    native.close()
                    python.close()

    def test_extreme_supported_configurations_and_history_rollover_match(self) -> None:
        """최대 FFT·채널·평활 이력 경계와 순환 이력 교체 이후의 수치를 비교한다."""

        configurations = ((8_000, 32, 128, 64, 70), (192_000, 1, 32_768, 1, 2))
        for rate, channels, size, history, windows in configurations:
            with self.subTest(rate=rate, channels=channels, fft_size=size, history=history):
                options = dict(fft_size=size, history_size=history, min_hz=rate / size, max_hz=rate)
                native = NativeSpectrumEngine(rate, channels, **options)
                python = PythonSpectrumEngine(rate, channels, **options)
                try:
                    source = _signal(size, channels, rate)
                    for index in range(windows):
                        block = source * ((index % 7) + 1) / 7.0
                        actual, expected = native.push(block), python.push(block)
                        _assert_frame(self, actual, expected)
                        self.assertEqual(actual.frequencies_hz[-1], rate / 2.0)
                finally:
                    native.close()
                    python.close()

    def test_dc_nyquist_clipping_and_noncontiguous_pcm_match(self) -> None:
        """DC 제거·Nyquist 보정·클리핑·비연속 배열을 같은 의미로 처리해야 한다."""

        size, rate = 128, 8_000
        options = dict(fft_size=size, history_size=4, min_hz=3_999.0, max_hz=8_001.0)
        native = NativeSpectrumEngine(rate, 2, **options)
        python = PythonSpectrumEngine(rate, 2, **options)
        nyquist = np.tile((1.0, -1.0), size // 2)
        wide = np.column_stack((nyquist * 0.4, nyquist, nyquist * -0.2, nyquist))
        try:
            for block in (wide[:, ::2], np.ones((size, 2)), np.full((size, 2), -2.0),
                          _signal(size, 2, rate)[::-1], np.zeros((size, 2))):
                actual, expected = native.push(block), python.push(block)
                _assert_frame(self, actual, expected)
                np.testing.assert_array_equal(actual.frequencies_hz, [4_000.0])
        finally:
            native.close()
            python.close()

    def test_c_abi_invalid_creation_null_handles_and_frequency_capacity(self) -> None:
        """직접 C ABI에서도 설정 상한·NULL 및 주파수 출력 용량을 안전하게 검사해야 한다."""

        library = native_dsp._load_library()
        self.assertEqual(library.tm_dsp_bin_count(None), 0)
        self.assertEqual(library.tm_dsp_reset(None), -1)
        self.assertEqual(library.tm_dsp_frequencies(None, None, 0), -1)
        library.tm_dsp_destroy(None)
        valid = [44_100, 2, 128, 4, 20.0, 20_000.0]
        bad_values = {0: (0, 7_999, 192_001, 0xFFFFFFFF), 1: (0, 33, 0xFFFFFFFF),
                      2: (0, 127, 129, 65_536, 0xFFFFFFFF), 3: (0, 65, 0xFFFFFFFF),
                      4: (0.0, -1.0, math.nan, math.inf, 21_000.0),
                      5: (0.0, 20.0, math.nan, math.inf)}
        for index, values in bad_values.items():
            for value in values:
                arguments = valid.copy()
                arguments[index] = value
                with self.subTest(index=index, value=value):
                    handle = library.tm_dsp_create(*arguments)
                    try:
                        self.assertFalse(handle)
                    finally:
                        if handle:
                            library.tm_dsp_destroy(handle)
        self.assertFalse(library.tm_dsp_create(44_100, 2, 128, 4, 1_001.0, 1_002.0))
        handle = library.tm_dsp_create(*valid)
        self.assertTrue(handle)
        try:
            count = library.tm_dsp_bin_count(handle)
            frequencies = np.full(count + 2, 123_456.0)
            pointer = native_dsp._double_pointer(frequencies)
            self.assertEqual(library.tm_dsp_frequencies(handle, None, count), -1)
            self.assertEqual(library.tm_dsp_frequencies(handle, pointer, count - 1), -1)
            np.testing.assert_array_equal(frequencies, 123_456.0)
            self.assertEqual(library.tm_dsp_frequencies(handle, pointer, count), count)
            np.testing.assert_array_equal(frequencies[count:], 123_456.0)
            expected = np.fft.rfftfreq(128, 1.0 / 44_100)
            expected = expected[(expected >= 20.0) & (expected <= 20_000.0)]
            np.testing.assert_allclose(frequencies[:count], expected, atol=1e-10)
        finally:
            library.tm_dsp_destroy(handle)

    def test_c_abi_rejections_do_not_mutate_pending_history_or_outputs(self) -> None:
        """부족한 용량·NULL·프레임 상한 오류는 누적 입력과 이력 및 출력 경계를 보존해야 한다."""

        library = native_dsp._load_library()
        handle = library.tm_dsp_create(44_100, 2, 128, 4, 20.0, 20_000.0)
        self.assertTrue(handle)
        count = library.tm_dsp_bin_count(handle)
        waveform, magnitudes, stats = (np.full(length + 2, 123_456.0) for length in (128, count, 3))
        outputs = (waveform, magnitudes, stats)
        pointers = tuple(native_dsp._double_pointer(values) for values in outputs)
        source = _signal(256)
        options = [handle, native_dsp._double_pointer(source), 64,
                   pointers[0], 128, pointers[1], count, pointers[2], 3]
        smoother = SpectrumSmoother(4)
        try:
            # 먼저 유효 이력 하나와 부분 입력을 넣어 오류 이후 둘 다 남는지 확인한다.
            first = source[:128].copy()
            initial = options.copy()
            initial[1], initial[2] = native_dsp._double_pointer(first), 128
            self.assertEqual(library.tm_dsp_push(*initial), 1)
            smoother.push(analyze_spectrum_frame(first, 44_100, fft_size=128))
            pending = source[128:192].copy()
            options[1] = native_dsp._double_pointer(pending)
            self.assertEqual(library.tm_dsp_push(*options), 0)
            for values in outputs:
                values[:] = 123_456.0
            invalid = ((0, None), (1, None), (2, 10_000_001), (3, None), (4, 127),
                       (5, None), (6, count - 1), (7, None), (8, 2))
            for index, value in invalid:
                rejected = options.copy()
                rejected[index] = value
                with self.subTest(index=index, value=value):
                    self.assertEqual(library.tm_dsp_push(*rejected), -1)
                    for values in outputs:
                        np.testing.assert_array_equal(values, 123_456.0)
            empty = options.copy()
            empty[1], empty[2] = None, 0
            self.assertEqual(library.tm_dsp_push(*empty), 0)
            for values in outputs:
                np.testing.assert_array_equal(values, 123_456.0)
            tail = source[192:].copy()
            options[1] = native_dsp._double_pointer(tail)
            self.assertEqual(library.tm_dsp_push(*options), 1)
            expected = smoother.push(analyze_spectrum_frame(source[128:], 44_100, fft_size=128))
            actual = SpectrumFrame(waveform[:128].astype(np.float32), expected.frequencies_hz,
                                   magnitudes[:count], *stats[:3])
            _assert_frame(self, actual, expected)
            for values, length in zip(outputs, (128, count, 3)):
                np.testing.assert_array_equal(values[length:], 123_456.0)
        finally:
            library.tm_dsp_destroy(handle)

    def test_antiphase_silence_floor_and_nonfinite_normalization_match(self) -> None:
        """역상·무음·표시 하한 및 비유한 PCM 처리는 기존 DSP와 같아야 한다."""

        native = NativeSpectrumEngine(48_000, 2)
        python = PythonSpectrumEngine(48_000, 2)
        mono = 0.5 * np.sin(2 * np.pi * 64 * np.arange(2_048) / 2_048)
        antiphase = np.column_stack((mono, -mono))
        dirty = antiphase.copy()
        dirty[1] = (np.nan, np.inf)
        dirty[2] = (-np.inf, 2.0)
        try:
            for block in (antiphase, antiphase * 1e-7, np.zeros_like(antiphase), dirty, antiphase * 1e-6, np.zeros_like(antiphase)):
                _assert_frame(self, native.push(block), python.push(block))
        finally:
            native.close()
            python.close()

    def test_bin_sine_has_calibrated_levels_and_crest(self) -> None:
        """정확한 FFT bin 사인파의 RMS·Peak 및 약 3.01 dB 크레스트를 보존해야 한다."""

        engine = NativeSpectrumEngine(48_000, 1)
        mono = 0.5 * np.sin(2 * np.pi * 64 * np.arange(2_048) / 2_048)
        try:
            frame = engine.push(mono)
            self.assertAlmostEqual(frame.peak_dbfs, 20 * math.log10(0.5), delta=1e-9)
            self.assertAlmostEqual(frame.peak_dbfs - frame.rms_dbfs, 10 * math.log10(2), delta=1e-9)
            self.assertAlmostEqual(frame.frequencies_hz[np.argmax(frame.magnitudes_dbfs)], 1_500.0, delta=1e-9)
        finally:
            engine.close()

    def test_output_ownership_partial_copy_and_reset(self) -> None:
        """반환 프레임과 부분 PCM은 후속 호출·입력 수정·reset에 소급 변경되지 않아야 한다."""

        engine = NativeSpectrumEngine(44_100, 2, fft_size=128)
        source = _signal(128)
        expected = SpectrumSmoother().push(analyze_spectrum_frame(source, 44_100, fft_size=128))
        first = source[:64].copy()
        try:
            self.assertIsNone(engine.push(first))
            first[:] = 0.0
            result = engine.push(source[64:])
            _assert_frame(self, result, expected)
            result.waveform[:] = -0.75
            result.magnitudes_dbfs[:] = 42.0
            engine.push(source[:19])
            engine.reset()
            _assert_frame(self, engine.push(source), expected)
            np.testing.assert_array_equal(result.waveform, -0.75)
            np.testing.assert_array_equal(result.magnitudes_dbfs, 42.0)
        finally:
            engine.close()

    def test_invalid_input_does_not_change_state_and_close_is_safe(self) -> None:
        """입력 검증 실패는 누적 상태를 보존하고 닫힌 컨텍스트는 다시 진입하지 않아야 한다."""

        engine = NativeSpectrumEngine(44_100, 2, fft_size=128)
        source = _signal(128)
        engine.push(source[:64])
        with self.assertRaises(ValueError):
            engine.push(np.zeros((64, 1)))
        expected = SpectrumSmoother().push(analyze_spectrum_frame(source, 44_100, fft_size=128))
        _assert_frame(self, engine.push(source[64:]), expected)
        engine.close()
        engine.close()
        with self.assertRaises(NativeDspError):
            engine.push(source)
        with self.assertRaises(NativeDspError):
            engine.reset()

    def test_concurrent_close_and_push_are_serialized(self) -> None:
        """ctypes가 GIL을 해제해도 close와 push가 같은 native handle에서 경합하면 안 된다."""

        engine = NativeSpectrumEngine(44_100, 2, fft_size=128)

        def feed() -> None:
            """종료 시점까지 짧은 PCM을 공급하고 명시적인 닫힘 오류만 허용한다."""

            try:
                for _ in range(100):
                    engine.push(_signal(128))
            except NativeDspError as exc:
                self.assertIn("closed", str(exc))

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = (executor.submit(feed), executor.submit(engine.close))
            for future in futures:
                future.result(timeout=10)
        engine.close()


if __name__ == "__main__":
    unittest.main()
