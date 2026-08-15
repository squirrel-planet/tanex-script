# 运行时值类型

from typing import Any
from errors import tanex_script_error

class runtime_error(tanex_script_error):
    def __init__(self, message):
        super().__init__(message)

class throw_signal(Exception):
    def __init__(self, value):
        super().__init__('<throw>')
        self.value = value

class return_signal(Exception):
    def __init__(self, value):
        super().__init__('<return>')
        self.value = value

class break_signal(Exception):
    def __init__(self):
        super().__init__('<break>')

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
    def __init__(self, statements, env, params = None, defaults = None):
        self.statements = statements
        self.env = env
        self.params = params if params is not None else []
        self.defaults = defaults if defaults is not None else [None] * len(self.params)
        self.owner = None
        self.meta: 'instance | None' = None

class builtin_function:
    def __init__(self, fn, name = None):
        self.fn = fn
        self.name = name or '<builtin>'
