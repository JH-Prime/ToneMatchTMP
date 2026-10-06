"""6개 분리음을 디스크에 보관하며 다시 추론하지 않는 믹서와 안전한 WAV 저장."""

from contextlib import ExitStack
import math
import os
import queue
from pathlib import Path
import shutil
import tempfile
import threading
import wave

import numpy as np

from separator import SEPARATOR_STEMS, SeparationCancelled, separate_stem_chunks
from playback import WavPlayer
from stem_removal import StemRemovalCancelled
from stem_removal import (_decode_input, _segment_request, _check_cancelled,
                          _normalized_paths, _commit_new_output)


class MixState:
    """UI와 재생 작업자가 일관된 불변 레벨 사본을 교환한다."""

    def __init__(self):
        """기본값은 모든 분리음의 원래 상대 레벨이다."""
        self._lock = threading.Lock()
        self._channels = {name: {"gain": 1.0, "mute": False, "solo": False} for name in SEPARATOR_STEMS}
        self._original = False

    def update(self, changes, *, original=None):
        """유효한 변경을 한 번에 적용하며 실패하면 이전 상태를 보존한다."""
        with self._lock:
            candidate = {name: dict(values) for name, values in self._channels.items()}
            for name, fields in changes.items():
                if name not in candidate or not isinstance(fields, dict) or set(fields) - {"gain", "mute", "solo"}:
                    raise ValueError("Invalid mixer channel")
                candidate[name].update(fields)
                gain = candidate[name]["gain"]
                if type(gain) not in (int, float) or not math.isfinite(gain) or not 0 <= gain <= 2:
                    raise ValueError("Gain must be between 0 and 2")
                if any(type(candidate[name][key]) is not bool for key in ("mute", "solo")):
                    raise ValueError("Mute/solo must be boolean")
            if original is not None and type(original) is not bool:
                raise ValueError("Original selection must be boolean")
            self._channels = candidate
            if original is not None:
                self._original = original

    def snapshot(self):
        """한 블록에 적용할 레벨과 원본 비교 선택을 일관되게 반환한다."""
        with self._lock:
            solo = any(item["solo"] for item in self._channels.values())
            gains = tuple(0.0 if item["mute"] or (solo and not item["solo"]) else item["gain"]
                          for item in self._channels.values())
            return gains, self._original

    def controls(self):
        """창을 다시 열 때 음소거·솔로 이전의 fader 값도 복원한다."""
        with self._lock:
            return {name: dict(values) for name, values in self._channels.items()}, self._original


