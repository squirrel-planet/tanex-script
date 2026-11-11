# `numeral_system` 进制转换库

> **导入**：`import "numeral_system" = *ns;`
> **来源**：`核心/standard_src/numeral_system.tsuc`，纯 Tanex Script 实现

---

## 模块概述

提供 2/8/10/16 进制互转功能。所有函数为纯函数，输入输出均为 `String` 或 `Integer` 类型。

**依赖**：仅依赖引导库核心类型。

---

## 导出列表 (`public`)

```tanex script
*** public = [
    "binary_to_hexadecimal", "hexadecimal_to_binary",
    "binary_to_octal", "octal_to_binary",
    "binary_to_integer", "integer_to_binary",
    "integer_to_hexadecimal", "hexadecimal_to_integer",
    "octal_to_integer", "integer_to_octal"
];
```

---

## 逐条目规范

### 二进制 ↔ 十六进制

#### `binary_to_hexadecimal` — 二进制转十六进制

> **签名**：`*** binary_to_hexadecimal = [*binary_string] => { ... }`  
> **参数**：`binary_string` (`String`) — 仅含 `0`/`1` 的字符串  
> **返回值**：`String` (大写十六进制)  
> **复杂度**：O(N) 字符数  
> **示例**：
```tanex script
ns.binary_to_hexadecimal("1010");   # => "A" #;
ns.binary_to_hexadecimal("1111");   # => "F" #;
ns.binary_to_hexadecimal("10000");  # => "10" #;
```

---

#### `hexadecimal_to_binary` — 十六进制转二进制

> **签名**：`*** hexadecimal_to_binary = [*hex_string] => { ... }`  
> **参数**：`hex_string` (`String`) — 十六进制字符串(0-9, A-F, a-f)  
> **返回值**：`String` (二进制，每字符展开为 4 位，含前导零)  
> **示例**：
```tanex script
ns.hexadecimal_to_binary("A");   # => "1010" #;
ns.hexadecimal_to_binary("1F");  # => "00011111" #;
```

---

### 二进制 ↔ 八进制

#### `binary_to_octal` — 二进制转八进制

> **签名**：`*** binary_to_octal = [*binary_string] => { ... }` (按 3 位分组)  
> **参数**：`binary_string` (`String`)  
> **返回值**：`String` (八进制)  
> **示例**：
```tanex script
ns.binary_to_octal("1010");   # => "12" #;
```

---

#### `octal_to_binary` — 八进制转二进制

> **签名**：`*** octal_to_binary = [*octal_string] => { ... }` (按 3 位展开)  
> **参数**：`octal_string` (`String`) — 八进制字符串(0-7)  
> **返回值**：`String` (二进制)  
> **示例**：
```tanex script
ns.octal_to_binary("12");     # => "001010" #;
```

---

### 二进制 ↔ 十进制整数

#### `binary_to_integer` — 二进制字符串转十进制整数

> **签名**：`*** binary_to_integer = [*binary_string] => { ... }`  
> **参数**：`binary_string` (`String`)  
> **返回值**：`Integer`  
> **示例**：
```tanex script
ns.binary_to_integer("1010");  # => `10 #;
```

---

#### `integer_to_binary` — 十进制整数转二进制字符串

> **签名**：`*** integer_to_binary = [*value] => { ... }`  
> **参数**：`value` (`Integer`) — 非负整数  
> **返回值**：`String` (二进制，无前导零)  
> **示例**：
```tanex script
ns.integer_to_binary(`10);    # => "1010" #;
ns.integer_to_binary(`0);     # => "0" #;
```

---

### 十进制整数 ↔ 十六进制

#### `integer_to_hexadecimal` — 十进制整数转十六进制字符串

> **签名**：`*** integer_to_hexadecimal = [*value] => { ... }`  
> **参数**：`value` (`Integer`) — 非负整数  
> **返回值**：`String` (大写十六进制，无前导零)  
> **示例**：
```tanex script
ns.integer_to_hexadecimal(`255);  # => "FF" #;
ns.integer_to_hexadecimal(`0);    # => "0" #;
```

---

#### `hexadecimal_to_integer` — 十六进制字符串转十进制整数

> **签名**：`*** hexadecimal_to_integer = [*hex_string] => { ... }`  
> **参数**：`hex_string` (`String`) — 十六进制字符串(0-9, A-F, a-f)  
> **返回值**：`Integer`  
> **示例**：
```tanex script
ns.hexadecimal_to_integer("FF");   # => `255 #;
ns.hexadecimal_to_integer("1a");   # => `26 #;
```

---

### 十进制整数 ↔ 八进制

#### `integer_to_octal` — 十进制整数转八进制字符串

> **签名**：`*** integer_to_octal = [*value] => { ... }`  
> **参数**：`value` (`Integer`) — 非负整数  
> **返回值**：`String` (八进制，无前导零)  
> **示例**：
```tanex script
ns.integer_to_octal(`10);   # => "12" #;
ns.integer_to_octal(`0);    # => "0" #;
```

---

#### `octal_to_integer` — 八进制字符串转十进制整数

> **签名**：`*** octal_to_integer = [*octal_string] => { ... }`  
> **参数**：`octal_string` (`String`) — 八进制字符串(0-7)  
> **返回值**：`Integer`  
> **示例**：
```tanex script
ns.octal_to_integer("12");   # => `10 #;
ns.octal_to_integer("0");    # => `0 #;
```

---

## 内部辅助(以下划线 `_` 前缀)

| 函数 | 用途 |
|------|------|
| `_hexadecimal_characters` | 十六进制字母表常量 `"0123456789ABCDEF"` |
| `_hexadecimal_lowercase` | 小写十六进制字母表 |
| `_character_string` | 字符码 → 单字符字符串 |
| `_hexadecimal_binary_map` | 十六进制字符 → 4 位二进制映射表 |
| `_octal_binary_map` | 八进制字符 → 3 位二进制映射表 |
| `_hexadecimal_value` | 十六进制字符码 → 数值(0-15) |
| `_hexadecimal_character` | 数值(0-15) → 十六进制字符码 |

---

## 版本历史

| 版本 | 变更 |
|------|------|
| 1.0.0 | 基线导出：10 个进制转换函数 |