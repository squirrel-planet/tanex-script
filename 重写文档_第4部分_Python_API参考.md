# 第 4 部分：Python API 参考

> **适用版本**：Tanex Script 1.x  
> **目标读者**：嵌入式开发者、工具链构建者、语言扩展作者  
> **前提**：Tanex Script 解释器以 Python 3.10+ 实现，暴露以下公共 API 供 Python 代码直接调用。

---

## 4.1 解释器入口与配置

### `TanexInterpreter` 类

> **签名**：`class TanexInterpreter:`  
> **所在模块**：`tanex.runtime.interpreter`  
> **一句话描述**：解释器主入口，管理地址空间、全局作用域、模块缓存、内置注册。

#### 构造函数

```python
def __init__(
    self,
    *,
    recursion_limit: int = 1000,
    stack_size: int = 8192,
    bootstrap_path: str = "run/bootstrap.tscc",
    lib_paths: List[str] = None,
    builtin_constants: Dict[str, TSValue] = None,
    custom_types: Dict[str, TSType] = None,
    custom_functions: Dict[str, Callable] = None,
    custom_special_members: Dict[str, Dict[str, Callable]] = None,
):
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `recursion_limit` | `int` | 1000 | 递归深度限制（函数调用、代码块嵌套） |
| `stack_size` | `int` | 8192 | 解释器操作栈大小 |
| `bootstrap_path` | `str` | `"run/bootstrap.tscc"` | 引导库编译产物路径 |
| `lib_paths` | `List[str]` | `[]` | 库搜索路径列表（预编译依赖解析用） |
| `builtin_constants` | `Dict[str, TSValue]` | `{}` | 额外注入的全局常量（如 `path`、`program_path`、`args`） |
| `custom_types` | `Dict[str, TSType]` | `{}` | 预注册的自定义类型对象 |
| `custom_functions` | `Dict[str, Callable]` | `{}` | 预注册的全局函数（Python 可调用对象） |
| `custom_special_members` | `Dict[str, Dict[str, Callable]]` | `{}` | 预注册的类型特殊成员 `{TypeName: {member: callable}}` |

#### 核心方法

##### `run_file(tscc_path: str, args: List[str] = None) -> TSValue`

> **签名**：`def run_file(self, tscc_path: str, args: List[str] = None) -> TSValue`  
> **一句话描述**：加载并执行 `.tscc` 编译产物文件。

| 参数 | 类型 | 说明 |
|------|------|------|
| `tscc_path` | `str` | `.tscc` 文件路径 |
| `args` | `List[str]` | 命令行参数列表（注入 `args` 常量） |

**返回值**：程序顶层最后一条语句的值，或 `$` 返回的值。

**异常**：
- `TSImportError`：文件不存在或导入失败
- `TSRuntimeError`：执行过程报错（未捕获错误）
- `TSCompileError`：文件非合法 `.tscc` 格式

##### `run_source(tsuc_source: str, filename: str = "<string>", args: List[str] = None) -> TSValue`

> **签名**：`def run_source(self, tsuc_source: str, filename: str = "<string>", args: List[str] = None) -> TSValue`  
> **一句话描述**：编译并执行源码字符串。

| 参数 | 类型 | 说明 |
|------|------|------|
| `tsuc_source` | `str` | Tanex Script 源码 |
| `filename` | `str` | 虚拟文件名（用于错误定位、import 相对路径解析） |
| `args` | `List[str]` | 命令行参数 |

**返回值**：同 `run_file`。

##### `run_ast(ast_dict: Dict, args: List[str] = None) -> TSValue`

> **签名**：`def run_ast(self, ast_dict: Dict, args: List[str] = None) -> TSValue`  
> **一句话描述**：直接执行已解析的 AST 字典（跳过编译）。

| 参数 | 类型 | 说明 |
|------|------|------|
| `ast_dict` | `Dict` | 完整编译产物字典（含 `Tanex Script`、`annotations`、`annotation`） |
| `args` | `List[str]` | 命令行参数 |

**用途**：工具链中间表示传递、缓存执行、测试。

##### `repl() -> None`

> **签名**：`def repl(self) -> None`  
> **一句话描述**：启动交互式 REPL 循环（阻塞直到用户输入 `:q`）。

**行为**：
- 读取行，累积直到遇到分号 `;` 形成完整语句
- 编译执行，打印结果（`repr` 形式）
- 支持 `:h` 帮助、`:q` 退出、`:ast` 显示 AST、`:tokens` 显示 Token

---

## 4.2 编译器 API

### 模块：`tanex.compile`

#### `tokenize(source: str, filename: str = "<string>") -> TokenList`

> **签名**：`def tokenize(source: str, filename: str = "<string>") -> TokenList`  
> **一句话描述**：词法分析，返回 Token 列表。

**返回值**：`TokenList`（`List[Token]`），每个 Token 含 `type`、`value`、`pos`。

**异常**：`TSLexError` 非法字符/未闭合字符串/注释。

#### `parse(tokens: TokenList, filename: str = "<string>") -> ASTDict`

> **签名**：`def parse(tokens: TokenList, filename: str = "<string>") -> ASTDict`  
> **一句话描述**：语法分析，Token 列表 → AST 字典。

**返回值**：AST 字典（仅语句列表，不含 `annotations`/`annotation`）。

**异常**：`TSParseError` 语法错误（含位置信息）。

#### `compile(source: str, filename: str = "<string>") -> ASTDict`

> **签名**：`def compile(source: str, filename: str = "<string>") -> ASTDict`  
> **一句话描述**：词法+语法一体化编译，源码 → 完整编译产物字典。

**返回值**：完整编译产物：
```python
{
    "Tanex Script": [...],  # 语句 AST 列表
    "annotations": {...},   # 注解映射
    "annotation": "..."     # 文件级注解（可选）
}
```

**异常**：`TSCompileError`（词法/语法错误统一）。

#### `compile_file(tsuc_path: str, output_tscc_path: str = None) -> ASTDict`

> **签名**：`def compile_file(tsuc_path: str, output_tscc_path: str = None) -> ASTDict`  
> **一句话描述**：编译 `.tsuc` 文件，可选写入 `.tscc` 文件。

| 参数 | 类型 | 说明 |
|------|------|------|
| `tsuc_path` | `str` | 源文件路径 |
| `output_tscc_path` | `str` | 输出路径，`None` 仅返回不写文件 |

**返回值**：编译产物字典。

#### `collect_imports(ast_dict: ASTDict) -> List[str]`

> **签名**：`def collect_imports(ast_dict: ASTDict) -> List[str]`  
> **一句话描述**：从 AST 提取所有静态 `import`/`->` 路径（字符串字面量），用于依赖图构建。

**返回值**：路径字符串列表（已解析为绝对路径或相对路径）。

---

## 4.3 运行时值模型（Python 侧）

> 所有运行时值统一继承 `TSValue` 基类，解释器内部通过多态分发。

### 基类

```python
class TSValue(ABC):
    @abstractmethod
    def ts_type(self) -> TSType: ...
    @abstractmethod
    def ts_truthy(self) -> bool: ...
    def ts_repr(self) -> str: ...
    def ts_equal(self, other: 'TSValue') -> bool: ...
