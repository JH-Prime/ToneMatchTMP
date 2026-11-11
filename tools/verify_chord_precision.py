"""Bounded, annotated release comparison; synthetic evidence is not song accuracy.

Uses only generated PCM, with no GUI, playback, private files or network. Keep
negative controls and failed cases in the report; coverage is never correctness.
"""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BASELINE_COMMIT = '83e88c10f62f6b174b2f95cf0e68b751a14f4db0'
BASELINE_COMMITS = {
    'v0.1.05': BASELINE_COMMIT,
    'v0.1.06': '7563242b054065f8893a6c6e344046e188e0b947',
    'v0.1.07': 'e8142f80151d5d92b05bc6c3e5c091934e63a093',
}
SOURCE_FILES = ('voicing.py', 'song_chords.py', 'guitar_shapes.py',
                'tools/verify_chord_trace.py', 'tools/verify_chord_uncertainty.py',
                'tools/verify_chord_precision.py')


def source_hashes():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in SOURCE_FILES}


IMPORT_HASHES = source_hashes()
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools'))
import song_chords
from verify_chord_trace import baseline_modules, signal
from verify_chord_uncertainty import measure, overlap, promotions, tone

RATE = 22050
NOTE_NAMES = ('C', 'C♯', 'D', 'E♭', 'E', 'F', 'F♯', 'G', 'A♭', 'A', 'B♭', 'B')
# Evaluation vocabulary is independent of the classifier's mutable templates.
TRIADS = {
    'major': ('', '7', 'maj7', '6', 'add9', '9', 'maj9', '11', 'maj11',
              '13', 'maj13', '6/9', '7b9', '7#9', '7#11', '7b13', 'maj7#11', 'add11'),
    'minor': ('m', 'm7', 'm6', 'm(add9)', 'm9', 'm11', 'm13',
              'm(maj7)', 'm(maj9)', 'm6/9', 'm(add11)'),
    'diminished': ('dim', 'dim7', 'm7b5'),
    'augmented': ('aug', '7#5', 'maj7#5'),
    'flat_fifth_major': ('7b5',),
    'sus2': ('sus2', '7sus2'), 'sus4': ('sus4', '7sus4'), 'power': ('5',),
}
SUFFIX_TRIAD = {suffix: kind for kind, suffixes in TRIADS.items() for suffix in suffixes}


def components(symbol):
    """Return root, root+triad quality, bass; reject unscorable labels."""
    if not isinstance(symbol, str):
        raise ValueError('Chord label must be a string')
    symbol = symbol.replace('♯', '#').replace('♭', 'b')
    match = re.fullmatch(r'([A-G])([#b]?)(.*?)(?:/([A-G])([#b]?))?', symbol)
    if match is None or match[3] not in SUFFIX_TRIAD:
        raise ValueError(f'Unsupported chord label: {symbol!r}')
    natural = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
    accidental = {'': 0, '#': 1, 'b': -1}
    root = (natural[match[1]] + accidental[match[2]]) % 12
    bass = ((natural[match[4]] + accidental[match[5]]) % 12
            if match[4] else root)
    return root, (root, SUFFIX_TRIAD[match[3]]), bass


def validate_annotations(truth, duration):
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError('Duration must be finite and positive')
    previous = 0.0
    for start, end, expected in truth:
        if (not math.isfinite(start) or not math.isfinite(end)
                or start < previous or end <= start or start < 0 or end > duration):
            raise ValueError('Annotations must be finite, ordered, nonoverlapping and in bounds')
        if not isinstance(expected, (list, tuple)):
            raise ValueError('Expected labels must be a list; an empty list denotes no chord')
        for symbol in expected:
            components(symbol)
        previous = end


