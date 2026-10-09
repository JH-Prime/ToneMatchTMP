"""모델 다운로드·장치 재생 없이 새 음악 작업 경로와 배포 의존성을 검사한다."""

from pathlib import Path
import shutil
import tempfile
import wave

import numpy as np

from chord_edits import effective_voicing, load_result, set_correction
from chart_pdf import save_chart_pdf
from playback import WavPlayer, read_pcm_block
from separator import SEPARATOR_STEMS
from song_chords import analyze_song_chords
from stem_mixer import StemBank, MixState, MixReader
from quad_cortex import load_catalog, recipes


def run_music_self_test():
    """CQT·수정·파일 기반 믹싱·한글 PDF·PortAudio 로딩을 실제 실행한다."""
    import sounddevice

    rate = 22050
    axis = np.arange(rate * 3, dtype=np.float64) / rate
    signal = sum(.1 * np.sin(2 * np.pi * 440 * 2 ** ((note - 69) / 12) * axis)
                 for note in (48, 52, 55))
    analysis = analyze_song_chords(np.column_stack((signal, -signal)), rate)
    cqt_ok = ("CQT" in analysis["method"] and analysis["analysis_source"] == "original_mix"
              and any(event["symbol"] == "C" for event in analysis["events"]))
    detuned = sum(.1 * np.sin(2 * np.pi * 440 * 2 ** ((note - 69 + .30) / 12) * axis)
                  for note in (48, 52, 55))
    tuned_analysis = analyze_song_chords(detuned[:, None], rate)
    detuned_ok = any(event['symbol'] == 'C' for event in tuned_analysis['events'])
    inventory = load_catalog()['devices']
    catalog_ok = len(inventory) == 689 and any(row['kind'] == 'announced' for row in inventory)
    from engine import extract_features, analyze_file, save_json
    recommendations = recipes(extract_features(np.column_stack((signal, signal)), rate), 'frfr')
    native_ids = {row['id'] for row in inventory if row['kind'] == 'native'}
    recipes_ok = len(recommendations) == 3 and all(
        block['catalog_id'] in native_ids and not block['parameters']
        for recipe in recommendations for block in recipe['blocks'])
    result = {"language": "ko", "features": {"bpm": 120},
              "source": {"file_name": "합성 진단.wav", "duration_seconds": 3},
              "chord_voicing": analysis}
    edited = set_correction(result, 0, "Dm9")
    edit_ok = (effective_voicing(edited)["events"][0]["symbol"] == "Dm9"
               and analysis["events"][0]["symbol"] != "Dm9")
    with tempfile.TemporaryDirectory(prefix="tonematch-music-check-") as folder:
        root = Path(folder)
        source = root / "synthetic.wav"
        with wave.open(str(source), "wb") as output:
            output.setparams((2, 2, 44100, 0, "NONE", "not compressed"))
            output.writeframes(np.zeros((132300, 2), dtype="<i2").tobytes())
        chord_result = analyze_file(source, 0, 0, 'unknown', 'full_mix', 'frfr',
                                    device_id='line6_helix', analysis_kind='chords')
        save_json(chord_result, root / 'chords.json')
        restored = load_result(root / 'chords.json', 'en')
        reopen_ok = (restored['analysis_kind'] == 'chords' and not restored['recipes']
                     and not restored['features'] and restored['chord_voicing']['analysis_source'] == 'original_mix')
        bank = StemBank(source)
        player = None
        try:
            shutil.copyfile(source, bank.original_path)
            bank.frames = 132300
            for index, stem in enumerate(SEPARATOR_STEMS):
                with bank.paths[stem].open("wb") as output:
                    output.write(np.full((bank.frames, 2), .01 * (index + 1), dtype="<f4").tobytes())
            state = MixState()
            state.update({"guitar": {"solo": True}})
            with MixReader(bank, state) as reader:
                block = read_pcm_block(reader, 123, 234)
            expected = .01 * (SEPARATOR_STEMS.index("guitar") + 1)
            pcm_ok = block.shape == (111, 2) and np.allclose(block, expected, atol=4e-5)
            # 생성·종료는 reader 수명만 검사하며 실제 출력 장치를 열지 않는다.
            player = WavPlayer(bank.original_path, source_factory=lambda: MixReader(bank, state))
            player.close()
            pcm_ok = bool(pcm_ok and player.wait_closed(2))
            path = bank.export(root / "guitar.wav", state, stem="guitar")
            with wave.open(str(path)) as output:
                export_ok = output.getnframes() == bank.frames and output.getframerate() == 44100
            pdf = save_chart_pdf(edited, root / "chart.pdf")
            pdf_ok = pdf["chart_pages"] == 1 and (root / "chart.pdf").stat().st_size > 1000
        finally:
            if player:
                player.close()
                player.wait_closed(2)
            bank.close()
    portaudio_ok = bool(sounddevice.get_portaudio_version()[0])
    checks = {"cqt": bool(cqt_ok), "manual_edit": bool(edit_ok), "pcm_reader": bool(pcm_ok),
              "mixer_export": bool(export_ok), "pdf_font": bool(pdf_ok), "portaudio_runtime": portaudio_ok,
              "qc_catalog": bool(catalog_ok), "qc_recipes": bool(recipes_ok),
              "chords_only_reopen": bool(reopen_ok), "cqt_detuned": bool(detuned_ok)}
    return {"ok": all(checks.values()), **checks, "audible_output_tested": False,
            "real_song_accuracy_measured": False}