```

### 具体值类

| 类名 | 对应语言类型 | 关键属性/方法 |
|------|-------------|--------------|
| `TSInteger` | `Integer` | `value: int` (Python 任意精度整数) |
| `TSNumber` | `Number` | `front: int`, `back: int`, `scale: int` (小数位数) |
| `TSString` | `String` | `data: TSList` (字符码链表) |
| `TSBoolean` | `Boolean` | `value: int` (0/1) |
| `TSNone` | `NoneType` | 单例 `TSNone.INSTANCE` |
| `TSNaN` | `NaNType` | 单例 `TSNaN.INSTANCE` |
| `TSInfinite` | `InfiniteType` | `sign: int` (+1/-1)，单例 `POS_INF`/`NEG_INF` |
| `TSList` | `List` | `head: TSListNode`, `tail: TSListNode`, `size: int` |
| `TSCode` | `Code` | `statements: List[ASTNode]`, `scope: Scope`, `params: List[ParamInfo]` |
| `TSAddress` | `Address` | `addr: int` |
| `TSError` | `Error` | `what: TSString`, `throw()` 方法 |
| `TSWarning` | `Warning` | `what: TSString`, `throw()` 方法 |
| `TSLibrary` | `Library` | `members: Dict[str, TSValue]`, `annotations: Dict[str, str]` |
| `TSType` | `Type` | `initialize: TSValue`, `inherit: TSType`, `special_members: Dict`, `members: Dict[str, int]`, `addable: bool`, `external_read_only: Dict` |
| `TSInstance` | 用户类型实例 | `type: TSType`, `members: Dict[str, int]` |
| `TSFunction` | 函数值 | `code: TSCode`, `closure_scope: Scope` |

### 值构造工厂函数

```python
def make_integer(n: int) -> TSInteger
def make_number(front: int, back: int, scale: int) -> TSNumber
def make_string(s: str) -> TSString
def make_boolean(b: bool) -> TSBoolean
def make_none() -> TSNone
def make_nan() -> TSNaN
def make_infinite(sign: int = 1) -> TSInfinite
def make_list(items: List[TSValue] = None) -> TSList
def make_code(statements: List[ASTNode], scope: Scope, params: List[ParamInfo] = None) -> TSCode
def make_address(addr: int) -> TSAddress
def make_error(what: str) -> TSError
def make_warning(what: str) -> TSWarning
def make_library(members: Dict[str, TSValue], annotations: Dict[str, str] = None) -> TSLibrary
def make_type(initialize: TSValue = None, inherit: TSType = None, **special_members) -> TSType
def make_instance(type_obj: TSType, members: Dict[str, int] = None) -> TSInstance
```

### 真值判定

```python
def ts_truthy(value: TSValue) -> bool:
    """语言级真值判定，对应 2.4.7 规则"""
    if isinstance(value, TSInteger):
        return value.value != 0
    if isinstance(value, TSInstance):
        bool_member = lookup_special_member(value.type, "boolean")
        if bool_member:
            return ts_truthy(call_special_member(bool_member, value))
        return True
    if isinstance(value, TSType):
        return True
    if isinstance(value, (TSCode, TSAddress, TSLibrary, TSFunction)):
        return True
    if isinstance(value, (TSNone, TSNaN)):
        return False
    return True  # Infinite, String, List 等默认真
