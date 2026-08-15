# 松鼠星球 Python 代码风格指南

> 非 PEP 8 标准，仅团队编码标准。

---

## 1. 命名规范

### 1.1 类名 — `snake_case`

类名使用小写字母 + 下划线，**不使用** PascalCase。

```python
# ✅ 正确
class user_service(object):
class data_processor(object):

# ❌ 避免（即使 PEP8 推荐）
class UserService:
class DataProcessor:
```

### 1.2 方法名 & 函数名 — `snake_case`

```python
# ✅ 正确
def get_user():
def _validate_input(self) -> bool:
def calculate_total_price(self, items: list, ...)
def _handle_api_error(self, code, message):
```

### 1.3 变量名 — `snake_case`

```python
# ✅ 正确
user_name = 'alice'
item_list = []
total_price = 0
is_activated = False
```

### 1.4 常量 — `snake_case`

不使用 `ALL_CAPS`，即使是逻辑上的常量也使用普通 `snake_case`。

```python
# ✅ 正确
error_messages = {404: '未找到', 500: '服务器错误'}
default_timeout = 30

# ❌ 避免
ERROR_MESSAGES = {404: '未找到', 500: '服务器错误'}
DEFAULT_TIMEOUT = 30
```

### 1.5 私有性

使用 `_` 或 `__` 前缀或使用 `__all__` 标记公用/私有。

```python
# ✅ 正确
def _internal_helper():
class _PrivateConfig(object):
    __slots__ = ['_cache']
```

---

## 2. 缩进

- **4 空格**作为缩进单位（不使用 Tab）

```python
# ✅ 正确
# 控制流缩进 — 4 空格缩进
if __name__ == '__main__':
    main()
```

```python
# ✅ 正确
# 函数定义换行续接 — 4 空格缩进
def calculate_total_price(
    self, items: list,
    discount: float | None = None,
    tax_rate: float = 0.05) -> float:
```

```python
# ✅ 正确
# 函数调用换行续接 — 4 空格缩进
self.calculate_total_price(
    items,
    discount=0.1,
    tax_rate=0.06
)
```

```python
# ✅ 正确
# 类定义换行续接 — 4 空格缩进
class fetch_web_api(fetch.api,
    web.fech.get):
    ...
```

```python
# ✅ 正确
# 函数调用换行续接 — 4 空格缩进
ojbect_to_sting(
    object = my_type('Hello World')
    special = False)
```

```python
# ✅ 正确
# 列表/字典换行续接 — 4 空格缩进
to_do_list = [
    '获取需求',
    '更改文件',
    '检查代码',
    '提交到Github'
]
mapping_table = {
    '&&': 'and',
    '||': 'or',
    'nullptr': 'None',
    'true': 'True',
    'false': 'False'
}
```

```python
# ✅ 正确
# 下标换行续接 — 4 空格缩进
sub_string =  string[my_lib.get_result(my_lib.start()):
    my_lib.get_result(my_lib.end())]
```

---

## 3. 空格

### 3.1 关键字参数赋值 — 等号两侧加空格

```python
# ✅ 等号两侧均有空格
print(value, end = '')
open('file.txt', encoding = 'utf-8')
json.dump(data, fp, ensure_ascii = False)
```

### 3.2 运算符 — 两侧加空格

```python
# ✅ 正确
count = 0
index += 1
total = price * quantity
```

### 3.3 逗号 — 右侧加空格

```python
# ✅ 正确
def __init__(self, name: str, age: int, active: bool = True):
user = user_type('alice', 25, True)
```

### 3.4 函数参数默认值 — `=` 两侧加空格

```python
# ✅ 正确
def fetch_data(url, timeout = 30, retry = 3):
def log_message(self, level = 'info') -> None:
```

> 注意：这与 PEP 8 推荐的不加空格不同，团队风格统一加空格。

---

## 4. 类型注解

- **非强制**：部分函数可以加类型注解，部分不加
- **混合风格**：可以使用 `typing.List` 旧风格和 `str | int` 新联合语法

```python
# 同时存在的两种风格
from typing import List, Optional

def run(self) -> None:
    items: List[str] = data.split(',')

def __init__(self, name: str = 'default', value: str | int | None = None):
```

- 建议统一为**新风格**（Python 3.10+），不使用 `typing` 模块：
  - `list[str]` 替代 `List[str]`
  - `str | int | None` 替代 `Optional[str]`
  - `None` 作为返回类型时写 `-> None`

```python
# ✅ 推荐新风格
def process(items: list[str]) -> None:
    ...

def lookup(key: str) -> str | None:
    ...
```