def precision_metrics(result, truth, duration):
    """Duration-weighted exact correctness plus independent harmonic components.

    Annotation gaps are unscored, not unknown truth. Empty label lists are
    negative controls. Multiple declared labels are accepted without adding
    their overlapping durations twice. Component scores never replace exact
    symbol correctness, and are defined only for positive chord annotations.
    """
    validate_annotations(truth, duration)
    previous = 0.0
    for row in result['events']:
        start, end = row['start_seconds'], row['end_seconds']
        if (not math.isfinite(start) or not math.isfinite(end)
                or abs(start - previous) > .001 or end <= start
                or start < 0 or end > duration + .001):
            raise ValueError('Predictions must form a finite contiguous bounded timeline')
        known = row['chord_type'] != 'unknown'
        if known:
            components(row['symbol'])
        elif row['symbol'] != '?':
            raise ValueError('An unknown prediction must use the unknown symbol')
        for candidate in row.get('alternatives', ()):
            components(candidate['symbol'])
        previous = end
    if abs(previous - duration) > .001:
        raise ValueError('Prediction timeline must cover the source duration')
    values = measure(result, truth, duration)
    values.update({key: 0.0 for key in ('root_correct_seconds', 'triad_correct_seconds',
                                      'bass_correct_seconds', 'scored_unknown_seconds',
                                      'negative_unknown_seconds')})
    for row in result['events']:
        known = row['chord_type'] != 'unknown'
        actual = components(row['symbol']) if known else None
        for start, end, expected in truth:
            amount = overlap(row['start_seconds'], row['end_seconds'], start, end)
            if not known:
                values['scored_unknown_seconds'] += amount
                if not expected:
                    values['negative_unknown_seconds'] += amount
            elif expected:
                expected_parts = [components(symbol) for symbol in expected]
                for index, name in enumerate(('root', 'triad', 'bass')):
                    if any(actual[index] == target[index] for target in expected_parts):
                        values[f'{name}_correct_seconds'] += amount
    values['scored_seconds'] = sum(end - start for start, end, _ in truth)
    values['unscored_seconds'] = duration - values['scored_seconds']
    values['chord_truth_seconds'] = sum(end - start for start, end, labels in truth if labels)
    values['negative_truth_seconds'] = values['scored_seconds'] - values['chord_truth_seconds']
    return {key: round(value, 6) if isinstance(value, float) else value
            for key, value in values.items()}


def regression_failures(before, after, changes):
    failures = []
    if changes['incorrect_newly_recognized_seconds'] > .001:
        failures.append('incorrect promotion in baseline unknown')
    for metric in ('incorrect_recognized_seconds', 'unknown_candidate_negative_seconds'):
        if after[metric] > before[metric] + .001:
            failures.append('increased ' + metric)
    if after['correct_recognized_seconds'] + .001 < before['correct_recognized_seconds']:
        failures.append('recognized correctness regressed')
    return failures


def harmonic_singleton(note, duration=2.4):
    axis = np.arange(round(RATE * duration)) / RATE
    frequency = 440 * 2 ** ((note - 69) / 12)
    mono = sum(np.sin(2 * np.pi * frequency * harmonic * axis) / harmonic
               for harmonic in range(1, 25) if frequency * harmonic < RATE / 2) * .1
    return np.column_stack((mono, -mono)).astype(np.float32)


def resonant_singleton(note, shape, duration=2.4):
    """One fundamental with resonant partials, not independent chord tones."""
    if shape not in ('formant', 'comb3', 'comb4'):
        raise ValueError('Unsupported harmonic envelope')
    axis = np.arange(round(RATE * duration)) / RATE
    frequency = 440 * 2 ** ((note - 69) / 12)
    mono = np.zeros(len(axis))
    for harmonic in range(1, 25):
        if frequency * harmonic >= RATE / 2:
            break
        weight = ((1 + 8 * np.exp(-((harmonic - 3) / 1.1) ** 2)) / harmonic
                  if shape == 'formant' else
                  (8 if harmonic % int(shape[-1]) == 0 else 1) / harmonic)
        mono += weight * np.sin(2 * np.pi * frequency * harmonic * axis)
    mono *= .2 / np.max(np.abs(mono))
    return np.column_stack((mono, -mono)).astype(np.float32)


def arpeggio(notes, duration=3.6, interval=.15):
    mono = np.zeros(round(RATE * duration))
    for index, onset in enumerate(np.arange(0, duration, interval)):
        start = round(onset * RATE)
        axis = np.arange(len(mono) - start) / RATE
        frequency = 440 * 2 ** ((notes[index % len(notes)] - 69) / 12)
        mono[start:] += .12 * np.sin(2 * np.pi * frequency * axis) * np.exp(-6 * axis)
    return np.column_stack((mono, mono)).astype(np.float32)


