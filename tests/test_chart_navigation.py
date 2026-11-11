"""Exercise real chart navigation without Tk windows or audio output."""

import types
import unittest
from unittest.mock import Mock

from app import ToneMatchApp
from chord_chart import build_chord_chart


def application(first_downbeat=0, duration=90):
    chart = build_chord_chart({'events': [], 'source_start_seconds': 30},
                             bpm=120, first_downbeat_seconds=first_downbeat,
                             duration_seconds=duration)
    view = types.SimpleNamespace(chart_data=chart, chart_page_index=0,
                                 selected_chart_bar=None, playback=Mock(),
                                 chart_canvas=Mock(), playback_controls=Mock(),
                                 _highlight_chart_bars=Mock(), _draw_chart_page=Mock())
    view.playback_controls.loop_var.get.return_value = True
    for name in ('_step_chart_bar', '_select_chart_bar'):
        setattr(view, name, types.MethodType(getattr(ToneMatchApp, name), view))
    return view, [bar for page in chart['pages'] for bar in page['bars']]


class ChartNavigationTests(unittest.TestCase):
    def test_adjacent_navigation_uses_chart_order_for_every_downbeat_offset(self):
        for first in (0, 1, 5, -2, -5):
            with self.subTest(first_downbeat=first):
                view, bars = application(first)
                view.selected_chart_bar = bars[0]
                self.assertEqual(view._step_chart_bar(1), 'break')
                self.assertIs(view.selected_chart_bar, bars[1])
                view.playback.seek.assert_called_with(bars[1]['start_seconds'])
                view.playback_controls.change_loop.assert_called_once_with()
                view._step_chart_bar(-1)
                self.assertIs(view.selected_chart_bar, bars[0])
                view.playback.seek.assert_called_with(bars[0]['start_seconds'])

    def test_page_crossings_follow_actual_bar_position(self):
        for first in (1, -2):
            with self.subTest(first_downbeat=first):
                view, bars = application(first)
                view.selected_chart_bar = bars[15]
                view._step_chart_bar(1)
                self.assertIs(view.selected_chart_bar, bars[16])
                self.assertEqual(view.chart_page_index, 1)
                view._step_chart_bar(-1)
                self.assertIs(view.selected_chart_bar, bars[15])
                self.assertEqual(view.chart_page_index, 0)

    def test_endpoints_clamp_without_wrapping(self):
        for first in (0, 1, -2):
            for selected, step in ((0, -1), (-1, 1)):
                with self.subTest(first_downbeat=first, selected=selected):
                    view, bars = application(first)
                    view.selected_chart_bar = bars[selected]
                    view._step_chart_bar(step)
                    self.assertIs(view.selected_chart_bar, bars[selected])

    def test_missing_or_stale_selection_starts_at_first_visible_bar(self):
        for selected in (None, {'number': 999}, {'number': 2, 'start_seconds': -1}):
            for step in (-1, 1):
                with self.subTest(selected=selected, step=step):
                    view, bars = application(1)
                    view.selected_chart_bar = selected
                    view._step_chart_bar(step)
                    self.assertIs(view.selected_chart_bar, bars[0])
                    self.assertEqual(view.chart_page_index, 0)

    def test_empty_chart_does_not_select_or_seek(self):
        view, bars = application(duration=0)
        self.assertEqual(bars, [])
        self.assertEqual(view._step_chart_bar(1), 'break')
        self.assertIsNone(view.selected_chart_bar)
        view.playback.seek.assert_not_called()
        view._draw_chart_page.assert_not_called()


if __name__ == '__main__':
    unittest.main()
