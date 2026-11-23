"""로컬 연습 반주 합성, 정렬된 PCM 믹싱, 장치 없는 WAV/MP3 저장."""

from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import wave

import numpy as np

from chord_edits import parse_symbol
from practice_chart import PracticeProject
from stem_removal import _commit_new_output, _ffmpeg_path, _stop_process


PARTS = ("drums", "bass", "chords", "click")
RATE = 44100
MAX_FRAMES = 20 * 60 * RATE
_MAX_READ = 65536
_PEAKS = (0.36, 0.22, 0.24, 0.14)


class PracticeCancelled(RuntimeError):
    """The owner cancelled synthetic rendering or export."""


@dataclass(frozen=True)
class MixSettings:
    """One validated, immutable snapshot of the four faders and master."""

    levels: tuple[float, ...] = (1, 1, 1, 0)
    muted: tuple[bool, ...] = (False, False, False, False)
    solo: str | None = None
    master: float = 1

    def __post_init__(self):
        if not isinstance(self.levels, tuple) or len(self.levels) != len(PARTS):
            raise ValueError("Expected four mixer levels.")
        if not isinstance(self.muted, tuple) or len(self.muted) != len(PARTS) or any(
                type(value) is not bool for value in self.muted):
            raise ValueError("Expected four mute switches.")
        if any(type(value) not in (int, float) or not 0 <= value <= 1
               for value in (*self.levels, self.master)):
            raise ValueError("Mixer levels must be between 0 and 1.")
        if self.solo is not None and self.solo not in PARTS:
            raise ValueError("Unknown solo part.")

    def enabled(self, index):
        return not self.muted[index] and (self.solo is None or self.solo == PARTS[index])


@dataclass(frozen=True)
class _Groove:
    kick: tuple[float, ...]
    snare: tuple[float, ...]
    cymbal: tuple[float, ...]
    bass: tuple[float, ...]
    comp: tuple[float, ...]
    bass_gate: float
    chord_gate: float
    brightness: float
    percussion: str = "hat"
    drum_level: float = 1.0
    walking: bool = False


_EIGHTHS = (0, .5, 1, 1.5, 2, 2.5, 3, 3.5)
_SWUNG = (0, 2 / 3, 1, 5 / 3, 2, 8 / 3, 3, 11 / 3)
_GROOVES = {
    "Rock": _Groove((0, 2, 2.5), (1, 3), _EIGHTHS, _EIGHTHS,
                    (0, 1.5, 2, 3), .82, .81, .75),
    "Pop": _Groove((0, 1.5, 2.5), (1, 3), _EIGHTHS, (0, .75, 1.5, 2.5, 3.25),
                   (0, .75, 1.5, 2.5, 3.5), .75, .69, .59, drum_level=.88),
    "Ballad": _Groove((0, 2.5), (2,), (0, 1, 2, 3), (0, 2),
                      (0, 2), .96, .95, .32, drum_level=.58),
    "Funk": _Groove((0, .75, 1.5, 2.75, 3.5), (1, 2.25, 3), _EIGHTHS + (1.75, 3.75),
                    (0, .75, 1.25, 1.75, 2.5, 3.25), (.5, 1.25, 2.75, 3.5),
                    .61, .39, .92),
    "Blues Shuffle": _Groove((0, 2, 8 / 3), (1, 3), _SWUNG, (0, 1, 2, 3),
                             (0, 2 / 3, 5 / 3, 2, 8 / 3, 11 / 3), .88, .54, .71,
                             walking=True),
    "Bossa Nova": _Groove((0, 1.5, 2, 3.5), (1, 2.5, 3.5), _EIGHTHS, (0, 1.5, 2, 3.5),
                          (0, 1, 2.5, 3.5), .87, .58, .43, "rim", .68),
    "Jazz Swing": _Groove((0, 2), (1, 3), (0, 1, 5 / 3, 2, 3, 11 / 3), (0, 1, 2, 3),
                          (0, 5 / 3, 8 / 3), .94, .73, .48, "ride", .61, True),
}


