# -*- coding: utf-8 -*-
'\nTanex Script 安装器（真正可安装的器）。\n\n职责：\n  - 启动即申请管理员（UAC）：通过 PyInstaller --uac-admin 清单 + 运行时 runas 兜底。\n  - 把内置的 payload (TanexScript.zip) 解压到 C:/Program Files/Tanex Script。\n  - 可选写入系统 PATH（HKLM）。\n  - 创建「开始菜单」与「桌面」快捷方式（任务栏按需求不自动固定）。\n  - 注册「控制面板-卸载」并自带 uninstall.exe。\n\n构建：pyinstaller --onefile --windowed --uac-admin --add-data "build/TanexScript.zip;payload" tools/installer.py\n'

import os
import sys
import time
import threading
import zipfile
import shutil
import ctypes
import winreg
import subprocess
import traceback
import datetime

# 早期崩溃捕获：必须在其它可能失败的导入之前设置。
# 之前“给管理员就闪退、无日志”说明崩溃发生在 main() 之前，故 excepthook 提前。
def _diag_path():
    return os.path.join(os.environ.get('TEMP', '.'), 'tanex_diag.log')

def diag(msg):
    '细粒度诊断日志：记录每个早期里程碑，用于定位‘一闪而过’的崩溃点。'
    try:
        with open(_diag_path(), 'a', encoding = 'utf-8') as f:
            f.write(
                datetime.datetime.now().isoformat(timespec = 'seconds') + '  ' + msg + '\n'
            )
    except Exception:
        pass

def _crash(exc_type, exc, tb):
    text = ''.join(traceback.format_exception(exc_type, exc, tb))
    diag('CRASH: ' + text)
    try:
        log_path = os.path.join(
            os.environ.get('TEMP', '.'),
            'tanex_installer_error.log'
        )
        with open(log_path, 'w', encoding = 'utf-8') as f:
            f.write(
                'Tanex Installer crash @ ' + datetime.datetime.now().isoformat() + '\n\n' + text
            )
        msg = 'Tanex Script 安装器运行出错：\n\n' + text[-1600:] + f'\n\n（完整日志已保存：{log_path}；诊断：{_diag_path()}）'
    except Exception as e:
        msg = f'安装器运行出错：{exc}\n(且无法写入日志：{e})'
    try:
        ctypes.windll.user32.MessageBoxW(None, msg, 'Tanex Script 安装器出错', 16)
    except Exception:
        pass

sys.excepthook = _crash

# 启动探针：若 %TEMP%\tanex_diag.log 里连 “boot start” 都没有，
# 说明 Python / bootloader 在跑我们的代码之前就崩了（清单 / bootloader 问题）。
diag('=== boot start (Python 解释器已到达模块顶层) ===')
try:
    import tkinter as tk

    diag('import tkinter OK')

    from tkinter import ttk, messagebox, filedialog

    diag('import tkinter 子模块 OK')
except Exception:
    diag('import tkinter 失败')
    raise

# 常量
app_name = 'Tanex Script'
publisher = 'Tanex Script Project'
reg_uninstall = 'Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\TanexScript'
reg_env = 'SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment'
exe_name = 'TanexScript.exe'
uninst_name = 'uninstall.exe'

title_font = 'SimHei'

# 权限 / 资源定位
def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False

def relaunch_as_admin():
    '以管理员身份重启自身。返回 True 表示已发起重启（当前进程应退出）。'
    if '--elevated' in sys.argv:
        return False
    params = '"--elevated" ' + ' '.join((f'"{a}"' for a in sys.argv[1:]))
    ctypes.windll.shell32.ShellExecuteW(
        None,
        'runas',
        sys.executable,
        params,
        None,
        1
    )
    return True

def resource_base():
    'frozen 时指向 PyInstaller 解压目录，否则指向脚本目录。'
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