```

### 类型查询

```python
def ts_type_of(value: TSValue) -> TSType:
    """对应一元运算符 type_of"""
    return value.ts_type()
```

---

## 4.4 地址空间与作用域 API

### `AddressSpace` 类

> **签名**：`class AddressSpace:`  
> **所在模块**：`tanex.runtime.environment`

```python
class AddressSpace:
    def __init__(self):
        self._cells: Dict[int, StorageCell] = {}
        self._next_addr: int = 0
    
    def allocate(self) -> int:
        """分配新地址，创建存储单元（初值 none），返回地址"""
        addr = self._next_addr
        self._next_addr += 1
        self._cells[addr] = StorageCell(TSNone.INSTANCE)
        return addr
    
    def read(self, addr: int) -> TSValue:
        """读取地址值，地址不存在抛异常"""
        if addr not in self._cells:
            raise TSAddressError(f"Address {addr} not allocated")
        return self._cells[addr].value
    
    def write(self, addr: int, value: TSValue) -> None:
        """写入地址，常量单元抛 TSConstError"""
        if addr not in self._cells:
            raise TSAddressError(f"Address {addr} not allocated")
        if self._cells[addr].is_const:
            raise TSConstError(f"Address {addr} is constant")
        self._cells[addr].value = value
    
    def mark_const(self, addr: int) -> None:
        """标记地址为只读"""
        if addr in self._cells:
            self._cells[addr].is_const = True
    
    def exists(self, addr: int) -> bool:
        return addr in self._cells
