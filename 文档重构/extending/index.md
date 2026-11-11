# 扩展与嵌入

> 对标 [Python Extending and Embedding](https://docs.python.org/zh-cn/3.16/extending/)
>
> 面向 C/C++ 与 Python 开发者，提供 Tanex Script 解释器的嵌入、扩展、工具开发完整 API 参考。

---

## 章节导航

| 文档 | 说明 | 目标读者 |
|------|------|----------|
| [embedding.md](embedding.md) | 解释器嵌入指南 | 应用开发者、引擎集成 |
| [compiler_api.md](compiler_api.md) | 编译器 API | 工具链开发者、IDE 插件 |
| [values.md](values.md) | 运行时值模型 | 扩展开发者、调试工具 |
| [environment.md](environment.md) | 地址空间与作用域 | 运行时内部开发 |
| [interpreter.md](interpreter.md) | 核心执行器 | 虚拟机开发、JIT 研究 |
| [loader.md](loader.md) | 模块加载器 | 插件系统、热重载 |
| [annotations.md](annotations.md) | 注解系统 | 文档生成、元编程工具 |
| [stdlib_registration.md](stdlib_registration.md) | 标准库注册机制 | 标准库维护者 |
| [errors.md](errors.md) | 错误与诊断 | 调试器、静态分析工具 |

---

## 快速开始：Python 嵌入

```python
from tanex.runtime.interpreter import TanexInterpreter

# 创建解释器
interp = TanexInterpreter()

# 运行源码
result = interp.run_source('''
    import "standard" = *std;
    std.standard_output << "Hello from embedded Tanex!\n";
''')

# 运行文件
result = interp.run_file("app.tscc")

# 注入自定义常量/函数
interp2 = TanexInterpreter(
    builtin_constants={"API_KEY": make_string("secret")},
    custom_functions={"my_func": python_impl}
)
```

---

## 快速开始：注册内置类型

```python
from tanex.runtime.values import TSType, make_integer
from tanex.runtime.interpreter import TanexInterpreter

# 定义 Python 侧类型
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
        from tanex.runtime.values import make_instance
        return make_instance(Vector2D(), {
            "x": make_integer(self_val.members["x"].value + other_val.members["x"].value),
            "y": make_integer(self_val.members["y"].value + other_val.members["y"].value)
        })
    
    def _str(self, self_val):
        from tanex.runtime.values import make_string
        return make_string(f"Vector2D({self_val.members['x'].value}, {self_val.members['y'].value})")

# 注册到解释器
interp = TanexInterpreter(
    custom_types={"Vector2D": Vector2D()}
)

interp.run_source('''
    * a = Vector2D{`1`, `2};
    * b = Vector2D{`3`, `4};
    std.standard_output << (a + b);  # => Vector2D(4, 6)
''')
```

---

## 核心概念速查

| 概念 | Python 类型 | 说明 |
|------|-------------|------|
| 解释器 | `TanexInterpreter` | 主入口，管理地址空间、作用域、模块缓存 |
| 地址空间 | `AddressSpace` | 存储所有运行时值的仓库，地址为整数 |
| 作用域 | `Scope` | 变量名→地址映射，支持嵌套与父链查找 |
| 运行时值 | `TSValue` 子类 | `TSInteger`、`TSNumber`、`TSString` 等 |
| 控制流信号 | Exception 子类 | `BreakSignal`、`ContinueSignal`、`ReturnSignal`、`ErrorSignal` |
| 注解表 | `AnnotationTable` | 编译期注解的运行时存储，支持库隔离 |

---

## 相关链接

- [教程：进阶](../tutorial/advanced.md) — 自定义类型、动态 import
- [专题指南：互操作](../howto/interop.md) — Python/C 互操作实战
- [语言参考：运行时内部](../reference/runtime_internals.md) — 解释器内部机制
- [语言参考：模块系统](../reference/modules.md) — import/-> 语义
- [标准库参考](../library/) — 可复用的工具函数