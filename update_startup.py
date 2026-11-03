"""Optional frozen-app startup update, before a working session is opened.

Network/archive work uses one daemon thread. The Tk thread alone renders status,
honours cancellation and hands off to a verified executable. No work runs on import.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import queue
import re
import subprocess
import sys
import tempfile
import threading


_launched_processes = []  # Keep the detached Popen alive until this process exits.


def cache_root() -> Path:
    return Path(os.environ.get('LOCALAPPDATA', tempfile.gettempdir())) / 'ToneMatchTMP' / 'updates'


def should_check_for_updates(arguments=None) -> bool:
    arguments = sys.argv[1:] if arguments is None else arguments
    return (bool(getattr(sys, 'frozen', False)) and sys.platform == 'win32'
            and '--skip-update' not in arguments
            and not any(value.startswith(('--self-test', '--stem-self-test')) for value in arguments))


def inherited_context() -> tuple[Path, Path] | None:
    """Accept original data context only inside its own managed update tree."""
    if not getattr(sys, 'frozen', False):
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


class _StartupView:
    """A compact progress surface; created only during normal executable startup."""

    def __init__(self, root, language):
        import tkinter as tk
        from tkinter import ttk
        self.english = language == 'en'
        font = 'Arial Narrow' if self.english else 'Malgun Gothic'
        self.root = root
        self.frame = tk.Frame(root, bg='#121b24', padx=24, pady=24)
        self.frame.pack(fill='both', expand=True)
        root.title('ToneMatch TMP')
        root.geometry('520x230')
        root.minsize(440, 220)
        tk.Label(self.frame, text='ToneMatch TMP', font=(font, 19, 'bold'),
                 bg='#121b24', fg='#edf4f7').pack(anchor='w')
        self.status = tk.Label(self.frame, text='', font=(font, 11),
                               bg='#121b24', fg='#edf4f7', wraplength=450, anchor='w')
        self.status.pack(fill='x', pady=(16, 8))
        style = ttk.Style(root)
        style.theme_use('clam')
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
        self.progress('checking', 0, 0)

    def progress(self, stage, done, total):
        labels = {
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
        else:
            self.bar.configure(mode='indeterminate')
            self.bar.start(30)
        self.status.configure(text=text)

    def destroy(self):
        self.bar.stop()
        self.frame.destroy()


def run_startup_update(root, version: str, installation_root: Path, data_root: Path) -> bool:
    """Return True after handoff/close, False to open the installed application."""
    try:
        settings_path = data_root / 'settings.json'
        settings = json.loads(settings_path.read_text(encoding='utf-8')) if settings_path.stat().st_size < 65536 else {}
        language = settings.get('language', 'ko') if isinstance(settings, dict) else 'ko'
    except (OSError, ValueError):
        language = 'ko'
    view = _StartupView(root, language)
    exit_application = False

    def finish(exit_requested):
        nonlocal exit_application
        exit_application = exit_requested
        root.quit()

    controller = StartupController(version, installation_root, data_root, cache_root(), view, finish)
    view.button.configure(command=controller.cancel)
    root.protocol('WM_DELETE_WINDOW', lambda: controller.cancel(exit_application=True))

    def poll():
        if controller.poll():
            root.after(80, poll)

    controller.start()
    root.after(0, poll)
    try:
        root.mainloop()
    finally:
        controller.cancel_event.set()
        view.destroy()
    return exit_application
