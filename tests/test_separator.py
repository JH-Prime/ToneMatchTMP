"""Demucs 기타 분리기의 CPU·CUDA 장치 선택과 런타임 진단 회귀 테스트."""

from __future__ import annotations

import sys
import tempfile
import types
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

import numpy as np


MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

import separator  # noqa: E402


class _FakeCuda:
    """실제 NVIDIA GPU 없이 CUDA 상태와 장치 정보를 흉내 낸다."""

    def __init__(self, available: bool) -> None:
        """테스트할 CUDA 사용 가능 여부와 호출 기록을 초기화한다."""
        self._available = available
        self.synchronize_calls = 0
        self.reset_calls = 0
        self.empty_cache_calls = 0

    def is_available(self) -> bool:
        """설정된 CUDA 사용 가능 여부를 반환한다."""
        return self._available

    def device_count(self) -> int:
        """CUDA 사용 가능 여부에 따라 가상 GPU 개수를 반환한다."""
        return 1 if self._available else 0

    def get_device_properties(self, _index: int) -> object:
        """가상 GPU의 이름·VRAM·연산 능력 정보를 반환한다."""
        return types.SimpleNamespace(
            name="Test RTX",
            total_memory=12 * 1024**3,
            major=8,
            minor=9,
        )

    def mem_get_info(self, _index: int) -> tuple[int, int]:
        """가상 GPU의 여유 메모리와 전체 메모리를 바이트로 반환한다."""
        return 7 * 1024**3, 12 * 1024**3

    def synchronize(self) -> None:
        """가상 CUDA 동기화 호출 횟수를 기록한다."""
        self.synchronize_calls += 1

    def reset_peak_memory_stats(self) -> None:
        """가상 CUDA 최대 메모리 통계 초기화 호출을 기록한다."""
        self.reset_calls += 1

    def max_memory_allocated(self) -> int:
        """테스트에서 확인할 고정 최대 GPU 메모리 사용량을 반환한다."""
        return 3_456

    def empty_cache(self) -> None:
        """가상 CUDA 캐시 정리 호출 횟수를 기록한다."""
        self.empty_cache_calls += 1


class _FakeTensor:
    """분리 입출력에 필요한 최소 텐서 동작을 NumPy 배열로 흉내 낸다."""

    def __init__(self, values: np.ndarray) -> None:
        """텐서가 감쌀 float32 배열을 저장한다."""
        self.values = np.asarray(values, dtype=np.float32)

    def detach(self) -> _FakeTensor:
        """그래프가 없는 동일한 가상 텐서를 반환한다."""
        return self

    def to(self, _device: str) -> _FakeTensor:
        """장치 전송을 흉내 내고 동일한 가상 텐서를 반환한다."""
        return self

    def numpy(self) -> np.ndarray:
        """가상 텐서가 가진 NumPy 배열을 반환한다."""
        return self.values


class _FakeInferenceMode:
    """PyTorch 추론 전용 문맥 진입 여부를 기록한다."""

    def __init__(self, torch_module: _FakeTorch) -> None:
        """호출 횟수를 기록할 가상 PyTorch 모듈을 저장한다."""
        self.torch_module = torch_module

    def __enter__(self) -> _FakeInferenceMode:
        """추론 문맥 진입 횟수를 늘리고 자신을 반환한다."""
        self.torch_module.inference_mode_entries += 1
        return self

    def __exit__(self, _exc_type: object, _exc: object, _traceback: object) -> None:
        """추론 문맥 종료를 정상 처리한다."""
        return None


