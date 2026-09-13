"""실제 C++ DSP를 강제 실행해 NumPy 수치와 동일 작업의 처리 시간을 비교한다."""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from native_dsp import create_spectrum_engine, native_runtime_info  # noqa: E402


def verify() -> dict:
    """여러 PCM 종류와 부분 블록 경계에서 실제 native 결과의 최대 오차를 모은다."""

    rng = np.random.default_rng(8008)
    size, rate = 2048, 44100
    axis = np.arange(size) / rate
    mono = 0.4 * np.sin(2 * np.pi * 440 * axis) + 0.12 * np.sin(2 * np.pi * 2120 * axis)
    blocks = [rng.normal(0, 0.15, (size, 2)), np.column_stack((mono, -mono)),
              np.zeros((size, 2)), np.column_stack((mono, mono)) * 1e-6]
    dirty = blocks[0].copy()
    dirty[:3] = [[np.nan, np.inf], [-np.inf, 2], [-2, 0]]
    blocks.append(dirty)
    pcm = np.concatenate(blocks * 3)
    engines = [create_spectrum_engine(rate, 2, backend=backend) for backend in ("cpp", "numpy")]
    errors = {"waveform": 0.0, "frequency_hz": 0.0, "spectrum_db": 0.0, "rms_db": 0.0,
              "peak_db": 0.0, "centroid_hz": 0.0}
    emitted = 0
    try:
        for start in range(0, len(pcm), 777):
            actual, expected = [engine.push(pcm[start:start + 777]) for engine in engines]
            if actual is None or expected is None:
                assert actual is None and expected is None
                continue
            emitted += 1
            for name, attribute in (("waveform", "waveform"), ("frequency_hz", "frequencies_hz"),
                                    ("spectrum_db", "magnitudes_dbfs"), ("rms_db", "rms_dbfs"),
                                    ("peak_db", "peak_dbfs"), ("centroid_hz", "spectral_centroid_hz")):
                errors[name] = max(errors[name], float(np.max(np.abs(np.asarray(getattr(actual, attribute)) - getattr(expected, attribute)))))
        for name, tolerance in {"waveform": 6e-8, "frequency_hz": 1e-8, "spectrum_db": 2e-5,
                                "rms_db": 1e-9, "peak_db": 1e-9, "centroid_hz": 1e-7}.items():
            if errors[name] > tolerance:
                raise RuntimeError(f"C++ parity failed: {name} error {errors[name]} > {tolerance}")
    finally:
        for engine in engines:
            engine.close()
    return {"ok": True, "runtime": native_runtime_info(), "completed_windows": emitted, "max_absolute_errors": errors}


def benchmark(iterations: int = 512, rounds: int = 5) -> dict:
    """생성·캡처를 제외한 동일 float32 PCM의 bridge 포함 push 지연 분포를 측정한다."""

    rate, size = 44100, 2048
    pcm = np.random.default_rng(8008).normal(0, 0.15, (16, size, 2)).astype(np.float32)
    measurements = {"cpp": [], "numpy": []}
    for round_index in range(rounds):
        for backend in (("cpp", "numpy") if round_index % 2 == 0 else ("numpy", "cpp")):
            engine = create_spectrum_engine(rate, 2, backend=backend)
            try:
                for index in range(32):
                    engine.push(pcm[index % len(pcm)])
                for index in range(iterations):
                    block = pcm[index % len(pcm)]
                    started = time.perf_counter_ns()
                    engine.push(block)
                    measurements[backend].append((time.perf_counter_ns() - started) / 1e6)
            finally:
                engine.close()
    result = {backend: {"median_ms": float(np.median(values)), "p95_ms": float(np.percentile(values, 95)),
                        "p99_ms": float(np.percentile(values, 99)), "max_ms": max(values)}
              for backend, values in measurements.items()}
    return {"scope": "Synthetic PCM push including Python bridge, FFT and smoothing; excludes capture, GUI, AI and offline analysis",
            "python": platform.python_version(), "numpy": np.__version__, "platform": platform.system(),
            "architecture": platform.machine(), "rate_hz": rate, "channels": 2, "fft_size": size,
            "history_size": 4, "input_dtype": "float32", "warmup_per_round": 32,
            "rounds": rounds, "iterations_per_round": iterations, "block_duration_ms": size / rate * 1000,
            "measurements": result, "median_speedup_numpy_over_cpp": result["numpy"]["median_ms"] / result["cpp"]["median_ms"]}


def main() -> int:
    """네이티브 사용을 강제 검증하고 선택적으로 로컬 벤치마크 JSON을 저장한다."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = verify()
    if args.benchmark:
        result["benchmark"] = benchmark()
    rendered = json.dumps(result, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
