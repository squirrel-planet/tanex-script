# Tanex Script 应用本体（占位）。
# 这是被安装程序打包、安装到用户机器上的「真正应用」。
# 当前为最小可运行窗口，仅用于验证打包/安装链路。
# 把你自己的业务逻辑替换到 main() 里即可，入口与文件名保持不变。

import os
import sys
import tkinter as tk
from tkinter import ttk

app_name = 'Tanex Script'

# 定位 IDLE 同款图标：frozen 时在 _MEIPASS / _internal / exe 同目录；开发态在 assets。
def _app_icon_path():
    candidates = []
    if getattr(sys, 'frozen', False):
        base = getattr(sys, '_MEIPASS', '')
        candidates.append(os.path.join(base, 'tanex-script.ico'))
        candidates.append(os.path.join(base, '_internal', 'tanex-script.ico'))
        ed = os.path.dirname(sys.executable)
        candidates.append(os.path.join(ed, 'tanex-script.ico'))
        candidates.append(os.path.join(ed, '_internal', 'tanex-script.ico'))
    candidates.append(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'assets', 'tanex-script.ico')
    )
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return None

def _apply_window_icon(root):
    p = _app_icon_path()
    if p:
        try:
            root.iconbitmap(p)
        except Exception:
            pass

def main():
    root = tk.Tk()
    _apply_window_icon(root)
    root.title(f'{app_name} · 已安装')
    root.geometry('560x340')
    root.resizable(False, False)

    frm = ttk.Frame(root, padding = 24)
    frm.pack(fill = tk.BOTH, expand = True)

    ttk.Label(frm, text = app_name, font = ('SimHei', 22, 'bold')).pack(pady = (20, 6))
    ttk.Label(
        frm,
        text = 'Tanex Script 已成功安装到本机。',
        font = ('Segoe UI', 11)
    ).pack(
        pady = (0, 4)
    )
    ttk.Label(
        frm,
        text = '这是占位应用本体，请在此处替换为你真实的程序逻辑。',
        foreground = '#64748b',
        wraplength = 420,
        justify = 'center'
    ).pack(
        pady = (0, 18)
    )

    ttk.Separator(frm, orient = tk.HORIZONTAL).pack(fill = tk.X, pady = (0, 14))

    info = ttk.LabelFrame(frm, text = '运行信息', padding = 10)
    info.pack(fill = tk.X)
    ttk.Label(info, text = '可执行文件: TanexScript.exe').pack(anchor = 'w')
    ttk.Label(
        info,
        text = '可通过开始菜单或桌面快捷方式启动。',
        foreground = '#64748b'
    ).pack(
        anchor = 'w',
        pady = (4, 0)
    )

    root.mainloop()

if __name__ == '__main__':
    main()
