"""ToneMatch TMP v0.0.06 데스크톱 애플리케이션.

로컬 오디오·영상 또는 Windows PC 재생음 녹음을 받아 AI로 guitar stem만
분리하고, Tone Master Pro에 수동 적용할 설명 가능한 톤 체인을 추천한다.
"""

from __future__ import annotations

import atexit
import json
import math
import multiprocessing
import os
import platform
import queue
import sys
import tempfile
import threading
import time
import traceback
import wave
import webbrowser
import zipfile
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText


def _ensure_standard_streams() -> None:
    """콘솔 없는 EXE에서도 외부 라이브러리가 표준 출력에 안전하게 쓰도록 한다."""
    for name in ("stdout", "stderr"):
        if getattr(sys, name) is None:
            stream = open(os.devnull, "w", encoding="utf-8")
            setattr(sys, name, stream)
            atexit.register(stream.close)


_ensure_standard_streams()

import numpy as np

from catalog import APP_VERSION, BUILD_DATE, CHANGELOG, MODEL_GUIDE_REVISION, TARGET_FIRMWARE
from debug_info import (
    PIPELINE_BLOCKS,
    block_by_id,
    block_for_progress,
    changelog_as_text,
    code_for_block,
    localized_block,
    source_file_path,
)
from devices import (
    DEVICE_PROFILES,
    device_description,
    device_id_from_label,
    device_label,
    is_supported_device,
)
from engine import (
    MAX_ANALYSIS_SECONDS,
    AnalysisError,
    analyze_file,
    human_feature_rows,
    relocalize_result,
    save_json,
)
from i18n import LANGUAGE_LABELS, choice_code, choice_label, choice_values, language_code, tr
from reference_compare import ReferenceCompareError, compare_live_frame
from recorder import (
    MAX_RECORD_SECONDS,
    CaptureDevice,
    RecordingError,
    capture_device_label,
    list_capture_devices,
    monitor_capture_device,
    record_device_to_wav,
)
from report import recipe_as_text, save_html
from separator import separator_runtime_status
from spectrum import SpectrumFrame, SpectrumSmoother, analyze_spectrum_frame
from voicing import pitch_class_names


APP_NAME = "ToneMatch TMP"
INPUT_METHODS = ("local", "record")
SUPPORTED_AUDIO_PATTERN = "*.wav *.mp3 *.flac *.m4a *.aac *.ogg *.opus *.wma *.aiff *.aif *.mp4 *.mov *.mkv *.webm"


COLORS = {
    "bg": "#0b1117",
    "panel": "#121b24",
    "panel_alt": "#17232e",
    "border": "#283846",
    "text": "#edf4f7",
    "muted": "#9fb0bc",
    "accent": "#39d6a5",
    "accent_hover": "#50e5b8",
    "blue": "#59a8ff",
    "warning": "#ffca69",
    "danger": "#ff7b7b",
}


