"""코드·보이싱 분석기의 결정론적 정확도·불확실성 회귀 테스트."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np


MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from voicing import CHORD_INTERVALS, _smooth_labels, analyze_voicings, candidate_guitar_shapes, voicing_analysis_dict  # noqa: E402


SAMPLE_RATE = 22_050


def _synth_chord(midi_notes: tuple[int, ...], duration: float = 3.0, tuning_reference_hz: float = 440.0) -> np.ndarray:
    """테스트 코드의 기본음과 약한 고조파를 가진 스테레오 신호를 합성한다."""
    time_axis = np.arange(int(round(SAMPLE_RATE * duration)), dtype=np.float64) / SAMPLE_RATE
    envelope = (1.0 - np.exp(-time_axis / 0.008)) * np.exp(-time_axis / max(1.8, duration))
    mono = np.zeros_like(time_axis)
    for midi_note in midi_notes:
        frequency = tuning_reference_hz * 2.0 ** ((midi_note - 69) / 12.0)
        mono += envelope * (
            np.sin(2.0 * np.pi * frequency * time_axis)
            + 0.30 * np.sin(4.0 * np.pi * frequency * time_axis)
            + 0.14 * np.sin(6.0 * np.pi * frequency * time_axis)
        )
    mono /= max(float(np.max(np.abs(mono))), 1e-12) * 1.5
    return np.column_stack((mono, np.roll(mono, 3) * 0.98)).astype(np.float32)


def _synth_picked_chord(midi_notes: tuple[int, ...], arpeggio: bool) -> np.ndarray:
    """엇갈린 발음·감쇠·배음과 약한 잡음을 포함한 6초 스트럼 또는 아르페지오를 만든다."""
    duration = 6.0
    time_axis = np.arange(int(SAMPLE_RATE * duration), dtype=np.float64) / SAMPLE_RATE
    mono = np.zeros_like(time_axis)
    for cycle in np.arange(0.0, duration, 1.2):
        for index, midi_note in enumerate(midi_notes):
            onset = cycle + index * (0.15 if arpeggio else 0.027)
            elapsed = np.maximum(0.0, time_axis - onset)
            envelope = np.where(time_axis >= onset, (1.0 - np.exp(-elapsed / 0.004)) * np.exp(-elapsed / 1.1), 0.0)
            frequency = 440.0 * 2.0 ** ((midi_note - 69) / 12.0)
            for harmonic, strength in ((1, 1.0), (2, 0.30), (3, 0.14), (4, 0.07)):
                mono += envelope * strength * np.sin(2.0 * np.pi * frequency * harmonic * elapsed)
    mono *= 0.60 / np.max(np.abs(mono))
    mono += np.random.default_rng(707).normal(0.0, 0.003, len(mono))
    return np.column_stack((mono, np.roll(mono, 3) * 0.97)).astype(np.float32)


class VoicingAnalysisTests(unittest.TestCase):
    """명확한 합성 코드가 보수적인 코드·역위 결과를 내는지 확인한다."""

    def test_temporal_alternatives_obey_the_same_minimum_evidence_gate(self) -> None:
        """시간 평활화에 제공하는 대안도 대표 코드와 같은 최소 근거 점수를 통과해야 한다."""
        from voicing import _classify_window, _guitar_midi_frequencies
        rng = np.random.default_rng(11034)
        pitches = np.zeros(len(_guitar_midi_frequencies()[0]))
        accepted = 0
        for _ in range(256):
            chroma = rng.dirichlet(np.ones(12) * 0.6)
            result = _classify_window(chroma, pitches, pitches, 0.1)
            for candidate in result.get("_candidates", ()):
                accepted += 1
                self.assertGreaterEqual(candidate["confidence"], 0.34)
        self.assertGreater(accepted, 0)

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

    def test_clear_seventh_chords_preserve_quality(self) -> None:
        """실제로 포함된 장7·단7·도미넌트7 음을 3화음으로 뭉개지 않아야 한다."""
        cases = [((48, 52, 55, 58), 0, "7"), ((48, 52, 55, 59), 0, "maj7"), ((45, 48, 52, 55), 9, "min7")]
        for notes, root_pc, chord_type in cases:
            with self.subTest(chord_type=chord_type):
                analysis = analyze_voicings(_synth_chord(notes), SAMPLE_RATE)
                event = max(analysis.events, key=lambda item: item.confidence)
                self.assertEqual((event.root_pc, event.chord_type), (root_pc, chord_type))
                self.assertGreaterEqual(event.confidence, 0.34)

    def test_extended_chords_preserve_all_heard_tones(self) -> None:
        """분명히 들리는 6·9·감7·반감7·서스펜디드 음을 더 작은 코드로 버리지 않는다."""
        cases = [
            ((48, 52, 55, 57), 0, "6"), ((48, 51, 55, 57), 0, "min6"),
            ((47, 50, 53, 57), 11, "min7b5"), ((48, 51, 54, 57), 0, "dim7"),
            ((48, 52, 56), 0, "aug"), ((48, 52, 55, 62), 0, "add9"),
            ((48, 51, 55, 62), 0, "minadd9"), ((48, 52, 55, 58, 62), 0, "9"),
            ((48, 52, 55, 59, 62), 0, "maj9"), ((48, 51, 55, 58, 62), 0, "min9"),
            ((48, 53, 55, 58), 0, "7sus4"),
        ]
        for notes, root, quality in cases:
            with self.subTest(quality=quality):
                analysis = analyze_voicings(_synth_chord(notes), SAMPLE_RATE)
                self.assertTrue(all((event.root_pc, event.chord_type) == (root, quality) for event in analysis.events))
                self.assertEqual(analysis.tonal_coverage, 1.0)

    def test_all_templates_transpose_across_twelve_roots(self) -> None:
        """20종 코드의 12개 근음 합성 입력 모두가 단순 전조에 같은 판정을 유지한다."""
        self.assertEqual(len(CHORD_INTERVALS), 20)
        for quality, intervals in CHORD_INTERVALS.items():
            for root in range(12):
                notes = tuple(48 + root + (14 if interval == 2 and quality != "sus2" else interval) for interval in intervals)
                with self.subTest(root=root, quality=quality):
                    analysis = analyze_voicings(_synth_chord(notes, 1.5), SAMPLE_RATE)
                    self.assertTrue(all((event.root_pc, event.chord_type) == (root, quality) for event in analysis.events))

    def test_extended_picked_chords_keep_their_extensions(self) -> None:
        """스트럼과 아르페지오에서도 반복해서 들리는 9음과 반감7을 보존한다."""
        for notes, root, quality in (((48, 52, 55, 58, 62), 0, "9"), ((47, 50, 53, 57), 11, "min7b5")):
            for arpeggio in (False, True):
                with self.subTest(quality=quality, arpeggio=arpeggio):
                    analysis = analyze_voicings(_synth_picked_chord(notes, arpeggio), SAMPLE_RATE)
                    known = [event for event in analysis.events if event.chord_type != "unknown"]
                    self.assertTrue(known)
                    self.assertTrue(all((event.root_pc, event.chord_type) == (root, quality) for event in known))

    def test_identical_pitch_sets_expose_other_harmonic_interpretations(self) -> None:
        """C6·Am7과 감7·증화음의 동음 구성 해석을 하나의 확정 답처럼 숨기지 않는다."""
        cases = [((48, 52, 55, 57), "6", {(9, "min7")}),
                 ((48, 51, 54, 57), "dim7", {(3, "dim7"), (6, "dim7"), (9, "dim7")}),
                 ((48, 52, 56), "aug", {(4, "aug"), (8, "aug")})]
        for notes, quality, expected in cases:
            with self.subTest(quality=quality):
                analysis = analyze_voicings(_synth_chord(notes), SAMPLE_RATE)
                for event in analysis.events:
                    self.assertEqual(event.chord_type, quality)
                    self.assertEqual({(item["root_pc"], item["chord_type"]) for item in event.alternatives}, expected)
                    self.assertTrue(event.evidence["ambiguous"])
                    self.assertLess(event.confidence, 0.70)
                    self.assertLessEqual(len(event.alternatives), 3)
                    self.assertTrue(all(item["score_delta"] <= 0.040 for item in event.alternatives))

    def test_absent_extension_and_missing_root_are_not_invented(self) -> None:
        """7화음에 9음을 추가하거나 근음 없는 음집합에 들리지 않은 C를 만들어내지 않는다."""
        for notes in ((48, 52, 55, 58), (52, 55, 58, 62)):
            with self.subTest(notes=notes):
                analysis = analyze_voicings(_synth_chord(notes), SAMPLE_RATE)
                observed = {note % 12 for note in notes}
                for event in analysis.events:
                    if event.chord_type == "unknown":
                        continue
                    self.assertNotEqual((event.root_pc, event.chord_type), (0, "9"))
                    self.assertTrue(set(event.pitch_classes).issubset(observed))
                    for other in event.alternatives:
                        required = {(other["root_pc"] + interval) % 12 for interval in CHORD_INTERVALS[other["chord_type"]]}
                        self.assertTrue(required.issubset(observed))

    def test_same_chord_with_new_bass_keeps_separate_inversion_events(self) -> None:
        """C에서 C/E로 바뀌는 실제 베이스 변화는 같은 코드 이름 때문에 합쳐지지 않는다."""
        source = np.concatenate((_synth_chord((48, 52, 55)), _synth_chord((40, 48, 52, 55))))
        analysis = analyze_voicings(source, SAMPLE_RATE)
        known = [event for event in analysis.events if event.chord_type != "unknown"]
        self.assertEqual(known[0].symbol, "C")
        self.assertEqual(known[-1].symbol, "C/E")
        self.assertLess(known[0].start_seconds, known[-1].start_seconds)

    def test_event_evidence_is_serializable_and_has_local_window_support(self) -> None:
        """표시 근거는 실제 관측음·템플릿 음·창 개수를 포함하고 확률 주장 없이 직렬화된다."""
        analysis = analyze_voicings(_synth_chord((48, 52, 55, 62)), SAMPLE_RATE)
        self.assertEqual(sum(event.evidence["supported_window_count"] for event in analysis.events), analysis.diagnostics["reliable_frame_count"])
        for event in voicing_analysis_dict(analysis)["events"]:
            evidence = event["evidence"]
            self.assertTrue(set(evidence["required_pitch_classes"]).issubset(evidence["observed_pitch_classes"]))
            self.assertEqual(evidence["supported_window_count"], evidence["analyzed_window_count"])
            self.assertGreaterEqual(evidence["explained_energy"], 0.60)
            self.assertLessEqual(evidence["explained_energy"], 1.0)
            self.assertEqual(event["alternatives"], ())
        self.assertEqual(analysis.diagnostics["score_semantics"], "heuristic_evidence_not_accuracy_probability")

    def test_weak_clean_chords_keep_pitch_identity(self) -> None:
        """작지만 잡음과 구분되는 같은 화음은 음량 정규화 없이 같은 이름을 유지해야 한다."""
        cases = [((48, 52, 55), 0, "major"), ((45, 48, 52), 9, "minor"), ((48, 52, 55, 58), 0, "7")]
        for notes, root_pc, chord_type in cases:
            for gain in (0.001, 0.0001):
                with self.subTest(notes=notes, gain=gain):
                    analysis = analyze_voicings(_synth_chord(notes) * gain, SAMPLE_RATE)
                    event = max(analysis.events, key=lambda item: item.confidence)
                    self.assertEqual((event.root_pc, event.chord_type), (root_pc, chord_type))
                    self.assertEqual(analysis.diagnostics["input_level"], "very_quiet")
                    self.assertLess(analysis.diagnostics["input_rms_dbfs"], -55.0)

    def test_plucked_strums_and_arpeggios_keep_stable_harmony(self) -> None:
        """현별 발음 시차와 작은 잡음이 있어도 지속되는 명확한 C·Am·G7의 정체를 유지한다."""
        cases = [((48, 52, 55, 60, 64), 0, "major"), ((45, 48, 52, 57), 9, "minor"), ((43, 47, 50, 53), 7, "7")]
        for notes, root, quality in cases:
            for arpeggio in (False, True):
                with self.subTest(root=root, quality=quality, arpeggio=arpeggio):
                    analysis = analyze_voicings(_synth_picked_chord(notes, arpeggio), SAMPLE_RATE)
                    known = [event for event in analysis.events if event.chord_type != "unknown"]
                    self.assertTrue(known)
                    self.assertTrue(all((event.root_pc, event.chord_type) == (root, quality) for event in known))
                    self.assertGreaterEqual(analysis.tonal_coverage, 0.5)

    def test_missing_template_competitors_do_not_imply_perfect_confidence(self) -> None:
        """대안이 없는 분명한 2음 코드에도 거부 점수 센티널에서 만들어진 100%를 주지 않는다."""
        analysis = analyze_voicings(_synth_chord((40, 47)), SAMPLE_RATE)
        self.assertTrue(any(event.chord_type == "power5" for event in analysis.events))
        self.assertTrue(all(event.confidence < 0.90 for event in analysis.events))

    def test_temporal_smoothing_rejects_isolated_label_without_copying_neighbors(self) -> None:
        """단발 B와 미확정 창을 이웃 C로 복사하지 않고 각각 미확정으로 유지한다."""
        base = {"root_pc": 0, "chord_type": "major", "symbol": "C", "confidence": 0.7}
        labels = [dict(base, _start_seconds=index * 0.6) for index in range(7)]
        labels[2].update(root_pc=11, symbol="B")
        labels[3].update(root_pc=None, chord_type="unknown", symbol="?", confidence=0.0)
        original = [dict(item) for item in labels]
        smoothed = _smooth_labels(labels)
        self.assertEqual(labels, original)
        self.assertEqual(smoothed[2]["chord_type"], "unknown")
        self.assertEqual(smoothed[3]["chord_type"], "unknown")
        self.assertEqual([item["_start_seconds"] for item in smoothed], [index * 0.6 for index in range(7)])
        self.assertTrue(all(smoothed[index]["symbol"] == "C" for index in (0, 1, 4, 5, 6)))

    def test_antiphase_stereo_does_not_cancel_chords(self) -> None:
        """완전히 반대 위상의 좌우 채널도 평균 소거되지 않고 코드를 검출해야 한다."""
        source = _synth_chord((48, 52, 55, 59))[:, 0]
        same_phase = np.column_stack((source, source))
        opposite_phase = np.column_stack((source, -source))
        normal = analyze_voicings(same_phase, SAMPLE_RATE)
        antiphase = analyze_voicings(opposite_phase, SAMPLE_RATE)
        self.assertEqual(normal.events, antiphase.events)
        self.assertEqual(normal.tonal_coverage, antiphase.tonal_coverage)
        self.assertTrue(all(event.chord_type == "maj7" for event in antiphase.events))
        self.assertEqual(antiphase.diagnostics["channel_policy"], "first_two_channels_rms_spectrum_no_phase_cancellation")

    def test_single_note_harmonics_do_not_invent_power_chord(self) -> None:
        """한 음의 배음을 여러 실제 음으로 오인해 E5 또는 C5를 만들어서는 안 된다."""
        time_axis = np.arange(SAMPLE_RATE * 3, dtype=np.float64) / SAMPLE_RATE
        for midi_note in (28, 40, 48, 57, 69):
            frequency = 440.0 * 2.0 ** ((midi_note - 69) / 12.0)
            signal = sum(np.sin(2.0 * np.pi * frequency * harmonic * time_axis) / harmonic for harmonic in range(1, 25) if frequency * harmonic < SAMPLE_RATE / 2)
            signal = (signal * (0.3 / np.max(np.abs(signal)))).astype(np.float32)
            for pcm in (_synth_chord((midi_note,)), np.column_stack((signal, -signal))):
                with self.subTest(midi_note=midi_note):
                    analysis = analyze_voicings(pcm, SAMPLE_RATE)
                    self.assertEqual(analysis.tonal_coverage, 0.0)
                    self.assertTrue(all(event.chord_type == "unknown" for event in analysis.events))
                    self.assertEqual(analysis.diagnostics["reason"], "insufficient_polyphonic_evidence")

    def test_noise_and_nonchord_dyad_remain_unknown(self) -> None:
        """광대역 잡음과 C-D 두 음은 필요한 코드 구성음이 없는 상태로 남아야 한다."""
        sources = [_synth_chord((48, 50))]
        for seed in (7, 26, 2026):
            rng = np.random.default_rng(seed)
            noise = rng.normal(0.0, 0.10, (SAMPLE_RATE * 4, 2)).astype(np.float32)
            sources.extend((noise, noise * 0.001))
        for index, source in enumerate(sources):
            with self.subTest(index=index):
                analysis = analyze_voicings(source, SAMPLE_RATE)
                self.assertEqual(analysis.tonal_coverage, 0.0)
                self.assertEqual(analysis.diagnostics["reliable_frame_count"], 0)
                self.assertTrue(all(event.chord_type == "unknown" for event in analysis.events))

    def test_tuning_reference_is_actually_used(self) -> None:
        """A=432 Hz 음원을 해당 기준으로 분석하면 올바른 C 코드를 유지해야 한다."""
        analysis = analyze_voicings(_synth_chord((48, 52, 55), tuning_reference_hz=432.0), SAMPLE_RATE, tuning_reference_hz=432.0)
        self.assertTrue(all(event.root_pc == 0 and event.chord_type == "major" for event in analysis.events))
        self.assertEqual(analysis.diagnostics["tuning_reference_hz"], 432.0)

    def test_common_sample_rates_keep_clear_chord_identity(self) -> None:
        """8·44.1·48 kHz에서도 같은 명확한 Cmaj7이 샘플레이트에 따라 바뀌지 않아야 한다."""
        for sample_rate in (8_000, 44_100, 48_000):
            time_axis = np.arange(sample_rate * 2, dtype=np.float64) / sample_rate
            mono = sum(np.sin(2.0 * np.pi * 440.0 * 2.0 ** ((note - 69) / 12.0) * time_axis) for note in (48, 52, 55, 59)) * 0.1
            with self.subTest(sample_rate=sample_rate):
                analysis = analyze_voicings(np.column_stack((mono, -mono)), sample_rate)
                self.assertTrue(all(event.root_pc == 0 and event.chord_type == "maj7" for event in analysis.events))

    def test_smoothing_does_not_fill_silent_gap_with_chord(self) -> None:
        """같은 코드 사이 무음은 이웃 라벨 복사로 가짜 코드 구간이 되어서는 안 된다."""
        chord = _synth_chord((48, 52, 55))
        source = np.concatenate((chord, np.zeros((SAMPLE_RATE * 2, 2), dtype=np.float32), chord), axis=0)
        analysis = analyze_voicings(source, SAMPLE_RATE)
        self.assertTrue(any(event.chord_type == "unknown" and event.start_seconds <= 4.0 <= event.end_seconds for event in analysis.events))
        self.assertGreater(analysis.diagnostics["unknown_frame_count"], 0)

    def test_diagnostics_explain_silence_and_consistent_frame_counts(self) -> None:
        """실패 이유와 실제 입력 레벨 및 창 개수는 JSON에서 확인할 수 있어야 한다."""
        analysis = analyze_voicings(np.zeros((SAMPLE_RATE * 2, 2), dtype=np.float32), SAMPLE_RATE)
        diagnostics = voicing_analysis_dict(analysis)["diagnostics"]
        self.assertEqual(diagnostics["status"], "no_reliable_chords")
        self.assertEqual(diagnostics["reason"], "silent_or_very_quiet")
        self.assertEqual(diagnostics["input_rms_dbfs"], -240.0)
        self.assertEqual(diagnostics["active_frame_count"], 0)
        self.assertEqual(diagnostics["reliable_frame_count"] + diagnostics["unknown_frame_count"], diagnostics["analyzed_frame_count"])
        empty = analyze_voicings(np.empty((0, 2), dtype=np.float32), SAMPLE_RATE)
        self.assertEqual(empty.diagnostics["input_rms_dbfs"], -240.0)
        self.assertEqual(empty.tonal_coverage, 0.0)

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

    def test_event_limit_keeps_unknown_time_gaps_and_complete_timeline(self) -> None:
        """상한으로 후보가 생략되어도 전체 길이와 실제 미확정 시간대는 삭제되지 않는다."""
        silence = np.zeros((SAMPLE_RATE * 2, 2), dtype=np.float32)
        source = np.concatenate((_synth_chord((48, 52, 55)), silence, _synth_chord((43, 47, 50)), silence, _synth_chord((45, 48, 52))))
        unlimited = analyze_voicings(source, SAMPLE_RATE, max_events=100)
        known_bounds = {(event.start_seconds, event.end_seconds, event.symbol) for event in unlimited.events if event.chord_type != "unknown"}
        for limit in (1, 2, 3, 4):
            with self.subTest(limit=limit):
                limited = analyze_voicings(source, SAMPLE_RATE, max_events=limit)
                self.assertLessEqual(limited.event_count, limit)
                self.assertEqual(limited.events[0].start_seconds, 0.0)
                self.assertEqual(limited.events[-1].end_seconds, len(source) / SAMPLE_RATE)
                self.assertEqual(limited.diagnostics["event_count_before_limit"], unlimited.event_count)
                self.assertTrue(limited.diagnostics["events_truncated"])
                for before, after in zip(limited.events, limited.events[1:]):
                    self.assertEqual(before.end_seconds, after.start_seconds)
                for event in limited.events:
                    if event.chord_type != "unknown":
                        self.assertIn((event.start_seconds, event.end_seconds, event.symbol), known_bounds)
                    else:
                        self.assertEqual(event.alternatives, ())
                        self.assertEqual(event.evidence, {})
                self.assertTrue(any(event.chord_type == "unknown" and event.start_seconds <= 4.0 <= event.end_seconds for event in limited.events))

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
        for value in (np.nan, np.inf, -np.inf):
            with self.subTest(value=value), self.assertRaises(ValueError):
                analyze_voicings(np.full((SAMPLE_RATE, 2), value), SAMPLE_RATE)


if __name__ == "__main__":
    unittest.main()