def load_app_icon():
    '定位 IDLE 同款图标：frozen 时在 _MEIPASS / _internal / exe 同目录；开发态在 assets。'
    candidates = []
    if getattr(sys, 'frozen', False):
        base = getattr(sys, '_MEIPASS', '')
        candidates.append(os.path.join(base, 'tanex-script.ico'))
        candidates.append(os.path.join(base, '_internal', 'tanex-script.ico'))
        ed = os.path.dirname(sys.executable)
        candidates.append(os.path.join(ed, 'tanex-script.ico'))
        candidates.append(os.path.join(ed, '_internal', 'tanex-script.ico'))
    candidates.append(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'tanex-script.ico')
    )
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return None

def apply_window_icon(root):
    p = load_app_icon()
    if p:
        try:
            root.iconbitmap(p)
        except Exception:
            pass

def payload_zip_path():
    p = os.path.join(resource_base(), 'payload', 'TanexScript.zip')
    if os.path.exists(p):
        return p

    # 开发态兜底：从项目 build 目录读取
    alt = os.path.abspath(os.path.join(resource_base(), '..', 'build', 'TanexScript.zip'))
    if os.path.exists(alt):
        return alt
    return None

# 系统操作（均需管理员）
def add_to_system_path(install_dir):
    key = winreg.OpenKey(
        winreg.HKEY_LOCAL_MACHINE,
        reg_env,
        0,
        winreg.KEY_READ | winreg.KEY_WRITE
    )
    try:
        cur = winreg.QueryValueEx(key, 'Path')[0] or ''
    except FileNotFoundError:
        cur = ''
    parts = [p for p in cur.split(';') if p.strip()]
    if install_dir not in parts:
        parts.append(install_dir)
        winreg.SetValueEx(key, 'Path', 0, winreg.REG_EXPAND_SZ, ';'.join(parts))
    winreg.CloseKey(key)
    _broadcast_env()

def remove_from_system_path(install_dir):
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            reg_env,
            0,
            winreg.KEY_READ | winreg.KEY_WRITE
        )
        cur = winreg.QueryValueEx(key, 'Path')[0] or ''
        parts = [p for p in cur.split(';') if p.strip() and os.path.normcase(p.rstrip('\\')) != os.path.normcase(install_dir.rstrip('\\'))]
        winreg.SetValueEx(key, 'Path', 0, winreg.REG_EXPAND_SZ, ';'.join(parts))
        winreg.CloseKey(key)
        _broadcast_env()
    except FileNotFoundError:
        pass

def _broadcast_env():
    hwnd_broadcast = 0xFFFF
    wm_settingchange = 0x001A
    ctypes.windll.user32.SendMessageTimeoutW(
        hwnd_broadcast,
        wm_settingchange,
        0,
        'Environment',
        0x0002,
        5000,
        None
    )

def create_shortcut(target, lnk_path, description = '', workdir = ''):
    '用系统自带 PowerShell + WScript.Shell 创建 .lnk，彻底去掉 pywin32 依赖。'
    os.makedirs(os.path.dirname(lnk_path), exist_ok = True)

    def q(s):
        return "'" + str(s).replace("'", "''") + "'"

    ps = "$ws = New-Object -ComObject WScript.Shell;$s = $ws.CreateShortcut({lnk});$s.TargetPath = {tgt};$s.Description = {desc};$s.WorkingDirectory = {wdir};$s.IconLocation = {tgt} + ',0';$s.Save()".format(
        lnk = q(lnk_path),
        tgt = q(target),
        desc = q(description),
        wdir = q(workdir or os.path.dirname(target))
    )
    subprocess.run(
        ['powershell.exe', '-NoProfile', '-WindowStyle', 'Hidden', '-Command', ps],
        check = True
    )

def start_menu_shortcut_path():
    base = os.path.join(
        os.environ.get('ALLUSERSPROFILE', 'C:\\ProgramData'),
        'Microsoft',
        'Windows',
        'Start Menu',
        'Programs',
        app_name,
        app_name + '.lnk'
    )
    return base

def desktop_shortcut_path():
    base = os.path.join(
        os.environ.get('PUBLIC', 'C:\\Users\\Public'),
        'Desktop',
        app_name + '.lnk'
    )
    return base

