"""샘플 위치 기반 재생 상태와 로컬 PCM 재생 도구."""

from __future__ import annotations

import math
import queue
from pathlib import Path
import tempfile
import threading
import wave

import numpy as np


class Transport:
    """장치와 독립된 반열린 샘플 범위로 탐색·반복·종료를 처리한다."""

    def __init__(self, frames: int, sample_rate: int):
        """유효한 PCM 길이를 받고 명시적인 재생 요청을 기다린다."""
        if not isinstance(frames, int) or not isinstance(sample_rate, int) or frames <= 0 or sample_rate <= 0:
            raise ValueError("Invalid PCM duration")
        self.frames = frames
        self.sample_rate = sample_rate
        self.position = 0
        self.state = "ready"
        self.loop: tuple[int, int] | None = None

    @property
    def seconds(self) -> float:
        """분석 구간 시작 기준 재생 초를 반환한다."""
        return self.position / self.sample_rate

    def _frame(self, seconds: float) -> int:
        """유한하고 음원 안에 있는 시각만 샘플 위치로 변환한다."""
        seconds = float(seconds)
        if not math.isfinite(seconds) or not 0 <= seconds <= self.frames / self.sample_rate:
            raise ValueError("Position is outside audio")
        return min(self.frames, round(seconds * self.sample_rate))

    def seek(self, seconds: float) -> None:
        """재생 여부는 유지하고 검증된 위치로 옮긴다."""
        self.position = self._frame(seconds)
        if self.position == self.frames and not self.loop:
            self.state = 'finished'
        elif self.state == "finished":
            self.state = "paused"

    def set_loop(self, start: float | None = None, end: float | None = None) -> None:
        """유효한 반복 구간을 적용하거나 인수 없이 반복을 해제한다."""
        if start is None and end is None:
            self.loop = None
            return
        first, last = self._frame(start), self._frame(end)
        if first >= last:
            raise ValueError("Loop must contain audio")
        self.loop = first, last

    def play(self) -> None:
        """재생을 명시적으로 시작하고 반복 범위 밖이나 EOF 위치를 보정한다."""
        if self.loop and not self.loop[0] <= self.position < self.loop[1]:
            self.position = self.loop[0]
        elif self.position >= self.frames:
            self.position = 0
        self.state = "playing"

    def pause(self) -> None:
        """현재 위치를 보존하며 재생을 멈춘다."""
        if self.state == "playing":
            self.state = "paused"

    def stop(self) -> None:
        """재생을 종료하고 처음 위치에서 다음 요청을 기다린다."""
        self.position = 0
        self.state = "ready"

    def next_span(self, block_frames: int) -> tuple[int, int] | None:
        """반복 또는 파일 끝을 넘지 않는 다음 읽기 범위를 반환한다."""
        if not isinstance(block_frames, int) or block_frames <= 0:
            raise ValueError("Invalid block size")
        if self.state != "playing":
            return None
        if self.loop and not self.loop[0] <= self.position < self.loop[1]:
            self.position = self.loop[0]
        limit = self.loop[1] if self.loop else self.frames
        return self.position, min(limit, self.position + block_frames)

    def advance(self, frames: int) -> None:
        """실제로 전달한 프레임만 전진하고 반복 또는 자연 종료를 적용한다."""
        if not isinstance(frames, int) or frames < 0:
            raise ValueError("Invalid advance")
        if self.state != "playing":
            return
        self.position += frames
        if self.loop and self.position >= self.loop[1]:
            self.position = self.loop[0]
        elif self.position >= self.frames:
            self.position = self.frames
            self.state = "finished"


def read_pcm_block(source: wave.Wave_read, start: int, end: int) -> np.ndarray:
    """WAV의 지정 범위를 정확히 읽고 잘린 PCM을 거부한다."""
    if source.getsampwidth() != 2 or source.getnchannels() not in (1, 2):
        raise ValueError("Playback requires mono/stereo PCM16")
    if not 0 <= start < end <= source.getnframes():
        raise ValueError("PCM range outside file")
    source.setpos(start)
    raw = source.readframes(end - start)
    if len(raw) != (end - start) * source.getnchannels() * 2:
        raise ValueError("Truncated playback PCM")
    return np.frombuffer(raw, dtype="<i2").reshape(-1, source.getnchannels()).astype(np.float32) / 32768


class PreparedAudio:
    """원본을 변경하지 않는 선택 구간 PCM과 임시 디렉터리를 소유한다."""

    def __init__(self):
        """독립 임시 디렉터리에만 쓰기 권한을 한정한다."""
        self._temporary = tempfile.TemporaryDirectory(prefix='tonematch-playback-')
        self.path = Path(self._temporary.name) / 'playback.wav'

    @classmethod
    def decode(cls, source, start=0, end=0, *, cancel_requested=None, progress=None, language='ko'):
        """기존 제한·취소·FFmpeg 경계를 재사용해 PCM을 준비한다."""
        from stem_removal import _decode_input, _segment_request

        path = Path(source).resolve(strict=True)
        if not path.is_file():
            raise ValueError('Playback source is not a file')
        start, duration = _segment_request(start, end)
        prepared = cls()
        try:
            _decode_input(path, prepared.path, start, duration, progress, cancel_requested, language)
            return prepared
        except BaseException:
            prepared.close()
            raise

    def close(self):
        """직접 만든 임시 디렉터리만 회수한다."""
        self._temporary.cleanup()


