"""Hidden Tk checks, no audio output or hardware access."""
from pathlib import Path
import tempfile
import unittest
from test_chord_chart_ui import hidden_chart_application, chart_result
from engine import relocalize_result


class PurposeUITests(unittest.TestCase):
    def test_chord_result_has_no_stale_recipe_tabs_and_can_switch_back(self):
        with tempfile.TemporaryDirectory() as folder, hidden_chart_application(Path(folder)) as (root, app):
            original = chart_result('original_mix')
            only = dict(original, analysis_kind='chords', features={}, recipes=[])
            only = relocalize_result(only, 'ko')
            app._show_result(only)
            self.assertNotIn('추천 3개', app.status_var.get())
            self.assertEqual(app.notebook.select(), str(app.voicing_tab))
            self.assertTrue(all(app.notebook.tab(i, 'state') == 'hidden' for i in range(3)))
            app._show_result(original)
            self.assertTrue(all(app.notebook.tab(i, 'state') == 'normal' for i in range(3)))

    def test_chord_purpose_ignores_modeler_and_disables_tone_controls(self):
        with tempfile.TemporaryDirectory() as folder, hidden_chart_application(Path(folder)) as (_, app):
            app.device_id = 'line6_helix'
            app.chords_only_var.set(True)
            app._update_analysis_availability()
            self.assertEqual(str(app.analyze_button['state']), 'normal')
            self.assertEqual(str(app.mix_combo['state']), 'disabled')
            self.assertEqual(str(app.device_combo['state']), 'disabled')
            self.assertIn('CQT', app.device_description_var.get())

    def test_catalog_search_preserves_licensing_and_pending_status(self):
        from qc_catalog_ui import CatalogWindow
        with tempfile.TemporaryDirectory() as folder, hidden_chart_application(Path(folder)) as (root, _):
            window = CatalogWindow(root, 'en')
            window.query.set('Plini')
            window.refresh()
            rows = [window.tree.item(item, 'values') for item in window.tree.get_children()]
            self.assertTrue(rows)
            self.assertTrue(all('Plini' in ' '.join(row) for row in rows))
            self.assertTrue(any('Archetype: Plini X' in row for row in rows))
            window.destroy()
