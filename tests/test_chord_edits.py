"""원래 분석 근거를 보존하는 수동 코드 수정과 저장 데이터 경계를 검증한다."""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from test_chord_chart_ui import chart_result
from chord_chart import build_chord_chart
from chord_edits import parse_symbol, set_correction, effective_voicing, load_result
from voicing import CHORD_SUFFIX, CHORD_INTERVALS, NOTE_NAMES
from report import save_html


class ChordEditTests(unittest.TestCase):
    """확장화음·역위·미확정·복원·파일 입력을 실제 모델로 검사한다."""

    def test_malformed_evidence_is_rejected_before_rendering(self):
        """다시 연 파일의 잘못된 근거·후보는 화면을 바꾸기 전에 거절한다."""
        corruptions = [
            {"pitch_classes": ["not-a-note"]}, {"evidence": ["not-an-object"]},
            {"evidence": {"observed_pitch_classes": [12]}},
            {"evidence": {"analyzed_window_count": "bad"}},
            {"alternatives": [None]}, {"alternatives": None},
            {"bass_pc": []}, {"confidence": "bad"}, {"end_seconds": 1300},
        ]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "invalid.json"
            for corruption in corruptions:
                result = chart_result("original_mix")
                result["chord_voicing"]["events"][0].update(corruption)
                path.write_text(json.dumps(result), encoding="utf-8")
                with self.subTest(corruption=corruption), self.assertRaises(ValueError):
                    load_result(path)

    def test_reopened_full_mix_chords_keep_independent_tone_separation_metadata(self):
        """코드 출처가 전체 음원이어도 기타 톤 분리 여부는 따로 보존한다."""
        result = chart_result("original_mix")
        result["source_separation"] = {"used": True, "guitar_rms_dbfs": -65.0}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "analysis.json"
            path.write_text(json.dumps(result), encoding="utf-8")
            loaded = load_result(path)
        self.assertEqual(loaded["source_separation"], result["source_separation"])

    def test_all_supported_chords_and_six_nine_inversion_parse(self):
        """기존 41종과 12근음을 수정 입력에서도 빠짐없이 지원한다."""
        for root in NOTE_NAMES:
            for chord_type in CHORD_INTERVALS:
                parsed = parse_symbol(root + CHORD_SUFFIX[chord_type])
                self.assertEqual(parsed['chord_type'], chord_type)
        parsed = parse_symbol('Db6/9/Ab')
        self.assertEqual((parsed['root_pc'], parsed['bass_pc'], parsed['chord_type']), (1, 8, '6add9'))
        self.assertEqual(parse_symbol('?')['chord_type'], 'unknown')
        for invalid in ('C<script>', 'Cpentatonic', 'H7', '', 'C/' + 'x' * 300, None):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                parse_symbol(invalid)

    def test_correction_preserves_original_and_removes_stale_acoustics(self):
        """다른 코드로 수정해도 원본은 유지하고 자동 근거는 새 코드에 붙이지 않는다."""
        original = chart_result()
        original['chord_voicing']['events'][0]['evidence'] = {'ambiguous': False}
        before = deepcopy(original)
        edited = set_correction(original, 0, 'Dm9')
        self.assertEqual(original, before)
        self.assertEqual(edited['chord_voicing'], before['chord_voicing'])
        event = effective_voicing(edited)['events'][0]
        self.assertEqual(event['symbol'], 'Dm9')
        self.assertIsNone(event['confidence'])
        self.assertTrue(event['manual_edit'])
        self.assertNotIn('evidence', event)
        self.assertNotIn('alternatives', event)
        self.assertNotEqual(event.get('candidate_shapes'), before['chord_voicing']['events'][0]['candidate_shapes'])
        self.assertEqual(set_correction(edited, 0, None)['chord_corrections'], {})

    def test_long_event_changes_every_continuation_with_full_mix_guard(self):
        """여러 마디에 걸친 수정 기호와 분수코드는 보존하고 운지는 숨긴다."""
        result = chart_result('original_mix')
        result['chord_voicing']['events'] = [dict(result['chord_voicing']['events'][0], start_seconds=0, end_seconds=35)]
        result = set_correction(result, 0, 'C6/9/E')
        chart = build_chord_chart(effective_voicing(result), bpm=120, beats_per_bar=4, duration_seconds=35)
        segments = [segment for page in chart['pages'] for bar in page['bars'] for segment in bar['segments']]
        self.assertGreater(len(segments), 16)
        self.assertEqual({segment['label'] for segment in segments}, {'C6/9/E'})
        self.assertTrue(all(segment.get('manual_edit') for segment in segments))
        self.assertTrue(all(not segment['candidate_shapes'] for segment in segments))

    def test_unknown_and_invalid_corrections_are_atomic(self):
        """미확정 수정과 검증 실패가 원본 및 직전 유효 상태를 오염시키지 않는다."""
        result = set_correction(chart_result(), 2, 'F#m7b5')
        before = deepcopy(result)
        for index, symbol in ((-1, 'C'), (999, 'C'), (True, 'C'), (1, 'nonsense')):
            with self.subTest(index=index), self.assertRaises(ValueError):
                set_correction(result, index, symbol)
        self.assertEqual(result, before)
        unknown = effective_voicing(set_correction(result, 2, '?'))['events'][2]
        self.assertEqual(unknown['chord_type'], 'unknown')
        self.assertEqual(unknown['candidate_shapes'], [])

    def test_save_reopen_validates_and_does_not_restore_local_audio_paths(self):
        """수정 JSON을 다시 열되 원본 경로와 실행 지시 같은 임의 필드는 사용하지 않는다."""
        result = set_correction(chart_result(), 2, 'Am7')
        result['source']['path'] = 'https://example.invalid/private.mp3'
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'analysis.json'
            path.write_text(json.dumps(result), encoding='utf-8')
            loaded = load_result(path, 'en')
            self.assertEqual(loaded['chord_corrections'], {'2': 'Am7'})
            self.assertNotIn('path', loaded['source'])
            self.assertEqual(effective_voicing(loaded)['events'][2]['symbol'], 'Am7')
            save_html(loaded, Path(folder) / 'reopened.html')
            self.assertIn('Am7', (Path(folder) / 'reopened.html').read_text(encoding='utf-8'))
            for corrupt in ({'chord_corrections': {'999': 'C'}}, {'source': {'duration_seconds': float('nan')}},
                            {'recipes': []}, {'features': {}}, {'chord_corrections': ['C']}):
                path.write_text(json.dumps({**result, **corrupt}), encoding='utf-8')
                with self.subTest(corrupt=corrupt), self.assertRaises(ValueError):
                    load_result(path, 'ko')
