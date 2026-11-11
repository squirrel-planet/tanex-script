# 互操作指南

> Tanex Script 与 Python、C、外部库的互操作。

---

## 1. Python 嵌入 Tanex Script

### 1.1 基础嵌入

```python
from tanex.runtime.interpreter import TanexInterpreter

# 创建解释器实例
interp = TanexInterpreter(
    recursion_limit=2000,
    stack_size=16384,
    bootstrap_path="run/bootstrap.tscc"
)

# 运行源码
result = interp.run_source('''
    import "standard" = *std;
    std.standard_output << "Hello from embedded!\n";
''')

# 运行编译产物
result = interp.run_file("build/app.tscc")

# 运行 AST
import tanex.compile as compile
ast = compile.compile(source)
result = interp.run_ast(ast)
```

### 1.2 注入全局常量

```python
from tanex.runtime.values import make_integer, make_string

interp = TanexInterpreter(
    builtin_constants={
        "app_config": make_string('{"debug": true}'),
        "max_retries": make_integer(3),
        "api_endpoint": make_string("https://api.example.com")
    }
)

# Tanex Script 中直接可用
interp.run_source('''
    std.println("Endpoint: " + api_endpoint);
    std.println("Retries: " + max_retries.string());
''')
```

### 1.3 注册自定义函数

```python
from tanex.runtime.values import make_integer, TSInteger

def py_add(a: TSInteger, b: TSInteger) -> TSInteger:
    """Python 实现的加法，供 Tanex 调用"""
    return make_integer(a.value + b.value)

interp = TanexInterpreter(
    custom_functions={
        "py_add": py_add
    }
)

interp.run_source('''
    * result = py_add(`10`, `20);
    std.println("Python add: " + result.string());  # => 30
''')
```

### 1.4 注册自定义类型与特殊成员

```python
from tanex.runtime.values import TSType, TSValue, make_integer

# 创建自定义类型
MyType = TSType()
MyType.initialize = lambda self, value: setattr(self, 'value', value)

def my_addition(self, other):
    return make_integer(self.value + other.value)

# 注册特殊成员
interp = TanexInterpreter(
    custom_types={"MyType": MyType},
    custom_special_members={
        "MyType": {"addition": my_addition}
    }
)

interp.run_source('''
    * a = MyType{`5};
    * b = MyType{`3};
    std.println((a + b).string());  # => 8 (调用 Python 实现)
