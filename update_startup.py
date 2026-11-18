"""Post-import executable startup presentation and optional verified update.

Network/archive work uses one daemon thread. The Tk thread alone renders status,
honours cancellation and hands off to a verified executable. No work runs on import.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import queue
import re
import subprocess
import sys
import tempfile
import threading
import time

from package_runtime import package_identity


_launched_processes = []  # Keep the detached Popen alive until this process exits.


def cache_root() -> Path:
    return Path(os.environ.get('LOCALAPPDATA', tempfile.gettempdir())) / 'ToneMatchTMP' / 'updates'


def should_show_startup(arguments=None) -> bool:
    """The EXE intro is independent of portable update eligibility."""
    arguments = sys.argv[1:] if arguments is None else arguments
    return (bool(getattr(sys, 'frozen', False)) and sys.platform == 'win32'
            and not any(value.startswith(('--self-test', '--stem-self-test')) for value in arguments))


def should_check_for_updates(arguments=None) -> bool:
    arguments = sys.argv[1:] if arguments is None else arguments
    return (should_show_startup(arguments) and '--skip-update' not in arguments
            and package_identity().status == 'unpackaged')


def inherited_context() -> tuple[Path, Path] | None:
    """Accept original data context only inside its own managed update tree."""
    if not getattr(sys, 'frozen', False) or package_identity().status != 'unpackaged':
        return None
    from auto_update import installation_cache
    try:
        executable = Path(sys.executable).resolve()
        origin = Path(os.environ['TONEMATCH_UPDATE_ORIGIN'])
        data = Path(os.environ['TONEMATCH_UPDATE_DATA'])
        target = Path(os.environ['TONEMATCH_UPDATE_TARGET'])
        if not all(path.is_absolute() for path in (origin, data, target)):
            return None
        origin, data = origin.resolve(), data.resolve()
        if not origin.is_dir() or target.resolve() != executable:
            return None
        match = re.fullmatch(r'ToneMatchTMP-v(\d+\.\d+\.\d+)\.exe', executable.name)
        if not match:
            return None
        expected = (installation_cache(origin, cache_root()) / 'versions'
                    / ('ToneMatchTMP-v' + match[1]) / executable.name)
        if expected.resolve() != executable or expected.is_symlink() or expected.parent.is_symlink():
            return None
        fallback = cache_root().parent.resolve()
        if data not in ((origin / 'data').resolve(), fallback):
            return None
        return origin, data
    except (KeyError, OSError, ValueError):
        return None


def _windows_dll_directory(path) -> None:
    if sys.platform == 'win32':
        import ctypes
        if not ctypes.windll.kernel32.SetDllDirectoryW(path):
            raise ctypes.WinError()


def launch_update(executable: Path, installation_root: Path, data_root: Path) -> None:
    """Launch only the core's verified target, with an independent frozen runtime."""
    if package_identity().status != 'unpackaged':
        raise ValueError('Portable update launch requires an unpackaged process package identity.')
    executable = executable.resolve()
    environment = os.environ.copy()
    environment.update({
        'PYINSTALLER_RESET_ENVIRONMENT': '1',
        'TONEMATCH_UPDATE_ORIGIN': str(installation_root.resolve()),
        'TONEMATCH_UPDATE_DATA': str(data_root.resolve()),
        'TONEMATCH_UPDATE_TARGET': str(executable),
        # Keep generated JIT files outside the immutable verified runtime.
        # This is inherited before the child's NumPy/librosa/Numba imports.
        'NUMBA_CACHE_DIR': str(data_root.resolve() / 'cache' / 'numba'),
    })
    runtime = getattr(sys, '_MEIPASS', None)
    if runtime:
        runtime_root = Path(runtime).resolve()
        environment['PATH'] = os.pathsep.join(
            item for item in environment.get('PATH', '').split(os.pathsep)
            if item and not Path(item).resolve().is_relative_to(runtime_root))
    # The PyInstaller Windows DLL directory is inherited by subprocesses. Reset
    # it around launch and restore it if this app must continue after a failure.
    _windows_dll_directory(None)
    try:
        process = subprocess.Popen(
            [str(executable), '--skip-update'], cwd=str(executable.parent),
            env=environment, shell=False, close_fds=True,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        _launched_processes.append(process)
    finally:
        _windows_dll_directory(runtime)


class StartupController:
    """Small testable worker-to-main-thread boundary; no Tk dependency."""

    def __init__(self, version, installation_root, data_root, update_cache, view, finish,
                 *, prepare=None, launch=launch_update):
        if prepare is None:
            from auto_update import prepare_update
            prepare = prepare_update
        self.version = version
        self.installation_root = installation_root
        self.data_root = data_root
        self.update_cache = update_cache
        self.view = view
        self.finish = finish
        self.prepare = prepare
        self.launch = launch
        self.cancel_event = threading.Event()
        self.progress_queue = queue.Queue(maxsize=1)
        self.result_queue = queue.Queue(maxsize=1)
        self.finished = False

    def start(self) -> None:
        if not self.finished:
            threading.Thread(target=self._work, name='ToneMatch-update', daemon=True).start()

    def _progress(self, stage, done=0, total=0) -> None:
        try:
            self.progress_queue.get_nowait()
        except queue.Empty:
            pass
        self.progress_queue.put_nowait((stage, done, total))

    def _work(self) -> None:
        try:
            target = self.prepare(self.version, self.installation_root, self.update_cache,
                                  self.cancel_event, self._progress)
        except Exception:
            # Updates are optional: a transport/cache failure must not prevent
            # the installed application from opening. Never show private paths.
            self._progress('unavailable')
            target = None
        self.result_queue.put_nowait(target)

    def _finish(self, exit_application: bool) -> None:
        if not self.finished:
            self.finished = True
            self.finish(exit_application)

    def cancel(self, exit_application=False) -> None:
        self.cancel_event.set()
        self._finish(exit_application)

    def poll(self) -> bool:
        """Called by the main thread; return whether polling should continue."""
        if self.finished:
            return False
        try:
            self.view.progress(*self.progress_queue.get_nowait())
        except queue.Empty:
            pass
        try:
            target = self.result_queue.get_nowait()
        except queue.Empty:
            return True
        if self.cancel_event.is_set() or target is None:
            self._finish(False)
        else:
            try:
                self.launch(target, self.installation_root, self.data_root)
            except (OSError, ValueError):
                self.view.progress('unavailable', 0, 0)
                self._finish(False)
            else:
                self._finish(True)
        return False


def waveform_heights(elapsed: float) -> tuple[float, ...]:
    """Decorative half-heights, unrelated to audio or measured progress."""
    return tuple(3.0 + 33.0 * math.exp(-((index - 12) / 9.0) ** 2)
                 * (0.25 + 0.75 * math.sin(elapsed * 3.2 - index * 0.38) ** 2)
                 for index in range(25))


class WaveformAnimation:
    """Own a bounded set of Canvas items and a single main-thread timer."""

    def __init__(self, root, canvas):
        self.root = root
        self.canvas = canvas
        self.started = time.monotonic()
        self.stopped = False
        self.job = None
        self.bars = [canvas.create_line(18 + index * 12, 46, 18 + index * 12, 46,
                                       fill='#39d6a5', width=5, capstyle='round')
                     for index in range(25)]
        self._tick()

    def _tick(self):
        from tkinter import TclError
        self.job = None
        if self.stopped:
            return
        try:
            heights = waveform_heights(time.monotonic() - self.started)
            for index, (item, height) in enumerate(zip(self.bars, heights)):
                x = 18 + index * 12
                self.canvas.coords(item, x, 46 - height, x, 46 + height)
            self.job = self.root.after(33, self._tick)
        except TclError:
            # Motion is optional: a missing canvas must not block continuation.
            self.stopped = True

    def stop(self):
        from tkinter import TclError
        self.stopped = True
        if self.job is not None:
            try:
                self.root.after_cancel(self.job)
            except TclError:
                pass
            self.job = None


class _StartupView:
    """One branded surface for the brief intro and real update progress."""

    def __init__(self, root, language, version):
        import tkinter as tk
        from tkinter import ttk
        self.english = language == 'en'
        font = 'Arial Narrow' if self.english else 'Malgun Gothic'
        self.root = root
        self.destroyed = False
        self.frame = tk.Frame(root, bg='#121b24', padx=24, pady=24)
        self.frame.pack(fill='both', expand=True)
        root.title('ToneMatch TMP')
        root.configure(bg='#121b24')
        width, height = 540, 350
        left = max(0, (root.winfo_screenwidth() - width) // 2)
        top = max(0, (root.winfo_screenheight() - height) // 2)
        root.geometry(f'{width}x{height}+{left}+{top}')
        root.minsize(480, 350)
        heading = tk.Frame(self.frame, bg='#121b24')
        heading.pack(fill='x')
        tk.Label(heading, text='ToneMatch TMP', font=('Arial Narrow', 25, 'bold'),
                 bg='#121b24', fg='#edf4f7').pack(side='left')
        tk.Label(heading, text=f'v{version}', font=('Arial Narrow', 11),
                 bg='#121b24', fg='#9fb0bc').pack(side='right', anchor='s', pady=5)
        self.canvas = tk.Canvas(self.frame, width=324, height=92, bg='#121b24',
                                highlightthickness=0)
        self.canvas.pack(pady=(8, 0))
        self.animation = WaveformAnimation(root, self.canvas)
        self.status = tk.Label(self.frame, text='', font=(font, 11),
                               bg='#121b24', fg='#edf4f7', wraplength=450, anchor='w')
        self.status.pack(fill='x', pady=(8, 8))
        style = ttk.Style(root)
        try:
            style.theme_use('clam')
        except tk.TclError:
            pass
        style.configure('Update.Horizontal.TProgressbar', troughcolor='#283846',
                        background='#39d6a5', borderwidth=0)
        self.bar = ttk.Progressbar(self.frame, mode='indeterminate',
                                   style='Update.Horizontal.TProgressbar')
        self.bar.pack(fill='x')
        self.button = tk.Button(self.frame, font=(font, 11),
                                text='Use installed version' if self.english else '현재 버전 실행',
                                bg='#283846', fg='#edf4f7', activebackground='#39d6a5',
                                activeforeground='#0b1117', relief='flat', padx=12, pady=7)
        self.button.pack(anchor='e', pady=(16, 0))
        self.progress('opening', 0, 0)

    def progress(self, stage, done, total):
        labels = {
            'opening': ('Opening ToneMatch TMP…', 'ToneMatch TMP를 시작합니다…'),
            'checking': ('Checking for updates…', '최신 버전을 확인하고 있습니다…'),
            'downloading': ('Downloading update', '업데이트 다운로드 중'),
            'verifying': ('Verifying update', '업데이트 검증 중'),
            'ready': ('Opening updated version…', '새 버전을 실행합니다…'),
            'current': ('Opening installed version…', '현재 버전을 실행합니다…'),
            'unavailable': ('Update unavailable; opening installed version…',
                            '업데이트를 확인할 수 없어 현재 버전을 실행합니다…'),
        }
        text = labels.get(stage, labels['checking'])[0 if self.english else 1]
        self.bar.stop()
        if total > 0:
            percent = max(0., min(100., 100. * done / total))
            text += f' · {percent:.0f}%'
            self.bar.configure(mode='determinate', maximum=100, value=percent)
        elif stage != 'opening':
            self.bar.configure(mode='indeterminate')
            self.bar.start(30)
        else:
            # The waveform is activity feedback; there is no measured percentage.
            self.bar.configure(mode='determinate', maximum=100, value=0)
        self.status.configure(text=text)

    def destroy(self):
        from tkinter import TclError
        if self.destroyed:
            return
        self.destroyed = True
        self.animation.stop()
        try:
            self.bar.stop()
            self.frame.destroy()
        except TclError:
            pass


def run_startup(root, version: str, installation_root: Path, data_root: Path) -> bool:
    """Return True after handoff/close, False to open the installed application."""
    from tkinter import TclError
    try:
        settings_path = data_root / 'settings.json'
        settings = json.loads(settings_path.read_text(encoding='utf-8')) if settings_path.stat().st_size < 65536 else {}
        language = settings.get('language', 'ko') if isinstance(settings, dict) else 'ko'
    except (OSError, ValueError):
        language = 'ko'
    view = _StartupView(root, language, version)
    deadline = time.monotonic() + 0.7
    previous_close = root.protocol('WM_DELETE_WINDOW')
    temporary_close = None
    controller = None
    timers = set()
    exit_application = False
    finished = False

    def schedule(delay, callback):
        def invoke():
            timers.discard(identifier)
            if not finished:
                callback()
        identifier = root.after(delay, invoke)
        timers.add(identifier)

    def finish(exit_requested):
        nonlocal exit_application, finished
        if finished:
            return
        finished = True
        exit_application = exit_requested
        if controller is not None:
            controller.cancel(exit_application=exit_requested)
        root.quit()

    def update_finished(exit_requested):
        if finished:
            return
        if exit_requested:
            finish(True)
        else:
            # Updates and presentation overlap. Explicit continue/close bypass
            # this timer even if the updater controller has already finished.
            remaining = max(0, math.ceil((deadline - time.monotonic()) * 1000))
            # Even an expired intro must finish inside the event loop: Tk
            # clears a prior quit request when mainloop() starts.
            schedule(remaining, lambda: finish(False))

    def poll():
        if controller.poll():
            schedule(80, poll)

    try:
        view.button.configure(command=lambda: finish(False))
        root.protocol('WM_DELETE_WINDOW', lambda: finish(True))
        temporary_close = root.protocol('WM_DELETE_WINDOW')
        if should_check_for_updates():
            view.progress('checking', 0, 0)
            controller = StartupController(version, installation_root, data_root,
                                           cache_root(), view, update_finished)
            controller.start()
            schedule(0, poll)
        else:
            update_finished(False)
        root.mainloop()
    finally:
        finished = True
        if controller is not None:
            controller.cancel_event.set()
        for identifier in timers:
            try:
                root.after_cancel(identifier)
            except TclError:
                pass
        timers.clear()
        try:
            root.protocol('WM_DELETE_WINDOW', previous_close)
            if isinstance(temporary_close, str) and temporary_close != previous_close:
                root.deletecommand(temporary_close)
        except TclError:
            pass
        view.destroy()
    return exit_application