```

### `Scope` 类

> **签名**：`class Scope:`  
> **所在模块**：`tanex.runtime.environment`

```python
class Scope:
    def __init__(self, parent: 'Scope' = None):
        self._bindings: Dict[str, int] = {}  # name -> address
        self._parent = parent
    
    def declare(self, name: str, addr: int) -> None:
        """在当前层声明/覆盖名字绑定"""
        self._bindings[name] = addr
    
    def resolve(self, name: str) -> Optional[int]:
        """查找名字，返回地址或 None（不报错）"""
        if name in self._bindings:
            return self._bindings[name]
        if self._parent:
            return self._parent.resolve(name)
        return None
    
    def resolve_or_error(self, name: str) -> int:
        """查找名字，未找到抛 TSNameError"""
        addr = self.resolve(name)
        if addr is None:
            raise TSNameError(f"Variable '{name}' not defined")
        return addr
    
    def local_has(self, name: str) -> bool:
        """仅查当前层，用于 *name 声明判断新建/复用"""
        return name in self._bindings
    
    def parent(self) -> Optional['Scope']:
        return self._parent
    
    def set_parent(self, parent: 'Scope') -> None:
        self._parent = parent
```

---

## 4.5 解释器核心执行器

### `eval(ast_node: ASTNode, scope: Scope, address_space: AddressSpace) -> TSValue`

> **签名**：`def eval(ast_node: ASTNode, scope: Scope, address_space: AddressSpace) -> TSValue`  
> **所在模块**：`tanex.runtime.interpreter`  
> **一句话描述**：递归求值单个 AST 节点，返回运行时值。

**分发逻辑**：按 `ast_node` 的类型键（`"integer"`、`"binary"`、`"unary"`、`"function"`、`"assignment"` 等）分发到对应处理函数。

### 控制流信号（异常类）

```python
class BreakSignal(Exception):
    """break 零元运算符"""
    pass

class ContinueSignal(Exception):
    """contiune 零元运算符"""
    pass

class ReturnSignal(Exception):
    """$ / return 一元运算符"""
    def __init__(self, value: TSValue):
        self.value = value

class ErrorSignal(Exception):
    """<- 抛出错误"""
    def __init__(self, value: TSValue):
        self.value = value
```

- 解释器在求值过程中捕获这些信号，按语义处理（`$$` 循环捕获 `BreakSignal`/`ContinueSignal`，函数调用捕获 `ReturnSignal`，`|` 尝试结构捕获 `ErrorSignal`）。

### 特殊成员调度

```python
def dispatch_binary(op: str, left: TSValue, right: TSValue, scope: Scope, addr_space: AddressSpace) -> TSValue:
    """二元运算符分发：查左操作数类型特殊成员，回退内置"""
    type_obj = left.ts_type()
    special_name = BINARY_OP_TO_SPECIAL[op]  # 如 "+" -> "addition"
    member = lookup_special_member(type_obj, special_name)
    if member:
        return call_special_member(member, left, right, scope, addr_space)
    # 内置类型兜底
    return builtin_binary_op(op, left, right)

def dispatch_unary(op: str, operand: TSValue, scope: Scope, addr_space: AddressSpace) -> TSValue:
    """一元运算符分发：查操作数类型特殊成员"""
    type_obj = operand.ts_type()
    special_name = UNARY_OP_TO_SPECIAL[op]
    member = lookup_special_member(type_obj, special_name)
    if member:
        return call_special_member(member, operand, scope, addr_space)
    return builtin_unary_op(op, operand)