---

## 5. 引号

- **优先使用单引号** `'` 作为字符串定界符
- 仅在字符串包含单引号时使用双引号

```python
# ✅ 单引号
name = 'alice'
message = '文件未找到，请重试'

# ✅ 双引号（内容包含单引号）
result = "it's done"
print(f"value: '{var}'")
```

---

## 6. 空行

| 位置 | 空行数 |
| ------ | -------- |
| import上下 | **1** 个空行 |
| 函数/类上下 | **1** 个空行 |
| 类内方法上下 | **1** 个空行 |
| 文件末尾 | **1** 个空行 |

**注意**：当一个需要上下空行的语句作为开头时**不要换行**，当import上或下有另一个import时，**不要换行**，保证import都在一块。

```python
import os
                                    # ← 1 个空行
def fetch_data(url):
    ...
                                    # ← 1 个空行
class user_service(object):
                                    # ← 1 个空行
    def __init__(self, ...):
        ...
                                    # ← 1 个空行
    def get_user(self) -> dict:
        ...
                                    # ← 1 个空行
class order_service(object):
    ...
                                    # ← 1 个空行
```

---

## 7. 导入

- **一行一个导入**
- 标准库导入在前

```python
import os
import sys
import json
from datetime import datetime
from typing import List, Optional
```

---

## 8. 类定义

继承 `object` 可以显式继承，也可以不显式继承。

```python
# ✅ 两种都正确
class user_service(object):
class order_service:
```

---

## 9. 文档字符串

**不使用文档字符串（docstring）**。函数/类的说明通过命名和代码本身表达。

```python
# ✅ 正确：见名知义，不写 docstring
def calculate_total_price(items: list) -> float:
    total = sum(item['price'] for item in items)
    return total
```

---

## 10. 注释

使用注释。不使用行后注释。使用中文注释。

```python
# ✅ 正确：注释独占一行
# 检查用户是否已激活
if user.status == 'active':
    grant_access()

# ❌ 避免：行后注释
if user.status == 'active':  # 检查用户是否已激活 (错误注释)
    grant_access()

# ❌ 避免：中文注释
if user.status == 'active':  # Check if the user has been activated (错误注释)
    grant_access()
```

---

## 11. 行长度

**无严格限制**。代码行可以超过 79/100 字符，优先保证可读性而非短行。

---

## 12. 条件与分支

### 12.1 条件表达式不加括号

```python
# ✅ 正确
if not items:
if __name__ == '__main__':
if length > 2:
```

### 12.2 善用隐式布尔检查

```python
# ✅ 正确
if not items:              # 而不是 if len(items) == 0
if user:                   # 而不是 if user is not None
```

---

## 13. 异常处理

不严格要求指定异常类型，允许 bare except。但 **严禁 `except: pass`** —— 捕获的异常必须处理（记录或报错），不可静默忽略：

```python
# ✅ 允许 bare except，且必须处理
try:
    result = api_call()
except:
    log_error('api 调用失败')
    raise

# ❌ 严禁
try:
    result = api_call()
except:
    pass
```

---

## 14. 错误处理模式

不严格要求

---

## 15. 字符串格式化

- **优先使用 f-string**
- 仅在简单拼接时使用 `+`

```python
# ✅ f-string
message = f'用户 {name} 的余额为 {balance} 元'

# ✅ 简单拼接
message = '文件 ' + filename + ' 未找到'
```

---

## 16. 元组与解包

定义多个变量时使用元组解包：

```python
# ✅ 正确
name, age = 'alice', 25
count, total = (0, 0.0)
```

---

## 17. 总结清单

| 风格项 | 团队标准 | PEP 8 参考（仅对比） |
| -------- | ---------- | --------------------- |
| 类命名 | `snake_case` | `PascalCase` |
| 缩进 | 4 空格（续行统一使用缩进，不是对齐括号） | 4 空格 |
| 关键字参数 `=` 空格 | 两侧加空格 | 不加空格 |
| 默认参数 `=` 空格 | 两侧加空格 | 不加空格 |
| 引号 | 优先单引号 | 无偏好 |
| 文档字符串 | 不使用 | 推荐使用 |
| 行长度 | 无限制 | 79/100 字符 |
| 异常处理 | 可 bare except，禁 `except: pass` | 推荐精确异常类型 |
| 常量命名 | `snake_case` | `UPPER_CASE` |
| 类型注解 | 可选，混合新旧风格 | 推荐 |
| 注释 | 适量使用 | 适量使用 |
