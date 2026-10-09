"""Device routing and separation-independent original-mixture chords."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import engine
from test_engine import _guitar_like_stereo


def analyze(kind='tone', device='tone_master_pro', **kwargs):
    audio = _guitar_like_stereo(duration=3)
    with patch('engine.decode_segment', return_value=(audio, 22050, 3.0)):
        return engine.analyze_file('fixture.wav', 30, 33, 'unknown', 'isolated', 'frfr',
                                   analysis_kind=kind, device_id=device, **kwargs)


class AnalysisModeTests(unittest.TestCase):
    def test_quad_cortex_survives_relocalization_without_tmp_models(self):
        messages = []
        result = analyze(device='quad_cortex', progress=lambda _, message: messages.append(message))
        self.assertFalse(any('TMP' in message for message in messages))
        self.assertEqual(result['target_firmware'], '4.1.1')
        self.assertEqual(len(result['recipes']), 3)
        english = engine.relocalize_result(result, 'en')
        self.assertEqual(english['device_id'], 'quad_cortex')
        self.assertEqual([r['template_id'] for r in result['recipes']], [r['template_id'] for r in english['recipes']])
        self.assertTrue(all('catalog_id' in block for r in english['recipes'] for block in r['blocks']))
        self.assertFalse(any('Pro Control' in step for step in english['application_steps']))

    def test_chords_only_needs_no_supported_device_separation_or_tone_features(self):
        progress = []
        with (patch('engine.separate_guitar_wav', side_effect=AssertionError('No AI')),
              patch('engine.extract_features', side_effect=AssertionError('No tone features'))):
            result = analyze(kind='chords', device='line6_helix', progress=lambda v, _: progress.append(v))
        self.assertEqual(result['analysis_kind'], 'chords')
        self.assertEqual(result['recipes'], [])
        self.assertEqual(result['features'], {})
        self.assertFalse(result['source_separation']['used'])
        self.assertEqual(result['chord_voicing']['analysis_source'], 'original_mix')
        self.assertEqual(result['source']['start_seconds'], 30)
        self.assertEqual(progress, sorted(progress))
        self.assertEqual(progress[-1], 100)
        self.assertEqual(engine.relocalize_result(result, 'en')['recipes'], [])

    def test_chords_only_cancel_and_bad_purpose_are_explicit(self):
        with self.assertRaises(engine.AnalysisError):
            analyze(kind='chords', cancel_requested=lambda: True)
        with self.assertRaises(ValueError):
            analyze(kind='invalid')

    def test_invalid_time_or_firmware_fails_before_decode(self):
        with patch('engine.decode_segment', side_effect=AssertionError('Must validate first')):
            for start, end in [(-1, 0), (float('nan'), 0), (0, float('inf')), (4, 3)]:
                with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                    engine.analyze_file('fixture.wav', start, end, 'unknown', 'isolated', 'frfr', analysis_kind='chords')
            with self.assertRaises(ValueError):
                engine.analyze_file('fixture.wav', 0, 3, 'unknown', 'isolated', 'frfr', device_id='quad_cortex', qc_firmware='bad')

    def test_chords_and_qc_saved_results_can_reopen_and_export(self):
        from chord_edits import load_result
        from report import save_html
        with tempfile.TemporaryDirectory() as folder:
            for kind, device in [('chords', 'tone_master_pro'), ('tone', 'quad_cortex')]:
                result = analyze(kind, device)
                path = Path(folder) / 'analysis.json'
                engine.save_json(result, path)
                restored = load_result(path, 'en')
                self.assertEqual(restored['analysis_kind'], kind)
                self.assertEqual(restored['device_id'], result['device_id'])
                html = Path(folder) / 'result.html'
                save_html(restored, html)
                content = html.read_text(encoding='utf-8')
                self.assertNotIn('Tone Master Pro starting points', content)
                self.assertIn('Chord' if kind == 'chords' else 'Quad Cortex', content)
                if kind == 'chords':
                    for heading in ('Tone fingerprint', 'Application steps', 'DSP diagnostics', 'Guitar-only file', 'Target firmware'):
                        self.assertNotIn(heading, content)
