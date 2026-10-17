"""미확정 코드의 후보·근거를 보존하고 저장 경계를 검증한다."""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

import chord_chart
from chord_edits import effective_voicing, load_result, set_correction


def uncertain_result():
    """오디오·창 생성 없이 저장 가능한 최소 코드 전용 결과를 만든다."""
    return {
        'analysis_kind': 'chords', 'features': {}, 'recipes': [],
        'source': {'file_name': 'fixture.wav', 'duration_seconds': 6},
        'chord_voicing': {'analysis_source': 'original_mix', 'events': [{
            'start_seconds': 1, 'end_seconds': 5, 'symbol': '?',
            'chord_type': 'unknown', 'root_pc': None, 'confidence': 0,
            'pitch_classes': [],
            'evidence': {'uncertainty_reason': 'weak_match',
                         'observed_pitch_classes': [0, 4, 7, 9]},
            'alternatives': [{'symbol': 'Am7', 'confidence': .3},
                             {'symbol': 'C6', 'confidence': .29}],
        }]},
    }


def chart_segments(result):
    """원본 이벤트와 생성 공백을 포함한 표시 조각을 모은다."""
    chart = chord_chart.build_chord_chart(effective_voicing(result), bpm=120,
                                         duration_seconds=6)
    return [segment for page in chart['pages'] for bar in page['bars']
            for segment in bar['segments']]