class StemBank:
    """정렬된 float32 분리음과 공통 헤드룸을 소유하며 원본은 변경하지 않는다."""

    def __init__(self, source):
        """전용 임시 폴더만 소유하고 사용자 경로를 쓰기 대상으로 쓰지 않는다."""
        self.source = Path(source).resolve(strict=True)
        if not self.source.is_file():
            raise ValueError("Mixer source is not a file")
        self._temporary = tempfile.TemporaryDirectory(prefix="tonematch-mixer-")
        self.directory = Path(self._temporary.name)
        self.original_path = self.directory / "original.wav"
        self.paths = {name: self.directory / (name + ".f32") for name in SEPARATOR_STEMS}
        self.frames = 0
        self.sample_rate = 44100
        self.headroom = 1.0

    @classmethod
    def prepare(cls, source, start=0, end=0, *, compute="auto", language="ko",
                progress=None, cancel_requested=None):
        """한 번만 분리하고 조각별로 저장해 긴 곡의 메모리 사용을 제한한다."""
        start, duration = _segment_request(start, end)
        bank = cls(source)
        try:
            _decode_input(bank.source, bank.original_path, start, duration, progress, cancel_requested, language)
            with wave.open(str(bank.original_path)) as original:
                expected_frames = original.getnframes()
            if shutil.disk_usage(bank.directory).free < expected_frames * 2 * 4 * 6 + 64 * 1024 * 1024:
                raise ValueError("분리음을 저장할 임시 디스크 공간이 부족합니다. / Not enough temporary disk space.")
            bound = 0.0
            with ExitStack() as resources:
                files = {name: resources.enter_context(path.open("wb")) for name, path in bank.paths.items()}

                def consume(stems):
                    """여섯 조각의 정렬과 유한 값을 검사한 뒤 같은 길이로 기록한다."""
                    nonlocal bound
                    _check_cancelled(cancel_requested, language)
                    if set(stems) != set(SEPARATOR_STEMS):
                        raise ValueError("Missing mixer stems")
                    arrays = [np.asarray(stems[name]) for name in SEPARATOR_STEMS]
                    if len({array.shape for array in arrays}) != 1 or arrays[0].ndim != 2 or arrays[0].shape[0] != 2:
                        raise ValueError("Unaligned mixer stems")
                    if not arrays[0].shape[1] or any(not np.all(np.isfinite(array)) for array in arrays):
                        raise ValueError("Invalid mixer PCM")
                    peak = np.zeros_like(arrays[0], dtype=np.float64)
                    for name, array in zip(SEPARATOR_STEMS, arrays):
                        peak += np.abs(array)
                        if np.max(np.abs(array)) > np.finfo(np.float32).max:
                            raise ValueError("Mixer PCM outside float32 range")
                        files[name].write(np.asarray(array.T, dtype="<f4").tobytes())
                    bound = max(bound, float(np.max(peak)))
                    bank.frames += arrays[0].shape[1]

                bank.separation_info = separate_stem_chunks(
                    bank.original_path, SEPARATOR_STEMS, consume, progress, cancel_requested, language, compute)
            _check_cancelled(cancel_requested, language)
            if bank.frames != expected_frames:
                raise ValueError("Stem duration differs from original")
            # 모든 fader가 2배여도 클리핑하지 않는 공통 계수. 개별 정규화하지 않는다.
            bank.headroom = min(1.0, .98 / max(1e-12, 2 * bound))
            return bank
        except SeparationCancelled as exc:
            bank.close()
            raise StemRemovalCancelled(str(exc)) from exc
        except BaseException:
            bank.close()
            raise

    def close(self):
        """재생·저장이 끝난 뒤 직접 만든 임시 파일만 회수한다."""
        self._temporary.cleanup()

    def export(self, destination, state, *, stem=None, cancel_requested=None, language="ko"):
        """레벨 사본을 새 WAV에 기록하고 취소·이름 충돌 시 기존 파일을 보호한다."""
        _check_cancelled(cancel_requested, language)
        _, target = _normalized_paths(self.source, destination, language)
        gains, original = state.snapshot()
        if stem is not None:
            if stem not in SEPARATOR_STEMS:
                raise ValueError("Unknown stem")
            gains, original = tuple(float(name == stem) for name in SEPARATOR_STEMS), False
        frozen = MixState()
        frozen.update({name: {"gain": gain} for name, gain in zip(SEPARATOR_STEMS, gains)}, original=original)
        descriptor, partial_name = tempfile.mkstemp(prefix=".mix-", suffix=".partial.wav", dir=target.parent)
        os.close(descriptor)
        partial = Path(partial_name)
        try:
            with MixReader(self, frozen) as reader, wave.open(str(partial), "wb") as output:
                output.setparams((2, 2, self.sample_rate, 0, "NONE", "not compressed"))
                while reader.position < self.frames:
                    _check_cancelled(cancel_requested, language)
                    output.writeframes(reader.readframes(65536))
            _check_cancelled(cancel_requested, language)
            _commit_new_output(partial, target, language)
        finally:
            partial.unlink(missing_ok=True)
        return target