def fixtures():
    """Development and transposed controls, not an independently held-out set."""
    cases = []

    def add(name, audio, labels, start=0.0):
        cases.append({'name': name, 'audio': audio,
                      'truth': [(start, len(audio) / RATE, labels)]})

    for root in (0, 3, 8):
        label = NOTE_NAMES[root]
        add(f'low_bass_major_root_{root}', tone([36 + root, 52 + root, 55 + root], 2.4), [label])
        add(f'harmonic_singleton_root_{root}', harmonic_singleton(36 + root), [])
    # A strong formant or periodic partial envelope must not count as several
    # independently played notes. Keep transposed controls and comb4 even when
    # that particular shape already abstained before the repair.
    for shape in ('formant', 'comb3', 'comb4'):
        for note in (36, 48, 57):
            add(f'{shape}_singleton_midi_{note}', resonant_singleton(note, shape), [])
    # A weak independent tone does not make the bass's loud third partial an
    # independently played fifth. These inputs vetoed the residual experiment.
    for note in (50, 58, 61):
        audio = resonant_singleton(36, 'formant')
        axis = np.arange(len(audio)) / RATE
        weak = .006 * np.sin(2 * np.pi * 440 * 2 ** ((note - 69) / 12) * axis)
        audio = (audio + np.column_stack((weak, -weak))).astype(np.float32)
        add(f'formant_with_weak_anchor_midi_{note}', audio, [])
    for root, third, seventh, suffix in ((0, 4, 10, '7'), (3, 4, 11, 'maj7'), (8, 3, 10, 'm7')):
        add(f'omitted_fifth_{suffix}_root_{root}',
            tone([48 + root, 48 + root + third, 48 + root + seventh], 2.4),
            [NOTE_NAMES[root] + suffix])
    for notes in ((48, 52, 55), (51, 55, 58), (60, 64, 67)):
        root = notes[0] % 12
        label = NOTE_NAMES[root]
        # All three notes have sounded by .3 s; an extra .15 s is unscored
        # attack stabilization, declared before any analyzer result is read.
        add(f'decaying_arpeggio_midi_{notes[0]}', arpeggio(notes),
            [label, label + '/' + NOTE_NAMES[notes[1] % 12],
             label + '/' + NOTE_NAMES[notes[2] % 12]], start=.45)
    add('inversion_E_bass', tone([40, 48, 55], 2.4), ['C/E'])
    rapid, annotations = signal([([60, 64, 67], 'C', 1.77), ([62, 66, 69], 'D', 1 / 3),
                                 ([55, 59, 62], 'G', 1 / 3), ([57, 60, 64], 'Am', 1.8)])
    cases.append({'name': 'tempo_180_quarter_changes', 'audio': rapid,
                  'truth': [(start, end, [label]) for start, end, label in annotations], 'bpm': 180})
    modulation, annotations = signal([([48, 52, 55], 'C', 2.13), ([52, 56, 59], 'E', .8),
                                      ([45, 48, 52], 'Am', 2.2), ([42, 49, 57], 'F♯m', 2.1)])
    cases.append({'name': 'brief_secondary_dominant', 'audio': modulation,
                  'truth': [(start, end, [label]) for start, end, label in annotations]})
    sustained = tone([48, 52, 55], 5)
    melody = tone([74], .3) * .45
    start = round(2.1 * RATE)
    sustained[start:start + len(melody)] += melody
    # The annotation follows the existing trace contract: a brief passing D
    # over sustained C is not a harmonic change to Cadd9.
    add('passing_melody_over_C', sustained, ['C'])
    silence = np.zeros((round(RATE * 2.4), 2), np.float32)
    add('silence', silence, [])
    add('noise_seed106', np.random.default_rng(106).normal(0, .05, silence.shape).astype(np.float32), [])
    add('bare_third_not_completed', tone([48, 52], 2.4), [])
    return cases


