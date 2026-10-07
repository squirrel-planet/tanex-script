import io
import os
import sys
import tempfile
import contextlib
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from compile.main import compile_source
from runtime.interpreter import interpreter

@pytest.fixture
def run_tsuc():
    # 编译并运行 tsuc 源码，捕获并返回标准输出
    def _run(source: str, base_dir: str | None = None) -> str:
        d = base_dir or tempfile.mkdtemp()
        path = os.path.join(d, 'main.tsuc')
        with open(path, 'w', encoding = 'utf-8') as f:
            f.write(source)
        compiled = compile_source(source, path)
        cc = os.path.join(d, 'main.tscc')
        with open(cc, 'w', encoding = 'utf-8') as f:
            f.write(compiled)
        interp = interpreter()
        interp.init_core()
        interp.load_bootstrap()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            interp.run_file(cc)
        return buf.getvalue()

    return _run