class MixReader:
    """WAV reader 계약으로 원본 또는 실시간 fader 합산 PCM을 제공한다."""

    def __init__(self, bank, state):
        """파일 핸들을 한 재생 작업자에 한정하고 배열은 블록만 할당한다."""
        self.bank, self.state, self.position = bank, state, 0
        self._resources = ExitStack()
        try:
            self.original = self._resources.enter_context(wave.open(str(bank.original_path)))
            self.stems = [self._resources.enter_context(bank.paths[name].open("rb")) for name in SEPARATOR_STEMS]
        except BaseException:
            self._resources.close()
            raise

    def __enter__(self):
        """읽기 범위 동안 핸들을 소유한다."""
        return self

    def __exit__(self, *args):
        """모든 파일 핸들을 닫은 뒤 임시 폴더 정리를 허용한다."""
        self._resources.close()

    def getnframes(self):
        """원본과 정렬된 전체 길이를 반환한다."""
        return self.bank.frames

    def getframerate(self):
        """분리 모델과 같은 샘플레이트를 반환한다."""
        return self.bank.sample_rate

    def getnchannels(self):
        """출력은 스테레오이다."""
        return 2

    def getsampwidth(self):
        """공통 헤드룸이 적용된 PCM16을 출력한다."""
        return 2

    def setpos(self, frame):
        """읽기 위치만 검증해 바꾸며 fader 상태는 유지한다."""
        if type(frame) is not int or not 0 <= frame <= self.bank.frames:
            raise ValueError("Mixer position outside audio")
        self.position = frame

    def readframes(self, count):
        """동일 시점의 분리음을 더하고 모든 채널에 같은 헤드룸을 적용한다."""
        if type(count) is not int or count < 0:
            raise ValueError("Invalid mixer block size")
        count = min(count, self.bank.frames - self.position)
        gains, original = self.state.snapshot()
        if original:
            self.original.setpos(self.position)
            raw = self.original.readframes(count)
            if len(raw) != count * 4:
                raise ValueError("Truncated original PCM")
        else:
            mixed = np.zeros((count, 2), np.float64)
            for stream, gain in zip(self.stems, gains):
                if not gain:
                    continue
                stream.seek(self.position * 8)
                data = stream.read(count * 8)
                if len(data) != count * 8:
                    raise ValueError("Truncated stem PCM")
                mixed += np.frombuffer(data, "<f4").reshape(-1, 2) * gain
            if not np.all(np.isfinite(mixed)):
                raise ValueError("Invalid mixed samples")
            raw = np.rint(np.clip(mixed * self.bank.headroom, -1, 1) * 32767).astype("<i2").tobytes()
        self.position += count
        return raw