''')
```

### 1.5 捕获解释器错误

```python
from tanex.runtime.errors import TSCompileError, TSRuntimeError, TSNameError, TSTypeError

try:
    interp.run_source(user_code)
except TSCompileError as e:
    print(f"编译错误 [{e.pos}]: {e.message}")
except TSNameError as e:
    print(f"变量未定义: {e.message}")
except TSTypeError as e:
    print(f"类型错误: {e.message}")
except TSRuntimeError as e:
    print(f"运行时错误: {e.message}")
```

---

## 2. 编译器 API 使用

### 2.1 编译源码

```python
import tanex.compile as compile

# 一体化编译
ast_dict = compile.compile(source, filename="app.tsuc")

# 分步编译
tokens = compile.tokenize(source, filename="app.tsuc")
ast = compile.parse(tokens, filename="app.tsuc")

# 编译文件
ast_dict = compile.compile_file("src/main.tsuc", "build/main.tscc")

# 提取依赖
deps = compile.collect_imports(ast_dict)
# ["lib.tscc", "standard.tscl", ...]
```

### 2.2 诊断信息

```python
from tanex.compile import TSCompileError

try:
    ast_dict = compile.compile(invalid_source)
except TSCompileError as e:
    for diag in e.diagnostics:
        print(f"{diag.severity.upper()} [{diag.position}]: {diag.message}")
        print(f"  Code: {diag.code}")
        print(f"  Snippet: {diag.snippet}")
```

---

## 3. 运行时值模型操作

### 3.1 值构造

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
none = make_none()
nan = make_nan()
inf = make_infinite(1)   # 正无穷
ninf = make_infinite(-1) # 负无穷

# 复合值
lst = make_list([make_integer(1), make_integer(2)])
code = make_code(statements=[], scope=current_scope)
addr = make_address(123)
err = make_error("something went wrong")
warn = make_warning("deprecated")

# 类型与实例
MyType = make_type(initialize=my_init_fn)
instance = make_instance(MyType, {"field": make_integer(42)})
```

### 3.2 真值判定与类型查询

```python
from tanex.runtime.values import ts_truthy, ts_type_of

ts_truthy(make_integer(0))      # False
ts_truthy(make_integer(1))      # True
ts_truthy(make_none())          # False
ts_truthy(make_string(""))      # False (空串)
ts_truthy(make_string("hi"))    # True

ts_type_of(make_integer(42))    # 返回 integer 类型对象
```

### 3.3 地址空间与作用域操作

```python
from tanex.runtime.environment import AddressSpace, Scope

addr_space = AddressSpace()
addr = addr_space.allocate()        # 分配地址
addr_space.write(addr, make_integer(42))
val = addr_space.read(addr)         # 读取值
addr_space.mark_const(addr)         # 标记常量

global_scope = Scope()
global_scope.declare("x", addr)     # 声明变量
found_addr = global_scope.resolve_or_error("x")

# 子作用域
child_scope = Scope(parent=global_scope)
child_scope.declare("y", addr_space.allocate())
```

---

## 4. C/C++ 扩展 (计划中)

> 未来版本将提供 C API，类似 [Python C API](https://docs.python.org/zh-cn/3.16/c-api/index.html)。

### 计划接口

```c
// 初始化解释器
TanexInterpreter* Tanex_NewInterpreter(TanexConfig* config);

// 运行源码
TanexValue* Tanex_RunSource(TanexInterpreter* interp, const char* source);

// 运行文件
TanexValue* Tanex_RunFile(TanexInterpreter* interp, const char* path);

// 注册 C 函数
void Tanex_RegisterFunction(TanexInterpreter* interp, const char* name, TanexCFunc func);

// 注册 C 类型
void Tanex_RegisterType(TanexInterpreter* interp, const char* name, TanexType* type);

// 错误处理
const char* Tanex_GetLastError(TanexInterpreter* interp);
void Tanex_ClearError(TanexInterpreter* interp);

// 清理
void Tanex_FreeInterpreter(TanexInterpreter* interp);
```

---

## 5. 外部库调用 (FFI, 计划中)

### 计划方案

```tanexscript
# 声明外部函数
*** extern "c" malloc = [*size] => { /* C 调用 */ };
*** extern "c" free = [*ptr] => { /* C 调用 */ };

# 调用
* ptr = malloc(`1024);
# 使用 ptr...
free(ptr);
```

### 安全考虑

- 内存安全：FFI 操作绕过 Tanex 内存管理
- 类型安全：需手动保证参数类型匹配
- 建议：优先用 Python 扩展实现复杂逻辑，再通过 Python API 调用

---

## 6. 进程间通信

### 6.1 标准输入输出

```tanexscript
# 子进程模式
import "standard" = *std;

# 读取 stdin (行分隔)
* line = "";
std.standard_input >> line;

# 写入 stdout
std.standard_output << "Result: " + result.string() + "\n";
```

### 6.2 JSON-RPC (计划中)

```tanexscript
import "jsonrpc" = *rpc;

* server = rpc.server({port: `8080});
server.register("add", { *params => params[`0] + params[`1] });
server.start();
```

---

## 7. 最佳实践清单

| 场景 | 推荐方案 |
|------|----------|
| Python 业务逻辑 | Python API 注册函数/类型，Tanex 调用 |
| 高性能数值计算 | Python (NumPy) 或 C 扩展，通过 Python API 桥接 |
| 现有 C 库 | 编写 Python C 扩展封装，再通过 Python API 暴露 |
| 简单配置/脚本 | 纯 Tanex Script，无需互操作 |
| 微服务通信 | HTTP/JSON-RPC/gRPC，Tanex 作为客户端或服务端 |

---

## 相关链接

- [扩展与嵌入：Python API](../extending/) — 完整 API 参考
- [语言参考：模块系统](../reference/modules.md) — import 机制
- [语言参考：运行时内部](../reference/runtime_internals.md) — 解释器内部结构
- [专题指南：性能优化](../howto/performance.md) — 跨语言调用开销
- [标准库：json](../library/json.md) — 数据序列化交互