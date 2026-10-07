# 子进程管理
#
# IDLE 不再自己实现执行逻辑：Shell 直接启动官方的 `main.py -s`，
# 把它的 stdin / stdout / stderr 接进 Tk 文本控件，等价于在终端里跑官方 REPL。
# 检查语法 / 编译 / 运行模块则分别调用 main.py 的 -c / -r 命令。

import os
import sys
import codecs
import queue
import signal
import threading
import subprocess

from config import ROOT

MAIN = os.path.join(ROOT, 'main.py')


def _popen_kwargs(cwd: str) -> dict:
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    env['PYTHONUTF8'] = '1'
    kwargs = {
        'stdin': subprocess.PIPE,
        'stdout': subprocess.PIPE,
        'stderr': subprocess.PIPE,
        'cwd': cwd,
        'env': env,
    }
    if os.name == 'nt':
        try:
            info = subprocess.STARTUPINFO()
            info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            info.wShowWindow = 0
            kwargs['startupinfo'] = info
        except Exception:
            pass
        # 新建进程组，Ctrl+C 才能送到子进程
        try:
            kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
        except Exception:
            pass
    return kwargs


_serial = [0]


class Proc:
    """一个子进程；stdout / stderr 分流入事件队列，由 Tk 主线程定时取走。

    事件格式：{'type': 'output'|'exit', 'tag': ..., 'proc': 代次, 'text': ...}
    代次用于区分「重启前那个进程」遗留的输出与退出事件。
    """

    def __init__(self, args, cwd = None, events = None, tag = 'shell'):
        _serial[0] += 1
        self.serial = _serial[0]
        self.args = list(args)
        self.cwd = cwd or ROOT
        self.events = events if events is not None else queue.Queue()
        self.tag = tag
        self.proc = None
        self.exit_code = None
        self._closing = False

    # -- 生命周期 --

    def start(self) -> bool:
        self._closing = False
        self.exit_code = None
        try:
            self.proc = subprocess.Popen(self.args, **_popen_kwargs(self.cwd))
        except OSError as exc:
            self.events.put({'type': 'output', 'tag': self.tag,
                'proc': self.serial, 'text': f'无法启动进程: {exc}\n',
                'error': True})
            self.events.put({'type': 'exit', 'tag': self.tag,
                'proc': self.serial, 'code': -1})
            return False
        for stream, is_error in ((self.proc.stdout, False),
                (self.proc.stderr, True)):
            threading.Thread(target = self._read_stream,
                args = (self.proc, stream, is_error), daemon = True).start()
        threading.Thread(target = self._wait_exit,
            args = (self.proc,), daemon = True).start()
        return True

    def kill(self):
        self._closing = True
        proc = self.proc
        self.proc = None
        if proc is None:
            return
        for stream in (proc.stdin, proc.stdout, proc.stderr):
            try:
                if stream:
                    stream.close()
            except Exception:
                pass
        try:
            proc.kill()
        except Exception:
            pass

    def interrupt(self) -> bool:
        proc = self.proc
        if proc is None or proc.poll() is not None:
            return False
        try:
            if os.name == 'nt':
                proc.send_signal(signal.CTRL_C_EVENT)
            else:
                proc.send_signal(signal.SIGINT)
            return True
        except Exception:
            return False

    @property
    def alive(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    # -- 通信 --

    def write(self, text: str) -> bool:
        """往子进程 stdin 写一行（不含换行时调用方自行补）。"""
        proc = self.proc
        if proc is None or proc.stdin is None:
            return False
        try:
            proc.stdin.write(text.encode('utf-8'))
            proc.stdin.flush()
            return True
        except Exception:
            return False

    # -- 读取 --

    def _read_stream(self, proc, stream, is_error: bool):
        decoder = codecs.getincrementaldecoder('utf-8')(errors = 'replace')
        try:
            while True:
                # read1 只做一次底层读，不会为了凑满缓冲区而阻塞，
                # 因此没有换行结尾的提示符也能立刻送达。
                chunk = stream.read1(8192)
                if not chunk:
                    break
                text = decoder.decode(chunk)
                if text:
                    text = text.replace('\r\n', '\n').replace('\r', '\n')
                    self.events.put({'type': 'output', 'tag': self.tag,
                        'proc': self.serial, 'text': text, 'error': is_error})
        except Exception:
            pass
        try:
            stream.close()
        except Exception:
            pass

    def _wait_exit(self, proc):
        """专门等进程真正结束再报退出：流 EOF 时 poll() 可能还没回收完。"""
        try:
            code = proc.wait()
        except Exception:
            code = None
        if proc is self.proc and not self._closing:
            self.exit_code = code
            self.events.put({'type': 'exit', 'tag': self.tag,
                'proc': self.serial, 'code': code})


def repl_command() -> list:
    """官方交互式 Shell：等价于在终端执行 `python -u main.py -s`。"""
    return [sys.executable, '-u', MAIN, '-s']


def compile_command(source_path: str, output_path: str) -> list:
    """编译：main.py -c <输出.tscc> <输入.tsuc>（main.py 的参数顺序如此）。"""
    return [sys.executable, '-u', MAIN, '-c', output_path, source_path]


def run_command(tscc_path: str) -> list:
    """运行编译产物：main.py -r <产物.tscc>。"""
    return [sys.executable, '-u', MAIN, '-r', tscc_path]
