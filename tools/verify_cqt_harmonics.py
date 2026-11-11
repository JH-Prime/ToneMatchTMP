"""Paired synthetic harmonic/power-chord comparison, not real-song accuracy."""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BASELINE_COMMIT = '7563242b054065f8893a6c6e344046e188e0b947'
BASELINE_COMMITS = {
    'v0.1.06': BASELINE_COMMIT,
    'v0.1.07': 'e8142f80151d5d92b05bc6c3e5c091934e63a093',
}
SOURCE_FILES = ('voicing.py', 'song_chords.py', 'guitar_shapes.py',
                'tests/test_cqt_harmonics.py', 'tools/verify_cqt_harmonics.py',
                'tools/verify_chord_precision.py', 'tools/verify_chord_uncertainty.py',
                'tools/verify_chord_trace.py')


def source_hashes():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCE_FILES}


IMPORT_HASHES = source_hashes()
sys.path[:0] = [str(ROOT), str(ROOT / 'tests'), str(ROOT / 'tools')]
import song_chords
from test_cqt_harmonics import RATE, tone_audio, resonant_audio
from verify_chord_precision import NOTE_NAMES, precision_metrics, regression_failures
from verify_chord_trace import baseline_modules
from verify_chord_uncertainty import promotions


def fixtures():
    """Declare independent acoustic truth before invoking either analyzer."""
    cases = []

    def add(name, audio, root=None, require_unknown=False, limitation=False):
        cases.append({'name': name, 'audio': audio, 'root': root,
                      'labels': [] if root is None else [NOTE_NAMES[root] + '5'],
                      'require_unknown': require_unknown, 'limitation': limitation})

    for note in (36, 48, 57):
        for shape in ('formant', 'comb3'):
            add(f'{shape}_singleton_{note}', resonant_audio(note, shape), require_unknown=True)
    for note, peak, shape in ((39, .04, 'formant'), (53, .35, 'comb3')):
        add(f'transposed_{shape}_{note}', resonant_audio(note, shape, peak), require_unknown=True)
    source = resonant_audio(36)
    axis = np.arange(len(source)) / RATE
    for note in (50, 58, 61):
        weak = .006 * np.sin(2 * np.pi * 440 * 2 ** ((note - 69) / 12) * axis)
        add(f'weak_unrelated_note_{note}', source + np.column_stack((weak, -weak)), require_unknown=True)
    for notes in ((36, 55), (48, 55), (45, 52), (41, 48), (36, 43, 48), (45, 52, 57)):
        add('power_' + '_'.join(map(str, notes)), tone_audio(notes), notes[0] % 12)
    add('quiet_independent_fifth', tone_audio((48, 55), weights=(1., .3)), 0)
    for cents in (-23., 27.):
        add(f'detuned_power_{cents}', tone_audio((48, 55), cents=cents), 0)
    for notes in ((48, 55), (36, 55), (45, 52)):
        add('harmonic_power_' + '_'.join(map(str, notes)), tone_audio(notes, harmonics=8), notes[0] % 12)
    for notes, weights, seed in (((36, 55), (.3, 1.), 41), ((48, 55), (1., .3), 19),
                                  ((39, 58), (.3, 1.), 67), ((53, 60), (1., .3), 83)):
        add(f'phase_power_{notes[0]}_{notes[1]}_{seed}',
            tone_audio(notes, weights=weights, harmonics=8, phase_seed=seed), notes[0] % 12)
    for harmonics in (1, 8):
        add(f'ordinary_singleton_{harmonics}', tone_audio((48,), harmonics=harmonics), require_unknown=True)
    # Keep known limits visible; they must not regress, but are not falsely
    # counted as successful harmonic rejection if they still receive a name.
    noise = np.random.default_rng(107).normal(0, .002, source.shape).astype(np.float32)
    add('noisy_formant_limitation', source + noise, limitation=True)
    frequency = 440 * 2 ** ((36 - 69) / 12)
    phase = 2 * np.pi * frequency * axis - frequency * .003 / 5 * np.cos(2 * np.pi * 5 * axis)
    mono = sum((1 + 8 * np.exp(-((h - 3) / 1.1) ** 2)) / h * np.sin(h * phase)
               for h in range(1, 25))
    mono *= .2 / np.max(np.abs(mono))
    add('vibrato_formant_limitation', np.column_stack((mono, -mono)).astype(np.float32), limitation=True)
    return cases


