# 运行时值模型

> Tanex Script 运行时值的 Python 侧表示，供嵌入、扩展、工具开发使用。

---

## 1. 值类层级

```
TSValue (抽象基类)
├── TSInteger          # Integer (原类型，直接存储 int)
├── TSNumber           # Number (front/back/scale)
├── TSString           # String (底层 TSList 存储字符码)
├── TSBoolean          # Boolean (value: 0/1)
├── TSNone             # NoneType (单例)
├── TSNaN              # NaNType (单例)
├── TSInfinite         # InfiniteType (sign: +1/-1，单例)
├── TSList             # List (头尾指针、size、节点链表)
├── TSCode             # Code (statements、scope、params)
├── TSAddress          # Address (addr: int)
├── TSError            # Error (what: TSString、throw())
├── TSWarning          # Warning (what: TSString、throw())
├── TSLibrary          # Library (members、annotations)
├── TSType             # Type (initialize、inherit、special_members、members、addable、external_read_only)
├── TSInstance         # 用户类型实例 (type: TSType、members)
└── TSFunction         # 函数值 (code: TSCode、closure_scope: Scope)
```

---

## 2. 基类 `TSValue`

```python
from abc import ABC, abstractmethod
from typing import Tuple

class TSValue(ABC):
    @abstractmethod
    def ts_type(self) -> 'TSType':
        """返回值的类型对象"""
        pass
    
    @abstractmethod
    def ts_truthy(self) -> bool:
        """语言级真值判定"""
        pass
    
    def ts_repr(self) -> str:
        """调试表示"""
        return f"<{self.__class__.__name__}>"
    
    def ts_equal(self, other: 'TSValue') -> bool:
        """相等性比较（默认对象同一性）"""
        return self is other
```

---

## 3. 具体值类

### 3.1 `TSInteger` — 整数 (原类型)

```python
class TSInteger(TSValue):
    def __init__(self, value: int):
        self.value = value  # Python 任意精度整数
    
    def ts_type(self) -> 'TSType':
        return BUILTIN_TYPES["integer"]
    
    def ts_truthy(self) -> bool:
        return self.value != 0
    
    def ts_repr(self) -> str:
        return f"`{self.value}"
    
    def ts_equal(self, other: 'TSValue') -> bool:
        return isinstance(other, TSInteger) and self.value == other.value
```

**特殊**：原类型不包装实例，解释器内部直接以 `int` 运算，不经过地址空间。

### 3.2 `TSNumber` — 精确十进制数

```python
class TSNumber(TSValue):
    def __init__(self, front: int, back: int, scale: int):
        self.front = front      # 整数部分
        self.back = back        # 小数部分 (去前导零)
        self.scale = scale      # 小数位数
    
    @classmethod
    def from_string(cls, s: str) -> 'TSNumber':
        """从 '3.14' 解析"""
        # 解析逻辑...
    
    def to_string(self) -> str:
        """转为 '3.14' 字符串"""
        # 格式化逻辑...
    
    def ts_type(self) -> 'TSType':
        return BUILTIN_TYPES["number"]
    
    def ts_truthy(self) -> bool:
        return self.front != 0 or self.back != 0
```

### 3.3 `TSString` — Unicode 字符串

```python
class TSString(TSValue):
    def __init__(self, data: 'TSList'):
        self.data = data  # TSList 节点值为字符码点 (TSInteger)
    
    @classmethod
    def from_python(cls, s: str) -> 'TSString':
        """从 Python 字符串创建"""
        lst = TSList()
        for ch in s:
            lst.append(make_integer(ord(ch)))
        return cls(lst)
    
    def to_python(self) -> str:
        """转为 Python 字符串"""
        chars = []
        node = self.data.head
        while node:
            chars.append(chr(node.value.value))
            node = node.next
        return "".join(chars)
    
    def ts_type(self) -> 'TSType':
        return BUILTIN_TYPES["string"]
    
    def ts_truthy(self) -> bool:
        return self.data.size > 0
