"""배포 EXE에서도 새 음악 작업 경로를 실제 호출하는 무음 자체 진단."""

import unittest


class MusicDiagnosticsTests(unittest.TestCase):
    def test_real_cqt_corrections_pcm_mixer_pdf_and_portaudio_runtime(self):
        from music_diagnostics import run_music_self_test
        result = run_music_self_test()
        self.assertTrue(result["ok"], result)
        for name in ("cqt", "manual_edit", "pcm_reader", "mixer_export", "pdf_font", "portaudio_runtime"):
            self.assertTrue(result[name], name)
        self.assertFalse(result["audible_output_tested"])
