"""결정론적 ToneMatch TMP 분석 엔진의 회귀 테스트.

표준 라이브러리와 NumPy만 사용하며, 별도 오디오 파일 대신 매번 같은 기타 유사
스테레오 신호를 만들어 깨끗한 소스 환경에서도 재현 가능하게 검증한다.
"""

from __future__ import annotations

import copy
import json
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

import engine  # noqa: E402
import report  # noqa: E402


def _guitar_like_stereo(
    duration: float = 6.0,
    sample_rate: int = engine.SAMPLE_RATE,
) -> np.ndarray:
    """약간의 스테레오 폭을 가진 재현 가능한 기타 플럭 신호를 합성한다."""

    rng = np.random.default_rng(20260902)
    frame_count = int(round(duration * sample_rate))
    mono = np.zeros(frame_count, dtype=np.float64)
    fundamentals = (82.41, 110.00, 146.83, 196.00, 123.47, 164.81)
    onsets = np.arange(0.12, duration - 0.45, 0.54)

    for note_index, onset in enumerate(onsets):
        start = int(round(onset * sample_rate))
        note_length = min(int(0.70 * sample_rate), frame_count - start)
        if note_length <= 0:
            continue
        time = np.arange(note_length, dtype=np.float64) / sample_rate
        attack_decay = (1.0 - np.exp(-time / 0.0035)) * np.exp(-time / 0.34)
        fundamental = fundamentals[note_index % len(fundamentals)]
        velocity = 0.62 + 0.30 * ((note_index * 7) % 11) / 10.0
        note = np.zeros(note_length, dtype=np.float64)
        harmonic_count = min(22, int(8_500 / fundamental))
        for harmonic in range(1, harmonic_count + 1):
            phase = rng.uniform(0.0, 2.0 * np.pi)
            note += np.sin(2.0 * np.pi * harmonic * fundamental * time + phase) / harmonic**1.30

        pick_noise = rng.normal(0.0, 1.0, note_length)
        pick_noise = np.diff(pick_noise, prepend=pick_noise[0])
        pick_noise *= 0.035 * np.exp(-time / 0.007)
        mono[start : start + note_length] += velocity * (attack_decay * note + pick_noise)

    peak = np.max(np.abs(mono))
    mono = mono / max(float(peak), 1e-12) * 0.68
    right = np.roll(mono, 5) * 0.97
    right[:5] = 0.0
    return np.column_stack((mono, right)).astype(np.float32)


def _spectral_shape(
    samples: np.ndarray,
    profile: str,
    sample_rate: int = engine.SAMPLE_RATE,
) -> np.ndarray:
    """밝기와 바디 테스트용으로 서로 다른 완만한 스펙트럼 외형을 적용한다."""

    result = np.empty_like(samples, dtype=np.float64)
    frequencies = np.fft.rfftfreq(len(samples), 1.0 / sample_rate)
    if profile == "bright":
        control_hz = (0, 100, 350, 800, 1_800, 4_500, 8_000, sample_rate / 2)
        control_gain = (0.12, 0.22, 0.38, 0.72, 1.55, 2.30, 1.25, 0.04)
    elif profile == "body":
        control_hz = (0, 70, 180, 500, 900, 1_800, 4_500, sample_rate / 2)
        control_gain = (0.08, 0.55, 1.75, 2.15, 1.35, 0.46, 0.12, 0.02)
    else:
        raise ValueError(f"unknown spectral profile: {profile}")

    response = np.interp(frequencies, control_hz, control_gain)
    for channel in range(samples.shape[1]):
        spectrum = np.fft.rfft(samples[:, channel].astype(np.float64))
        result[:, channel] = np.fft.irfft(spectrum * response, n=len(samples))

    peak = np.max(np.abs(result))
    return (result / max(float(peak), 1e-12) * 0.68).astype(np.float32)


