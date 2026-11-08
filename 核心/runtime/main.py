# 运行时入口

import os
import sys
from runtime.interpreter import interpreter

def _finish_run(result, returned):
    if returned:
        if isinstance(result, int):
            sys.exit(result)
        raise RuntimeError(
            f'顶层 return 的值必须是整数（用作程序退出码），但得到: {result!r}'
        )

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
            interp,
            debug_lines,
            interp._resolve_source_path(file_path)
        )
    result, returned = interp.run_file(file_path)
    _finish_run(result, returned)

# 运行内存中的编译产物（-t/--temp），不生成 .tscc 文件
def run_compiled_entry(compiled, source_path, debug_lines = None, program_args = None, program_dir = None):
    interp = interpreter()
    interp.init_core()
    interp.load_bootstrap()
    interp.set_program_dir(program_dir or os.getcwd())
    if program_args is not None:
        interp.set_program_args(program_args)
    interp.inject_args()
    if debug_lines:
        from runtime.debugger import debugger
        interp._debugger = debugger(interp, debug_lines, source_path)
    result, returned = interp.run_compiled(compiled, source_path)
    _finish_run(result, returned)
