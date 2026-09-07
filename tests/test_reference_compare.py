"""레벨 정규화 기준 음색 프로필과 실시간 차이 계산의 회귀 테스트."""

from __future__ import annotations

import json
import math
import sys
import unittest
from pathlib import Path

import numpy as np


MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from reference_compare import (  # noqa: E402
    BANDS,
    MAX_REFERENCE_FRAMES,
    MIN_INPUT_RMS_DBFS,
    PROFILE_BIN_COUNT,
    REFERENCE_COMPARE_SCHEMA,
    REFERENCE_PROFILE_SCHEMA,
    ReferenceCompareError,
    build_reference_profile,
    compare_live_frame,
)
from spectrum import SpectrumFrame, analyze_spectrum_frame  # noqa: E402


SAMPLE_RATE = 48_000
FFT_SIZE = 2_048


def _tone(frequencies_hz: tuple[float, ...], amplitudes: tuple[float, ...], length: int, rate: int) -> np.ndarray:
    """지정 주파수와 진폭을 합친 결정론적 합성 파형을 만든다."""

    indexes = np.arange(length, dtype=np.float64)
    result = np.zeros(length, dtype=np.float64)
    for frequency_hz, amplitude in zip(frequencies_hz, amplitudes, strict=True):
        result += amplitude * np.sin(2.0 * np.pi * frequency_hz * indexes / rate)
    return result.astype(np.float32)


def _manual_frame(frequencies_hz: np.ndarray, relative_power: np.ndarray, gain_db: float = -30.0) -> SpectrumFrame:
    """임의 주파수 격자와 매끄러운 파워 분포를 공개 SpectrumFrame으로 포장한다."""

    levels = 10.0 * np.log10(relative_power) + gain_db
    return SpectrumFrame(
        waveform=np.zeros(FFT_SIZE, dtype=np.float32),
        frequencies_hz=frequencies_hz.astype(np.float64),
        magnitudes_dbfs=levels.astype(np.float64),
        rms_dbfs=-24.0 + gain_db,
        peak_dbfs=-18.0 + gain_db,
        spectral_centroid_hz=float(np.sum(frequencies_hz * relative_power) / np.sum(relative_power)),
    )


