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


def verify_dtype(dtype: type) -> dict:
    """하나의 입력 정밀도에서 실제 native 결과와 누적 카운터를 매 블록 비교한다."""

    rng = np.random.default_rng(8008)
    size, rate = 2048, 44100
    axis = np.arange(size) / rate
    mono = 0.4 * np.sin(2 * np.pi * 440 * axis) + 0.12 * np.sin(2 * np.pi * 2120 * axis)
    blocks = [rng.normal(0, 0.15, (size, 2)), np.column_stack((mono, -mono)),
              np.zeros((size, 2)), np.column_stack((mono, mono)) * 1e-6]
    dirty = blocks[0].copy()
    dirty[:3] = [[np.nan, np.inf], [-np.inf, 2], [-2, 0]]
    blocks.append(dirty)
    pcm = np.concatenate(blocks * 3).astype(dtype)
    engines = [create_spectrum_engine(rate, 2, backend=backend) for backend in ("cpp", "numpy")]
    errors = {"waveform": 0.0, "frequency_hz": 0.0, "spectrum_db": 0.0, "rms_db": 0.0,
              "peak_db": 0.0, "centroid_hz": 0.0}
    emitted = 0
    try:
        for start in range(0, len(pcm), 777):
            actual, expected = [engine.push(pcm[start:start + 777]) for engine in engines]
            accepted = min(start + 777, len(pcm))
            counters = {"input_frames": accepted, "completed_windows": accepted // size,
                        "pending_frames": accepted % size}
            if any(engine.stream_stats() != counters for engine in engines):
                raise RuntimeError("Native or NumPy stream counters differ from accepted PCM.")
            if actual is None or expected is None:
                if actual is not None or expected is not None:
                    raise RuntimeError("Native and NumPy emission boundaries differ.")
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
        for engine in engines:
            engine.reset()
            if any(engine.stream_stats().values()):
                raise RuntimeError("Reset did not clear stream counters.")
    finally:
        for engine in engines:
            engine.close()
    return {"input_dtype": np.dtype(dtype).name, "completed_windows": emitted,
            "max_absolute_errors": errors, "stream_stats_ok": True, "reset_stats_ok": True}


def verify() -> dict:
    """float32 직접 입력과 기존 float64 입력을 실제 ABI 2에서 각각 검증한다."""

    runtime = native_runtime_info()
    if not runtime["available"] or runtime["backend"] != "cpp" or runtime["abi_version"] != 2:
        raise RuntimeError("Release verification requires actual C++ ABI 2.")
    cases = [verify_dtype(dtype) for dtype in (np.float32, np.float64)]
    errors = {name: max(case["max_absolute_errors"][name] for case in cases)
              for name in cases[0]["max_absolute_errors"]}
    return {"ok": True, "runtime": runtime, "completed_windows": sum(case["completed_windows"] for case in cases),
            "max_absolute_errors": errors, "input_cases": cases,
            "float32_parity_ok": True, "stream_stats_ok": True}


def benchmark(iterations: int = 512, rounds: int = 5) -> dict:
    """생성·캡처를 제외한 동일 float32 PCM의 bridge 포함 push 지연 분포를 측정한다."""

    rate, size = 44100, 2048
    pcm = np.random.default_rng(8008).normal(0, 0.15, (16, size, 2)).astype(np.float32)
    measurements = {"cpp": [], "numpy": [], "cpp_float64_input": []}
    labels = tuple(measurements)
    for round_index in range(rounds):
        order = labels[round_index % len(labels):] + labels[:round_index % len(labels)]
        if round_index % 2:
            order = order[::-1]
        for label in order:
            engine = create_spectrum_engine(rate, 2, backend="numpy" if label == "numpy" else "cpp")
            try:
                for index in range(32):
                    block = pcm[index % len(pcm)]
                    engine.push(block.astype(np.float64) if label == "cpp_float64_input" else block)
                for index in range(iterations):
                    block = pcm[index % len(pcm)]
                    started = time.perf_counter_ns()
                    # ABI 1과 같은 float32→float64 입력 복사 비용을 포함한 ABI 2 대조 경로이다.
                    if label == "cpp_float64_input":
                        block = block.astype(np.float64)
                    engine.push(block)
                    measurements[label].append((time.perf_counter_ns() - started) / 1e6)
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
            "measurements": result, "median_speedup_numpy_over_cpp": result["numpy"]["median_ms"] / result["cpp"]["median_ms"],
            "float64_control_scope": "Same ABI 2 DLL, with float32-to-float64 input allocation inside the timer; not a v0.0.08 binary comparison",
            "avoided_float64_input_allocation_bytes_per_push": size * 2 * 8,
            "order": "Rotating and alternating all three paths; warmup for each path in every round"}


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
