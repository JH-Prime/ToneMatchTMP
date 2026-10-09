"""Searchable offline official-model reference; does not activate licenses."""
import tkinter as tk
from tkinter import ttk
from i18n import tr
from quad_cortex import load_catalog, CATALOG_SOURCE


class CatalogWindow(tk.Toplevel):
    def __init__(self, parent, language='ko'):
        """네트워크 연결 없이 검색 가능한 모델·라이선스 목록 창을 만든다."""
        super().__init__(parent)
        if not parent.winfo_viewable():
            self.withdraw()
        self.title(tr('qc.catalog', language))
        self.geometry('940x580')
        self.minsize(640, 400)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        self.rows = load_catalog()['devices']
        self.query = tk.StringVar(self)
        self.count = tk.StringVar(self)
        ko = language != 'en'
        notice = ('공식 목록 2026-10-07 · 검색: 모델/분류/원장비/플러그인\n목록 전체와 추천 대상은 다릅니다. Capture·플러그인·미출시 항목은 기본 추천에서 제외됩니다.' if ko else
                  'Official list · 2026-10-07 · Search model/category/basis/plugin\nInventory is not the recipe pool. Captures, plugins and announced devices are excluded from default recipes.')
        ttk.Label(self, text=notice, wraplength=880).grid(row=0, column=0, sticky='ew', padx=12, pady=10)
        search = ttk.Frame(self)
        search.grid(row=1, column=0, sticky='ew', padx=12)
        search.columnconfigure(1, weight=1)
        ttk.Label(search, text='검색' if ko else 'Search').grid(row=0, column=0, padx=(0, 8))
        ttk.Entry(search, textvariable=self.query).grid(row=0, column=1, sticky='ew')
        ttk.Label(search, textvariable=self.count).grid(row=0, column=2, padx=8)
        frame = ttk.Frame(self)
        frame.grid(row=2, column=0, sticky='nsew', padx=12, pady=10)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        columns = ('kind', 'category', 'name', 'based_on', 'added_in', 'required_plugin')
        self.tree = ttk.Treeview(frame, columns=columns, show='headings')
        headings = ('종류', '분류', '모델', '기반 장비', 'CorOS ≥', '필요 플러그인') if ko else ('Kind', 'Category', 'Model', 'Based on', 'CorOS ≥', 'Required plugin')
        for column, heading, width in zip(columns, headings, (100, 120, 210, 210, 80, 160)):
            self.tree.heading(column, text=heading)
            self.tree.column(column, width=width, minwidth=70)
        self.tree.grid(row=0, column=0, sticky='nsew')
        yscroll = ttk.Scrollbar(frame, orient='vertical', command=self.tree.yview)
        yscroll.grid(row=0, column=1, sticky='ns')
        xscroll = ttk.Scrollbar(frame, orient='horizontal', command=self.tree.xview)
        xscroll.grid(row=1, column=0, sticky='ew')
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.detail = tk.StringVar(self, value=CATALOG_SOURCE)
        ttk.Label(self, textvariable=self.detail, wraplength=880).grid(row=3, column=0, sticky='ew', padx=12, pady=8)
        self.tree.bind('<<TreeviewSelect>>', self._select)
        self.bind('<Escape>', lambda _: self.destroy())
        self.query.trace_add('write', lambda *_: self.refresh())
        self.refresh()

    def refresh(self):
        """검색어에 맞는 모델만 표시하고 전체 대비 개수를 갱신한다."""
        self.tree.delete(*self.tree.get_children())
        query = self.query.get().strip().casefold()
        count = 0
        for row in self.rows:
            if query and query not in ' '.join(str(value or '') for value in row.values()).casefold():
                continue
            values = [row[key] or '—' for key in self.tree['columns']]
            self.tree.insert('', 'end', iid=row['id'], values=values)
            count += 1
        self.count.set(f'{count} / {len(self.rows)}')

    def _select(self, _event):
        """선택 항목의 변경 이력과 공식 출처를 별도로 표시한다."""
        selected = self.tree.selection()
        if selected:
            row = next(row for row in self.rows if row['id'] == selected[0])
            self.detail.set(f"{row['name']} | {row['kind']} | Previous: {row['previous_name'] or '—'} | Updated: {row['updated_in'] or '—'} | Replaces: {row['replaces'] or '—'}\n{CATALOG_SOURCE}")