def _check_cancelled(cancel_requested):
    if cancel_requested is not None and cancel_requested():
        raise PracticeCancelled("Practice audio processing was cancelled.")


def _pcm16(samples):
    if not np.all(np.isfinite(samples)):
        raise ValueError("Practice audio contains invalid samples.")
    return np.rint(np.clip(samples, -1.0, 1.0) * 32767).astype("<i2").tobytes()


def _percussion():
    """Precompute bounded one-shots with deterministic noise and smooth tails."""
    rng = np.random.default_rng(412)

    def voice(seconds, decay, amp, body):
        t = np.arange(round(seconds * RATE), dtype=np.float64) / RATE
        attack = np.minimum(1.0, t / .002)
        release = np.minimum(1.0, (seconds - t) / .015)
        return (amp * attack * release * np.exp(-decay * t) * body(t)).astype(np.float32)

    def noise(t):
        signal = rng.uniform(-1, 1, len(t))
        return np.diff(signal, prepend=0) * .5

    return {
        "kick": voice(.24, 18, .18, lambda t: np.sin(2 * np.pi * (53 * t + 49 / 32 * (1 - np.exp(-32 * t))))),
        "snare": voice(.19, 25, .155, lambda t: .75 * noise(t) + .25 * np.sin(2 * np.pi * 178 * t)),
        "stick": voice(.09, 48, .115, lambda t: .6 * noise(t) + .4 * np.sin(2 * np.pi * 980 * t)),
        "hat": voice(.095, 49, .054, noise),
        "ride": voice(.265, 16, .063, lambda t: .7 * noise(t) + .3 * np.sin(2 * np.pi * 4303 * t)),
        "downbeat": voice(.085, 43, .138, lambda t: np.sin(2 * np.pi * 1670 * t)),
        "beat": voice(.065, 56, .101, lambda t: np.sin(2 * np.pi * 1175 * t)),
    }


def _add_hit(track, first, sample, scale=1.0):
    count = min(len(sample), len(track) - first)
    if count > 0:
        track[first:first + count] += sample[:count] * scale


def _tone(track, first, stop, notes, amplitude, brightness, decay):
    """Place a harmonic voice with an attack and release inside the chord slot."""
    if stop <= first:
        return
    frames = stop - first
    t = np.arange(frames, dtype=np.float64) / RATE
    duration = frames / RATE
    envelope = np.minimum(1.0, t / .008) * np.minimum(1.0, (duration - t) / .018)
    envelope *= np.exp(-decay * t)
    signal = np.zeros(frames)
    for midi in notes:
        phase = 2 * np.pi * (440 * 2 ** ((midi - 69) / 12)) * t
        signal += np.sin(phase) + brightness * (.27 * np.sin(2 * phase) + .09 * np.sin(3 * phase))
    track[first:stop] += amplitude / len(notes) * signal * envelope


def _slots(pattern, start_beat, end_beat, gate):
    """Start at each chord boundary even when the groove has no hit there."""
    onsets = [start_beat, *(beat for beat in pattern if start_beat < beat < end_beat)]
    for first, limit in zip(onsets, onsets[1:] + [end_beat]):
        yield first, first + (limit - first) * gate


def _music_bar(tracks, at, one_shots, groove, harmony):
    drum, bass, chord, _ = tracks
    for pattern, hit in ((groove.kick, "kick"), (groove.snare, "stick" if groove.percussion == "rim" else "snare"),
                         (groove.cymbal, "ride" if groove.percussion == "ride" else "hat")):
        for beat in pattern:
            _add_hit(drum, at(beat), one_shots[hit], groove.drum_level * (1 if beat % 1 == 0 else .72))
    for start, end, parsed in harmony:
        if parsed is None:
            continue
        root, slash = parsed["root_pc"], parsed["bass_pc"]
        pitches = parsed["pitch_classes"]
        for index, (first, stop) in enumerate(_slots(groove.bass, start, end, groove.bass_gate)):
            pc = slash if slash is not None else root
            if slash is None and groove.walking:
                pc = pitches[index % len(pitches)]
            _tone(bass, at(first), at(stop), (36 + pc,), .19, .49, 1.8)
        chord_root = 52 + (root - 4) % 12
        # The parser preserves interval order. Wrapped extensions sound above the triad.
        notes = []
        for pc in pitches:
            note = chord_root + (pc - root) % 12
            while notes and note < notes[-1]:
                note += 12
            notes.append(note)
        for first, stop in _slots(groove.comp, start, end, groove.chord_gate):
            _tone(chord, at(first), at(stop), notes, .17, groove.brightness, 2.5)


