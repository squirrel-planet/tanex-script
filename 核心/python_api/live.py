# python_api 示例模块：故意不声明 __all__，用于验证
# TanexScript 侧能否看到 Python 模块运行期动态新增的公开成员。


def attach():
    # 模块没有 __all__，公开成员走 dir() 枚举；
    # 这里在投影生成之后才挂上新名字。
    globals()['marker'] = 42
    return 'attached'


def replace():
    globals()['marker'] = 99
    return 'replaced'
