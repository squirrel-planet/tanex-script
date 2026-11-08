# python_api 根包：包自身的公开内容会在首次成员访问时
# 合并进全局 python_api 容器（与子包 __init__.py 行为一致）。

__all__ = ['API_VERSION', 'about']

API_VERSION = '1.0'


def about():
    return 'TanexScript python_api bridge'
