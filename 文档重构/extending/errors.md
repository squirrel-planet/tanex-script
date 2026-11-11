# 错误与诊断

> Tanex Script 解释器的错误体系、诊断信息结构、错误码对照。

---

## 1. 异常类层级

```python
class TSError(Exception):
    """基类：含位置信息、错误码"""
    def __init__(self, message: str, pos: Tuple[int, int] = None, code: str = None):
        self.message = message
        self.pos = pos          # (line, column)
        self.code = code        # 错误码字符串
        super().__init__(message)

class TSCompileError(TSError):
    """编译期错误（词法/语法）"""
    def __init__(self, message: str, pos: Tuple[int, int] = None, diagnostics: List[Diagnostic] = None):
        self.diagnostics = diagnostics or []
        super().__init__(message, pos=pos)

class TSRuntimeError(TSError):
    """运行时错误（未捕获）"""
    pass

class TSNameError(TSRuntimeError):
    """变量未定义"""
    pass

class TSTypeError(TSRuntimeError):
    """类型错误（不支持运算、成员不存在等）"""
    pass

class TSImportError(TSRuntimeError):
    """模块导入失败"""
    pass

class TSConstError(TSRuntimeError):
    """常量修改尝试"""
    pass

class TSAddressError(TSRuntimeError):
    """地址无效"""
    pass

class TSAnnotationError(TSRuntimeError):
    """注解不存在"""
    pass

class TSArithError(TSRuntimeError):
    """算术域错误（整除/取余除零）"""
    pass

class TSControlError(TSRuntimeError):
    """控制流错误（break/continue 不在循环、跳出层数不足）"""
    pass
```

---

## 2. 诊断信息结构

```python
from dataclasses import dataclass
from typing import Tuple, List, Optional

@dataclass
class Diagnostic:
    code: str                    # 错误码（如 "E001", "W001"）
    message: str                 # 人类可读消息
    position: Tuple[int, int]    # (line, column), 1-based
    severity: str                # "error" / "warning" / "info"
    source: str                  # 源文件路径或 "<repl>"
    snippet: str                 # 错误位置源码片段

@dataclass
class TSCompileError(TSError):
    diagnostics: List[Diagnostic] = None
```

---

## 3. 错误码对照表

### 3.1 编译期错误 (E0xx)

| 错误码 | 类别 | 消息模板 | 触发场景 |
|--------|------|----------|----------|
| E001 | 词法 | "Illegal character: {char}" | 非法字符 |
| E002 | 语法 | "Unexpected token: {token}" | 语法错误 |
| E003 | 语法 | "Unclosed string literal" | 字符串未闭合 |
| E004 | 语法 | "Unclosed annotation" | 注解未闭合 |
| E005 | 语法 | "Invalid identifier: {name}" | 标识符含数字 |
| E006 | 语法 | "Expected {expected}, got {got}" | Token 不匹配 |
| E007 | 语法 | "Invalid escape sequence: \\{char}" | 字符串非法转义 |
| E008 | 语法 | "Number literal must have decimal point" | Number 字面量无小数点 |

### 3.2 编译期语义错误 (E1xx)

| 错误码 | 类别 | 消息模板 | 触发场景 |
|--------|------|----------|----------|
| E100 | 导入 | "Ambiguous import path: {path}" | 导入歧义 |
| E101 | 导入 | "Circular dependency detected" | 循环依赖 |
| E102 | 导入 | "Module not found: {path}" | 模块不存在 |
| E103 | 导入 | "Internal path not found in library: {path}" | .tscl 内部路径不存在 |
| E104 | 声明 | "Duplicate identifier: {name}" | 同作用域重复声明 |
| E105 | 声明 | "Consecutive declaration count must be >= 1" | 连续声明 N < 1 |
| E106 | 声明 | "Consecutive declaration operand must be integer" | 连续声明操作数非整数 |

### 3.3 运行时错误 (E2xx)

| 错误码 | 类别 | 消息模板 | 触发场景 |
|--------|------|----------|----------|
| E200 | 名字 | "Variable '{name}' not defined" | 变量未定义 |
| E201 | 成员 | "Member '{name}' not found" | 成员不存在 |
| E202 | 类型 | "Type '{type}' does not support operator '{op}'" | 运算符重载缺失 |
| E203 | 类型 | "Type '{type}' does not support subscript" | 下标操作不支持 |
| E204 | 类型 | "Type '{type}' does not support member access" | 成员访问不支持 |
| E205 | 常量 | "Cannot assign to constant" | 常量修改尝试 |
| E206 | 常量 | "Constant member already exists" | 常量成员重复定义 |
| E207 | 算术 | "Division by zero in integer divide" | 整除除零 |
| E208 | 算术 | "Modulo by zero" | 取余除零 |
| E209 | 算术 | "Negative factorial argument" | 阶乘负数参数 |
| E210 | 控制流 | "Multi-level return depth exceeded" | 跳出层数不足 |
| E211 | 控制流 | "Break/continue not in loop" | break/continue 不在循环 |
| E212 | 控制流 | "Top-level return must be integer" | 顶层返回非整数 |
| E213 | 注解 | "Annotation not found: {key}" | 注解不存在 |
| E214 | 地址 | "Address {addr} not allocated" | 地址无效 |
| E215 | 地址 | "Address {addr} is constant" | 地址只读 |

