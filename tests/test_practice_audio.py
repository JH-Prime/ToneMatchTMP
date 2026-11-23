"""Practice audio contracts exercised with PCM data and no output device."""

from contextlib import contextmanager
from dataclasses import replace
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import wave

import numpy as np

from practice_audio import PARTS, MixSettings, PracticeCancelled, render_practice
from practice_chart import PracticeProject, STYLES, parse_chart


@contextmanager
def rendered(chart, **settings):
    project = PracticeProject(parse_chart(chart), **settings)
    audio = render_practice(project)
    try:
        yield audio
    finally:
        audio.close()


def read_samples(audio, settings, start=0, count=8192):
    with audio.open_mix(lambda: settings) as source:
        source.setpos(start)
        return np.frombuffer(source.readframes(count), dtype="<i2")


class PracticeAudioTests(unittest.TestCase):
    def test_bar_frames_use_one_absolute_clock_and_align_all_exports(self):
        chart = "| Cmaj9 | F#m7b5 B7 | Em7 |"
        with rendered(chart, bpm=137, count_in=2) as audio, tempfile.TemporaryDirectory() as folder:
            positions = tuple(round(i * 4 * 60 * audio.rate / 137) for i in range(2, 6))
            self.assertEqual(audio.start_frame, positions[0])
            self.assertEqual(audio.bar_starts, positions[:-1])
            self.assertEqual(audio.frames, positions[-1])
            self.assertEqual(audio.rate, 44100)
            for part in (*PARTS, None):
                with self.subTest(part=part):
                    path = Path(folder) / f"{part}.wav"
                    audio.export(path, MixSettings(), part=part)
                    with wave.open(str(path), "rb") as source:
                        self.assertEqual(source.getsampwidth(), 2)
                        self.assertEqual(source.getframerate(), audio.rate)
                        self.assertEqual(source.getnframes(), audio.frames - audio.start_frame)
                        self.assertTrue(np.any(np.frombuffer(source.readframes(8192), dtype="<i2")))

    def test_count_in_and_live_mix_snapshot_have_distinct_controls(self):
        with rendered("| D |", count_in=1, bpm=120) as audio:
            settings = MixSettings()
            with audio.open_mix(lambda: settings) as source:
                preroll = source.readframes(8192)
                self.assertTrue(np.any(np.frombuffer(preroll, dtype="<i2")))
                source.setpos(0)
                settings = replace(settings, muted=(False, False, False, True))
                self.assertFalse(any(source.readframes(8192)))
                source.setpos(audio.start_frame)
                settings = MixSettings(solo="bass")
                self.assertTrue(any(source.readframes(8192)))
                source.setpos(audio.start_frame)
                settings = replace(settings, master=0)
                self.assertFalse(any(source.readframes(8192)))

    def test_slash_bass_changes_pitch_and_rest_silences_harmony(self):
        with rendered("| C/E | - |", bpm=120, count_in=0) as audio:
            bass = MixSettings(solo="bass")
            data = read_samples(audio, bass).astype(float)
            magnitude = np.abs(np.fft.rfft(data * np.hanning(len(data))))
            peak = int(magnitude[1:].argmax()) + 1
            # E is 41.2 or 82.4 Hz, while C is 32.7 or 65.4 Hz.
            dominant_hz = peak * audio.rate / len(data)
            self.assertLess(min(abs(dominant_hz - 41.2), abs(dominant_hz - 82.4)), 4)
            for part in ("bass", "chords"):
                with self.subTest(part=part):
                    self.assertFalse(np.any(read_samples(audio, MixSettings(solo=part),
                                                         start=audio.bar_starts[1])))

    def test_styles_produce_distinct_deterministic_audio_with_headroom(self):
        chart = "| Cmaj13 | G7b9 |"
        signatures = set()
        for style in (*STYLES, STYLES[0]):
            with self.subTest(style=style), rendered(chart, bpm=133, style=style, count_in=0) as audio:
                settings = MixSettings(levels=(1, 1, 1, 1))
                with audio.open_mix(lambda: settings) as source:
                    chunks = []
                    while raw := source.readframes(8192):
                        samples = np.frombuffer(raw, dtype="<i2")
                        self.assertLess(np.max(np.abs(samples.astype(np.int32))), 32767)
                        chunks.append(raw)
                signatures.add(hashlib.sha256(b"".join(chunks)).digest())
        self.assertEqual(len(signatures), len(STYLES))

    def test_export_cancellation_and_collision_preserve_existing_file(self):
        with rendered("| C |", count_in=0) as audio, tempfile.TemporaryDirectory() as folder:
            dest = Path(folder) / "mix.wav"
            self.assertRaises(PracticeCancelled, audio.export, dest, MixSettings(), cancel_requested=lambda: True)
            self.assertEqual(list(Path(folder).iterdir()), [])
            existing = b"keep these bytes"
            dest.write_bytes(existing)
            self.assertRaises(FileExistsError, audio.export, dest, MixSettings())
            self.assertEqual(dest.read_bytes(), existing)
            self.assertEqual(list(Path(folder).iterdir()), [dest])

    def test_render_cancellation_cleans_up_partial_track_files(self):
        project = PracticeProject(parse_chart("| Cm | F7 | Bb |"), count_in=1)
        with tempfile.TemporaryDirectory() as root, patch("practice_audio.tempfile.tempdir", root):
            calls = iter((False, False, False, True))
            self.assertRaises(PracticeCancelled, render_practice, project,
                              cancel_requested=lambda: next(calls, True))
            self.assertEqual(list(Path(root).iterdir()), [])

    def test_unresolved_chord_refuses_to_render(self):
        project = PracticeProject(parse_chart("| C | ? |"))
        with self.assertRaisesRegex(ValueError, "2"):
            render_practice(project)

    def test_checked_in_ffmpeg_encodes_mp3_without_a_device(self):
        with rendered("| Fsus4 C7 |", count_in=0) as audio, tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "practice.mp3"
            audio.export(path, MixSettings())
            data = path.read_bytes()
            self.assertGreater(len(data), 2048)
            self.assertTrue(data.startswith(b"ID3") or (data[0] == 0xff and data[1] & 0xe0 == 0xe0))
