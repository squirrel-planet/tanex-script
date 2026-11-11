# Tanex Script 启动器。
# 打包后同一个 TanexScript.exe 承担两种角色：
# 无参数时启动 IDLE 图形界面；带参数时作为命令行主程序运行。
# IDLE/runner.py 在 frozen 环境下会调用同目录的 TanexScript.exe 并传入
# -s / -c / -r 等参数，所以这里不能再是占位窗口。

import os
import sys
import ctypes


# 控制台版 exe 才能把 stdout 接到管道供 IDLE 的 Shell 使用；
# 启动图形界面时把控制台窗口藏起来，避免闪黑框。
def hide_console():
    if os.name != 'nt':
        return
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)
    except OSError:
        return


# 打包自检：打印冻结环境下的关键路径，供 packager.py 校验资源落点。
def dump_paths():
    import config
    from compile.preprocessor.preprocessor import preprocessor
    import runtime.interpreter as interpreter_module

    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding = 'utf-8')
    interpreter_dir = os.path.dirname(os.path.abspath(interpreter_module.__file__))
    print('executable:', sys.executable)
    print('frozen:', getattr(sys, 'frozen', False))
    print('meipass:', getattr(sys, '_MEIPASS', None))
    print('config_file:', getattr(config, '__file__', None))
    print('config_here:', config.here)
    print('config_root:', config.root)
    print('stdlib_root:', preprocessor._stdlib_root())
    print('library_root:', preprocessor._library_root())
    print('interpreter_dir:', interpreter_dir)
    print('bootstrap_exists:', os.path.isfile(os.path.join(interpreter_dir, 'bootstrap.tscc')))
    print('standard_exists:', os.path.isfile(os.path.join(preprocessor._library_root(), 'standard.tscl')))


# 打包自检：确认图形界面与解释器的全部模块在冻结环境下都能导入。
def check_imports():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding = 'utf-8')
    import main
    import idle
    import config
    import editor
    import shell
    import doc_viewer
    import runner
    import lexer
    import menus
    import window
    import codeview
    from runtime.repl import repl_entry
    from runtime.main import run_entry

    print('imports_ok: True')
    print('cli_main:', callable(main.main))
    print('idle_main:', callable(idle.main))
    print('repl_entry:', callable(repl_entry))
    print('run_entry:', callable(run_entry))
    print('config_root:', config.root)


def main():
    if '--dump-paths' in sys.argv:
        dump_paths()
        return
    if '--check-imports' in sys.argv:
        check_imports()
        return
    if len(sys.argv) > 1:
        import main as cli

        cli.main()
        return
    hide_console()
    import idle

    idle.main()


if __name__ == '__main__':
    main()
