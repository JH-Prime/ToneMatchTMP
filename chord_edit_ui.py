"""선택 마디의 원본 이벤트에 대응하는 수동 코드 수정 대화상자."""

import tkinter as tk
from tkinter import ttk

from chord_edits import effective_voicing
from i18n import tr
from voicing import CHORD_INTERVALS, CHORD_SUFFIX, NOTE_NAMES


class ChordEditor(tk.Toplevel):
    """자동 분석 근거와 구분된 코드 기호 수정·원본 복원을 제공한다."""

    def __init__(self, parent, result, indices, language, apply_edit, undo_edit):
        """선택 마디의 이벤트만 나열해 연속 마디의 같은 이벤트를 중복 수정하지 않는다."""
        super().__init__(parent)
        self.withdraw()
        self.transient(parent)
        self.title(tr('edit.title', language))
        self.language = language
        self.result, self.indices = result, indices
        self.apply_edit, self.undo_edit = apply_edit, undo_edit
        self.columnconfigure(0, weight=1)
        body = ttk.Frame(self, padding=16)
        body.grid(sticky='nsew')
        body.columnconfigure(0, weight=1)
        ttk.Label(body, text=tr('edit.notice', language), wraplength=470).grid(row=0, column=0, sticky='w', pady=(0, 10))
        self.events = ttk.Combobox(body, state='readonly', width=48,
                                  values=[self._event_label(index) for index in indices])
        self.events.grid(row=1, column=0, sticky='ew')
        self.events.current(0)
        self.events.bind('<<ComboboxSelected>>', self.select_event)
        self.original_var = tk.StringVar(self)
        ttk.Label(body, textvariable=self.original_var, wraplength=470).grid(row=2, column=0, sticky='w', pady=8)
        self.symbol_var = tk.StringVar(self)
        symbols = ['?'] + [root + CHORD_SUFFIX[key] for root in NOTE_NAMES for key in CHORD_INTERVALS]
        entry = ttk.Combobox(body, textvariable=self.symbol_var, values=symbols, width=30)
        entry.grid(row=3, column=0, sticky='ew')
        entry.bind('<Return>', self.apply)
        ttk.Label(body, text=tr('edit.examples', language), wraplength=470).grid(row=4, column=0, sticky='w', pady=6)
        actions = ttk.Frame(body)
        actions.grid(row=5, column=0, sticky='ew')
        for column, (key, command) in enumerate((('edit.apply', self.apply), ('edit.undo', self.undo),
                                               ('edit.restore', self.restore), ('edit.close', self.destroy))):
            ttk.Button(actions, text=tr(key, language), command=command).grid(row=0, column=column, padx=(0, 5))
        self.status_var = tk.StringVar(self)
        ttk.Label(body, textvariable=self.status_var, wraplength=470).grid(row=6, column=0, sticky='w', pady=8)
        self.bind('<Escape>', lambda event: self.destroy())
        self.select_event()
        self.resizable(False, False)
        if parent.winfo_viewable():
            self.deiconify()
            self.grab_set()
            entry.focus_set()

    def _event_label(self, index):
        """원본 구간 기준 초와 이벤트 번호를 함께 표시한다."""
        event = self.result['chord_voicing']['events'][index]
        offset = self.result.get('source', {}).get('start_seconds', 0)
        return f"#{index + 1} · {offset + event['start_seconds']:.2f}–{offset + event['end_seconds']:.2f}s"

    def select_event(self, _event=None):
        """선택 이벤트의 자동 추정과 현재 수정값을 나란히 구분한다."""
        index = self.indices[self.events.current()]
        original = self.result['chord_voicing']['events'][index]
        self.original_var.set(tr('edit.original', self.language, symbol=original.get('symbol', '?')))
        self.symbol_var.set(effective_voicing(self.result)['events'][index].get('symbol', '?'))
        self.status_var.set('')

    def apply(self, _event=None):
        """기호 검증에 성공했을 때만 앱 상태를 교체하고 오류는 대화상자에 남긴다."""
        try:
            self.result = self.apply_edit(self.indices[self.events.current()], self.symbol_var.get())
            self.status_var.set(tr('edit.applied', self.language))
        except ValueError as exc:
            self.status_var.set(str(exc))

    def restore(self):
        """수정 지도에서 해당 이벤트만 제거해 원래 추정 근거를 복원한다."""
        self.result = self.apply_edit(self.indices[self.events.current()], None)
        self.select_event()

    def undo(self):
        """가장 최근 수정 한 건을 되돌리고 현재 표시를 다시 읽는다."""
        self.result = self.undo_edit()
        self.select_event()
