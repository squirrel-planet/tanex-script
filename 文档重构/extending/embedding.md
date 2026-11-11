# 解释器嵌入指南

> 将 Tanex Script 解释器嵌入 Python 应用程序的完整指南。

---

## 1. 基础嵌入

### 1.1 创建解释器实例

```python
from tanex.runtime.interpreter import TanexInterpreter

# 默认配置
interp = TanexInterpreter()

# 自定义配置
interp = TanexInterpreter(
    recursion_limit=2000,      # 递归深度限制
    stack_size=16384,          # 操作栈大小
    bootstrap_path="run/bootstrap.tscc",  # 引导库路径
    lib_paths=["libs", "/shared/tanex_libs"],  # 库搜索路径
)
```

### 1.2 运行源码

```python
# 直接运行字符串源码
result = interp.run_source('''
    import "standard" = *std;
    std.standard_output << "Hello!\n";
''', filename="<string>", args=[])

# 参数说明：
# - source: Tanex Script 源码字符串
# - filename: 虚拟文件名（用于错误定位、相对路径解析）
# - args: 命令行参数列表（注入 args 常量）
```

### 1.3 运行编译产物

```python
# 运行 .tscc 文件
result = interp.run_file("build/app.tscc", args=["arg1", "arg2"])

# 运行已解析的 AST 字典
import tanex.compile as compile
ast_dict = compile.compile(source)
result = interp.run_ast(ast_dict, args=[])
```

### 1.4 启动 REPL

```python
# 交互模式（阻塞直到用户退出）
interp.repl()
```

---

## 2. 配置与依赖注入

### 2.1 注入全局常量

```python
from tanex.runtime.values import make_string, make_integer, make_boolean

interp = TanexInterpreter(
    builtin_constants={
        "API_KEY": make_string("sk-12345"),
        "MAX_RETRIES": make_integer(3),
        "DEBUG_MODE": make_boolean(True),
        "CONFIG_JSON": make_string('{"timeout": 30}')
    }
)

# Tanex Script 中直接使用
interp.run_source('''
    std.println("API: " + API_KEY);
    std.println("Retries: " + MAX_RETRIES.string());
    std.println("Debug: " + DEBUG_MODE.string());
''')
```

### 2.2 注册自定义函数

```python
from tanex.runtime.values import TSValue, TSInteger, make_integer

def py_factorial(n: TSInteger) -> TSInteger:
    """Python 实现的阶乘，供 Tanex 调用"""
    val = n.value
    if val < 0:
        from tanex.runtime.errors import TSArithError
        raise TSArithError("factorial: argument cannot be negative")
    result = 1
    for i in range(2, val + 1):
        result *= i
    return make_integer(result)

interp = TanexInterpreter(
    custom_functions={
        "factorial": py_factorial
    }
)

interp.run_source('''
    std.println("5! = " + factorial(`5).string());  # => 120
''')
```

### 2.3 注册自定义类型

```python
from tanex.runtime.values import TSType, TSValue, make_integer, make_string, make_instance

# 定义矩阵类型
class MatrixType(TSType):
    def __init__(self):
        super().__init__()
        self.initialize = self._init
        self.special_members = {
            "addition": self._add,
            "multiply": self._mul,
            "string": self._str,
            "index": self._index
        }
    
    def _init(self, self_val, rows, cols):
        self_val.members["rows"] = rows
        self_val.members["cols"] = cols
        self_val.members["data"] = [make_integer(0)] * (rows.value * cols.value)
    
    def _add(self, self_val, other_val):
        if self_val.members["rows"].value != other_val.members["rows"].value \
           or self_val.members["cols"].value != other_val.members["cols"].value:
            raise ValueError("Matrix dimension mismatch")
        result = make_instance(MatrixType(), {
            "rows": self_val.members["rows"],
            "cols": self_val.members["cols"]
        })
        for i in range(len(self_val.members["data"])):
            result.members["data"][i] = make_integer(
                self_val.members["data"][i].value + other_val.members["data"][i].value
            )
        return result
    
    def _mul(self, self_val, other_val):
        # 矩阵乘法实现...
        pass
    
    def _str(self, self_val):
        rows = self_val.members["rows"].value
        cols = self_val.members["cols"].value
        return make_string(f"Matrix({rows}x{cols})")
    
    def _index(self, self_val, key):
        # key 为 [row, col] 列表
        row = key.members["data"][0].value
        col = key.members["data"][1].value
        idx = row * self_val.members["cols"].value + col
        return self_val.members["data"][idx]

interp = TanexInterpreter(
    custom_types={"Matrix": MatrixType()}
)

interp.run_source('''
    * m1 = Matrix{`2`, `3};
    * m2 = Matrix{`2`, `3};
    std.println((m1 + m2).string());