```

### 3.4 `TSBoolean` — 布尔

```python
class TSBoolean(TSValue):
    TRUE = None   # 类属性单例
    FALSE = None
    
    def __init__(self, value: int):  # 0 或 1
        self.value = value
    
    def ts_type(self) -> 'TSType':
        return BUILTIN_TYPES["boolean"]
    
    def ts_truthy(self) -> bool:
        return self.value != 0
```

### 3.5 单例类型

```python
class TSNone(TSValue):
    INSTANCE = None
    def __init__(self): ...
    def ts_type(self): return BUILTIN_TYPES["none_type"]
    def ts_truthy(self): return False

class TSNaN(TSValue):
    INSTANCE = None
    def ts_type(self): return BUILTIN_TYPES["nan_type"]
    def ts_truthy(self): return False

class TSInfinite(TSValue):
    POS_INF = None
    NEG_INF = None
    def __init__(self, sign: int): ...  # +1 或 -1
    def ts_type(self): return BUILTIN_TYPES["infinite_type"]
    def ts_truthy(self): return True
```

### 3.6 `TSList` — 单向链表

```python
class TSListNode:
    def __init__(self, value: TSValue):
        self.value = value
        self.next = None

class TSList(TSValue):
    def __init__(self):
        self.head = None
        self.tail = None
        self.size = 0
    
    def append(self, value: TSValue) -> None:
        node = TSListNode(value)
        if self.tail is None:
            self.head = self.tail = node
        else:
            self.tail.next = node
            self.tail = node
        self.size += 1
    
    def index(self, i: int) -> TSValue:
        if i < 0 or i >= self.size:
            raise IndexError(f"List index {i} out of range [0, {self.size})")
        node = self.head
        for _ in range(i):
            node = node.next
        return node.value
    
    def ts_type(self) -> 'TSType':
        return BUILTIN_TYPES["list"]
    
    def ts_truthy(self) -> bool:
        return self.size > 0
```

### 3.7 `TSCode` — 代码块

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ParamInfo:
    name: str
    type_annotation: Optional['TSType'] = None
    default_ast: Optional[dict] = None

class TSCode(TSValue):
    def __init__(self, statements: List[dict], scope: 'Scope', params: List[ParamInfo] = None):
        self.statements = statements
        self.scope = scope
        self.params = params or []
    
    def ts_type(self) -> 'TSType':
        return BUILTIN_TYPES["code"]
    
    def ts_truthy(self) -> bool:
        return True
```

### 3.8 `TSAddress` — 地址值

```python
class TSAddress(TSValue):
    def __init__(self, addr: int):
        self.addr = addr
    
    def ts_type(self) -> 'TSType':
        return BUILTIN_TYPES["address"]
    
    def ts_truthy(self) -> bool:
        return True
```

### 3.9 `TSError` / `TSWarning`

```python
class TSError(TSValue):
    def __init__(self, what: TSString):
        self.what = what
    
    def throw(self, interp) -> None:
        from tanex.runtime.interpreter import ErrorSignal
        raise ErrorSignal(self)

class TSWarning(TSValue):
    def __init__(self, what: TSString):
        self.what = what
    
    def throw(self, interp) -> None:
        # 打印警告，不抛出信号
        print(f"WARN: {self.what.to_python()}")
```

### 3.10 `TSLibrary` — 模块句柄

```python
class TSLibrary(TSValue):
    def __init__(self, members: dict, annotations: dict = None):
        self.members = members          # name -> TSValue (地址已解析)
        self.annotations = annotations or {}  # 独立注解空间
    
    def ts_type(self) -> 'TSType':
        return BUILTIN_TYPES["library"]
    
    def ts_truthy(self) -> bool:
        return True
```

### 3.11 `TSType` — 类型对象

```python
class TSType(TSValue):
    def __init__(self):
        self.initialize: Optional[TSValue] = None
        self.inherit: Optional['TSType'] = None
        self.special_members: dict = {}      # name -> TSValue (函数)
        self.members: dict = {}              # name -> address (int)
        self.addable: bool = True            # 可新增标记
        self.external_read_only: dict = {}   # member_name -> bool
    
    def ts_type(self) -> 'TSType':
        return BUILTIN_TYPES["type_type"]
    
    def ts_truthy(self) -> bool:
        return True
```

