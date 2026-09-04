"""실시간 스펙트럼 DSP와 유한 롤링 평활화의 결정론적 회귀 테스트."""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

import numpy as np


MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from spectrum import DBFS_FLOOR, SpectrumFrame, SpectrumSmoother, analyze_spectrum_frame  # noqa: E402


SAMPLE_RATE = 48_000
FFT_SIZE = 2_048


def _bin_sine(bin_index: int, amplitude: float = 0.5, length: int = FFT_SIZE) -> np.ndarray:
    """FFT bin 중심에 정확히 놓이는 위상 0의 결정론적 사인파를 만든다."""

    indexes = np.arange(length, dtype=np.float64)
    return (amplitude * np.sin(2.0 * np.pi * bin_index * indexes / FFT_SIZE)).astype(np.float32)


def _manual_frame(
    frequencies: tuple[float, ...],
    powers: tuple[float, ...],
    *,
    waveform_value: float,
    rms_dbfs: float,
    peak_dbfs: float,
) -> SpectrumFrame:
    """평활화 수치 계약을 직접 검증할 작은 스펙트럼 프레임을 만든다."""

    frequency_array = np.asarray(frequencies, dtype=np.float64)
    power_array = np.asarray(powers, dtype=np.float64)
    centroid = float(np.dot(frequency_array, power_array) / np.sum(power_array))
    return SpectrumFrame(
        waveform=np.full(8, waveform_value, dtype=np.float32),
        frequencies_hz=frequency_array,
        magnitudes_dbfs=10.0 * np.log10(power_array),
        rms_dbfs=rms_dbfs,
        peak_dbfs=peak_dbfs,
        spectral_centroid_hz=centroid,
    )


