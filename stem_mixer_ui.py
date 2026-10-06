"""코드표와 분리된 악기 믹서 창. 모델·파일 작업은 MixerSession이 소유한다."""

from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog

from i18n import tr
from separator import SEPARATOR_STEMS


class MixerWindow(tk.Toplevel):
    """6개 추정 분리음의 레벨·모니터·WAV 저장을 명시적으로 조작한다."""

    def __init__(self, parent, session, request, language, colors, can_start):
        """창을 여는 것만으로 추론하거나 오디오 장치를 열지 않는다."""
        super().__init__(parent)
        self.session, self.request, self.language = session, request, language
        self.can_start = can_start
        self.title(tr("mixer.title", language))
        self.geometry("760x540")
        self.minsize(640, 400)
        self.configure(background=colors["panel_alt"])
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<Escape>", lambda event: self.close())
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        canvas = tk.Canvas(self, background=colors["panel_alt"], highlightthickness=0)
        canvas.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        canvas.configure(yscrollcommand=scroll.set)
        content = ttk.Frame(canvas, padding=12, style="Alt.TFrame")
        item = canvas.create_window(0, 0, window=content, anchor="nw")
        content.columnconfigure(1, weight=1)
        content.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(item, width=event.width))
        self.canvas = canvas
        source, start, end, _compute = request
        label = f"{Path(source).name}  |  {start:g}–{end:g}s" if source else tr("error.stem_choose_source", language)
        ttk.Label(content, text=label, style="Alt.TLabel", wraplength=620).grid(
            row=0, column=0, columnspan=6, sticky="w")
        ttk.Label(content, text=tr("mixer.notice", language), style="Alt.TLabel",
                  wraplength=620).grid(row=1, column=0, columnspan=6, sticky="ew", pady=(6, 10))
        self.prepare_button = ttk.Button(content, text=tr("mixer.prepare", language), command=self.prepare)
        self.prepare_button.grid(row=2, column=0, columnspan=3, sticky="w", pady=(0, 8))
        self.cancel_button = ttk.Button(content, text=tr("ui.stem_cancel", language), command=session.cancel)
        self.cancel_button.grid(row=2, column=4, columnspan=2, sticky="e")
        self.channels, self.mix_widgets = {}, []
        self.save_buttons = []
        controls, original = session.state.controls()
        for row, name in enumerate(SEPARATOR_STEMS, 3):
            values = controls[name]
            variables = {"gain": tk.DoubleVar(self, value=values["gain"]),
                         "mute": tk.BooleanVar(self, value=values["mute"]),
                         "solo": tk.BooleanVar(self, value=values["solo"]),
                         "level": tk.StringVar(self, value=f'{values["gain"] * 100:.0f}%')}
            self.channels[name] = variables
            ttk.Label(content, text=tr(f"stem.{name}", language), style="Alt.TLabel").grid(
                row=row, column=0, sticky="w", padx=(0, 10))
            scale = ttk.Scale(content, from_=0, to=2, variable=variables["gain"],
                              command=lambda value: self.change_mix())
            scale.grid(row=row, column=1, sticky="ew", pady=8)
            ttk.Label(content, textvariable=variables["level"], width=5, style="Alt.TLabel").grid(row=row, column=2)
            self.mix_widgets.append(scale)
            for column, flag in ((3, "mute"), (4, "solo")):
                control = ttk.Checkbutton(content, text=tr(f"mixer.{flag}", language),
                                          variable=variables[flag], command=self.change_mix, style="Alt.TCheckbutton")
                control.grid(row=row, column=column, padx=4)
                self.mix_widgets.append(control)
            save = ttk.Button(content, text="WAV…", command=lambda stem=name: self.export(stem))
            save.grid(row=row, column=5)
            self.save_buttons.append(save)
        self.original_var = tk.BooleanVar(self, value=original)
        self.original_button = ttk.Checkbutton(content, text=tr("mixer.original", language),
                                              variable=self.original_var, command=self.change_mix,
                                              style="Alt.TCheckbutton")
        self.original_button.grid(row=9, column=0, columnspan=6, sticky="w", pady=(10, 3))
        self.mix_widgets.append(self.original_button)
        self.ready_var = tk.StringVar(self)
        ttk.Label(content, textvariable=self.ready_var, style="Alt.TLabel", wraplength=620).grid(
            row=10, column=0, columnspan=6, sticky="ew", pady=6)
        footer = ttk.Frame(self, padding=12, style="Alt.TFrame")
        footer.grid(row=1, column=0, columnspan=2, sticky="ew")
        footer.columnconfigure(2, weight=1)
        self.play_button = ttk.Button(footer, text=tr("mixer.play", language), command=self.toggle)
        self.play_button.grid(row=0, column=0, padx=(0, 6))
        self.stop_button = ttk.Button(footer, text=tr("play.stop", language), command=session.stop)
        self.stop_button.grid(row=0, column=1)
        self.position_var = tk.DoubleVar(self, value=0)
        self.seek = ttk.Scale(footer, from_=0, to=1, variable=self.position_var)
        self.seek.grid(row=0, column=2, sticky="ew", padx=8)
        self.seek.bind("<ButtonRelease-1>", self.seek_audio)
        self.seek.bind("<KeyRelease>", self.seek_audio)
        self.export_button = ttk.Button(footer, text=tr("mixer.export", language), command=self.export)
        self.export_button.grid(row=0, column=3)
        self.progress = ttk.Progressbar(footer, maximum=100)
        self.progress.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(10, 4))
        self.status_var = tk.StringVar(self)
        ttk.Label(footer, textvariable=self.status_var, style="Alt.TLabel", wraplength=660).grid(
            row=2, column=0, columnspan=4, sticky="ew")
        self.refresh()

    def prepare(self):
        """명시적인 버튼으로만 선택한 로컬 구간을 분리한다."""
        if not self.can_start():
            self.status_var.set(tr("dialog.wait_for_task", self.language))
            return
        try:
            source, start, end, compute = self.request
            self.session.prepare(source, start, end, compute=compute, language=self.language)
            for variables in self.channels.values():
                variables["gain"].set(1)
                variables["mute"].set(False)
                variables["solo"].set(False)
            self.original_var.set(False)
            self.change_mix()
        except (OSError, ValueError, RuntimeError) as exc:
            self.session.error = str(exc)
        self.refresh()

    def change_mix(self):
        """fader만 바꾸며 분리 모델을 호출하지 않는다."""
        self.session.state.update({
            name: {key: variables[key].get() for key in ("gain", "mute", "solo")}
            for name, variables in self.channels.items()}, original=self.original_var.get())
        for variables in self.channels.values():
            variables["level"].set(f'{variables["gain"].get() * 100:.0f}%')

    def toggle(self):
        """사용자가 누른 재생만 허용하며 다른 오디오 작업과 겹치지 않게 한다."""
        if not self.can_start():
            return
        try:
            self.session.toggle()
        except (OSError, ValueError, RuntimeError) as exc:
            self.session.error = str(exc)
        self.refresh()

    def seek_audio(self, _event=None):
        """스케일의 명시적 마우스·키보드 조작만 재생 위치를 바꾼다."""
        if self.session.player:
            self.session.player.seek(self.position_var.get())

    def export(self, stem=None):
        """기존 파일을 덮어쓰지 않는 새 WAV 경로를 사용자에게 받는다."""
        if self.session.busy or not self.session.bank:
            return
        bank = self.session.bank
        path = filedialog.asksaveasfilename(
            parent=self, title=tr("mixer.export", self.language), defaultextension=".wav",
            initialfile=f"{bank.source.stem}_{stem or 'mix'}.wav", filetypes=(("WAV", "*.wav"),))
        if path:
            try:
                self.session.export(path, stem=stem, language=self.language)
            except (OSError, ValueError, RuntimeError) as exc:
                self.session.error = str(exc)
        self.refresh()

    def refresh(self):
        """메인 앱 타이머에서 상태를 읽고 정지·오류·저장 완료를 표시한다."""
        self.session.poll()
        ready = self.session.bank is not None and not self.session.busy
        self.prepare_button.configure(state="disabled" if self.session.busy else "normal")
        self.cancel_button.configure(state="normal" if self.session.operation else "disabled")
        for widget in self.mix_widgets + self.save_buttons + [self.play_button, self.export_button, self.seek]:
            widget.configure(state="normal" if ready else "disabled")
        self.stop_button.configure(state="normal" if self.session.player else "disabled")
        self.progress.configure(value=self.session.progress)
        if self.session.bank:
            bank = self.session.bank
            self.ready_var.set(tr("mixer.ready", self.language, file=bank.source.name,
                                  seconds=bank.frames / bank.sample_rate, gain=bank.headroom * 100))
        else:
            self.ready_var.set(tr("mixer.empty", self.language))
        player = self.session.player
        snapshot = player.snapshot() if player else {}
        self.play_button.configure(text=tr("mixer.pause" if snapshot.get("state") in ("playing", "draining")
                                           else "mixer.play", self.language))
        if snapshot:
            self.seek.configure(to=snapshot["duration"])
            if self.focus_get() is not self.seek:
                self.position_var.set(snapshot["position"])
        message = self.session.error or snapshot.get("error")
        if not message and self.session.busy:
            message = self.session.message or tr("mixer.working", self.language)
        if not message and self.session.saved_path:
            message = tr("mixer.saved", self.language, file=self.session.saved_path.name)
        self.status_var.set(message or tr("mixer.idle", self.language))

    def close(self):
        """창을 닫으면 진행 작업·재생을 멈추고 준비된 분리음은 앱 종료까지 유지한다."""
        self.session.cancel()
        self.session.stop()
        self.destroy()