def register_uninstall(install_dir, uninstall_exe):
    key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, reg_uninstall)
    try:
        winreg.SetValueEx(key, 'DisplayName', 0, winreg.REG_SZ, app_name)
        winreg.SetValueEx(
            key,
            'UninstallString',
            0,
            winreg.REG_SZ,
            f'"{uninstall_exe}" --uninstall'
        )
        winreg.SetValueEx(
            key,
            'DisplayIcon',
            0,
            winreg.REG_SZ,
            os.path.join(install_dir, exe_name) + ',0'
        )
        winreg.SetValueEx(key, 'InstallLocation', 0, winreg.REG_SZ, install_dir)
        winreg.SetValueEx(key, 'Publisher', 0, winreg.REG_SZ, publisher)
        winreg.SetValueEx(key, 'DisplayVersion', 0, winreg.REG_SZ, '1.0.0')
        winreg.SetValueEx(key, 'NoModify', 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, 'NoRepair', 0, winreg.REG_DWORD, 1)
    finally:
        winreg.CloseKey(key)

def unregister_uninstall():
    try:
        winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, reg_uninstall)
    except FileNotFoundError:
        pass

def get_install_location():
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_uninstall)
        val = winreg.QueryValueEx(key, 'InstallLocation')[0]
        winreg.CloseKey(key)
        return val
    except FileNotFoundError:
        return os.path.join(
            os.environ.get('ProgramFiles', 'C:\\Program Files'),
            app_name
        )

# 卸载逻辑
def handle_uninstall():
    if '--uninstall-stage2' in sys.argv:
        _uninstall_stage2()
        return

    # 阶段一：把自身复制到临时目录并以 stage2 运行，避免删除正在运行的文件
    try:
        tmp = os.path.join(
            os.environ.get('TEMP', 'C:\\Windows\\Temp'),
            f'tanex_uninstall_{os.getpid()}.exe'
        )
        shutil.copyfile(sys.executable, tmp)
        ctypes.windll.shell32.ShellExecuteW(
            None,
            'runas',
            tmp,
            '--uninstall-stage2',
            None,
            0
        )
    except Exception as e:
        messagebox.showerror('卸载失败', f'无法启动卸载程序：{e}')

def _uninstall_stage2():
    install_dir = get_install_location()
    try:
        remove_from_system_path(install_dir)
    except Exception as e:
        print('PATH 清理失败:', e)
    try:
        for lnk in (start_menu_shortcut_path(), desktop_shortcut_path()):
            if os.path.exists(lnk):
                os.remove(lnk)
            d = os.path.dirname(lnk)
            try:
                if d.endswith(app_name) and (not os.listdir(d)):
                    os.rmdir(d)
            except OSError:
                pass
    except Exception as e:
        print('快捷方式清理失败:', e)
    unregister_uninstall()
    try:
        if os.path.isdir(install_dir):
            shutil.rmtree(install_dir, ignore_errors = True)
    except Exception as e:
        print('目录清理失败:', e)
    messagebox.showinfo(app_name, 'Tanex Script 已卸载。')