class SpectrumAnalysisTests(unittest.TestCase):
    """합성 PCM 한 프레임의 FFT, 레벨, 입력 정규화 계약을 검증한다."""

    def test_bin_centered_sine_has_calibrated_frequency_and_levels(self) -> None:
        """정확한 bin 사인파의 주파수와 peak·RMS·스펙트럼 dBFS가 보정돼야 한다."""

        bin_index = 64
        expected_frequency = SAMPLE_RATE * bin_index / FFT_SIZE
        mono = _bin_sine(bin_index, 0.5)
        stereo = np.column_stack((mono, mono))

        result = analyze_spectrum_frame(stereo, SAMPLE_RATE, fft_size=FFT_SIZE)
        peak_index = int(np.argmax(result.magnitudes_dbfs))

        self.assertAlmostEqual(result.frequencies_hz[peak_index], expected_frequency, places=12)
        self.assertAlmostEqual(result.magnitudes_dbfs[peak_index], 20.0 * math.log10(0.5), delta=0.03)
        self.assertAlmostEqual(result.peak_dbfs, 20.0 * math.log10(0.5), delta=0.001)
        self.assertAlmostEqual(result.rms_dbfs, 20.0 * math.log10(0.5 / math.sqrt(2.0)), delta=0.001)
        self.assertAlmostEqual(result.spectral_centroid_hz, expected_frequency, delta=SAMPLE_RATE / FFT_SIZE)
        self.assertEqual(result.waveform.shape, (FFT_SIZE,))
        self.assertTrue(np.all(np.diff(result.frequencies_hz) > 0.0))
        self.assertTrue(np.all(np.isfinite(result.magnitudes_dbfs)))

    def test_two_tones_keep_their_six_decibel_level_difference(self) -> None:
        """진폭이 두 배인 bin 중심 성분은 약 6.02 dB 더 크게 표시돼야 한다."""

        quiet_bin = 16
        loud_bin = 128
        mono = _bin_sine(quiet_bin, 0.25) + _bin_sine(loud_bin, 0.5)
        result = analyze_spectrum_frame(mono, SAMPLE_RATE, fft_size=FFT_SIZE)
        quiet_frequency = SAMPLE_RATE * quiet_bin / FFT_SIZE
        loud_frequency = SAMPLE_RATE * loud_bin / FFT_SIZE
        quiet_index = int(np.flatnonzero(result.frequencies_hz == quiet_frequency)[0])
        loud_index = int(np.flatnonzero(result.frequencies_hz == loud_frequency)[0])

        self.assertAlmostEqual(
            result.magnitudes_dbfs[loud_index] - result.magnitudes_dbfs[quiet_index],
            20.0 * math.log10(2.0),
            delta=0.05,
        )
        self.assertEqual(int(np.argmax(result.magnitudes_dbfs)), loud_index)

    def test_antiphase_stereo_does_not_cancel_the_power_spectrum(self) -> None:
        """좌우 역상은 표시 파형이 상쇄돼도 채널 파워 FFT에서는 사라지면 안 된다."""

        bin_index = 80
        mono = _bin_sine(bin_index, 0.5)
        antiphase = np.column_stack((mono, -mono))

        result = analyze_spectrum_frame(antiphase, SAMPLE_RATE, fft_size=FFT_SIZE)
        peak_index = int(np.argmax(result.magnitudes_dbfs))

        np.testing.assert_allclose(result.waveform, 0.0, atol=1e-7, rtol=0.0)
        self.assertAlmostEqual(result.frequencies_hz[peak_index], SAMPLE_RATE * bin_index / FFT_SIZE, places=12)
        self.assertAlmostEqual(result.magnitudes_dbfs[peak_index], 20.0 * math.log10(0.5), delta=0.03)

    def test_short_and_long_inputs_use_left_padding_and_latest_samples(self) -> None:
        """짧은 블록은 왼쪽을 0으로 채우고 긴 블록은 마지막 FFT 구간만 사용해야 한다."""

        short = np.full((256, 2), 0.25, dtype=np.float32)
        padded = analyze_spectrum_frame(short, SAMPLE_RATE, fft_size=FFT_SIZE)
        np.testing.assert_array_equal(padded.waveform[:-256], np.zeros(FFT_SIZE - 256, dtype=np.float32))
        np.testing.assert_allclose(padded.waveform[-256:], 0.25, atol=0.0, rtol=0.0)
        self.assertAlmostEqual(padded.rms_dbfs, 20.0 * math.log10(0.25), delta=0.001)
        self.assertAlmostEqual(padded.peak_dbfs, 20.0 * math.log10(0.25), delta=0.001)

        early = _bin_sine(16, 0.8)
        latest = _bin_sine(96, 0.4)
        long_input = np.concatenate((early, latest))
        latest_only = analyze_spectrum_frame(long_input, SAMPLE_RATE, fft_size=FFT_SIZE)
        peak_index = int(np.argmax(latest_only.magnitudes_dbfs))
        self.assertAlmostEqual(latest_only.frequencies_hz[peak_index], SAMPLE_RATE * 96 / FFT_SIZE, places=12)
        np.testing.assert_allclose(latest_only.waveform, latest, atol=0.0, rtol=0.0)

    def test_silence_and_nonfinite_samples_always_produce_finite_output(self) -> None:
        """무음은 유한한 표시 하한을 사용하고 NaN·무한대 입력은 안전하게 정리해야 한다."""

        silence = analyze_spectrum_frame(np.zeros((FFT_SIZE, 2), dtype=np.float32), SAMPLE_RATE)
        self.assertTrue(np.all(silence.magnitudes_dbfs == DBFS_FLOOR))
        self.assertEqual(silence.rms_dbfs, DBFS_FLOOR)
        self.assertEqual(silence.peak_dbfs, DBFS_FLOOR)
        self.assertEqual(silence.spectral_centroid_hz, 0.0)

        dirty = np.zeros((FFT_SIZE, 2), dtype=np.float32)
        dirty[10] = (np.nan, np.inf)
        dirty[11] = (-np.inf, np.nan)
        cleaned = analyze_spectrum_frame(dirty, SAMPLE_RATE)
        self.assertTrue(np.all(np.isfinite(cleaned.waveform)))
        self.assertTrue(np.all(np.isfinite(cleaned.magnitudes_dbfs)))
        self.assertTrue(np.isfinite(cleaned.rms_dbfs))
        self.assertTrue(np.isfinite(cleaned.peak_dbfs))
        self.assertTrue(np.isfinite(cleaned.spectral_centroid_hz))
        self.assertLessEqual(float(np.max(np.abs(cleaned.waveform))), 1.0)

    def test_frequency_range_is_inclusive_and_capped_at_nyquist(self) -> None:
        """선택 주파수의 양 끝을 포함하되 최대값은 나이퀴스트를 넘지 않아야 한다."""

        bin_width = SAMPLE_RATE / FFT_SIZE
        result = analyze_spectrum_frame(
            _bin_sine(64),
            SAMPLE_RATE,
            fft_size=FFT_SIZE,
            min_hz=bin_width * 10,
            max_hz=SAMPLE_RATE,
        )
        self.assertEqual(result.frequencies_hz[0], bin_width * 10)
        self.assertEqual(result.frequencies_hz[-1], SAMPLE_RATE / 2)

    def test_invalid_pcm_and_analysis_settings_are_rejected(self) -> None:
        """빈 입력·잘못된 차원·복소 PCM과 유효하지 않은 분석 설정은 거부해야 한다."""

        valid = np.zeros((FFT_SIZE, 2), dtype=np.float32)
        cases = (
            ("empty", lambda: analyze_spectrum_frame(np.array([], dtype=np.float32), SAMPLE_RATE)),
            ("rank", lambda: analyze_spectrum_frame(np.zeros((8, 2, 1), dtype=np.float32), SAMPLE_RATE)),
            ("channels", lambda: analyze_spectrum_frame(np.zeros((8, 0), dtype=np.float32), SAMPLE_RATE)),
            ("complex", lambda: analyze_spectrum_frame(np.ones(8, dtype=np.complex64), SAMPLE_RATE)),
            ("sample_rate", lambda: analyze_spectrum_frame(valid, 4_000)),
            ("fft_size", lambda: analyze_spectrum_frame(valid, SAMPLE_RATE, fft_size=1)),
            ("min_hz", lambda: analyze_spectrum_frame(valid, SAMPLE_RATE, min_hz=-1.0)),
            ("dc_range", lambda: analyze_spectrum_frame(valid, SAMPLE_RATE, min_hz=0.0)),
            ("range", lambda: analyze_spectrum_frame(valid, SAMPLE_RATE, min_hz=1_000.0, max_hz=999.0)),
            ("nyquist", lambda: analyze_spectrum_frame(valid, SAMPLE_RATE, min_hz=25_000.0, max_hz=30_000.0)),
        )
        for label, operation in cases:
            with self.subTest(case=label), self.assertRaises(ValueError):
                operation()