def compare(baseline_ref='v0.1.05', methods=('cqt', 'fft')):
    if not methods or len(set(methods)) != len(methods) or not set(methods) <= {'cqt', 'fft'}:
        raise ValueError('Select cqt and/or fft once each')
    if baseline_ref not in BASELINE_COMMITS:
        raise ValueError('Unsupported precision baseline')
    before_hashes = source_hashes()
    if before_hashes != IMPORT_HASHES:
        raise RuntimeError('Source changed after import; restart the comparison')
    commit = subprocess.check_output(['git', 'rev-parse', '--verify', baseline_ref + '^{commit}'],
                                     cwd=ROOT, text=True).strip()
    if commit != BASELINE_COMMITS[baseline_ref]:
        raise ValueError(f'Precision baseline must resolve to immutable {baseline_ref} source')
    baseline_hashes = {name: hashlib.sha256(subprocess.check_output(
        ['git', 'show', f'{commit}:{name}'], cwd=ROOT)).hexdigest()
        for name in ('voicing.py', 'song_chords.py', 'guitar_shapes.py')}
    # The isolated loader replaces only the analyzer modules. Its shared
    # guitar_shapes import must therefore still be the tagged implementation.
    if before_hashes['guitar_shapes.py'] != baseline_hashes['guitar_shapes.py']:
        raise RuntimeError('Shared baseline dependency differs: guitar_shapes.py')
    old = baseline_modules(commit)['song_chords']
    warm = tone([48, 52, 55], 1)
    for method in methods:
        old.analyze_song_chords(warm, RATE, method=method)
        song_chords.analyze_song_chords(warm, RATE, method=method)
    rows, failures = [], []
    for case in fixtures():
        duration = len(case['audio']) / RATE
        validate_annotations(case['truth'], duration)
        for method in methods:
            entry = {'case': case['name'], 'method': method, 'duration_seconds': duration,
                     'truth': case['truth'], 'audio_sha256': hashlib.sha256(case['audio'].tobytes()).hexdigest()}
            results = {}
            for name, analyzer in (('baseline', old.analyze_song_chords),
                                   ('current', song_chords.analyze_song_chords)):
                start = time.perf_counter()
                result = analyzer(case['audio'], RATE, method=method)
                elapsed = time.perf_counter() - start
                if result['method_id'] != method:
                    raise AssertionError('Selected analysis frontend changed')
                results[name] = result
                entry[name] = precision_metrics(result, case['truth'], duration)
                entry[name]['elapsed_seconds'] = round(elapsed, 4)
            entry['promotions'] = promotions(results['baseline'], results['current'], case['truth'])
            entry['failures'] = regression_failures(entry['baseline'], entry['current'], entry['promotions'])
            failures.extend(f"{case['name']}/{method}: {failure}" for failure in entry['failures'])
            rows.append(entry)
    after_hashes = source_hashes()
    if after_hashes != before_hashes:
        failures.append('Source changed during comparison; results are invalid')
    aggregate_keys = ('correct_recognized_seconds', 'incorrect_recognized_seconds',
                      'scored_unknown_seconds', 'root_correct_seconds', 'triad_correct_seconds',
                      'bass_correct_seconds', 'scored_seconds', 'chord_truth_seconds', 'elapsed_seconds')
    aggregate = {name: {key: round(sum(row[name][key] for row in rows), 6)
                        for key in aggregate_keys} for name in ('baseline', 'current')}
    return {'schema': 'tonematch-chord-precision-comparison/v1',
            'created': datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=9))).isoformat(),
            'baseline_ref': baseline_ref, 'baseline_commit': commit, 'baseline_source_sha256': baseline_hashes,
            'source_sha256_before': before_hashes, 'source_sha256_after': after_hashes,
            'methods': list(methods), 'case_count': len(rows), 'sample_rate': RATE,
            'scope': 'Deterministic development fixtures and transposed controls; not independent song accuracy',
            'real_song_accuracy_measured': False, 'aggregate': aggregate,
            'correct_newly_recognized_seconds': round(sum(row['promotions']['correct_newly_recognized_seconds'] for row in rows), 6),
            'incorrect_newly_recognized_seconds': round(sum(row['promotions']['incorrect_newly_recognized_seconds'] for row in rows), 6),
            'passed': not failures, 'failures': failures, 'cases': rows}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-ref', default='v0.1.05')
    parser.add_argument('--methods', nargs='+', choices=('cqt', 'fft'), default=['cqt', 'fft'])
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
