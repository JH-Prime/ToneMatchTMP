"""모델 다운로드·장치 재생 없이 새 음악 작업 경로와 배포 의존성을 검사한다."""

from pathlib import Path
from copy import deepcopy
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


def run_practice_self_test():
    """합성 반주를 생성하고 프레임·이조·내보내기를 장치 출력 없이 확인한다."""
    from practice_audio import MixSettings, render_practice
    from practice_chart import PracticeProject, load_project, parse_chart, save_project, transpose_chart

    bars = transpose_chart(parse_chart("[A] | D/F# A7 | Bm - |"), 2)
    project = PracticeProject(bars, bpm=140, style='Funk')
    with tempfile.TemporaryDirectory(prefix='tonematch-practice-check-') as folder:
        directory = Path(folder)
        save_project(project, directory / 'practice.json')
        restored = load_project(directory / 'practice.json')
        audio = render_practice(restored)
        try:
            mix = MixSettings()
            with audio.open_mix(lambda: mix) as source:
                frames = audio.frames == source.getnframes()
                start = audio.start_frame
                first = read_pcm_block(source, start, start + min(audio.rate, audio.frames - start))
                pcm = bool(np.all(np.isfinite(first)) and 0.01 < np.max(np.abs(first)) < 1.0)
            audio.export(directory / 'bass.wav', mix, part='bass')
            with wave.open(str(directory / 'bass.wav'), 'rb') as exported:
                aligned_export = (exported.getnframes() == audio.frames - start
                                  and exported.getframerate() == audio.rate)
            audio.export(directory / 'mix.mp3', mix)
            mp3_export = (directory / 'mix.mp3').stat().st_size > 1024
            count_in = start > 0 and audio.bar_starts[0] == start
        finally:
            audio.close()
    transpose = bars[0].chords == ('E/G#', 'B7') and bars[1].chords == ('C#m', '-')
    checks = {'project_roundtrip': restored == project, 'slash_bass_transposed': transpose,
              'aligned_frames': frames and aligned_export and count_in,
              'finite_pcm': pcm, 'mp3_export': mp3_export}
    return {'ok': all(checks.values()), **checks, 'audible_output_tested': False}


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
    fft_analysis = analyze_song_chords(np.column_stack((signal, -signal)), rate, method='fft')
    fft_ok = (fft_analysis['method_id'] == 'fft' and any(event['symbol'] == 'C' for event in fft_analysis['events'])
              and all(not event['candidate_shapes'] for event in fft_analysis['events']))
    fft_edited = set_correction({'chord_voicing': fft_analysis}, 0, 'Dm9')
    fft_ok = fft_ok and effective_voicing(fft_edited)['events'][0]['symbol'] == 'Dm9'
    # Distinct single notes must stay unknown while retaining their own evidence.
    note_axis = np.arange(rate * 2, dtype=np.float64) / rate
    note_changes = np.concatenate([
        .2 * np.sin(2 * np.pi * 440 * 2 ** ((note - 69) / 12) * note_axis)
        for note in (48, 50)])
    evidence_ok = True
    for method in ('cqt', 'fft'):
        changed = analyze_song_chords(np.column_stack((note_changes, -note_changes)), rate, method=method)
        evidence_ok = evidence_ok and all(row['symbol'] == '?' for row in changed['events'])
        for seconds, expected in ((1., {0}), (3., {2})):
            rows = [row for row in changed['events'] if row['start_seconds'] <= seconds < row['end_seconds']]
            evidence_ok = evidence_ok and len(rows) == 1 and set(
                rows[0]['evidence']['observed_pitch_classes']) == expected
    # A resonant third partial plus a weak unrelated tone must not be promoted
    # to an independently played fifth. The FFT low-bass gain is deferred.
    frequency = 440 * 2 ** ((36 - 69) / 12)
    harmonic_signal = sum((1 + 8 * np.exp(-((partial - 3) / 1.1) ** 2)) / partial
                          * np.sin(2 * np.pi * frequency * partial * axis)
                          for partial in range(1, 25))
    harmonic_signal *= .2 / np.max(np.abs(harmonic_signal))
    harmonic_signal += .006 * np.sin(2 * np.pi * 440 * 2 ** ((58 - 69) / 12) * axis)
    harmonic_analysis = analyze_song_chords(
        np.column_stack((harmonic_signal, -harmonic_signal)), rate, method='fft')
    harmonic_ok = bool(harmonic_analysis['events']) and all(
        row['chord_type'] == 'unknown' for row in harmonic_analysis['events'])
    cqt_harmonic = analyze_song_chords(
        np.column_stack((harmonic_signal, -harmonic_signal)), rate, method='cqt')
    cqt_harmonic_ok = bool(cqt_harmonic['events']) and all(
        row['chord_type'] == 'unknown' and not row['alternatives'] for row in cqt_harmonic['events'])
    # The nearby equal-tempered fifth is independent evidence, including a
    # harmonic-rich wide voicing. Withholding every C5 would fail this check.
    power_signal = sum(.07 / partial ** 1.5 * np.sin(
        2 * np.pi * 440 * 2 ** ((note - 69) / 12) * partial * axis)
        for note in (36, 55) for partial in range(1, 9))
    power_analysis = analyze_song_chords(np.column_stack((power_signal, -power_signal)), rate)
    power_ok = bool(power_analysis['events']) and all(
        row['symbol'] == 'C5' for row in power_analysis['events'])
    omitted = sum(.1 * np.sin(2 * np.pi * 440 * 2 ** ((note - 69) / 12) * axis)
                  for note in (48, 52, 58))
    omitted_analysis = analyze_song_chords(omitted[:, None], rate)
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
        invalid_symbol_ok = True
        for automatic in (analysis, restored['chord_voicing']):
            invalid = deepcopy(chord_result)
            invalid['chord_voicing'] = deepcopy(automatic)
            del invalid['chord_voicing']['events'][0]['symbol']
            save_json(invalid, root / 'invalid-symbol.json')
            try:
                load_result(root / 'invalid-symbol.json')
            except ValueError:
                pass
            else:
                invalid_symbol_ok = False
        method_ok = restored['chord_voicing']['method_id'] == 'cqt'
        chord_result['chord_voicing'] = fft_analysis
        save_json(chord_result, root / 'fft.json')
        fft_restored = load_result(root / 'fft.json', 'en')
        method_ok = method_ok and fft_restored['chord_voicing']['method_id'] == 'fft' and fft_restored['model_guide'] == 'FFT'
        # The declared C7 interpretation must not turn the absent G into an
        # observed note when the frozen runtime saves and reopens its evidence.
        omitted_result = deepcopy(chord_result)
        omitted_result['chord_voicing'] = omitted_analysis
        save_json(omitted_result, root / 'omitted-fifth.json')
        omitted_restored = load_result(root / 'omitted-fifth.json', 'en')
        omitted_events = omitted_restored['chord_voicing']['events']
        omitted_ok = bool(omitted_events) and all(
            row['symbol'] == 'C7' and set(row['pitch_classes']) == {0, 4, 10}
            and set(row['evidence']['required_pitch_classes']) == {0, 4, 10}
            for row in omitted_events)
        # Exercise abstention persistence/export inside the frozen runtime too.
        # This deliberately abstained synthetic CQT event is not an accuracy test.
        from voicing import _unknown_window
        from report import save_html
        uncertain = deepcopy(chord_result)
        uncertain['chord_voicing'] = deepcopy(analysis)
        unknown = _unknown_window(analysis['events'][0], 'temporal_instability')
        unknown.update(start_seconds=0., end_seconds=3., candidate_shapes=[])
        unknown.pop('_start_seconds', None)
        unknown.pop('_evidence_seconds', None)
        uncertain['chord_voicing'].update(events=[unknown], event_count=1, tonal_coverage=0.)
        save_json(uncertain, root / 'uncertain.json')
        uncertainty_restored = load_result(root / 'uncertain.json', 'en')
        restored_event = uncertainty_restored['chord_voicing']['events'][0]
        save_html(uncertainty_restored, root / 'uncertain.html')
        uncertainty_pdf = save_chart_pdf(uncertainty_restored, root / 'uncertain.pdf')
        uncertainty_ok = (restored_event['symbol'] == '?' and bool(restored_event['alternatives'])
                          and restored_event['evidence']['uncertainty_reason'] == 'temporal_instability'
                          and 'adjacent observations' in (root / 'uncertain.html').read_text(encoding='utf-8')
                          and uncertainty_pdf['chart_pages'] == 1)
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
              "chords_only_reopen": bool(reopen_ok), "cqt_detuned": bool(detuned_ok),
              "fft": bool(fft_ok), "method_reopen": bool(method_ok),
              "uncertainty_reopen_exports": bool(uncertainty_ok),
              "fft_harmonic_rejection": bool(harmonic_ok), "omitted_fifth_reopen": bool(omitted_ok),
              "cqt_harmonic_rejection": bool(cqt_harmonic_ok), "cqt_power_preservation": bool(power_ok),
              "uncertain_note_changes_preserved": bool(evidence_ok),
              "invalid_symbol_rejected": bool(invalid_symbol_ok)}
    return {"ok": all(checks.values()), **checks, "audible_output_tested": False,
            "real_song_accuracy_measured": False}
