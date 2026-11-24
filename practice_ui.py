"""연습 반주 편집 창과 합성·재생 자원 관리."""

from bisect import bisect_right
from dataclasses import dataclass, replace
from pathlib import Path
from queue import Queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import webbrowser

from playback import WavPlayer
from practice_audio import MixSettings, PARTS, render_practice
from practice_chart import (
    CADENCE_TONICS, MAX_CHART_CHARS, STYLES, PracticeProject, build_prompt, cadence_chart, format_chart, load_project,
    parse_chart, save_project, transpose_chart, transpose_key,
)


@dataclass
class _Job:
    kind: str
    project: PracticeProject
    cancel: threading.Event
    result: Queue
    thread: threading.Thread


class _PracticeSession:
    """장치 진입과 상태 반영은 호출자 스레드에서, 파일 작업은 한 작업자에서 수행한다."""

    def __init__(self, can_play, *, render=render_practice, player=WavPlayer):
        self.can_play = can_play
        self._render, self._make_player = render, player
        self.mix = MixSettings()
        self.player = self.audio = self._key = self._loop = None
        self._job = None
        self._retiring = self.closing = False
        self.notice, self.error = '', ''

    @staticmethod
    def _render_key(project):
        return project.bars, project.bpm, project.style, project.count_in

    @property
    def busy(self):
        return self._job is not None

    @property
    def playback_active(self):
        if self._job and self._job.kind == 'play' and not self._job.cancel.is_set():
            return True
        state = self.player.snapshot() if self.player else {}
        return bool(state.get('output_active') or state.get('state') in ('playing', 'draining'))

    def _start_job(self, kind, project, destination=None, part=None):
        cached = self.audio if self._key == self._render_key(project) and not self._retiring else None
        if cached is None and self.player:
            self.player.close()
            self._retiring = True
        cancel = threading.Event()
        results = Queue(maxsize=1)
        mix = self.mix

        def work():
            rendered = None
            exported = False
            try:
                if not cancel.is_set() and cached is None:
                    rendered = self._render(project, cancel_requested=cancel.is_set)
                if not cancel.is_set() and kind == 'export':
                    (cached or rendered).export(destination, mix, part=part, cancel_requested=cancel.is_set)
                    exported = True
                results.put((rendered, None, exported))
            except Exception as exc:
                results.put((rendered, exc, False))

        thread = threading.Thread(target=work, name='ToneMatchPractice', daemon=True)
        thread.start()
        self._job = _Job(kind, project, cancel, results, thread)
        self.notice, self.error = ('rendering' if kind == 'play' else 'exporting'), ''

    def play(self, project):
        """재생 직전과 비동기 준비 완료 시 앱의 장치 사용 조건을 확인한다."""
        if self.busy or self.closing:
            return
        if not self.can_play():
            self.notice, self.error = 'audio_busy', ''
            return
        if self.audio and self._key == self._render_key(project) and not self._retiring:
            self._play_ready(project)
        else:
            self._start_job('play', project)

    def _play_ready(self, project):
        if not self.player:
            audio = self.audio
            self.player = self._make_player('practice.wav', source_factory=lambda: audio.open_mix(lambda: self.mix))
            self._loop = None
        if project.loop != self._loop:
            if project.loop:
                self.player.set_loop(self.audio.start_frame / self.audio.rate, self.audio.frames / self.audio.rate,
                                     pre_roll=True)
            else:
                self.player.set_loop()
            self._loop = project.loop
        self.player.play()
        self.notice, self.error = '', ''

    def export(self, project, destination, *, part=None):
        """내보내기에는 시작 시점 믹서 값의 불변 사본을 사용한다."""
        if not self.busy and not self.closing:
            self._start_job('export', project, destination, part)

    def suspend(self):
        """타 기능이 장치를 쓰기 전에 지연된 재생 요청까지 취소한다."""
        if self._job and self._job.kind == 'play':
            self._job.cancel.set()
        if self.player and not self._retiring and not self.closing:
            state = self.player.snapshot()
            if state['state'] != 'ready':
                self.player.stop()
        return not self.playback_active

    def cancel(self):
        if self._job:
            self._job.cancel.set()
            self.notice = 'cancelling'
        else:
            self.notice = ''
        self.error = ''
        self.suspend()

    def poll(self):
        """완료된 작업의 소유권을 옮기고 취소된 반주를 즉시 회수한다."""
        if self._retiring:
            if self.player and not self.player.wait_closed():
                return
            self.player = None
            if not self.closing:
                self._close_audio()
            self._retiring = False
        job = self._job
        if job is None or job.thread.is_alive():
            return
        self._job = None
        rendered, failure, exported = job.result.get_nowait()
        if job.cancel.is_set() or self.closing or failure:
            if rendered:
                rendered.close()
            if exported:
                self.notice, self.error = 'exported', ''
            elif job.cancel.is_set() or self.closing:
                self.notice, self.error = 'cancelled', ''
            else:
                self.notice, self.error = '', str(failure)
            return
        if rendered:
            self._close_audio()
            self.audio, self._key = rendered, self._render_key(job.project)
        if job.kind == 'export':
            self.notice = 'exported'
        elif not self.can_play():
            self.notice = 'audio_busy'
        else:
            try:
                self._play_ready(job.project)
            except (OSError, ValueError, RuntimeError) as exc:
                self.notice, self.error = '', str(exc)

    def _close_audio(self):
        if self.audio:
            self.audio.close()
        self.audio = self._key = None

    def close(self):
        if not self.closing:
            self.closing = True
            if self._job:
                self._job.cancel.set()
            if self.player:
                self.player.close()
                self._retiring = True

    def wait_closed(self):
        self.poll()
        if self.closing and not self.busy and self.player is None:
            self._close_audio()
            return True
        return False