class UncertaintyModelTests(unittest.TestCase):
    """후보가 확정 기호로 승격되지 않으며 복원 가능한지 검사한다."""

    def test_chart_preserves_uncertain_evidence_without_promoting_candidate(self):
        result = uncertain_result()
        raw = result['chord_voicing']['events'][0]
        before = deepcopy(result)
        segments = [part for part in chart_segments(result) if part['event_index'] == 0]
        self.assertEqual(len(segments), 3)
        for segment in segments:
            self.assertEqual(segment['label'], '?')
            self.assertTrue(segment['unknown'])
            self.assertEqual(segment.get('evidence'), raw['evidence'])
            self.assertEqual(segment.get('alternatives'), raw['alternatives'])
        segments[0]['evidence']['observed_pitch_classes'].append(2)
        segments[0]['alternatives'][0]['symbol'] = 'Dm'
        self.assertEqual(result, before)
        self.assertEqual(segments[1]['alternatives'][0]['symbol'], 'Am7')

    def test_unobserved_gaps_have_reason_and_no_editable_index_or_candidates(self):
        gaps = [part for part in chart_segments(uncertain_result()) if part['event_index'] is None]
        self.assertEqual(len(gaps), 2)
        for gap in gaps:
            self.assertEqual(gap['label'], '?')
            self.assertEqual(gap.get('evidence'), {'uncertainty_reason': 'unobserved_gap'})
            self.assertEqual(gap.get('alternatives'), [])

    def test_reason_descriptions_are_localized_and_legacy_unknown_is_generic(self):
        reasons = ('low_signal', 'insufficient_tonal_evidence', 'weak_match',
                   'temporal_instability', 'unobserved_gap', 'output_limit')
        for reason in reasons:
            event = {'chord_type': 'unknown', 'symbol': '?',
                     'evidence': {'uncertainty_reason': reason}}
            with self.subTest(reason=reason):
                korean = chord_chart.uncertainty_description(event)
                english = chord_chart.uncertainty_description(event, 'en')
                self.assertTrue(korean)
                self.assertTrue(english)
                self.assertNotEqual(korean, english)
        legacy = {'chord_type': 'unknown', 'symbol': '?'}
        self.assertEqual(chord_chart.uncertainty_description(legacy, 'en'),
                         'There is not enough evidence to identify a chord.')
        segment = chart_segments(uncertain_result())[0]
        self.assertTrue(chord_chart.uncertainty_description(segment))

    def test_known_and_manual_events_have_no_automatic_uncertainty_description(self):
        stale = {'uncertainty_reason': 'weak_match'}
        for event in ({'chord_type': 'major', 'symbol': 'C', 'evidence': stale},
                      {'chord_type': 'unknown', 'symbol': '?', 'manual_edit': True,
                       'evidence': stale}):
            self.assertEqual(chord_chart.uncertainty_description(event), '')

    def test_reason_enum_is_validated_when_reopening_json(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'analysis.json'
            for reason in ('guessed_from_next_chord', '', None, [], {}, True, 4):
                result = uncertain_result()
                result['chord_voicing']['events'][0]['evidence']['uncertainty_reason'] = reason
                path.write_text(json.dumps(result), encoding='utf-8')
                with self.subTest(reason=reason), self.assertRaisesRegex(ValueError, 'uncertainty'):
                    load_result(path)

    def test_saved_unknown_and_legacy_unknown_reopen_without_data_loss(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'analysis.json'
            for legacy in (False, True):
                result = uncertain_result()
                event = result['chord_voicing']['events'][0]
                if legacy:
                    event.pop('evidence')
                    event.pop('alternatives')
                path.write_text(json.dumps(result), encoding='utf-8')
                loaded = load_result(path, 'en')
                self.assertEqual(loaded['chord_voicing']['events'][0], event)
                self.assertEqual(effective_voicing(loaded)['events'][0]['symbol'], '?')

    def test_recovered_metadata_requires_a_boolean_and_an_identified_chord(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'analysis.json'
            for value in ('true', 1, 0, [], {}, None, True):
                result = uncertain_result()
                result['chord_voicing']['events'][0]['evidence']['reanalysis_recovered'] = value
                path.write_text(json.dumps(result), encoding='utf-8')
                with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'reanalysis'):
                    load_result(path)
            for identified in (False, True):
                result = uncertain_result()
                event = result['chord_voicing']['events'][0]
                event['evidence']['reanalysis_recovered'] = identified
                if identified:
                    event.update(symbol='Am7', chord_type='min7', root_pc=9)
                    event['evidence'].pop('uncertainty_reason')
                path.write_text(json.dumps(result), encoding='utf-8')
                loaded = load_result(path)
                self.assertIs(loaded['chord_voicing']['events'][0]['evidence']['reanalysis_recovered'], identified)

    def test_twenty_minute_observation_counts_reopen_with_a_finite_bound(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'analysis.json'
            for count in (24_001, 25_000):
                result = uncertain_result()
                result['source']['duration_seconds'] = 1200
                event = result['chord_voicing']['events'][0]
                event.update(start_seconds=0, end_seconds=1200)
                event['evidence'].update(analyzed_window_count=count, supported_window_count=count)
                path.write_text(json.dumps(result), encoding='utf-8')
                with self.subTest(count=count):
                    loaded = load_result(path)
                    self.assertEqual(loaded['chord_voicing']['events'][0]['evidence']['analyzed_window_count'], count)
            for key in ('supported_window_count', 'analyzed_window_count'):
                for count in (-1, True, 24_001.0, '24001', 25_001):
                    result = uncertain_result()
                    result['chord_voicing']['events'][0]['evidence'][key] = count
                    path.write_text(json.dumps(result), encoding='utf-8')
                    with self.subTest(key=key, count=count), self.assertRaisesRegex(ValueError, 'counts'):
                        load_result(path)

    def test_correction_and_undo_remove_then_restore_automatic_candidates(self):
        result = uncertain_result()
        before = deepcopy(result)
        for symbol in ('Am7', '?'):
            corrected = set_correction(result, 0, symbol)
            event = effective_voicing(corrected)['events'][0]
            self.assertTrue(event['manual_edit'])
            self.assertNotIn('evidence', event)
            self.assertNotIn('alternatives', event)
            self.assertEqual(chord_chart.uncertainty_description(event), '')
            restored = set_correction(corrected, 0, None)
            self.assertEqual(effective_voicing(restored)['events'][0],
                             before['chord_voicing']['events'][0])
        self.assertEqual(result, before)

    def test_unknown_primary_label_cannot_be_overridden_by_candidate_symbol(self):
        result = uncertain_result()
        result['chord_voicing']['events'][0]['symbol'] = 'Am7'
        segments = [part for part in chart_segments(result) if part['event_index'] == 0]
        self.assertTrue(all(part['label'] == '?' and part['unknown'] for part in segments))


if __name__ == '__main__':
    unittest.main()