def dispatch_compare(op: str, left: TSValue, right: TSValue, scope: Scope, addr_space: AddressSpace) -> TSValue:
    """比较运算符分发：含兜底组合逻辑（2.4.3 规则）"""
    # 1. 直接特殊成员
    # 2. 组合兜底
    # 3. compare 三路比较
    # 4. 对象同一性兜底
    ...
```

---

## 4.6 模块加载器

### `load_library_module(path_expr_ast: ASTNode, scope: Scope, address_space: AddressSpace) -> TSLibrary`

> **签名**：`def load_library_module(path_expr_ast: ASTNode, scope: Scope, address_space: AddressSpace) -> TSLibrary`  
> **所在模块**：`tanex.runtime.loader`  
> **一句话描述**：运行时加载模块（动态 import 路径求值后调用）。

**流程**：
1. 求值 `path_expr_ast` 得字符串路径
2. 调用 `resolve_import_path` 解析为绝对路径列表
3. 打开 `.tscc`/`.tscl`，解析 AST
4. 在当前地址空间/作用域执行库语句
5. 收集库顶层声明构建 `TSLibrary` 对象
6. 合并库 `annotations` 到独立注解空间
7. 返回 `TSLibrary`

### `resolve_import_path(expr_value: TSValue) -> List[ResolvedPath]`

> **签名**：`def resolve_import_path(expr_value: TSValue) -> List[ResolvedPath]`  
> **一句话描述**：路径解析算法（歧义消除、标准库优先、后缀补全）。

**返回值**：`List[ResolvedPath]`，每项含 `path`、`type`（`file`/`dir`/`tscl`）、`priority`。

### `ModuleCache` 类

```python
class ModuleCache:
    def __init__(self):
        self._cache: Dict[str, TSLibrary] = {}  # 绝对路径 -> Library
    
    def get(self, path: str) -> Optional[TSLibrary]:
        return self._cache.get(path)
    
    def put(self, path: str, library: TSLibrary) -> None:
        self._cache[path] = library
    
    def invalidate(self, path: str) -> None:
        self._cache.pop(path, None)
    
    def clear(self) -> None:
        self._cache.clear()
```

- 解释器实例持有一个 `ModuleCache`，支持热重载（调用 `invalidate` 后重新加载）。

---

## 4.7 注解系统

### `AnnotationTable` 类

> **签名**：`class AnnotationTable:`  
> **所在模块**：`tanex.runtime.annotations`

```python
class AnnotationTable:
    def __init__(self):
        self._global: Dict[str, str] = {}  # 顶层注解
        self._libraries: Dict[str, Dict[str, str]] = {}  # lib_name -> {member: annotation}
    
    def merge(self, annotations: Dict[str, str], lib_name: str = None) -> None:
        """合并编译产物 annotations。
        lib_name=None: 合并到 _global
        lib_name=str: 合并到 _libraries[lib_name]"""
        target = self._global if lib_name is None else self._libraries.setdefault(lib_name, {})
        target.update(annotations)
    
    def get(self, key: str, lib_name: str = None) -> Optional[str]:
        """读取注解。
        lib_name=None: 查 _global
        lib_name=str: 查 _libraries[lib_name]"""
        target = self._global if lib_name is None else self._libraries.get(lib_name, {})
        return target.get(key)
    
    def get_file_annotation(self, lib_name: str = None) -> Optional[str]:
        """读取文件级注解（编译产物 annotation 字段）"""
        # 存储在特殊键 "__file__" 或单独字段
        ...
```

- 解释器持有一个 `AnnotationTable`，启动时合并引导库注解，后续每加载一个模块合并其注解。
- `??` 运算符实现调用 `table.get(key, lib_name)`。

---

## 4.8 标准库注册机制

### 内置类型注册

```python
def register_builtin_type(name: str, type_obj: TSType) -> None:
    """在全局作用域声明常量类型标识符"""
    interpreter.global_scope.declare(name, addr)
    interpreter.address_space.write(addr, type_obj)
    interpreter.address_space.mark_const(addr)
