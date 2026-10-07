# 代码视图：行号栏 + 文本区 + 滚动条，带 TanexScript 语法着色

import re
import tkinter as tk
from tkinter import font as tkfont

import config
from lexer import scan_spans

_kind_tag = {
    'keyword': 'keyword',
    'name': 'name',
    'string': 'string',
    'number_literal': 'number',
    'number': 'number',
    'comment': 'comment',
    'annotation': 'comment',
}
_all_tags = ('keyword', 'name', 'string', 'number', 'comment',
    'error_line', 'output', 'error', 'result', 'system', 'prompt', 'input')


class CodeView(tk.Frame):
    """一个可复用的代码编辑部件。

    show_line_numbers=False 时用于 Shell；on_change 在内容变化时回调。
    """

    def __init__(self, master, show_line_numbers = True, on_change = None,
            width = 80, height = 24, wrap = 'none', **kwargs):
        super().__init__(master, **kwargs)
        self.on_change = on_change
        self.show_line_numbers = show_line_numbers
        self._recolor_pending = False
        self.font = config.mono()
        self.gutter_font = config.small()

        self.text = tk.Text(self,
            width = width,
            height = height,
            undo = True,
            maxundo = 400,
            autoseparators = True,
            wrap = wrap,
            font = self.font,
            background = config.BG,
            foreground = config.FG,
            insertbackground = config.INSERT,
            selectbackground = '#cfe3ff',
            selectforeground = '#000000',
            relief = 'flat',
            borderwidth = 0,
            highlightthickness = 0,
            padx = 8,
            pady = 6,
            spacing1 = 1,
            spacing3 = 1,
            takefocus = True,
        )
        self._configure_tabs()

        self.vbar = tk.Scrollbar(self, orient = 'vertical',
            command = self.text.yview, width = 12)
        self.hbar = tk.Scrollbar(self, orient = 'horizontal',
            command = self.text.xview, width = 12)
        self.text.configure(
            yscrollcommand = self._on_scroll,
            xscrollcommand = self.hbar.set,
        )

        self.gutter = None
        if show_line_numbers:
            self.gutter = tk.Canvas(self, width = 40,
                background = config.GUTTER_BG,
                highlightthickness = 0,
                borderwidth = 0,
                takefocus = False)

        self.grid_rowconfigure(0, weight = 1)
        self.grid_columnconfigure(1, weight = 1)
        column = 0
        if self.gutter is not None:
            self.gutter.grid(row = 0, column = 0, sticky = 'ns')
            column = 1
        self.text.grid(row = 0, column = column, sticky = 'nsew')
        self.vbar.grid(row = 0, column = column + 1, sticky = 'ns')
        self.hbar.grid(row = 1, column = column, sticky = 'ew')

        self._configure_tags()
        self.text.bind('<<Modified>>', self._on_modified)
        self.text.bind('<Configure>', lambda e: self._draw_gutter())
        self.text.bind('<ButtonRelease-1>', lambda e: self._draw_gutter())
        self.text.bind('<KeyRelease>', self._on_key_release)

    # -- 基础配置 --

    def _configure_tabs(self):
        try:
            f = tkfont.Font(font = self.font)
            step = max(8, int(f.measure('0') * 4))
            self.text.configure(tabs = tuple(range(step, step * 21, step)))
            self.text.configure(tabstyle = 'tabular' if tk.TkVersion >= 8.5 else 'tabular')
        except Exception:
            pass

    def _configure_tags(self):
        text = self.text
        for tag in _all_tags:
            text.tag_remove(tag, '1.0', 'end')
        for kind, color in config.SYNTAX.items():
            text.tag_configure(kind, foreground = color)
        for tag, color in config.SHELL.items():
            text.tag_configure(tag, foreground = color)
        text.tag_configure('system', font = (config.FONT_NAME, config.FONT_SIZE, 'italic'))
        text.tag_configure('error_line', background = '#ffe8e8')
        text.tag_configure('search', background = '#ffe9a8')
        text.tag_raise('sel')

    # -- 内容访问 --

    def get_text(self) -> str:
        return self.text.get('1.0', 'end-1c')

    def set_text(self, source: str):
        text = self.text
        text.delete('1.0', 'end')
        text.insert('1.0', source)
        text.edit_modified(False)
        self.recolor()
        self._draw_gutter()
        text.mark_set('insert', '1.0')
        text.see('1.0')

    def clear(self):
        self.text.delete('1.0', 'end')
        self.text.edit_modified(False)
        self._draw_gutter()

    def is_modified(self) -> bool:
        try:
            return bool(self.text.edit_modified())
        except Exception:
            return False

    def set_modified(self, flag: bool):
        self.text.edit_modified(flag)

    def current_line(self) -> int:
        try:
            return int(self.text.index('insert').split('.')[0])
        except Exception:
            return 1

    def current_column(self) -> int:
        try:
            return int(self.text.index('insert').split('.')[1]) + 1
        except Exception:
            return 1

    def goto_line(self, line: int, mark = False):
        text = self.text
        text.tag_remove('error_line', '1.0', 'end')
        index = f'{max(1, line)}.0'
        text.mark_set('insert', index)
        text.see(index)
        if mark:
            text.tag_add('error_line', index, f'{max(1, line)}.end')
        text.focus_set()

    # -- 着色与行号 --

    def _on_modified(self, event = None):
        # 不在这里清零修改标记：编辑器要靠它判断“是否已修改”
        self.schedule_recolor()
        if self.on_change:
            self.on_change()

    def _on_key_release(self, event = None):
        self._draw_gutter()

    def _on_scroll(self, first, last):
        self.vbar.set(first, last)
        self._draw_gutter()

    def schedule_recolor(self):
        if self._recolor_pending:
            return
        self._recolor_pending = True
        self.after_idle(self._do_recolor)

    def _do_recolor(self):
        self._recolor_pending = False
        self.recolor()

    def recolor(self, start = '1.0', end = 'end-1c'):
        """按词法扫描结果着色；默认整篇，也可只刷某一区间（Shell 输入区）。"""
        text = self.text
        for tag in ('keyword', 'name', 'string', 'number', 'comment'):
            text.tag_remove(tag, start, end)
        try:
            source = text.get(start, end)
        except tk.TclError:
            return
        if not source:
            return
        for s, e, kind in scan_spans(source):
            tag = _kind_tag.get(kind)
            if not tag:
                continue
            try:
                text.tag_add(tag, f'{start}+{s}c', f'{start}+{e}c')
            except tk.TclError:
                break

    def _draw_gutter(self):
        if not self.show_line_numbers or self.gutter is None:
            return
        canvas = self.gutter
        text = self.text
        if not text.winfo_ismapped():
            return
        canvas.delete('all')
        try:
            total = int(text.index('end-1c').split('.')[0])
        except Exception:
            total = 1
        need = max(38, 16 + 9 * len(str(total)))
        try:
            if abs(int(canvas.cget('width')) - need) > 2:
                canvas.configure(width = need)
        except Exception:
            pass
        index = text.index('@0,0')
        drawn = 0
        height = text.winfo_height()
        while drawn < 6000:
            info = text.dlineinfo(index)
            if info is None:
                break
            y = info[1]
            if y > height:
                break
            number = str(index).split('.')[0]
            canvas.create_text(need - 8, y, anchor = 'ne',
                text = number, font = self.gutter_font, fill = config.GUTTER_FG)
            index = text.index(index + '+1line')
            drawn += 1