class _FakeTorch(types.ModuleType):
    """실제 PyTorch 없이 분리 루프와 CUDA 안전 처리를 실행하는 가상 모듈이다."""

    def __init__(self, cuda_available: bool, cuda_build: str | None = "12.8") -> None:
        """가상 버전·CUDA 런타임과 호출 기록을 초기화한다."""
        super().__init__("torch")
        self.__version__ = "2.test"
        self.version = types.SimpleNamespace(cuda=cuda_build)
        self.cuda = _FakeCuda(cuda_available)
        self.inference_mode_entries = 0
        self.thread_count: int | None = None

    def set_num_threads(self, thread_count: int) -> None:
        """CPU 스레드 설정값을 테스트 기록으로 보존한다."""
        self.thread_count = thread_count

    def from_numpy(self, values: np.ndarray) -> _FakeTensor:
        """NumPy 배열을 가상 텐서로 감싸 반환한다."""
        return _FakeTensor(values)

    def inference_mode(self) -> _FakeInferenceMode:
        """추론 전용 실행 여부를 검증할 문맥 관리자를 반환한다."""
        return _FakeInferenceMode(self)


class _FakeSeparator:
    """모델 다운로드 없이 입력을 guitar stem으로 되돌리는 가상 Demucs 분리기다."""

    last_device: str | None = None

    def __init__(self, *, device: str, **_options: object) -> None:
        """선택된 실행 장치를 기록하고 guitar 출력 모델을 준비한다."""
        type(self).last_device = device
        self.model = types.SimpleNamespace(sources=("guitar",))

    def separate_tensor(self, mixture: _FakeTensor, *, sr: int) -> tuple[_FakeTensor, dict[str, _FakeTensor]]:
        """입력 레벨을 유지한 guitar stem을 반환해 파일 경로 전체를 검증한다."""
        if sr != separator.SEPARATOR_SAMPLE_RATE:
            raise ValueError("unexpected sample rate")
        return mixture, {"guitar": _FakeTensor(mixture.values)}


def _fake_torch(cuda_available: bool, cuda_build: str | None = "12.8") -> types.ModuleType:
    """장치 결정과 런타임 진단에 필요한 최소 PyTorch 모듈을 만든다."""
    return _FakeTorch(cuda_available, cuda_build)