def _center_window(window: tk.Tk, width: int, height: int) -> None:
    """주 모니터 가운데에 창을 배치하되 작은 화면 경계를 넘지 않게 한다."""
    window.update_idletasks()
    screen_w = window.winfo_screenwidth()
    screen_h = window.winfo_screenheight()
    actual_width = min(width, max(980, screen_w - 40))
    actual_height = min(height, max(700, screen_h - 80))
    x = max(0, (screen_w - actual_width) // 2)
    y = max(0, (screen_h - actual_height) // 2)
    window.geometry(f"{actual_width}x{actual_height}+{x}+{y}")


def _portable_root() -> Path:
    """소스 실행 또는 PyInstaller onedir 실행의 포터블 루트를 반환한다."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _runtime_data_root() -> Path:
    """우선 EXE 옆 data를 쓰고 권한이 없으면 LocalAppData로 안전하게 폴백한다."""
    preferred = _portable_root() / "data"
    try:
        preferred.mkdir(parents=True, exist_ok=True)
        probe = preferred / ".write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return preferred
    except OSError:
        fallback = Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir())) / "ToneMatchTMP"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def _input_method_label(code: str, language: str) -> str:
    """입력 방법의 안정적인 코드에 대응하는 언어별 화면 라벨을 만든다."""
    return tr(f"input.{code}", language)


def _input_method_code(label: str) -> str:
    """한국어 또는 영어 입력 방법 라벨을 안정적인 코드로 되돌린다."""
    for code in INPUT_METHODS:
        if label in {_input_method_label(code, "ko"), _input_method_label(code, "en")}:
            return code
    return "local"


class ToneMatchApp:
    """한·영 UI, 녹음, 분석, 개발자 도구와 내보내기를 관리한다."""

    def __init__(self, root: tk.Tk) -> None:
        """영구 상태를 준비하고 전체 Tkinter 화면과 이벤트 루프를 구성한다."""
        self.root = root
        self.root.title(f"{APP_NAME} · v{APP_VERSION}")
        self.root.minsize(1080, 720)
        _center_window(root, 1320, 880)
        self.root.configure(bg=COLORS["bg"])
        self.data_root = _runtime_data_root()
        self.log_root = self.data_root / "logs"
        self.log_root.mkdir(parents=True, exist_ok=True)
        self.result: dict | None = None
        self.worker: threading.Thread | None = None
        self.record_worker: threading.Thread | None = None
        self.spectrum_worker: threading.Thread | None = None
        self.spectrum_stop_event: threading.Event | None = None
        self.spectrum_session_id = 0
        self.spectrum_stop_requested = False
        self.spectrum_frames: queue.Queue[tuple[int, SpectrumFrame]] = queue.Queue(maxsize=1)
        self.last_spectrum_frame: SpectrumFrame | None = None
        self.last_reference_comparison: dict | None = None
        self.events: queue.Queue[tuple] = queue.Queue()
        self.analysis_cancel_event = threading.Event()
        self.analysis_started_at: float | None = None
        self.analysis_elapsed_seconds = 0.0
        self.analysis_progress_percent = 0.0
        self.record_stop_event = threading.Event()
        self.closing = False
        self.temporary_recordings: set[Path] = set()
        self.capture_devices: list[CaptureDevice] = []
        self.capture_label_map: dict[str, CaptureDevice] = {}
        self.capture_device_id = ""
        self.language = "ko"
        self.device_id = "tone_master_pro"
        self.pickup_code = "unknown"
        self.mix_code = "auto"
        self.output_code = "frfr"
        self.compute_backend_code = "auto"
        self.input_method_code = "local"
        self.hardware_status: dict[str, object] = {}
        self.hardware_probe_active = False
        self.recipe_texts: list[ScrolledText] = []
        self.debug_nodes: dict[str, tuple[int, int]] = {}
        self.debug_log_lines: list[str] = []
        self.active_debug_block = "input"
        self.selected_debug_block = "input"
        self.completed_debug_blocks: set[str] = {"boot"}
        self._load_settings()

        self.file_var = tk.StringVar()
        self.url_var = tk.StringVar()
        self.start_var = tk.StringVar(value="0")
        self.end_var = tk.StringVar(value="0")
        self.record_limit_var = tk.StringVar(value="360")
        self.language_var = tk.StringVar(value=LANGUAGE_LABELS[self.language])
        self.device_var = tk.StringVar()
        self.pickup_var = tk.StringVar()
        self.mix_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.compute_var = tk.StringVar()
        self.input_method_var = tk.StringVar()
        self.capture_var = tk.StringVar()
        self.developer_var = tk.BooleanVar(value=False)

        self._configure_style()
        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(50, self._drain_spectrum_frames)
        self.root.after(80, self._drain_events)
        self.root.after(250, self._tick_analysis_progress)
        self.root.after(180, self._start_hardware_probe)

    @property
    def ui_font(self) -> str:
        """현재 언어에 맞춰 사용자가 지정한 기본 UI 글꼴을 반환한다."""
        return "Arial Narrow" if self.language == "en" else "Malgun Gothic"

    def _load_settings(self) -> None:
        """이전 실행의 언어·장치·연산 백엔드 선택을 읽되 손상된 파일은 무시한다."""
        path = self.data_root / "settings.json"
        try:
            settings = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return
        self.language = settings.get("language") if settings.get("language") in LANGUAGE_LABELS else self.language
        candidate_device = str(settings.get("device_id", self.device_id))
        if any(item["id"] == candidate_device for item in DEVICE_PROFILES):
            self.device_id = candidate_device
        candidate_compute = str(settings.get("compute_backend", self.compute_backend_code))
        if candidate_compute in {"auto", "cuda", "cpu"}:
            self.compute_backend_code = candidate_compute

    def _save_settings(self) -> None:
        """다음 실행에서도 유지할 언어·장치·연산 백엔드 선택을 작은 JSON으로 저장한다."""
        payload = {
            "language": self.language,
            "device_id": self.device_id,
            "compute_backend": self.compute_backend_code,
        }
        try:
            (self.data_root / "settings.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass

    def _configure_style(self) -> None:
        """현재 언어 글꼴과 어두운 색상표를 모든 공통 위젯 스타일에 적용한다."""
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        font = self.ui_font
        style.configure("TFrame", background=COLORS["bg"])
        style.configure("Panel.TFrame", background=COLORS["panel"], relief="flat")
        style.configure("Alt.TFrame", background=COLORS["panel_alt"], relief="flat")
        style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["text"], font=(font, 10))
        style.configure("Panel.TLabel", background=COLORS["panel"], foreground=COLORS["text"], font=(font, 10))
        style.configure("Muted.TLabel", background=COLORS["panel"], foreground=COLORS["muted"], font=(font, 9))
        style.configure("Title.TLabel", background=COLORS["bg"], foreground=COLORS["text"], font=(font, 23, "bold"))
        style.configure("Accent.TLabel", background=COLORS["bg"], foreground=COLORS["accent"], font=(font, 9, "bold"))
        style.configure("CardTitle.TLabel", background=COLORS["panel"], foreground=COLORS["text"], font=(font, 12, "bold"))
        style.configure("TButton", background=COLORS["panel_alt"], foreground=COLORS["text"], borderwidth=0, padding=(10, 7), font=(font, 9, "bold"))
        style.map("TButton", background=[("active", COLORS["border"]), ("disabled", "#1b242b")], foreground=[("disabled", "#64727c")])
        style.configure("Accent.TButton", background=COLORS["accent"], foreground="#06100d", padding=(16, 10), font=(font, 10, "bold"))
        style.map("Accent.TButton", background=[("active", COLORS["accent_hover"]), ("disabled", "#31594d")])
        style.configure("Danger.TButton", background="#583039", foreground="#ffd9df", padding=(12, 10), font=(font, 9, "bold"))
        style.configure("TEntry", fieldbackground="#0d151c", foreground=COLORS["text"], insertcolor=COLORS["text"], bordercolor=COLORS["border"], padding=7, font=(font, 9))
        style.configure("TCombobox", fieldbackground="#0d151c", background="#0d151c", foreground=COLORS["text"], arrowcolor=COLORS["muted"], bordercolor=COLORS["border"], padding=6, font=(font, 9))
        style.map("TCombobox", fieldbackground=[("readonly", "#0d151c")], foreground=[("readonly", COLORS["text"])])
        style.configure("Horizontal.TProgressbar", troughcolor="#1d2b35", background=COLORS["accent"], bordercolor="#1d2b35", lightcolor=COLORS["accent"], darkcolor=COLORS["accent"])
        style.configure("TNotebook", background=COLORS["panel"], borderwidth=0)
        style.configure("TNotebook.Tab", background="#111a22", foreground=COLORS["muted"], padding=(13, 8), borderwidth=0, font=(font, 9, "bold"))
        style.map("TNotebook.Tab", background=[("selected", COLORS["panel_alt"])], foreground=[("selected", COLORS["accent"])])
        style.configure("Developer.TCheckbutton", background=COLORS["bg"], foreground=COLORS["muted"], font=(font, 9, "bold"), padding=4)
        style.map("Developer.TCheckbutton", background=[("active", COLORS["bg"])], foreground=[("selected", COLORS["accent"]), ("active", COLORS["text"])])
        style.configure("Treeview", background=COLORS["panel_alt"], foreground=COLORS["text"], fieldbackground=COLORS["panel_alt"], borderwidth=0, rowheight=28, font=(font, 9))
        style.configure("Treeview.Heading", background="#101820", foreground=COLORS["muted"], relief="flat", font=(font, 9, "bold"))
        self.root.option_add("*TCombobox*Listbox.background", "#0d151c")
        self.root.option_add("*TCombobox*Listbox.foreground", COLORS["text"])
        self.root.option_add("*TCombobox*Listbox.selectBackground", COLORS["border"])

    @staticmethod
    def _panel(parent: tk.Misc, **grid_options: object) -> ttk.Frame:
        """공통 배경과 여백을 가진 카드형 패널을 만들어 즉시 배치한다."""
        frame = ttk.Frame(parent, style="Panel.TFrame", padding=16)
        frame.grid(**grid_options)
        return frame

    @staticmethod
    def _field_label(parent: tk.Misc, text: str, row: int, column: int, columnspan: int = 1) -> None:
        """입력 필드 위의 작은 설명 라벨을 지정한 그리드 위치에 배치한다."""
        ttk.Label(parent, text=text, style="Muted.TLabel").grid(row=row, column=column, columnspan=columnspan, sticky="w", pady=(7, 3))

    def _sync_left_scroll_region(self, _event: object | None = None) -> None:
        """입력 카드 내용 높이가 바뀔 때 스크롤 가능한 전체 영역을 다시 계산한다."""
        if hasattr(self, "left_canvas") and self.left_canvas.winfo_exists():
            self.left_canvas.configure(scrollregion=self.left_canvas.bbox("all"))

    def _resize_left_scroll_content(self, event: tk.Event) -> None:
        """창 너비가 바뀌어도 입력 카드 내부 프레임이 캔버스 폭을 정확히 채우게 한다."""
        if hasattr(self, "left_canvas") and self.left_canvas.winfo_exists():
            self.left_canvas.itemconfigure(self.left_canvas_window, width=max(1, event.width))

    def _enable_left_mousewheel(self, _event: object | None = None) -> None:
        """포인터가 입력 카드 위에 있을 때 휠을 해당 세로 스크롤에 연결한다."""
        self.root.bind_all("<MouseWheel>", self._scroll_left_panel)

    def _disable_left_mousewheel(self, _event: object | None = None) -> None:
        """포인터가 입력 카드를 벗어나면 다른 화면의 휠 동작을 방해하지 않게 연결을 푼다."""
        self.root.unbind_all("<MouseWheel>")

    def _scroll_left_panel(self, event: tk.Event) -> None:
        """Windows 마우스 휠 회전량을 입력 카드의 세로 이동 단위로 변환한다."""
        if hasattr(self, "left_canvas") and self.left_canvas.winfo_exists():
            self.left_canvas.yview_scroll(int(-event.delta / 120), "units")

    def _build_ui(self) -> None:
        """입력·결과·개발자·변경 기록과 하단 상태를 현재 언어로 구성한다."""
        self.recipe_texts.clear()
        self.debug_nodes.clear()
        self.language_var.set(LANGUAGE_LABELS[self.language])
        self.device_var.set(device_label(self.device_id, self.language))
        self.pickup_var.set(choice_label("pickup", self.pickup_code, self.language))
        self.mix_var.set(choice_label("mix", self.mix_code, self.language))
        self.output_var.set(choice_label("output", self.output_code, self.language))
        self.compute_var.set(choice_label("compute", self.compute_backend_code, self.language))
        self.input_method_var.set(_input_method_label(self.input_method_code, self.language))

        shell = ttk.Frame(self.root, padding=(22, 18, 22, 14))
        shell.pack(fill="both", expand=True)
        shell.columnconfigure(0, weight=0, minsize=420)
        shell.columnconfigure(1, weight=1)
        shell.rowconfigure(1, weight=1)

        header = ttk.Frame(shell)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 13))
        header.columnconfigure(0, weight=1)
        brand = ttk.Frame(header)
        brand.grid(row=0, column=0, sticky="w")
        ttk.Label(brand, text=tr("app.unofficial", self.language), style="Accent.TLabel").pack(anchor="w")
        ttk.Label(brand, text=APP_NAME, style="Title.TLabel").pack(anchor="w")
        ttk.Label(brand, text=tr("app.subtitle", self.language), foreground=COLORS["muted"]).pack(anchor="w", pady=(1, 0))

        tools = ttk.Frame(header)
        tools.grid(row=0, column=1, sticky="e")
        ttk.Label(tools, text=tr("ui.language", self.language), foreground=COLORS["muted"]).grid(row=0, column=0, sticky="e", padx=(0, 6))
        self.language_combo = ttk.Combobox(tools, textvariable=self.language_var, values=tuple(LANGUAGE_LABELS.values()), width=12, state="readonly")
        self.language_combo.grid(row=0, column=1, sticky="e")
        self.language_combo.bind("<<ComboboxSelected>>", self._change_language)
        ttk.Label(tools, text=tr("ui.device", self.language), foreground=COLORS["muted"]).grid(row=1, column=0, sticky="e", padx=(0, 6), pady=(6, 0))
        device_values = tuple(device_label(item["id"], self.language) for item in DEVICE_PROFILES)
        self.device_combo = ttk.Combobox(tools, textvariable=self.device_var, values=device_values, width=39, state="readonly")
        self.device_combo.grid(row=1, column=1, sticky="e", pady=(6, 0))
        self.device_combo.bind("<<ComboboxSelected>>", self._change_device)
        ttk.Checkbutton(tools, text=tr("ui.developer", self.language), variable=self.developer_var, command=self._toggle_developer_mode, style="Developer.TCheckbutton").grid(row=2, column=1, sticky="e", pady=(5, 0))

        left_shell = ttk.Frame(shell, style="Panel.TFrame")
        left_shell.grid(row=1, column=0, sticky="nsew", padx=(0, 13))
        left_shell.rowconfigure(0, weight=1)
        left_shell.columnconfigure(0, weight=1)
        self.left_canvas = tk.Canvas(left_shell, bg=COLORS["panel"], highlightthickness=0, borderwidth=0, width=404)
        self.left_canvas.grid(row=0, column=0, sticky="nsew")
        left_scroll = ttk.Scrollbar(left_shell, orient="vertical", command=self.left_canvas.yview)
        left_scroll.grid(row=0, column=1, sticky="ns")
        self.left_canvas.configure(yscrollcommand=left_scroll.set)
        left = ttk.Frame(self.left_canvas, style="Panel.TFrame", padding=16)
        self.left_canvas_window = self.left_canvas.create_window((0, 0), window=left, anchor="nw")
        left.bind("<Configure>", self._sync_left_scroll_region)
        self.left_canvas.bind("<Configure>", self._resize_left_scroll_content)
        self.left_canvas.bind("<Enter>", self._enable_left_mousewheel)
        self.left_canvas.bind("<Leave>", self._disable_left_mousewheel)
        left.columnconfigure(0, weight=1)
        ttk.Label(left, text=tr("ui.source_section", self.language), style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        self.device_description_var = tk.StringVar(value=device_description(self.device_id, self.language))
        ttk.Label(left, textvariable=self.device_description_var, style="Muted.TLabel", wraplength=380).grid(row=1, column=0, sticky="w", pady=(2, 4))

        self._field_label(left, tr("ui.input_method", self.language), 2, 0)
        self.input_combo = ttk.Combobox(left, textvariable=self.input_method_var, values=tuple(_input_method_label(code, self.language) for code in INPUT_METHODS), state="readonly")
        self.input_combo.grid(row=3, column=0, sticky="ew")
        self.input_combo.bind("<<ComboboxSelected>>", self._change_input_method)

        file_row = ttk.Frame(left, style="Panel.TFrame")
        file_row.grid(row=4, column=0, sticky="ew", pady=(6, 0))
        file_row.columnconfigure(0, weight=1)
        self.file_entry = ttk.Entry(file_row, textvariable=self.file_var)
        self.file_entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.choose_file_button = ttk.Button(file_row, text=tr("ui.choose_file", self.language), command=self._choose_audio)
        self.choose_file_button.grid(row=0, column=1)

        recording = ttk.Frame(left, style="Panel.TFrame")
        recording.grid(row=5, column=0, sticky="ew")
        recording.columnconfigure(0, weight=1)
        self._field_label(recording, tr("ui.record_device", self.language), 0, 0, 2)
        self.capture_combo = ttk.Combobox(recording, textvariable=self.capture_var, state="readonly")
        self.capture_combo.grid(row=1, column=0, sticky="ew", padx=(0, 6))
        self.capture_combo.bind("<<ComboboxSelected>>", self._capture_device_changed)
        self.refresh_devices_button = ttk.Button(recording, text=tr("ui.refresh_devices", self.language), command=self._refresh_capture_devices)
        self.refresh_devices_button.grid(row=1, column=1)
        self._field_label(recording, tr("ui.record_limit", self.language), 2, 0)
        record_controls = ttk.Frame(recording, style="Panel.TFrame")
        record_controls.grid(row=3, column=0, columnspan=2, sticky="ew")
        record_controls.columnconfigure(1, weight=1)
        self.record_limit_entry = ttk.Entry(record_controls, textvariable=self.record_limit_var, width=9)
        self.record_limit_entry.grid(row=0, column=0, padx=(0, 6))
        self.record_button = ttk.Button(record_controls, text=tr("ui.start_record", self.language), command=self._toggle_recording)
        self.record_button.grid(row=0, column=1, sticky="ew")
        self.record_notice = ttk.Label(recording, text=tr("ui.record_notice", self.language), style="Muted.TLabel", wraplength=370)
        self.record_notice.grid(row=4, column=0, columnspan=2, sticky="w", pady=(5, 0))
        self.record_only_widgets = [self.capture_combo, self.refresh_devices_button, self.record_limit_entry, self.record_button]

        self._field_label(left, tr("ui.youtube_reference", self.language), 6, 0)
        url_row = ttk.Frame(left, style="Panel.TFrame")
        url_row.grid(row=7, column=0, sticky="ew")
        url_row.columnconfigure(0, weight=1)
        ttk.Entry(url_row, textvariable=self.url_var).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(url_row, text=tr("ui.open_browser", self.language), command=self._open_reference).grid(row=0, column=1)

        segment = ttk.Frame(left, style="Panel.TFrame")
        segment.grid(row=8, column=0, sticky="ew")
        segment.columnconfigure((0, 1), weight=1)
        self._field_label(segment, tr("ui.start_seconds", self.language), 0, 0)
        self._field_label(segment, tr("ui.end_seconds", self.language), 0, 1)
        self.start_entry = ttk.Entry(segment, textvariable=self.start_var, width=12)
        self.start_entry.grid(row=1, column=0, sticky="ew", padx=(0, 4))
        self.end_entry = ttk.Entry(segment, textvariable=self.end_var, width=12)
        self.end_entry.grid(row=1, column=1, sticky="ew", padx=(4, 0))

        ttk.Label(left, text=tr("ui.tone_section", self.language), style="CardTitle.TLabel").grid(row=9, column=0, sticky="w", pady=(10, 0))
        options = ttk.Frame(left, style="Panel.TFrame")
        options.grid(row=10, column=0, sticky="ew")
        options.columnconfigure((0, 1), weight=1)
        self._field_label(options, tr("ui.pickup", self.language), 0, 0)
        self._field_label(options, tr("ui.mix", self.language), 0, 1)
        self.pickup_combo = ttk.Combobox(options, textvariable=self.pickup_var, values=choice_values("pickup", self.language), state="readonly")
        self.pickup_combo.grid(row=1, column=0, sticky="ew", padx=(0, 4))
        self.mix_combo = ttk.Combobox(options, textvariable=self.mix_var, values=choice_values("mix", self.language), state="readonly")
        self.mix_combo.grid(row=1, column=1, sticky="ew", padx=(4, 0))
        self._field_label(options, tr("ui.output", self.language), 2, 0, 2)
        self.output_combo = ttk.Combobox(options, textvariable=self.output_var, values=choice_values("output", self.language), state="readonly")
        self.output_combo.grid(row=3, column=0, columnspan=2, sticky="ew")

        # 입력 옵션을 스크롤해도 분석 버튼·진행률·현재 단계는 항상 보존한다.
        analyze_area = ttk.Frame(left_shell, style="Panel.TFrame", padding=(16, 10, 16, 12))
        analyze_area.grid(row=1, column=0, columnspan=2, sticky="ew")
        analyze_area.columnconfigure(0, weight=1)
        self.analyze_button = ttk.Button(analyze_area, text=tr("ui.analyze", self.language), style="Accent.TButton", command=self._start_analysis)
        self.analyze_button.grid(row=0, column=0, sticky="ew")
        self.cancel_button = ttk.Button(analyze_area, text=tr("ui.cancel_analysis", self.language), style="Danger.TButton", command=self._cancel_analysis, state="disabled")
        self.cancel_button.grid(row=0, column=1, padx=(6, 0))
        self.progress_var = tk.DoubleVar(value=self.analysis_progress_percent)
        self.progress = ttk.Progressbar(analyze_area, variable=self.progress_var, maximum=100)
        self.progress.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 4))
        self.progress_detail_var = tk.StringVar()
        ttk.Label(analyze_area, textvariable=self.progress_detail_var, style="Panel.TLabel", wraplength=375).grid(row=2, column=0, columnspan=2, sticky="w", pady=(0, 4))
        self._refresh_analysis_progress()
        self.status_var = tk.StringVar(value=tr("status.choose_file", self.language))
        ttk.Label(analyze_area, textvariable=self.status_var, style="Muted.TLabel", wraplength=375).grid(row=3, column=0, columnspan=2, sticky="w")

        note = tk.Label(left, text=tr("ui.tip", self.language), bg="#0d171f", fg=COLORS["muted"], justify="left", anchor="w", wraplength=375, padx=10, pady=8, font=(self.ui_font, 8))
        note.grid(row=12, column=0, sticky="ew", pady=(9, 0))

        right = self._panel(shell, row=1, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(2, weight=1)
        top = ttk.Frame(right, style="Panel.TFrame")
        top.grid(row=0, column=0, sticky="ew", pady=(0, 9))
        top.columnconfigure(0, weight=1)
        self.result_title_var = tk.StringVar(value=tr("ui.result", self.language))
        ttk.Label(top, textvariable=self.result_title_var, style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        self.export_json_button = ttk.Button(top, text=tr("ui.save_json", self.language), command=self._export_json, state="disabled")
        self.export_json_button.grid(row=0, column=1, padx=(6, 0))
        self.export_html_button = ttk.Button(top, text=tr("ui.html_report", self.language), command=self._export_html, state="disabled")
        self.export_html_button.grid(row=0, column=2, padx=(6, 0))
        self.copy_button = ttk.Button(top, text=tr("ui.copy_recipe", self.language), command=self._copy_recipe, state="disabled")
        self.copy_button.grid(row=0, column=3, padx=(6, 0))
        self.summary_var = tk.StringVar(value=tr("ui.empty_summary", self.language))
        ttk.Label(right, textvariable=self.summary_var, style="Muted.TLabel", wraplength=780).grid(row=1, column=0, sticky="ew", pady=(0, 9))

        self.notebook = ttk.Notebook(right)
        self.notebook.grid(row=2, column=0, sticky="nsew")
        self.notebook.bind("<<NotebookTabChanged>>", self._update_copy_availability)
        for rank in range(1, 4):
            tab = ttk.Frame(self.notebook, style="Alt.TFrame", padding=4)
            self.notebook.add(tab, text=tr("ui.recipe_tab", self.language, rank=rank))
            tab.rowconfigure(0, weight=1)
            tab.columnconfigure(0, weight=1)
            text = ScrolledText(tab, wrap="word", bg=COLORS["panel_alt"], fg=COLORS["text"], insertbackground=COLORS["text"], selectbackground="#315369", relief="flat", padx=17, pady=15, font=(self.ui_font, 10), state="disabled")
            text.grid(row=0, column=0, sticky="nsew")
            text.tag_configure("heading", font=(self.ui_font, 17, "bold"), foreground=COLORS["accent"], spacing3=6)
            text.tag_configure("subheading", font=(self.ui_font, 10), foreground=COLORS["muted"], spacing3=12)
            text.tag_configure("route", font=(self.ui_font, 10, "bold"), foreground=COLORS["warning"], spacing1=2, spacing3=8)
            text.tag_configure("block", font=(self.ui_font, 11, "bold"), foreground=COLORS["blue"], spacing1=10, spacing3=4)
            text.tag_configure("parameter", foreground=COLORS["text"], lmargin1=18, lmargin2=18)
            text.tag_configure("reason", foreground=COLORS["muted"], lmargin1=18, lmargin2=18, spacing3=4)
            text.tag_configure("warning", foreground=COLORS["warning"], spacing1=8)
            self.recipe_texts.append(text)

        self.voicing_tab = ttk.Frame(self.notebook, style="Alt.TFrame", padding=4)
        self.notebook.add(self.voicing_tab, text=tr("ui.voicing_tab", self.language))
        self.voicing_tab.rowconfigure(0, weight=1)
        self.voicing_tab.columnconfigure(0, weight=1)
        self.voicing_text = ScrolledText(self.voicing_tab, wrap="word", bg=COLORS["panel_alt"], fg=COLORS["text"], selectbackground="#315369", relief="flat", padx=18, pady=16, font=(self.ui_font, 10), state="disabled")
        self.voicing_text.grid(row=0, column=0, sticky="nsew")
        self.voicing_text.tag_configure("heading", font=(self.ui_font, 16, "bold"), foreground=COLORS["accent"], spacing3=7)
        self.voicing_text.tag_configure("intro", foreground=COLORS["muted"], spacing3=12)
        self.voicing_text.tag_configure("event", font=(self.ui_font, 12, "bold"), foreground=COLORS["blue"], spacing1=10, spacing3=3)
        self.voicing_text.tag_configure("detail", foreground=COLORS["text"], lmargin1=18, lmargin2=18)
        self.voicing_text.tag_configure("warning", foreground=COLORS["warning"], spacing1=10)

        self._build_spectrum_tab()
        self._build_reference_compare_tab()

        self.diag_tab = ttk.Frame(self.notebook, style="Alt.TFrame", padding=12)
        self.notebook.add(self.diag_tab, text=tr("ui.diagnostics", self.language))
        self.diag_tab.rowconfigure(2, weight=1)
        self.diag_tab.columnconfigure(0, weight=1)

        compute_controls = ttk.Frame(self.diag_tab, style="Alt.TFrame")
        compute_controls.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        compute_controls.columnconfigure(1, weight=1)
        ttk.Label(compute_controls, text=tr("ui.compute_backend", self.language), background=COLORS["panel_alt"], foreground=COLORS["text"], font=(self.ui_font, 10, "bold")).grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.compute_combo = ttk.Combobox(compute_controls, textvariable=self.compute_var, values=choice_values("compute", self.language), state="readonly", width=28)
        self.compute_combo.grid(row=0, column=1, sticky="w")
        self.compute_combo.bind("<<ComboboxSelected>>", self._change_compute_backend)
        self.hardware_refresh_button = ttk.Button(compute_controls, text=tr("ui.recheck_hardware", self.language), command=self._start_hardware_probe)
        self.hardware_refresh_button.grid(row=0, column=2, sticky="e", padx=(8, 0))
        ttk.Label(self.diag_tab, text=tr("ui.compute_hint", self.language), background=COLORS["panel_alt"], foreground=COLORS["muted"], font=(self.ui_font, 9), wraplength=700, justify="left").grid(row=1, column=0, sticky="ew", pady=(0, 8))

        diagnostics_table = ttk.Frame(self.diag_tab, style="Alt.TFrame")
        diagnostics_table.grid(row=2, column=0, sticky="nsew")
        diagnostics_table.rowconfigure(0, weight=1)
        diagnostics_table.columnconfigure(0, weight=1)
        self.diag_tree = ttk.Treeview(diagnostics_table, columns=("metric", "value"), show="headings", selectmode="none")
        self.diag_tree.heading("metric", text=tr("ui.metric", self.language))
        self.diag_tree.heading("value", text=tr("ui.value", self.language))
        self.diag_tree.column("metric", width=235, minwidth=180, stretch=False, anchor="w")
        self.diag_tree.column("value", width=360, minwidth=220, stretch=True, anchor="w")
        self.diag_tree.grid(row=0, column=0, sticky="nsew")
        diag_scroll = ttk.Scrollbar(diagnostics_table, orient="vertical", command=self.diag_tree.yview)
        diag_scroll.grid(row=0, column=1, sticky="ns")
        self.diag_tree.configure(yscrollcommand=diag_scroll.set)

        self._build_debug_tab()
        self._build_changelog_tab()
        self.notebook.hide(self.debug_tab)
        self.notebook.hide(self.changelog_tab)
        self._update_copy_availability()

        footer = ttk.Frame(shell)
        footer.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        footer.columnconfigure(0, weight=1)
        ttk.Label(footer, text=tr("ui.footer", self.language), foreground="#6f818d", font=(self.ui_font, 8)).grid(row=0, column=0, sticky="w")
        ttk.Label(footer, text=f"v{APP_VERSION} · {BUILD_DATE}", foreground="#6f818d", font=("Consolas", 8)).grid(row=0, column=1, sticky="e")

        self._refresh_capture_devices(silent=True)
        self._change_input_method()
        self._populate_diagnostics()
        self._update_analysis_availability()
        if self.result:
            self._show_result(self.result, reset_notebook=False)
        if self.last_spectrum_frame is not None:
            self._apply_spectrum_frame(self.last_spectrum_frame, update_comparison=False)

    def _build_debug_tab(self) -> None:
        """처리 순서도, 클릭형 실제 소스, 런타임 로그와 디버그 번들 버튼을 만든다."""
        self.debug_tab = ttk.Frame(self.notebook, style="Alt.TFrame", padding=9)
        self.notebook.add(self.debug_tab, text=tr("ui.debug_tab", self.language))
        self.debug_tab.columnconfigure(1, weight=1)
        self.debug_tab.rowconfigure(0, weight=1)
        diagram_panel = ttk.Frame(self.debug_tab, style="Panel.TFrame", padding=(9, 10))
        diagram_panel.grid(row=0, column=0, sticky="nsw", padx=(0, 9))
        ttk.Label(diagram_panel, text=tr("ui.pipeline", self.language), style="CardTitle.TLabel").pack(anchor="w", padx=4)
        ttk.Label(diagram_panel, text=tr("ui.click_block", self.language), style="Muted.TLabel", wraplength=248).pack(anchor="w", padx=4, pady=(2, 6))
        self.debug_canvas = tk.Canvas(diagram_panel, width=270, height=500, bg=COLORS["panel"], highlightthickness=0, bd=0)
        self.debug_canvas.pack(fill="y", expand=False)
        self._draw_debug_diagram()

        detail = ttk.Frame(self.debug_tab, style="Alt.TFrame")
        detail.grid(row=0, column=1, sticky="nsew")
        detail.columnconfigure(0, weight=1)
        detail.rowconfigure(2, weight=3)
        detail.rowconfigure(4, weight=1)
        self.debug_title_var = tk.StringVar()
        self.debug_description_var = tk.StringVar()
        ttk.Label(detail, textvariable=self.debug_title_var, background=COLORS["panel_alt"], foreground=COLORS["accent"], font=(self.ui_font, 14, "bold")).grid(row=0, column=0, sticky="ew", padx=8, pady=(3, 2))
        ttk.Label(detail, textvariable=self.debug_description_var, background=COLORS["panel_alt"], foreground=COLORS["muted"], font=(self.ui_font, 9), wraplength=640, justify="left").grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 6))
        self.debug_code = ScrolledText(detail, wrap="none", bg="#091016", fg="#d9e5eb", insertbackground=COLORS["text"], selectbackground="#315369", relief="flat", padx=11, pady=9, font=("Consolas", 9), state="disabled")
        self.debug_code.grid(row=2, column=0, sticky="nsew", padx=8)
        self.debug_code.tag_configure("comment", foreground="#67c587")
        self.debug_code.tag_configure("docstring", foreground="#d9a66f")
        self.debug_code.tag_configure("line", foreground="#687985")
        log_header = ttk.Frame(detail, style="Alt.TFrame")
        log_header.grid(row=3, column=0, sticky="ew", padx=8, pady=(8, 3))
        log_header.columnconfigure(0, weight=1)
        ttk.Label(log_header, text=tr("ui.runtime_log", self.language), background=COLORS["panel_alt"], foreground=COLORS["muted"], font=(self.ui_font, 9, "bold")).grid(row=0, column=0, sticky="w")
        self.debug_bundle_button = ttk.Button(log_header, text=tr("ui.debug_bundle", self.language), command=self._export_debug_bundle)
        self.debug_bundle_button.grid(row=0, column=1, sticky="e")
        self.debug_log = ScrolledText(detail, height=6, wrap="word", bg="#0d151c", fg=COLORS["muted"], relief="flat", padx=10, pady=8, font=("Consolas", 8), state="disabled")
        self.debug_log.grid(row=4, column=0, sticky="nsew", padx=8, pady=(0, 4))
        self._select_debug_block(self.active_debug_block)
        for line in self.debug_log_lines[-300:]:
            self.debug_log.configure(state="normal")
            self.debug_log.insert("end", line + "\n")
            self.debug_log.configure(state="disabled")
        self._append_debug_log(f"v{APP_VERSION} · {BUILD_DATE} · UI ready")

    def _build_changelog_tab(self) -> None:
        """패치 버전·변경사항·알려진 제한을 현재 언어로 읽는 탭을 만든다."""
        self.changelog_tab = ttk.Frame(self.notebook, style="Alt.TFrame", padding=12)
        self.notebook.add(self.changelog_tab, text=tr("ui.changelog_tab", self.language))
        self.changelog_tab.columnconfigure(0, weight=1)
        self.changelog_tab.rowconfigure(0, weight=1)
        self.changelog_text = ScrolledText(self.changelog_tab, wrap="word", bg=COLORS["panel_alt"], fg=COLORS["text"], relief="flat", padx=22, pady=18, font=(self.ui_font, 10))
        self.changelog_text.grid(row=0, column=0, sticky="nsew")
        self.changelog_text.insert("1.0", changelog_as_text(CHANGELOG, self.language))
        self.changelog_text.configure(state="disabled")

    def _build_spectrum_tab(self) -> None:
        """선택한 입력 장치의 파형·주파수·레벨을 보여주는 실시간 탭을 만든다."""
        self.spectrum_tab = ttk.Frame(self.notebook, style="Alt.TFrame", padding=12)
        self.notebook.add(self.spectrum_tab, text=tr("ui.spectrum_tab", self.language))
        self.spectrum_tab.columnconfigure(0, weight=1)
        self.spectrum_tab.rowconfigure(4, weight=2)
        self.spectrum_tab.rowconfigure(6, weight=3)

        controls = ttk.Frame(self.spectrum_tab, style="Alt.TFrame")
        controls.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        controls.columnconfigure(1, weight=1)
        ttk.Label(
            controls,
            text=tr("ui.spectrum_device", self.language),
            background=COLORS["panel_alt"],
            foreground=COLORS["text"],
            font=(self.ui_font, 10, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=(0, 9))
        self.spectrum_capture_combo = ttk.Combobox(controls, textvariable=self.capture_var, state="readonly")
        self.spectrum_capture_combo.grid(row=0, column=1, sticky="ew")
        self.spectrum_capture_combo.bind("<<ComboboxSelected>>", self._capture_device_changed)
        self.spectrum_refresh_button = ttk.Button(
            controls,
            text=tr("ui.refresh_devices", self.language),
            command=self._refresh_capture_devices,
        )
        self.spectrum_refresh_button.grid(row=0, column=2, padx=(7, 0))
        self.spectrum_button = ttk.Button(
            controls,
            text=tr("ui.start_spectrum", self.language),
            style="Accent.TButton",
            command=self._toggle_spectrum_monitor,
        )
        self.spectrum_button.grid(row=0, column=3, padx=(7, 0))

        self.spectrum_status_var = tk.StringVar(value=tr("status.spectrum_ready", self.language))
        ttk.Label(
            self.spectrum_tab,
            textvariable=self.spectrum_status_var,
            background=COLORS["panel_alt"],
            foreground=COLORS["muted"],
            font=(self.ui_font, 9),
            wraplength=720,
            justify="left",
        ).grid(row=1, column=0, sticky="ew", pady=(0, 8))

        metrics = ttk.Frame(self.spectrum_tab, style="Alt.TFrame")
        metrics.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        metrics.columnconfigure((0, 1, 2), weight=1)
        self.spectrum_rms_var = tk.StringVar(value="-120.0 dBFS")
        self.spectrum_peak_var = tk.StringVar(value="-120.0 dBFS")
        self.spectrum_centroid_var = tk.StringVar(value="—")
        metric_items = (
            ("feature.rms", self.spectrum_rms_var),
            ("feature.peak", self.spectrum_peak_var),
            ("feature.centroid", self.spectrum_centroid_var),
        )
        for column, (label_key, variable) in enumerate(metric_items):
            card = tk.Frame(metrics, bg="#101a22", highlightbackground=COLORS["border"], highlightthickness=1)
            card.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 4, 0 if column == 2 else 4))
            tk.Label(card, text=tr(label_key, self.language), bg="#101a22", fg=COLORS["muted"], font=(self.ui_font, 8)).pack(anchor="w", padx=10, pady=(7, 0))
            tk.Label(card, textvariable=variable, bg="#101a22", fg=COLORS["accent"], font=("Consolas", 13, "bold")).pack(anchor="w", padx=10, pady=(1, 7))

        ttk.Label(
            self.spectrum_tab,
            text=tr("ui.waveform", self.language),
            background=COLORS["panel_alt"],
            foreground=COLORS["text"],
            font=(self.ui_font, 9, "bold"),
        ).grid(row=3, column=0, sticky="w")
        self.waveform_canvas = tk.Canvas(self.spectrum_tab, height=130, bg="#081017", highlightbackground=COLORS["border"], highlightthickness=1, bd=0)
        self.waveform_canvas.grid(row=4, column=0, sticky="nsew", pady=(3, 8))
        self.waveform_canvas.bind("<Configure>", self._spectrum_canvas_resized)

        ttk.Label(
            self.spectrum_tab,
            text=tr("ui.frequency_spectrum", self.language),
            background=COLORS["panel_alt"],
            foreground=COLORS["text"],
            font=(self.ui_font, 9, "bold"),
        ).grid(row=5, column=0, sticky="w")
        self.spectrum_canvas = tk.Canvas(self.spectrum_tab, height=250, bg="#081017", highlightbackground=COLORS["border"], highlightthickness=1, bd=0)
        self.spectrum_canvas.grid(row=6, column=0, sticky="nsew", pady=(3, 0))
        self.spectrum_canvas.bind("<Configure>", self._spectrum_canvas_resized)

    def _build_reference_compare_tab(self) -> None:
        """분석한 기준 스펙트럼과 실시간 입력의 레벨 정규화 차이 탭을 만든다."""
        self.reference_compare_tab = ttk.Frame(self.notebook, style="Alt.TFrame", padding=12)
        self.notebook.add(self.reference_compare_tab, text=tr("ui.reference_compare_tab", self.language))
        self.reference_compare_tab.columnconfigure(0, weight=1)
        self.reference_compare_tab.rowconfigure(3, weight=0)
        self.reference_compare_tab.rowconfigure(6, weight=1)

        controls = ttk.Frame(self.reference_compare_tab, style="Alt.TFrame")
        controls.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        controls.columnconfigure(1, weight=1)
        ttk.Label(
            controls,
            text=tr("ui.spectrum_device", self.language),
            background=COLORS["panel_alt"],
            foreground=COLORS["text"],
            font=(self.ui_font, 10, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=(0, 9))
        self.reference_capture_combo = ttk.Combobox(controls, textvariable=self.capture_var, state="readonly")
        self.reference_capture_combo.grid(row=0, column=1, sticky="ew")
        self.reference_capture_combo.bind("<<ComboboxSelected>>", self._capture_device_changed)
        self.reference_refresh_button = ttk.Button(
            controls,
            text=tr("ui.refresh_devices", self.language),
            command=self._refresh_capture_devices,
        )
        self.reference_refresh_button.grid(row=0, column=2, padx=(7, 0))
        self.reference_compare_button = ttk.Button(
            controls,
            text=tr("ui.start_reference_compare", self.language),
            style="Accent.TButton",
            command=lambda: self._toggle_spectrum_monitor(require_reference=True),
        )
        self.reference_compare_button.grid(row=0, column=3, padx=(7, 0))

        self.reference_status_var = tk.StringVar(value=tr("status.reference_missing", self.language))
        ttk.Label(
            self.reference_compare_tab,
            textvariable=self.reference_status_var,
            background=COLORS["panel_alt"],
            foreground=COLORS["muted"],
            font=(self.ui_font, 9),
            wraplength=760,
            justify="left",
        ).grid(row=1, column=0, sticky="ew", pady=(0, 5))

        self.reference_file_var = tk.StringVar(value="—")
        reference_row = ttk.Frame(self.reference_compare_tab, style="Alt.TFrame")
        reference_row.grid(row=2, column=0, sticky="ew", pady=(0, 7))
        ttk.Label(
            reference_row,
            text=f"{tr('ui.reference_file', self.language)}:",
            background=COLORS["panel_alt"],
            foreground=COLORS["text"],
            font=(self.ui_font, 9, "bold"),
        ).pack(side="left")
        ttk.Label(
            reference_row,
            textvariable=self.reference_file_var,
            background=COLORS["panel_alt"],
            foreground=COLORS["accent"],
            font=(self.ui_font, 9),
        ).pack(side="left", padx=(6, 0))

        table_frame = ttk.Frame(self.reference_compare_tab, style="Alt.TFrame")
        table_frame.grid(row=3, column=0, sticky="ew", pady=(0, 6))
        table_frame.columnconfigure(0, weight=1)
        self.reference_tree = ttk.Treeview(
            table_frame,
            columns=("band", "reference", "current", "delta"),
            show="headings",
            height=6,
            selectmode="none",
        )
        headings = (
            ("band", tr("ui.compare_band", self.language), 230, "w"),
            ("reference", tr("ui.compare_reference", self.language), 120, "center"),
            ("current", tr("ui.compare_current", self.language), 120, "center"),
            ("delta", tr("ui.compare_delta", self.language), 150, "center"),
        )
        for column, label, width, anchor in headings:
            self.reference_tree.heading(column, text=label)
            self.reference_tree.column(column, width=width, minwidth=90, stretch=column == "band", anchor=anchor)
        self.reference_tree.tag_configure("positive", foreground=COLORS["blue"])
        self.reference_tree.tag_configure("negative", foreground=COLORS["warning"])
        self.reference_tree.grid(row=0, column=0, sticky="ew")

        ttk.Label(
            self.reference_compare_tab,
            text=tr("ui.reference_compare_note", self.language),
            background=COLORS["panel_alt"],
            foreground=COLORS["muted"],
            font=(self.ui_font, 8),
            wraplength=760,
            justify="left",
        ).grid(row=4, column=0, sticky="ew", pady=(0, 6))
        ttk.Label(
            self.reference_compare_tab,
            text=tr("ui.reference_difference", self.language),
            background=COLORS["panel_alt"],
            foreground=COLORS["text"],
            font=(self.ui_font, 9, "bold"),
        ).grid(row=5, column=0, sticky="w")
        self.reference_canvas = tk.Canvas(
            self.reference_compare_tab,
            height=250,
            bg="#081017",
            highlightbackground=COLORS["border"],
            highlightthickness=1,
            bd=0,
        )
        self.reference_canvas.grid(row=6, column=0, sticky="nsew", pady=(3, 0))
        self.reference_canvas.bind("<Configure>", self._reference_canvas_resized)

    def _spectrum_is_running(self) -> bool:
        """실시간 스펙트럼 세션이 종료 이벤트 처리 전까지 활성인지 반환한다."""
        return self.spectrum_worker is not None

    @staticmethod
    def _spectrum_plot_x(frequency_hz: float, width: int) -> float:
        """20 Hz~20 kHz 로그 축의 주파수를 캔버스 가로 좌표로 바꾼다."""
        left = 46.0
        right = max(left + 1.0, float(width) - 11.0)
        frequency = min(20_000.0, max(20.0, float(frequency_hz)))
        ratio = math.log10(frequency / 20.0) / math.log10(20_000.0 / 20.0)
        return left + ratio * (right - left)

    @staticmethod
    def _spectrum_plot_y(level_dbfs: float, height: int) -> float:
        """-120~0 dBFS 레벨을 스펙트럼 캔버스 세로 좌표로 바꾼다."""
        top = 9.0
        bottom = max(top + 1.0, float(height) - 25.0)
        level = min(0.0, max(-120.0, float(level_dbfs)))
        return top + (-level / 120.0) * (bottom - top)

    def _spectrum_canvas_resized(self, _event: object | None = None) -> None:
        """스펙트럼 탭 크기가 바뀌면 축과 마지막 측정 프레임을 다시 그린다."""
        if self.closing:
            return
        self._draw_waveform_grid()
        self._draw_spectrum_grid()
        if self.last_spectrum_frame is not None:
            self._draw_waveform(self.last_spectrum_frame)
            self._draw_spectrum(self.last_spectrum_frame)

    def _draw_waveform_grid(self) -> None:
        """파형 캔버스에 기준 레벨과 시간 방향 보조선을 그린다."""
        if not hasattr(self, "waveform_canvas") or not self.waveform_canvas.winfo_exists():
            return
        canvas = self.waveform_canvas
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        canvas.delete("grid")
        if width < 70 or height < 45:
            return
        left, right = 37.0, float(width) - 9.0
        top, bottom = 8.0, float(height) - 15.0
        for level, label in ((1.0, "+1"), (0.0, "0"), (-1.0, "-1")):
            y = top + (1.0 - (level + 1.0) / 2.0) * (bottom - top)
            canvas.create_line(left, y, right, y, fill="#20303b", width=1, tags=("grid",))
            canvas.create_text(31, y, text=label, fill=COLORS["muted"], anchor="e", font=("Consolas", 7), tags=("grid",))
        for fraction in (0.25, 0.5, 0.75):
            x = left + fraction * (right - left)
            canvas.create_line(x, top, x, bottom, fill="#15232c", width=1, tags=("grid",))

    def _draw_spectrum_grid(self) -> None:
        """주파수 캔버스에 로그 주파수축과 dBFS 기준선을 그린다."""
        if not hasattr(self, "spectrum_canvas") or not self.spectrum_canvas.winfo_exists():
            return
        canvas = self.spectrum_canvas
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        canvas.delete("grid")
        if width < 100 or height < 70:
            return
        left, right = 46.0, float(width) - 11.0
        top, bottom = 9.0, float(height) - 25.0
        for level in (0, -24, -48, -72, -96, -120):
            y = self._spectrum_plot_y(float(level), height)
            canvas.create_line(left, y, right, y, fill="#20303b", width=1, tags=("grid",))
            canvas.create_text(40, y, text=str(level), fill=COLORS["muted"], anchor="e", font=("Consolas", 7), tags=("grid",))
        frequency_ticks = (
            (20, "20"),
            (50, "50"),
            (100, "100"),
            (200, "200"),
            (500, "500"),
            (1_000, "1k"),
            (2_000, "2k"),
            (5_000, "5k"),
            (10_000, "10k"),
            (20_000, "20k"),
        )
        for frequency, label in frequency_ticks:
            x = self._spectrum_plot_x(float(frequency), width)
            canvas.create_line(x, top, x, bottom, fill="#15232c", width=1, tags=("grid",))
            canvas.create_text(x, float(height) - 13.0, text=label, fill=COLORS["muted"], anchor="center", font=("Consolas", 7), tags=("grid",))
        canvas.create_text(left, 2, text="dBFS", fill=COLORS["muted"], anchor="nw", font=("Consolas", 7), tags=("grid",))

    def _draw_waveform(self, frame: SpectrumFrame) -> None:
        """최신 PCM 파형을 현재 캔버스 폭에 맞춰 줄여 그린다."""
        if not hasattr(self, "waveform_canvas") or not self.waveform_canvas.winfo_exists():
            return
        canvas = self.waveform_canvas
        canvas.delete("dynamic")
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        if width < 70 or height < 45:
            return
        values = np.asarray(frame.waveform, dtype=np.float64)
        if values.size < 2:
            return
        left, right = 37.0, float(width) - 9.0
        top, bottom = 8.0, float(height) - 15.0
        point_count = min(values.size, max(2, int(right - left)))
        indices = np.linspace(0, values.size - 1, point_count, dtype=np.int64)
        sampled = np.clip(values[indices], -1.0, 1.0)
        x_values = np.linspace(left, right, point_count)
        y_values = top + (1.0 - (sampled + 1.0) / 2.0) * (bottom - top)
        coordinates = np.column_stack((x_values, y_values)).reshape(-1).tolist()
        canvas.create_line(*coordinates, fill=COLORS["blue"], width=1.4, tags=("dynamic",))

    def _draw_spectrum(self, frame: SpectrumFrame) -> None:
        """평활화된 FFT 레벨과 스펙트럼 중심을 로그 주파수축에 그린다."""
        if not hasattr(self, "spectrum_canvas") or not self.spectrum_canvas.winfo_exists():
            return
        canvas = self.spectrum_canvas
        canvas.delete("dynamic")
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        if width < 100 or height < 70:
            return
        frequencies = np.asarray(frame.frequencies_hz, dtype=np.float64)
        levels = np.asarray(frame.magnitudes_dbfs, dtype=np.float64)
        mask = np.isfinite(frequencies) & np.isfinite(levels) & (frequencies >= 20.0) & (frequencies <= 20_000.0)
        if not np.any(mask):
            return
        frequencies = frequencies[mask]
        levels = np.clip(levels[mask], -120.0, 0.0)
        x_values = np.asarray([self._spectrum_plot_x(value, width) for value in frequencies], dtype=np.float64)
        y_values = np.asarray([self._spectrum_plot_y(value, height) for value in levels], dtype=np.float64)
        # 같은 화면 픽셀에 여러 FFT bin이 모이면 가장 강한 레벨을 남긴다.
        pixels = np.rint(x_values).astype(np.int64)
        unique_pixels, first_indices = np.unique(pixels, return_index=True)
        reduced_x = unique_pixels.astype(np.float64)
        reduced_y = np.minimum.reduceat(y_values, first_indices)
        coordinates = np.column_stack((reduced_x, reduced_y)).reshape(-1).tolist()
        if len(coordinates) >= 4:
            canvas.create_line(*coordinates, fill=COLORS["accent"], width=1.8, tags=("dynamic",))
        centroid = float(frame.spectral_centroid_hz)
        if 20.0 <= centroid <= 20_000.0:
            x = self._spectrum_plot_x(centroid, width)
            bottom = float(height) - 25.0
            canvas.create_line(x, 9, x, bottom, fill=COLORS["warning"], dash=(4, 4), tags=("dynamic",))
            canvas.create_text(
                min(float(width) - 8.0, x + 5.0),
                12,
                text=f"{centroid:.0f} Hz",
                fill=COLORS["warning"],
                anchor="nw",
                font=("Consolas", 8),
                tags=("dynamic",),
            )

    @staticmethod
    def _reference_plot_y(delta_db: float, height: int) -> float:
        """±18 dB 비교 차이를 캔버스 세로 좌표로 제한해 변환한다."""
        top = 10.0
        bottom = max(top + 1.0, float(height) - 25.0)
        delta = min(18.0, max(-18.0, float(delta_db)))
        return top + ((18.0 - delta) / 36.0) * (bottom - top)

    def _reference_canvas_resized(self, _event: object | None = None) -> None:
        """비교 탭 크기가 바뀌면 차이 축과 마지막 유효 곡선을 다시 그린다."""
        if self.closing:
            return
        self._draw_reference_grid()
        if self.last_reference_comparison is not None:
            self._draw_reference_difference(self.last_reference_comparison)

    def _draw_reference_grid(self) -> None:
        """레퍼런스 차이 캔버스에 로그 주파수축과 ±18 dB 기준선을 그린다."""
        if not hasattr(self, "reference_canvas") or not self.reference_canvas.winfo_exists():
            return
        canvas = self.reference_canvas
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        canvas.delete("grid")
        if width < 100 or height < 70:
            return
        left, right = 46.0, float(width) - 11.0
        top, bottom = 10.0, float(height) - 25.0
        for delta in (18, 12, 6, 0, -6, -12, -18):
            y = self._reference_plot_y(float(delta), height)
            color = "#385263" if delta == 0 else "#20303b"
            width_px = 2 if delta == 0 else 1
            canvas.create_line(left, y, right, y, fill=color, width=width_px, tags=("grid",))
            canvas.create_text(40, y, text=f"{delta:+d}", fill=COLORS["muted"], anchor="e", font=("Consolas", 7), tags=("grid",))
        for frequency, label in ((20, "20"), (50, "50"), (100, "100"), (200, "200"), (500, "500"), (1_000, "1k"), (2_000, "2k"), (5_000, "5k"), (10_000, "10k"), (20_000, "20k")):
            x = self._spectrum_plot_x(float(frequency), width)
            canvas.create_line(x, top, x, bottom, fill="#15232c", width=1, tags=("grid",))
            canvas.create_text(x, float(height) - 13.0, text=label, fill=COLORS["muted"], anchor="center", font=("Consolas", 7), tags=("grid",))
        canvas.create_text(left, 2, text="Δ dB", fill=COLORS["muted"], anchor="nw", font=("Consolas", 7), tags=("grid",))

    def _draw_reference_difference(self, comparison: dict) -> None:
        """현재−기준의 주파수별 정규화 dB 차이를 로그 축에 그린다."""
        if not hasattr(self, "reference_canvas") or not self.reference_canvas.winfo_exists():
            return
        canvas = self.reference_canvas
        canvas.delete("dynamic")
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        if width < 100 or height < 70:
            return
        frequencies = np.asarray(comparison.get("frequencies_hz", ()), dtype=np.float64)
        deltas = np.asarray(comparison.get("delta_db", ()), dtype=np.float64)
        if frequencies.ndim != 1 or deltas.shape != frequencies.shape:
            return
        mask = np.isfinite(frequencies) & np.isfinite(deltas) & (frequencies >= 20.0) & (frequencies <= 20_000.0)
        if not np.any(mask):
            return
        frequencies = frequencies[mask]
        deltas = np.clip(deltas[mask], -18.0, 18.0)
        x_values = np.asarray([self._spectrum_plot_x(value, width) for value in frequencies], dtype=np.float64)
        y_values = np.asarray([self._reference_plot_y(value, height) for value in deltas], dtype=np.float64)
        pixels = np.rint(x_values).astype(np.int64)
        unique_pixels, first_indices = np.unique(pixels, return_index=True)
        reduced_x = unique_pixels.astype(np.float64)
        counts = np.diff(np.append(first_indices, len(y_values)))
        reduced_y = np.add.reduceat(y_values, first_indices) / counts
        coordinates = np.column_stack((reduced_x, reduced_y)).reshape(-1).tolist()
        if len(coordinates) >= 4:
            canvas.create_line(*coordinates, fill=COLORS["accent"], width=1.8, tags=("dynamic",))

    @staticmethod
    def _format_frequency_range(low_hz: object, high_hz: object) -> str:
        """대역 경계를 Hz 또는 kHz가 섞인 짧은 화면 문자열로 바꾼다."""
        def compact(value: object) -> str:
            """한 주파수 값을 읽기 쉬운 Hz/kHz 숫자로 축약한다."""
            frequency = float(value)
            if frequency >= 1_000.0:
                return f"{frequency / 1_000.0:g}k"
            return f"{frequency:g}"

        return f"{compact(low_hz)}–{compact(high_hz)} Hz"

    @staticmethod
    def _reference_band_level(band: dict) -> float:
        """프로필 밴드의 버전 호환 레벨 키를 유한 실수로 읽는다."""
        value = band.get("reference_db", band.get("relative_db", band.get("level_db", 0.0)))
        level = float(value)
        return level if math.isfinite(level) else 0.0

    def _populate_reference_rows(self, comparison: dict | None = None) -> None:
        """기준 프로필 또는 최신 비교를 Reference·Current·Δ 여섯 행으로 표시한다."""
        if not hasattr(self, "reference_tree") or not self.reference_tree.winfo_exists():
            return
        self.reference_tree.delete(*self.reference_tree.get_children())
        profile = self.result.get("reference_spectrum") if self.result else None
        if not isinstance(profile, dict):
            return
        bands = comparison.get("bands", ()) if comparison else profile.get("bands", ())
        for band in bands:
            if not isinstance(band, dict):
                continue
            band_id = str(band.get("id", ""))
            band_name = tr(f"band.{band_id}", self.language)
            if band_name == f"band.{band_id}":
                band_name = str(band.get("name", band_id or "—"))
            try:
                frequency_range = self._format_frequency_range(band.get("low_hz", 0.0), band.get("high_hz", 0.0))
            except (TypeError, ValueError):
                frequency_range = "—"
            label = f"{band_name} · {frequency_range}"
            if not band.get("available", True):
                self.reference_tree.insert("", "end", values=(band_name, "—", "—", "—"))
                continue
            if comparison:
                reference_db = float(band.get("reference_db", 0.0))
                current_db = float(band.get("current_db", 0.0))
                delta_db = float(band.get("delta_db", current_db - reference_db))
                tag = "positive" if delta_db > 0.05 else "negative" if delta_db < -0.05 else ""
                values = (label, f"{reference_db:.1f} dB", f"{current_db:.1f} dB", f"{delta_db:+.1f} dB")
            else:
                reference_db = self._reference_band_level(band)
                tag = ""
                values = (label, f"{reference_db:.1f} dB", "—", "—")
            self.reference_tree.insert("", "end", values=values, tags=(tag,) if tag else ())

    def _refresh_reference_profile(self, reset_comparison: bool = False) -> None:
        """현재 분석 결과의 기준 파일·밴드·상태를 비교 탭에 반영한다."""
        if not hasattr(self, "reference_status_var"):
            return
        profile = self.result.get("reference_spectrum") if self.result else None
        if not isinstance(profile, dict):
            self.reference_file_var.set("—")
            self.reference_status_var.set(tr("status.reference_missing", self.language))
            self.last_reference_comparison = None
            self._populate_reference_rows()
            if hasattr(self, "reference_canvas"):
                self.reference_canvas.delete("dynamic")
            self._update_spectrum_availability()
            return
        file_name = str(self.result.get("source", {}).get("file_name", "—"))
        self.reference_file_var.set(file_name)
        if reset_comparison:
            self.last_reference_comparison = None
        if self._spectrum_is_running():
            self.reference_status_var.set(tr("status.reference_running", self.language, file=file_name, rate=21.5))
        elif self.last_reference_comparison is None:
            self.reference_status_var.set(tr("status.reference_ready", self.language, file=file_name))
        else:
            self.reference_status_var.set(tr("status.reference_stopped", self.language))
        self._populate_reference_rows(self.last_reference_comparison)
        self._draw_reference_grid()
        if self.last_reference_comparison is not None:
            self._draw_reference_difference(self.last_reference_comparison)
        elif hasattr(self, "reference_canvas"):
            self.reference_canvas.delete("dynamic")
        self._update_spectrum_availability()

    def _apply_spectrum_frame(self, frame: SpectrumFrame, update_comparison: bool = True) -> None:
        """최신 스펙트럼 프레임의 수치와 두 캔버스를 Tk 메인 스레드에서 갱신한다."""
        if self.closing or not hasattr(self, "spectrum_rms_var"):
            return
        self.last_spectrum_frame = frame
        self.spectrum_rms_var.set(f"{frame.rms_dbfs:.1f} dBFS")
        self.spectrum_peak_var.set(f"{frame.peak_dbfs:.1f} dBFS")
        centroid = float(frame.spectral_centroid_hz)
        self.spectrum_centroid_var.set(f"{centroid:.0f} Hz" if centroid > 0.0 else "—")
        self._draw_waveform(frame)
        self._draw_spectrum(frame)
        profile = self.result.get("reference_spectrum") if self.result else None
        if update_comparison and isinstance(profile, dict):
            try:
                comparison = compare_live_frame(profile, frame)
            except ReferenceCompareError as exc:
                if "silent" in str(exc).lower():
                    self.reference_status_var.set(tr("status.reference_quiet", self.language))
                else:
                    self.reference_status_var.set(tr("status.reference_failed", self.language))
                    self._append_debug_log(f"reference compare error · {type(exc).__name__} · {exc}")
            else:
                self.last_reference_comparison = comparison
                self._populate_reference_rows(comparison)
                self._draw_reference_difference(comparison)
                if self._spectrum_is_running():
                    file_name = str(self.result.get("source", {}).get("file_name", "—"))
                    self.reference_status_var.set(tr("status.reference_running", self.language, file=file_name, rate=21.5))

    def _clear_spectrum_frame_queue(self) -> None:
        """새 세션 전에 남아 있는 이전 스펙트럼 화면 프레임을 버린다."""
        try:
            while True:
                self.spectrum_frames.get_nowait()
        except queue.Empty:
            pass

    def _offer_latest_spectrum(self, session_id: int, frame: SpectrumFrame) -> None:
        """작업 스레드에서 가장 최신 프레임 하나만 bounded 큐에 남긴다."""
        try:
            self.spectrum_frames.put_nowait((session_id, frame))
            return
        except queue.Full:
            pass
        try:
            self.spectrum_frames.get_nowait()
        except queue.Empty:
            pass
        try:
            self.spectrum_frames.put_nowait((session_id, frame))
        except queue.Full:
            pass

    def _drain_spectrum_frames(self) -> None:
        """bounded 큐의 최신 측정치만 꺼내 메인 스레드에서 화면에 반영한다."""
        latest: tuple[int, SpectrumFrame] | None = None
        try:
            while True:
                latest = self.spectrum_frames.get_nowait()
        except queue.Empty:
            pass
        if (
            latest is not None
            and latest[0] == self.spectrum_session_id
            and self._spectrum_is_running()
            and not self.spectrum_stop_requested
        ):
            self._apply_spectrum_frame(latest[1])
        if not self.closing:
            try:
                self.root.after(50, self._drain_spectrum_frames)
            except tk.TclError:
                pass

    def _toggle_spectrum_monitor(self, require_reference: bool = False) -> None:
        """선택한 장치의 공용 실시간 스펙트럼 또는 레퍼런스 비교를 토글한다."""
        if self._spectrum_is_running():
            if self.spectrum_stop_event is not None:
                self.spectrum_stop_event.set()
            self.spectrum_stop_requested = True
            self.spectrum_status_var.set(tr("status.spectrum_stopping", self.language))
            if self.result and isinstance(self.result.get("reference_spectrum"), dict):
                self.reference_status_var.set(tr("status.reference_stopping", self.language))
            self._update_spectrum_availability()
            return
        if require_reference and not (self.result and isinstance(self.result.get("reference_spectrum"), dict)):
            self.reference_status_var.set(tr("status.reference_missing", self.language))
            return
        other_busy = bool(
            (self.worker and self.worker.is_alive())
            or (self.record_worker and self.record_worker.is_alive())
            or self.hardware_probe_active
        )
        if other_busy:
            messagebox.showinfo(APP_NAME, tr("dialog.wait_for_task", self.language))
            return
        if not self.capture_device_id:
            messagebox.showwarning(APP_NAME, tr("error.no_capture_devices", self.language))
            return

        self.spectrum_session_id += 1
        session_id = self.spectrum_session_id
        stop_event = threading.Event()
        self.spectrum_stop_event = stop_event
        self.spectrum_stop_requested = False
        self._clear_spectrum_frame_queue()
        self.last_reference_comparison = None
        self._populate_reference_rows()
        self.reference_canvas.delete("dynamic")
        self.spectrum_status_var.set(tr("status.spectrum_running", self.language, rate=21.5))
        if self.result and isinstance(self.result.get("reference_spectrum"), dict):
            file_name = str(self.result.get("source", {}).get("file_name", "—"))
            self.reference_status_var.set(tr("status.reference_running", self.language, file=file_name, rate=21.5))
        self._append_debug_log(f"spectrum start · {self.capture_device_id} · session={session_id}")
        self.spectrum_worker = threading.Thread(
            target=self._spectrum_monitor_worker,
            args=(session_id, self.capture_device_id, stop_event, self.language),
            daemon=True,
        )
        self.spectrum_worker.start()
        self._update_analysis_availability()

    def _spectrum_monitor_worker(
        self,
        session_id: int,
        device_id: str,
        stop_event: threading.Event,
        language: str,
    ) -> None:
        """장치 블록을 FFT 프레임으로 바꿔 UI bounded 큐에 공급한다."""
        smoother = SpectrumSmoother(history_size=4)

        def handle_block(block: np.ndarray, sample_rate: int) -> None:
            """녹음 콜백의 PCM 블록을 분석하고 최근 네 프레임을 평활화한다."""
            if stop_event.is_set():
                return
            frame = analyze_spectrum_frame(block, sample_rate)
            self._offer_latest_spectrum(session_id, smoother.push(frame))

        try:
            monitor_capture_device(device_id, stop_event, handle_block, language)
            self.events.put(("spectrum_finished", session_id))
        except Exception as exc:
            self.events.put(("spectrum_error", session_id, exc, traceback.format_exc()))

    def _finish_spectrum_monitor(
        self,
        session_id: int,
        error: Exception | None = None,
        detail: str = "",
    ) -> None:
        """현재 세션의 종료·오류를 반영하고 잠근 컨트롤을 안전하게 복구한다."""
        if session_id != self.spectrum_session_id or self.closing:
            return
        self.spectrum_worker = None
        self.spectrum_stop_event = None
        self.spectrum_stop_requested = False
        self._clear_spectrum_frame_queue()
        if error is None:
            self.spectrum_status_var.set(tr("status.spectrum_stopped", self.language))
            if self.result and isinstance(self.result.get("reference_spectrum"), dict):
                self.reference_status_var.set(tr("status.reference_stopped", self.language))
            self._append_debug_log(f"spectrum stop · session={session_id}")
        else:
            self.spectrum_status_var.set(tr("status.spectrum_failed", self.language))
            if self.result and isinstance(self.result.get("reference_spectrum"), dict):
                self.reference_status_var.set(tr("status.reference_failed", self.language))
            self._append_debug_log(f"spectrum error · {type(error).__name__} · {error}\n{detail}")
            messagebox.showerror(APP_NAME, str(error))
        self._change_input_method()
        self._update_analysis_availability()

    def _update_spectrum_availability(self) -> None:
        """다른 작업과 장치 상태를 보고 실시간 스펙트럼 컨트롤을 잠그거나 푼다."""
        if not hasattr(self, "spectrum_button") or not self.spectrum_button.winfo_exists():
            return
        active = self._spectrum_is_running()
        other_busy = bool(
            (self.worker and self.worker.is_alive())
            or (self.record_worker and self.record_worker.is_alive())
            or self.hardware_probe_active
        )
        if active:
            self.spectrum_button.configure(
                text=tr("ui.stop_spectrum", self.language),
                style="Danger.TButton",
                state="disabled" if self.spectrum_stop_requested else "normal",
            )
        else:
            enabled = bool(self.capture_device_id and not other_busy)
            self.spectrum_button.configure(
                text=tr("ui.start_spectrum", self.language),
                style="Accent.TButton",
                state="normal" if enabled else "disabled",
            )
        selector_enabled = bool(self.capture_device_id and not active and not other_busy)
        self.spectrum_capture_combo.configure(state="readonly" if selector_enabled else "disabled")
        self.spectrum_refresh_button.configure(state="normal" if not active and not other_busy else "disabled")
        if hasattr(self, "reference_compare_button") and self.reference_compare_button.winfo_exists():
            has_reference = bool(self.result and isinstance(self.result.get("reference_spectrum"), dict))
            if active:
                self.reference_compare_button.configure(
                    text=tr("ui.stop_reference_compare", self.language),
                    style="Danger.TButton",
                    state="disabled" if self.spectrum_stop_requested or not has_reference else "normal",
                )
            else:
                enabled = bool(has_reference and self.capture_device_id and not other_busy)
                self.reference_compare_button.configure(
                    text=tr("ui.start_reference_compare", self.language),
                    style="Accent.TButton",
                    state="normal" if enabled else "disabled",
                )
            self.reference_capture_combo.configure(state="readonly" if selector_enabled else "disabled")
            self.reference_refresh_button.configure(state="normal" if not active and not other_busy else "disabled")
        if active:
            for widget in self.record_only_widgets:
                widget.configure(state="disabled")

    def _change_language(self, _event: object | None = None) -> None:
        """선택값과 결과 수치를 보존한 채 전체 화면을 새 언어와 글꼴로 다시 만든다."""
        if (
            (self.worker and self.worker.is_alive())
            or (self.record_worker and self.record_worker.is_alive())
            or self._spectrum_is_running()
        ):
            self.language_var.set(LANGUAGE_LABELS[self.language])
            messagebox.showinfo(APP_NAME, tr("dialog.wait_for_task", self.language))
            return
        new_language = language_code(self.language_var.get())
        if new_language == self.language:
            return
        self.pickup_code = choice_code("pickup", self.pickup_var.get())
        self.mix_code = choice_code("mix", self.mix_var.get())
        self.output_code = choice_code("output", self.output_var.get())
        self.compute_backend_code = choice_code("compute", self.compute_var.get())
        self.input_method_code = _input_method_code(self.input_method_var.get())
        self.device_id = device_id_from_label(self.device_var.get())
        developer_enabled = self.developer_var.get()
        self.language = new_language
        if self.result:
            self.result = relocalize_result(self.result, self.language)
        for child in self.root.winfo_children():
            child.destroy()
        self._configure_style()
        self._build_ui()
        self.developer_var.set(developer_enabled)
        if developer_enabled:
            self._toggle_developer_mode()
        self._save_settings()

    def _change_device(self, _event: object | None = None) -> None:
        """멀티이펙터 선택을 갱신하고 미구현 장치에서는 분석을 비활성화한다."""
        self.device_id = device_id_from_label(self.device_var.get())
        self.device_description_var.set(device_description(self.device_id, self.language))
        if not is_supported_device(self.device_id):
            self.status_var.set(tr("status.unsupported_device", self.language))
        else:
            self.status_var.set(tr("status.ready", self.language) if self.file_var.get() else tr("status.choose_file", self.language))
        self._update_analysis_availability()
        self._save_settings()

    def _start_hardware_probe(self) -> None:
        """PyTorch·CUDA 확인을 UI 밖의 스레드에서 시작해 창 멈춤을 방지한다."""
        if (
            self.hardware_probe_active
            or (self.worker and self.worker.is_alive())
            or (self.record_worker and self.record_worker.is_alive())
            or self._spectrum_is_running()
        ):
            return
        self.hardware_probe_active = True
        self.hardware_status = {}
        self._set_compute_controls_enabled(False)
        self._populate_diagnostics()
        self._update_analysis_availability()
        threading.Thread(target=self._hardware_probe_worker, daemon=True).start()

    def _hardware_probe_worker(self) -> None:
        """Demucs와 GPU 런타임을 검사하고 메인 UI 큐로 결과를 전달한다."""
        try:
            status = separator_runtime_status("auto")
        except Exception as exc:
            status = {"available": False, "error": str(exc), "resolved_device": "unavailable"}
        self.events.put(("hardware_status", status))

    def _apply_hardware_status(self, status: dict[str, object]) -> None:
        """하드웨어 검사 결과를 저장하고 가능한 선택값·진단표·로그를 갱신한다."""
        self.hardware_probe_active = False
        self.hardware_status = dict(status)
        cuda_available = bool(status.get("cuda_available"))
        codes = ("auto", "cuda", "cpu") if cuda_available else ("auto", "cpu")
        if self.compute_backend_code == "cuda" and not cuda_available:
            self.compute_backend_code = "auto"
            self._save_settings()
        self.compute_combo.configure(values=tuple(choice_label("compute", code, self.language) for code in codes))
        self.compute_var.set(choice_label("compute", self.compute_backend_code, self.language))
        self._populate_diagnostics()
        self._update_analysis_availability()
        self._append_debug_log(
            "hardware probe · "
            f"cuda={str(cuda_available).lower()} · "
            f"gpu={status.get('gpu_name') or '-'} · "
            f"recommended={status.get('resolved_device', 'unavailable')}"
        )

    def _change_compute_backend(self, _event: object | None = None) -> None:
        """표시된 AI 가속 선택을 안정적인 auto·cuda·cpu 코드로 저장한다."""
        self.compute_backend_code = choice_code("compute", self.compute_var.get())
        self.compute_var.set(choice_label("compute", self.compute_backend_code, self.language))
        self._save_settings()
        self._populate_diagnostics()
        self._append_debug_log(f"compute preference · {self.compute_backend_code}")

    def _set_compute_controls_enabled(self, enabled: bool) -> None:
        """하드웨어 검사·분석 상태에 맞춰 가속 선택과 재검사 버튼을 함께 잠그거나 푼다."""
        if not hasattr(self, "compute_combo") or not self.compute_combo.winfo_exists():
            return
        busy = bool(
            (self.worker and self.worker.is_alive())
            or (self.record_worker and self.record_worker.is_alive())
            or self._spectrum_is_running()
        )
        active = bool(enabled and not busy and not self.hardware_probe_active)
        self.compute_combo.configure(state="readonly" if active else "disabled")
        self.hardware_refresh_button.configure(state="normal" if active else "disabled")

    @staticmethod
    def _format_bytes(value: object) -> str:
        """바이트 값을 진단표에서 읽기 쉬운 MiB 또는 GiB 문자열로 바꾼다."""
        if value is None:
            return "-"
        try:
            size = max(0, int(value))
        except (TypeError, ValueError):
            return "-"
        if size >= 1024**3:
            return f"{size / 1024**3:.2f} GiB"
        return f"{size / 1024**2:.1f} MiB"

    def _populate_diagnostics(self) -> None:
        """하드웨어·AI 분리 벤치마크·DSP 특징을 한 진단표에 순서대로 표시한다."""
        if not hasattr(self, "diag_tree") or not self.diag_tree.winfo_exists():
            return
        for item in self.diag_tree.get_children():
            self.diag_tree.delete(item)

        def add(label_key: str, value: object) -> None:
            """번역된 항목명과 문자열 값을 진단표 끝에 추가한다."""
            self.diag_tree.insert("", "end", values=(tr(label_key, self.language), str(value)))

        add("diag.compute_preference", choice_label("compute", self.compute_backend_code, self.language))
        status = self.hardware_status
        if not status:
            add("diag.hardware_status", tr("value.checking", self.language))
        else:
            add("diag.hardware_status", tr("value.available" if status.get("available") else "value.unavailable", self.language))
            resolved = str(status.get("resolved_device") or "unavailable").upper()
            add("diag.recommended_device", resolved)
            add("diag.cuda_available", tr("value.yes" if status.get("cuda_available") else "value.no", self.language))
            add("diag.cuda_build", status.get("cuda_build") or "CPU-only")
            add("diag.gpu_model", status.get("gpu_name") or "-")
            total = self._format_bytes(status.get("gpu_vram_total_bytes"))
            free = self._format_bytes(status.get("gpu_vram_free_bytes"))
            add("diag.gpu_memory", f"{total} / {free}")
            add("diag.runtime_versions", f"{status.get('torch_version', '-')} / {status.get('cuda_build') or '-'}")
            add("diag.model_cache", tr("value.cached" if status.get("model_cached") else "value.not_cached", self.language))
            if status.get("device_resolution_error") or status.get("error"):
                add("diag.fallback_reason", status.get("device_resolution_error") or status.get("error"))
        add("diag.native_dsp", tr("value.numpy_native", self.language))

        if not self.result:
            return
        separation = self.result.get("source_separation", {})
        if separation.get("used"):
            self.diag_tree.insert("", "end", values=(tr("ui.guitar_source", self.language), tr("ui.guitar_stem_only", self.language)))
            self.diag_tree.insert("", "end", values=(tr("ui.separator_model", self.language), separation.get("model", "")))
            add("diag.requested_device", str(separation.get("requested_device") or "-").upper())
            add("diag.effective_device", str(separation.get("resolved_device") or "-").upper())
            add("diag.inference_time", f"{float(separation.get('inference_total_seconds', 0.0)):.2f} s")
            add("diag.chunk_speed", f"{float(separation.get('inference_seconds_per_chunk', 0.0)):.2f} s")
            realtime_factor = float(separation.get("realtime_factor", 0.0))
            speed = (1.0 / realtime_factor) if realtime_factor > 0 else 0.0
            add("diag.realtime_factor", f"{realtime_factor:.3f} RTF · {speed:.2f}× realtime")
            if separation.get("peak_gpu_memory_bytes") is not None:
                add("diag.peak_gpu_memory", self._format_bytes(separation.get("peak_gpu_memory_bytes")))
        else:
            add("diag.effective_device", tr("value.not_applicable", self.language))
        for label, value in human_feature_rows(self.result["features"], self.language):
            self.diag_tree.insert("", "end", values=(label, value))

    def _change_input_method(self, _event: object | None = None) -> None:
        """로컬 파일과 PC 재생음 녹음 모드에 맞춰 관련 컨트롤 상태를 바꾼다."""
        self.input_method_code = _input_method_code(self.input_method_var.get())
        recording = self.input_method_code == "record"
        for widget in self.record_only_widgets:
            if widget is self.capture_combo:
                state = "readonly" if recording else "disabled"
            else:
                state = "normal" if recording else "disabled"
            widget.configure(state=state)
        self.file_entry.configure(state="readonly" if recording else "normal")
        self.choose_file_button.configure(state="disabled" if recording else "normal")
        self.start_entry.configure(state="disabled" if recording else "normal")
        self.end_entry.configure(state="disabled" if recording else "normal")
        if not is_supported_device(self.device_id):
            self.status_var.set(tr("status.unsupported_device", self.language))
        elif recording:
            self.start_var.set("0")
            self.end_var.set("0")
            self.status_var.set(tr("status.recording_ready", self.language))
        elif self.file_var.get():
            self.status_var.set(tr("status.ready", self.language))
        else:
            self.status_var.set(tr("status.choose_file", self.language))
        self._update_analysis_availability()

    def _refresh_capture_devices(self, silent: bool = False) -> None:
        """Windows 오디오 장치를 다시 열거하고 기존 선택이 가능하면 유지한다."""
        try:
            devices = list_capture_devices()
        except RecordingError as exc:
            devices = []
            if not silent:
                messagebox.showerror(APP_NAME, str(exc))
        self.capture_devices = devices
        self.capture_label_map = {capture_device_label(item, self.language): item for item in devices}
        capture_values = tuple(self.capture_label_map)
        self.capture_combo.configure(values=capture_values)
        if hasattr(self, "spectrum_capture_combo"):
            self.spectrum_capture_combo.configure(values=capture_values)
        if hasattr(self, "reference_capture_combo"):
            self.reference_capture_combo.configure(values=capture_values)
        selected = next((item for item in devices if item.id == self.capture_device_id), None)
        if selected is None:
            selected = next((item for item in devices if item.is_loopback), devices[0] if devices else None)
        if selected:
            self.capture_device_id = selected.id
            self.capture_var.set(capture_device_label(selected, self.language))
        else:
            self.capture_device_id = ""
            self.capture_var.set(tr("error.no_capture_devices", self.language))
        self._update_spectrum_availability()

    def _capture_device_changed(self, _event: object | None = None) -> None:
        """녹음 콤보박스의 표시 라벨을 실제 장치 식별자로 저장한다."""
        device = self.capture_label_map.get(self.capture_var.get())
        self.capture_device_id = device.id if device else ""
        self._update_spectrum_availability()

    def _toggle_recording(self) -> None:
        """현재 상태에 따라 PC 재생음 녹음을 시작하거나 중지 요청을 보낸다."""
        if self.record_worker and self.record_worker.is_alive():
            self.record_stop_event.set()
            self.status_var.set(tr("status.recording_stopped", self.language))
            self.record_button.configure(state="disabled")
            return
        if (
            (self.worker and self.worker.is_alive())
            or self._spectrum_is_running()
            or self.hardware_probe_active
        ):
            messagebox.showinfo(APP_NAME, tr("dialog.wait_for_task", self.language))
            return
        if not self.capture_device_id:
            messagebox.showwarning(APP_NAME, tr("error.no_capture_devices", self.language))
            return
        try:
            limit = float(self.record_limit_var.get().strip())
        except ValueError:
            messagebox.showwarning(APP_NAME, tr("error.time_number", self.language))
            return
        if not math.isfinite(limit) or limit < 3:
            messagebox.showwarning(APP_NAME, tr("error.minimum_segment", self.language))
            return
        limit = min(limit, float(MAX_RECORD_SECONDS))
        self.record_limit_var.set(f"{limit:g}")
        capture_root = self.data_root / "captures"
        capture_root.mkdir(parents=True, exist_ok=True)
        destination = capture_root / f"capture-{datetime.now():%Y%m%d-%H%M%S}.wav"
        self.temporary_recordings.add(destination)
        self.record_stop_event.clear()
        self.record_button.configure(text=tr("ui.stop_record", self.language), style="Danger.TButton")
        self.analyze_button.configure(state="disabled")
        self.language_combo.configure(state="disabled")
        self.status_var.set(tr("progress.recording", self.language, elapsed=0.0, limit=limit))
        self._append_debug_log(f"record start · {self.capture_device_id} · limit={limit:.1f}s")
        self.record_worker = threading.Thread(target=self._recording_worker, args=(destination, limit), daemon=True)
        self.record_worker.start()
        self._update_analysis_availability()

    def _recording_worker(self, destination: Path, limit: float) -> None:
        """오디오 녹음을 백그라운드에서 실행하고 UI 큐에 상태를 전달한다."""
        def progress(elapsed: float, text: str) -> None:
            """녹음 경과 시간을 메인 UI가 읽는 이벤트로 바꾼다."""
            self.events.put(("record_progress", elapsed, limit, text))

        try:
            duration = record_device_to_wav(self.capture_device_id, destination, limit, self.record_stop_event, progress, self.language)
            self.events.put(("record_done", destination, duration))
        except Exception as exc:
            self.events.put(("record_error", exc, traceback.format_exc()))

    def _toggle_developer_mode(self) -> None:
        """개발자 순서도와 변경 기록 탭을 표시하거나 숨긴다."""
        if self.developer_var.get():
            self.notebook.add(self.debug_tab, text=tr("ui.debug_tab", self.language))
            self.notebook.add(self.changelog_tab, text=f"{tr('ui.changelog_tab', self.language)} · {APP_VERSION}")
            self._append_debug_log("developer options enabled")
            self.notebook.select(self.debug_tab)
        else:
            if self.notebook.select() in {str(self.debug_tab), str(self.changelog_tab)}:
                self.notebook.select(0)
            self.notebook.hide(self.debug_tab)
            self.notebook.hide(self.changelog_tab)
        self._update_copy_availability()

    def _draw_debug_diagram(self) -> None:
        """실제 실행 순서대로 클릭 가능한 세로 블록과 연결 화살표를 그린다."""
        canvas = self.debug_canvas
        canvas.delete("all")
        self.debug_nodes.clear()
        x1, x2 = 10, 258
        # 720p급 창에서 오른쪽 결과 영역이 높이를 나눠 써도 11개 단계가 모두 보이게 한다.
        node_height, gap, top = 23, 5, 3
        active_order = block_by_id(self.active_debug_block)["order"]
        for index, raw_block in enumerate(PIPELINE_BLOCKS):
            block = localized_block(raw_block["id"], self.language)
            y1 = top + index * (node_height + gap)
            y2 = y1 + node_height
            if block["id"] in self.completed_debug_blocks:
                fill, outline = "#14392f", COLORS["accent"]
            elif block["order"] == active_order:
                fill, outline = "#17344a", COLORS["blue"]
            else:
                fill, outline = "#111a22", COLORS["border"]
            tag = f"node:{block['id']}"
            rectangle = canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline=outline, width=2, tags=(tag, "node"))
            canvas.create_text(x1 + 13, y1 + 6, text=f"{block['order']:02d}", fill=COLORS["accent"], anchor="w", font=("Consolas", 7, "bold"), tags=(tag, "node"))
            canvas.create_text(x1 + 47, y1 + 5, text=block["title"], fill=COLORS["text"], anchor="w", font=(self.ui_font, 7, "bold"), tags=(tag, "node"))
            canvas.create_text(x1 + 47, y1 + 16, text=block["short"], fill=COLORS["muted"], anchor="w", font=(self.ui_font, 6), tags=(tag, "node"))
            self.debug_nodes[block["id"]] = (rectangle, block["order"])
            canvas.tag_bind(tag, "<Button-1>", lambda _event, value=block["id"]: self._select_debug_block(value))
            canvas.tag_bind(tag, "<Enter>", lambda _event: canvas.configure(cursor="hand2"))
            canvas.tag_bind(tag, "<Leave>", lambda _event: canvas.configure(cursor=""))
            if index < len(PIPELINE_BLOCKS) - 1:
                canvas.create_line((x1 + x2) / 2, y2 + 2, (x1 + x2) / 2, y2 + gap - 1, fill="#527080", width=2, arrow="last")

    def _select_debug_block(self, block_id: str) -> None:
        """선택한 처리 블록의 언어별 설명과 연결된 실제 함수 원문을 표시한다."""
        self.selected_debug_block = block_id
        block = localized_block(block_id, self.language)
        symbols = ", ".join(symbol for _file, symbol in block["symbols"])
        io_text = "Input" if self.language == "en" else "입력"
        output_text = "Output" if self.language == "en" else "출력"
        function_text = "Functions" if self.language == "en" else "함수"
        self.debug_title_var.set(f"{block['order']:02d} · {block['title']}")
        self.debug_description_var.set(f"{block['description']}\n{io_text}: {block['inputs']}  →  {output_text}: {block['outputs']}\n{function_text}: {symbols}")
        try:
            code = code_for_block(block_id)
        except Exception as exc:
            code = f"# 소스 코드를 불러오지 못했습니다.\n# {exc}"
        self.debug_code.configure(state="normal")
        self.debug_code.delete("1.0", "end")
        self.debug_code.insert("1.0", code)
        for line_number, line in enumerate(code.splitlines(), start=1):
            stripped = line.lstrip()
            start, end = f"{line_number}.0", f"{line_number}.end"
            if stripped.startswith("#") or "  #" in line:
                self.debug_code.tag_add("comment", start, end)
            if '"""' in line or "'''" in line:
                self.debug_code.tag_add("docstring", start, end)
            self.debug_code.tag_add("line", start, f"{line_number}.6")
        self.debug_code.configure(state="disabled")
        self.debug_code.see("1.0")

    def _append_debug_log(self, message: str) -> None:
        """시각 포함 이벤트를 화면과 EXE 옆 일별 UTF-8 로그 파일에 함께 남긴다."""
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        line = f"[{stamp}] {message}"
        self.debug_log_lines.append(line)
        self.debug_log_lines = self.debug_log_lines[-300:]
        try:
            log_path = self.log_root / f"ToneMatchTMP-{datetime.now():%Y%m%d}.log"
            with log_path.open("a", encoding="utf-8") as output:
                output.write(line + "\n")
        except OSError:
            pass
        if hasattr(self, "debug_log") and self.debug_log.winfo_exists():
            self.debug_log.configure(state="normal")
            self.debug_log.insert("end", line + "\n")
            self.debug_log.see("end")
            self.debug_log.configure(state="disabled")

    def _set_debug_progress(self, progress: float, message: str) -> None:
        """진행률로 활성·완료 블록을 계산하고 순서도와 로그를 갱신한다."""
        self.active_debug_block = block_for_progress(progress)
        active_order = block_by_id(self.active_debug_block)["order"]
        self.completed_debug_blocks = {block["id"] for block in PIPELINE_BLOCKS if block["order"] < active_order}
        if progress >= 100:
            self.completed_debug_blocks.add("result")
        self._draw_debug_diagram()
        self._append_debug_log(f"{progress:5.1f}% · {self.active_debug_block} · {message}")

    def _refresh_analysis_progress(self) -> None:
        """실제 콜백의 전체 단계 진행률과 독립적인 경과 시간을 표시한다."""
        if self.analysis_started_at is not None:
            self.analysis_elapsed_seconds = max(0.0, time.monotonic() - self.analysis_started_at)
        seconds = int(self.analysis_elapsed_seconds)
        elapsed = f"{seconds // 60:02d}:{seconds % 60:02d}"
        self.progress_detail_var.set(tr("progress.overall", self.language, percent=self.analysis_progress_percent, elapsed=elapsed))

    def _tick_analysis_progress(self) -> None:
        """다운로드나 추론 콜백을 기다리는 동안에도 경과 시간을 계속 갱신한다."""
        if self.closing:
            return
        self._refresh_analysis_progress()
        try:
            self.root.after(250, self._tick_analysis_progress)
        except tk.TclError:
            pass

    def _finish_analysis_progress(self) -> None:
        """완료·오류·취소 시 마지막 진행률과 소요 시간을 화면에 보존한다."""
        self._refresh_analysis_progress()
        self.analysis_started_at = None

    def _choose_audio(self) -> None:
        """파일 선택 창에서 오디오 또는 영상 경로를 받아 입력 상태를 갱신한다."""
        filetypes = ((tr("dialog.audio_files", self.language), SUPPORTED_AUDIO_PATTERN), (tr("dialog.all_files", self.language), "*.*"))
        path = filedialog.askopenfilename(title=tr("dialog.choose_audio_title", self.language), filetypes=filetypes)
        if path:
            self.file_var.set(path)
            self.status_var.set(tr("status.ready", self.language))

    def _open_reference(self) -> None:
        """참고 URL을 기본 브라우저에서 열되 앱이 YouTube 음원을 추출하지 않는다."""
        value = self.url_var.get().strip()
        if not value:
            messagebox.showinfo(APP_NAME, tr("dialog.enter_url", self.language))
            return
        if not value.lower().startswith(("https://", "http://")):
            value = "https://" + value
        webbrowser.open(value)

    def _parse_inputs(self) -> tuple[str, float, float]:
        """화면 문자열을 분석 요청으로 바꾸고 파일·시간·장치 조건을 검증한다."""
        if not is_supported_device(self.device_id):
            raise AnalysisError(tr("error.unsupported_device", self.language))
        path = self.file_var.get().strip().strip('"')
        if not path or not Path(path).is_file():
            raise AnalysisError(tr("error.choose_file", self.language))
        try:
            start = float(self.start_var.get().strip() or "0")
            end = float(self.end_var.get().strip() or "0")
        except ValueError as exc:
            raise AnalysisError(tr("error.time_number", self.language)) from exc
        if not math.isfinite(start) or not math.isfinite(end) or start < 0 or end < 0:
            raise AnalysisError(tr("error.time_positive", self.language))
        if end != 0 and end <= start:
            raise AnalysisError(tr("error.end_after_start", self.language))
        if end != 0 and end - start < 3:
            raise AnalysisError(tr("error.minimum_segment", self.language))
        if end != 0:
            end = min(end, start + MAX_ANALYSIS_SECONDS)
        return path, start, end

    def _start_analysis(self) -> None:
        """검증된 요청을 별도 스레드에서 시작하고 취소·내보내기 상태를 설정한다."""
        if self.worker and self.worker.is_alive():
            return
        if (self.record_worker and self.record_worker.is_alive()) or self._spectrum_is_running() or self.hardware_probe_active:
            messagebox.showinfo(APP_NAME, tr("dialog.wait_for_task", self.language))
            return
        try:
            path, start, end = self._parse_inputs()
        except AnalysisError as exc:
            messagebox.showwarning(APP_NAME, str(exc))
            return
        self.pickup_code = choice_code("pickup", self.pickup_var.get())
        self.mix_code = choice_code("mix", self.mix_var.get())
        self.output_code = choice_code("output", self.output_var.get())
        self.compute_backend_code = choice_code("compute", self.compute_var.get())
        self.result = None
        self.completed_debug_blocks = {"boot"}
        self.active_debug_block = "input"
        self._draw_debug_diagram()
        range_label = f"{start:.3f}s–{'full' if end == 0 else f'{end:.3f}s'}"
        self._append_debug_log(
            f"analysis request · {Path(path).name} · {range_label} · "
            f"separation={self.mix_code} · compute={self.compute_backend_code}"
        )
        self.analysis_cancel_event.clear()
        self.analysis_started_at = time.monotonic()
        self.analysis_elapsed_seconds = 0.0
        self.analysis_progress_percent = 2.0
        self.progress_var.set(2)
        self._refresh_analysis_progress()
        self._refresh_reference_profile(reset_comparison=True)
        self.status_var.set(tr("status.preparing", self.language))
        self.analyze_button.configure(state="disabled", text=tr("ui.analyzing", self.language))
        self.cancel_button.configure(state="normal")
        self.language_combo.configure(state="disabled")
        self._set_compute_controls_enabled(False)
        for button in (self.export_json_button, self.export_html_button, self.copy_button):
            button.configure(state="disabled")
        request = {
            "source": path,
            "start_seconds": start,
            "end_seconds": end,
            "pickup": self.pickup_code,
            "mix_mode": self.mix_code,
            "output_mode": self.output_code,
            "reference_url": self.url_var.get().strip(),
            "device_id": self.device_id,
            "language": self.language,
            "compute_backend": self.compute_backend_code,
        }
        self.worker = threading.Thread(target=self._analysis_worker, args=(request,), daemon=True)
        self.worker.start()
        self._update_analysis_availability()

    def _cancel_analysis(self) -> None:
        """다운로드 또는 Demucs 내부 처리 구간 경계에서 멈추도록 취소 신호를 보낸다."""
        if self.worker and self.worker.is_alive():
            self.analysis_cancel_event.set()
            self.cancel_button.configure(state="disabled")
            self.status_var.set(tr("status.cancelling", self.language))
            self._append_debug_log("analysis cancellation requested")

    def _analysis_worker(self, request: dict) -> None:
        """전체 기타 분석을 실행하고 결과 또는 오류를 메인 UI 큐에 전달한다."""
        def progress(value: float, text: str) -> None:
            """엔진 콜백을 Tk 메인 스레드용 진행 이벤트로 변환한다."""
            self.events.put(("progress", value, text))

        try:
            result = analyze_file(**request, progress=progress, cancel_requested=self.analysis_cancel_event.is_set)
            self.events.put(("done", result))
        except Exception as exc:
            self.events.put(("error", exc, traceback.format_exc()))

    def _drain_events(self) -> None:
        """백그라운드 분석·녹음·스펙트럼 제어 이벤트를 Tk 메인 스레드에서 처리한다."""
        try:
            while True:
                event = self.events.get_nowait()
                if event[0] == "progress":
                    value = float(event[1])
                    if math.isfinite(value):
                        self.analysis_progress_percent = max(self.analysis_progress_percent, min(100.0, max(0.0, value)))
                    self.progress_var.set(self.analysis_progress_percent)
                    self._refresh_analysis_progress()
                    if not self.analysis_cancel_event.is_set():
                        self.status_var.set(event[2])
                    self._set_debug_progress(self.analysis_progress_percent, event[2])
                elif event[0] == "done":
                    self._show_result(event[1])
                elif event[0] == "error":
                    self._show_error(event[1], event[2])
                elif event[0] == "record_progress":
                    self.status_var.set(event[3])
                    self.progress_var.set(min(100.0, event[1] / max(event[2], 1.0) * 100.0))
                elif event[0] == "record_done":
                    self._recording_completed(event[1], event[2])
                elif event[0] == "record_error":
                    self._recording_failed(event[1], event[2])
                elif event[0] == "hardware_status":
                    self._apply_hardware_status(event[1])
                elif event[0] == "spectrum_finished":
                    self._finish_spectrum_monitor(event[1])
                elif event[0] == "spectrum_error":
                    self._finish_spectrum_monitor(event[1], event[2], event[3])
        except queue.Empty:
            pass
        if not self.closing:
            try:
                self.root.after(80, self._drain_events)
            except tk.TclError:
                pass

    def _recording_completed(self, path: Path, duration: float) -> None:
        """완료된 임시 녹음을 현재 분석 파일로 연결하고 버튼 상태를 복구한다."""
        self.file_var.set(str(path))
        self.start_var.set("0")
        self.end_var.set("0")
        self.progress_var.set(0)
        self.record_button.configure(text=tr("ui.start_record", self.language), style="TButton", state="normal")
        self.language_combo.configure(state="readonly")
        self._set_compute_controls_enabled(True)
        self.status_var.set(tr("status.recording_complete", self.language, seconds=duration))
        self._append_debug_log(f"record complete · {path.name} · {duration:.2f}s")
        self._update_analysis_availability()

    def _recording_failed(self, exc: Exception, detail: str) -> None:
        """녹음 실패 메시지와 상세 로그를 남기고 UI를 다시 사용할 수 있게 한다."""
        self.progress_var.set(0)
        self.record_button.configure(text=tr("ui.start_record", self.language), style="TButton", state="normal")
        self.language_combo.configure(state="readonly")
        self._set_compute_controls_enabled(True)
        self._append_debug_log(f"record error · {type(exc).__name__} · {exc}\n{detail}")
        messagebox.showerror(APP_NAME, str(exc))
        self._update_analysis_availability()

    def _show_error(self, exc: Exception, detail: str) -> None:
        """분석 실패 상태를 복구하고 사용자 메시지와 영구 개발 로그를 남긴다."""
        self._finish_analysis_progress()
        self.status_var.set(tr("status.failed", self.language))
        self.analyze_button.configure(text=tr("ui.analyze", self.language))
        self.cancel_button.configure(state="disabled")
        self.language_combo.configure(state="readonly")
        self._set_compute_controls_enabled(True)
        self._append_debug_log(f"analysis error · {type(exc).__name__} · {exc}\n{detail}")
        message = str(exc) if isinstance(exc, AnalysisError) else tr("dialog.unexpected", self.language, error=exc)
        if "취소" not in message and "cancel" not in message.lower():
            messagebox.showerror(APP_NAME, message)
        self._update_analysis_availability()

    def _show_result(self, result: dict, reset_notebook: bool = True) -> None:
        """추천 체인 세 개, 기타 stem 진단과 상태를 현재 언어 화면에 표시한다."""
        self.result = result
        self.analysis_progress_percent = 100.0
        self._finish_analysis_progress()
        self._set_debug_progress(100, tr("progress.complete", self.language))
        self.progress_var.set(100)
        features = result["features"]
        top = result["recipes"][0]
        self.result_title_var.set(f"{top['name']} · {tr('recipe.match', self.language, value=top['match_percent'])}")
        self.summary_var.set(tr("result.feature_summary", self.language, sat=features["saturation"] * 100, bright=features["brightness"] * 100, body=features["body"] * 100, amb=features["ambience"] * 100, conf=features["analysis_confidence"] * 100))
        for index, recipe in enumerate(result["recipes"]):
            self._render_recipe(self.recipe_texts[index], recipe)
            self.notebook.tab(index, text=f"{tr('ui.recipe_tab', self.language, rank=index + 1)} · {recipe['match_percent']}%")
        self._render_voicing(result.get("chord_voicing", {}))
        separation = result.get("source_separation", {})
        if separation.get("used"):
            self._append_debug_log(
                "separation backend · "
                f"requested={separation.get('requested_device', '-')} · "
                f"active={separation.get('resolved_device', '-')} · "
                f"inference={float(separation.get('inference_total_seconds', 0.0)):.2f}s"
            )
        self._populate_diagnostics()
        self._refresh_reference_profile(reset_comparison=reset_notebook)
        if reset_notebook:
            self.notebook.select(0)
        self.status_var.set(tr("status.complete", self.language))
        self.analyze_button.configure(text=tr("ui.analyze_again", self.language))
        self.cancel_button.configure(state="disabled")
        self.language_combo.configure(state="readonly")
        self._set_compute_controls_enabled(True)
        self._update_analysis_availability()
        for button in (self.export_json_button, self.export_html_button, self.copy_button):
            button.configure(state="normal")

    def _render_recipe(self, widget: ScrolledText, recipe: dict) -> None:
        """한 추천 체인의 모델·순서·파라미터·이유를 읽기 쉬운 서식으로 그린다."""
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("end", f"{recipe['name']}\n", "heading")
        widget.insert("end", f"{recipe['archetype']}  ·  {tr('recipe.match', self.language, value=recipe['match_percent'])}\n{recipe['description']}\n", "subheading")
        widget.insert(
            "end",
            f"{tr('recipe.output_route', self.language)} · {recipe['output_mode_label']}\n"
            f"{tr('recipe.route_applicability', self.language)} · {recipe['route_applicability_label']}\n",
            "route",
        )
        widget.insert("end", f"{tr('recipe.pickup_correction', self.language)}  {recipe['pickup_correction']}\n", "reason")
        for block in recipe["blocks"]:
            category = block.get("category_label", block["category"])
            widget.insert("end", f"\n{block['order']:02d}  {category}  ·  {block['model']}\n", "block")
            for name, value in block["parameters"].items():
                widget.insert("end", f"    {name:<22} {value}\n", "parameter")
            widget.insert("end", f"    ↳ {block['reason']}\n", "reason")
        if recipe["limitations"]:
            widget.insert("end", f"\n{tr('recipe.caution', self.language)}\n", "warning")
            for item in recipe["limitations"]:
                widget.insert("end", f"• {item}\n", "warning")
        widget.configure(state="disabled")
        widget.see("1.0")

    def _render_voicing(self, analysis: dict) -> None:
        """실험 보이싱 타임라인과 연주 후보를 별도 결과 탭에 표시한다."""
        widget = self.voicing_text
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("end", tr("ui.voicing_tab", self.language) + "\n", "heading")
        widget.insert("end", tr("ui.voicing_intro", self.language) + "\n", "intro")
        events = analysis.get("events", [])
        reliable = [event for event in events if event.get("chord_type") != "unknown"]
        if not reliable:
            widget.insert("end", tr("ui.voicing_empty", self.language) + "\n", "warning")
        for event in reliable:
            start = self._format_time(float(event["start_seconds"]))
            end = self._format_time(float(event["end_seconds"]))
            confidence = int(round(float(event["confidence"]) * 100))
            widget.insert("end", f"{start}–{end}   {event['symbol']}   {confidence}%\n", "event")
            notes = pitch_class_names(event.get("pitch_classes", ())) or "—"
            register = tr(f"voicing.register.{event.get('register', 'unknown')}", self.language)
            spacing = tr(f"voicing.spacing.{event.get('spacing', 'unknown')}", self.language)
            inversion = tr(f"voicing.inversion.{event.get('inversion', 'unknown')}", self.language)
            widget.insert("end", f"{tr('ui.voicing_notes', self.language)} · {notes}\n", "detail")
            widget.insert("end", f"{tr('ui.voicing_profile', self.language)} · {register} · {spacing} · {inversion}\n", "detail")
            shapes = event.get("candidate_shapes", [])
            if shapes:
                widget.insert("end", tr("ui.playable_shapes", self.language) + "\n", "warning")
                for shape in shapes:
                    frets = " ".join(str(value) for value in shape["frets_low_e_to_high_e"])
                    widget.insert("end", f"    {shape['label']} · E A D G B e = {frets}\n", "detail")
        widget.insert("end", "\n" + tr("ui.voicing_limit", self.language), "warning")
        widget.configure(state="disabled")
        widget.see("1.0")

    @staticmethod
    def _format_time(seconds: float) -> str:
        """초 단위 위치를 긴 곡에서도 읽기 쉬운 분:초 문자열로 바꾼다."""
        total = max(0, int(round(seconds)))
        minutes, remainder = divmod(total, 60)
        return f"{minutes:02d}:{remainder:02d}"

    def _update_analysis_availability(self) -> None:
        """장치 지원과 분석·녹음·스펙트럼 상태를 보고 공통 컨트롤을 갱신한다."""
        busy = (
            (self.worker and self.worker.is_alive())
            or (self.record_worker and self.record_worker.is_alive())
            or self._spectrum_is_running()
            or self.hardware_probe_active
        )
        enabled = is_supported_device(self.device_id) and not busy
        self.analyze_button.configure(state="normal" if enabled else "disabled")
        self.language_combo.configure(state="disabled" if busy else "readonly")
        self._set_compute_controls_enabled(not busy)
        self._update_spectrum_availability()
        self._update_copy_availability()

    def _update_copy_availability(self, _event: object | None = None) -> None:
        """현재 탭에 복사할 표시 내용이 있고 작업 중이 아닐 때만 복사 버튼을 켠다."""
        if not hasattr(self, "copy_button") or not hasattr(self, "notebook"):
            return
        selected_tab = self.notebook.select()
        developer_tabs = {
            str(getattr(self, "debug_tab", "")),
            str(getattr(self, "changelog_tab", "")),
        }
        busy = bool((self.worker and self.worker.is_alive()) or (self.record_worker and self.record_worker.is_alive()))
        has_content = bool(self.result) or selected_tab in developer_tabs
        self.copy_button.configure(state="normal" if has_content and not busy else "disabled")

    def _default_export_name(self, suffix: str) -> str:
        """입력 파일명을 안전한 기본 내보내기 파일명으로 바꾼다."""
        stem = Path(self.result["source"]["file_name"]).stem if self.result else "tone"
        safe = "".join(character if character.isalnum() or character in "-_" else "_" for character in stem)[:60]
        return f"{safe}_ToneMatchTMP{suffix}"

    def _export_json(self) -> None:
        """현재 전체 분석 데이터와 분리 진단을 UTF-8 JSON으로 저장한다."""
        if not self.result:
            return
        path = filedialog.asksaveasfilename(title=tr("dialog.save_json_title", self.language), defaultextension=".json", initialfile=self._default_export_name(".json"), filetypes=(("JSON", "*.json"),))
        if path:
            try:
                save_json(self.result, path)
                self._mark_export(path, "JSON")
            except OSError as exc:
                messagebox.showerror(APP_NAME, tr("dialog.save_failed", self.language, error=exc))

    def _export_html(self) -> None:
        """현재 결과를 외부 자원이 없는 한·영 HTML 리포트로 저장하고 선택 시 연다."""
        if not self.result:
            return
        path = filedialog.asksaveasfilename(title=tr("dialog.save_html_title", self.language), defaultextension=".html", initialfile=self._default_export_name(".html"), filetypes=(("HTML", "*.html"),))
        if path:
            try:
                save_html(self.result, path)
                self._mark_export(path, "HTML")
                if messagebox.askyesno(APP_NAME, tr("dialog.open_report", self.language)):
                    webbrowser.open(Path(path).resolve().as_uri())
            except OSError as exc:
                messagebox.showerror(APP_NAME, tr("dialog.save_failed", self.language, error=exc))

    def _mark_export(self, path: str, kind: str) -> None:
        """내보내기 단계를 순서도에 표시하고 상태와 영구 로그를 갱신한다."""
        self.completed_debug_blocks.add("export")
        self.active_debug_block = "export"
        self._draw_debug_diagram()
        self._append_debug_log(f"{kind} export · {path}")
        key = "status.json_saved" if kind == "JSON" else "status.html_saved"
        self.status_var.set(tr(key, self.language, path=path))

    def _copy_recipe(self) -> None:
        """현재 선택한 결과·진단·개발자 탭의 표시 내용을 클립보드에 복사한다."""
        selected_tab = self.notebook.select()
        selected_index = self.notebook.index(selected_tab)
        tab_name = str(self.notebook.tab(selected_tab, "text"))
        if selected_index < len(self.recipe_texts):
            if not self.result:
                return
            value = recipe_as_text(self.result, selected_index)
            log_detail = f"recipe rank={selected_index + 1}"
        elif selected_tab == str(self.voicing_tab):
            if not self.result:
                return
            value = self.voicing_text.get("1.0", "end-1c")
            log_detail = "chord voicing"
        elif selected_tab == str(self.reference_compare_tab):
            if not self.result or not isinstance(self.result.get("reference_spectrum"), dict):
                return
            headings = "\t".join(
                (
                    tr("ui.compare_band", self.language),
                    tr("ui.compare_reference", self.language),
                    tr("ui.compare_current", self.language),
                    tr("ui.compare_delta", self.language),
                )
            )
            rows = ["\t".join(str(part) for part in self.reference_tree.item(item, "values")) for item in self.reference_tree.get_children()]
            value = "\n".join((headings, *rows, "", tr("ui.reference_compare_note", self.language)))
            log_detail = "reference comparison"
        elif selected_tab == str(self.diag_tab):
            if not self.result:
                return
            headings = f"{tr('ui.metric', self.language)}\t{tr('ui.value', self.language)}"
            rows = ["\t".join(str(part) for part in self.diag_tree.item(item, "values")) for item in self.diag_tree.get_children()]
            value = "\n".join((headings, *rows))
            log_detail = "DSP diagnostics"
        elif selected_tab == str(self.debug_tab):
            value = "\n\n".join(
                part
                for part in (
                    self.debug_title_var.get(),
                    self.debug_description_var.get(),
                    self.debug_code.get("1.0", "end-1c"),
                )
                if part
            )
            log_detail = f"developer source block={self.selected_debug_block}"
        elif selected_tab == str(self.changelog_tab):
            value = self.changelog_text.get("1.0", "end-1c")
            log_detail = "changelog"
        else:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(value)
        self.completed_debug_blocks.add("export")
        self.active_debug_block = "export"
        self._draw_debug_diagram()
        self._append_debug_log(f"clipboard copy · {log_detail}")
        self.status_var.set(tr("status.tab_copied", self.language, tab=tab_name))

    def _export_debug_bundle(self) -> None:
        """다른 PC에서 진단·개발을 이어갈 소스, 로그, 이력, 환경 정보를 ZIP으로 묶는다."""
        initial = f"ToneMatchTMP-v{APP_VERSION}-DebugBundle.zip"
        destination = filedialog.asksaveasfilename(title=tr("dialog.debug_bundle_title", self.language), defaultextension=".zip", initialfile=initial, filetypes=(("ZIP", "*.zip"),))
        if not destination:
            return
        source_names = ("app.py", "catalog.py", "debug_info.py", "devices.py", "engine.py", "i18n.py", "recorder.py", "reference_compare.py", "report.py", "separator.py", "spectrum.py", "voicing.py")
        diagnostics = {
            "app_version": APP_VERSION,
            "build_date": BUILD_DATE,
            "python": sys.version,
            "platform": platform.platform(),
            "compute_preference": self.compute_backend_code,
            "separator": self.hardware_status or {"status": "not_probed"},
            "data_root": str(self.data_root),
        }
        try:
            with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
                archive.writestr("diagnostics/runtime.json", json.dumps(diagnostics, ensure_ascii=False, indent=2))
                archive.writestr("history/CHANGELOG_KO.txt", changelog_as_text(CHANGELOG, "ko"))
                archive.writestr("history/CHANGELOG_EN.txt", changelog_as_text(CHANGELOG, "en"))
                archive.writestr("logs/current-session.log", "\n".join(self.debug_log_lines) + "\n")
                for log_path in sorted(self.log_root.glob("*.log")):
                    archive.write(log_path, f"logs/{log_path.name}")
                for name in source_names:
                    try:
                        archive.write(source_file_path(name), f"source/{name}")
                    except FileNotFoundError:
                        continue
            self._append_debug_log(f"debug bundle export · {destination}")
            self.status_var.set(tr("status.debug_bundle_saved", self.language, path=destination))
        except OSError as exc:
            messagebox.showerror(APP_NAME, tr("dialog.save_failed", self.language, error=exc))

    def _on_close(self) -> None:
        """모든 작업에 중지 신호를 보내고 임시 녹음을 정리한 뒤 창을 닫는다."""
        self.closing = True
        self.analysis_cancel_event.set()
        self.record_stop_event.set()
        if self.spectrum_stop_event is not None:
            self.spectrum_stop_event.set()
        self.spectrum_session_id += 1
        self._clear_spectrum_frame_queue()
        self._save_settings()
        for path in self.temporary_recordings:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        capture_root = self.data_root / "captures"
        try:
            if capture_root.is_dir() and not any(capture_root.iterdir()):
                capture_root.rmdir()
        except OSError:
            pass
        self.root.destroy()


def _write_self_test_audio(path: Path, sample_rate: int = 44_100, duration: float = 8.0) -> None:
    """패키지 자체 진단에 사용할 재현 가능한 기타 유사 스테레오 WAV를 만든다."""
    rng = np.random.default_rng(20260902)
    frame_count = int(sample_rate * duration)
    audio = np.zeros(frame_count, dtype=np.float64)
    frequencies = (82.41, 110.0, 146.83, 196.0, 246.94)
    for note_index, onset in enumerate(np.arange(0.25, duration - 0.5, 0.62)):
        start = int(onset * sample_rate)
        length = min(int(0.72 * sample_rate), frame_count - start)
        time_axis = np.arange(length) / sample_rate
        envelope = (1.0 - np.exp(-time_axis / 0.005)) * np.exp(-time_axis / 0.34)
        fundamental = frequencies[note_index % len(frequencies)]
        note = np.zeros(length)
        for harmonic in range(1, 15):
            note += np.sin(2 * np.pi * fundamental * harmonic * time_axis + rng.uniform(0, 2 * np.pi)) / harmonic**1.25
        note += 0.03 * rng.standard_normal(length) * np.exp(-time_axis / 0.012)
        audio[start : start + length] += 0.28 * envelope * np.tanh(note)
    delayed = np.zeros_like(audio)
    delay_samples = int(0.31 * sample_rate)
    delayed[delay_samples:] = audio[:-delay_samples] * 0.18
    left = np.clip(audio + delayed, -0.96, 0.96)
    right = np.clip(audio + np.roll(delayed, int(0.011 * sample_rate)) * 0.92, -0.96, 0.96)
    pcm = np.asarray(np.round(np.column_stack((left, right)) * 32767), dtype="<i2")
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm.tobytes())


def run_self_test(output_path: str | Path) -> int:
    """합성 기타로 오프라인 분석·한영 변환·개발자 소스와 런타임을 검사한다."""
    destination = Path(output_path).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix="tonematch_selftest_") as temp_dir:
            source = Path(temp_dir) / "synthetic-guitar.wav"
            _write_self_test_audio(source)
            result = analyze_file(source, 0, 8, "unknown", "isolated", "frfr", language="ko")
            english = relocalize_result(result, "en")
        sample_axis = np.arange(2048, dtype=np.float64) / 44_100
        live_sample = 0.3 * np.sin(2.0 * np.pi * 440.0 * sample_axis)
        comparison = compare_live_frame(result["reference_spectrum"], analyze_spectrum_frame(live_sample, 44_100))
        reference_compare_ok = (
            len(result["reference_spectrum"]["bands"]) == 6
            and len(comparison["bands"]) == 6
            and bool(np.all(np.isfinite(comparison["delta_db"])))
            and english.get("reference_spectrum") == result["reference_spectrum"]
        )
        debug_sources_ok = all("def " in code_for_block(block["id"]) and "소스 위치를 찾지 못했습니다" not in code_for_block(block["id"]) for block in PIPELINE_BLOCKS)
        separator_status = separator_runtime_status()
        payload = {
            "ok": len(result.get("recipes", [])) == 3 and debug_sources_ok and english.get("language") == "en" and bool(separator_status.get("available")) and reference_compare_ok,
            "app_version": APP_VERSION,
            "ffmpeg_analysis": True,
            "developer_source_blocks": len(PIPELINE_BLOCKS),
            "developer_sources_ok": debug_sources_ok,
            "english_localization": english.get("language") == "en",
            "reference_compare_ok": reference_compare_ok,
            "reference_bands": len(result["reference_spectrum"]["bands"]),
            "separator_runtime": separator_status,
            "top_recipe": result["recipes"][0]["name"],
            "recipe_count": len(result["recipes"]),
            "target_firmware": result["target_firmware"],
        }
        destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0 if payload["ok"] else 2
    except Exception as exc:
        destination.write_text(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2), encoding="utf-8")
        return 1


def main() -> int:
    """자체 진단 인수를 처리하거나 한·영 데스크톱 GUI 이벤트 루프를 시작한다."""
    multiprocessing.freeze_support()
    if "--self-test-output" in sys.argv:
        try:
            index = sys.argv.index("--self-test-output")
            return run_self_test(sys.argv[index + 1])
        except (IndexError, ValueError):
            return 2
    root = tk.Tk()
    ToneMatchApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