class MixerSession:
    """메인 스레드에서 분리·내보내기 결과와 재생 자원 수명을 직렬화한다."""

    def __init__(self):
        """파일과 출력 장치를 열지 않는 빈 세션을 만든다."""
        self.bank = self.player = None
        self.state = MixState()
        self.error = self.message = ""
        self.saved_path = None
        self.progress = 0.0
        self.operation = ""
        self._generation = 0
        self._cancel = threading.Event()
        self._events = queue.Queue()
        self._workers = []
        self._retired = []

    @property
    def busy(self):
        """완료 큐 처리 전이나 취소 후 정리 중에도 중복 작업을 막는다."""
        return bool(self.operation or self._workers or self._retired)

    def _start(self, operation, action):
        """작업자는 Tk에 접근하지 않고 세대가 붙은 이벤트만 전달한다."""
        self.operation = operation
        self.error = self.message = ""
        self.saved_path = None
        self.progress = 0.0
        self._cancel = threading.Event()
        generation, cancel = self._generation, self._cancel

        def report(percent, message):
            self._events.put((generation, "progress", (percent, message)))

        def run():
            try:
                value = action(cancel.is_set, report)
                self._events.put((generation, operation, value))
            except StemRemovalCancelled:
                self._events.put((generation, "cancelled", None))
            except Exception as exc:
                self._events.put((generation, "error", str(exc)))

        worker = threading.Thread(target=run, name="ToneMatchMixer", daemon=True)
        self._workers.append(worker)
        worker.start()

    def prepare(self, source, start=0, end=0, *, compute="auto", language="ko"):
        """이전 자원을 회수하고 새 로컬 구간을 한 번만 분리한다."""
        self.poll()
        if self.busy:
            raise RuntimeError("Mixer is busy")
        self.clear()
        self.state = MixState()
        self._start("prepare", lambda cancel, progress: StemBank.prepare(
            source, start, end, compute=compute, language=language,
            progress=progress, cancel_requested=cancel))

    def export(self, destination, *, stem=None, language="ko"):
        """저장 시점 레벨을 고정하고 내보내기를 백그라운드에서 실행한다."""
        self.poll()
        if self.busy or self.bank is None:
            raise RuntimeError("Mixer is not ready")
        controls, original = self.state.controls()
        frozen = MixState()
        # 원본 비교는 모니터 전용이며 '믹스 저장'은 항상 fader 믹스를 저장한다.
        frozen.update(controls, original=False)
        bank = self.bank
        self._start("export", lambda cancel, progress: bank.export(
            destination, frozen, stem=stem, language=language, cancel_requested=cancel))

    def toggle(self):
        """명시적인 재생 클릭 때만 장치를 열고 같은 분리음 파일을 사용한다."""
        if self.busy or self.bank is None:
            return
        if self.player is None:
            bank, state = self.bank, self.state
            self.player = WavPlayer(bank.original_path, source_factory=lambda: MixReader(bank, state))
        if self.player.snapshot()["state"] in ("playing", "draining"):
            self.player.pause()
        else:
            self.player.play()

    def stop(self):
        """준비된 분리음을 유지하며 오디오 출력만 멈춘다."""
        if self.player:
            self.player.stop()

    def cancel(self):
        """현재 파일 작업만 취소하며 이미 준비된 분리음을 보존한다."""
        self._cancel.set()

    def clear(self):
        """새 세대로 바꾸고 작업자 종료 후에만 임시 파일을 정리한다."""
        self._cancel.set()
        self._generation += 1
        self.operation = ""
        if self.player:
            self.player.close()
        if self.bank or self.player:
            self._retired.append((self.player, self.bank))
        self.player = self.bank = None
        self.error = self.message = ""
        self.saved_path = None
        self.poll()

    def poll(self):
        """오래된 완료는 버리고 파일과 출력 작업자 종료를 확인해 회수한다."""
        while True:
            try:
                generation, kind, value = self._events.get_nowait()
            except queue.Empty:
                break
            if generation != self._generation or (self._cancel.is_set() and kind == "prepare"):
                if kind == "prepare":
                    self._retired.append((None, value))
                if generation == self._generation:
                    self.operation = ""
                continue
            if kind == "progress":
                percent, self.message = value
                self.progress = max(self.progress, min(100.0, max(0.0, float(percent))))
                continue
            self.operation = ""
            if kind == "prepare":
                self.bank = value
                self.progress = 100.0
            elif kind == "export":
                self.saved_path = value
                self.progress = 100.0
            elif kind == "error":
                self.error = value
        self._workers = [worker for worker in self._workers if worker.is_alive()]
        pending = []
        for player, bank in self._retired:
            if not self._workers and (not player or player.wait_closed()):
                if bank:
                    bank.close()
            else:
                pending.append((player, bank))
        self._retired = pending

    def suspend(self):
        """캡처·AI 시작 전에 출력 해제와 파일 작업 종료 여부를 확인한다."""
        self.stop()
        self.poll()
        return not self.busy and not (self.player and self.player.snapshot()["output_active"])

    def is_closed(self):
        """종료 시 마지막 작업자와 임시 파일이 모두 회수되었는지 확인한다."""
        self.poll()
        return not self.bank and not self.player and not self.busy
