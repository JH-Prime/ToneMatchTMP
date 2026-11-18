"""Procedural startup motion without a Tk window or audio source."""
import math
import unittest
from unittest.mock import patch

import update_startup as startup


class FakeCanvas:
    def __init__(self):
        self.items = {}
        self.updates = 0

    def create_line(self, *coordinates, **options):
        item = len(self.items) + 1
        self.items[item] = coordinates
        return item

    def coords(self, item, *coordinates):
        self.updates += 1
        self.items[item] = coordinates


class FakeRoot:
    def __init__(self):
        self.jobs = {}
        self.next_id = 0

    def after(self, delay, callback):
        self.next_id += 1
        self.jobs[self.next_id] = callback
        return self.next_id

    def after_cancel(self, job):
        self.jobs.pop(job, None)

    def tick(self):
        job, callback = next(iter(self.jobs.items()))
        del self.jobs[job]
        callback()


class WaveformTests(unittest.TestCase):
    def test_geometry_is_bounded_finite_and_moves_over_time(self):
        frames = [startup.waveform_heights(t) for t in (0.0, 0.1, 0.7, 10_000.0)]
        self.assertTrue(all(len(frame) == 25 for frame in frames))
        self.assertNotEqual(frames[0], frames[1])
        self.assertTrue(all(math.isfinite(h) and 3 <= h <= 36
                            for frame in frames for h in frame))

    def test_motion_reuses_items_and_stop_cancels_all_callbacks(self):
        root, canvas = FakeRoot(), FakeCanvas()
        with patch.object(startup.time, 'monotonic', return_value=100.0) as clock:
            animation = startup.WaveformAnimation(root, canvas)
            original_ids = set(canvas.items)
            self.assertEqual(len(original_ids), 25)
            before = dict(canvas.items)
            clock.return_value = 100.25
            root.tick()
            self.assertEqual(set(canvas.items), original_ids)
            self.assertNotEqual(canvas.items, before)
            self.assertEqual(len(root.jobs), 1)
            retained_callback = next(iter(root.jobs.values()))
            animation.stop()
            animation.stop()
            changes = canvas.updates
            retained_callback()
            self.assertEqual(canvas.updates, changes)
            self.assertFalse(root.jobs)

    def test_drawing_failure_stops_motion_without_raising(self):
        import tkinter
        root, canvas = FakeRoot(), FakeCanvas()
        animation = startup.WaveformAnimation(root, canvas)
        with patch.object(canvas, 'coords', side_effect=tkinter.TclError('destroyed')):
            root.tick()
        self.assertFalse(root.jobs)
        animation.stop()


if __name__ == '__main__':
    unittest.main()
