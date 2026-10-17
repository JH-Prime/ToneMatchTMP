"""Deterministic chord uncertainty comparison; not real-song accuracy evidence.

No GUI, playback, user audio, or network is used. Fixtures discovered during
development are regression controls, not a held-out evaluation corpus.
"""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SOURCE_HASHES = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                 for name in ('song_chords.py', 'voicing.py', 'tools/verify_chord_uncertainty.py')}
sys.path.insert(0, str(ROOT))
import song_chords
from verify_chord_trace import baseline_modules, signal

RATE = 22050


def tone(notes, duration=3.0, weights=None):
    axis = np.arange(round(duration * RATE)) / RATE
    weights = weights if weights is not None else [1.0] * len(notes)
    mono = sum(weight * np.sin(2 * np.pi * 440 * 2 ** ((note - 69) / 12) * axis)
               for note, weight in zip(notes, weights)) * (.25 / max(1, len(notes)))
    return np.column_stack((mono, mono)).astype(np.float32)


def fixtures():
    """Declare harmonic truth separately from classifier output."""
    cases = []

    def add(name, audio, symbols, *, negative=False, stress=False):
        cases.append({'name': name, 'audio': audio,
                      'truth': [(0.0, len(audio) / RATE, symbols)],
                      'negative': negative, 'stress': stress})

    add('clean_C', tone([48, 52, 55]), ['C'])
    add('quiet_third_C', tone([48, 52, 55], weights=[1, .2, 1]), ['C'])
    add('ambiguous_C6_Am7', tone([48, 52, 55, 57]), ['C6', 'Am7/C'])
    add('detuned_minor', tone([45.3, 48.3, 52.3]), ['Am'])
    add('power_dyad_not_major', tone([48, 55]), ['C5'])
    for name, parts in (
        ('low_register_change', [([36, 40, 43], 'C', 3.17), ([33, 36, 40], 'Am', 2.53)]),
        ('tempo_180_quarters', [([60, 64, 67], 'C', 1.77), ([62, 66, 69], 'D', 1 / 3),
                                ([55, 59, 62], 'G', 1 / 3), ([57, 60, 64], 'Am', 1.8)]),
        ('silent_gap', [([48, 52, 55], 'C', 2.03), ([], '?', .8), ([45, 48, 52], 'Am', 2)]),
    ):
        audio, truth = signal(parts)
        cases.append({'name': name, 'audio': audio,
                      'truth': [(start, end, [] if symbol == '?' else [symbol])
                                for start, end, symbol in truth],
                      'negative': False, 'stress': False})
    silence = np.zeros((3 * RATE, 2), np.float32)
    add('silence', silence, [], negative=True)
    add('white_noise_seed17', np.random.default_rng(17).normal(0, .025, silence.shape).astype(np.float32),
        [], negative=True)
    add('single_A2', tone([45]), [], negative=True)
    add('incomplete_C_E', tone([48, 52]), [], negative=True)
    add('chromatic_cluster', tone(list(range(48, 60))), [], negative=True)
    noise = np.random.default_rng(23).normal(0, 1, (4 * RATE, 2)).astype(np.float32)
    add('C_moderate_noise', tone([48, 52, 55], 4) + noise * .2, ['C'])
    add('C_heavy_noise_stress', tone([48, 52, 55], 4) + noise, ['C'], stress=True)
    # A deliberately difficult arpeggio. The expected pitch collection is C,
    # but event onset before all three notes have sounded is not scored.
    mono = np.zeros(4 * RATE)
    for index, onset in enumerate(np.arange(0, 4, .45)):
        start = round(onset * RATE)
        axis = np.arange(len(mono) - start) / RATE
        note = [48, 52, 55][index % 3]
        mono[start:] += .12 * np.sin(2 * np.pi * 440 * 2 ** ((note - 69) / 12) * axis) * np.exp(-axis * 6)
    cases.append({'name': 'decaying_arpeggio_stress',
                  'audio': np.column_stack((mono, mono)).astype(np.float32),
                  'truth': [(.9, 4.0, ['C', 'C/E', 'C/G'])],
                  'negative': False, 'stress': True})
    return cases


def overlap(a, b, start, end):
    return max(0.0, min(b, end) - max(a, start))