class _PracticeReader:
    """WAV-compatible streaming reader over a generated arrangement."""

    def __init__(self, audio, streams, settings_provider):
        self.audio = audio
        self.streams = streams
        self.settings_provider = settings_provider
        self.position = 0

    def getnframes(self):
        return self.audio.frames

    def getframerate(self):
        return self.audio.rate

    def getnchannels(self):
        return 1

    def getsampwidth(self):
        return 2

    def setpos(self, frame):
        if type(frame) is not int or not 0 <= frame <= self.audio.frames:
            raise ValueError("Practice position outside audio.")
        self.position = frame

    def readframes(self, count):
        """Apply one mix snapshot to a bounded frame range."""
        if type(count) is not int or not 0 <= count <= _MAX_READ:
            raise ValueError("Invalid practice block size.")
        count = min(count, self.audio.frames - self.position)
        settings = self.settings_provider()
        if not isinstance(settings, MixSettings):
            raise TypeError("Expected practice mixer settings.")
        result = np.zeros(count, dtype=np.float32)
        pre_roll = min(count, max(0, self.audio.start_frame - self.position))
        for index, stream in enumerate(self.streams):
            click_pre_roll = PARTS[index] == "click" and pre_roll > 0
            if not settings.enabled(index) or (not settings.levels[index] and not click_pre_roll):
                continue
            stream.seek(self.position * 2)
            raw = stream.read(count * 2)
            if len(raw) != count * 2:
                raise ValueError("Practice track PCM is truncated.")
            data = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32767
            result += data * settings.levels[index]
            if click_pre_roll:
                result[:pre_roll] += data[:pre_roll] * (1 - settings.levels[index])
        self.position += count
        return _pcm16(result * settings.master)


class PracticeAudio:
    """Own the generated parts until playback and export readers close."""

    rate = RATE

    def __init__(self, temporary, frames, bar_starts):
        self._temporary = temporary
        self._paths = tuple(Path(temporary.name) / f"{part}.pcm" for part in PARTS)
        self.frames = frames
        self.bar_starts = bar_starts
        self.start_frame = bar_starts[0]

    @contextmanager
    def open_mix(self, settings_provider):
        """Open aligned tracks for a single reader; no output device is created."""
        with ExitStack() as stack:
            streams = tuple(stack.enter_context(path.open("rb")) for path in self._paths)
            yield _PracticeReader(self, streams, settings_provider)

    def close(self):
        """Remove owned temporary files after all readers have stopped."""
        self._temporary.cleanup()

    def export(self, destination, settings, part=None, cancel_requested=None):
        """Save a mono mix or isolated part without the pre-roll; reject overwrite."""
        _check_cancelled(cancel_requested)
        target = Path(destination).absolute()
        suffix = target.suffix.lower()
        if suffix not in (".wav", ".mp3") or (part is not None and (part not in PARTS or suffix != ".wav")):
            raise ValueError("Use WAV or MP3 for the mix and WAV for individual parts.")
        if target.exists() or target.is_symlink():
            raise FileExistsError("The selected export file already exists.")
        if not isinstance(settings, MixSettings):
            raise TypeError("Expected practice mixer settings.")
        if part is not None:
            settings = MixSettings(levels=(1, 1, 1, 1), solo=part)
        with tempfile.TemporaryDirectory(prefix=".practice-", dir=target.parent) as folder:
            wav = Path(folder) / "audio.wav"
            with self.open_mix(lambda: settings) as reader, wave.open(str(wav), "wb") as output:
                output.setparams((1, 2, self.rate, 0, "NONE", "not compressed"))
                reader.setpos(self.start_frame)
                while reader.position < self.frames:
                    _check_cancelled(cancel_requested)
                    output.writeframesraw(reader.readframes(_MAX_READ))
            partial = wav
            if suffix == ".mp3":
                partial = Path(folder) / "audio.mp3"
                _encode_mp3(wav, partial, cancel_requested)
            _check_cancelled(cancel_requested)
            _commit_new_output(partial, target, "ko")
        return target


