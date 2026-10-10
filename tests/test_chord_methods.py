"""두 실제 전처리 방식의 원본 입력·취소·저장 계약을 검증한다."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import engine
from chord_edits import load_result, set_correction, effective_voicing
from i18n import voicing_context_lines
from report import save_html
from song_chords import analyze_song_chords, ChordAnalysisCancelled
from test_song_chords import chord_audio


class ChordMethodTests(unittest.TestCase):
    def test_moving_bass_and_section_gap_do_not_become_one_root_progression(self):
        """저음 E는 C/E로 남고 쉼 뒤 Am을 앞 화음으로 복사하지 않는다."""
        audio = np.concatenate((chord_audio([48, 52, 55]), chord_audio([40, 48, 55]),
                                np.zeros((22050 * 2, 2), np.float32), chord_audio([45, 48, 52])))
        for method in ('cqt', 'fft'):
            with self.subTest(method=method):
                events = analyze_song_chords(audio, 22050, method=method)['events']
                self.assertEqual([row['symbol'] for row in events], ['C', 'C/E', '?', 'Am'])
                self.assertLessEqual(events[2]['start_seconds'], 7)
                self.assertGreaterEqual(events[2]['end_seconds'], 7)

    def test_fft_uses_original_antiphase_pcm_and_no_guitar_shapes(self):
        audio = chord_audio([48, 52, 55], duration=7)
        audio[:, 1] *= -1
        progress = []
        with patch('song_chords._cqt_magnitudes', side_effect=AssertionError('FFT must not run CQT')):
            result = analyze_song_chords(audio, 22050, method='fft', progress=progress.append)
        self.assertEqual(result['method_id'], 'fft')
        self.assertEqual(result['analysis_source'], 'original_mix')
        self.assertIn('C', [row['symbol'] for row in result['events']])
        self.assertTrue(all(not row['candidate_shapes'] for row in result['events']))
        self.assertTrue(all(row['register'] == 'unknown' for row in result['events']))
        self.assertEqual(progress, sorted(progress))
        self.assertEqual(progress[-1], 1)
        self.assertAlmostEqual(result['events'][-1]['end_seconds'], 7)

    def test_fft_cancellation_occurs_inside_work_and_bounds_are_shared(self):
        audio = chord_audio([48, 52, 55], duration=12)
        progress = []
        with self.assertRaises(ChordAnalysisCancelled):
            analyze_song_chords(audio, 22050, method='fft', progress=progress.append,
                                cancel_requested=lambda: bool(progress))
        self.assertGreater(progress[0], 0)
        self.assertLess(progress[-1], 1)
        for method in ('fft', 'cqt'):
            with self.assertRaises(ValueError):
                analyze_song_chords(np.array([[np.nan]], np.float32), 22050, method=method)

    def test_method_routes_and_identity_survives_saved_result_and_language(self):
        audio = chord_audio([48, 52, 55])
        with tempfile.TemporaryDirectory() as folder:
            for method in ('cqt', 'fft'):
                for purpose in ('chords', 'tone'):
                    with self.subTest(method=method, purpose=purpose), patch('engine.decode_segment', return_value=(audio, 22050, 3)), patch('engine.separate_guitar_wav', side_effect=AssertionError('No AI')):
                        result = engine.analyze_file('fixture.wav', 30, 33, 'unknown', 'isolated', 'frfr',
                                                     analysis_kind=purpose, chord_method=method)
                        self.assertEqual(result['chord_voicing']['method_id'], method)
                        self.assertEqual(result['chord_voicing']['source_start_seconds'], 30)
                        result = set_correction(result, 0, 'Dm9')
                        self.assertEqual(effective_voicing(result)['events'][0]['symbol'], 'Dm9')
                        path = Path(folder) / 'result.json'
                        engine.save_json(result, path)
                        restored = load_result(path, 'en')
                        self.assertEqual(restored['chord_voicing']['method_id'], method)
                        self.assertIn(method.upper(), ' '.join(voicing_context_lines(restored['chord_voicing'], 'en')))
                        output = Path(folder) / 'result.html'
                        save_html(restored, output)
                        self.assertIn(method.upper(), output.read_text(encoding='utf-8'))
                        if purpose == 'chords':
                            self.assertEqual(restored['model_guide'], method.upper())

    def test_invalid_method_is_rejected_before_decode_and_on_reopen(self):
        with patch('engine.decode_segment', side_effect=AssertionError('Validate before decode')):
            with self.assertRaises(ValueError):
                engine.analyze_file('fixture.wav', 0, 3, 'unknown', 'isolated', 'frfr', chord_method='guess')
        from test_chord_chart_ui import chart_result
        with tempfile.TemporaryDirectory() as folder:
            data = chart_result('original_mix')
            path = Path(folder) / 'legacy.json'
            engine.save_json(data, path)
            legacy = load_result(path, 'en')
            self.assertNotIn('CQT', ' '.join(voicing_context_lines(legacy['chord_voicing'], 'en')))
            data['chord_voicing']['method_id'] = 'guess'
            engine.save_json(data, path)
            with self.assertRaises(ValueError):
                load_result(path, 'en')
