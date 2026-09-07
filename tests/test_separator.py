"""Demucs 기타 분리기의 CPU·CUDA 장치 선택과 런타임 진단 회귀 테스트."""

from __future__ import annotations

import sys
import tempfile
import types
import unittest
import wave
from pathlib import Path
from typing import Any
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

    def __init__(self, *, device: str, callback: object = None, **_options: object) -> None:
        """선택된 실행 장치를 기록하고 guitar 출력 모델을 준비한다."""
        _FakeSeparator.last_device = device
        self.callback = callback
        self.model = types.SimpleNamespace(sources=("guitar",), segment=0.04,
                                           samplerate=separator.SEPARATOR_SAMPLE_RATE)

    def separate_tensor(self, mixture: _FakeTensor, *, sr: int) -> tuple[_FakeTensor, dict[str, _FakeTensor]]:
        """입력 레벨을 유지한 guitar stem을 반환해 파일 경로 전체를 검증한다."""
        if sr != separator.SEPARATOR_SAMPLE_RATE:
            raise ValueError("unexpected sample rate")
        if self.callback:
            stride = int((1 - separator.SEPARATION_OVERLAP) * int(sr * self.model.segment))
            for offset in range(0, mixture.values.shape[-1], stride):
                for state in ("start", "end"):
                    self.callback({"state": state, "model_idx_in_bag": 0, "segment_offset": offset,
                                   "models": 1, "audio_length": mixture.values.shape[-1]})
        return mixture, {"guitar": _FakeTensor(mixture.values)}


def _write_test_wav(path: Path, frames: int = 4_410) -> None:
    """분리 진행률·취소 검증용으로 짧은 비무음 스테레오 PCM 파일을 만든다."""
    samples = np.full((frames, 2), 0.2, dtype=np.float32)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(separator.SEPARATOR_SAMPLE_RATE)
        output.writeframes(np.round(samples * 32_767.0).astype("<i2").tobytes())


def _fake_separation_modules(separator_class: type = _FakeSeparator) -> dict[str, object]:
    """분리기 생성과 콜백 테스트에 쓸 가상 Demucs·PyTorch 모듈을 묶는다."""
    demucs = types.ModuleType("demucs")
    demucs.__path__ = []
    api = types.ModuleType("demucs.api")
    api.Separator = separator_class
    return {"torch": _FakeTorch(False), "demucs": demucs, "demucs.api": api}


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