class PracticeWindow:
    """수동 코드표, 연습 반주와 믹서를 한 창에서 조작한다."""

    _PROVIDERS = {'ChatGPT': 'https://chatgpt.com/', 'Claude': 'https://claude.ai/new'}
    _NOTICES = {
        'audio_busy': ('다른 오디오 작업이 끝난 뒤 재생하세요.', 'Wait for the other audio task before playing.'),
        'rendering': ('반주 준비 중…', 'Preparing accompaniment…'),
        'exporting': ('오디오 저장 중…', 'Exporting audio…'),
        'cancelling': ('취소 중…', 'Cancelling…'),
        'cancelled': ('취소했습니다.', 'Cancelled.'),
        'exported': ('오디오를 저장했습니다.', 'Audio saved.'),
    }

    def __init__(self, parent, language, colors, *, can_play, release):
        self.language, self.colors, self._release = language, colors, release
        self._session = _PracticeSession(can_play)
        self.project = None
        self._after, self._current_bar = None, None
        self._applying = self._closed = False
        self._message = ''
        self._busy_widgets = []
        self.window = window = tk.Toplevel(parent)
        window.title(self._text('연습 반주', 'Practice accompaniment'))
        window.geometry('970x710')
        window.minsize(830, 630)
        window.configure(background=colors['panel_alt'])
        window.protocol('WM_DELETE_WINDOW', self.close)
        window.bind('<Escape>', lambda _event: self.close())
        self._build()
        self._preview()
        self._refresh()

    def _text(self, ko, en):
        return en if self.language == 'en' else ko

    def _label(self, parent, text='', **kwargs):
        return ttk.Label(parent, text=text, style='Alt.TLabel', font=(self.font, 10), **kwargs)

    def _button(self, parent, label, command, *, idle_only=False):
        widget = ttk.Button(parent, text=label, command=command)
        if idle_only:
            self._busy_widgets.append(widget)
        return widget

    def _build(self):
        window = self.window
        self.font = self._text('Malgun Gothic', 'Arial Narrow')
        window.columnconfigure(0, weight=1)
        window.rowconfigure(0, weight=1)
        body = ttk.Frame(window, padding=12, style='Alt.TFrame')
        body.grid(sticky='nsew')
        body.columnconfigure(0, weight=1)
        body.rowconfigure(1, weight=1)
        header = ttk.Frame(body, style='Alt.TFrame')
        header.grid(row=0, column=0, columnspan=2, sticky='ew', pady=(0, 8))
        header.columnconfigure(1, weight=1)
        self.title = tk.StringVar(window)
        self.key = tk.StringVar(window)
        self._label(header, self._text('곡 제목', 'Song title')).grid(row=0, column=0, padx=(0, 6))
        ttk.Entry(header, textvariable=self.title, font=(self.font, 11)).grid(row=0, column=1, sticky='ew')
        self._label(header, self._text('키 (선택)', 'Key (optional)')).grid(row=0, column=2, padx=8)
        ttk.Entry(header, textvariable=self.key, width=15, font=(self.font, 11)).grid(row=0, column=3)

        self.tabs = ttk.Notebook(body)
        self.tabs.grid(row=1, column=0, sticky='nsew', padx=(0, 12))
        self._build_chart_tab()
        self._build_cadence_tab()
        self._build_prompt_tab()
        self._build_mix(body)

        footer = ttk.Frame(body, style='Alt.TFrame')
        footer.grid(row=2, column=0, columnspan=2, sticky='ew', pady=(10, 0))
        self.play_button = self._button(footer, self._text('재생', 'Play'), self._toggle, idle_only=True)
        self.play_button.pack(side='left', padx=(0, 5))
        self.stop_button = self._button(footer, self._text('정지', 'Stop'), self._stop)
        self.stop_button.pack(side='left', padx=(0, 12))
        self.position = tk.StringVar(window)
        self._label(footer, textvariable=self.position).pack(side='left')
        self.status = tk.StringVar(window)
        self._label(body, textvariable=self.status, wraplength=780).grid(
            row=3, column=0, columnspan=2, sticky='ew', pady=(5, 0))
        for variable in (self.title, self.key, self.style, self.bpm, self.count_in, self.loop):
            variable.trace_add('write', self._changed)

    def _text_box(self, parent, height):
        frame = ttk.Frame(parent, style='Alt.TFrame')
        widget = tk.Text(frame, height=height, width=35, wrap='word', undo=True, font=(self.font, 11),
                         background=self.colors['panel'], foreground=self.colors['text'],
                         insertbackground=self.colors['text'], selectbackground=self.colors['border'],
                         relief='flat', padx=8, pady=6)
        scroll = ttk.Scrollbar(frame, orient='vertical', command=widget.yview)
        widget.configure(yscrollcommand=scroll.set)
        widget.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')
        return frame, widget

    def _build_chart_tab(self):
        tab = self.chart_tab = ttk.Frame(self.tabs, padding=8, style='Alt.TFrame')
        self.tabs.add(tab, text=self._text('코드표', 'Chord chart'))
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)
        tab.rowconfigure(3, weight=1)
        self._label(tab, self._text('코드표를 붙여넣거나 수정하세요. | 로 마디를 나눕니다.',
                                   'Paste or edit the chord chart. Separate bars with |.')).grid(row=0, sticky='w')
        editor, self.chart = self._text_box(tab, 6)
        editor.grid(row=1, sticky='nsew', pady=(5, 7))
        self.chart.insert('1.0', '[A]\n| C | Am7 | Dm7 G7 | C/E |')
        self.chart.edit_modified(False)
        self.chart.bind('<<Modified>>', self._chart_changed)

        controls = ttk.Frame(tab, style='Alt.TFrame')
        controls.grid(row=2, sticky='ew', pady=(0, 6))
        for label, action in (
            (self._text('미리보기', 'Preview'), self._preview),
            (self._text('−1 반음', '−1 semitone'), lambda: self._transpose(-1)),
            (self._text('+1 반음', '+1 semitone'), lambda: self._transpose(1)),
            (self._text('저장…', 'Save…'), self._save),
            (self._text('불러오기…', 'Open…'), self._open),
        ):
            self._button(controls, label, action).pack(side='left', padx=(0, 4))

        table_frame = ttk.Frame(tab, style='Alt.TFrame')
        table_frame.grid(row=3, sticky='nsew')
        self.table = ttk.Treeview(table_frame, columns=('number', 'section', 'chords'), show='headings', height=6)
        for name, title, width, stretch in (
            ('number', self._text('마디', 'Bar'), 47, False),
            ('section', self._text('구간', 'Section'), 122, False),
            ('chords', self._text('코드와 박자', 'Chords and beats'), 235, True),
        ):
            self.table.heading(name, text=title)
            self.table.column(name, width=width, stretch=stretch)
        self.table.tag_configure('playing', background=self.colors['accent'], foreground=self.colors['bg'])
        self.table.pack(side='left', fill='both', expand=True)
        scroll = ttk.Scrollbar(table_frame, orient='vertical', command=self.table.yview)
        scroll.pack(side='right', fill='y')
        self.table.configure(yscrollcommand=scroll.set)
        self.table.bind('<Double-1>', self._seek_bar)
        self.table.bind('<Return>', self._seek_bar)

    def _build_cadence_tab(self):
        tab = ttk.Frame(self.tabs, padding=12, style='Alt.TFrame')
        self.tabs.add(tab, text=self._text('2–5–1 반주', '2–5–1 backing'))
        tab.columnconfigure(0, weight=1)
        style = ttk.Style(self.window)
        style.configure('Alt.TRadiobutton', background=self.colors['panel_alt'],
                        foreground=self.colors['text'], font=(self.font, 10))
        style.map('Alt.TRadiobutton', background=[('active', self.colors['panel_alt'])],
                  foreground=[('selected', self.colors['accent'])])
        self.cadence_tonic = tk.StringVar(self.window, value='C')
        self.cadence_minor = tk.BooleanVar(self.window, value=False)
        self.cadence_cycle = tk.BooleanVar(self.window, value=False)

        controls = ttk.Frame(tab, style='Alt.TFrame')
        controls.grid(row=0, sticky='w', pady=(0, 10))
        self._label(controls, self._text('시작 키', 'Starting key')).pack(side='left', padx=(0, 8))
        ttk.Combobox(controls, values=CADENCE_TONICS, textvariable=self.cadence_tonic,
                     state='readonly', width=5, font=(self.font, 10)).pack(side='left')
        ttk.Radiobutton(controls, text=self._text('장조', 'Major'), variable=self.cadence_minor,
                        value=False, style='Alt.TRadiobutton').pack(side='left', padx=(12, 8))
        ttk.Radiobutton(controls, text=self._text('단조', 'Minor'), variable=self.cadence_minor,
                        value=True, style='Alt.TRadiobutton').pack(side='left')

        modes = ttk.Frame(tab, style='Alt.TFrame')
        modes.grid(row=1, sticky='w', pady=(0, 10))
        ttk.Radiobutton(modes, text=self._text('한 키', 'One key'), variable=self.cadence_cycle,
                        value=False, style='Alt.TRadiobutton').pack(side='left', padx=(0, 8))
        ttk.Radiobutton(modes, text=self._text('완전4도씩 12키 순환', '12-key cycle by fourths'),
                        variable=self.cadence_cycle, value=True, style='Alt.TRadiobutton').pack(side='left')
        self._label(tab, self._text('키마다 4마디입니다. 2도와 5도를 한 마디씩, 1도를 두 마디 연주합니다.',
                                   'Four bars per key. One bar each on ii and V, then two on the tonic.'),
                    wraplength=385).grid(row=2, sticky='w', pady=(0, 9))
        self._button(tab, self._text('코드표 만들기', 'Create chord chart'), self._apply_cadence,
                     idle_only=True).grid(row=3, sticky='w')

    def _apply_cadence(self):
        def apply():
            mode = 'Minor' if self.cadence_minor.get() else 'Major'
            key = f'{self.cadence_tonic.get()} {mode}'
            bars = cadence_chart(key, cycle=self.cadence_cycle.get())
            generated = PracticeProject(bars, title=self.title.get(), key=key, bpm=float(self.bpm.get()),
                                        style=self.style.get(), count_in=int(self.count_in.get()),
                                        loop=self.loop.get())
            if self.chart.compare('end-1c', '>', '1.0') and not messagebox.askyesno(
                self._text('2–5–1 코드표', '2–5–1 chord chart'),
                self._text('현재 코드표를 2–5–1 코드표로 바꿀까요?',
                           'Replace the current chart with the 2–5–1 chart?'),
                parent=self.window,
            ):
                return
            self._session.cancel()
            self._show_project(generated, restore_editor=True)
            self.tabs.select(self.chart_tab)
        self._report(apply)

    def _build_prompt_tab(self):
        tab = self.prompt_tab = ttk.Frame(self.tabs, padding=8, style='Alt.TFrame')
        self.tabs.add(tab, text=self._text('AI 질문', 'AI question'))
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(2, weight=1)
        label = self._text(
            '제목과 선택 키로 질문을 만듭니다. AI가 제시한 코드는 차트에 붙여넣고 확인하세요.',
            'Create a question from the title and optional key. Paste the AI suggestion into the chart and check it.',
        )
        self._label(tab, label, wraplength=405).grid(row=0, sticky='w', pady=(0, 8))
        controls = ttk.Frame(tab, style='Alt.TFrame')
        controls.grid(row=1, sticky='ew')
        self._button(controls, self._text('질문 보기', 'Show question'), self._prompt).pack(side='left', padx=(0, 4))
        self._button(controls, self._text('복사', 'Copy'), lambda: self._prompt(copy=True)).pack(side='left', padx=(0, 4))
        for name in self._PROVIDERS:
            self._button(controls, self._text(f'복사 + {name}', f'Copy + {name}'),
                         lambda provider=name: self._prompt(copy=True, provider=provider)).pack(side='left', padx=(0, 4))
        frame, self.prompt = self._text_box(tab, 10)
        frame.grid(row=2, sticky='nsew', pady=(8, 0))
        self.prompt.configure(state='disabled')

    def _build_mix(self, body):
        side = ttk.Frame(body, style='Alt.TFrame')
        side.grid(row=1, column=1, sticky='new')
        side.columnconfigure(1, weight=1)
        self.style = tk.StringVar(self.window, value='Pop')
        self.bpm = tk.StringVar(self.window, value='110')
        self.count_in = tk.StringVar(self.window, value='1')
        self.loop = tk.BooleanVar(self.window, value=True)
        self._label(side, self._text('반주 스타일', 'Style')).grid(row=0, column=0, sticky='w', padx=(0, 7))
        ttk.Combobox(side, values=STYLES, textvariable=self.style, state='readonly', width=15,
                     font=(self.font, 10)).grid(row=0, column=1, columnspan=3, sticky='ew', pady=3)
        self._label(side, 'BPM').grid(row=1, column=0, sticky='w')
        ttk.Entry(side, textvariable=self.bpm, width=8, font=(self.font, 10)).grid(row=1, column=1, sticky='w')
        self._label(side, self._text('카운트인', 'Count-in')).grid(row=2, column=0, sticky='w')
        ttk.Combobox(side, values=('0', '1', '2'), textvariable=self.count_in, state='readonly', width=4,
                     font=(self.font, 10)).grid(row=2, column=1, sticky='w', pady=3)
        self._label(side, self._text('마디', 'bars')).grid(row=2, column=2, sticky='w')
        ttk.Checkbutton(side, text=self._text('반복', 'Loop'), variable=self.loop,
                        style='Alt.TCheckbutton').grid(row=3, column=0, columnspan=4, sticky='w')
        self._label(side, self._text('파트 믹서', 'Part mixer')).grid(row=4, column=0, columnspan=4,
                                                                  sticky='w', pady=(11, 3))
        self.master = tk.DoubleVar(self.window, value=self._session.mix.master)
        self.levels, self.muted = [], []
        self.solo = tk.StringVar(self.window, value='')
        self._label(side, self._text('마스터', 'Master')).grid(row=5, column=0, sticky='w')
        ttk.Scale(side, from_=0, to=1, variable=self.master, command=self._mix_changed).grid(
            row=5, column=1, columnspan=3, sticky='ew', pady=5)
        self._label(side, self._text('뮤트', 'Mute')).grid(row=6, column=2)
        self._label(side, self._text('솔로', 'Solo')).grid(row=6, column=3)
        for index, (part, name) in enumerate(zip(PARTS, (
            self._text('드럼', 'Drums'), self._text('베이스', 'Bass'),
            self._text('코드', 'Chords'), self._text('클릭', 'Click'),
        ))):
            row = index + 7
            gain = tk.DoubleVar(self.window, value=self._session.mix.levels[index])
            mute = tk.BooleanVar(self.window)
            self.levels.append(gain)
            self.muted.append(mute)
            self._label(side, name).grid(row=row, column=0, sticky='w')
            ttk.Scale(side, from_=0, to=1, variable=gain, length=90, command=self._mix_changed).grid(
                row=row, column=1, sticky='ew', padx=(0, 5), pady=6)
            ttk.Checkbutton(side, variable=mute, command=self._mix_changed, style='Alt.TCheckbutton').grid(
                row=row, column=2)
            ttk.Radiobutton(side, variable=self.solo, value=part, command=self._mix_changed).grid(row=row, column=3)
            self._button(side, 'WAV…', lambda selected=part: self._export('wav', selected),
                         idle_only=True).grid(row=row, column=4, padx=(5, 0))
        ttk.Radiobutton(side, variable=self.solo, value='', command=self._mix_changed,
                        text=self._text('솔로 해제', 'No solo')).grid(row=11, column=0, columnspan=4, sticky='w')
        self._label(side, self._text('믹스 내보내기', 'Export mix')).grid(row=12, column=0, columnspan=4,
                                                                      sticky='w', pady=(12, 4))
        for column, ext in enumerate(('wav', 'mp3')):
            self._button(side, ext.upper() + '…', lambda kind=ext: self._export(kind),
                         idle_only=True).grid(row=13, column=column, sticky='w', padx=(0, 4))

    def _mix_changed(self, _value=None):
        if len(self.levels) == len(PARTS):
            self._session.mix = MixSettings(tuple(var.get() for var in self.levels),
                                            tuple(var.get() for var in self.muted),
                                            self.solo.get() or None, self.master.get())

    def _changed(self, *_args):
        if not self._applying:
            self._session.cancel()
            self._message = self._text('편집한 코드표를 확인하세요.', 'Review the edited chart.')

    def _chart_changed(self, _event):
        if self.chart.edit_modified():
            self.chart.edit_modified(False)
            self._changed()

    def _read_project(self):
        # Check the actual text boundary before copying it out of the editor.
        if self.chart.compare('end-1c', '>', f'1.0 + {MAX_CHART_CHARS} chars'):
            raise ValueError(self._text('코드표가 너무 깁니다.', 'The chart is too long.'))
        raw = self.chart.get('1.0', 'end-1c')
        bpm = float(self.bpm.get())
        count_in = int(self.count_in.get())
        return PracticeProject(parse_chart(raw), title=self.title.get(), key=self.key.get(),
                               bpm=bpm, style=self.style.get(), count_in=count_in, loop=self.loop.get())

    def _show_project(self, project, *, restore_editor=False):
        if restore_editor:
            self._applying = True
            try:
                for variable, value in ((self.title, project.title), (self.key, project.key),
                                        (self.bpm, f'{project.bpm:g}'), (self.style, project.style),
                                        (self.count_in, str(project.count_in)), (self.loop, project.loop)):
                    variable.set(value)
                self.chart.delete('1.0', 'end')
                self.chart.insert('1.0', format_chart(project.bars))
                self.chart.edit_reset()
                self.chart.edit_modified(False)
            finally:
                self._applying = False
        self.project, self._current_bar = project, None
        self._message = self._text(f'{len(project.bars)}마디', f'{len(project.bars)} bars')
        previous = self.table.get_children()
        if previous:
            self.table.delete(*previous)
        section = ''
        for index, bar in enumerate(project.bars, 1):
            section = bar.section or section
            chords = '  ·  '.join(f'{name} × {beats}' for name, beats in zip(bar.chords, bar.beats))
            self.table.insert('', 'end', iid=str(index), values=(index, section, chords))
        if project.unresolved_bars:
            bars = ', '.join(map(str, project.unresolved_bars))
            self._message += self._text(f'  |  미확정 마디: {bars}', f'  |  Unresolved bars: {bars}')
        self._session.notice, self._session.error = '', ''

    def _commit(self, *, require_resolved=False, refresh=False):
        project = self._read_project()
        changed = project != self.project
        if changed:
            self._session.cancel()
        if refresh or changed:
            self._show_project(project)
        if require_resolved and project.unresolved_bars:
            raise ValueError(self._text('재생 전에 미확정 코드(?)를 수정하세요.',
                                        'Resolve unknown chords (?) before playing or exporting.'))
        return project

    def _report(self, action):
        try:
            return action()
        except (OSError, ValueError, RuntimeError, tk.TclError) as exc:
            self._session.notice, self._session.error = '', ''
            self._message = str(exc)

    def _preview(self):
        self._report(lambda: self._commit(refresh=True))

    def _transpose(self, step):
        def apply():
            project = self._commit()
            key = transpose_key(project.key, step)
            prefer_flats = len(key) > 1 and key[1] == 'b'
            updated = replace(project, key=key, bars=transpose_chart(project.bars, step, prefer_flats=prefer_flats))
            self._session.cancel()
            self._show_project(updated, restore_editor=True)
        self._report(apply)

    def _prompt(self, *, copy=False, provider=None):
        def prepare():
            question = build_prompt(self.title.get(), self.key.get(), language=self.language)
            self.prompt.configure(state='normal')
            self.prompt.delete('1.0', 'end')
            self.prompt.insert('1.0', question)
            self.prompt.configure(state='disabled')
            if copy:
                self.window.clipboard_clear()
                self.window.clipboard_append(question)
                self._message = self._text('질문을 복사했습니다.', 'Question copied.')
            if provider and not webbrowser.open_new_tab(self._PROVIDERS[provider]):
                self._message = self._text('브라우저를 열지 못했습니다. 복사한 질문을 붙여넣으세요.',
                                           'Could not open the browser. Paste the copied question into your AI tool.')
        self._report(prepare)

    def _save(self):
        project = self._report(self._commit)
        if not project:
            return
        path = filedialog.asksaveasfilename(parent=self.window, defaultextension='.practice.json',
                                           initialfile='ToneMatch-practice.practice.json', filetypes=(('JSON', '*.json'),))
        if path:
            def write():
                save_project(project, Path(path))
                self._message = self._text('연습 프로젝트를 저장했습니다.', 'Practice project saved.')
            self._report(write)

    def _open(self):
        path = filedialog.askopenfilename(parent=self.window, filetypes=(('JSON', '*.json'),))
        if path:
            def read():
                project = load_project(Path(path))
                self._session.cancel()
                self._show_project(project, restore_editor=True)
                self.tabs.select(self.chart_tab)
            self._report(read)

    def _toggle(self):
        def toggle():
            player = self._session.player
            if player and player.snapshot()['state'] in ('playing', 'draining'):
                player.pause()
                return
            self._session.play(self._commit(require_resolved=True))
            self.tabs.select(self.chart_tab)
        self._report(toggle)

    def _stop(self):
        self._session.cancel()

    def _export(self, kind, part=None):
        project = self._report(lambda: self._commit(require_resolved=True))
        if not project:
            return
        label = part or 'mix'
        path = filedialog.asksaveasfilename(parent=self.window, defaultextension=f'.{kind}',
                                           initialfile=f'ToneMatch-{label}.{kind}',
                                           filetypes=((kind.upper(), f'*.{kind}'),))
        if path:
            self._report(lambda: self._session.export(project, Path(path), part=part))

    def _seek_bar(self, _event):
        player, audio = self._session.player, self._session.audio
        selection = self.table.selection()
        if (player and audio and selection and self.project and
                self._session._key == self._session._render_key(self.project) and not self._session._retiring):
            self._report(lambda: player.seek(audio.bar_starts[int(selection[0]) - 1] / audio.rate))

    def _update_cursor(self, snapshot):
        current = None
        label = ''
        audio = self._session.audio
        if audio and snapshot.get('state') in ('playing', 'paused', 'draining'):
            frame = round(snapshot['position'] * audio.rate)
            current = bisect_right(audio.bar_starts, frame)
            label = self._text(f'{current}마디', f'Bar {current}') if current else self._text('카운트인', 'Count-in')
        if current != self._current_bar:
            previous = str(self._current_bar)
            if self.table.exists(previous):
                self.table.item(previous, tags=())
            self._current_bar = current
            if current and self.table.exists(str(current)):
                self.table.item(str(current), tags=('playing',))
                self.table.see(str(current))
        self.position.set(label)

    def _refresh(self):
        self._after = None
        if self._closed:
            return
        session = self._session
        if session.closing:
            if session.wait_closed():
                self._finish_close()
                return
        else:
            session.poll()
            snapshot = session.player.snapshot() if session.player else {}
            self._update_cursor(snapshot)
            for widget in self._busy_widgets:
                widget.configure(state='disabled' if session.busy else 'normal')
            active = snapshot.get('state') in ('playing', 'draining')
            self.play_button.configure(text=self._text('일시 정지', 'Pause') if active else self._text('재생', 'Play'))
            self.stop_button.configure(text=self._text('취소', 'Cancel') if session.busy else self._text('정지', 'Stop'))
            notice = self._text(*self._NOTICES[session.notice]) if session.notice else ''
            self.status.set(session.error or snapshot.get('error') or notice or self._message)
        self._after = self.window.after(70, self._refresh)

    @property
    def playback_active(self):
        return self._session.playback_active

    def suspend(self):
        return self._session.suspend()

    def close(self):
        if not self._closed and not self._session.closing:
            self._session.close()
            self.window.withdraw()
            if self._session.wait_closed():
                self._finish_close()

    def wait_closed(self):
        return self._closed

    def _finish_close(self):
        self._closed = True
        if self._after is not None:
            self.window.after_cancel(self._after)
            self._after = None
        self.window.destroy()
        self._release(self)
