# 编译器 API

> 程序化调用 Tanex Script 编译器：词法分析、语法分析、一体化编译、依赖提取。

---

## 1. 模块导入

```python
import tanex.compile as compile
from tanex.compile import (
    tokenize, parse, compile, compile_file, collect_imports,
    TSCompileError, TSLexError, TSParseError
)
```

---

## 2. 词法分析

### 2.1 `tokenize(source: str, filename: str = "<string>") -> TokenList`

```python
source = '''
    import "standard" = *std;
    std.standard_output << "Hello\n";
'''

tokens = compile.tokenize(source, filename="app.tsuc")
# tokens: List[Token]
```

**Token 结构**：
```python
class Token:
    type: str          # "identifier", "integer", "string", "operator", "keyword", "annotation", ...
    value: str         # 原始文本
    pos: Tuple[int, int]  # (line, column), 1-based
```

**示例输出**：
```python
[
    Token(type="import", value="import", pos=(1, 1)),
    Token(type="string", value='"standard"', pos=(1, 8)),
    Token(type="assign", value="=", pos=(1, 19)),
    Token(type="identifier", value="std", pos=(1, 21)),
    Token(type="semicolon", value=";", pos=(1, 24)),
    Token(type="identifier", value="std", pos=(2, 1)),
    Token(type="member", value=".", pos=(2, 4)),
    Token(type="identifier", value="standard_output", pos=(2, 5)),
    Token(type="output", value="<<", pos=(2, 20)),
    Token(type="string", value='"Hello\\n"', pos=(2, 23)),
    Token(type="semicolon", value=";", pos=(2, 32)),
]
```

### 2.2 异常

```python
try:
    tokens = compile.tokenize(invalid_source)
except TSLexError as e:
    # 非法字符、未闭合字符串/注释
    print(f"Lexical error at {e.pos}: {e.message}")
```

---

## 3. 语法分析

### 3.1 `parse(tokens: TokenList, filename: str = "<string>") -> ASTDict`

```python
tokens = compile.tokenize(source)
ast = compile.parse(tokens, filename="app.tsuc")
# ast: Dict (仅语句列表，不含 annotations)
```

**返回 AST 字典**：
```python
{
    "statements": [
        {"import": {...}},
        {"function": {...}}
    ]
}
```

### 3.2 异常

```python
try:
    ast = compile.parse(tokens)
except TSParseError as e:
    print(f"Parse error at {e.pos}: {e.message}")
    print(f"Expected: {e.expected}, Got: {e.got}")
```

---

## 4. 一体化编译

### 4.1 `compile(source: str, filename: str = "<string>") -> ASTDict`

```python
source = '''
    @ # My Module #;
    import "standard" = *std;
    std.standard_output << "Hello\n";
'''

ast_dict = compile.compile(source, filename="app.tsuc")
```

**返回完整编译产物**：
```python
{
    "Tanex Script": [
        # 语句 AST 列表
    ],
    "annotations": {
        # 注解映射
    },
    "annotation": "My Module",  # 文件级注解（可选）
    "version": 1  # 编译产物格式版本 [待确认]
}
```

### 4.2 `compile_file(tsuc_path: str, output_tscc_path: str = None) -> ASTDict`

```python
# 编译文件并可选写入 .tscc
ast_dict = compile.compile_file("src/main.tsuc", "build/main.tscc")

# 仅编译不写文件
ast_dict = compile.compile_file("src/main.tsuc")
```

### 4.3 异常

```python
try:
    ast_dict = compile.compile(source)
except TSCompileError as e:
    for diag in e.diagnostics:
        print(f"{diag.severity.upper()} [{diag.position}]: {diag.message}")
        print(f"  Code: {diag.code}")
        print(f"  Snippet: {diag.snippet}")
```

---

## 5. 依赖提取

### 5.1 `collect_imports(ast_dict: ASTDict) -> List[str]`

```python
ast_dict = compile.compile(source)
deps = compile.collect_imports(ast_dict)
# ["lib.tscc", "standard.tscl", "encoding/ascii.tscl", ...]
```

- 仅提取**静态字符串字面量**路径的 import
- 动态表达式路径被忽略
- 返回已解析的绝对路径或相对路径

---

## 6. 诊断信息结构

### 6.1 `Diagnostic` 数据类

```python
from dataclasses import dataclass

@dataclass
class Diagnostic:
    code: str              # 错误码 (如 "E001", "W001")
    message: str           # 人类可读消息
    position: Tuple[int, int]  # (line, column)
    severity: str          # "error" / "warning" / "info"
    source: str            # 源文件路径或 "<repl>"
    snippet: str           # 错误位置源码片段
```

### 6.2 `TSCompileError.diagnostics`

```python
try:
    compile.compile(source)
except TSCompileError as e:
    for diag in e.diagnostics:
        print(f"[{diag.code}] {diag.source}:{diag.position[0]}:{diag.position[1]}")
        print(f"  {diag.message}")
        print(f"  > {diag.snippet}")
```

---

## 7. 错误码对照表

| 错误码 | 类别 | 消息模板 | 触发场景 |
|--------|------|----------|----------|
| E001 | 词法 | "Illegal character: {char}" | 非法字符 |
| E002 | 语法 | "Unexpected token: {token}" | 语法错误 |
| E003 | 语法 | "Unclosed string literal" | 字符串未闭合 |
| E004 | 语法 | "Unclosed annotation" | 注解未闭合 |
| E005 | 语法 | "Invalid identifier: {name}" | 标识符含数字 |
| E006 | 语法 | "Expected {expected}, got {got}" | Token 不匹配 |
| E100 | 编译 | "Ambiguous import path: {path}" | 导入歧义 |
| E101 | 编译 | "Circular dependency detected" | 循环依赖 |
| W001 | 警告 | "Import shadows existing identifier: {name}" | 导入覆盖同名标识符 |

---

## 8. 完整示例：构建工具链

```python
import tanex.compile as compile
from tanex.compile import TSCompileError
import json
import sys

def build_project(src_dir: str, out_dir: str):
    """编译整个项目"""
    import os
    from pathlib import Path
    
    # 收集所有 .tsuc 文件
    tsuc_files = list(Path(src_dir).rglob("*.tsuc"))
    
    # 编译每个文件
    for tsuc in tsuc_files:
        rel = tsuc.relative_to(src_dir)
        out_tscc = Path(out_dir) / rel.with_suffix(".tscc")
        out_tscc.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            ast = compile.compile_file(str(tsuc), str(out_tscc))
            print(f"✓ {rel}")
        except TSCompileError as e:
            print(f"✗ {rel}: {e}")
            sys.exit(1)
    
    print(f"Build successful: {len(tsuc_files)} files compiled to {out_dir}")

if __name__ == "__main__":
    build_project("src", "build")
```

---

## 相关链接

- [语言参考：语句](../reference/statements.md#92-编译产物-json-schema) — 编译产物完整 Schema
- [语言参考：模块系统](../reference/modules.md) — import/-> 语义与路径解析
- [扩展与嵌入：嵌入指南](embedding.md) — 解释器嵌入
- [错误与诊断](errors.md) — 完整错误体系
- [专题指南：测试策略](../howto/testing.md) — 编译器测试