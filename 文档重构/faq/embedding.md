# 嵌入与扩展常见问题

> Tanex Script 解释器嵌入 Python、注册自定义类型/函数、C API 等问题。

---

## Python 嵌入

### Q: 如何在 Python 中运行 Tanex Script 代码？
**A**: 
```python
from tanex.runtime.interpreter import TanexInterpreter

interp = TanexInterpreter()
result = interp.run_source('''
    import "standard" = *std;
    std.standard_output << "Hello from Python!\n";
''')
```

### Q: 如何向 Tanex 注入 Python 变量/常量？
**A**: 使用 `builtin_constants` 参数：
```python
from tanex.runtime.values import make_string, make_integer

interp = TanexInterpreter(
    builtin_constants={
        "API_KEY": make_string("sk-12345"),
        "MAX_RETRIES": make_integer(3)
    }
)
# Tanex 中直接使用 API_KEY、MAX_RETRIES
```

### Q: 如何注册 Python 函数供 Tanex 调用？
**A**: 
```python
from tanex.runtime.values import TSInteger, make_integer

def py_factorial(n: TSInteger) -> TSInteger:
    val = n.value
    if val < 0:
        from tanex.runtime.errors import TSArithError
        raise TSArithError("factorial: negative argument")
    result = 1
    for i in range(2, val + 1):
        result *= i
    return make_integer(result)

interp = TanexInterpreter(
    custom_functions={"factorial": py_factorial}
)

interp.run_source('std.println(factorial(`5).string());  # => 120')
```

### Q: 如何注册自定义类型（运算符重载）？
**A**: 继承 `TSType` 并注册特殊成员：
```python
from tanex.runtime.values import TSType, TSValue, make_integer, make_string, make_instance

class Vector2D(TSType):
    def __init__(self):
        super().__init__()
        self.initialize = self._init
        self.special_members = {
            "addition": self._add,
            "string": self._str
        }
    
    def _init(self, self_val, x, y):
        self_val.members["x"] = make_integer(x.value)
        self_val.members["y"] = make_integer(y.value)
    
    def _add(self, self_val, other_val):
        return make_instance(Vector2D(), {
            "x": make_integer(self_val.members["x"].value + other_val.members["x"].value),
            "y": make_integer(self_val.members["y"].value + other_val.members["y"].value)
        })
    
    def _str(self, self_val):
        return make_string(f"Vector2D({self_val.members['x'].value}, {self_val.members['y'].value})")

interp = TanexInterpreter(custom_types={"Vector2D": Vector2D()})
```

### Q: 如何捕获 Tanex 运行时错误？
**A**: 
```python
from tanex.runtime.errors import (
    TSCompileError, TSRuntimeError, TSNameError, 
    TSTypeError, TSImportError, TSArithError
)

try:
    result = interp.run_source(user_code)
except TSCompileError as e:
    for diag in e.diagnostics:
        print(f"[{diag.code}] {diag.message} at {diag.position}")
except TSNameError as e:
    print(f"Undefined variable: {e.message}")
except TSTypeError as e:
    print(f"Type error: {e.message}")
except TSArithError as e:
    print(f"Arithmetic error: {e.message}")
except TSRuntimeError as e:
    print(f"Runtime error: {e.message}")
```

---

## 编译器 API

### Q: 如何程序化编译 Tanex Script 源码？
**A**: 
```python
import tanex.compile as compile

# 一体化编译
ast_dict = compile.compile(source, filename="app.tsuc")

# 分步
tokens = compile.tokenize(source)
ast = compile.parse(tokens)

# 编译文件
ast_dict = compile.compile_file("src/main.tsuc", "build/main.tscc")

# 提取依赖
deps = compile.collect_imports(ast_dict)
```

### Q: 如何获取编译错误详细信息？
**A**: 
```python
try:
    ast_dict = compile.compile(source)
except compile.TSCompileError as e:
    for diag in e.diagnostics:
        print(f"[{diag.code}] {diag.source}:{diag.position[0]}:{diag.position[1]}")
        print(f"  {diag.message}")
        print(f"  > {diag.snippet}")