''')
```

---

## 3. 高级嵌入场景

### 3.1 沙箱执行

```python
def run_sandboxed(interp: TanexInterpreter, source: str, 
                  allowed_imports: list = None,
                  max_time_ms: int = 5000) -> TSValue:
    """在受限环境中运行代码"""
    # 创建子作用域隔离
    # 限制 import 白名单
    # 设置超时（需解释器支持）
    # 限制内存/递归
    return interp.run_source(source)
```

### 3.2 多解释器实例

```python
# 每个请求独立解释器（无状态共享）
def handle_request(user_code: str):
    interp = TanexInterpreter(
        builtin_constants={"USER_ID": make_integer(current_user.id)},
        custom_functions={"db_query": db_query_wrapper}
    )
    return interp.run_source(user_code)
```

### 3.3 解释器状态持久化

```python
# 保存解释器状态（地址空间、作用域、模块缓存）
state = interp.serialize()

# 恢复状态
interp2 = TanexInterpreter()
interp2.deserialize(state)
```

---

## 4. 错误处理

```python
from tanex.runtime.errors import (
    TSCompileError, TSRuntimeError, TSNameError, 
    TSTypeError, TSImportError, TSConstError
)

try:
    result = interp.run_source(user_code)
except TSCompileError as e:
    # 编译错误：语法、词法
    for diag in e.diagnostics:
        log.error(f"Compile [{diag.position}]: {diag.message}")
except TSNameError as e:
    # 变量未定义
    log.error(f"Undefined variable: {e.message}")
except TSTypeError as e:
    # 类型错误：不支持运算、成员不存在
    log.error(f"Type error: {e.message}")
except TSImportError as e:
    # 模块导入失败
    log.error(f"Import failed: {e.message}")
except TSConstError as e:
    # 常量修改尝试
    log.error(f"Const violation: {e.message}")
except TSRuntimeError as e:
    # 其他运行时错误
    log.error(f"Runtime error: {e.message}")
```

---

## 5. 性能优化建议

| 场景 | 建议 |
|------|------|
| 频繁调用 `run_source` | 复用解释器实例，避免重复初始化引导库 |
| 大量并发请求 | 使用解释器池，或每请求新实例（权衡内存 vs 隔离） |
| 热代码路径 | 将核心逻辑移至 Python 自定义函数/类型 |
| 启动延迟敏感 | 预热解释器：启动时执行空 `run_source(";")` |

---

## 6. 完整示例：表达式计算器服务

```python
from flask import Flask, request, jsonify
from tanex.runtime.interpreter import TanexInterpreter
from tanex.runtime.values import make_integer, make_string
from tanex.runtime.errors import TSCompileError, TSRuntimeError

app = Flask(__name__)

# 单例解释器（预热）
interp = TanexInterpreter(
    custom_functions={
        "now": lambda: make_integer(int(time.time())),
        "uuid": lambda: make_string(str(uuid.uuid4()))
    }
)
interp.run_source(";")  # 预热

@app.route("/eval", methods=["POST"])
def eval_expr():
    data = request.get_json()
    expr = data.get("expr", "")
    
    # 安全包装
    safe_source = f'''
        import "standard" = *std;
        * result = {expr};
        std.standard_output << result.string();
    '''
    
    try:
        result = interp.run_source(safe_source, filename="<api>")
        return jsonify({"success": True, "result": str(result)})
    except TSCompileError as e:
        return jsonify({"success": False, "error": "CompileError", "details": str(e)}), 400
    except TSRuntimeError as e:
        return jsonify({"success": False, "error": "RuntimeError", "details": str(e)}), 500

if __name__ == "__main__":
    app.run(port=8080)
```

---

## 相关链接

- [编译器 API](compiler_api.md) — 程序化编译
- [运行时值模型](values.md) — 值构造与操作
- [核心执行器](interpreter.md) — 执行器内部
- [错误与诊断](errors.md) — 完整错误体系
- [专题指南：互操作](../howto/interop.md) — 更多嵌入实战