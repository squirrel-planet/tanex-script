# 注解系统

> 编译期元数据在运行时的存储与读取机制。

---

## 1. 注解表 `AnnotationTable`

```python
class AnnotationTable:
    def __init__(self):
        self._global: Dict[str, str] = {}          # 顶层注解
        self._libraries: Dict[str, Dict[str, str]] = {}  # lib_name -> {member: annotation}
        self._file_annotations: Dict[str, str] = {}      # lib_name -> file_annotation
    
    def merge(self, annotations: Dict[str, str], lib_name: str = None) -> None:
        """
        合并编译产物 annotations。
        lib_name=None: 合并到 _global (用户文件、引导库、-> 引入)
        lib_name=str: 合并到 _libraries[lib_name] (import 引入)
        """
        target = self._global if lib_name is None else self._libraries.setdefault(lib_name, {})
        target.update(annotations)
    
    def merge_file_annotation(self, annotation: str, lib_name: str = None) -> None:
        """合并文件级注解"""
        if lib_name is None:
            # 用户文件文件级注解，仅保留最后一个
            self._file_annotations["__main__"] = annotation
        else:
            self._file_annotations[lib_name] = annotation
    
    def get(self, key: str, lib_name: str = None) -> Optional[str]:
        """
        读取注解，对应 ?? 运算符。
        lib_name=None: 查 _global (当前作用域、引导库、-> 引入的注解)
        lib_name=str: 查 _libraries[lib_name] (import 引入的库独立空间)
        """
        target = self._global if lib_name is None else self._libraries.get(lib_name, {})
        return target.get(key)
    
    def get_file_annotation(self, lib_name: str = None) -> Optional[str]:
        """读取文件级注解 (?? lib_name)"""
        return self._file_annotations.get(lib_name)
    
    def clear(self) -> None:
        self._global.clear()
        self._libraries.clear()
        self._file_annotations.clear()
```

---

## 2. 注解合并策略

### 2.1 启动时

```python
# 解释器初始化
annotation_table = AnnotationTable()

# 1. 合并引导库注解 (bootstrap.tscc 的 annotations)
bootstrap_ast = parse_tscc("run/bootstrap.tscc")
annotation_table.merge(bootstrap_ast.get("annotations", {}), lib_name=None)
if bootstrap_ast.get("annotation"):
    annotation_table.merge_file_annotation(bootstrap_ast["annotation"], lib_name=None)
```

### 2.2 加载用户文件

```python
def run_file(tscc_path: str, args: List[str] = None):
    ast_dict = parse_tscc(tscc_path)
    
    # 用户文件注解合并到全局 (覆盖同名引导注解)
    annotation_table.merge(ast_dict.get("annotations", {}), lib_name=None)
    if ast_dict.get("annotation"):
        annotation_table.merge_file_annotation(ast_dict["annotation"], lib_name=None)
    
    # 执行...
```

### 2.3 import 引入

```python
def load_library_module(path_expr_ast, scope, addr_space, lib_name):
    lib = _load_module_impl(path_expr_ast, scope, addr_space)
    
    # 库注解合并到独立空间
    annotation_table.merge(lib.annotations, lib_name=lib_name)
    if lib.file_annotation:
        annotation_table.merge_file_annotation(lib.file_annotation, lib_name=lib_name)
    
    return lib
```

### 2.4 -> 引入

```python
def eval_include(include_ast, scope, addr_space):
    path_val = eval(include_ast["include"]["path"], scope, addr_space)
    lib = load_library_module(include_ast, scope, addr_space, lib_name=None)
    
    # -> 注解直接合并到全局 (键冲突覆盖警告)
    annotation_table.merge(lib.annotations, lib_name=None)
    if lib.file_annotation:
        # 文件级注解：-> 引入不保留库的文件级注解
        pass
    
    return lib  # 返回值通常被忽略
```

---

## 3. 读取实现 (`??` 运算符)

```python
def eval_annotation_read(operand_ast: dict, scope: Scope, addr_space: AddressSpace) -> TSValue:
    """求值 ?? 运算符"""
    # operand 必须为标识符或 lib.member 成员访问链
    if operand_ast["type"] == "name":
        key = operand_ast["name"]["value"]
        lib_name = None
    elif operand_ast["type"] == "member":
        left = operand_ast["member"]["left"]
        right = operand_ast["member"]["right"]
        if left["type"] == "name" and right["type"] == "name":
            lib_name = left["name"]["value"]
            key = right["name"]["value"]
        else:
            raise TSTypeError("Annotation read operand must be identifier or lib.member")
    else:
        raise TSTypeError("Annotation read operand must be identifier or lib.member")
    
    content = annotation_table.get(key, lib_name)
    return make_string(content) if content is not None else TSNone.INSTANCE
```

---

## 4. 作用域规则

| 读取形式 | 查找空间 | 说明 |
|----------|----------|------|
| `?? name` | `_global` | 当前文件、引导库、-> 引入的注解 |
| `?? lib.member` | `_libraries["lib"]` | import 引入库的独立注解空间 |
| `?? Type.member` | `_global` (键为 `"Type.member"`) | 当前作用域的成员级注解 |
| `?? lib` | `_file_annotations["lib"]` | 库的文件级注解 |

**库隔离**：`import "lib" = *h;` 时，`lib` 的注解写入独立空间，**不平铺**到顶层。必须通过 `?? lib.member` 访问。

---

## 5. 编译期收集

### 5.1 词法分析阶段

```python
def tokenize(source: str) -> List[Token]:
    tokens = []
    i = 0
    while i < len(source):
        if source[i] == '@':
            # 解析注解
            annotation_token, i = parse_annotation(source, i)
            tokens.append(annotation_token)
        elif source[i] == '#':
            # 解析注释
            comment_token, i = parse_comment(source, i)
            tokens.append(comment_token)
        else:
            # 其他 token
            ...
    return tokens

def parse_annotation(source: str, start: int) -> Tuple[Token, int]:
    # @ ident # content #;
    # 返回 annotation Token，含 target 和 content
    pass
```

### 5.2 语法分析阶段

```python
def parse(tokens: List[Token]) -> ASTDict:
    annotations = {}
    file_annotation = None
    
    for token in tokens:
        if token.type == "annotation":
            if token.target:
                annotations[token.target] = token.content
            else:
                file_annotation = token.content
        # 其他语句解析...
    
    return {
        "Tanex Script": statements,
        "annotations": annotations,
        "annotation": file_annotation
    }
```

---

## 6. 性能考量

- **延迟构建字符串**：注解内容仅在 `??` 读取时构建 Python 字符串，编译产物中存储原始文本
- **内存效率**：注解表仅存储被引用的注解，未读取的不构建字符串对象
- **并发安全**：`AnnotationTable` 非线程安全，解释器单线程模型下无需锁

---

## 相关链接

- [语言参考：词法](../reference/lexical.md#注解) — 注解语法
- [语言参考：表达式](../reference/expressions.md#一元注解读取) — `??` 运算符
- [语言参考：模块系统](../reference/modules.md#7-库注解隔离机制) — 库注解隔离
- [核心执行器](interpreter.md) — 注解合并时机
- [模块加载器](loader.md) — import 注解处理
- [专题指南：元编程](../howto/metaprogramming.md) — 注解驱动开发实战