def _write_pcm16_stereo(path: Path, samples: np.ndarray, sample_rate: int) -> None:
    """float 스테레오 배열을 16-bit PCM WAV 테스트 파일로 저장한다."""
    pcm = np.round(np.clip(samples, -0.999, 0.999) * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(pcm.tobytes())


def _voicing_payload(coverage: float, reliable_frames: int = 12) -> dict:
    """원본 믹스 재분석 정책을 DSP 구현과 독립적으로 검증할 코드 결과를 만든다."""
    return {
        "schema": "tonematch-voicing/v1",
        "method": "deterministic-test",
        "window_seconds": 0.6,
        "hop_seconds": 0.25,
        "event_count": 2,
        "tonal_coverage": coverage,
        "diagnostics": {
            "status": "ok" if coverage >= 0.15 else "insufficient_evidence",
            "reason": "test_evidence",
            "input_rms_dbfs": -24.0,
            "analyzed_frame_count": 24,
            "active_frame_count": 20,
            "reliable_frame_count": reliable_frames,
            "unknown_frame_count": 24 - reliable_frames,
        },
        "events": [
            {
                "start_seconds": 0.0,
                "end_seconds": 1.0,
                "root_pc": None,
                "chord_type": "unknown",
                "symbol": "?",
                "bass_pc": None,
                "inversion": "unknown",
                "pitch_classes": (),
                "register": "unknown",
                "spacing": "unknown",
                "confidence": 0.0,
                "candidate_shapes": (),
            },
            {
                "start_seconds": 1.0,
                "end_seconds": 3.0,
                "root_pc": 0,
                "chord_type": "major",
                "symbol": "C/E",
                "bass_pc": 4,
                "inversion": "first",
                "pitch_classes": (0, 4, 7),
                "register": "mid",
                "spacing": "close",
                "confidence": 0.8,
                "candidate_shapes": ({"label": "test-shape", "frets_low_e_to_high_e": ("x", 3, 2, 0, 1, 0)},),
            },
        ],
        "limitations": (),
    }


class ChordSourcePolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        """분리 기타와 원본 믹스가 구별되는 작은 PCM을 준비한다."""
        self.guitar = np.full((400, 2), 0.1, dtype=np.float32)
        self.mixture = np.full((400, 2), 0.3, dtype=np.float32)

    def _run_sources(self, primary: dict, candidate: dict | None = None, **kwargs: object) -> tuple[dict, object, object]:
        """실제 디코딩·DSP 없이 두 소스의 선택과 호출 인자를 검사한다."""
        samples = kwargs.pop("samples", self.guitar)
        mixture = kwargs.pop("mixture", self.mixture)
        separation_requested = kwargs.pop("separation_requested", True)
        analyses = [copy.deepcopy(primary)]
        if candidate is not None:
            analyses.append(copy.deepcopy(candidate))
        with (
            patch.object(engine, "analyze_voicings", side_effect=analyses) as analyze,
            patch.object(engine, "voicing_analysis_dict", side_effect=lambda analysis: analysis),
            patch.object(engine, "decode_segment", return_value=(mixture, 22_050, 3.0)) as decode,
        ):
            result = engine._analyze_chord_sources(
                samples, 22_050, source="local-test.mp3", start_seconds=37.5,
                end_seconds=40.5, language="ko", separation_requested=separation_requested, **kwargs,
            )
        return result, analyze, decode

    def test_provided_audio_does_not_redecode_for_weak_chord_evidence(self) -> None:
        """기타 단독으로 지정한 파일은 코드가 약해도 원본 믹스로 바꾸지 않는다."""
        result, analyze, decode = self._run_sources(_voicing_payload(0.0, 0), separation_requested=False)
        self.assertEqual(result["analysis_source"], "provided_audio")
        self.assertEqual(result["source_start_seconds"], 37.5)
        self.assertFalse(result["fallback"]["attempted"])
        analyze.assert_called_once()
        decode.assert_not_called()

    def test_reliable_guitar_stem_does_not_trigger_mix_fallback(self) -> None:
        """기타에 충분한 코드 근거가 있으면 비용이 큰 원본 재분석을 생략한다."""
        result, analyze, decode = self._run_sources(_voicing_payload(0.4))
        self.assertEqual(result["analysis_source"], "guitar_stem")
        self.assertEqual(result["fallback"]["reason"], "not_needed")
        analyze.assert_called_once()
        decode.assert_not_called()

    def test_better_mix_is_selected_and_guitar_voicing_claims_are_removed(self) -> None:
        """원본 화성이 개선되면 출처를 남기되 기타 운지·음역으로 오인할 정보는 숨긴다."""
        progress = []
        result, analyze, decode = self._run_sources(
            _voicing_payload(0.02, 1), _voicing_payload(0.7), progress=lambda value, message: progress.append(value),
        )
        self.assertEqual(result["analysis_source"], "original_mix")
        self.assertEqual(result["source_start_seconds"], 37.5)
        self.assertTrue(result["fallback"]["attempted"])
        self.assertTrue(result["fallback"]["selected"])
        self.assertEqual(result["fallback"]["primary_tonal_coverage"], 0.02)
        self.assertEqual(result["fallback"]["candidate_tonal_coverage"], 0.7)
        self.assertEqual(result["primary_diagnostics"]["reliable_frame_count"], 1)
        self.assertEqual(analyze.call_count, 2)
        self.assertIs(analyze.call_args_list[0].args[0], self.guitar)
        self.assertIs(analyze.call_args_list[1].args[0], self.mixture)
        decode.assert_called_once_with("local-test.mp3", 37.5, 40.5, None, "ko")
        self.assertEqual(progress, [83])
        for event in result["events"]:
            self.assertFalse(event["candidate_shapes"])
            self.assertEqual(event["register"], "unknown")
            self.assertEqual(event["spacing"], "unknown")
            self.assertEqual(event["inversion"], "unknown")
            self.assertIsNone(event["bass_pc"])
            self.assertNotIn("/", event["symbol"])

    def test_near_silent_guitar_triggers_fallback_even_with_coverage(self) -> None:
        """낮은 음량 stem의 그럴듯한 코드 비율만으로 원본 참고 분석을 막지 않는다."""
        quiet = self.guitar * 0.001
        result, _, decode = self._run_sources(_voicing_payload(0.3), _voicing_payload(0.5), samples=quiet)
        self.assertTrue(result["fallback"]["selected"])
        self.assertEqual(result["fallback"]["reason"], "weak_guitar_stem")
        self.assertLess(result["fallback"]["primary_input_rms_dbfs"], -50)
        decode.assert_called_once()

    def test_unconvincing_mix_is_not_selected(self) -> None:
        """원본 후보도 낮은 커버리지·적은 프레임·미미한 개선이면 기타 결과를 유지한다."""
        cases = ((0.02, 0.14, 12, self.guitar), (0.02, 0.4, 2, self.guitar), (0.12, 0.16, 12, self.guitar * 0.001))
        for primary_coverage, candidate_coverage, frames, samples in cases:
            with self.subTest(primary=primary_coverage, candidate=candidate_coverage, frames=frames):
                result, _, _ = self._run_sources(
                    _voicing_payload(primary_coverage), _voicing_payload(candidate_coverage, frames), samples=samples,
                    mixture=samples,
                )
                self.assertEqual(result["analysis_source"], "guitar_stem")
                self.assertEqual(result["tonal_coverage"], primary_coverage)
                self.assertFalse(result["fallback"]["selected"])
                self.assertEqual(result["fallback"]["reason"], "no_better_harmony")

    def test_weak_stem_leak_does_not_outrank_clearer_original_harmony(self) -> None:
        """아주 작은 분리 누출의 높은 코드 비율보다 충분히 선명한 원본 화성을 우선한다."""
        result, _, _ = self._run_sources(
            _voicing_payload(0.7), _voicing_payload(0.4), samples=self.guitar * 0.001,
        )
        self.assertEqual(result["analysis_source"], "original_mix")
        self.assertTrue(result["fallback"]["selected"])
        self.assertEqual(result["tonal_coverage"], 0.4)

    def test_optional_fallback_decode_error_retains_primary_result(self) -> None:
        """선택적 원본 디코딩 실패는 정상 기타·톤 결과 전체를 실패시키지 않는다."""
        primary = _voicing_payload(0.02, 1)
        with (
            patch.object(engine, "analyze_voicings", return_value=primary),
            patch.object(engine, "voicing_analysis_dict", side_effect=lambda analysis: analysis),
            patch.object(engine, "decode_segment", side_effect=engine.AnalysisError("decode <unavailable>")),
        ):
            result = engine._analyze_chord_sources(
                self.guitar, 22_050, source="local-test.mp3", start_seconds=0.0,
                end_seconds=3.0, language="ko", separation_requested=True,
            )
        self.assertEqual(result["analysis_source"], "guitar_stem")
        self.assertEqual(result["fallback"]["reason"], "fallback_unavailable")
        self.assertEqual(result["fallback"]["error_type"], "AnalysisError")
        self.assertFalse(result["fallback"]["selected"])

    def test_cancellation_during_fallback_is_not_swallowed_as_optional_error(self) -> None:
        """원본 추가 분석의 취소를 단순 참고 실패로 삼켜 계속 실행하지 않는다."""
        cancelled = False

        def decode_then_cancel(*args: object) -> tuple[np.ndarray, int, float]:
            """재디코딩 직후 사용자가 취소한 상황을 재현한다."""
            nonlocal cancelled
            cancelled = True
            return self.mixture, 22_050, 3.0

        with (
            patch.object(engine, "analyze_voicings", return_value=_voicing_payload(0.02, 1)) as analyze,
            patch.object(engine, "voicing_analysis_dict", side_effect=lambda analysis: analysis),
            patch.object(engine, "decode_segment", side_effect=decode_then_cancel),
        ):
            with self.assertRaisesRegex(engine.AnalysisError, "취소"):
                engine._analyze_chord_sources(
                    self.guitar, 22_050, source="local-test.mp3", start_seconds=0.0,
                    end_seconds=3.0, language="ko", separation_requested=True,
                    cancel_requested=lambda: cancelled,
                )
        analyze.assert_called_once()

    def test_optional_fallback_analysis_error_does_not_expose_exception_text(self) -> None:
        """원본 화성의 잘못된 PCM은 기타 결과를 유지하며 예외의 사적인 경로를 저장하지 않는다."""
        with (
            patch.object(engine, "analyze_voicings", side_effect=[_voicing_payload(0.02, 1), ValueError("private-source-path")]),
            patch.object(engine, "voicing_analysis_dict", side_effect=lambda analysis: analysis),
            patch.object(engine, "decode_segment", return_value=(self.mixture, 22_050, 3.0)),
        ):
            result = engine._analyze_chord_sources(
                self.guitar, 22_050, source="local-test.mp3", start_seconds=37.5,
                end_seconds=40.5, language="en", separation_requested=True,
            )
        self.assertEqual(result["fallback"]["reason"], "fallback_unavailable")
        self.assertEqual(result["fallback"]["error_type"], "ValueError")
        self.assertEqual(result["source_start_seconds"], 37.5)
        self.assertEqual(result["analysis_source"], "guitar_stem")
        self.assertNotIn("private-source-path", json.dumps(result))

    def test_fallback_does_not_hide_programming_errors(self) -> None:
        """예상하지 않은 코드 오류는 조용히 선택적 원본 실패로 처리하지 않는다."""
        with (
            patch.object(engine, "analyze_voicings", side_effect=[_voicing_payload(0.02, 1), RuntimeError("test-programming-error")]),
            patch.object(engine, "voicing_analysis_dict", side_effect=lambda analysis: analysis),
            patch.object(engine, "decode_segment", return_value=(self.mixture, 22_050, 3.0)),
        ):
            with self.assertRaisesRegex(RuntimeError, "test-programming-error"):
                engine._analyze_chord_sources(
                    self.guitar, 22_050, source="local-test.mp3", start_seconds=0.0,
                    end_seconds=3.0, language="en", separation_requested=True,
                )

    def test_cancellation_before_or_after_either_analysis_propagates(self) -> None:
        """주 분석과 추가 분석 각각의 진입·종료 경계에서 취소가 즉시 전달된다."""
        for cancel_on_call, expected_analyses in ((1, 0), (2, 1), (4, 2)):
            with self.subTest(cancel_check=cancel_on_call):
                check_count = 0

                def requested() -> bool:
                    """지정한 취소 확인 지점부터 사용자의 취소 상태를 유지한다."""
                    nonlocal check_count
                    check_count += 1
                    return check_count >= cancel_on_call

                with (
                    patch.object(engine, "analyze_voicings", side_effect=[_voicing_payload(0.02, 1), _voicing_payload(0.7)]) as analyze,
                    patch.object(engine, "voicing_analysis_dict", side_effect=lambda analysis: analysis),
                    patch.object(engine, "decode_segment", return_value=(self.mixture, 22_050, 3.0)),
                ):
                    with self.assertRaisesRegex(engine.AnalysisError, "cancel"):
                        engine._analyze_chord_sources(
                            self.guitar, 22_050, source="local-test.mp3", start_seconds=0.0,
                            end_seconds=3.0, language="en", separation_requested=True,
                            cancel_requested=requested,
                        )
                self.assertEqual(analyze.call_count, expected_analyses)


class EngineAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        """모든 테스트가 공유하는 합성 원본과 두 스펙트럼 변형을 준비한다."""
        cls.sample_rate = engine.SAMPLE_RATE
        cls.base = _guitar_like_stereo(sample_rate=cls.sample_rate)
        cls.bright = _spectral_shape(cls.base, "bright", cls.sample_rate)
        cls.body_heavy = _spectral_shape(cls.base, "body", cls.sample_rate)

    def _analyze_result(
        self,
        samples: np.ndarray,
        reference_url: str = "",
        output_mode: str = "FRFR / 헤드폰 / USB / PA",
    ) -> dict:
        """파일 디코딩만 대체하고 나머지 전체 분석·추천 시퀀스를 실행한다."""
        duration = len(samples) / self.sample_rate
        with patch.object(
            engine,
            "decode_segment",
            return_value=(samples, self.sample_rate, duration),
        ):
            return engine.analyze_file(
                "합성_기타.wav",
                0.0,
                duration,
                pickup="직접 입력/모름",
                mix_mode="기타 단독/타브 영상",
                output_mode=output_mode,
                reference_url=reference_url,
            )

    def test_near_silence_raises_analysis_error(self) -> None:
        """거의 무음인 입력은 사용자에게 의미 있는 분석 오류를 내야 한다."""
        silent = np.zeros((self.sample_rate * 4, 2), dtype=np.float32)
        with self.assertRaisesRegex(engine.AnalysisError, "무음"):
            engine.extract_features(silent, self.sample_rate)

    def test_bright_and_body_profiles_have_expected_relative_order(self) -> None:
        """고역 강조 신호와 중저역 강조 신호의 상대 특징 순서를 검증한다."""
        bright_features = engine.extract_features(self.bright, self.sample_rate)
        body_features = engine.extract_features(self.body_heavy, self.sample_rate)

        self.assertGreater(
            bright_features.brightness,
            body_features.brightness + 0.12,
            (bright_features.brightness, body_features.brightness),
        )
        self.assertGreater(
            body_features.body,
            bright_features.body + 0.12,
            (body_features.body, bright_features.body),
        )

    def test_pcm16_wav_round_trip_is_stereo_and_close_to_source(self) -> None:
        """16-bit WAV 입출력 뒤 채널·길이·샘플 오차가 허용 범위인지 확인한다."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            wav_path = Path(temporary_directory) / "합성 기타.wav"
            _write_pcm16_stereo(wav_path, self.base, self.sample_rate)
            decoded, decoded_rate = engine.read_pcm_wav(wav_path)

        self.assertEqual(decoded_rate, self.sample_rate)
        self.assertEqual(decoded.shape, self.base.shape)
        np.testing.assert_allclose(decoded, self.base, atol=2.0 / 32768.0, rtol=0.0)

    def test_analysis_returns_three_ordered_recipes(self) -> None:
        """상위 레시피 세 개와 각 체인의 블록 순번·카테고리 순서를 검사한다."""
        result = self._analyze_result(self.base)

        self.assertEqual(result["schema"], "tonematch-tmp-recipe/v1")
        reference = result["reference_spectrum"]
        self.assertEqual(reference["schema"], "tonematch.reference-spectrum.v1")
        self.assertEqual(
            [band["id"] for band in reference["bands"]],
            ["low", "low_mid", "mid", "presence", "treble", "air"],
        )
        self.assertEqual(len(result["recipes"]), 3)
        self.assertEqual(len({item["template_id"] for item in result["recipes"]}), 3)

        category_rank = {
            "Dynamics": 0,
            "Stompbox": 1,
            "Amp Head": 2,
            "Cabinet": 3,
            "Modulation": 4,
            "Delay": 5,
            "Reverb": 6,
            "EQ": 7,
        }
        for recipe_item in result["recipes"]:
            blocks = recipe_item["blocks"]
            self.assertTrue(blocks, recipe_item["template_id"])
            self.assertEqual(
                [block["order"] for block in blocks],
                list(range(1, len(blocks) + 1)),
            )
            ranks = [category_rank[block["category"]] for block in blocks]
            self.assertEqual(ranks, sorted(ranks), recipe_item["template_id"])
            self.assertTrue(all(block["model"] for block in blocks))
            self.assertTrue(all(block["parameters"] for block in blocks))

    def test_chord_mix_fallback_does_not_replace_tone_or_reference_pcm(self) -> None:
        """코드만 원본 믹스를 사용해도 톤·스펙트럼·레시피 입력은 분리 기타 그대로여야 한다."""
        primary = _voicing_payload(0.02, 1)
        candidate = _voicing_payload(0.7)
        with (
            patch.object(engine, "analyze_voicings", return_value=copy.deepcopy(primary)),
            patch.object(engine, "voicing_analysis_dict", side_effect=lambda analysis: analysis),
        ):
            baseline = self._analyze_result(self.base)
        with (
            patch.object(engine, "decode_to_pcm_wav", return_value=6.0),
            patch.object(engine, "separate_guitar_wav", return_value=object()),
            patch.object(engine, "separation_info_dict", return_value={"guitar_rms_dbfs": -24.0}),
            patch.object(engine, "read_pcm_wav", return_value=(self.base, self.sample_rate)),
            patch.object(engine, "decode_segment", return_value=(self.bright, self.sample_rate, 6.0)),
            patch.object(engine, "analyze_voicings", side_effect=[copy.deepcopy(primary), copy.deepcopy(candidate)]),
            patch.object(engine, "voicing_analysis_dict", side_effect=lambda analysis: analysis),
            patch.object(engine, "extract_features", wraps=engine.extract_features) as extract,
            patch.object(engine, "build_reference_profile", wraps=engine.build_reference_profile) as reference,
        ):
            result = engine.analyze_file(
                "local-test.mp3", 30.0, 36.0, pickup="직접 입력/모름",
                mix_mode="full_mix", output_mode="FRFR / 헤드폰 / USB / PA",
            )
        self.assertIs(extract.call_args.args[0], self.base)
        self.assertIs(reference.call_args.args[0], self.base)
        self.assertTrue(result["source_separation"]["used"])
        self.assertEqual(result["chord_voicing"]["analysis_source"], "original_mix")
        self.assertEqual(result["chord_voicing"]["source_start_seconds"], 30.0)
        self.assertEqual(result["features"], baseline["features"])
        self.assertEqual(result["reference_spectrum"], baseline["reference_spectrum"])
        self.assertEqual(result["recipes"], baseline["recipes"])
        english = engine.relocalize_result(result, "en")
        self.assertEqual(english["chord_voicing"], result["chord_voicing"])

    def test_output_routes_match_amp_and_cabinet_policy(self) -> None:
        """세 출력 연결의 Amp·Cabinet 구성과 적용 안내가 실제 추천 블록과 일치해야 한다."""
        cases = {
            "FRFR / 헤드폰 / USB / PA": (True, True, "high"),
            "파워앰프 + 실제 기타 캐비닛 (캐비닛 제외)": (True, False, "medium"),
            "기타 앰프 전면 입력 (앰프/캐비닛 제외)": (False, False, "low"),
        }
        for output_label, (expect_amp, expect_cab, applicability) in cases.items():
            with self.subTest(output=output_label):
                result = self._analyze_result(self.base, output_mode=output_label)
                recipe_item = result["recipes"][0]
                categories = [block["category"] for block in recipe_item["blocks"]]
                self.assertEqual("Amp Head" in categories, expect_amp)
                self.assertEqual("Cabinet" in categories, expect_cab)
                self.assertEqual(recipe_item["amp_included"], expect_amp)
                self.assertEqual(recipe_item["cabinet_included"], expect_cab)
                self.assertEqual(recipe_item["route_applicability"], applicability)
                self.assertEqual([block["order"] for block in recipe_item["blocks"]], list(range(1, len(recipe_item["blocks"]) + 1)))
                if expect_cab:
                    cabinet = next(block for block in recipe_item["blocks"] if block["category"] == "Cabinet")
                    self.assertIn("LOW CUT FILTER", cabinet["parameters"])
                    self.assertIn("HIGH CUT FILTER", cabinet["parameters"])
                    self.assertNotIn("EQ", categories, "캐비닛 컷과 같은 Low/High Cut EQ를 중복 적용하면 안 됩니다.")
                if output_label.startswith("파워앰프"):
                    self.assertTrue(recipe_item["omitted_reference_cabinet"])
                    self.assertTrue(any("Cabinet/IR" in step for step in result["application_steps"]))
                if output_label.startswith("기타 앰프"):
                    self.assertTrue(recipe_item["omitted_reference_amp"])
                    self.assertTrue(any("Amp와 Cabinet" in step for step in result["application_steps"]))

                english = engine.relocalize_result(result, "en")
                self.assertEqual(
                    [block["category"] for block in english["recipes"][0]["blocks"]],
                    categories,
                )
                self.assertIs(english["reference_spectrum"], result["reference_spectrum"])
                self.assertEqual(english["reference_spectrum"], result["reference_spectrum"])

    def test_reference_profile_is_deterministic_and_finite(self) -> None:
        """같은 최종 PCM은 항상 같은 유한 참조 곡선과 6대역 값을 만들어야 한다."""
        first = engine.build_reference_profile(self.base, self.sample_rate, max_frames=32)
        second = engine.build_reference_profile(self.base, self.sample_rate, max_frames=32)

        self.assertEqual(first, second)
        self.assertEqual(first["sample_rate_hz"], self.sample_rate)
        self.assertGreater(first["active_frames"], 0)
        self.assertLessEqual(first["active_frames"], first["sampled_frames"])
        numeric_values = (
            first["frequencies_hz"]
            + first["frequency_edges_hz"]
            + first["normalized_power"]
            + first["relative_db"]
            + [band["relative_db"] for band in first["bands"]]
        )
        self.assertTrue(np.all(np.isfinite(np.asarray(numeric_values, dtype=np.float64))))
        self.assertAlmostEqual(sum(first["normalized_power"]), 1.0, places=12)

    def test_catalog_cabinet_positions_are_structured_and_valid(self) -> None:
        """모든 TMP 캐비닛 조합의 마이크 위치·거리·축이 검증 가능한 형식이어야 한다."""
        features = engine.extract_features(self.base, self.sample_rate)
        for template in engine.TEMPLATES:
            if not template.get("cab"):
                continue
            with self.subTest(template=template["id"]):
                position, axis = engine._parse_mic_position(template["mic_position"])
                self.assertIn("/", position)
                self.assertIn(axis, {"ON AXIS", "OFF AXIS"})
                parameters = engine._cabinet_parameters(template, features)
                self.assertEqual(parameters["MIC"], template["mic"])
                self.assertTrue(parameters["LOW CUT FILTER"].endswith(" Hz"))
                self.assertTrue(parameters["HIGH CUT FILTER"].endswith(" Hz"))

    def test_direct_template_remains_valid_without_amp_or_cabinet(self) -> None:
        """앰프·캐비닛이 없는 다이렉트 템플릿도 모든 출력 경로에서 빈 참조값 없이 조립돼야 한다."""
        features = engine.extract_features(self.base, self.sample_rate)
        template = next(item for item in engine.TEMPLATES if item["id"] == "rockbox_direct")
        for output_mode in ("frfr", "power_amp_cab", "amp_front"):
            with self.subTest(output_mode=output_mode):
                recipe_item = engine._recipe_from_template(template, features, "unknown", output_mode, 0.8, "ko")
                categories = [block["category"] for block in recipe_item["blocks"]]
                self.assertNotIn("Amp Head", categories)
                self.assertNotIn("Cabinet", categories)
                self.assertIsNone(recipe_item["reference_amp"])
                self.assertIsNone(recipe_item["reference_cabinet"])
                self.assertIsNone(recipe_item["omitted_reference_amp"])
                self.assertIsNone(recipe_item["omitted_reference_cabinet"])
                self.assertFalse(any(item.rstrip().endswith("-") for item in recipe_item["limitations"]))

    def test_json_and_html_exports_are_complete_and_escape_url(self) -> None:
        """JSON/HTML 저장 내용과 HTML 특수문자 이스케이프를 검증한다."""
        unsafe_url = "https://example.test/watch?a=1&label=<guitar>"
        result = self._analyze_result(self.base, reference_url=unsafe_url)

        with tempfile.TemporaryDirectory() as temporary_directory:
            output_directory = Path(temporary_directory)
            json_path = output_directory / "result.json"
            html_path = output_directory / "result.html"
            engine.save_json(result, json_path)
            report.save_html(result, html_path)

            parsed = json.loads(json_path.read_text(encoding="utf-8"))
            html_text = html_path.read_text(encoding="utf-8")

        self.assertEqual(parsed["schema"], result["schema"])
        self.assertEqual(parsed["target_firmware"], result["target_firmware"])
        self.assertEqual(len(parsed["recipes"]), 3)
        self.assertEqual(parsed["source"]["reference_url"], unsafe_url)
        self.assertEqual(parsed["reference_spectrum"], result["reference_spectrum"])
        self.assertIn("합성", json.dumps(parsed, ensure_ascii=False))

        self.assertTrue(html_text.startswith("<!doctype html>"))
        self.assertIn("ToneMatch TMP 분석 결과", html_text)
        self.assertIn(result["target_firmware"], html_text)
        for recipe_item in result["recipes"]:
            self.assertIn(recipe_item["name"], html_text)
        self.assertIn("연결 경로 적용성", html_text)
        self.assertIn(result["recipes"][0]["route_applicability_label"], html_text)
        self.assertNotIn("<guitar>", html_text)
        self.assertIn("&lt;guitar&gt;", html_text)
        self.assertIn("&amp;label=", html_text)
        self.assertIn("참조 비교", html_text)
        self.assertIn("Reference | Current | Δ", html_text)
        self.assertIn("Current와 Δ는 실시간 입력 세션 값", html_text)
        for band in result["reference_spectrum"]["bands"]:
            self.assertIn(band["name"], html_text)

        escaped_result = json.loads(json.dumps(result, ensure_ascii=False))
        escaped_result["reference_spectrum"]["bands"][0]["name"] = '<Low & "hot">'
        legacy_result = json.loads(json.dumps(result, ensure_ascii=False))
        legacy_result.pop("reference_spectrum")
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_directory = Path(temporary_directory)
            escaped_path = output_directory / "escaped.html"
            legacy_path = output_directory / "legacy.html"
            report.save_html(escaped_result, escaped_path)
            report.save_html(legacy_result, legacy_path)
            escaped_html = escaped_path.read_text(encoding="utf-8")
            legacy_html = legacy_path.read_text(encoding="utf-8")

        self.assertNotIn('<Low & "hot">', escaped_html)
        self.assertIn("&lt;Low &amp; &quot;hot&quot;&gt;", escaped_html)
        self.assertNotIn("reference-compare", legacy_html)
        self.assertNotIn("참조 비교", legacy_html)

    def test_chord_exports_preserve_source_unknown_gaps_and_original_timestamps(self) -> None:
        """한·영 HTML과 JSON에 출처·진단·미확인 구간·원본 시각을 보존한다."""
        baseline = self._analyze_result(self.base)
        for language in ("ko", "en"):
            for analysis_source in ("guitar_stem", "provided_audio", "original_mix"):
                with self.subTest(language=language, source=analysis_source):
                    result = engine.relocalize_result(baseline, language)
                    result["chord_voicing"] = analysis = _voicing_payload(0.7)
                    analysis.update({
                        "analysis_source": analysis_source,
                        "source_start_seconds": 37.5,
                        "fallback": {
                            "attempted": analysis_source == "original_mix",
                            "selected": analysis_source == "original_mix",
                            "reason": "weak_guitar_stem" if analysis_source == "original_mix" else "not_needed",
                            "primary_tonal_coverage": 0.02,
                            "primary_input_rms_dbfs": -60.0,
                            "candidate_tonal_coverage": 0.7,
                        },
                    })
                    with tempfile.TemporaryDirectory() as temporary_directory:
                        html_path = Path(temporary_directory) / "chords.html"
                        json_path = Path(temporary_directory) / "chords.json"
                        report.save_html(result, html_path)
                        engine.save_json(result, json_path)
                        html_text = html_path.read_text(encoding="utf-8")
                        json_result = json.loads(json_path.read_text(encoding="utf-8"))
                    self.assertIn("37.5s–38.5s", html_text)
                    self.assertIn("38.5s–40.5s", html_text)
                    self.assertIn("<b>?</b><br>—", html_text)
                    self.assertEqual(json_result["chord_voicing"]["analysis_source"], analysis_source)
                    self.assertEqual(json_result["chord_voicing"]["source_start_seconds"], 37.5)
                    self.assertEqual(json_result["chord_voicing"]["diagnostics"], analysis["diagnostics"])
                    self.assertEqual(json_result["chord_voicing"]["events"][0]["chord_type"], "unknown")
                    for line in report.voicing_context_lines(analysis, language):
                        self.assertIn(report.html.escape(line), html_text)
                    if analysis_source == "original_mix":
                        self.assertIn(report.tr("ui.voicing_mix_profile", language), html_text)
                        self.assertNotIn("test-shape", html_text)
                        self.assertNotIn("E A D G B e =", html_text)
                        self.assertNotIn("<b>C/E</b>", html_text)
                        self.assertIn("<b>C</b>", html_text)
                    else:
                        self.assertIn("test-shape", html_text)
                        self.assertIn("E A D G B e =", html_text)
                        self.assertIn("<b>C/E</b>", html_text)

    def test_chord_context_and_event_labels_are_html_escaped(self) -> None:
        """코드 진단 문구와 후보 운지에 포함된 특수문자가 HTML로 실행되지 않는다."""
        result = self._analyze_result(self.base)
        result["chord_voicing"] = _voicing_payload(0.7)
        event = result["chord_voicing"]["events"][1]
        event["symbol"] = '<C & "major">'
        event["candidate_shapes"][0]["label"] = "<shape & candidate>"
        for language in ("ko", "en"):
            result["language"] = language
            with (
                tempfile.TemporaryDirectory() as temporary_directory,
                patch.object(report, "voicing_context_lines", return_value=['<script>alert("source")</script>']),
            ):
                html_path = Path(temporary_directory) / "escaped-chords.html"
                report.save_html(result, html_path)
                html_text = html_path.read_text(encoding="utf-8")
            self.assertNotIn("<script>", html_text)
            self.assertIn("&lt;script&gt;alert(&quot;source&quot;)&lt;/script&gt;", html_text)
            self.assertIn("&lt;C &amp; &quot;major&quot;&gt;", html_text)
            self.assertIn("&lt;shape &amp; candidate&gt;", html_text)

    def test_legacy_chord_export_infers_consistent_source_and_selected_offset(self) -> None:
        """이전 결과도 출처와 선택 시각을 행·안내에 똑같이 적용하며 원본 딕셔너리는 바꾸지 않는다."""
        baseline = self._analyze_result(self.base)
        for language in ("ko", "en"):
            for separated in (False, True):
                with self.subTest(language=language, separated=separated):
                    result = engine.relocalize_result(baseline, language)
                    result["source"]["start_seconds"] = 37.5
                    result["source"]["end_seconds"] = 40.5
                    result["source_separation"]["used"] = separated
                    analysis = _voicing_payload(0.7)
                    result["chord_voicing"] = analysis
                    before = copy.deepcopy(analysis)
                    with tempfile.TemporaryDirectory() as temporary_directory:
                        html_path = Path(temporary_directory) / "legacy-chords.html"
                        report.save_html(result, html_path)
                        html_text = html_path.read_text(encoding="utf-8")
                    expected_source = "guitar_stem" if separated else "provided_audio"
                    self.assertIn(report.html.escape(report.tr(f"ui.voicing_source_{expected_source}", language)), html_text)
                    self.assertIn(report.html.escape(report.tr("ui.voicing_time_note", language, start=37.5)), html_text)
                    self.assertIn("37.5s–38.5s", html_text)
                    self.assertIn("38.5s–40.5s", html_text)
                    self.assertEqual(analysis, before)

    def test_unknown_only_export_has_localized_hint_and_never_invents_a_voicing(self) -> None:
        """전체 미확정 분석은 언어별 이유 안내를 보여 주되 코드·운지·신뢰도를 꾸미지 않는다."""
        baseline = self._analyze_result(self.base)
        for language in ("ko", "en"):
            for quiet in (False, True):
                with self.subTest(language=language, quiet=quiet):
                    result = engine.relocalize_result(baseline, language)
                    analysis = _voicing_payload(0.0, 0)
                    analysis["events"] = [analysis["events"][0]]
                    analysis["diagnostics"]["active_frame_count"] = 0 if quiet else 20
                    result["chord_voicing"] = analysis
                    with tempfile.TemporaryDirectory() as temporary_directory:
                        html_path = Path(temporary_directory) / "unknown-chords.html"
                        report.save_html(result, html_path)
                        html_text = html_path.read_text(encoding="utf-8")
                    hint_key = "ui.voicing_hint_quiet" if quiet else "ui.voicing_hint_generic"
                    self.assertIn(report.html.escape(report.tr(hint_key, language)), html_text)
                    self.assertIn(report.html.escape(report.tr("ui.voicing_unknown", language)), html_text)
                    self.assertIn("<b>?</b><br>—", html_text)
                    self.assertNotIn("<b>C/E</b>", html_text)
                    self.assertNotIn("E A D G B e =", html_text)


if __name__ == "__main__":
    unittest.main()