class SeparatorDeviceTests(unittest.TestCase):
    """사용자 연산 장치 설정이 안전하고 결정론적으로 해석되는지 검증한다."""

    def test_cpu_preference_always_resolves_to_cpu(self) -> None:
        """CUDA가 있어도 명시적 CPU 설정은 CPU를 유지해야 한다."""
        self.assertEqual(separator.resolve_compute_device("cpu", _fake_torch(True)), "cpu")

    def test_auto_prefers_cuda_and_falls_back_to_cpu(self) -> None:
        """자동 설정은 CUDA를 우선하고 사용할 수 없으면 CPU로 내려가야 한다."""
        self.assertEqual(separator.resolve_compute_device("auto", _fake_torch(True)), "cuda")
        self.assertEqual(separator.resolve_compute_device("auto", _fake_torch(False)), "cpu")

    def test_explicit_unavailable_cuda_has_clear_error(self) -> None:
        """사용할 수 없는 CUDA를 명시하면 한영 안내가 포함된 분리 오류를 내야 한다."""
        with self.assertRaises(separator.SeparationError) as context:
            separator.resolve_compute_device("cuda", _fake_torch(False, None))
        message = str(context.exception)
        self.assertIn("CUDA가 요청", message)
        self.assertIn("CUDA was requested", message)

    def test_invalid_preference_is_rejected(self) -> None:
        """지원 목록에 없는 장치 이름은 조용히 CPU로 바꾸지 않고 거부해야 한다."""
        with self.assertRaises(separator.SeparationError):
            separator.resolve_compute_device("metal", _fake_torch(False))

    def test_runtime_status_reports_gpu_build_memory_and_resolution(self) -> None:
        """개발자 진단이 CUDA 빌드·GPU·VRAM·연산 능력과 실제 장치를 모두 보여야 한다."""
        fake_torch = _fake_torch(True)
        fake_demucs = types.ModuleType("demucs")
        fake_demucs.__version__ = "4.test"
        with (
            patch.dict(sys.modules, {"torch": fake_torch, "demucs": fake_demucs}),
            patch.object(separator, "separator_model_is_cached", return_value=False),
        ):
            status = separator.separator_runtime_status("auto")

        self.assertTrue(status["available"])
        self.assertEqual(status["requested_device"], "auto")
        self.assertEqual(status["resolved_device"], "cuda")
        self.assertEqual(status["device"], "cuda")
        self.assertTrue(status["cuda_available"])
        self.assertEqual(status["cuda_build"], "12.8")
        self.assertEqual(status["gpu_name"], "Test RTX")
        self.assertEqual(status["gpu_vram_total_bytes"], 12 * 1024**3)
        self.assertEqual(status["gpu_vram_free_bytes"], 7 * 1024**3)
        self.assertEqual(status["compute_capability"], "8.9")

    def test_runtime_status_keeps_explicit_cuda_failure_visible(self) -> None:
        """진단 화면에서는 명시적 CUDA 실패를 숨기지 않고 오류 설명으로 보존해야 한다."""
        fake_torch = _fake_torch(False, None)
        fake_demucs = types.ModuleType("demucs")
        fake_demucs.__version__ = "4.test"
        with (
            patch.dict(sys.modules, {"torch": fake_torch, "demucs": fake_demucs}),
            patch.object(separator, "separator_model_is_cached", return_value=False),
        ):
            status = separator.separator_runtime_status("cuda")

        self.assertEqual(status["requested_device"], "cuda")
        self.assertEqual(status["resolved_device"], "unavailable")
        self.assertIn("CUDA was requested", status["device_resolution_error"])

    def test_cuda_separation_uses_inference_mode_and_reports_timings(self) -> None:
        """CUDA 분리가 추론 문맥·메모리 정리를 사용하고 결과 진단에 실행 시간을 남겨야 한다."""
        fake_torch = _FakeTorch(True)
        fake_demucs = types.ModuleType("demucs")
        fake_demucs.__path__ = []
        fake_demucs.__version__ = "4.test"
        fake_api = types.ModuleType("demucs.api")
        fake_api.Separator = _FakeSeparator

        with tempfile.TemporaryDirectory() as temporary_directory:
            source_path = Path(temporary_directory) / "source.wav"
            destination_path = Path(temporary_directory) / "guitar.wav"
            samples = np.full((4_410, 2), 0.2, dtype=np.float32)
            pcm = np.round(samples * 32_767.0).astype("<i2")
            with wave.open(str(source_path), "wb") as output:
                output.setnchannels(2)
                output.setsampwidth(2)
                output.setframerate(separator.SEPARATOR_SAMPLE_RATE)
                output.writeframes(pcm.tobytes())

            with (
                patch.dict(
                    sys.modules,
                    {"torch": fake_torch, "demucs": fake_demucs, "demucs.api": fake_api},
                ),
                patch.object(separator, "separator_model_is_cached", return_value=True),
            ):
                info = separator.separate_guitar_wav(
                    source_path,
                    destination_path,
                    compute_preference="auto",
                )

        self.assertEqual(_FakeSeparator.last_device, "cuda")
        self.assertEqual(info.requested_device, "auto")
        self.assertEqual(info.resolved_device, "cuda")
        self.assertEqual(info.processed_chunks, 1)
        self.assertEqual(info.peak_gpu_memory_bytes, 3_456)
        self.assertGreaterEqual(info.inference_total_seconds, 0.0)
        self.assertGreaterEqual(info.inference_seconds_per_chunk, 0.0)
        self.assertGreaterEqual(info.realtime_factor, 0.0)
        self.assertEqual(fake_torch.inference_mode_entries, 1)
        self.assertEqual(fake_torch.cuda.reset_calls, 1)
        self.assertGreaterEqual(fake_torch.cuda.synchronize_calls, 2)
        self.assertEqual(fake_torch.cuda.empty_cache_calls, 1)


if __name__ == "__main__":
    unittest.main()
