"""정답을 아는 합성 입력으로 코드 판별을 비교한다. 실제 곡 정확도 평가가 아니다."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
import types

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import voicing


CASES = {
    "power5": (0, 7), "major": (0, 4, 7), "minor": (0, 3, 7),
    "sus2": (0, 2, 7), "sus4": (0, 5, 7), "dim": (0, 3, 6),
    "7": (0, 4, 7, 10), "maj7": (0, 4, 7, 11), "min7": (0, 3, 7, 10),
    "6": (0, 4, 7, 9), "min6": (0, 3, 7, 9), "min7b5": (0, 3, 6, 10),
    "dim7": (0, 3, 6, 9), "aug": (0, 4, 8), "add9": (0, 4, 7, 14),
    "minadd9": (0, 3, 7, 14), "9": (0, 4, 7, 10, 14),
    "maj9": (0, 4, 7, 11, 14), "min9": (0, 3, 7, 10, 14), "7sus4": (0, 5, 7, 10),
    "7sus2": (0, 2, 7, 10), "11": (0, 4, 7, 10, 14, 17),
    "maj11": (0, 4, 7, 11, 14, 17), "min11": (0, 3, 7, 10, 14, 17),
    "13": (0, 4, 7, 10, 14, 17, 21), "maj13": (0, 4, 7, 11, 14, 17, 21),
    "min13": (0, 3, 7, 10, 14, 17, 21), "minmaj7": (0, 3, 7, 11),
    "minmaj9": (0, 3, 7, 11, 14), "6add9": (0, 4, 7, 9, 14),
    "min6add9": (0, 3, 7, 9, 14), "7b5": (0, 4, 6, 10),
    "7sharp5": (0, 4, 8, 10), "7b9": (0, 4, 7, 10, 13),
    "7sharp9": (0, 4, 7, 10, 15), "7sharp11": (0, 4, 7, 10, 18),
    "7b13": (0, 4, 7, 10, 20), "maj7sharp5": (0, 4, 8, 11),
    "maj7sharp11": (0, 4, 7, 11, 18), "add11": (0, 4, 7, 17),
    "minadd11": (0, 3, 7, 17),
}
RATE = 22_050


def synthesize(notes: tuple[int, ...], texture: str, seed: int) -> np.ndarray:
    """동일한 정답 음에 서로 다른 배음·발음 시차·감쇠·약한 잡음을 적용한다."""
    axis = np.arange(int(RATE * 2.4)) / RATE
    rng = np.random.default_rng(seed)
    mono = np.zeros(len(axis))
    for index, note in enumerate(notes):
        onset = index * 0.032 if texture == "picked_noisy" else 0.0
        elapsed = np.maximum(0.0, axis - onset)
        envelope = np.where(axis >= onset, (1.0 - np.exp(-elapsed / 0.006)) * np.exp(-elapsed / 2.0), 0.0)
        frequency = 440.0 * 2.0 ** ((note - 69) / 12.0)
        amplitude = rng.uniform(0.8, 1.1) if texture == "picked_noisy" else 1.0
        for harmonic, gain in ((1, 1.0), (2, 0.28), (3, 0.13), (4, 0.06)):
            mono += amplitude * envelope * gain * np.sin(2 * np.pi * frequency * harmonic * elapsed)
    mono *= 0.6 / max(float(np.max(np.abs(mono))), 1e-12)
    if texture == "picked_noisy":
        mono += rng.normal(0.0, 0.002, len(mono))
    return np.column_stack((mono, np.roll(mono, 5) * 0.97)).astype(np.float32)


def summarize(module, samples: np.ndarray, expected: tuple[int, str] | None) -> dict:
    """가장 긴 확정 구간의 이름과 대안 포함 여부를 정답과 비교한다."""
    analysis = module.analyze_voicings(samples, RATE)
    durations = {}
    candidates = set()
    for event in analysis.events:
        if event.chord_type == "unknown":
            continue
        label = (event.root_pc, event.chord_type)
        durations[label] = durations.get(label, 0.0) + event.end_seconds - event.start_seconds
        candidates.add(label)
        for item in getattr(event, "alternatives", ()):
            candidates.add((item["root_pc"], item["chord_type"]))
    primary = max(durations, key=durations.get) if durations else None
    return {"primary": list(primary) if primary else None,
            "exact_primary": primary == expected,
            "expected_present_anywhere": expected in candidates if expected else not candidates,
            "tonal_coverage": analysis.tonal_coverage}


def load_baseline(reference: str):
    """명시한 로컬 Git 리비전에서 이전 분석기만 메모리로 읽는다."""
    source = subprocess.check_output(["git", "show", f"{reference}:voicing.py"], cwd=ROOT, encoding="utf-8")
    module = types.ModuleType("voicing_benchmark_baseline")
    sys.modules[module.__name__] = module
    exec(compile(source, f"{reference}:voicing.py", "exec"), module.__dict__)
    return module


def main() -> None:
    """고정된 984개 코드·36개 비화음 대조 사례를 실행하고 새 JSON 보고서를 만든다."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-ref", default="v0.0.11")
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    if arguments.output.exists():
        parser.error("결과 경로는 새 파일이어야 합니다.")
    baseline = load_baseline(arguments.baseline_ref)
    results = []
    started = time.perf_counter()
    for index, (quality, intervals) in enumerate(CASES.items()):
        for root in range(12):
            for texture in ("sustained_harmonic", "picked_noisy"):
                pcm = synthesize(tuple(48 + root + interval for interval in intervals), texture, index * 100 + root)
                results.append({"quality": quality, "root_pc": root, "texture": texture,
                                "baseline": summarize(baseline, pcm, (root, quality)),
                                "current": summarize(voicing, pcm, (root, quality))})
    controls = []
    for root in range(12):
        for kind in ("single_note", "nonchord_dyad", "noise"):
            pcm = (np.random.default_rng(root).normal(0, 0.04, (RATE * 2, 2)).astype(np.float32)
                   if kind == "noise" else synthesize((48 + root,) if kind == "single_note" else (48 + root, 49 + root), "picked_noisy", root))
            controls.append({"kind": kind, "root_pc": root,
                             "baseline": summarize(baseline, pcm, None), "current": summarize(voicing, pcm, None)})
    totals = {}
    for name in ("baseline", "current"):
        totals[name] = {"exact_primary_cases": sum(item[name]["exact_primary"] for item in results),
                        "expected_present_anywhere_cases": sum(item[name]["expected_present_anywhere"] for item in results),
                        "negative_controls_rejected": sum(item[name]["exact_primary"] for item in controls),
                        "per_quality_exact": {quality: sum(item[name]["exact_primary"] for item in results if item["quality"] == quality) for quality in CASES}}
    payload = {"schema": "tonematch-synthetic-voicing-benchmark/v1", "baseline_ref": arguments.baseline_ref,
               "scope": "Deterministic root-position synthetic chords only; NOT measured real-song or fingering accuracy. Equal pitch-class sets can have several valid names. Expected-present-anywhere is not a top-label accuracy measure.",
               "case_count": len(results), "negative_control_count": len(controls), "sample_rate": RATE,
               "elapsed_seconds": round(time.perf_counter() - started, 3), "totals": totals,
               "cases": results, "negative_controls": controls}
    with arguments.output.open("x", encoding="utf-8") as destination:
        json.dump(payload, destination, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps({key: value for key, value in payload.items() if key not in ("cases", "negative_controls")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
