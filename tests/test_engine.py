"""결정론적 ToneMatch TMP 분석 엔진의 회귀 테스트.

표준 라이브러리와 NumPy만 사용하며, 별도 오디오 파일 대신 매번 같은 기타 유사
스테레오 신호를 만들어 깨끗한 소스 환경에서도 재현 가능하게 검증한다.
"""

from __future__ import annotations

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


if __name__ == "__main__":
    unittest.main()