class ReferenceProfileTests(unittest.TestCase):
    """오프라인 프로필의 격자, 정규화, 채널 파워 및 입력 검증을 확인한다."""

    def test_profile_is_json_ready_finite_and_bounded(self) -> None:
        """긴 PCM도 384개 이하 프레임으로 고정 길이 JSON 프로필을 만들어야 한다."""

        mono = _tone((187.5, 1_500.0, 6_000.0), (0.35, 0.2, 0.08), SAMPLE_RATE * 20, SAMPLE_RATE)
        profile = build_reference_profile(np.column_stack((mono, mono)), SAMPLE_RATE)

        self.assertEqual(profile["schema"], REFERENCE_PROFILE_SCHEMA)
        self.assertEqual(profile["sampled_frames"], MAX_REFERENCE_FRAMES)
        self.assertLessEqual(profile["active_frames"], MAX_REFERENCE_FRAMES)
        self.assertEqual(len(profile["frequencies_hz"]), PROFILE_BIN_COUNT)
        self.assertEqual(len(profile["frequency_edges_hz"]), PROFILE_BIN_COUNT + 1)
        self.assertEqual(len(profile["normalized_power"]), PROFILE_BIN_COUNT)
        self.assertEqual(len(profile["bands"]), len(BANDS))
        self.assertAlmostEqual(sum(profile["normalized_power"]), 1.0, places=12)
        json.dumps(profile, allow_nan=False)
        self.assertTrue(np.all(np.isfinite(np.asarray(profile["relative_db"]))))

    def test_antiphase_stereo_preserves_the_reference_power(self) -> None:
        """좌우 역상은 mono 합에서 상쇄되더라도 채널별 파워 프로필에서 보존돼야 한다."""

        mono = _tone((750.0, 3_000.0), (0.4, 0.15), FFT_SIZE * 8, SAMPLE_RATE)
        in_phase = build_reference_profile(np.column_stack((mono, mono)), SAMPLE_RATE)
        antiphase = build_reference_profile(np.column_stack((mono, -mono)), SAMPLE_RATE)

        np.testing.assert_allclose(antiphase["normalized_power"], in_phase["normalized_power"], atol=1e-14, rtol=0.0)
        self.assertGreater(max(antiphase["relative_db"]), -20.0)

    def test_reference_gain_changes_do_not_change_tone_shape(self) -> None:
        """같은 파형의 전체 입력 게인만 달라지면 정규화 프로필은 동일해야 한다."""

        mono = _tone((375.0, 2_250.0), (0.32, 0.11), FFT_SIZE * 10, SAMPLE_RATE)
        quiet = build_reference_profile(mono * 0.2, SAMPLE_RATE)
        loud = build_reference_profile(mono * 0.8, SAMPLE_RATE)

        np.testing.assert_allclose(quiet["normalized_power"], loud["normalized_power"], atol=1e-13, rtol=1e-12)

    def test_silence_nonfinite_and_invalid_settings_are_rejected(self) -> None:
        """무음·비유한 PCM과 허용 범위를 벗어난 설정은 안전한 공개 오류를 내야 한다."""

        valid = np.ones((FFT_SIZE, 2), dtype=np.float32) * 0.1
        dirty = valid.copy()
        dirty[0, 0] = np.nan
        cases = (
            lambda: build_reference_profile(np.zeros((FFT_SIZE, 2), dtype=np.float32), SAMPLE_RATE),
            lambda: build_reference_profile(dirty, SAMPLE_RATE),
            lambda: build_reference_profile(np.array([], dtype=np.float32), SAMPLE_RATE),
            lambda: build_reference_profile(valid, 4_000),
            lambda: build_reference_profile(valid, SAMPLE_RATE, fft_size=64),
            lambda: build_reference_profile(valid, SAMPLE_RATE, max_frames=MAX_REFERENCE_FRAMES + 1),
        )
        for operation in cases:
            with self.subTest(operation=operation), self.assertRaises(ReferenceCompareError):
                operation()

    def test_reference_quiet_gate_uses_practical_rms_threshold(self) -> None:
        """-75 dBFS 이하의 기준 잡음은 거부하고 그 위의 유효 신호는 분석해야 한다."""

        waveform = _tone((750.0,), (1.0,), FFT_SIZE, SAMPLE_RATE).astype(np.float64)
        waveform /= np.sqrt(np.mean(waveform**2))
        with self.assertRaisesRegex(ReferenceCompareError, "-75 dBFS"):
            build_reference_profile(waveform * 10.0 ** ((MIN_INPUT_RMS_DBFS - 1.0) / 20.0), SAMPLE_RATE)
        profile = build_reference_profile(waveform * 10.0 ** ((MIN_INPUT_RMS_DBFS + 1.0) / 20.0), SAMPLE_RATE)
        self.assertEqual(profile["minimum_rms_dbfs"], MIN_INPUT_RMS_DBFS)
        self.assertAlmostEqual(sum(profile["normalized_power"]), 1.0, places=12)

    def test_low_rate_profile_marks_unavailable_bands_without_reversed_ranges(self) -> None:
        """8 kHz 표본률에서 Treble/Air는 뒤집힌 범위 없이 비가용으로 기록해야 한다."""

        profile = build_reference_profile(_tone((750.0,), (0.3,), FFT_SIZE, 8_000), 8_000)
        for row in profile["bands"]:
            self.assertGreaterEqual(row["high_hz"], row["low_hz"])
            self.assertEqual(row["available"], row["id"] not in ("treble", "air"))


