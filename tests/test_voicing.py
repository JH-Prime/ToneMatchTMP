"""실험 코드 보이싱 분석기의 결정론적 회귀 테스트."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np


MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from voicing import analyze_voicings, candidate_guitar_shapes, voicing_analysis_dict  # noqa: E402


SAMPLE_RATE = 22_050


def _synth_chord(midi_notes: tuple[int, ...], duration: float = 3.0) -> np.ndarray:
    """테스트 코드의 기본음과 약한 고조파를 가진 스테레오 신호를 합성한다."""
    time_axis = np.arange(int(round(SAMPLE_RATE * duration)), dtype=np.float64) / SAMPLE_RATE
    envelope = (1.0 - np.exp(-time_axis / 0.008)) * np.exp(-time_axis / max(1.8, duration))
    mono = np.zeros_like(time_axis)
    for midi_note in midi_notes:
        frequency = 440.0 * 2.0 ** ((midi_note - 69) / 12.0)
        mono += envelope * (
            np.sin(2.0 * np.pi * frequency * time_axis)
            + 0.30 * np.sin(4.0 * np.pi * frequency * time_axis)
            + 0.14 * np.sin(6.0 * np.pi * frequency * time_axis)
        )
    mono /= max(float(np.max(np.abs(mono))), 1e-12) * 1.5
    return np.column_stack((mono, np.roll(mono, 3) * 0.98)).astype(np.float32)


class VoicingAnalysisTests(unittest.TestCase):
    """명확한 합성 코드가 보수적인 코드·역위 결과를 내는지 확인한다."""

    def test_major_minor_and_power_chords(self) -> None:
        """C, Am, E5의 코드 유형과 근음이 예상값으로 판정되어야 한다."""
        cases = [
            ((48, 52, 55, 60, 64), 0, "major", "C"),
            ((45, 52, 57, 60, 64), 9, "minor", "Am"),
            ((40, 47, 52, 59), 4, "power5", "E5"),
        ]
        for notes, root_pc, chord_type, symbol in cases:
            with self.subTest(symbol=symbol):
                analysis = analyze_voicings(_synth_chord(notes), SAMPLE_RATE)
                event = max(analysis.events, key=lambda item: item.confidence)
                self.assertEqual(event.root_pc, root_pc)
                self.assertEqual(event.chord_type, chord_type)
                self.assertEqual(event.symbol, symbol)
                self.assertGreaterEqual(event.confidence, 0.34)

    def test_inversion_uses_lowest_audible_pitch(self) -> None:
        """낮은 E가 포함된 C 코드는 C/E 역위 후보로 표시되어야 한다."""
        analysis = analyze_voicings(_synth_chord((40, 48, 52, 55, 60, 64)), SAMPLE_RATE)
        event = max(analysis.events, key=lambda item: item.confidence)
        self.assertEqual(event.root_pc, 0)
        self.assertEqual(event.bass_pc, 4)
        self.assertEqual(event.inversion, "inversion")
        self.assertEqual(event.symbol, "C/E")

    def test_timeline_preserves_three_chord_order(self) -> None:
        """C→G→Am 연결은 시간 순서가 유지된 세 대표 화음으로 나타나야 한다."""
        signal = np.concatenate(
            (
                _synth_chord((48, 52, 55, 60, 64), 3.0),
                _synth_chord((43, 50, 55, 59, 62), 3.0),
                _synth_chord((45, 52, 57, 60, 64), 3.0),
            ),
            axis=0,
        )
        analysis = analyze_voicings(signal, SAMPLE_RATE)
        symbols = [event.symbol.split("/")[0] for event in analysis.events if event.chord_type != "unknown"]
        condensed = [symbol for index, symbol in enumerate(symbols) if index == 0 or symbol != symbols[index - 1]]
        self.assertIn("C", condensed)
        self.assertIn("G", condensed)
        self.assertIn("Am", condensed)
        self.assertLess(condensed.index("C"), condensed.index("G"))
        self.assertLess(condensed.index("G"), condensed.index("Am"))
        self.assertEqual(analysis.events[0].start_seconds, 0.0)
        self.assertEqual(analysis.events[-1].end_seconds, 9.0)
        for before, after in zip(analysis.events, analysis.events[1:]):
            self.assertEqual(before.end_seconds, after.start_seconds)

    def test_candidate_shapes_are_explicitly_not_detected(self) -> None:
        """연주 후보 운지는 실제 음원에서 검출한 것처럼 표시되면 안 된다."""
        shapes = candidate_guitar_shapes(0, "major")
        self.assertEqual(len(shapes), 2)
        self.assertTrue(all(shape["detected"] is False for shape in shapes))
        self.assertTrue(all(len(shape["frets_low_e_to_high_e"]) == 6 for shape in shapes))

    def test_silence_is_unknown_and_result_is_deterministic(self) -> None:
        """무음은 unknown이며 같은 입력은 직렬화 결과까지 완전히 같아야 한다."""
        silence = np.zeros((SAMPLE_RATE * 2, 2), dtype=np.float32)
        silent_result = analyze_voicings(silence, SAMPLE_RATE)
        self.assertTrue(all(event.chord_type == "unknown" for event in silent_result.events))
        source = _synth_chord((48, 52, 55, 60, 64))
        first = voicing_analysis_dict(analyze_voicings(source, SAMPLE_RATE))
        second = voicing_analysis_dict(analyze_voicings(source, SAMPLE_RATE))
        self.assertEqual(first, second)
        self.assertEqual(first["schema"], "tonematch-voicing/v1")

    def test_invalid_pcm_is_rejected(self) -> None:
        """채널 차원이 없거나 지나치게 낮은 샘플레이트 입력은 거부해야 한다."""
        with self.assertRaises(ValueError):
            analyze_voicings(np.zeros(100, dtype=np.float32), SAMPLE_RATE)
        with self.assertRaises(ValueError):
            analyze_voicings(np.zeros((100, 2), dtype=np.float32), 4_000)
        with self.assertRaises(ValueError):
            analyze_voicings(np.zeros((SAMPLE_RATE, 2), dtype=np.float32), SAMPLE_RATE, max_events=0)


if __name__ == "__main__":
    unittest.main()