### 3.12 `TSInstance` — 用户类型实例

```python
class TSInstance(TSValue):
    def __init__(self, type_obj: TSType, members: dict = None):
        self.type = type_obj
        self.members = members or {}  # name -> address (int)
    
    def ts_type(self) -> 'TSType':
        return self.type
    
    def ts_truthy(self) -> bool:
        # 查找 boolean 特殊成员
        bool_member = self.type.special_members.get("boolean")
        if bool_member:
            return ts_truthy(call_special(bool_member, self))
        return True
```

### 3.13 `TSFunction` — 函数值

```python
class TSFunction(TSValue):
    def __init__(self, code: TSCode, closure_scope: 'Scope'):
        self.code = code
        self.closure_scope = closure_scope
    
    def ts_type(self) -> 'TSType':
        return BUILTIN_TYPES["function_name"]
    
    def ts_truthy(self) -> bool:
        return True
```

---

## 4. 值构造工厂函数

```python
# 基础值
def make_integer(n: int) -> TSInteger: ...
def make_number(front: int, back: int, scale: int) -> TSNumber: ...
def make_string(s: str) -> TSString: ...
def make_boolean(b: bool) -> TSBoolean: ...
def make_none() -> TSNone: return TSNone.INSTANCE
def make_nan() -> TSNaN: return TSNaN.INSTANCE
def make_infinite(sign: int = 1) -> TSInfinite: ...

# 复合值
def make_list(items: List[TSValue] = None) -> TSList: ...
def make_code(statements: List[dict], scope: 'Scope', params: List[ParamInfo] = None) -> TSCode: ...
def make_address(addr: int) -> TSAddress: ...
def make_error(what: str) -> TSError: ...
def make_warning(what: str) -> TSWarning: ...
def make_library(members: dict, annotations: dict = None) -> TSLibrary: ...

# 类型与实例
def make_type(initialize: TSValue = None, inherit: TSType = None, **special_members) -> TSType: ...
def make_instance(type_obj: TSType, members: dict = None) -> TSInstance: ...
```

---

## 5. 真值判定与类型查询

```python
def ts_truthy(value: TSValue) -> bool:
    """语言级真值判定"""
    if isinstance(value, TSInteger):
        return value.value != 0
    if isinstance(value, TSInstance):
        bool_member = value.type.special_members.get("boolean")
        if bool_member:
            return ts_truthy(call_special(bool_member, value))
        return True
    if isinstance(value, TSType):
        return True
    if isinstance(value, (TSCode, TSAddress, TSLibrary, TSFunction)):
        return True
    if isinstance(value, (TSNone, TSNaN)):
        return False
    return True

def ts_type_of(value: TSValue) -> TSType:
    """对应一元运算符 type_of"""
    return value.ts_type()
```

---

## 6. 真值判定规则表

| 值类型 | 真值结果 |
|--------|----------|
| `TSInteger` | `value != 0` |
| `TSNumber` | `front != 0 or back != 0` |
| `TSString` | `data.size > 0` |
| `TSList` | `size > 0` |
| `TSBoolean` | `value != 0` |
| `TSNone` | `False` |
| `TSNaN` | `False` |
| `TSInfinite` | `True` |
| 实例 | 有 `boolean` 特殊成员则调用，否则 `True` |
| 类型对象 | `True` |
| `TSCode`/`TSAddress`/`TSLibrary`/`TSFunction` | `True` |

---

## 相关链接

- [解释器嵌入](embedding.md) — 使用值模型进行嵌入开发
- [核心执行器](interpreter.md) — 值在执行中的流转
- [地址空间与作用域](environment.md) — 值的存储与查找
- [语言参考：类型系统](../reference/types.md) — 语言层面类型规范
- [语言参考：表达式](../reference/expressions.md) — 值的求值语义