```

---

## 运行时值操作

### Q: 如何在 Python 中构造 Tanex 值？
**A**: 
```python
from tanex.runtime.values import (
    make_integer, make_number, make_string, make_boolean,
    make_none, make_nan, make_infinite,
    make_list, make_code, make_address,
    make_error, make_warning, make_library,
    make_type, make_instance
)

# 基础值
i = make_integer(42)
n = make_number(3, 14, 2)  # 3.14
s = make_string("hello")
b = make_boolean(True)

# 复合值
lst = make_list([make_integer(1), make_integer(2)])
err = make_error("something went wrong")
```

### Q: 如何在 Python 中判断 Tanex 值的真假？
**A**: 
```python
from tanex.runtime.values import ts_truthy

ts_truthy(make_integer(0))      # False
ts_truthy(make_integer(1))      # True
ts_truthy(make_none())          # False
ts_truthy(make_string(""))      # False
ts_truthy(make_string("hi"))    # True
```

---

## C API (计划中)

### Q: 有 C API 吗？
**A**: 目前**仅提供 Python API**。C API 在规划中，类似 [Python C API](https://docs.python.org/zh-cn/3.16/c-api/index.html)。计划接口包括：
- `Tanex_NewInterpreter()`
- `Tanex_RunSource()`
- `Tanex_RegisterFunction()`
- `Tanex_RegisterType()`

### Q: 如何调用现有 C 库？
**A**: 目前建议：
1. 编写 Python C 扩展封装 C 库
2. 通过 Python API 注册为 `custom_functions` 或 `custom_types`
3. Tanex 通过 Python API 调用

---

## 互操作场景

### Q: Tanex 能作为配置语言嵌入应用吗？
**A**: **非常适合**。优势：
- 语法简洁、无副作用的声明式配置
- 支持代码块作为回调/钩子
- Python API 便于注入应用对象
- 沙箱执行可限制权限

### Q: Tanex 能做 Web 后端脚本吗？
**A**: 可以，但需注意：
- 无原生异步/并发支持
- 建议将 I/O 移至 Python 层，Tanex 只处理业务逻辑
- 性能敏感路径用 Python/NumPy 实现

### Q: 如何实现插件系统？
**A**: 
```python
# 主程序
interp = TanexInterpreter(custom_functions={"register_plugin": py_register})

# 插件代码 (plugin_auth.tsuc)
register_plugin("auth", { 
    login: [*u,*p] => { ... },
    logout: [*u] => { ... }
});

# 主程序加载插件
interp.run_file("plugin_auth.tscc")
```

---

## 性能与调试

### Q: 嵌入 Tanex 会影响主程序性能吗？
**A**: 
- 解释器启动 ~10-50ms（含引导库加载）
- 热代码路径建议移至 Python 自定义函数/类型
- 复用解释器实例避免重复初始化

### Q: 如何调试嵌入的 Tanex 代码？
**A**: 
- `--verbose` 查看编译/执行耗时
- `interp.repl()` 交互式调试
- 捕获异常查看诊断信息
- 未来版本将支持堆栈追踪、断点

### Q: 如何热重载插件？
**A**: 
```python
# 使缓存失效
interp.module_cache.invalidate("/path/to/plugin.tscc")
# 重新导入
interp.run_source('import "/path/to/plugin.tscc" = *plugin;')
```

---

## 常见错误

### Q: `TSTypeError: Type 'X' does not support operator '+'`？
**A**: 类型 `X` 未注册 `addition` 特殊成员。需在 Python 侧注册或 Tanex 中定义：
```tanexscript
*** X.addition = [*self, *other] => { ... };
```

### Q: `TSImportError: Ambiguous import path`？
**A**: 同名多内容（如 `lib.tsuc`、`lib.tscc`、`lib/` 共存）。加后缀消除歧义：
```tanexscript
import "lib/";      # 文件夹
import "lib.tsuc";  # 源码文件
```

### Q: `TSConstError: Cannot assign to constant`？
**A**: 尝试修改 `***` 声明的常量，或 `external_read_only` 成员。

---

## 相关链接

- [扩展与嵌入指南](../extending/) — 完整 API 参考
- [语言参考：模块系统](../reference/modules.md) — import 语义
- [专题指南：互操作](../howto/interop.md) — 实战案例
- [GitHub Issues](https://github.com/tanex-script/tanex-script/issues) — Bug 报告、功能请求