### 3.4 警告 (W0xx)

| 错误码 | 消息模板 | 触发场景 |
|--------|----------|----------|
| W001 | "Import shadows existing identifier: {name}" | 导入覆盖同名标识符 |
| W002 | "Unused variable: {name}" | 变量声明未使用 |
| W003 | "Deprecated API: {name}" | 使用废弃 API |
| W004 | "Implicit declaration of variable: {name}" | 隐式声明变量 |

---

## 4. 诊断信息输出示例

### 4.1 编译错误

```
Error: Compile error in app.tsuc:3:5
  E002: Unexpected token: '+'
  >     a = `1 + `2;
  >     ^

Error: Compile error in app.tsuc
  E100: Ambiguous import path: 'lib'
  Note: Found multiple matches: lib.tsuc, lib.tscc, lib/
  Help: Use explicit suffix: 'lib.tsuc', 'lib/', or absolute path
```

### 4.2 运行时错误

```
Runtime Error: E202: Type 'MyType' does not support operator '+'
  at app.tsuc:10:5
  >     std.println(a + b);
  >         ^~~
  Note: Register 'addition' special member on MyType
```

### 4.3 详细诊断模式 (`--verbose`)

```
[ERROR] app.tsuc:3:5: E002 Unexpected token: '+'
  Context: Parsing binary expression
  Expected: operand, got: '+'
  Source line: a = `1 + `2;
                        ^
[ERROR] app.tsuc:10:5: E202 Type 'MyType' does not support operator '+'
  Context: Evaluating binary expression
  Left type: MyType, Right type: MyType
  Missing special member: addition
  Suggestion: *** MyType.addition = [*self, *other] => { ... };
```

---

## 5. 错误处理最佳实践

### 5.1 捕获与转换

```python
try:
    result = interp.run_source(user_code)
except TSCompileError as e:
    for diag in e.diagnostics:
        log.error(f"[{diag.code}] {diag.source}:{diag.position[0]}:{diag.position[1]}")
        log.error(f"  {diag.message}")
        if diag.snippet:
            log.error(f"  > {diag.snippet}")
except TSNameError as e:
    log.error(f"Undefined variable: {e.message}")
except TSTypeError as e:
    log.error(f"Type error: {e.message}")
except TSImportError as e:
    log.error(f"Import failed: {e.message}")
except TSArithError as e:
    log.error(f"Arithmetic error: {e.message}")
except TSRuntimeError as e:
    log.error(f"Runtime error: {e.message}")
```

### 5.2 用户友好错误页 (Web 场景)

```python
def format_error_for_web(error: TSError) -> dict:
    base = {
        "type": error.__class__.__name__,
        "message": error.message,
        "code": error.code
    }
    if error.pos:
        base["position"] = {"line": error.pos[0], "column": error.pos[1]}
    if isinstance(error, TSCompileError):
        base["diagnostics"] = [
            {
                "code": d.code,
                "message": d.message,
                "position": {"line": d.position[0], "column": d.position[1]},
                "severity": d.severity,
                "snippet": d.snippet
            }
            for d in error.diagnostics
        ]
    return base
```

---

## 6. 调试支持

### 6.1 堆栈追踪 (计划中)

```python
# 未来版本
try:
    interp.run_source(code)
except TSRuntimeError as e:
    print(e.stack_trace())
    # 输出:
    # Traceback (most recent call last):
    #   File "app.tsuc", line 10, in <module>
    #     result = divide(`10`, `0)
    #   File "math.tsuc", line 5, in divide
    #     $ a / b;
    # Runtime Error: E207 Division by zero in integer divide
```

### 6.2 断点调试 (计划中)

```python
# 设置断点回调
interp.set_breakpoint_callback(lambda frame: {
    if frame.line == 10 and frame.file == "app.tsuc":
        debugger.break_here()
})
```

---

## 相关链接

- [编译器 API](compiler_api.md) — TSCompileError、Diagnostic
- [解释器嵌入](embedding.md) — 捕获与处理错误
- [核心执行器](interpreter.md) — 控制流信号与错误信号
- [语言参考：错误处理](../reference/errors.md) — 语言层面错误处理语义
- [专题指南：错误处理](../howto/error_handling.md) — 实战错误处理模式