def _encode_mp3(source, destination, cancel_requested):
    """Run only the bundled converter on a generated WAV, without console or audio output."""
    _check_cancelled(cancel_requested)
    converter = _ffmpeg_path()
    if not converter.is_file():
        raise RuntimeError("The bundled FFmpeg is required for MP3 export.")
    command = [str(converter), "-hide_banner", "-loglevel", "error", "-nostdin",
               "-protocol_whitelist", "file", "-f", "wav", "-i", str(source),
               "-map", "0:a:0", "-c:a", "libmp3lame", "-q:a", "3", "-n", str(destination)]
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL,
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    try:
        deadline = time.monotonic() + 180
        while True:
            _check_cancelled(cancel_requested)
            if time.monotonic() >= deadline:
                raise RuntimeError("MP3 export timed out.")
            try:
                code = process.wait(timeout=.15)
                break
            except subprocess.TimeoutExpired:
                continue
    finally:
        if process.poll() is None:
            _stop_process(process)
    if code or not destination.is_file() or not destination.stat().st_size:
        raise RuntimeError("MP3 encoding failed.")


def render_practice(project, cancel_requested=None):
    """Generate four aligned local tracks, one bar per frame allocation."""
    if not isinstance(project, PracticeProject):
        raise TypeError("Expected a validated practice project.")
    _check_cancelled(cancel_requested)
    if project.style not in _GROOVES:
        raise ValueError("Unsupported practice style.")
    groove = _GROOVES[project.style]
    frames_per_beat = 60 * RATE / project.bpm

    def frame(beat):
        return round(beat * frames_per_beat)

    end_bar = project.count_in + len(project.bars)
    frames = frame(end_bar * 4)
    if not 0 < frames <= MAX_FRAMES:
        raise ValueError("Practice arrangement exceeds the render duration limit.")
    bar_starts = tuple(frame(bar * 4) for bar in range(project.count_in, end_bar))
    if not bar_starts:
        raise ValueError("The practice chart is empty.")
    for number, bar in enumerate(project.bars, 1):
        if "?" in bar.chords:
            raise ValueError(f"Unresolved chord in bar {number}.")
    temporary = tempfile.TemporaryDirectory(prefix="tonematch-practice-")
    audio = PracticeAudio(temporary, frames, bar_starts)
    try:
        required = frames * len(PARTS) * 2 + 64 * 1024 * 1024
        if shutil.disk_usage(temporary.name).free < required:
            raise OSError("Not enough temporary disk space for practice audio.")
        one_shots = _percussion()
        with ExitStack() as stack:
            streams = tuple(stack.enter_context(path.open("wb")) for path in audio._paths)
            for index in range(end_bar):
                _check_cancelled(cancel_requested)
                beat_origin = index * 4
                first = frame(beat_origin)

                def at(beat):
                    return frame(beat_origin + beat) - first

                tracks = np.zeros((len(PARTS), at(4)), dtype=np.float32)
                for beat in range(4):
                    _add_hit(tracks[3], at(beat), one_shots["downbeat" if beat == 0 else "beat"])
                if index >= project.count_in:
                    chart_bar = project.bars[index - project.count_in]
                    accumulated = 0
                    harmony = []
                    for symbol, beats in zip(chart_bar.chords, chart_bar.beats):
                        harmony.append((accumulated, accumulated + beats,
                                        None if symbol == "-" else parse_symbol(symbol)))
                        accumulated += beats
                    _music_bar(tracks, at, one_shots, groove, harmony)
                for stream, track, peak in zip(streams, tracks, _PEAKS):
                    stream.write(_pcm16(np.clip(track, -peak, peak)))
        _check_cancelled(cancel_requested)
        return audio
    except BaseException:
        audio.close()
        raise
