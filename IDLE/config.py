# IDLE 外观与路径配置

import os
import tkinter as tk
from tkinter import font as tkfont

# IDLE 所在目录与 TanexScript 项目根目录
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# 应用图标：Windows 用 .ico，其他平台退回 png
ICON = os.path.join(HERE, 'tanex-script.ico')
LOGO = os.path.join(HERE, 'logo.png')
_logo_image = None

def apply_icon(window):
    """给窗口设置应用图标；.ico 失败时退回 png 的 iconphoto。"""
    global _logo_image
    if os.name == 'nt':
        try:
            if os.path.isfile(ICON):
                window.iconbitmap(ICON)
                return
        except Exception:
            pass
    try:
        if os.path.isfile(LOGO):
            if _logo_image is None:
                _logo_image = tk.PhotoImage(file = LOGO)
            window.iconphoto(True, _logo_image)
    except Exception:
        pass

FONT_NAME = 'Consolas'
FONT_SIZE = 12
SMALL_SIZE = 10

# 在 Tk 根窗口创建后调用，挑选本机可用的等宽字体
def init_fonts(root):
    global FONT_NAME
    try:
        families = set(tkfont.families(root))
    except Exception:
        return
    for name in ('Cascadia Mono', 'Cascadia Code', 'Consolas',
        'JetBrains Mono', 'Source Code Pro', 'DejaVu Sans Mono',
        'Courier New'):
        if name in families:
            FONT_NAME = name
            return

def mono(size = None):
    return (FONT_NAME, size if size else FONT_SIZE)

def small():
    return (FONT_NAME, SMALL_SIZE)

# 编辑区配色
BG = '#ffffff'
FG = '#1f2328'
GUTTER_BG = '#f6f8fa'
GUTTER_FG = '#a0a6ad'
STATUS_BG = '#f0f3f6'
STATUS_FG = '#5b6570'
INSERT = '#1f2328'
CARET_LINE = '#f5f8fc'

# 语法着色：与 TanexScript 自身的配色一致，但加深以适配浅色背景
SYNTAX = {
    'keyword': '#a626a4',
    'string': '#b76b2a',
    'number': '#4d8f3f',
    'comment': '#8a919a',
    'name': '#2a6fb0',
}

# Shell 文本标签配色
SHELL = {
    'output': '#1f2328',   # 程序输出
    'error': '#c0392b',    # 错误
    'result': '#1155cc',   # 表达式回显值
    'system': '#6a737d',   # IDLE 自身的提示
    'prompt': '#7a1f7a',   # >>> ...
    'input': '#0b6b3a',    # 程序读取的输入
}

TITLE = 'TanexScript IDLE'
FILE_TYPES = [
    ('TanexScript 源文件', '*.tsuc'),
    ('TanexScript 编译产物', '*.tscc'),
    ('TanexScript 库', '*.tscl'),
    ('所有文件', '*.*'),
]
