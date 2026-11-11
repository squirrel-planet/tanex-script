# TanexScript 文档查看器（IDLE 内嵌）
# 用法（由 idle.py 调用）：
#     DocViewer(toplevel, initial_file=可选路径)
#
# 提供：打开 .md 文档、目录浏览、基础 Markdown 渲染（标题/代码块/行内代码）。
import os
import tkinter as tk
from tkinter import ttk, filedialog, font as tkfont

FONT_FAMILY = 'Consolas'
CODE_FONT = 'Consolas'

# 标题级别 -> 字号（1 最大）
_HEADING_SIZES = {1: 20, 2: 17, 3: 15, 4: 13, 5: 12, 6: 12}


class DocViewer(tk.Frame):
    def __init__(self, master, initial_file=None):
        super().__init__(master)
        self.master = master
        self.master.title('TanexScript 文档查看器')
        self._current = None
        self._docs_root = None
        self.pack(fill='both', expand=True)
        self._build_ui()
        if initial_file and os.path.isfile(initial_file):
            self.load_file(initial_file)
        else:
            self._render_welcome()

    # -- UI 构建 --
    def _build_ui(self):
        bar = tk.Frame(self)
        bar.pack(side='top', fill='x')
        tk.Button(bar, text='打开文档', command=self._open).pack(side='left', padx=4, pady=4)
        tk.Button(bar, text='目录', command=self._show_index).pack(side='left', padx=4, pady=4)
        self._path_var = tk.StringVar(value='')
        tk.Label(bar, textvariable=self._path_var).pack(side='left', padx=8, pady=4)

        body = tk.PanedWindow(self, orient='horizontal', sashrelief='raised')
        body.pack(side='top', fill='both', expand=True)

        self.listbox = tk.Listbox(body, font=(FONT_FAMILY, 11))
        self.listbox.bind('<Double-1>', self._on_pick)
        body.add(self.listbox, width=220)

        text_frame = tk.Frame(body)
        self.text = tk.Text(text_frame, wrap='word', font=(FONT_FAMILY, 11),
                            padx=10, pady=10, undo=True)
        self.text.pack(side='left', fill='both', expand=True)
        scroll = ttk.Scrollbar(text_frame, command=self.text.yview)
        scroll.pack(side='right', fill='y')
        self.text['yscrollcommand'] = scroll.set
        body.add(text_frame, width=600)

        self._configure_tags()

    def _configure_tags(self):
        for level, size in _HEADING_SIZES.items():
            self.text.tag_config(f'h{level}', font=(FONT_FAMILY, size, 'bold'))
        self.text.tag_config('codeblock', font=(CODE_FONT, 11),
                             background='#1e1e1e', foreground='#d4d4d4',
                             wrap='none', lmargin1=8, lmargin2=8)
        self.text.tag_config('inline', font=(CODE_FONT, 11))

    # -- 文档列表 / 目录 --
    def _show_index(self):
        docs_dir = self._docs_dir()
        self.listbox.delete(0, 'end')
        if not docs_dir or not os.path.isdir(docs_dir):
            self.listbox.insert('end', '(未找到文档目录)')
            return
        for root, _dirs, files in os.walk(docs_dir):
            for f in sorted(files):
                if f.endswith('.md'):
                    full = os.path.join(root, f)
                    rel = os.path.relpath(full, docs_dir)
                    self.listbox.insert('end', rel)
        self._docs_root = docs_dir

    def _on_pick(self, _event=None):
        sel = self.listbox.curselection()
        if not sel:
            return
        name = self.listbox.get(sel[0])
        if name.startswith('('):
            return
        path = os.path.join(self._docs_root or '', name)
        if os.path.isfile(path):
            self.load_file(path)

    # -- 打开文件 --
    def _open(self):
        path = filedialog.askopenfilename(
            title='打开 TanexScript 文档',
            filetypes=[('Markdown', '*.md'), ('全部', '*.*')],
            initialdir=self._docs_dir() or os.getcwd())
        if path:
            self.load_file(path)

    def load_file(self, path):
        self._current = path
        self._path_var.set(os.path.basename(path))
        try:
            with open(path, 'r', encoding='utf-8') as fh:
                text = fh.read()
        except Exception as exc:  # noqa: BLE001
            text = f'无法读取文件：{exc}'
        self._render(text)

    # -- Markdown 渲染（轻量）--
    def _render(self, text):
        self.text.configure(state='normal')
        self.text.delete('1.0', 'end')
        lines = text.split('\n')
        in_code = False
        for raw in lines:
            if raw.strip().startswith('```'):
                in_code = not in_code
                continue
            if in_code:
                self.text.insert('end', raw + '\n', 'codeblock')
                continue
            stripped = raw.lstrip()
            for level in range(1, 7):
                prefix = '#' * level
                if stripped.startswith(prefix + ' '):
                    self.text.insert('end', raw + '\n', f'h{level}')
                    break
            else:
                self._insert_inline(raw + '\n')
        self.text.configure(state='disabled')

    def _insert_inline(self, line):
        # 行内代码 `...` 用 mono 标签
        parts = line.split('`')
        for i, part in enumerate(parts):
            if i % 2 == 1:
                self.text.insert('end', part, 'inline')
            else:
                self.text.insert('end', part)
        if not line.endswith('\n'):
            self.text.insert('end', '\n')

    def _render_welcome(self):
        welcome = (
            '# TanexScript 文档查看器\n\n'
            '点击「打开文档」选择 .md 文件，或点击「目录」浏览文档目录。\n\n'
            '支持：标题（#）、代码块（```）、行内代码（`）。'
        )
        self._render(welcome)

    # -- 文档目录推断 --
    def _docs_dir(self):
        # 优先使用项目内文档目录；找不到则回退到当前文件所在目录
        here = os.path.dirname(os.path.abspath(__file__))
        candidates = [
            os.path.join(here, '..', 'Tanex Script文档'),
            os.path.join(here, '..', '..', 'tanex_script', 'doc'),
        ]
        for c in candidates:
            abs_c = os.path.abspath(c)
            if os.path.isdir(abs_c):
                return abs_c
        return os.path.dirname(here)
