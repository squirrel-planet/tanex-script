# TanexScript Shell 窗口
#
# Shell 不做任何自己的执行实现：它启动官方的 `python -u main.py -s`，
# 把子进程的 stdin / stdout / stderr 接到文本控件上，等价于在终端里跑官方 REPL。
# 语句完整性、续行缩进、静默语句、回显格式、错误输出全部由官方 REPL 决定。

import os
import re
import time
import queue
import tkinter as tk
from tkinter import messagebox

import config
import lexer
import menus
import runner
from codeview import CodeView
from runner import Proc
from window import WindowMixin

_ansi = re.compile(r'\x1b\[[0-9;?]*[a-zA-Z]')
# 官方 REPL 在非交互输入下用 input() 输出提示符：'>>> ' 或 '... ' 加缩进
_prompt_re = re.compile(r'^(>>>|\.\.\.)[ ]*$')
_nav_keys = frozenset({
    'Left', 'Right', 'Up', 'Down', 'Prior', 'Next', 'Home', 'End',
    'Shift_L', 'Shift_R', 'Control_L', 'Control_R', 'Alt_L', 'Alt_R',
    'Caps_Lock', 'Insert', 'Escape', 'Tab',
})
INPUT_MARKER = '输入 > '


class ShellWindow(tk.Tk, WindowMixin):
    def __init__(self, app):
        super().__init__()
        self.app = app
        config.init_fonts(self)
        self.title(config.TITLE + ' — Shell')
        self.geometry('980x640')
        self.configure(background = config.BG)
        config.apply_icon(self)

        self.view = CodeView(self, show_line_numbers = False,
            on_change = self._on_input_change, height = 26)
        self.view.pack(fill = 'both', expand = True)
        self.text = self.view.text

        self.events = queue.Queue()
        self.repl = Proc(runner.repl_command(), cwd = config.ROOT,
            events = self.events, tag = 'shell')
        self.task = None                 # 编译 / 运行 / 检查用的一次性进程
        self.steps = []                  # 待执行的多步命令
        self.temp_files = []             # 任务结束后要删掉的临时文件

        self.state = 'starting'          # starting | prompt | busy | input | task
        self.history = []
        self.hist_index = 0
        self.max_lines = 5000
        self._find_dialog = None
        self._expect_input = False
        self._quiet_since = time.time()

        menus.build_menubar(app, self, 'shell')
        self._bind_keys()
        self.protocol('WM_DELETE_WINDOW', self.app.quit_app)

        self._write_system('TanexScript IDLE — 交互式 Shell\n')
        self._write_system('底层就是官方的 main.py -s：'
            '每条语句以 ; 结尾后立即执行\n')
        self._write_system('Ctrl+C 中断执行，Ctrl+F6 重启 Shell，F5 运行模块\n')
        self._write_system('正在启动运行时…\n')
        self._mark('iomark', 'end', 'right')
        self._mark('cmd_start', 'end-1c', 'left')
        self._mark('input_start', 'end-1c', 'left')
        self._start_repl()
        self.after(30, self._poll)
        self.after(200, lambda: self.text.focus_set())

    # -- 文本输出 --

    def _write(self, text, tag = None):
        self.text.insert('end', text, (tag,) if tag else ())
        self._trim()
        self.text.see('end')

    def _write_system(self, text):
        self._write(text, 'system')

    def _write_out(self, text, error = False):
        text = _ansi.sub('', text)
        self.text.insert('end', text, ('error' if error else 'output',))
        self._quiet_since = time.time()
        self._trim()
        self.text.see('end')

    def _trim(self):
        try:
            lines = int(self.text.index('end-1c').split('.')[0])
        except Exception:
            return
        if lines > self.max_lines:
            self.text.delete('1.0', f'{lines - self.max_lines + 500}.0')

    def _last_line(self) -> str:
        try:
            return self.text.get('end-1c linestart', 'end-1c')
        except tk.TclError:
            return ''

    def _mark(self, name, index = 'end-1c', gravity = 'left'):
        self.text.mark_set(name, index)
        self.text.mark_gravity(name, gravity)

    # -- 提示符 --

    def _emit_prompt(self, prompt_text = '>>> '):
        """自己画一个提示符（子进程已退出、或刚清空窗口时用）。"""
        self.text.insert('end', prompt_text, ('prompt',))
        self._mark('cmd_start', 'end-1c linestart', 'left')
        self._mark('input_start', 'end-1c', 'left')
        self._expect_input = False
        self.state = 'prompt'
        self.text.see('end')

    def _take_prompt(self) -> bool:
        """把子进程输出末尾的提示符改成 prompt 配色，并进入可输入状态。"""
        line = self._last_line()
        if not _prompt_re.match(line):
            return False
        start = self.text.index('end-1c linestart')
        end = self.text.index('end-1c')
        self.text.delete(start, end)
        self.text.insert(start, line, ('prompt',))
        self._mark('cmd_start', start, 'left')
        self._mark('input_start', 'end-1c', 'left')
        self._expect_input = False
        self.state = 'prompt'
        self.text.see('end')
        return True

    def _show_input_marker(self):
        self.text.insert('end', INPUT_MARKER, ('input',))
        self._mark('input_start', 'end-1c', 'left')
        self.state = 'input'
        self.text.see('end')

    def _replace_input(self, lines):
        text = self.text
        start = self.text.index('cmd_start')
        text.delete(start, 'end-1c')
        text.insert(start, '>>> ', ('prompt',))
        self._mark('input_start', 'end-1c', 'left')
        if lines:
            text.insert('end', '\n'.join(lines))
        text.see('end')
        self.view.recolor('input_start', 'end-1c')

    def _recall(self, delta):
        if self.state != 'prompt' or not self.history:
            return 'break'
        index = self.hist_index + delta
        index = max(0, min(len(self.history), index))
        self.hist_index = index
        lines = self.history[index] if index < len(self.history) else []
        self._replace_input(lines)
        return 'break'

    # -- 按键 --

    def _bind_keys(self):
        text = self.text
        text.bind('<Return>', self._on_return)
        text.bind('<KeyPress>', self._guard_key)
        text.bind('<Up>', lambda e: self._recall(-1))
        text.bind('<Down>', lambda e: self._recall(1))
        text.bind('<Alt-p>', lambda e: self._recall(-1))
        text.bind('<Alt-n>', lambda e: self._recall(1))
        text.bind('<Home>', self._on_home)
        text.bind('<Control-c>', self._on_control_c)
        text.bind('<ButtonRelease-1>', self._on_click)
        self.bind('<Control-F6>', lambda e: self.restart_shell())
        self.bind('<F5>', lambda e: self.run_module())
        self.bind('<Control-q>', lambda e: self.app.quit_app())
        self.bind('<Control-o>', lambda e: self.app.open_file())
        self.bind('<Control-n>', lambda e: self.app.new_editor())

    def _guard_key(self, event):
        text = self.text
        sym = event.keysym
        if event.state & 0x0004 or event.state & 0x0008:
            return None                      # 组合键交给各自绑定
        if self.state != 'prompt':
            return 'break'                   # 非提示符状态不接受输入
        try:
            before = text.compare('insert', '<', 'input_start')
        except tk.TclError:
            return None
        if before:
            text.mark_set('insert', 'end')
            if sym in ('BackSpace', 'Delete'):
                return 'break'
        return None

    def _on_click(self, event = None):
        text = self.text
        try:
            selected = bool(text.tag_ranges('sel'))
        except Exception:
            selected = False
        if selected or self.state != 'prompt':
            return
        try:
            if text.compare('insert', '<', 'input_start'):
                text.mark_set('insert', 'end')
        except tk.TclError:
            pass

    def _on_home(self, event = None):
        text = self.text
        try:
            if text.compare('insert', '<', 'input_start'):
                text.mark_set('insert', 'input_start')
            else:
                line = text.index('insert').split('.')[0]
                if text.compare('insert', '>', f'{line}.0 + 4c'):
                    text.mark_set('insert', f'{line}.0 + 4c')
                else:
                    text.mark_set('insert', f'{line}.0')
        except tk.TclError:
            pass
        return 'break'

    def _on_control_c(self, event = None):
        try:
            if self.text.tag_ranges('sel'):
                return None                  # 有选区 → 复制
        except Exception:
            pass
        self.interrupt()
        return 'break'

    def _on_input_change(self):
        if self.state in ('prompt', 'input'):
            try:
                self.view.recolor('input_start', 'end-1c')
            except tk.TclError:
                pass

    # -- 提交 --

    def _on_return(self, event = None):
        if self.state in ('starting', 'busy', 'task'):
            return 'break'
        text = self.text
        raw = text.get('input_start', 'end-1c')
        text.insert('end', '\n')             # 让子进程的输出从新行开始
        self._mark('iomark', 'end', 'right')
        text.see('end')
        if self.state == 'input':
            self.state = 'busy'
            self.repl.write(raw + '\n')
            return 'break'
        self.history.append(raw.split('\n') if '\n' in raw else [raw])
        self.hist_index = len(self.history)
        self.state = 'busy'
        self._expect_input = lexer.has_input_operator(raw)
        self.repl.write(raw + '\n')
        return 'break'

    # -- 子进程事件 --

    def _start_repl(self):
        self.state = 'starting'
        self._expect_input = False
        self._quiet_since = time.time()
        self.repl.kill()
        self.repl = Proc(runner.repl_command(), cwd = config.ROOT,
            events = self.events, tag = 'shell')
        self.repl.start()

    def _poll(self):
        while True:
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break
            try:
                self._handle_event(event)
            except Exception as exc:
                self._write_out(f'IDLE 内部错误: {exc}\n', error = True)
        self._settle()
        self.after(30, self._poll)

    def _handle_event(self, event):
        kind = event.get('type')
        serial = event.get('proc')
        if kind == 'output':
            # 丢掉被 kill 掉的旧进程留下的输出
            if event.get('tag') == 'task':
                if self.task is not None and serial != self.task.serial:
                    return
            elif serial != self.repl.serial:
                return
            self._write_out(event.get('text', ''), event.get('error', False))
            return
        if kind == 'exit':
            if event.get('tag') == 'task':
                if self.task is not None and serial == self.task.serial:
                    self._on_task_exit(event.get('code'))
            elif serial == self.repl.serial:
                self._on_repl_exit(event.get('code'))
            return
        if kind == 'error':
            self._write_out(event.get('text', '') + '\n', error = True)

    def _on_repl_exit(self, code):
        self.repl.proc = None
        if getattr(self, '_closing', False):
            return
        self._write_system(f'Shell 进程已退出（退出码 {code}），正在重新启动…\n')
        self._start_repl()

    def _on_task_exit(self, code):
        self.task = None
        if self.steps:
            self._spawn_next_step()
            return
        if code not in (0, None):
            self._write_system(f'命令结束，退出码 {code}\n')
        self._cleanup_temp()
        if self.repl.alive:
            self._emit_prompt()
        else:
            self._start_repl()

    def _settle(self):
        """队列已空：判断子进程是在等命令、还是程序在 >> 读输入。"""
        if self.state in ('starting', 'busy'):
            if self._take_prompt():
                return
            if self._expect_input \
                    and time.time() - self._quiet_since > 0.2 \
                    and not self._last_line():
                self._show_input_marker()

    # -- 一次性任务：检查 / 编译 / 运行 --

    def _materialize(self, source: str, path: str) -> str:
        """把编辑器缓冲落成真实的 .tsuc 文件（放在源文件同目录，保证相对 import 可用）。"""
        if path and os.path.isfile(path):
            folder = os.path.dirname(os.path.abspath(path))
            base = os.path.splitext(os.path.basename(path))[0]
        else:
            folder = config.ROOT
            base = 'untitled'
        temp = os.path.join(folder, f'{base}._idle_{os.getpid()}.tsuc')
        with open(temp, 'w', encoding = 'utf-8') as handle:
            handle.write(source)
        self.temp_files.append(temp)
        return temp

    def _cleanup_temp(self):
        for path in self.temp_files:
            try:
                os.remove(path)
            except OSError:
                pass
        self.temp_files = []

    def _run_steps(self, steps: list):
        if self.task is not None or self.state == 'task':
            self._write_system('当前还有任务在执行，请稍候或先中断\n')
            return
        self.steps = list(steps)
        self.state = 'task'
        self._spawn_next_step()

    def _spawn_next_step(self):
        if not self.steps:
            return
        args = self.steps.pop(0)
        self.task = Proc(args, cwd = config.ROOT,
            events = self.events, tag = 'task')
        if not self.task.start():
            self.task = None
            self.steps = []
            self._cleanup_temp()
            self._emit_prompt()

    # -- 对外命令 --

    def run_file(self, source: str, path: str, mode: str = 'run',
            output: str | None = None):
        """按官方 main.py 的流程处理一段源码。"""
        real = self._materialize(source, path)
        if mode == 'compile':
            if not output:
                self._write_system('未指定输出文件\n')
                self._cleanup_temp()
                return
            self._write_system(f'编译: {path}\n')
            self._run_steps([runner.compile_command(real, output)])
            return
        if mode == 'check':
            self._write_system(f'检查语法: {path}\n')
            product = os.path.splitext(real)[0] + '.tscc'
            self.temp_files.append(product)
            self._run_steps([runner.compile_command(real, product)])
            return
        self._write_system(f'运行: {path}\n')
        product = os.path.splitext(real)[0] + '.tscc'
        self.temp_files.append(product)
        self._run_steps([
            runner.compile_command(real, product),
            runner.run_command(product),
        ])

    def compile_file(self, source: str, path: str, output: str | None):
        self.run_file(source, path, 'compile', output)

    def check_source(self, source: str, path: str):
        self.run_file(source, path, 'check')

    def run_module(self, event = None):
        editor = self.app.front_editor()
        if editor is None:
            self._write_system('没有可运行的编辑器窗口，请先新建或打开文件\n')
            return 'break'
        editor.run_module()
        return 'break'

    def check_syntax(self, event = None):
        editor = self.app.front_editor()
        if editor is None:
            self._write_system('没有可检查的编辑器窗口\n')
            return 'break'
        editor.check_syntax()
        return 'break'

    def compile_tscc(self, event = None):
        editor = self.app.front_editor()
        if editor is None:
            self._write_system('没有可编译的编辑器窗口\n')
            return 'break'
        editor.compile_tscc()
        return 'break'

    def interrupt(self, event = None):
        if self.state == 'task':
            self._write_system('正在中断任务…\n')
            if self.task is not None:
                self.task.interrupt()
            return 'break'
        if self.state in ('busy', 'input'):
            self._write_system('正在中断执行…\n')
            self.repl.interrupt()
            return 'break'
        self._write_system('当前没有正在执行的代码（Ctrl+F6 可重启 Shell）\n')
        return 'break'

    def restart_shell(self, event = None):
        self._write_system('正在重启 Shell…\n')
        self.steps = []
        if self.task is not None:
            self.task.kill()
            self.task = None
        self._cleanup_temp()
        self.history = []
        self.hist_index = 0
        self._start_repl()
        return 'break'

    def clear_shell(self, event = None):
        self.text.delete('1.0', 'end')
        self._mark('iomark', 'end', 'right')
        self._write_system('TanexScript IDLE — 交互式 Shell（已清空）\n')
        if self.repl.alive:
            self._emit_prompt()
        else:
            self._start_repl()
        return 'break'

    def set_workdir(self, event = None):
        from tkinter import filedialog
        folder = filedialog.askdirectory(initialdir = self.repl.cwd,
            parent = self, title = '选择 Shell 工作目录')
        if not folder:
            return 'break'
        self.repl.cwd = folder
        self._write_system(f'工作目录: {folder}\n')
        self.restart_shell()
        return 'break'

    def close_window(self, event = None):
        self.app.quit_app()
        return 'break'

    def shutdown(self):
        self._closing = True
        if self.task is not None:
            self.task.kill()
            self.task = None
        self.repl.kill()
        self._cleanup_temp()
