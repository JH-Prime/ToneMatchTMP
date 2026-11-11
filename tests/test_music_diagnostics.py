"""배포 EXE에서도 새 음악 작업 경로를 실제 호출하는 무음 자체 진단."""

import unittest


class MusicDiagnosticsTests(unittest.TestCase):
    def test_real_cqt_corrections_pcm_mixer_pdf_and_portaudio_runtime(self):
        from music_diagnostics import run_music_self_test
        result = run_music_self_test()
        self.assertTrue(result['uncertainty_reopen_exports'])
        self.assertTrue(result['fft_harmonic_rejection'])
        self.assertTrue(result['cqt_harmonic_rejection'])
        self.assertTrue(result['cqt_power_preservation'])
        self.assertTrue(result['omitted_fifth_reopen'])
        self.assertTrue(result['uncertain_note_changes_preserved'])
        self.assertTrue(result['invalid_symbol_rejected'])
        self.assertTrue(result["ok"], result)
        for name in ("cqt", "manual_edit", "pcm_reader", "mixer_export", "pdf_font", "portaudio_runtime",
                     "qc_catalog", "qc_recipes", "chords_only_reopen", "cqt_detuned", "fft", "method_reopen"):
            self.assertTrue(result[name], name)
        self.assertFalse(result["audible_output_tested"])
