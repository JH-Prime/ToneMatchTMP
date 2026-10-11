"""Local annotated-signal comparison; never reports real-song accuracy."""
import argparse
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import statistics
import subprocess
import sys
import time
import types
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import song_chords
import voicing

RATE = 22050


def baseline_modules(ref):
    modules = {}
    for name in ('voicing', 'song_chords'):
        source = subprocess.check_output(['git', 'show', f'{ref}:{name}.py'], cwd=ROOT).decode('utf-8')
        module = types.ModuleType('_trace_baseline_' + name)
        # Dataclasses resolve their module while class definitions are executed.
        with patch.dict(sys.modules, {module.__name__: module, **modules}):
            exec(compile(source, f'{ref}/{name}.py', 'exec'), module.__dict__)
        modules[name] = module
    return modules


def signal(parts, cents=0):
    blocks, annotations, start = [], [], 0.0
    for notes, symbol, duration in parts:
        axis = np.arange(round(RATE * duration)) / RATE
        mono = sum(np.sin(2 * np.pi * 440 * 2 ** ((note + cents / 100 - 69) / 12) * axis)
                   for note in notes) * (.25 / max(1, len(notes))) if notes else np.zeros_like(axis)
        blocks.append(np.column_stack((mono, mono)).astype(np.float32))
        end = start + len(mono) / RATE
        annotations.append((start, end, symbol))
        start = end
    return np.concatenate(blocks), annotations


def metrics(rows, truth, bpm=None):
    correct = sum(max(0, min(row['end_seconds'], end) - max(row['start_seconds'], start))
                  for row in rows for start, end, symbol in truth if row['symbol'] == symbol)
    boundaries = []
    for left, right in zip(truth, truth[1:]):
        candidates = [abs(a['end_seconds'] - left[1]) for a, b in zip(rows, rows[1:])
                      if a['symbol'] == left[2] and b['symbol'] == right[2]]
        boundaries.append(round(min(candidates), 4) if candidates else None)
    return {'duration_weighted_symbol_agreement': round(correct / truth[-1][1], 6),
            'correctly_labeled_seconds': round(correct, 6),
            'boundary_errors_seconds': boundaries,
            'boundary_errors_beats': ([None if value is None else round(value * bpm / 60, 4)
                                       for value in boundaries] if bpm else None),
            'missing_expected_transitions': sum(value is None for value in boundaries),
            'events': [[r['symbol'], r['start_seconds'], r['end_seconds']] for r in rows]}


def compare(baseline_ref):
    old = baseline_modules(baseline_ref)
    c, am, fs = ([48, 52, 55], 'C'), ([45, 48, 52], 'Am'), ([42, 49, 57], 'F♯m')
    cases = [
        ('brief_secondary_dominant', [(*c, 2.13), ([52, 56, 59], 'E', .8), (*am, 2.2), (*fs, 2.1)], 0),
        ('early_boundary', [(*c, 1.73), (*fs, 2.37)], 0),
        ('batch_seam_positive_tuning', [(*c, 6.13), (*fs, 2.37)], 30),
        ('batch_seam_negative_tuning', [(*c, 6.37), (*fs, 2.37)], -30),
        ('extension_and_inversion', [(*c, 2), ([48, 52, 55, 62], 'Cadd9', 2), ([40, 48, 55], 'C/E', 2)], 0),
        ('silent_gap', [(*c, 2.03), ([], '?', .8), (*am, 2)], 0),
        ('held_out_sus', [([50, 55, 57], 'Dsus4', 2.47), ([43, 47, 50], 'G', .9), ([45, 48, 52], 'Am', 2.34)], 0),
        ('held_out_low_register', [([36, 40, 43], 'C', 3.17), ([33, 36, 40], 'Am', 2.53)], 0),
        ('held_out_other_root', [([53, 57, 60], 'F', 1.91), ([50, 53, 57], 'Dm', .87), ([47, 51, 54], 'B', 2.29)], 0),
        ('tempo_180_quarter_notes', [([60, 64, 67], 'C', 1.77), ([62, 66, 69], 'D', 1 / 3),
                                    ([55, 59, 62], 'G', 1 / 3), ([57, 60, 64], 'Am', 1.8)], 0),
        ('tempo_180_song_edges', [([60, 64, 67], 'C', 1 / 3), ([62, 66, 69], 'D', 2),
                                ([55, 59, 62], 'G', 1 / 3)], 0),
    ]
    # Warm the shared transform/JIT runtime equally; do not compare cold versus warm.
    warm, _ = signal([(*c, 1)])
    for analyzer in (old['song_chords'].analyze_song_chords, song_chords.analyze_song_chords):
        analyzer(warm, RATE)
    results = []
    for name, parts, cents in cases:
        audio, truth = signal(parts, cents)
        bpm = 180 if name.startswith('tempo_180_') else None
        entry = {'case': name, 'duration_seconds': len(audio) / RATE, 'tuning_cents': cents, 'bpm': bpm}
        for key, analyzer in (('baseline', old['song_chords'].analyze_song_chords), ('current', song_chords.analyze_song_chords)):
            start = time.perf_counter()
            result = analyzer(audio, RATE)
            entry[key] = metrics(result['events'], truth, bpm)
            entry[key]['elapsed_seconds'] = round(time.perf_counter() - start, 4)
        results.append(entry)
    pool = [dict(voicing._unknown_window({}), root_pc=root, chord_type=kind,
                 symbol=f'{root}:{kind}', _score=.7 + ((root + i) % 3) * .01)
            for i, kind in enumerate(('major', 'minor')) for root in range(12)]
    windows = [dict(pool[i % len(pool)], _candidates=pool, _start_seconds=i * .2) for i in range(6000)]
    benchmarks, signatures = {}, {}
    for key, decoder in (('baseline', old['voicing']._smooth_labels), ('current', voicing._smooth_labels)):
        times = []
        for _ in range(3):
            start = time.perf_counter()
            rows = decoder(windows)
            times.append(time.perf_counter() - start)
        benchmarks[key] = {'runs_seconds': times, 'median_seconds': statistics.median(times)}
        signatures[key] = [(r['root_pc'], r['chord_type']) for r in rows]
    assert signatures['baseline'] == signatures['current']
    total_seconds = sum(entry['duration_seconds'] for entry in results)
    aggregate = {key: sum(entry[key]['correctly_labeled_seconds'] for entry in results) / total_seconds
                 for key in ('baseline', 'current')}
    return {'schema': 'tonematch-chord-trace-comparison/v1', 'baseline_ref': baseline_ref,
            'created': datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=9))).isoformat(),
            'scope': f'{len(cases)} synthetic annotated sequences; not a real-song accuracy benchmark',
            'aggregate_duration_weighted_symbol_agreement': aggregate,
            'cases': results, 'decoder_benchmark': benchmarks,
            'decoder_observations': 6000, 'decoder_candidates_per_observation': 24,
            'decoder_legacy_objective_preserved': True, 'real_song_accuracy_measured': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-ref', default='1edefc6')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = compare(args.baseline_ref)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + '\n', encoding='utf-8')
    else:
        print(text)
