"""수정 대화상자·되돌리기·파일 재열기와 언어/리포트 연결을 확인한다."""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_chord_chart_ui import hidden_chart_application, chart_result, chart_text
from i18n import LANGUAGE_LABELS, tr
from report import save_html
from catalog import TARGET_FIRMWARE, MODEL_GUIDE_REVISION


class ChordEditUiTests(unittest.TestCase):
    """실제 Tk 위젯을 숨겨 둔 채 사용자의 코드 수정 동작을 실행한다."""

    def test_editor_apply_undo_restore_and_language_preserve_original(self):
        """코드 편집 후 원본·페이지는 보존되고 잘못된 입력은 부분 반영되지 않는다."""
        with tempfile.TemporaryDirectory() as folder, hidden_chart_application(Path(folder)) as (_root, app):
            app._show_result(chart_result())
            original = deepcopy(app.result['chord_voicing'])
            app._select_chart_bar(app.chart_data['pages'][0]['bars'][0])
            editor = app._open_chord_editor()
            self.assertIsNotNone(editor)
            editor.symbol_var.set('Dm9')
            editor.apply()
            self.assertEqual(app.result['chord_corrections'], {'0': 'Dm9'})
            self.assertIn('Dm9 *', chart_text(app, 'chord_label'))
            editor.symbol_var.set('invalid')
            editor.apply()
            self.assertEqual(app.result['chord_corrections'], {'0': 'Dm9'})
            self.assertTrue(editor.status_var.get())
            app._undo_chord_edit()
            self.assertFalse(app.result['chord_corrections'])
            app._apply_chord_edit(2, 'Am7')
            editor.destroy()
            app.language_var.set(LANGUAGE_LABELS['en'])
            app._change_language()
            self.assertIn('Am7 *', chart_text(app, 'chord_label'))
            self.assertEqual(app.result['chord_voicing'], original)
            app._apply_chord_edit(2, None)
            self.assertIn('?', chart_text(app, 'unknown_chord'))

    def test_reopen_is_atomic_and_requires_source_relink(self):
        """저장 결과를 열어도 자동 재생하지 않고 잘못된 JSON은 현재 결과를 유지한다."""
        with tempfile.TemporaryDirectory() as folder, hidden_chart_application(Path(folder)) as (_root, app):
            app._show_result(chart_result())
            app._apply_chord_edit(0, 'Bb7')
            path = Path(folder) / 'saved.json'
            path.write_text(json.dumps(app.result), encoding='utf-8')
            with patch('app.filedialog.askopenfilename', return_value=str(path)), patch('playback.default_output') as output:
                app._open_result()
                output.assert_not_called()
            self.assertEqual(app.result['chord_corrections'], {'0': 'Bb7'})
            self.assertIsNone(app.playback.source)
            before = deepcopy(app.result)
            path.write_text('{}', encoding='utf-8')
            with patch('app.filedialog.askopenfilename', return_value=str(path)), patch('app.messagebox.showerror') as error:
                app._open_result()
                error.assert_called_once()
            self.assertEqual(app.result, before)

    def test_html_includes_edit_without_claiming_machine_confidence(self):
        """리포트의 수정 기호와 사용자 수정 표시가 원본의 확률 점수를 상속하지 않는다."""
        with tempfile.TemporaryDirectory() as folder, hidden_chart_application(Path(folder)) as (_root, app):
            result = chart_result()
            result['source']['file_name'] = 'synthetic.wav'
            result['source']['end_seconds'] = 105.0
            result['target_firmware'] = TARGET_FIRMWARE
            result['model_guide'] = MODEL_GUIDE_REVISION
            app._show_result(result)
            app._apply_chord_edit(0, 'Dm9')
            path = Path(folder) / 'report.html'
            save_html(app.result, path)
            html = path.read_text(encoding='utf-8')
            self.assertIn('Dm9', html)
            self.assertIn(tr('edit.manual', app.language), html)
