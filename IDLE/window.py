# 窗口公共行为：编辑命令、查找对话框、关闭流程

import tkinter as tk
from tkinter import messagebox

import config


class WindowMixin:
    """Shell 窗口与编辑器窗口共用的编辑类命令。"""

    def focus_text(self):
        widget = self.focus_get()
        try:
            if isinstance(widget, tk.Text) \
                    and widget.winfo_toplevel() is self.winfo_toplevel():
                return widget
        except Exception:
            pass
        return getattr(self, 'text', None)

    def undo(self, event = None):
        text = self.focus_text()
        try:
            text.edit_undo()
        except Exception:
            pass
        return 'break'

    def redo(self, event = None):
        text = self.focus_text()
        try:
            text.edit_redo()
        except Exception:
            pass
        return 'break'

    def cut(self, event = None):
        text = self.focus_text()
        try:
            text.event_generate('<<Cut>>')
        except Exception:
            pass
        return 'break'

    def copy(self, event = None):
        text = self.focus_text()
        try:
            text.event_generate('<<Copy>>')
        except Exception:
            pass
        return 'break'

    def paste(self, event = None):
        text = self.focus_text()
        try:
            text.event_generate('<<Paste>>')
        except Exception:
            pass
        return 'break'

    def select_all(self, event = None):
        text = self.focus_text()
        if text is None:
            return 'break'
        text.tag_add('sel', '1.0', 'end')
        text.mark_set('insert', 'end')
        return 'break'

    def find(self, event = None):
        text = self.focus_text()
        if text is None:
            return 'break'
        if getattr(self, '_find_dialog', None) is not None:
            try:
                self._find_dialog.lift()
                self._find_dialog.entry.focus_set()
                return 'break'
            except Exception:
                self._find_dialog = None
        self._find_dialog = FindDialog(self, text)
        return 'break'


class FindDialog(tk.Toplevel):
    """简单的查找对话框，在当前窗口中高亮命中内容。"""

    def __init__(self, master, text):
        super().__init__(master)
        self.text = text
        self.title('查找')
        self.transient(master)
        self.resizable(False, False)
        self.configure(background = config.STATUS_BG)
        self.pattern = tk.StringVar()
        text.tag_configure('search', background = '#ffe9a8')

        frame = tk.Frame(self, background = config.STATUS_BG, padx = 8, pady = 8)
        frame.pack(fill = 'both')
        tk.Label(frame, text = '查找:', background = config.STATUS_BG,
            foreground = config.STATUS_FG).pack(side = 'left')
        self.entry = tk.Entry(frame, textvariable = self.pattern, width = 28)
        self.entry.pack(side = 'left', padx = 6)
        self.entry.focus_set()
        self.entry.bind('<Return>', lambda e: self.find_next())
        self.entry.bind('<Escape>', lambda e: self.destroy())
        tk.Button(frame, text = '下一个', command = self.find_next,
            width = 8).pack(side = 'left')
        tk.Button(frame, text = '上一个', command = self.find_prev,
            width = 8).pack(side = 'left', padx = 4)
        tk.Button(frame, text = '关闭', command = self.destroy,
            width = 6).pack(side = 'left')
        self.protocol('WM_DELETE_WINDOW', self.destroy)
        # 有选中内容时预填
        try:
            selected = text.get('sel.first', 'sel.last')
            if selected and '\n' not in selected:
                self.pattern.set(selected)
        except Exception:
            pass

    def _pattern(self) -> str:
        return self.pattern.get().strip()

    def _search(self, backwards = False):
        pattern = self._pattern()
        if not pattern:
            return
        text = self.text
        text.tag_remove('search', '1.0', 'end')
        try:
            if backwards:
                start = text.index('insert')
                index = text.search(pattern, start, backwards = True,
                    stopindex = '1.0', nocase = 0)
            else:
                start = text.index('insert+1c')
                index = text.search(pattern, start, stopindex = 'end', nocase = 0)
                if not index:
                    index = text.search(pattern, '1.0', stopindex = 'end', nocase = 0)
        except tk.TclError:
            return
        if not index:
            self.bell()
            return
        end = f'{index}+{len(pattern)}c'
        text.tag_add('search', index, end)
        text.tag_add('sel', index, end)
        text.mark_set('insert', end)
        text.see(index)

    def find_next(self):
        self._search(False)

    def find_prev(self):
        self._search(True)

    def destroy(self):
        try:
            self.text.tag_remove('search', '1.0', 'end')
        except Exception:
            pass
        try:
            if getattr(self.master, '_find_dialog', None) is self:
                self.master._find_dialog = None
        except Exception:
            pass
        super().destroy()


def confirm_save(window, title = 'TanexScript IDLE') -> bool:
    return messagebox.askyesnocancel(title, '文件已修改，是否保存？')
