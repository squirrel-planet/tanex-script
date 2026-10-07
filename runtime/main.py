# 运行时入口

import os
import sys
from runtime.interpreter import interpreter

def run_entry(file_path, debug_lines = None, program_args = None):
    if not os.path.exists(file_path):
        raise RuntimeError('文件不存在: ' + file_path)
    interp = interpreter()
    interp.init_core()
    interp.load_bootstrap()
    interp.set_program_dir(os.path.dirname(os.path.abspath(file_path)))
    if program_args is not None:
        interp.set_program_args(program_args)
    # 库文件（.tscl）场景不注入运行时引导常量（args/path/program_path），保持与既有行为一致
    if not file_path.endswith('.tscl'):
        interp.inject_args()
    if debug_lines:
        from runtime.debugger import debugger
        interp._debugger = debugger(
            interp, debug_lines, interp._resolve_source_path(file_path))
    result, returned = interp.run_file(file_path)
    if returned:
        if isinstance(result, int):
            sys.exit(result)
        raise RuntimeError(
            f'顶层 return 的值必须是整数（用作程序退出码），但得到: {result!r}')