def default_output(**kwargs):
    """명시적 재생 시에만 기본 Windows 출력 장치를 연다."""
    import sounddevice

    return sounddevice.OutputStream(dtype='float32', latency=0.1, **kwargs)


class WavPlayer:
    """단일 작업자가 PCM과 출력 장치를 소유하는 비차단 재생 서비스."""

    def __init__(self, path, *, output_factory=None, source_factory=None, block_frames=2048):
        """파일 형식만 검사하고 사용자 요청 전에는 장치를 열지 않는다."""
        if type(block_frames) is not int or block_frames <= 0:
            raise ValueError('Invalid block size')
        self.path = Path(path)
        self._source_factory = source_factory or (lambda: wave.open(str(self.path), 'rb'))
        with self._source_factory() as source:
            if source.getsampwidth() != 2 or source.getnchannels() not in (1, 2):
                raise ValueError('Playback requires mono/stereo PCM16')
            self.transport = Transport(source.getnframes(), source.getframerate())
            self.channels = source.getnchannels()
        self._output_factory = output_factory or default_output
        self._block_frames = block_frames
        self._condition = threading.Condition()
        self._revision = 0
        self._closed = False
        self._output_active = False
        self._error = ''
        self._thread = threading.Thread(target=self._run, name='ToneMatchPlayback', daemon=True)
        self._thread.start()

    def snapshot(self):
        """UI가 잠금 밖에서 사용할 수 있는 현재 상태 복사본을 반환한다."""
        with self._condition:
            state = self.transport.state
            if state == 'finished' and self._output_active:
                state = 'draining'
            return {'state': 'closed' if self._closed else state,
                    'position': self.transport.seconds,
                    'duration': self.transport.frames / self.transport.sample_rate,
                    'loop': self.transport.loop,
                    'error': self._error, 'output_active': self._output_active}

    def _command(self, name, *args):
        """검증된 명령만 반영하고 이전 블록 완료의 위치 갱신을 무효화한다."""
        with self._condition:
            if self._closed:
                raise RuntimeError('Playback is closed')
            getattr(self.transport, name)(*args)
            if name == 'pause' and self.transport.state == 'finished' and self._output_active:
                self.transport.state = 'paused'
            self._error = ''
            self._revision += 1
            self._condition.notify_all()

    def play(self):
        """명시적인 재생 요청을 작업자에게 전달한다."""
        self._command('play')

    def pause(self):
        """UI를 대기시키지 않고 재생 중단을 요청한다."""
        self._command('pause')

    def stop(self):
        """첫 위치로 돌아가고 현재 출력 블록 이후 대기 오디오를 폐기한다."""
        self._command('stop')

    def seek(self, seconds):
        """검증된 새 위치로 이동하며 이전 위치의 쓰기 완료를 무시한다."""
        self._command('seek', seconds)

    def set_loop(self, start=None, end=None):
        """반복 구간 변경을 출력 작업자와 직렬화한다."""
        self._command('set_loop', start, end)

    def close(self):
        """작업자 종료만 요청하므로 Tk 이벤트 처리를 막지 않는다."""
        with self._condition:
            self._closed = True
            self._revision += 1
            self._condition.notify_all()

    def wait_closed(self, timeout=0):
        """자원 소유자가 PCM을 삭제하기 전에 작업자 종료를 확인한다."""
        self._thread.join(timeout)
        return not self._thread.is_alive()

    def _run(self):
        """유일한 장치 소유자로 블록 쓰기·중단·자연 종료를 처리한다."""
        while True:
            with self._condition:
                self._condition.wait_for(lambda: self._closed or self.transport.state == 'playing')
                if self._closed:
                    return
                revision = self._revision
                self._output_active = True
            output = None
            finished = False
            failure = ''
            try:
                output = self._output_factory(samplerate=self.transport.sample_rate,
                                              channels=self.channels, blocksize=self._block_frames)
                output.start()
                with self._source_factory() as source:
                    while True:
                        with self._condition:
                            if self._closed or revision != self._revision:
                                break
                            span = self.transport.next_span(self._block_frames)
                        if span is None:
                            break
                        block = read_pcm_block(source, *span)
                        output.write(block)
                        with self._condition:
                            if self._closed or revision != self._revision:
                                break
                            self.transport.advance(len(block))
                            if self.transport.state == 'finished':
                                # UI에는 마지막 버퍼의 drain과 close 이후에 완료를 공개한다.
                                finished = True
                                break
                if finished:
                    output.stop()
                else:
                    output.abort()
            except Exception as exc:
                failure = str(exc)
            finally:
                if output is not None:
                    try:
                        output.close()
                    except Exception as exc:
                        failure = failure or str(exc)
                with self._condition:
                    self._output_active = False
                    if revision == self._revision and not self._closed:
                        if failure:
                            self._error = failure
                            self.transport.state = 'error'
                        elif finished:
                            self.transport.state = 'finished'
                    self._condition.notify_all()