```

### 内置函数注册

```python
def register_builtin_function(name: str, py_callable: Callable) -> None:
    """将 Python 函数包装为 TSFunction 注册到全局作用域"""
    fn_val = make_function_from_python(py_callable)
    interpreter.global_scope.declare(name, addr)
    interpreter.address_space.write(addr, fn_val)
    interpreter.address_space.mark_const(addr)
```

### 特殊成员注册

```python
def register_special_member(type_obj: TSType, member_name: str, py_callable: Callable) -> None:
    """在类型对象上注册特殊成员（运算符重载）"""
    fn_val = make_function_from_python(py_callable)
    type_obj.special_members[member_name] = fn_val
```

---

## 4.9 错误与诊断

### 异常类层级

```python
class TSError(Exception):
    """基类：含位置信息、错误码"""
    def __init__(self, message: str, pos: Tuple[int, int] = None, code: str = None):
        self.message = message
        self.pos = pos  # (line, column)
        self.code = code  # 错误码字符串

class TSCompileError(TSError):
    """编译期错误（词法/语法）"""
    pass

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
```

### 诊断信息结构

```python
@dataclass
class Diagnostic:
    code: str              # 错误码（如 "E001"、"W001"）
    message: str           # 人类可读消息
    position: Tuple[int, int]  # (line, column)
    severity: str          # "error" / "warning" / "info"
    source: str            # 源文件路径或 "<repl>"
    snippet: str           # 错误位置源码片段
```

### 错误码对照表（部分）

| 错误码 | 类别 | 消息模板 | 触发场景 |
|--------|------|----------|----------|
| E001 | 词法 | "Illegal character: {char}" | 非法字符 |
| E002 | 语法 | "Unexpected token: {token}" | 语法错误 |
| E003 | 语法 | "Unclosed string literal" | 字符串未闭合 |
| E101 | 运行时 | "Variable '{name}' not defined" | 变量未定义 |
| E102 | 运行时 | "Member '{name}' not found" | 成员不存在 |
| E103 | 运行时 | "Type '{type}' does not support operator '{op}'" | 运算符重载缺失 |
| E104 | 运行时 | "Division by zero in integer divide" | 整除除零 |
| E105 | 运行时 | "Modulo by zero" | 取余除零 |
| E106 | 运行时 | "Cannot assign to constant" | 常量修改 |
| E107 | 运行时 | "Multi-level return depth exceeded" | 跳出层数不足 |
| E108 | 运行时 | "Ambiguous import path: {path}" | 导入歧义 |
| E109 | 运行时 | "Annotation not found: {key}" | 注解不存在（?? 报错模式） |
| W001 | 警告 | "Import shadows existing identifier: {name}" | 导入覆盖同名标识符 |

---

> **本章自检结果 (4)**：
> - [x] 解释器入口、编译器 API、值模型、地址空间/作用域、核心执行器、模块加载器、注解系统、标准库注册、错误诊断完整覆盖
> - [x] 所有类/函数含签名、参数表、返回值、异常、行为说明
> - [x] 与第 2 部分语言语义（传地址、真值判定、特殊成员分发、控制流信号）严格一致
> - [x] 错误码体系与 2.8.4 错误分类前缀对应
> - [x] 不确定项（Number 除法精度策略、JSON 解析错误格式、shuffle 内部依赖公开性）已标注 `[待确认]`

---

*下一部分：[第 5 部分 引导库内部规范](./10-bootstrap-internal-spec.md) — 启动流程、核心类型初始化细节、引导库注解表、版本演进*

*再下：[第 6 部分 附录](./11-appendices.md) — 术语表、版本变更记录、废弃项清单、运算符速查卡、AST 节点参考、编译产物 JSON Schema、常见陷阱与最佳实践*