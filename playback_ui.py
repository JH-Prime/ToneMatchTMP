"""코드표 하단의 작은 재생 도구막대와 접근 가능한 탐색 제어."""

import tkinter as tk
from tkinter import ttk, messagebox

from i18n import tr


class PlaybackControls(ttk.Frame):
    """작업자 상태를 메인 스레드에서만 읽어 버튼·재생 위치를 갱신한다."""

    def __init__(self, parent, session, language, *, can_play, follow, selected_bar):
        """기존 코드표 스타일을 유지하는 두 줄 제어 막대를 만든다."""
        super().__init__(parent, style='Alt.TFrame', padding=(4, 2))
        self.session, self.language = session, language
        self.can_play, self.follow, self.selected_bar = can_play, follow, selected_bar
        self.columnconfigure(4, weight=1)
        self.play_button = ttk.Button(self, command=self.toggle, width=6, style='Chart.TButton')
        self.play_button.grid(row=0, column=0)
        ttk.Button(self, text=tr('play.stop', language), command=self.stop, width=5,
                   style='Chart.TButton').grid(row=0, column=1)
        self.loop_var = tk.BooleanVar(self, value=bool(session.loop))
        ttk.Checkbutton(self, text=tr('play.loop', language), variable=self.loop_var,
                        command=self.change_loop).grid(row=0, column=2, padx=3)
        self.follow_var = tk.BooleanVar(self, value=True)
        ttk.Checkbutton(self, text=tr('play.follow', language), variable=self.follow_var).grid(row=0, column=3)
        self.time_var = tk.StringVar(self)
        ttk.Label(self, textvariable=self.time_var, width=13, anchor='e', font=('Consolas', 8)).grid(row=0, column=4, sticky='e')
        self.position_var = tk.DoubleVar(self)
        self.scale = ttk.Scale(self, from_=0, to=1, variable=self.position_var)
        self.scale.grid(row=1, column=0, columnspan=5, sticky='ew')
        self.scale.bind('<ButtonPress-1>', self._begin_drag)
        self.scale.bind('<ButtonRelease-1>', self._end_drag)
        self.scale.bind('<KeyRelease>', self._end_drag)
        self.dragging = False
        self.status_var = tk.StringVar(self)
        self.status = ttk.Label(self, textvariable=self.status_var, font=('Segoe UI', 8), width=1, takefocus=True)
        self.status.grid(row=1, column=0, columnspan=5, sticky='ew')
        self.status.bind('<Double-Button-1>', self.show_status)
        self.status.bind('<Return>', self.show_status)
        self.refresh()

    def show_status(self, _event=None):
        """좁은 한 줄에 다 보이지 않는 오류도 키보드로 전체 내용을 확인한다."""
        if self.status_var.get():
            messagebox.showinfo('ToneMatch TMP', self.status_var.get(), parent=self)

    def toggle(self):
        """다른 장치 작업과 겹치지 않을 때만 사용자 재생 요청을 전달한다."""
        if self.can_play():
            self.session.toggle(self.language)
        self.refresh()

    def stop(self):
        """준비·재생을 멈추고 시간 표시를 즉시 갱신한다."""
        self.session.stop()
        self.refresh()

    def change_loop(self):
        """선택 마디가 있을 때에만 그 범위를 반복하고 실패 시 체크를 복원한다."""
        bar = self.selected_bar()
        try:
            if self.loop_var.get() and bar:
                self.session.set_loop(bar['start_seconds'], bar['end_seconds'])
            else:
                self.session.set_loop()
        except ValueError as exc:
            self.session.error = str(exc)
        self.loop_var.set(bool(self.session.loop))

    def _begin_drag(self, _event=None):
        """드래그 중 작업자 시각이 슬라이더를 덮어쓰지 않도록 한다."""
        self.dragging = True

    def _end_drag(self, _event=None):
        """마우스나 키보드 탐색의 최종 위치만 출력 작업자에게 전달한다."""
        self.dragging = False
        self.session.seek(self.position_var.get())
        self.follow(self.position_var.get(), self.follow_var.get())

    def refresh(self):
        """빈 상태·준비·오류와 구간 상대 시간을 장치 접근 없이 표시한다."""
        self.session.poll()
        snapshot = self.session.player.snapshot() if self.session.player else {}
        state = snapshot.get('state', 'ready')
        active = state in ('playing', 'draining')
        key = 'play.cancel' if self.session.preparing else 'play.pause' if active else 'play.play'
        enabled = bool(self.session.source) and self.can_play()
        self.play_button.configure(text=tr(key, self.language), state='normal' if enabled else 'disabled')
        duration = snapshot.get('duration', max(0.0, self.session.source[2] - self.session.source[1]) if self.session.source else 0)
        position = snapshot.get('position', self.session.position)
        self.scale.configure(to=max(0.001, duration), state='normal' if enabled and duration else 'disabled')
        if not self.dragging:
            self.position_var.set(position)
        self.time_var.set(f'{int(position)//60:02}:{int(position)%60:02} / {int(duration)//60:02}:{int(duration)%60:02}')
        error = self.session.error or snapshot.get('error', '')
        message = error or (tr('play.preparing', self.language) if self.session.preparing else '')
        if not self.session.source:
            message = tr('play.no_source', self.language)
        self.status_var.set(message)
        if message:
            self.scale.grid_remove()
            self.status.grid()
        else:
            self.status.grid_remove()
            self.scale.grid()
        if active and not self.dragging:
            self.follow(position, self.follow_var.get())
