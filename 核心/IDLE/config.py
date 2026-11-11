# IDLE 外观与路径配置

import os
import sys
import tkinter as tk
from tkinter import font as tkfont

# IDLE 所在目录与 TanexScript 项目根目录。
# frozen 时 __file__ 是 PyInstaller 的虚拟路径，真实资源放在安装目录下。
if getattr(sys, 'frozen', False):
    root = os.path.dirname(sys.executable)
    here = os.path.join(root, 'IDLE')
else:
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)

# 应用图标：Windows 用 .ico，其他平台退回 png
icon = os.path.join(here, 'tanex-script.ico')
logo = os.path.join(here, 'logo.png')
app_id = 'TanexScript.IDLE'
_logo_image = None

# 给窗口设置应用图标；.ico 失败时退回 png 的 iconphoto。
# Windows 下同时用 wm_seticon 补一次 32x32 小图标，标题栏与 Alt+Tab
# 都能拿到合适尺寸。
def apply_icon(window):
    global _logo_image
    if os.name == 'nt':
        try:
            if os.path.isfile(icon):
                window.iconbitmap(icon)
                _apply_icon_win32(window)
                return
        except Exception:
            pass
    try:
        if os.path.isfile(logo):
            if _logo_image is None:
                _logo_image = tk.PhotoImage(file = logo)
            window.iconphoto(True, _logo_image)
    except Exception:
        pass

# 显式发 wm_seticon，确保大/小图标都挂上（任务栏与 Alt+Tab 读这两个）。
def _apply_icon_win32(window):
    try:
        import ctypes
        from ctypes import wintypes

        hwnd = int(window.frame(), 0)
        user32 = ctypes.windll.user32
        wm_seticon = 0x0080
        icon_small, icon_big = 0, 1
        lr_loadfromfile = 0x00000010
        image_icon = 1

        # 任务栏用 32x32，Alt+Tab 用 48x48
        for size, which in ((32, icon_small), (48, icon_big)):
            handle = user32.LoadImageW(
                0,
                icon,
                image_icon,
                size,
                size,
                lr_loadfromfile
            )
            if not handle:
                continue
            user32.SendMessageW(hwnd, wm_seticon, which, handle)
    except Exception:
        pass

# 声明进程的 AppUserModelID。
# 不声明的话 Windows 会把窗口归到 python.exe 组，任务栏显示 Python 的图标
# 而不是我们自己的；声明后任务栏才会读窗口自己的图标。
# 必须在创建任何窗口之前调用。
def set_app_user_model_id() -> bool:
    if os.name != 'nt':
        return False
    try:
        import ctypes

        result = ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            app_id
        )
        return result == 0
    except Exception:
        return False

font_name = 'Consolas'
font_size = 12
small_size = 10

# 在 Tk 根窗口创建后调用，挑选本机可用的等宽字体
def init_fonts(root):
    global FONT_NAME
    try:
        families = set(tkfont.families(root))
    except Exception:
        return
    for name in (
        'Cascadia Mono',
        'Cascadia Code',
        'Consolas',
        'JetBrains Mono',
        'Source Code Pro',
        'DejaVu Sans Mono',
        'Courier New'
    ):
        if name in families:
            font_name = name
            return

def mono(size = None):
    return (font_name, size if size else font_size)

def small():
    return (font_name, small_size)

# 编辑区配色
bg = '#ffffff'
fg = '#1f2328'
gutter_bg = '#f6f8fa'
gutter_fg = '#a0a6ad'
status_bg = '#f0f3f6'
status_fg = '#5b6570'
insert = '#1f2328'
caret_line = '#f5f8fc'

# 语法着色：与 TanexScript 自身的配色一致，但加深以适配浅色背景
syntax = {
    'keyword': '#a626a4',
    'string': '#b76b2a',
    'number': '#4d8f3f',
    'comment': '#8a919a',
    'name': '#2a6fb0'
}

# Shell 文本标签配色
# 程序输出
# 错误
# 表达式回显值
# IDLE 自身的提示
# 程序读取的输入
shell = {
    'output': '#1f2328',
    'error': '#c0392b',
    'result': '#1155cc',
    'system': '#6a737d',
    'prompt': '#7a1f7a',
    'input': '#0b6b3a'
}

title = 'TanexScript IDLE'
file_types = [
    ('TanexScript 源文件', '*.tsuc'),
    ('TanexScript 编译产物', '*.tscc'),
    ('TanexScript 库', '*.tscl'),
    ('所有文件', '*.*')
]
