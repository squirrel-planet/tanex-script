import json
import os
import sys

sys.path.insert(0, '..')

from compile.main import compile_source
from runtime.interpreter import interpreter


def _make_repl_interp(program_args = None):
    # 模拟 runtime/repl.py repl_entry 的初始化序列
    interp = interpreter()
    interp.init_core()
    interp.load_bootstrap()
    if program_args is not None:
        interp.set_program_args(program_args)
    interp.inject_args(repl_mode = True)
    return interp


def _string_of(interp, value):
    codes = interp._list_to_py(interp._get_string_value(value))
    return ''.join(chr(c) for c in codes)


def _run_source(interp, source):
    ast = json.loads(compile_source(source, '<shell-mode-input>',
        exit_on_error = False))
    statements = ast['Tanex Script']
    interp.annotations.update(ast.get('annotations', {}))
    return interp.run_statements(statements)


def test_repl_path_is_none():
    interp = _make_repl_interp()
    cell = interp.global_scope.names.get('path')
    assert cell is not None
    assert interp._is_none_value(cell.value)


def test_repl_program_path_equals_regular():
    interp = _make_repl_interp()
    cell = interp.global_scope.names.get('program_path')
    assert cell is not None
    repl_path = _string_of(interp, cell.value)
    # 常规运行模式（inject_args 默认参数）应注入相同 program_path
    regular = interpreter()
    regular.init_core()
    regular.load_bootstrap()
    regular.inject_args()
    assert repl_path == _string_of(regular, regular.global_scope.names['program_path'].value)
    assert os.path.isdir(repl_path)


def test_repl_import_program_path_no_undefined_error():
    interp = _make_repl_interp()
    # 修复前：import "{program_path}/libary/standard" 会报"变量未定义: program_path"
    _run_source(interp, 'import "{program_path}/libary/standard";')


def test_repl_args_filled_when_provided():
    interp = _make_repl_interp(program_args = ['x', 'y'])
    cell = interp.global_scope.names.get('args')
    assert cell is not None
    # 其他填充常量同样允许填充：args 在 REPL 下与常规模式行为一致
    codes = interp._list_to_py(cell.value)
    assert len(codes) == 2
    assert _string_of(interp, codes[0]) == 'x'
    assert _string_of(interp, codes[1]) == 'y'
