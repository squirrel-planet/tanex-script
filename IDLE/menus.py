# 菜单栏：Shell 窗口与编辑器窗口共用同一套菜单定义

import os
import sys
import tkinter as tk
from tkinter import messagebox

import config

ABOUT_TEXT = (
    'TanexScript IDLE\n'
    '一个模仿 Python IDLE 的 TanexScript 集成开发与学习环境。\n'
    '\n'
    '· Shell 窗口：每条语句以 ; 结尾后立即执行\n'
    '· 编辑器窗口：F5 运行模块，Alt+X 只检查语法\n'
    '· 代码在独立的子进程中运行，随时可以 Ctrl+C 中断\n'
)
SHORTCUTS = (
    'Ctrl+N  新建文件        Ctrl+O  打开文件\n'
    'Ctrl+S  保存            Ctrl+W  关闭窗口\n'
    'Ctrl+Z  撤销            Ctrl+Y  重做\n'
    'Ctrl+F  查找            Ctrl+A  全选\n'
    'F5      运行模块        Alt+X   检查语法\n'
    'Ctrl+C  中断执行（Shell 中）\n'
    'Ctrl+F6 重启 Shell      Ctrl+Q  退出（Shell 中）\n'
    '↑ / ↓   历史命令        Alt+P / Alt+N 上一条 / 下一条\n'
)


def _add(menu, label, command, accelerator = None):
    if accelerator:
        menu.add_command(label = label, command = command,
            accelerator = accelerator)
    else:
        menu.add_command(label = label, command = command)


def build_menubar(app, win, kind):
    """给窗口装上一套菜单；kind 为 'shell' 或 'editor'。"""
    menubar = tk.Menu(win)
    win.configure(menu = menubar)
    is_editor = kind == 'editor'

    # 文件
    file_menu = tk.Menu(menubar, tearoff = 0)
    menubar.add_cascade(label = '文件', menu = file_menu)
    _add(file_menu, '新建文件', app.new_editor, 'Ctrl+N')
    _add(file_menu, '打开…', app.open_file, 'Ctrl+O')
    if is_editor:
        file_menu.add_separator()
        _add(file_menu, '保存', win.save, 'Ctrl+S')
        _add(file_menu, '另存为…', win.save_as)
    file_menu.add_separator()
    _add(file_menu, '关闭窗口', win.close_window, 'Ctrl+W')
    if not is_editor:
        file_menu.add_separator()
        _add(file_menu, '退出', app.quit_app, 'Ctrl+Q')

    # 编辑
    edit_menu = tk.Menu(menubar, tearoff = 0)
    menubar.add_cascade(label = '编辑', menu = edit_menu)
    _add(edit_menu, '撤销', win.undo, 'Ctrl+Z')
    _add(edit_menu, '重做', win.redo, 'Ctrl+Y')
    edit_menu.add_separator()
    _add(edit_menu, '剪切', win.cut, 'Ctrl+X')
    _add(edit_menu, '复制', win.copy, 'Ctrl+C')
    _add(edit_menu, '粘贴', win.paste, 'Ctrl+V')
    _add(edit_menu, '全选', win.select_all, 'Ctrl+A')
    edit_menu.add_separator()
    _add(edit_menu, '查找…', win.find, 'Ctrl+F')

    # 运行
    run_menu = tk.Menu(menubar, tearoff = 0)
    menubar.add_cascade(label = '运行', menu = run_menu)
    _add(run_menu, '运行模块', win.run_module, 'F5')
    _add(run_menu, '检查语法', win.check_syntax, 'Alt+X')
    _add(run_menu, '编译为 .tscc', win.compile_tscc, 'Ctrl+Shift+C')

    # Shell
    if not is_editor:
        shell_menu = tk.Menu(menubar, tearoff = 0)
        menubar.add_cascade(label = 'Shell', menu = shell_menu)
        _add(shell_menu, '中断执行', win.interrupt, 'Ctrl+C')
        _add(shell_menu, '重启 Shell', win.restart_shell, 'Ctrl+F6')
        _add(shell_menu, '清空窗口', win.clear_shell)
        shell_menu.add_separator()
        _add(shell_menu, '设置工作目录…', win.set_workdir)

    # 窗口（只在 Shell 中，列出已打开的编辑器）
    if not is_editor:
        win_menu = tk.Menu(menubar, tearoff = 0)
        menubar.add_cascade(label = '窗口', menu = win_menu)
        _add(win_menu, '列出已打开的编辑器', app.show_windows)
        _add(win_menu, '全部前置', app.raise_editors)

    # 帮助
    help_menu = tk.Menu(menubar, tearoff = 0)
    menubar.add_cascade(label = '帮助', menu = help_menu)
    _add(help_menu, '打开语言文档', app.open_docs)
    _add(help_menu, '快捷键', _shortcuts)
    _add(help_menu, '关于 TanexScript IDLE', _about)
    return menubar


def _about():
    root = None
    try:
        root = tk._default_root
    except Exception:
        root = None
    messagebox.showinfo('关于', ABOUT_TEXT + '\n'
        + f'Python {sys.version.split()[0]}   Tk {tk.TkVersion}\n'
        + f'项目根目录: {config.ROOT}')


def _shortcuts():
    messagebox.showinfo('快捷键', SHORTCUTS)
