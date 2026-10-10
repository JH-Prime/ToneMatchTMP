"""실제 Tk의 색상·글꼴·선택 상태로 코드 UI 회귀를 검증한다."""
from pathlib import Path
from types import SimpleNamespace
import tempfile
from tkinter import ttk, font
import unittest
from unittest.mock import Mock, patch

from app import COLORS
from i18n import LANGUAGE_LABELS
from test_chord_chart_ui import hidden_chart_application, chart_result, widget_offset


def descendants(widget):
    """숨긴 실제 위젯 트리를 재귀적으로 검사한다."""
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


class ChordControlTests(unittest.TestCase):
    def test_compact_header_preserves_readable_controls_and_chart_height(self):
        """작은 고배율 창에서 장식 제목을 접어 설정과 악보를 위한 공간을 남긴다."""
        with tempfile.TemporaryDirectory() as folder, hidden_chart_application(Path(folder), scaling=2.0) as (root, app):
            app._show_result(chart_result('original_mix'))
            app.notebook.select(app.voicing_tab)
            for language in ('ko', 'en'):
                app.language_var.set(LANGUAGE_LABELS[language])
                app._change_language()
                root.update()
                self.assertGreaterEqual(app.chart_canvas.winfo_height(), 140)
                self.assertFalse(app.brand.grid_info())
                language_x, language_y = widget_offset(app.language_combo, root)
                device_x, device_y = widget_offset(app.device_combo, root)
                self.assertLessEqual(language_x + app.language_combo.winfo_width(), device_x)
                self.assertEqual(language_y, device_y)
                self.assertLessEqual(device_x + app.device_combo.winfo_width(), root.winfo_width())
            # Withdrawn roots do not apply window-manager geometry changes.
            # Exercise the same resize callback without showing a test window.
            app._resize_header(SimpleNamespace(width=1200, height=800))
            self.assertTrue(app.brand.grid_info())
            self.assertEqual(app.header_tools.grid_info()['column'], 1)
            app._resize_header(SimpleNamespace(width=960, height=600))
            root.update()
            self.assertFalse(app.brand.grid_info())
            self.assertGreaterEqual(app.chart_canvas.winfo_height(), 140)

    def test_analysis_button_passes_the_selected_method_to_worker(self):
        """화면에서 고른 방식이 두 분석 목적의 작업자 요청에 그대로 전달된다."""
        with tempfile.TemporaryDirectory() as folder, hidden_chart_application(Path(folder)) as (root, app):
            for method in ('CQT', 'FFT'):
                for chords_only in (False, True):
                    app.worker = None
                    app.chord_method_var.set(method)
                    app.chords_only_var.set(chords_only)
                    with patch.object(app, '_parse_inputs', return_value=('fixture.wav', 0, 3)), patch('app.threading.Thread') as thread:
                        app._start_analysis()
                        request = thread.call_args.kwargs['args'][0]
                        self.assertEqual(request['chord_method'], method.lower())
                        self.assertEqual(request['analysis_kind'], 'chords' if chords_only else 'tone')
                        thread.return_value.start.assert_called_once()
            app.worker = None

    def test_all_choice_controls_use_dark_styles_and_language_font(self):
        for scaling in (1.33, 1.67, 2.0, 2.67):
            with self.subTest(scaling=scaling), tempfile.TemporaryDirectory() as folder:
                with hidden_chart_application(Path(folder), scaling=scaling) as (root, app):
                    for language in ('ko', 'en'):
                        app.language_var.set(LANGUAGE_LABELS[language])
                        app._change_language()
                        styles = ttk.Style(root)
                        expected = font.Font(root=root, family=app.ui_font, size=10).actual('family')
                        for widget in descendants(root):
                            if not isinstance(widget, (ttk.Checkbutton, ttk.Radiobutton)):
                                continue
                            name = widget.cget('style') or widget.winfo_class()
                            with self.subTest(language=language, label=widget.cget('text')):
                                self.assertIn(styles.lookup(name, 'background'),
                                              (COLORS['bg'], COLORS['panel'], COLORS['panel_alt']))
                                resolved = font.Font(root=root, font=styles.lookup(name, 'font')).actual('family')
                                self.assertEqual(resolved, expected)
                        self.assertEqual(font.Font(root=root, font=app.playback_controls.status.cget('font')).actual('family'), expected)

    def test_purpose_choices_method_language_and_busy_state(self):
        with tempfile.TemporaryDirectory() as folder, hidden_chart_application(Path(folder)) as (root, app):
            self.assertEqual(len(app.purpose_buttons), 2)
            app.purpose_buttons[1].invoke()
            self.assertTrue(app.chords_only_var.get())
            app.chord_method_var.set('FFT')
            app.language_var.set(LANGUAGE_LABELS['en'])
            app._change_language()
            self.assertTrue(app.chords_only_var.get())
            self.assertEqual(app.chord_method_var.get(), 'FFT')
            app.worker = Mock(is_alive=lambda: True)
            app._update_analysis_availability()
            self.assertTrue(all('disabled' in button.state() for button in app.purpose_buttons))
            self.assertIn('disabled', app.chord_method_combo.state())
            app.worker = None
            app._update_analysis_availability()
            app.purpose_buttons[0].invoke()
            self.assertFalse(app.chords_only_var.get())

    def test_inventory_is_not_exposed_but_native_recommendations_remain(self):
        from quad_cortex import load_catalog
        self.assertGreater(len(load_catalog()['devices']), 600)
        with tempfile.TemporaryDirectory() as folder, hidden_chart_application(Path(folder)) as (root, app):
            labels = [str(widget.cget('text')) for widget in descendants(root) if isinstance(widget, ttk.Button)]
            self.assertFalse(any('장비 목록' in label or 'catalog' in label.lower() for label in labels))
            self.assertFalse(hasattr(app, '_show_qc_catalog'))