class PlaybackSession:
    """메인 스레드에서 준비 완료 세대를 검증하고 임시 PCM 수명을 관리한다."""

    def __init__(self):
        """재생 파일을 선택하거나 자동 재생하지 않는 빈 세션을 만든다."""
        self.source = None
        self.player = None
        self.prepared = None
        self.error = ''
        self.preparing = False
        self._generation = 0
        self._cancel = threading.Event()
        self._events = queue.Queue()
        self._workers = []
        self._retired = []
        self.position = 0.0
        self.loop = None

    def set_source(self, path, start=0, end=0):
        """분석에 사용한 원본과 구간을 저장하며 이전 작업은 무효화한다."""
        source = (str(Path(path).resolve()), float(start), float(end)) if path else None
        if source == self.source:
            return
        self.clear()
        self.source = source

    def clear(self):
        """이전 준비 결과와 출력 자원을 비차단 방식으로 회수 요청한다."""
        self._cancel.set()
        self._generation += 1
        if self.player:
            self.player.close()
            self._retired.append((self.player, self.prepared))
        self.player = self.prepared = self.source = None
        self.preparing = False
        self.position = 0.0
        self.loop = None
        self.error = ''
        self.poll()

    def toggle(self, language='ko'):
        """사용자 클릭으로만 PCM 준비 후 재생하거나 현재 재생을 일시 정지한다."""
        if self.preparing:
            self.stop()
        elif self.player:
            if self.player.snapshot()['state'] in ('playing', 'draining'):
                self.player.pause()
            else:
                self.player.play()
        elif self.source:
            self.error = ''
            self.preparing = True
            self._cancel = threading.Event()
            worker = threading.Thread(target=self._prepare, args=(self._generation, self.source, self._cancel, language),
                                      name='ToneMatchPlaybackDecode', daemon=True)
            self._workers.append(worker)
            worker.start()

    def _prepare(self, generation, source, cancel, language):
        """백그라운드에서는 UI를 만지지 않고 소유권과 오류를 큐로 전달한다."""
        try:
            prepared = PreparedAudio.decode(*source, cancel_requested=cancel.is_set, language=language)
            self._events.put((generation, prepared, ''))
        except Exception as exc:
            self._events.put((generation, None, str(exc)))

    def poll(self):
        """현재 요청의 결과만 채택하고 사용이 끝난 파일을 정리한다."""
        while True:
            try:
                generation, prepared, error = self._events.get_nowait()
            except queue.Empty:
                break
            if generation != self._generation:
                if prepared:
                    prepared.close()
                continue
            self.preparing = False
            self.error = error
            if prepared:
                player = None
                try:
                    player = WavPlayer(prepared.path)
                    player.seek(min(self.position, player.snapshot()['duration']))
                    if self.loop:
                        player.set_loop(*self.loop)
                    player.play()
                    self.player, self.prepared = player, prepared
                except Exception as exc:
                    if player is not None:
                        player.close()
                        self._retired.append((player, prepared))
                    else:
                        prepared.close()
                    self.error = str(exc)
        pending = []
        for player, prepared in self._retired:
            if player.wait_closed():
                if prepared:
                    prepared.close()
            else:
                pending.append((player, prepared))
        self._retired = pending
        self._workers = [worker for worker in self._workers if worker.is_alive()]

    def seek(self, seconds):
        """준비 전 선택 위치도 보존해 첫 재생부터 해당 마디를 듣게 한다."""
        seconds = float(seconds)
        if not math.isfinite(seconds) or seconds < 0:
            raise ValueError('Invalid playback position')
        if self.player:
            self.player.seek(min(seconds, self.player.snapshot()['duration']))
        self.position = seconds

    def set_loop(self, start=None, end=None):
        """UI에서 선택한 마디 반복 범위를 준비 전후 동일하게 보존한다."""
        candidate = None if start is None and end is None else (float(start), float(end))
        if candidate and (not all(math.isfinite(value) for value in candidate) or not 0 <= candidate[0] < candidate[1]):
            raise ValueError('Invalid loop range')
        if self.player:
            self.player.set_loop(*(candidate or (None, None)))
        self.loop = candidate

    def stop(self):
        """준비 중 재생 예약까지 취소하고 이미 준비된 음원은 유지한다."""
        if self.preparing:
            self._cancel.set()
            self._generation += 1
            self.preparing = False
        if self.player:
            self.player.stop()
        self.position = 0.0

    def suspend(self):
        """장치 사용 작업에 앞서 멈추고 완전히 회수됐는지 반환한다."""
        self.stop()
        self.poll()
        return not self._workers and not self._retired and not (self.player and self.player.snapshot()['output_active'])

    def is_closed(self):
        """종료 시 모든 임시 파일 작업자가 빠져나왔는지 검사한다."""
        self.poll()
        return not self.player and not self._workers and not self._retired
