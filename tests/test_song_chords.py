"""전체 음원의 CQT 코드 분석 계약을 합성 신호로 검증한다."""

import unittest
import numpy as np

from song_chords import analyze_song_chords, ChordAnalysisCancelled


def chord_audio(notes, duration=3.0, sample_rate=22050, amplitudes=None):
    """옥타브·상대 음량을 지정한 결정론적 화음 PCM을 만든다."""
    time = np.arange(int(duration * sample_rate)) / sample_rate
    weights = amplitudes or [1.0] * len(notes)
    mono = sum(weight * np.sin(2 * np.pi * 440 * 2 ** ((note - 69) / 12) * time)
               for note, weight in zip(notes, weights)) * (0.25 / max(1, len(notes)))
    return np.column_stack((mono, mono)).astype(np.float32)


class SongChordTests(unittest.TestCase):
    def test_major_minor_suspended_and_slash_chords(self):
        """기타 운지 없이 기본·서스펜디드·저음 전위 기호를 보존한다."""
        cases = [([48, 52, 55], "C"), ([45, 48, 52], "Am"),
                 ([50, 55, 57], "Dsus4"), ([40, 48, 55], "C/E")]
        for notes, expected in cases:
            with self.subTest(symbol=expected):
                result = analyze_song_chords(chord_audio(notes), 22050)
                self.assertIn("CQT", result["method"])
                known = [event for event in result["events"] if event["symbol"] != "?"]
                self.assertTrue(known)
                self.assertEqual(max(known, key=lambda e: e["end_seconds"] - e["start_seconds"])["symbol"], expected)
                self.assertTrue(all(not event["candidate_shapes"] for event in result["events"]))

    def test_identical_pitch_collections_keep_alternative_interpretations(self):
        """C6와 Am7의 구성음이 같아도 하나를 유일한 정답으로 표시하지 않는다."""
        result = analyze_song_chords(chord_audio([48, 52, 55, 57]), 22050)
        event = max(result["events"], key=lambda e: e["end_seconds"] - e["start_seconds"])
        symbols = {event["symbol"]} | {item["symbol"] for item in event["alternatives"]}
        self.assertIn("C6", symbols)
        self.assertIn("Am7/C", symbols)
        self.assertTrue(event["evidence"]["ambiguous"])
        self.assertEqual(result["diagnostics"]["score_semantics"], "heuristic_evidence_not_accuracy_probability")

    def test_silence_noise_and_single_note_do_not_fabricate_chords(self):
        """무음·비주기 잡음·단음에서 화음을 만들어 내지 않는다."""
        rng = np.random.default_rng(11)
        for audio in (np.zeros((66150, 2), np.float32),
                      rng.normal(0, 0.02, (66150, 2)).astype(np.float32),
                      chord_audio([45])):
            result = analyze_song_chords(audio, 22050)
            self.assertFalse(any(event["symbol"] != "?" for event in result["events"]))

    def test_stereo_antiphase_and_quiet_defining_tone(self):
        """역상 채널을 합쳐 지우거나 평균보다 작은 장3도를 버리지 않는다."""
        audio = chord_audio([48, 52, 55], amplitudes=[1.0, 0.35, 1.0])
        audio[:, 1] *= -1
        result = analyze_song_chords(audio, 22050)
        self.assertIn("C", [event["symbol"] for event in result["events"]])

    def test_progress_cancellation_and_input_bounds(self):
        """분할 처리의 진행률·취소와 유한 입력 경계를 검사한다."""
        values = []
        result = analyze_song_chords(chord_audio([48, 52, 55], duration=12), 22050,
                                     progress=values.append)
        self.assertTrue(values)
        self.assertEqual(values, sorted(values))
        self.assertEqual(values[-1], 1.0)
        self.assertAlmostEqual(result["events"][-1]["end_seconds"], 12, places=2)
        with self.assertRaises(ChordAnalysisCancelled):
            analyze_song_chords(chord_audio([48, 52, 55]), 22050, cancel_requested=lambda: True)
        for audio, rate in ((np.array([[np.nan]], np.float32), 22050),
                            (np.zeros((2, 2)), 0), (np.zeros(20), 22050)):
            with self.assertRaises(ValueError):
                analyze_song_chords(audio, rate)


if __name__ == "__main__":
    unittest.main()
