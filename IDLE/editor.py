# 编辑器窗口：新建 / 打开 / 保存 / 运行 TanexScript 源文件

import os
import re
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox

import config
import lexer
import menus
from codeview import CodeView
from window import WindowMixin

_pairs = {
    'parenleft': '()',
    'bracketleft': '[]',
    'braceleft': '{}',
}
_closers = {
    'parenright': ')',
    'bracketright': ']',
    'braceright': '}',
}
_indent_re = re.compile(r'[ \t]*')


class EditorWindow(tk.Toplevel, WindowMixin):
    def __init__(self, app, path = None):
        super().__init__(app.shell)
        self.app = app
        self.path = path
        self._find_dialog = None
        self.title(config.TITLE)
        self.geometry('920x660')
        self.configure(background = config.BG)
        config.apply_icon(self)

        self.view = CodeView(self, show_line_numbers = True,
            on_change = self._on_change, height = 32)
        self.view.pack(fill = 'both', expand = True)
        self.text = self.view.text

        self.status = tk.Label(self, text = '', anchor = 'w',
            background = config.STATUS_BG, foreground = config.STATUS_FG,
            padx = 8, pady = 2, font = config.small())
        self.status.pack(fill = 'x', side = 'bottom')

        menus.build_menubar(app, self, 'editor')
        self._bind_keys()
        self.protocol('WM_DELETE_WINDOW', self.close_window)

        if path and os.path.isfile(path):
            self._load(path)
        else:
            self.view.set_text('')
        self._refresh()

    # -- 文件读写 --

    def _load(self, path):
        try:
            with open(path, 'r', encoding = 'utf-8') as f:
                source = f.read()
        except OSError as exc:
            messagebox.showerror('打开失败', f'无法读取文件:\n{exc}', parent = self)
            source = ''
        except UnicodeDecodeError:
            try:
                with open(path, 'r', encoding = 'gbk') as f:
                    source = f.read()
            except Exception as exc:
                messagebox.showerror('打开失败', f'无法解码文件:\n{exc}', parent = self)
                source = ''
        self.view.set_text(source)
        self.view.set_modified(False)

    def save(self, event = None):
        if self.path is None:
            return self.save_as()
        try:
            with open(self.path, 'w', encoding = 'utf-8') as f:
                f.write(self.view.get_text())
        except OSError as exc:
            messagebox.showerror('保存失败', f'无法写入文件:\n{exc}', parent = self)
            return False
        self.view.set_modified(False)
        self._refresh()
        return True

    def save_as(self, event = None):
        initial = os.path.dirname(self.path) if self.path else self.app.last_dir
        path = filedialog.asksaveasfilename(
            parent = self,
            title = '保存 TanexScript 文件',
            initialdir = initial,
            defaultextension = '.tsuc',
            filetypes = config.FILE_TYPES,
        )
        if not path:
            return False
        self.path = path
        self.app.last_dir = os.path.dirname(path)
        return self.save()

    def ask_save(self) -> bool:
        """返回 False 表示用户取消，调用方应中止后续操作。"""
        if not self.view.is_modified():
            return True
        answer = messagebox.askyesnocancel(config.TITLE,
            f'是否保存对“{self.short_name()}”的修改？', parent = self)
        if answer is None:
            return False
        if answer:
            return self.save()
        return True

    def ensure_saved(self) -> bool:
        if self.path is None or self.view.is_modified():
            return self.ask_save()
        return True

    # -- 标题与状态栏 --

    def short_name(self) -> str:
        return os.path.basename(self.path) if self.path else '未命名'

    def _refresh(self):
        star = '*' if self.view.is_modified() else ''
        self.title(f'{self.short_name()}{star} — {config.TITLE}')
        self._update_status()

    def _on_change(self):
        self._refresh()

    def _update_status(self, event = None):
        try:
            line = self.view.current_line()
            column = self.view.current_column()
            total = int(self.text.index('end-1c').split('.')[0])
        except Exception:
            line, column, total = 1, 1, 1
        name = self.path if self.path else '未命名（尚未保存）'
        flag = '已修改' if self.view.is_modified() else '已保存'
        self.status.configure(
            text = f'行 {line}  列 {column}   共 {total} 行   ·   {name}   ·   {flag}   ·   F5 运行')

    # -- 按键 --

    def _bind_keys(self):
        text = self.text
        text.bind('<Return>', self._on_return)
        text.bind('<Tab>', self._on_tab)
        text.bind('<Shift-Tab>', self._on_shift_tab)
        text.bind('<BackSpace>', self._on_backspace)
        for keysym in _pairs:
            text.bind(f'<KeyPress-{keysym}>', self._on_open_bracket)
        for keysym in _closers:
            text.bind(f'<KeyPress-{keysym}>', self._on_close_bracket)
        text.bind('<KeyRelease>', self._update_status)
        text.bind('<ButtonRelease-1>', self._update_status)
        self.bind('<Control-s>', lambda e: self.save())
        self.bind('<Control-Shift-S>', lambda e: self.save_as())
        self.bind('<Control-w>', lambda e: self.close_window())
        self.bind('<Control-f>', lambda e: self.find())
        self.bind('<Control-a>', lambda e: self.select_all())
        self.bind('<F5>', lambda e: self.run_module())
        self.bind('<Alt-x>', lambda e: self.check_syntax())
        self.bind('<Control-Shift-C>', lambda e: self.compile_tscc())

    def _on_return(self, event = None):
        text = self.text
        index = text.index('insert')
        line = index.split('.')[0]
        before = text.get(f'{line}.0', index)
        indent = _indent_re.match(before).group(0)
        stripped = before.strip()
        if stripped and stripped[-1] in '{([':
            indent += '    '
        if stripped[:1] in (')', ']', '}'):
            if indent.endswith('    '):
                indent = indent[:-4]
            elif indent:
                indent = indent[:-1]
        text.insert('insert', '\n' + indent)
        text.see('insert')
        return 'break'

    def _on_tab(self, event = None):
        text = self.text
        try:
            if text.tag_ranges('sel'):
                self._shift_selection(4)
                return 'break'
        except tk.TclError:
            pass
        text.insert('insert', '    ')
        return 'break'

    def _on_shift_tab(self, event = None):
        self._shift_selection(-4)
        return 'break'

    def _shift_selection(self, delta: int):
        text = self.text
        try:
            start = text.index('sel.first')
            end = text.index('sel.last')
        except tk.TclError:
            return
        first = int(start.split('.')[0])
        last = int(end.split('.')[0])
        if end.split('.')[1] == '0' and last > first:
            last -= 1
        for number in range(first, last + 1):
            head = f'{number}.0'
            content = text.get(head, f'{number}.end')
            if delta > 0:
                text.insert(head, ' ' * delta)
            else:
                strip = len(content) - len(content.lstrip(' '))
                remove = min(4, strip) if strip else min(4, len(content))
                if remove:
                    text.delete(head, f'{number}.{remove}c')

    def _on_backspace(self, event = None):
        text = self.text
        try:
            if text.tag_ranges('sel'):
                return None
        except tk.TclError:
            pass
        index = text.index('insert')
        column = int(index.split('.')[1])
        if column >= 4:
            if text.get(f'{index}-4c', index) == '    ':
                text.delete(f'{index}-4c', index)
                return 'break'
        return None

    def _on_open_bracket(self, event):
        text = self.text
        pair = _pairs.get(event.keysym)
        if not pair:
            return None
        try:
            if text.tag_ranges('sel'):
                text.delete('sel.first', 'sel.last')
        except tk.TclError:
            pass
        text.insert('insert', pair)
        text.mark_set('insert', 'insert-1c')
        return 'break'

    def _on_close_bracket(self, event):
        text = self.text
        char = _closers.get(event.keysym)
        if not char:
            return None
        try:
            if text.tag_ranges('sel'):
                return None
        except tk.TclError:
            pass
        if text.get('insert', 'insert+1c') == char:
            text.mark_set('insert', 'insert+1c')
            return 'break'
        return None

    # -- 运行相关 --

    def run_module(self, event = None):
        if not self.ensure_saved():
            return 'break'
        self.app.run_editor(self)
        return 'break'

    def check_syntax(self, event = None):
        self.app.check_editor(self)
        return 'break'

    def compile_tscc(self, event = None):
        if not self.ensure_saved():
            return 'break'
        if self.path is None:
            return 'break'
        output = self.path.rsplit('.', 1)[0] + '.tscc'
        self.app.compile_editor(self, output)
        return 'break'

    # -- 关闭 --

    def close_window(self, event = None):
        if not self.ask_save():
            return 'break'
        self.app.forget_editor(self)
        try:
            if self._find_dialog is not None:
                self._find_dialog.destroy()
        except Exception:
            pass
        self.destroy()
        return 'break'