# 安装界面（保留三步向导，进度改为真实执行）
class tanex_installer_ui:

    def __init__(self, root):
        self.root = root
        self.root.title(f'{app_name} 安装程序')
        self.root.geometry('820x540')
        self.root.resizable(False, False)

        self.current_step = 1
        self.is_installing = False
        self.install_thread = None

        self.install_path = tk.StringVar(
            value = os.path.join(
                os.environ.get('ProgramFiles', 'C:\\Program Files'),
                app_name
            )
        )
        self.add_to_path = tk.BooleanVar(value = True)
        self.create_startmenu = tk.BooleanVar(value = True)
        self.create_desktop = tk.BooleanVar(value = True)

        style = ttk.Style()
        style.theme_use('vista')
        style.configure(
            'Accent.Horizontal.TProgressbar',
            troughcolor = '#e2e8f0',
            background = '#3776ab',
            thickness = 14
        )

        self.build_title_bar()
        self.build_main_layout()
        self.root.protocol('WM_DELETE_WINDOW', self.on_close)

    def _load_logo_image(self, size = 26):
        '用 TanexScript 图标(tanex-script.ico)生成标题栏小图标；失败则回退 None。'
        try:
            from PIL import Image, ImageTk

            p = load_app_icon()
            if not p:
                return None
            im = Image.open(p)

            # 选 ICO 中尺寸最大的那一帧再缩放，更清晰
            try:
                frames, idx = [], 0
                while True:
                    frames.append(im.size)
                    idx += 1
                    try:
                        im.seek(idx)
                    except EOFError:
                        break
                if frames:
                    best = max(
                        range(len(frames)),
                        key = lambda i: frames[i][0] * frames[i][1]
                    )
                    im.seek(best)
            except Exception:
                im.seek(0)
            im = im.convert('RGBA').resize((size, size), Image.LANCZOS)
            return ImageTk.PhotoImage(im)
        except Exception:
            return None

    # 标题栏
    def build_title_bar(self):
        bar = ttk.Frame(self.root)
        bar.pack(fill = tk.X, side = tk.TOP)
        self.logo_img = self._load_logo_image(26)
        if self.logo_img is not None:
            logo = tk.Label(bar, image = self.logo_img, bg = '#3776ab')
        else:
            logo = tk.Label(
                bar,
                text = 'Tx',
                bg = '#3776ab',
                fg = 'white',
                font = (title_font, 12, 'bold'),
                width = 3
            )
        logo.pack(side = tk.LEFT, padx = (14, 10), pady = 8)
        ttk.Label(
            bar,
            text = f'{app_name} 安装程序',
            font = (title_font, 13, 'bold')
        ).pack(
            side = tk.LEFT
        )
        ttk.Label(
            bar,
            text = '版本 1.0.0 (64-bit)',
            foreground = '#64748b'
        ).pack(
            side = tk.LEFT,
            padx = (10, 0)
        )
        ttk.Separator(self.root, orient = tk.HORIZONTAL).pack(fill = tk.X)

    # 主布局
    def build_main_layout(self):
        main = ttk.Frame(self.root)
        main.pack(fill = tk.BOTH, expand = True)
        self.sidebar = ttk.Frame(main, width = 200)
        self.sidebar.pack(side = tk.LEFT, fill = tk.Y)
        self.sidebar.pack_propagate(False)
        ttk.Separator(main, orient = tk.VERTICAL).pack(side = tk.LEFT, fill = tk.Y)
        self.content = ttk.Frame(main)
        self.content.pack(side = tk.LEFT, fill = tk.BOTH, expand = True)
        self.build_sidebar()
        self.build_content_pages()

    def build_sidebar(self):
        f = ttk.Frame(self.sidebar)
        f.pack(fill = tk.X, padx = 10, pady = (24, 0))
        self.step_labels = []
        for title, desc in [
            ('安装选项', '选择组件和路径'),
            ('正在安装', '复制文件与配置'),
            ('安装完成', '准备就绪')
        ]:
            item = ttk.Frame(f)
            item.pack(fill = tk.X, pady = (0, 14))
            t = ttk.Label(item, text = title, font = (title_font, 12, 'bold'))
            t.pack(fill = tk.X, padx = 6, pady = (4, 0))
            d = ttk.Label(item, text = desc, foreground = '#94a3b8')
            d.pack(fill = tk.X, padx = 6, pady = (0, 4))
            self.step_labels.append((t, d))
        footer = ttk.Frame(self.sidebar)
        footer.pack(side = tk.BOTTOM, fill = tk.X, padx = 14, pady = 14)
        ttk.Separator(footer, orient = tk.HORIZONTAL).pack(fill = tk.X, pady = (0, 10))
        ttk.Label(footer, text = publisher, foreground = '#94a3b8').pack(anchor = 'w')
        self.update_sidebar(1)

    def update_sidebar(self, cur):
        for i, (t, d) in enumerate(self.step_labels):
            n = i + 1
            if n < cur:
                t.config(foreground = '#27c93f')
                d.config(foreground = '#94a3b8')
            elif n == cur:
                t.config(foreground = '#3776ab')
                d.config(foreground = '#475569')
            else:
                t.config(foreground = '#94a3b8')
                d.config(foreground = '#cbd5e1')

    # 内容页
    def build_content_pages(self):
        self.page_container = ttk.Frame(self.content)
        self.page_container.pack(fill = tk.BOTH, expand = True, padx = 24, pady = 16)
        self.page1 = ttk.Frame(self.page_container)
        self.page2 = ttk.Frame(self.page_container)
        self.page3 = ttk.Frame(self.page_container)
        self.build_page1()
        self.build_page2()
        self.build_page3()
        self.show_page(1)

    def show_page(self, step):
        for p in (self.page1, self.page2, self.page3):
            p.pack_forget()
        {1: self.page1, 2: self.page2, 3: self.page3}[step].pack(fill = tk.BOTH, expand = True)
        self.current_step = step
        self.update_sidebar(step)

    # 页1：选项
    def build_page1(self):
        h = ttk.Frame(self.page1)
        h.pack(fill = tk.X, pady = (0, 12))
        ttk.Label(
            h,
            text = f'欢迎安装 {app_name}',
            font = (title_font, 16, 'bold')
        ).pack(
            fill = tk.X
        )
        ttk.Label(
            h,
            text = '选择安装选项，然后点击“下一步”继续。',
            foreground = '#475569'
        ).pack(
            fill = tk.X,
            pady = (4, 0)
        )

        og = ttk.LabelFrame(self.page1, text = '安装选项', padding = 10)
        og.pack(fill = tk.X, pady = (0, 12))
        ttk.Checkbutton(
            og,
            text = '添加到系统 PATH 环境变量（推荐）',
            variable = self.add_to_path
        ).pack(
            anchor = 'w',
            pady = 3
        )
        ttk.Checkbutton(
            og,
            text = '创建开始菜单快捷方式（推荐）',
            variable = self.create_startmenu
        ).pack(
            anchor = 'w',
            pady = 3
        )
        ttk.Checkbutton(
            og,
            text = '创建桌面快捷方式（可选）',
            variable = self.create_desktop
        ).pack(
            anchor = 'w',
            pady = 3
        )

        pg = ttk.LabelFrame(self.page1, text = '安装位置', padding = 10)
        pg.pack(fill = tk.X, pady = (0, 12))
        ttk.Label(pg, text = '目标文件夹：').pack(anchor = 'w', pady = (0, 4))
        row = ttk.Frame(pg)
        row.pack(fill = tk.X)
        self.path_entry = ttk.Entry(row, textvariable = self.install_path)
        self.path_entry.pack(side = tk.LEFT, fill = tk.X, expand = True)
        ttk.Button(
            row,
            text = '浏览...',
            command = self.browse_folder,
            width = 10
        ).pack(
            side = tk.LEFT,
            padx = (8, 0)
        )
        ttk.Label(
            pg,
            text = '需要管理员权限才能写入 Program Files 与系统 PATH。',
            foreground = '#94a3b8'
        ).pack(
            anchor = 'w',
            pady = (6, 0)
        )

        bb = ttk.Frame(self.page1)
        bb.pack(fill = tk.X, side = tk.BOTTOM, pady = (12, 0))
        ttk.Separator(bb, orient = tk.HORIZONTAL).pack(fill = tk.X, pady = (0, 10))
        bi = ttk.Frame(bb)
        bi.pack(fill = tk.X)
        ttk.Button(bi, text = '取消', command = self.on_close, width = 10).pack(side = tk.RIGHT, padx = 8, 0)
        ttk.Button(bi, text = '下一步', command = self.on_next_to_step2, width = 10).pack(side = tk.RIGHT)

    def browse_folder(self):
        cur = self.install_path.get()
        init = cur if os.path.isdir(cur) else os.environ.get('ProgramFiles', 'C:\\')
        folder = filedialog.askdirectory(
            title = '选择安装文件夹',
            initialdir = init,
            mustexist = False
        )
        if folder:
            self.install_path.set(folder.replace('/', '\\'))

    # 页2：进度
    def build_page2(self):
        h = ttk.Frame(self.page2)
        h.pack(fill = tk.X, pady = (0, 10))
        ttk.Label(
            h,
            text = f'正在安装 {app_name}',
            font = (title_font, 16, 'bold')
        ).pack(
            fill = tk.X
        )
        ttk.Label(
            h,
            text = '请稍候，安装程序正在复制文件并配置环境。',
            foreground = '#475569'
        ).pack(
            fill = tk.X,
            pady = (4, 0)
        )

        pg = ttk.LabelFrame(self.page2, text = '安装进度', padding = 10)
        pg.pack(fill = tk.X, pady = (0, 10))
        sr = ttk.Frame(pg)
        sr.pack(fill = tk.X, pady = (0, 6))
        ttk.Label(sr, text = '状态：').pack(side = tk.LEFT)
        self.progress_status = ttk.Label(sr, text = '准备中...', foreground = '#3776ab')
        self.progress_status.pack(side = tk.LEFT)
        self.progress_var = tk.DoubleVar(value = 0)
        self.progress_bar = ttk.Progressbar(
            pg,
            variable = self.progress_var,
            maximum = 100,
            mode = 'determinate',
            style = 'Accent.Horizontal.TProgressbar'
        )
        self.progress_bar.pack(fill = tk.X, pady = (0, 8))
        dr = ttk.Frame(pg)
        dr.pack(fill = tk.X)
        self.progress_file = ttk.Label(dr, text = '正在初始化...', foreground = '#64748b')
        self.progress_file.pack(side = tk.LEFT)
        self.progress_percent = ttk.Label(dr, text = '0%', foreground = '#64748b')
        self.progress_percent.pack(side = tk.RIGHT)

        lg = ttk.LabelFrame(self.page2, text = '安装日志', padding = 4)
        lg.pack(fill = tk.BOTH, expand = True, pady = (0, 10))
        lf = tk.Frame(lg, bg = '#1e1e1e')
        lf.pack(fill = tk.BOTH, expand = True)
        self.log_text = tk.Text(
            lf,
            bg = '#1e1e1e',
            fg = '#d4d4d4',
            font = ('Consolas', 10),
            bd = 0,
            padx = 8,
            pady = 6,
            height = 5,
            wrap = tk.WORD,
            state = tk.DISABLED,
            highlightthickness = 0,
            insertbackground = 'white'
        )
        self.log_text.pack(fill = tk.BOTH, expand = True)
        sb = ttk.Scrollbar(lf, command = self.log_text.yview)
        sb.pack(side = tk.RIGHT, fill = tk.Y)
        self.log_text.config(yscrollcommand = sb.set)
        self.log_text.tag_configure('highlight', foreground = '#7bc8ff')
        self.log_text.tag_configure('normal', foreground = '#d4d4d4')
        self.add_log('安装程序已启动（管理员）')

        bb = ttk.Frame(self.page2)
        bb.pack(fill = tk.X, side = tk.BOTTOM)
        ttk.Separator(bb, orient = tk.HORIZONTAL).pack(fill = tk.X, pady = (0, 10))
        bi = ttk.Frame(bb)
        bi.pack(fill = tk.X)
        self.cancel_page2_btn = ttk.Button(bi, text = '取消', command = self.on_cancel_step2, width = 10)
        self.cancel_page2_btn.pack(side = tk.RIGHT, padx = (8, 0))
        self.next_step3_btn = ttk.Button(
            bi,
            text = '下一步',
            command = self.on_next_to_step3,
            width = 10,
            state = tk.DISABLED
        )
        self.next_step3_btn.pack(side = tk.RIGHT)

    def add_log(self, message, highlight = False):
        self.log_text.config(state = tk.NORMAL)
        line = f"[{time.strftime('%H:%M:%S')}] {message}\n"
        self.log_text.insert(tk.END, line, 'highlight' if highlight else 'normal')
        self.log_text.see(tk.END)
        self.log_text.config(state = tk.DISABLED)

    # 页3：完成
    def build_page3(self):
        h = ttk.Frame(self.page3)
        h.pack(fill = tk.X, pady = (0, 12))
        ttk.Label(h, text = '安装完成', font = title_font, 16, 'bold').pack(fill = tk.X)
        ttk.Label(
            h,
            text = f'{app_name} 已成功安装到您的计算机。',
            foreground = '#475569'
        ).pack(
            fill = tk.X,
            pady = (4, 0)
        )
        c = ttk.Frame(self.page3)
        c.pack(fill = tk.BOTH, expand = True)
        ttk.Label(
            c,
            text = '安装成功',
            font = title_font, 24, 'bold',
            foreground = 'black'
        ).pack(
            pady = (30, 16)
        )
        ttk.Label(
            c,
            text = '您可以从开始菜单或桌面启动 Tanex Script。',
            foreground = '#1e4b7a',
            wraplength = 400,
            justify = tk.CENTER
        ).pack(
            pady = (0, 8)
        )
        ttk.Label(
            c,
            text = '感谢使用 Tanex Script 安装程序。',
            foreground = '#64748b'
        ).pack()
        bb = ttk.Frame(self.page3)
        bb.pack(fill = tk.X, side = tk.BOTTOM)
        ttk.Separator(bb, orient = tk.HORIZONTAL).pack(fill = tk.X, pady = (0, 10))
        bi = ttk.Frame(bb)
        bi.pack(fill = tk.X)
        ttk.Button(bi, text = '完成', command = self.on_finish, width = 10).pack(side = tk.RIGHT)

    # 导航
    def on_next_to_step2(self):
        self.show_page(2)
        self.start_installation()

    def on_next_to_step3(self):
        if str(self.next_step3_btn['state']) != 'disabled':
            self.show_page(3)

    def on_cancel_step2(self):
        if self.is_installing:
            self.is_installing = False
            self.add_log('安装已取消', highlight = True)
            self.progress_status.config(text = '已取消')
            self.next_step3_btn.config(state = tk.DISABLED)
            self.cancel_page2_btn.config(state = tk.DISABLED)
        else:
            self.root.destroy()

    def on_finish(self):
        self.root.destroy()

    def on_close(self):
        if self.is_installing:
            if messagebox.askyesno('确认', '安装正在进行，确定要退出吗？'):
                self.is_installing = False
                self.root.destroy()
        else:
            self.root.destroy()

    # 安装执行
    def start_installation(self):
        self.is_installing = True
        self.progress_var.set(0)
        self.progress_percent.config(text = '0%')
        self.progress_status.config(text = '准备中...')
        self.progress_file.config(text = '正在初始化...')
        self.log_text.config(state = tk.NORMAL)
        self.log_text.delete('1.0', tk.END)
        self.log_text.config(state = tk.DISABLED)

        target = self.install_path.get()
        self.add_log(f'开始安装 {app_name} 到 {target}', highlight = True)
        if self.add_to_path.get():
            self.add_log('将添加到系统 PATH')
        if self.create_startmenu.get():
            self.add_log('创建开始菜单快捷方式')
        if self.create_desktop.get():
            self.add_log('创建桌面快捷方式')

        self.next_step3_btn.config(state = tk.DISABLED)
        self.cancel_page2_btn.config(state = tk.NORMAL)
        self.install_thread = threading.Thread(
            target = self._install_worker,
            args = (target,),
            daemon = True
        )
        self.install_thread.start()

    def _install_worker(self, target):
        steps = []
        if True:
            steps.append((10, '正在创建安装目录...', '创建目录'))
        steps.append((30, '正在解压应用程序...', 'TanexScript.zip'))
        if self.add_to_path.get():
            steps.append((50, '正在配置环境变量(PATH)...', '系统 PATH'))
        if self.create_startmenu.get():
            steps.append((70, '正在创建开始菜单快捷方式...', '开始菜单'))
        if self.create_desktop.get():
            steps.append((85, '正在创建桌面快捷方式...', '桌面'))
        steps.append((95, '正在注册卸载信息...', '控制面板'))
        steps.append((100, '安装完成！', '所有组件已安装'))

        for progress, status, detail in steps:
            if not self.is_installing:
                return
            self.root.after(0, self._update, progress, status, detail)
            try:
                self._run_step(status, target)
            except Exception as e:
                self.root.after(0, self.add_log, f'步骤失败: {e}', True)
                self.root.after(0, lambda: self.progress_status.config(text = '失败'))
                return
            time.sleep(0.25)
        if self.is_installing:
            self.root.after(0, self._on_complete)

    def _run_step(self, status, target):
        if status.startswith('创建安装目录'):
            os.makedirs(target, exist_ok = True)
            self.root.after(0, self.add_log, f'创建目录: {target}')
        elif status.startswith('解压'):
            zp = payload_zip_path()
            if not zp:
                raise RuntimeError('找不到内置 TanexScript.zip，请用 packager 重新打包。')

            # 清理旧文件后再解压
            for name in os.listdir(target):
                p = os.path.join(target, name)
                try:
                    shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
                except OSError:
                    pass
            with zipfile.ZipFile(zp, 'r') as z:
                z.extractall(target)
            self.root.after(0, self.add_log, f'解压完成: {os.path.join(target, exe_name)}')
        elif status.startswith('配置环境'):
            add_to_system_path(target)
            self.root.after(0, self.add_log, '已写入系统 PATH')
        elif status.startswith('开始菜单'):
            lnk = start_menu_shortcut_path()
            create_shortcut(os.path.join(target, exe_name), lnk, app_name, target)
            self.root.after(0, self.add_log, f'开始菜单: {lnk}')
        elif status.startswith('桌面'):
            lnk = desktop_shortcut_path()
            create_shortcut(os.path.join(target, exe_name), lnk, app_name, target)
            self.root.after(0, self.add_log, f'桌面: {lnk}')
        elif status.startswith('注册卸载'):
            # 把自身复制为 uninstall.exe 以便后续卸载
            unexe = os.path.join(target, uninst_name)
            try:
                shutil.copyfile(sys.executable, unexe)
            except Exception as e:
                self.root.after(0, self.add_log, f'复制卸载程序失败: {e}')
            register_uninstall(target, unexe)
            self.root.after(0, self.add_log, '已注册卸载信息')

    def _update(self, progress, status, detail):
        if not self.is_installing:
            return
        self.progress_var.set(progress)
        self.progress_percent.config(text = f'{progress}%')
        self.progress_status.config(text = status)
        self.progress_file.config(text = detail)
        self.add_log(f'{status}  {detail}')

    def _on_complete(self):
        self.is_installing = False
        self.progress_var.set(100)
        self.progress_percent.config(text = '100%')
        self.progress_status.config(text = '安装完成！')
        self.progress_file.config(text = '所有组件已安装')
        self.add_log('安装成功！', highlight = True)
        self.next_step3_btn.config(state = tk.NORMAL)
        self.cancel_page2_btn.config(state = tk.DISABLED)

# 入口
def main():
    # 早期崩溃捕获已在模块顶部通过 sys.excepthook 设置，这里直接进主流程
    try:
        _real_main()
    except SystemExit:
        raise
    except Exception:
        diag('main() 未捕获异常')
        raise

def _real_main():
    diag('real_main 进入')
    if any((a in ('--uninstall', '--uninstall-stage2') for a in sys.argv)):
        diag('进入卸载流程')
        handle_uninstall()
        return

    diag(f"is_admin 检查前；frozen={getattr(sys, 'frozen', False)}")
    admin = is_admin()
    diag(f'is_admin = {admin}')
    if not admin:
        if relaunch_as_admin():
            diag('已发起以管理员重启，当前进程退出')
            sys.exit(0)
        messagebox.showerror(
            '权限不足',
            '本安装程序需要管理员权限才能写入 Program Files 与系统 PATH。'
        )
        sys.exit(1)

    diag('准备创建 Tk 根窗口')
    root = tk.Tk()
    apply_window_icon(root)
    diag('Tk 根窗口已创建，进入主循环')
    app = tanex_installer_ui(root)
    root.mainloop()
    diag('主循环结束，正常退出')

if __name__ == '__main__':
    main()
