# 运行时入口

import os
import sys
from runtime.interpreter import interpreter

def run_entry(file_path):
    if not os.path.exists(file_path):
        raise RuntimeError('文件不存在: ' + file_path)
    interp = interpreter()
    interp.init_core()
    interp.load_bootstrap()
    result, returned = interp.run_file(file_path)
    if returned:
        if isinstance(result, int):
            sys.exit(result)
        raise RuntimeError(
            f'顶层 return 的值必须是整数（用作程序退出码），但得到: {result!r}')
