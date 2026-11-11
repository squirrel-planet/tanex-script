# `encoding.ascii` ASCII 编解码库

> **导入**：`import "encoding.ascii" = *ascii;`
> **来源**：`核心/standard_src/encoding/ascii.tsuc`，纯 Tanex Script 实现

---

## 模块概述

提供字节列表 ↔ ASCII 字符串转换、字符分类判断、大小写转换功能。仅处理 ASCII 范围(0-127)，非 ASCII 字符按原样处理或报错。

**依赖**：仅依赖引导库核心类型。

---

## 导出列表 (`public`)

```tanex script
*** public = [
    "ascii_decode", "ascii_encode",
    "is_digit", "is_upper", "is_lower", "is_alpha", "is_alphanumeric",
    "is_space", "is_printable",
    "to_upper", "to_lower", "upper", "lower"
];
```

---

## 逐条目规范

### 编解码

#### `ascii_decode` — 字节列表转 ASCII 字符串

> **签名**：`*** ascii_decode = [*data] => { *r=string{}; *i=0; { i < data.size } $$ { r.push_char(data.index(i)); i = i + 1; }; $ r; }`  
> **参数**：`data` (`List<Integer>`) — 字节码列表，每元素 0-255  
> **返回值**：`String`  
> **异常**：元素超出 0-255 范围行为未定义 [待确认]  
> **复杂度**：O(N)  
> **示例**：
```tanex script
ascii.ascii_decode([`72`, `101`, `108`, `108`, `111`]);  # => "Hello" #;
```

---

#### `ascii_encode` — ASCII 字符串转字节列表

> **签名**：`*** ascii_encode = [*text] => { *r=List{}; *i=0; { i < text.data.size } $$ { r.append(text.data.index(i)); i = i + 1; }; $ r; }`  
> **参数**：`text` (`String`) — ASCII 字符串  
> **返回值**：`List<Integer>` (字节码列表)  
> **复杂度**：O(N)  
> **示例**：
```tanex script
ascii.ascii_encode("Hi");  # => [`72`, `105`] #;
```

---

### 字符分类函数

所有分类函数参数为 `c` (`Integer` 字符码)，返回 `Boolean`。

| 函数 | 签名 | 判断范围 | 示例 |
|------|------|----------|------|
| `is_digit` | `c >= 48 && c <= 57` | `0`-`9` (48-57) | `ascii.is_digit(`65) => false` |
| `is_upper` | `c >= 65 && c <= 90` | `A`-`Z` (65-90) | `ascii.is_upper(`65) => true` |
| `is_lower` | `c >= 97 && c <= 122` | `a`-`z` (97-122) | `ascii.is_lower(`97) => true` |
| `is_alpha` | `is_upper(c) \|\| is_lower(c)` | 字母 | `ascii.is_alpha(`65) => true` |
| `is_alphanumeric` | `is_digit(c) \|\| is_alpha(c)` | 字母数字 | `ascii.is_alphanumeric(`48) => true` |
| `is_space` | `c==32\|\|c==9\|\|c==10\|\|c==13` | 空格/制表/换行/回车 | `ascii.is_space(`32) => true` |
| `is_printable` | `c >= 32 && c <= 126` | 可打印 ASCII | `ascii.is_printable(`32) => true` |

---

### 大小写转换

#### `to_upper` / `to_lower` — 单字符转换

> **签名**：
> - `*** to_upper = [*c] => { is_lower(c) ? c - 32 : c; }`
> - `*** to_lower = [*c] => { is_upper(c) ? c + 32 : c; }`
> **参数**：`c` (`Integer` 字符码)  
> **返回值**：`Integer` (转换后字符码)  
> **示例**：
```tanex script
ascii.to_upper(`97);    # => `65 ('a' -> 'A') #;
ascii.to_lower(`65);    # => `97 ('A' -> 'a') #;
ascii.to_upper(`48);    # => `48 ('0' 非字母，原样返回) #;
```

---

#### `upper` / `lower` — 整字符串转换

> **签名**：
> - `*** upper = [*text] => { *r=string{}; *i=0; { i < text.data.size } $$ { r.push_char(to_upper(text.data.index(i))); i = i + 1; }; $ r; }`
> - `*** lower = [*text] => { ... to_lower ... }`
> **参数**：`text` (`String`)  
> **返回值**：`String` (转换后)  
> **示例**：
```tanex script
ascii.upper("Hello");  # => "HELLO" #;
ascii.lower("HELLO");  # => "hello" #;
ascii.upper("中文");    # => "中文" (非 ASCII 原样返回) #;
```

**注意**：仅处理 ASCII 字母(A-Z/a-z)，非 ASCII 字符原样返回。

---

## 版本历史

| 版本 | 变更 |
|------|------|
| 1.0.0 | 基线导出：14 个函数 |