class SeparatorProgressTests(unittest.TestCase):
    """실제 다운로드·추론 이벤트만 반영하고 실패·취소의 원인을 보존하는지 검증한다."""

    def test_windowless_download_progress_tracks_bytes_without_standard_streams(self) -> None:
        """stdout·stderr가 None인 GUI 환경에서도 실제 다운로드량이 표시되어야 한다."""
        events = []
        progress_class = separator._download_progress_class(
            lambda value, message: events.append((value, message)), None, "en", "weights", 18, 23)
        with patch.object(sys, "stdout", None), patch.object(sys, "stderr", None):
            with progress_class(total=100, initial=20) as bar:
                bar.update(80)
        self.assertEqual(events[0][0], 19)
        self.assertEqual(events[-1][0], 23)
        self.assertIn("100.0", events[-1][1])

    def test_unknown_download_total_does_not_invent_percentage(self) -> None:
        """총 파일 크기를 모를 때는 수신 바이트만 표시하고 단계값을 올리지 않아야 한다."""
        events = []
        progress_class = separator._download_progress_class(
            lambda value, message: events.append((value, message)), None, "en", "weights", 18, 23)
        with progress_class(total=None) as bar:
            bar.update(1_048_576)
        self.assertEqual({value for value, _message in events}, {18})

    def test_download_cancellation_uses_supported_interrupt(self) -> None:
        """다운로드 콜백 취소는 Hugging Face가 정리하는 KeyboardInterrupt로 전달되어야 한다."""
        progress_class = separator._download_progress_class(None, lambda: True, "en", "weights", 18, 23)
        with progress_class(total=100) as bar:
            with self.assertRaises(KeyboardInterrupt):
                bar.update(1)

    def test_segment_events_update_inside_first_chunk(self) -> None:
        """30초 조각 하나가 끝나기 전에도 내부 분할 완료마다 진행률이 증가해야 한다."""
        events = []
        with tempfile.TemporaryDirectory() as directory:
            source, destination = Path(directory) / "source.wav", Path(directory) / "guitar.wav"
            _write_test_wav(source)
            with (patch.dict(sys.modules, _fake_separation_modules()),
                  patch.object(separator, "separator_model_is_cached", return_value=True)):
                separator.separate_guitar_wav(source, destination,
                    progress=lambda value, message: events.append((value, message)))
        percentages = [value for value, _message in events]
        self.assertEqual(percentages, sorted(percentages))
        self.assertTrue(any(24 < value < 66 for value in percentages))
        self.assertEqual(percentages[-1], 68)

    def test_cancel_between_internal_segments_removes_partial_file(self) -> None:
        """내부 블록 완료 후 취소하면 다음 블록 전에 멈추고 미완성 stem을 제거해야 한다."""
        events = []
        with tempfile.TemporaryDirectory() as directory:
            source, destination = Path(directory) / "source.wav", Path(directory) / "guitar.wav"
            _write_test_wav(source)
            with (patch.dict(sys.modules, _fake_separation_modules()),
                  patch.object(separator, "separator_model_is_cached", return_value=True)):
                with self.assertRaises(separator.SeparationCancelled):
                    separator.separate_guitar_wav(source, destination,
                        progress=lambda value, message: events.append(value),
                        cancel_requested=lambda: any(24 < value < 66 for value in events))
            self.assertFalse(destination.exists())

    def test_cancel_before_model_import_leaves_output_absent(self) -> None:
        """시작 전 취소 요청은 모델 다운로드나 출력 파일 생성 전에 처리되어야 한다."""
        with tempfile.TemporaryDirectory() as directory:
            source, destination = Path(directory) / "source.wav", Path(directory) / "guitar.wav"
            _write_test_wav(source)
            with patch.object(separator, "_load_hf_separator_model") as loader:
                with self.assertRaises(separator.SeparationCancelled):
                    separator.separate_guitar_wav(source, destination, cancel_requested=lambda: True)
            loader.assert_not_called()
            self.assertFalse(destination.exists())

    def test_model_failure_preserves_type_and_does_not_claim_network_failure(self) -> None:
        """일반 모델 초기화 오류의 원인을 그대로 남기고 인터넷 연결 문제로 단정하지 않아야 한다."""
        class FailingSeparator:
            """실제 Demucs 생성자처럼 모델 로딩 override를 실행하는 가상 분리기다."""

            def __init__(self, **options: object) -> None:
                """상속된 로딩 지점을 호출해 오류 변환 경로를 검증한다."""
                self._load_model()

        original_error = AttributeError("'NoneType' object has no attribute 'write'")
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.wav"
            _write_test_wav(source)
            with (patch.dict(sys.modules, _fake_separation_modules(FailingSeparator)),
                  patch.object(separator, "separator_model_is_cached", return_value=False),
                  patch.object(separator, "_load_hf_separator_model", side_effect=original_error)):
                with self.assertRaises(separator.SeparationError) as caught:
                    separator.separate_guitar_wav(source, Path(directory) / "guitar.wav", language="en")
        self.assertIs(caught.exception.__cause__, original_error)
        self.assertIn("AttributeError", str(caught.exception))
        self.assertNotIn("first run needs internet", str(caught.exception))

    def test_model_error_classification_uses_exception_chain(self) -> None:
        """상위 래퍼가 있어도 네트워크·캐시·메모리의 구체적인 예외 원인을 찾아야 한다."""
        for original, expected in ((TimeoutError("timed out"), "error.separator_network"),
                                   (PermissionError("denied"), "error.separator_cache"),
                                   (MemoryError("full"), "error.separator_memory"),
                                   (ValueError("bad manifest"), "error.separator_model")):
            wrapper = RuntimeError("wrapped")
            wrapper.__cause__ = original
            self.assertEqual(separator._model_error_key(wrapper), expected)

    def test_multimodel_progress_ignores_duplicates_and_waits_for_every_model(self) -> None:
        """여러 모델의 겹침 블록은 중복 집계하지 않고 모든 모델 완료 후에만 끝나야 한다."""
        events = []
        tracker = separator._SeparationProgress(lambda value, message: events.append(value), None, "en")
        submodel = types.SimpleNamespace(segment=1.0, samplerate=100)
        model = types.SimpleNamespace(models=[submodel, submodel])
        tracker.begin_chunk(model, 0, 1, 100, 0, 100)
        for model_index in range(2):
            for offset in (0, 85):
                event = {"state": "end", "model_idx_in_bag": model_index, "segment_offset": offset}
                tracker(event)
                before_duplicate = events[-1]
                tracker(event)
                self.assertEqual(events[-1], before_duplicate)
            if model_index == 0:
                self.assertLess(events[-1], 66)
        self.assertEqual(events[-1], 66)

    def test_hf_loader_uses_complete_cache_without_network_download(self) -> None:
        """캐시가 완전하면 YAML·가중치를 네트워크 호출 없이 읽고 로딩 단계를 알려야 한다."""
        import huggingface_hub
        events = []
        fake_apply = types.ModuleType("demucs.apply")
        fake_hf = types.ModuleType("demucs.hf")
        model = types.SimpleNamespace(eval=lambda: None)
        fake_apply.BagOfModels = lambda models, weights, segment: model
        fake_hf.load_safetensors_model = lambda path: object()
        with tempfile.TemporaryDirectory() as directory:
            yaml_path = Path(directory) / "htdemucs_6s.yaml"
            yaml_path.write_text("models: ['model123']\n", encoding="utf-8")
            weights_path = Path(directory) / "model123.safetensors"
            weights_path.write_bytes(b"mock-model")

            def cached_download(**options: object) -> str:
                """캐시 전용 옵션이 없으면 실패해 숨겨진 네트워크 접근을 검출한다."""
                self.assertTrue(options.get("local_files_only"))
                return str(Path(directory) / str(options["filename"]))

            with (patch.dict(sys.modules, {"demucs.apply": fake_apply, "demucs.hf": fake_hf}),
                  patch.object(huggingface_hub, "hf_hub_download", side_effect=cached_download) as download):
                loaded = separator._load_hf_separator_model(
                    lambda value, message: events.append(value), None, "en")
        self.assertIs(loaded, model)
        self.assertEqual(download.call_count, 2)
        self.assertEqual(events, [23])

    def test_hf_loader_downloads_missing_file_with_progress_class(self) -> None:
        """가중치 캐시가 없을 때만 다운로드를 수행하고 공식 tqdm 확장 인자를 넘겨야 한다."""
        import huggingface_hub
        from huggingface_hub.errors import LocalEntryNotFoundError
        events = []
        fake_apply = types.ModuleType("demucs.apply")
        fake_hf = types.ModuleType("demucs.hf")
        model = types.SimpleNamespace(eval=lambda: None)
        fake_apply.BagOfModels = lambda models, weights, segment: model
        fake_hf.load_safetensors_model = lambda path: object()
        with tempfile.TemporaryDirectory() as directory:
            yaml_path = Path(directory) / "htdemucs_6s.yaml"
            yaml_path.write_text("models: ['model123']\n", encoding="utf-8")
            weights_path = Path(directory) / "model123.safetensors"
            weights_path.write_bytes(b"mock-model")

            def missing_weights_download(**options: Any) -> str:
                """YAML은 캐시에서 반환하고 누락된 가중치의 실제 진행 이벤트만 흉내 낸다."""
                if str(options["filename"]).endswith(".yaml"):
                    return str(yaml_path)
                if options.get("local_files_only"):
                    raise LocalEntryNotFoundError("not cached")
                with options["tqdm_class"](total=100) as bar:
                    bar.update(100)
                return str(weights_path)

            with (patch.dict(sys.modules, {"demucs.apply": fake_apply, "demucs.hf": fake_hf}),
                  patch.object(huggingface_hub, "hf_hub_download", side_effect=missing_weights_download) as download):
                separator._load_hf_separator_model(lambda value, message: events.append(value), None, "en")
        self.assertEqual(download.call_count, 3)
        self.assertEqual(events, [18, 23, 23])

    def test_hf_loader_preserves_network_failure_without_legacy_fallback(self) -> None:
        """HF 연결 실패가 legacy 다운로드의 stdout 예외로 덮이지 않고 그대로 전달되어야 한다."""
        import huggingface_hub
        from huggingface_hub.errors import LocalEntryNotFoundError
        fake_apply = types.ModuleType("demucs.apply")
        fake_hf = types.ModuleType("demucs.hf")
        fake_apply.BagOfModels = object
        fake_hf.load_safetensors_model = object
        original = TimeoutError("HF request timed out")
        with (patch.dict(sys.modules, {"demucs.apply": fake_apply, "demucs.hf": fake_hf}),
              patch.object(huggingface_hub, "hf_hub_download",
                           side_effect=[LocalEntryNotFoundError("not cached"), original]) as download):
            with self.assertRaises(TimeoutError) as caught:
                separator._load_hf_separator_model(None, None, "en")
        self.assertIs(caught.exception, original)
        self.assertEqual(download.call_count, 2)

    def test_installed_demucs_api_accepts_progress_model_loader_override(self) -> None:
        """설치된 실제 Demucs API에서 로더 주입·샘플레이트·콜백 인자가 호환되어야 한다."""
        try:
            from demucs.api import Separator as DemucsSeparator
        except ImportError:
            self.skipTest("Optional Demucs runtime is not installed")
        model = types.SimpleNamespace(sources=("guitar",), audio_channels=2,
                                      samplerate=separator.SEPARATOR_SAMPLE_RATE, segment=0.04)

        def mocked_inference(instance: Any, mixture: Any, sr: int) -> tuple[Any, dict[str, Any]]:
            """실제 API의 초기화 결과를 검증하고 모델 연산 없이 입력을 되돌린다."""
            self.assertIs(instance.model, model)
            self.assertEqual(instance.samplerate, sr)
            self.assertIsInstance(instance._callback, separator._SeparationProgress)
            self.assertFalse(instance._progress)
            return mixture, {"guitar": mixture}

        with tempfile.TemporaryDirectory() as directory:
            source, destination = Path(directory) / "source.wav", Path(directory) / "guitar.wav"
            _write_test_wav(source)
            with (patch.object(separator, "_load_hf_separator_model", return_value=model),
                  patch.object(separator, "separator_model_is_cached", return_value=True),
                  patch.object(DemucsSeparator, "separate_tensor", autospec=True, side_effect=mocked_inference)):
                info = separator.separate_guitar_wav(source, destination, compute_preference="cpu")
            self.assertTrue(destination.exists())
        self.assertEqual(info.processed_chunks, 1)


if __name__ == "__main__":
    unittest.main()
