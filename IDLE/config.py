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
APP_ID = 'TanexScript.IDLE'
_logo_image = None

def apply_icon(window):
    """给窗口设置应用图标；.ico 失败时退回 png 的 iconphoto。

    Windows 下同时用 WM_SETICON 补一次 32x32 小图标，标题栏与 Alt+Tab
    都能拿到合适尺寸。
    """
    global _logo_image
    if os.name == 'nt':
        try:
            if os.path.isfile(ICON):
                window.iconbitmap(ICON)
                _apply_icon_win32(window)
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

def _apply_icon_win32(window):
    """显式发 WM_SETICON，确保大/小图标都挂上（任务栏与 Alt+Tab 读这两个）。"""
    try:
        import ctypes
        from ctypes import wintypes
        hwnd = int(window.frame(), 0)
        user32 = ctypes.windll.user32
        WM_SETICON = 0x0080
        ICON_SMALL, ICON_BIG = 0, 1
        LR_LOADFROMFILE = 0x00000010
        IMAGE_ICON = 1
        # 任务栏用 32x32，Alt+Tab 用 48x48
        for size, which in ((32, ICON_SMALL), (48, ICON_BIG)):
            handle = user32.LoadImageW(0, ICON, IMAGE_ICON, size, size,
                LR_LOADFROMFILE)
            if not handle:
                continue
            user32.SendMessageW(hwnd, WM_SETICON, which, handle)
    except Exception:
        pass

def set_app_user_model_id() -> bool:
    """声明进程的 AppUserModelID。

    不声明的话 Windows 会把窗口归到 python.exe 组，任务栏显示 Python 的图标
    而不是我们自己的；声明后任务栏才会读窗口自己的图标。
    必须在创建任何窗口之前调用。
    """
    if os.name != 'nt':
        return False
    try:
        import ctypes
        result = ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            APP_ID)
        return result == 0
    except Exception:
        return False

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
