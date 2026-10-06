"""CQT와 이전 FFT를 같은 합성 입력으로 비교하며 실음원 정확도로 오해하지 않는다."""

import argparse
import json
from pathlib import Path
import sys
import time

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from song_chords import analyze_song_chords
from voicing import CHORD_INTERVALS, analyze_voicings, voicing_analysis_dict


def synthesize(notes, harmonic=False):
    """배음 유무만 다른 2.4초 화음을 만들고 두 분석기에 같은 PCM을 준다."""
    time_axis = np.arange(52920) / 22050
    audio = np.zeros(len(time_axis))
    for note in notes:
        frequency = 440 * 2 ** ((note - 69) / 12)
        for partial, gain in ((1, 1), (2, .35), (3, .2), (4, .1), (5, .07)) if harmonic else ((1, 1),):
            audio += gain * np.sin(2 * np.pi * frequency * partial * time_axis)
    audio *= .7 / max(1, np.max(np.abs(audio)))
    return np.column_stack((audio, audio)).astype(np.float32)


def benchmark(output):
    """동일 사례의 가장 긴 구간과 후보를 평가하고 실패 사례도 결과에 남긴다."""
    result = {"scope": "synthetic_regression_not_real_song_accuracy", "case_count": 0, "frontends": {}}
    methods = {"fft": lambda audio: voicing_analysis_dict(analyze_voicings(audio, 22050)),
               "cqt": lambda audio: analyze_song_chords(audio, 22050)}
    for name in methods:
        result["frontends"][name] = {"top_one": 0, "candidate_included": 0, "seconds": 0, "failures": []}
    for harmonic in (False, True):
        for root in (0, 4, 9):
            for quality, intervals in CHORD_INTERVALS.items():
                audio = synthesize([48 + root + note for note in intervals], harmonic)
                result["case_count"] += 1
                for name, analyze in methods.items():
                    started = time.perf_counter()
                    data = analyze(audio)
                    result["frontends"][name]["seconds"] += time.perf_counter() - started
                    event = max(data["events"], key=lambda item: item["end_seconds"] - item["start_seconds"])
                    main = (event["root_pc"], event["chord_type"])
                    options = {main} | {(item["root_pc"], item["chord_type"]) for item in event.get("alternatives", [])}
                    result["frontends"][name]["top_one"] += int(main == (root, quality))
                    result["frontends"][name]["candidate_included"] += int((root, quality) in options)
                    if (root, quality) not in options:
                        result["frontends"][name]["failures"].append(
                            {"root": root, "quality": quality, "harmonic": harmonic, "prediction": event["symbol"]})
    Path(output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({**result, "frontends": {key: {k: v for k, v in value.items() if k != "failures"}
                                              for key, value in result["frontends"].items()}}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    benchmark(parser.parse_args().output)