def compare(baseline_ref='v0.1.06'):
    if baseline_ref not in BASELINE_COMMITS:
        raise ValueError('Unsupported harmonic baseline')
    before = source_hashes()
    if before != IMPORT_HASHES:
        raise RuntimeError('Source changed after import; restart comparison')
    commit = subprocess.check_output(['git', 'rev-parse', '--verify', baseline_ref + '^{commit}'],
                                     cwd=ROOT, text=True).strip()
    if commit != BASELINE_COMMITS[baseline_ref]:
        raise ValueError(f'Harmonic baseline must resolve to immutable {baseline_ref} source')
    baseline_hashes = {name: hashlib.sha256(subprocess.check_output(
        ['git', 'show', f'{commit}:{name}'], cwd=ROOT)).hexdigest()
        for name in ('voicing.py', 'song_chords.py', 'guitar_shapes.py')}
    if before['guitar_shapes.py'] != baseline_hashes['guitar_shapes.py']:
        raise RuntimeError('Shared baseline dependency differs: guitar_shapes.py')
    old = baseline_modules(commit)['song_chords']
    warm = tone_audio((48, 55))
    for analyzer in (old.analyze_song_chords, song_chords.analyze_song_chords):
        analyzer(warm, RATE, method='cqt')
    rows, failures = [], []
    for case in fixtures():
        audio = case['audio']
        duration = len(audio) / RATE
        truth = [(0., duration, case['labels'])]
        row = {'case': case['name'], 'expected_root_pc': case['root'], 'truth': truth,
               'limitation_control': case['limitation'], 'required_full_rejection': case['require_unknown'],
               'sample_rate': RATE, 'audio_shape': list(audio.shape), 'audio_dtype': str(audio.dtype),
               'audio_sha256': hashlib.sha256(audio.tobytes()).hexdigest()}
        results = {}
        for name, analyzer in (('baseline', old.analyze_song_chords), ('current', song_chords.analyze_song_chords)):
            start = time.perf_counter()
            result = analyzer(audio, RATE, method='cqt')
            elapsed = time.perf_counter() - start
            if result['method_id'] != 'cqt':
                raise AssertionError('Selected frontend changed')
            results[name] = result
            row[name] = precision_metrics(result, truth, duration)
            row[name]['elapsed_seconds'] = round(elapsed, 6)
        if row['audio_sha256'] != hashlib.sha256(audio.tobytes()).hexdigest():
            raise RuntimeError('Analyzer mutated the input')
        row['promotions'] = promotions(results['baseline'], results['current'], truth)
        row['failures'] = regression_failures(row['baseline'], row['current'], row['promotions'])
        if case['require_unknown'] and row['current']['scored_unknown_seconds'] < duration - .001:
            row['failures'].append('targeted singleton did not fully abstain')
        if case['root'] is not None and row['current']['correct_recognized_seconds'] < duration - .001:
            row['failures'].append('independent fifth lost full correct duration')
        failures.extend(f"{case['name']}: {failure}" for failure in row['failures'])
        rows.append(row)
    after = source_hashes()
    if before != after:
        failures.append('Source changed during comparison; results invalid')
    keys = ('correct_recognized_seconds', 'incorrect_recognized_seconds', 'scored_unknown_seconds',
            'unknown_candidate_negative_seconds', 'elapsed_seconds')
    aggregate = {name: {key: round(sum(row[name][key] for row in rows), 6) for key in keys}
                 for name in ('baseline', 'current')}
    wrong_before = aggregate['baseline']['incorrect_recognized_seconds']
    wrong_after = aggregate['current']['incorrect_recognized_seconds']
    # The original harmonic patch must improve v0.1.06. Later maintenance
    # comparisons protect that accepted improvement without demanding a new one.
    if baseline_ref == 'v0.1.06' and wrong_after >= wrong_before:
        failures.append('No false-recognition improvement')
    elif wrong_after > wrong_before + .001:
        failures.append('False-recognition regressed')
    return {'schema': 'tonematch-cqt-harmonics-comparison/v1',
            'created': datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=9))).isoformat(),
            'baseline_ref': baseline_ref, 'baseline_commit': commit,
            'baseline_source_sha256': baseline_hashes, 'source_sha256_before': before,
            'source_sha256_after': after, 'method': 'cqt', 'case_count': len(rows),
            'scope': 'Deterministic paired development and transposed controls; not real-song accuracy',
            'real_song_accuracy_measured': False,
            'limitations': ['exact_harmonic_coincidence_cannot_identify_source_count',
                            'no_general_rejection_guarantee_for_noise_vibrato_or_inharmonicity'],
            'aggregate': aggregate, 'passed': not failures, 'failures': failures, 'cases': rows}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-ref', default='v0.1.06')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = compare(args.baseline_ref)
    text = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + '\n', encoding='utf-8')
        print(json.dumps({key: report[key] for key in ('case_count', 'passed', 'failures', 'aggregate')}))
    else:
        print(text)
    raise SystemExit(0 if report['passed'] else 1)
