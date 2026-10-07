# 运行时值类型

from typing import Any
from errors import tanex_script_error

class runtime_error(tanex_script_error):
    def __init__(self, message, file = None, line = None, col = None):
        super().__init__(message, file = file, line = line, col = col)
        # 调用链回溯帧列表：[(文件, 行, 列, 描述)]，从入口到出错点；
        # 由解释器在异常冒泡时挂一次完整快照，None 表示未挂载
        self.trace = None

    # 将缺失的位置/文件信息补到错误上（已有信息不覆盖）
    def annotate(self, file = None, pos = None):
        if file is not None and self.file is None:
            self.file = file
        if pos:
            if self.line is None:
                self.line = pos[0]
            if self.col is None:
                self.col = pos[1]
        return self

class throw_signal(Exception):
    def __init__(self, value):
        super().__init__('<throw>')
        self.value = value

class return_signal(Exception):
    def __init__(self, value, depth = 1):
        super().__init__('<return>')
        self.value = value
        self.depth = depth

class break_signal(Exception):
    def __init__(self):
        super().__init__('<break>')

class contiune_signal(Exception):
    def __init__(self):
        super().__init__('<contiune>')

class type_object:
    def __init__(self, name = None):
        self.name = name
        self.members: dict[str, Any] = {}
        self.inherit: 'type_object | None' = None

class instance:
    def __init__(self, typ):
        self.type = typ
        self.members: dict[str, Any] = {}
        self.inherit: 'instance | type_object | None' = None

class code_value:
    def __init__(self, statements, env, params = None, defaults = None,
        types = None, file = None, param_modes = None):
        self.statements = statements
        self.env = env
        self.params = params if params is not None else []
        self.defaults = defaults if defaults is not None else [None] * len(self.params)
        # 参数类型位：[*name, 类型, 默认值] 中的类型标注，以 AST 形式暂存，
        # 调用时才解析为类型对象做校验（单类型名或类型名列表）
        self.types = types if types is not None else [None] * len(self.params)
        # 形参传递模式：与 params 一一对应，取 '*'（值传递，深拷贝实参）
        # 或 '**'（引用传递，直接绑定实参原 cell）。*name / **name、
        # [*name, 类型, 默认值] / [**name, 类型, 默认值] 两种写法都支持。
        self.param_modes = param_modes if param_modes is not None \
            else ['*'] * len(self.params)
        # 类型标注 AST 的解析结果缓存（按参数下标）
        self._type_cache: dict = {}
        self.owner = None
        self.meta: 'instance | None' = None
        # code_value 定义所在源文件，用于函数调用时切换错误定位上下文
        self.file = file

class builtin_function:
    def __init__(self, fn, name = None):
        self.fn = fn
        self.name = name or '<builtin>'