class LiveComparisonTests(unittest.TestCase):
    """실시간 공통 격자 투영, 게인 불변 차이와 오류 schema를 검증한다."""

    def setUp(self) -> None:
        """각 테스트에 동일한 두 톤 기준 프로필을 준비한다."""

        reference = _tone((750.0, 3_000.0), (0.35, 0.12), FFT_SIZE * 12, SAMPLE_RATE)
        self.profile = build_reference_profile(reference, SAMPLE_RATE)

    def test_live_gain_changes_leave_comparison_unchanged(self) -> None:
        """현재 입력의 전체 게인만 바뀌면 모든 상대 곡선과 대역 차이는 같아야 한다."""

        mono = _tone((750.0, 3_000.0), (0.35, 0.12), FFT_SIZE, SAMPLE_RATE)
        quiet = compare_live_frame(self.profile, analyze_spectrum_frame(mono * 0.2, SAMPLE_RATE))
        loud = compare_live_frame(self.profile, analyze_spectrum_frame(mono * 0.8, SAMPLE_RATE))

        np.testing.assert_allclose(quiet["current_relative_db"], loud["current_relative_db"], atol=1e-10, rtol=0.0)
        np.testing.assert_allclose(quiet["delta_db"], loud["delta_db"], atol=1e-10, rtol=0.0)
        np.testing.assert_allclose(
            [row["delta_db"] for row in quiet["bands"]],
            [row["delta_db"] for row in loud["bands"]],
            atol=1e-10,
            rtol=0.0,
        )
        self.assertEqual(quiet["schema"], REFERENCE_COMPARE_SCHEMA)
        self.assertEqual(len(quiet["bands"]), 6)
        json.dumps(quiet, allow_nan=False)

    def test_identical_pcm_has_zero_curve_and_band_deltas_at_supported_rates(self) -> None:
        """같은 PCM의 양쪽 경로는 FFT 누설을 포함한 전체 차이 곡선에서 일치해야 한다."""

        for rate in (8_000, 22_050, 44_100, 48_000):
            for tones in ((750.0, 3_000.0), (752.3, 2_989.7)):
                with self.subTest(rate=rate, tones=tones):
                    mono = _tone(tones, (0.35, 0.12), FFT_SIZE, rate)
                    profile = build_reference_profile(mono, rate)
                    result = compare_live_frame(profile, analyze_spectrum_frame(mono, rate))
                    np.testing.assert_allclose(result["delta_db"], 0.0, atol=1e-7, rtol=0.0)
                    np.testing.assert_allclose(
                        [row["delta_db"] for row in result["bands"]], 0.0, atol=1e-7, rtol=0.0
                    )
                    for row in result["bands"]:
                        self.assertGreaterEqual(row["high_hz"], row["low_hz"])
                    if rate == 8_000:
                        self.assertFalse(result["bands"][-1]["available"])
                        self.assertFalse(result["bands"][-2]["available"])

    def test_band_delta_sign_and_value_follow_normalized_energy_ratio(self) -> None:
        """한 대역의 진폭을 두 배로 바꾸면 정규화 에너지 비율의 dB와 부호가 맞아야 한다."""
        reference = _tone((750.0, 3_000.0), (0.2, 0.2), FFT_SIZE, SAMPLE_RATE)
        current = _tone((750.0, 3_000.0), (0.4, 0.2), FFT_SIZE, SAMPLE_RATE)
        result = compare_live_frame(build_reference_profile(reference, SAMPLE_RATE), analyze_spectrum_frame(current, SAMPLE_RATE))
        bands = {row["id"]: row for row in result["bands"]}
        self.assertAlmostEqual(bands["mid"]["delta_db"], 10.0 * math.log10(0.8 / 0.5), delta=0.001)
        self.assertAlmostEqual(bands["presence"]["delta_db"], 10.0 * math.log10(0.2 / 0.5), delta=0.001)

    def test_nyquist_and_antiphase_pcm_use_the_same_channel_power_convention(self) -> None:
        """나이퀴스트 성분과 좌우 역상이 있어도 양쪽 단측 FFT 보정은 같아야 한다."""

        rate = 8_000
        mono = _tone((752.3,), (0.3,), FFT_SIZE, rate)
        mono += 0.12 * np.power(-1.0, np.arange(FFT_SIZE))
        stereo = np.column_stack((mono, -mono))
        result = compare_live_frame(build_reference_profile(stereo, rate), analyze_spectrum_frame(stereo, rate))
        np.testing.assert_allclose(result["delta_db"], 0.0, atol=1e-7, rtol=0.0)

    def test_quiet_live_noise_is_rejected_and_weak_valid_tones_remain_comparable(self) -> None:
        """미약한 잡음의 정규화 확대를 막고 관측 가능한 약한 톤의 대역 차이는 보존한다."""

        rng = np.random.default_rng(19)
        noise = rng.normal(size=FFT_SIZE)
        noise /= np.sqrt(np.mean(noise**2))
        quiet = analyze_spectrum_frame(noise * 10.0 ** ((MIN_INPUT_RMS_DBFS - 1.0) / 20.0), SAMPLE_RATE)
        with self.assertRaisesRegex(ReferenceCompareError, "-75 dBFS"):
            compare_live_frame(self.profile, quiet)

        mono = _tone((752.3, 2_989.7), (0.35, 0.12), FFT_SIZE, SAMPLE_RATE).astype(np.float64)
        reference = build_reference_profile(mono, SAMPLE_RATE)
        weak = analyze_spectrum_frame(mono * 0.001, SAMPLE_RATE)
        self.assertGreater(weak.rms_dbfs, MIN_INPUT_RMS_DBFS)
        result = compare_live_frame(reference, weak)
        for row in result["bands"]:
            self.assertLess(abs(row["delta_db"]), 0.001)

    def test_different_live_grid_and_rate_are_projected_to_reference_grid(self) -> None:
        """다른 표본률·FFT 격자도 공통 로그 셀에 투영되어 유한한 비교를 반환해야 한다."""

        live_rate = 44_100
        live = _tone((750.0, 3_000.0), (0.35, 0.12), 4_096, live_rate)
        frame = analyze_spectrum_frame(live, live_rate, fft_size=4_096)
        result = compare_live_frame(self.profile, frame)

        self.assertGreater(len(result["frequencies_hz"]), 180)
        self.assertEqual(len(result["frequencies_hz"]), len(result["delta_db"]))
        self.assertTrue(np.all(np.isfinite(np.asarray(result["delta_db"]))))
        self.assertTrue(np.all(np.diff(np.asarray(result["frequencies_hz"])) > 0.0))
        for row in result["bands"]:
            if row["id"] in ("mid", "presence"):
                self.assertLess(abs(row["delta_db"]), 0.01)

    def test_smooth_spectrum_is_stable_across_different_input_grids(self) -> None:
        """같은 매끄러운 스펙트럼을 다른 선형 격자로 주면 대역 결과가 거의 같아야 한다."""

        coarse_hz = np.linspace(20.0, 20_000.0, 900, dtype=np.float64)
        fine_hz = np.linspace(20.0, 20_000.0, 1_800, dtype=np.float64)

        def shape(values: np.ndarray) -> np.ndarray:
            """두 봉우리를 가진 양의 매끄러운 테스트 파워 분포를 계산한다."""

            log_hz = np.log(values)
            return np.exp(-0.5 * np.square((log_hz - math.log(500.0)) / 0.7)) + 0.4 * np.exp(
                -0.5 * np.square((log_hz - math.log(5_000.0)) / 0.5)
            )

        coarse_result = compare_live_frame(self.profile, _manual_frame(coarse_hz, shape(coarse_hz)))
        fine_result = compare_live_frame(self.profile, _manual_frame(fine_hz, shape(fine_hz), gain_db=-12.0))
        coarse_bands = np.asarray([row["current_db"] for row in coarse_result["bands"]])
        fine_bands = np.asarray([row["current_db"] for row in fine_result["bands"]])
        np.testing.assert_allclose(coarse_bands, fine_bands, atol=0.08, rtol=0.0)

    def test_wrong_schema_nonfinite_frame_and_silence_are_rejected(self) -> None:
        """손상된 프로필 schema·비유한 실시간 값·무음 프레임은 공개 오류로 거부해야 한다."""

        mono = _tone((750.0,), (0.3,), FFT_SIZE, SAMPLE_RATE)
        valid_frame = analyze_spectrum_frame(mono, SAMPLE_RATE)
        wrong_schema = dict(self.profile)
        wrong_schema["schema"] = "unknown"
        dirty = SpectrumFrame(
            waveform=valid_frame.waveform,
            frequencies_hz=valid_frame.frequencies_hz,
            magnitudes_dbfs=np.full_like(valid_frame.magnitudes_dbfs, np.nan),
            rms_dbfs=valid_frame.rms_dbfs,
            peak_dbfs=valid_frame.peak_dbfs,
            spectral_centroid_hz=valid_frame.spectral_centroid_hz,
        )
        silence = analyze_spectrum_frame(np.zeros(FFT_SIZE, dtype=np.float32), SAMPLE_RATE)

        for operation in (
            lambda: compare_live_frame(wrong_schema, valid_frame),
            lambda: compare_live_frame(self.profile, dirty),
            lambda: compare_live_frame(self.profile, silence),
        ):
            with self.subTest(operation=operation), self.assertRaises(ReferenceCompareError):
                operation()


if __name__ == "__main__":
    unittest.main()
