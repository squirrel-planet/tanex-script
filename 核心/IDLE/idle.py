# TanexScript IDLE 入口
# 用法:
#     python IDLE/idle.py            # 只打开 Shell
#     python IDLE/idle.py 文件.tsuc  # 同时打开指定文件

import os
import sys
import tkinter as tk
from tkinter import messagebox
import config
from editor import editor_window
from shell import shell_window
from doc_viewer import DocViewer

class idle_app:

    def __init__(self, open_paths = None):
        config.set_app_user_model_id()
        self.editors = []
        self.last_dir = config.root
        self.shell = shell_window(self)
        self.shell.report_callback_exception = self._on_tk_error
        for path in open_paths or []:
            if os.path.isfile(path):
                self.new_editor(os.path.abspath(path))
        self.shell.mainloop()

    # -- 窗口管理 --
    def new_editor(self, path = None):
        window = editor_window(self, path)
        self.editors.append(window)
        if path:
            self.last_dir = os.path.dirname(path)
        return window

    def forget_editor(self, window):
        try:
            self.editors.remove(window)
        except ValueError:
            pass

    def front_editor(self):
        try:
            focus = self.shell.focus_get()
        except Exception:
            focus = None
        for window in self.editors:
            try:
                if focus is not None and focus.winfo_toplevel() is window:
                    return window
            except Exception:
                continue
        return self.editors[-1] if self.editors else None

    def open_file(self, path = None):
        if not path:
            path = tk.filedialog.askopenfilename(
                parent = self.shell,
                title = '打开 TanexScript 文件',
                initialdir = self.last_dir,
                filetypes = config.file_types
            )
        if not path:
            return None
        path = os.path.abspath(path)
        for window in self.editors:
            if window.path and os.path.abspath(window.path) == path:
                window.lift()
                window.focus_force()
                return window
        return self.new_editor(path)

    def raise_editors(self):
        for window in self.editors:
            try:
                window.lift()
            except Exception:
                pass

    def show_windows(self):
        if not self.editors:
            messagebox.showinfo('已打开的编辑器', '当前没有编辑器窗口')
            return
        lines = [f'{i + 1}. {window.short_name()}' for i, window in enumerate(self.editors)]
        messagebox.showinfo('已打开的编辑器', '\n'.join(lines))

    # -- 运行 --
    def run_editor(self, editor):
        source = editor.view.get_text()
        path = editor.path or '<未命名>'
        self.shell.run_file(source, path, 'run')
        self._focus_shell()

    def check_editor(self, editor):
        source = editor.view.get_text()
        path = editor.path or '<未命名>'
        self.shell.check_source(source, path)
        self._focus_shell()

    def compile_editor(self, editor, output):
        source = editor.view.get_text()
        self.shell.compile_file(source, editor.path or '<未命名>', output)
        self._focus_shell()

    def _focus_shell(self):
        try:
            self.shell.lift()
        except Exception:
            pass

    # -- 帮助 --
    def open_docs(self):
        folder = os.path.join(config.root, 'Tanex Script文档')
        if not os.path.isdir(folder):
            messagebox.showinfo('文档', f'未找到文档目录:\n{folder}')
            return
        try:
            if os.name == 'nt':
                os.startfile(folder)
            else:
                import subprocess

                subprocess.Popen(['xdg-open', folder])
        except Exception:
            index = os.path.join(folder, 'index.md')
            if os.path.isfile(index):
                self.new_editor(index)

    # 打开文档查看器窗口
    def open_doc_viewer(self, path = None):
        top = tk.Toplevel(self.shell)
        DocViewer(top, initial_file = path)

    # -- 退出 --
    def quit_app(self):
        for window in list(self.editors):
            if not window.ask_save():
                return
        try:
            self.shell.shutdown()
        except Exception:
            pass
        try:
            self.shell.destroy()
        except Exception:
            pass

    def _on_tk_error(self, exc, value, traceback):
        try:
            messagebox.showerror(
                'IDLE 内部错误',
                f'{exc.__name__}: {value}'
            )
        except Exception:
            pass

        # 打包成窗口程序(--windowed)后 sys.__stderr__ 是 None，写之前先判一下
        stderr = getattr(sys, '__stderr__', None)
        if stderr is not None:
            stderr.write(f'IDLE 内部错误: {exc.__name__}: {value}\n')

def main():
    # 必须在创建窗口之前声明，否则任务栏会把窗口归到 python.exe 组
    config.set_app_user_model_id()
    paths = [arg for arg in sys.argv[1:] if not arg.startswith('-')]
    idle_app(paths)

if __name__ == '__main__':
    main()
