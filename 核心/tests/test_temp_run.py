import contextlib
import io
import os
import sys
sys.path.insert(0, '..')
from compile.main import compile_source
from runtime.interpreter import interpreter

def test_run_compiled_in_memory():
    # -t/--temp 的核心路径：编译产物不落地，直接从内存运行
    source = 'standard_output << 65;'
    compiled = compile_source(source, '<temp>')
    interp = interpreter()
    interp.init_core()
    interp.load_bootstrap()
    interp.set_program_dir(os.getcwd())
    interp.set_program_args([])
    interp.inject_args()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        result, returned = interp.run_compiled(compiled, '<temp>')
    assert returned is False
    assert buf.getvalue() == 'A'
