"""Changing uncertain observations retain their own time-local evidence."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
from pypdf import PdfReader

from chord_edits import effective_voicing, load_result, set_correction
from chart_pdf import save_chart_pdf
from report import save_html
from song_chords import analyze_song_chords
from voicing import _limit_timeline_events, _merge_events, _unknown_window


def uncertain_windows(observations):
    rows = []
    for index, notes in enumerate(observations):
        row = _unknown_window({'evidence': {'observed_pitch_classes': notes}})
        row['_start_seconds'] = index * .1 - .3
        rows.append(row)
    return rows


class EvidenceMergeTests(unittest.TestCase):
    def test_distinct_unknown_notes_keep_separate_contiguous_intervals(self):
        rows = uncertain_windows([(0,), (0,), (2,), (2,)])
        before = deepcopy(rows)
        events = _merge_events(rows, .1, .6, .4, include_shapes=False)
        self.assertEqual([event.evidence['observed_pitch_classes'] for event in events], [(0,), (2,)])
        self.assertEqual([event.evidence['analyzed_window_count'] for event in events], [2, 2])
        self.assertTrue(all(event.symbol == '?' and not event.alternatives for event in events))
        self.assertEqual((events[0].start_seconds, events[-1].end_seconds), (0., .4))
        self.assertEqual(events[0].end_seconds, events[1].start_seconds)
        self.assertEqual(rows, before)

    def test_equivalent_note_sets_merge_despite_order_and_duplicates(self):
        rows = uncertain_windows([(7, 0, 7), (0, 7)])
        events = _merge_events(rows, .1, .6, .2, include_shapes=False)
        self.assertEqual(len(events), 1)
        self.assertEqual(set(events[0].evidence['observed_pitch_classes']), {0, 7})
        self.assertEqual(events[0].evidence['analyzed_window_count'], 2)

    def test_note_changes_do_not_split_the_same_known_chord(self):
        rows = uncertain_windows([(0, 4, 7), (0, 4, 7, 9)])
        for row in rows:
            row.update(root_pc=0, chord_type='major', symbol='C', confidence=.7,
                       pitch_classes=(0, 4, 7))
            row['evidence'].pop('uncertainty_reason')
        events = _merge_events(rows, .1, .6, .2, include_shapes=False)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].symbol, 'C')

    def test_diverse_unknown_evidence_keeps_the_existing_timeline_budget(self):
        rows = uncertain_windows([(index % 2,) for index in range(4100)])
        events = _merge_events(rows, .1, .6, 410., include_shapes=False)
        self.assertEqual(len(events), 4100)
        limited = _limit_timeline_events(events, 4096)
        self.assertLessEqual(len(limited), 4096)
        self.assertEqual((limited[0].start_seconds, limited[-1].end_seconds), (0., 410.))
        self.assertTrue(all(event.symbol == '?' and not event.alternatives for event in limited))
        self.assertTrue(all(event.evidence['uncertainty_reason'] == 'output_limit' for event in limited))


class EvidencePcmTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rate = 22050
        axis = np.arange(rate * 2) / rate
        mono = np.concatenate([.12 * np.sin(2 * np.pi * 440 * 2 ** ((note - 69) / 12) * axis)
                               for note in (48, 50)])
        audio = np.column_stack((mono, -mono)).astype(np.float32)
        cls.analyses = {method: analyze_song_chords(audio, rate, method=method) for method in ('cqt', 'fft')}

    def test_c_then_d_single_notes_remain_unknown_with_each_notes_evidence(self):
        for method, analysis in self.analyses.items():
            with self.subTest(method=method):
                events = analysis['events']
                self.assertTrue(all(row['symbol'] == '?' for row in events))
                for seconds, expected in ((.5, {0}), (3.5, {2})):
                    row = next(row for row in events if row['start_seconds'] <= seconds < row['end_seconds'])
                    self.assertEqual(set(row['evidence']['observed_pitch_classes']), expected)
                    self.assertFalse(row['alternatives'])
                self.assertEqual((events[0]['start_seconds'], events[-1]['end_seconds']), (0., 4.))
                for left, right in zip(events, events[1:]):
                    self.assertEqual(left['end_seconds'], right['start_seconds'])

    def test_reopening_edit_restore_and_exports_keep_both_local_observations(self):
        with tempfile.TemporaryDirectory() as folder:
            for method, analysis in self.analyses.items():
                with self.subTest(method=method):
                    source = {'analysis_kind': 'chords', 'features': {}, 'recipes': [],
                              'source': {'file_name': 'synthetic.wav', 'duration_seconds': 4},
                              'chord_voicing': analysis}
                    path = Path(folder) / (method + '.json')
                    path.write_text(json.dumps(source), encoding='utf-8')
                    loaded = load_result(path, 'en')
                    rows = effective_voicing(loaded)['events']
                    self.assertIn([2], [row['evidence']['observed_pitch_classes'] for row in rows])
                    index = next(i for i, row in enumerate(rows) if row['evidence']['observed_pitch_classes'] == [2])
                    edited = set_correction(loaded, index, 'D5')
                    self.assertNotIn('evidence', effective_voicing(edited)['events'][index])
                    restored = set_correction(edited, index, None)
                    self.assertEqual(effective_voicing(restored)['events'], rows)
                    html = Path(folder) / (method + '.html')
                    save_html(restored, html)
                    text = html.read_text(encoding='utf-8')
                    self.assertIn('Observed pitch-class candidates: C', text)
                    self.assertIn('Observed pitch-class candidates: D', text)
                    pdf = Path(folder) / (method + '.pdf')
                    save_chart_pdf(restored, pdf)
                    text = '\n'.join(page.extract_text() for page in PdfReader(pdf).pages)
                    self.assertIn('Observed: C |', text)
                    self.assertIn('Observed: D |', text)


if __name__ == '__main__':
    unittest.main()
