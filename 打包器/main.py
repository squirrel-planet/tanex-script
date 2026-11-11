# -*- coding: utf-8 -*-
# 打包器入口：等价于 python tools/packager.py

import os
import runpy


target = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'tools',
    'packager.py'
)

if __name__ == '__main__':
    runpy.run_path(target, run_name = '__main__')