class SpectrumSmootherTests(unittest.TestCase):
    """스펙트럼 평활화의 선형 파워 평균, 유한 이력과 초기화를 검증한다."""

    def test_two_frames_are_averaged_in_linear_power(self) -> None:
        """dB 산술 평균이 아니라 선형 파워와 RMS 제곱 평균을 사용해야 한다."""

        first = _manual_frame((100.0, 1_000.0), (0.01, 0.0001), waveform_value=0.1, rms_dbfs=-20.0, peak_dbfs=-6.0)
        second = _manual_frame((100.0, 1_000.0), (0.0001, 0.01), waveform_value=0.2, rms_dbfs=-40.0, peak_dbfs=-12.0)
        smoother = SpectrumSmoother(history_size=4)
        smoother.push(first)
        result = smoother.push(second)
        expected_power = np.array((0.00505, 0.00505), dtype=np.float64)

        np.testing.assert_allclose(result.magnitudes_dbfs, 10.0 * np.log10(expected_power), atol=1e-12, rtol=0.0)
        self.assertAlmostEqual(result.rms_dbfs, 10.0 * math.log10(0.00505), places=12)
        self.assertEqual(result.peak_dbfs, -6.0)
        self.assertAlmostEqual(result.spectral_centroid_hz, 550.0, places=12)
        np.testing.assert_array_equal(result.waveform, second.waveform)

    def test_history_is_bounded_and_evicts_the_oldest_frame(self) -> None:
        """설정된 프레임 수를 넘으면 가장 오래된 파워는 평균에서 빠져야 한다."""

        first = _manual_frame((100.0, 200.0), (1.0, 0.01), waveform_value=0.1, rms_dbfs=-10.0, peak_dbfs=-3.0)
        second = _manual_frame((100.0, 200.0), (0.01, 1.0), waveform_value=0.2, rms_dbfs=-20.0, peak_dbfs=-6.0)
        third = _manual_frame((100.0, 200.0), (0.25, 0.25), waveform_value=0.3, rms_dbfs=-30.0, peak_dbfs=-9.0)
        smoother = SpectrumSmoother(history_size=2)
        smoother.push(first)
        smoother.push(second)
        result = smoother.push(third)

        expected_power = np.array(((0.01 + 0.25) / 2.0, (1.0 + 0.25) / 2.0))
        np.testing.assert_allclose(result.magnitudes_dbfs, 10.0 * np.log10(expected_power), atol=1e-12, rtol=0.0)
        self.assertEqual(result.peak_dbfs, -6.0)
        np.testing.assert_array_equal(result.waveform, third.waveform)

    def test_reset_and_frequency_grid_change_clear_history(self) -> None:
        """명시적 초기화와 서로 다른 주파수 격자는 이전 프레임을 섞지 않아야 한다."""

        first = _manual_frame((100.0, 200.0), (1.0, 0.01), waveform_value=0.1, rms_dbfs=-10.0, peak_dbfs=-3.0)
        second = _manual_frame((100.0, 200.0), (0.04, 0.16), waveform_value=0.2, rms_dbfs=-20.0, peak_dbfs=-6.0)
        changed_grid = _manual_frame((100.0, 300.0), (0.09, 0.25), waveform_value=0.3, rms_dbfs=-30.0, peak_dbfs=-9.0)
        smoother = SpectrumSmoother(history_size=4)

        smoother.push(first)
        smoother.reset()
        reset_result = smoother.push(second)
        np.testing.assert_allclose(reset_result.magnitudes_dbfs, second.magnitudes_dbfs, atol=1e-12, rtol=0.0)
        self.assertEqual(reset_result.rms_dbfs, second.rms_dbfs)
        self.assertEqual(reset_result.peak_dbfs, second.peak_dbfs)

        changed_result = smoother.push(changed_grid)
        np.testing.assert_allclose(changed_result.magnitudes_dbfs, changed_grid.magnitudes_dbfs, atol=1e-12, rtol=0.0)
        self.assertEqual(changed_result.rms_dbfs, changed_grid.rms_dbfs)
        self.assertEqual(changed_result.peak_dbfs, changed_grid.peak_dbfs)

    def test_history_copies_frames_and_rejects_invalid_values(self) -> None:
        """호출자 배열 변경은 이력에 소급되지 않고 잘못된 프레임은 거부돼야 한다."""

        first = _manual_frame((100.0, 200.0), (1.0, 0.01), waveform_value=0.1, rms_dbfs=-10.0, peak_dbfs=-3.0)
        smoother = SpectrumSmoother(history_size=2)
        smoother.push(first)
        first.magnitudes_dbfs[:] = DBFS_FLOOR
        second = _manual_frame((100.0, 200.0), (0.01, 1.0), waveform_value=0.2, rms_dbfs=-20.0, peak_dbfs=-6.0)
        result = smoother.push(second)
        expected_power = (np.array((1.0, 0.01)) + np.array((0.01, 1.0))) / 2.0
        np.testing.assert_allclose(result.magnitudes_dbfs, 10.0 * np.log10(expected_power), atol=1e-12, rtol=0.0)

        invalid = SpectrumFrame(
            waveform=np.zeros(8),
            frequencies_hz=np.array((100.0, 200.0)),
            magnitudes_dbfs=np.array((-20.0, np.nan)),
            rms_dbfs=-20.0,
            peak_dbfs=-10.0,
            spectral_centroid_hz=150.0,
        )
        with self.assertRaises(ValueError):
            smoother.push(invalid)
        with self.assertRaises(ValueError):
            SpectrumSmoother(history_size=0)


if __name__ == "__main__":
    unittest.main()