def measure(result, truth, duration):
    rows = result['events']
    values = {key: 0.0 for key in (
        'recognized_seconds', 'correct_recognized_seconds', 'incorrect_recognized_seconds',
        'unknown_with_candidates_seconds', 'unknown_without_candidates_seconds',
        'unknown_with_correct_candidate_seconds', 'unknown_candidate_negative_seconds')}
    previous = 0.0
    for row in rows:
        start, end = row['start_seconds'], row['end_seconds']
        if abs(start - previous) > .001 or end <= start:
            raise AssertionError('Non-contiguous or non-positive event interval')
        previous = end
        known = row['chord_type'] != 'unknown'
        alternatives = row.get('alternatives', ())
        if len(alternatives) > 3:
            raise AssertionError('Candidate list exceeds three entries')
        category = ('recognized_seconds' if known else 'unknown_with_candidates_seconds'
                    if alternatives else 'unknown_without_candidates_seconds')
        values[category] += end - start
        for a, b, expected in truth:
            amount = overlap(start, end, a, b)
            if known:
                key = 'correct_recognized_seconds' if row['symbol'] in expected else 'incorrect_recognized_seconds'
                values[key] += amount
            elif alternatives:
                if any(candidate['symbol'] in expected for candidate in alternatives):
                    values['unknown_with_correct_candidate_seconds'] += amount
                if not expected:
                    values['unknown_candidate_negative_seconds'] += amount
    if abs(previous - duration) > .001:
        raise AssertionError('Timeline does not cover the source duration')
    values = {key: round(value, 6) for key, value in values.items()}
    values['event_count'] = len(rows)
    values['events'] = [[row['symbol'], row['start_seconds'], row['end_seconds'],
                        [item['symbol'] for item in row.get('alternatives', ())],
                        row.get('evidence', {}).get('uncertainty_reason')]
                       for row in rows]
    values['reanalysis_diagnostics'] = {key: value for key, value in result.get('diagnostics', {}).items()
                                      if 'reanaly' in key or 'retry' in key or 'recover' in key}
    return values


def promotions(before, after, truth):
    """Separate correct new labels from incorrect new labels in old unknowns."""
    correct = incorrect = 0.0
    for old in before['events']:
        if old['chord_type'] != 'unknown':
            continue
        for new in after['events']:
            if new['chord_type'] == 'unknown':
                continue
            start = max(old['start_seconds'], new['start_seconds'])
            end = min(old['end_seconds'], new['end_seconds'])
            for a, b, expected in truth:
                amount = overlap(start, end, a, b)
                if new['symbol'] in expected:
                    correct += amount
                else:
                    incorrect += amount
    return {'correct_newly_recognized_seconds': round(correct, 6),
            'incorrect_newly_recognized_seconds': round(incorrect, 6)}


def compare(baseline_ref='v0.1.04', methods=('cqt',)):
    old = baseline_modules(baseline_ref)['song_chords']
    # Equal warm-up avoids mixing transform/JIT startup with steady-state work.
    warm = tone([48, 52, 55], 1)
    for method in methods:
        old.analyze_song_chords(warm, RATE, method=method)
        song_chords.analyze_song_chords(warm, RATE, method=method)
    results, failures = [], []
    for case in fixtures():
        for method in methods:
            duration = len(case['audio']) / RATE
            entry = {'case': case['name'], 'method': method, 'duration_seconds': duration,
                     'negative_control': case['negative'], 'stress_case': case['stress'],
                     'truth': case['truth']}
            analyses = {}
            for name, analyzer in (('baseline', old.analyze_song_chords),
                                   ('current', song_chords.analyze_song_chords)):
                start = time.perf_counter()
                result = analyzer(case['audio'], RATE, method=method)
                elapsed = time.perf_counter() - start
                if result['method_id'] != method:
                    raise AssertionError('Selected frontend identity changed')
                analyses[name] = result
                entry[name] = measure(result, case['truth'], duration)
                entry[name]['elapsed_seconds'] = round(elapsed, 4)
            entry['promotions'] = promotions(analyses['baseline'], analyses['current'], case['truth'])
            # Gates compare scored durations, never a raw coverage increase.
            if entry['promotions']['incorrect_newly_recognized_seconds'] > .001:
                failures.append(f"{case['name']}/{method}: incorrect promotion in baseline unknown")
            for metric in ('incorrect_recognized_seconds', 'unknown_candidate_negative_seconds'):
                if entry['current'][metric] > entry['baseline'][metric] + .001:
                    failures.append(f"{case['name']}/{method}: increased {metric}")
            if not case['stress'] and entry['current']['correct_recognized_seconds'] + .001 < entry['baseline']['correct_recognized_seconds']:
                failures.append(f"{case['name']}/{method}: recognized correctness regressed")
            results.append(entry)
    changed = [name for name, digest in SOURCE_HASHES.items()
               if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest]
    if changed:
        failures.append('Source changed during comparison: ' + ', '.join(changed))
    return {'schema': 'tonematch-chord-uncertainty-comparison/v1',
            'created': datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=9))).isoformat(),
            'baseline_ref': baseline_ref, 'methods': list(methods),
            'scope': 'Deterministic development fixtures; no independent or real-song accuracy claim',
            'source_sha256': SOURCE_HASHES,
            'case_count': len(results), 'passed': not failures, 'failures': failures,
            'correct_newly_recognized_seconds': round(sum(row['promotions']['correct_newly_recognized_seconds'] for row in results), 6),
            'incorrect_newly_recognized_seconds': round(sum(row['promotions']['incorrect_newly_recognized_seconds'] for row in results), 6),
            'real_song_accuracy_measured': False, 'cases': results}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-ref', default='v0.1.04')
    parser.add_argument('--methods', nargs='+', choices=('cqt', 'fft'), default=['cqt'])
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = compare(args.baseline_ref, tuple(args.methods))
    text = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + '\n', encoding='utf-8')
        print(json.dumps({key: report[key] for key in ('case_count', 'passed', 'failures',
                         'correct_newly_recognized_seconds', 'incorrect_newly_recognized_seconds')}, ensure_ascii=False))
    else:
        print(text)
    raise SystemExit(0 if report['passed'] else 1)
