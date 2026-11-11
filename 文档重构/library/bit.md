# `bit` 位运算库

> **导入**：`import "bit" = *bit;`
> **来源**：`核心/standard_src/bit.tsuc`，纯 Tanex Script 实现
> **注意**：原文件未声明 `public` 且无注解，本文档补充完整规范。

---

## 模块概述

提供整数位运算：AND/OR/XOR/NOT/左移/右移，以及二进制↔十进制转换。所有操作基于整数的二进制位模式运算。

**依赖**：仅依赖引导库核心类型。

---

## 导出列表 (`public`)

```tanex script
*** public = [
    "bit_and", "bit_or", "bit_xor", "bit_not",
    "bit_left_shift", "bit_right_shift",
    "to_binary", "to_decimal"
];
```

---

## 逐条目规范

### 位逻辑运算

#### `bit_and` — 位与

> **签名**：`*** bit_and = [[*a, integer], [*b, integer]] => { ... }` (按位与，二进制串运算)  
> **参数**：`a`, `b` (`Integer`)  
> **返回值**：`Integer` (按位与结果)  
> **复杂度**：O(log max(a,b)) 位数  
> **示例**：
```tanex script
bit.bit_and(`5`, `3);  # => `1 (101 & 011 = 001) #;
```

---

#### `bit_or` — 位或

> **签名**：类似 `bit_and`，按位或运算  
> **示例**：
```tanex script
bit.bit_or(`5`, `3);  # => `7 (101 | 011 = 111) #;
```

---

#### `bit_xor` — 位异或

> **签名**：类似，按位异或运算  
> **示例**：
```tanex script
bit.bit_xor(`5`, `3);  # => `6 (101 ^ 011 = 110) #;
```

---

#### `bit_not` — 位非(补码)

> **签名**：`*** bit_not = [[*n, integer]] => { n == 0 ? 1 : (2^(floor(log2(n))+1) - 1 - n); }`  
> **参数**：`n` (`Integer`)  
> **返回值**：`Integer`  
> **示例**：
```tanex script
bit.bit_not(`0);   # => `1 #;
bit.bit_not(`5);   # => `2 (101 -> 010, 3 位宽补码) #;
```

**注意**：位宽取最小能表示 n 的位数。`n=0` 特殊返回 `1`。

---

### 位移运算

#### `bit_left_shift` — 逻辑左移

> **签名**：`*** bit_left_shift = [[*n, integer], [*sh, integer]] => { $ n * (2^sh); }`  
> **参数**：
> - `n` (`Integer`) — 被移位整数
> - `sh` (`Integer`) — 移位数 (≥0)  
> **返回值**：`Integer` (等价 `n * 2^sh`)  
> **示例**：
```tanex script
bit.bit_left_shift(`3`, `2);   # => `12 (3 * 4) #;
```

---

#### `bit_right_shift` — 逻辑右移

> **签名**：`*** bit_right_shift = [[*n, integer], [*sh, integer]] => { $ n \ (2^sh); }`  
> **参数**：同左移  
> **返回值**：`Integer` (等价 `n \ 2^sh`，整除)  
> **示例**：
```tanex script
bit.bit_right_shift(`12`, `2); # => `3 (12 \ 4) #;
```

---

### 二进制 ↔ 十进制转换

#### `to_binary` — 十进制整数转二进制表示

> **签名**：`*** to_binary = [[*n, integer]] => { ... }` 返回二进制位模式的十进制整数  
> **参数**：`n` (`Integer`) — 非负整数  
> **返回值**：`Integer` (数字仅含 0/1，如 `5` → `101` 即整数一百零一)  
> **示例**：
```tanex script
bit.to_binary(`5);     # => `101 #;
bit.to_binary(`0);     # => `0 #;
```

**注意**：返回的「二进制」实为十进制整数(数字仅含 0/1)，非字符串。配合位运算函数使用。

---

#### `to_decimal` — 二进制表示转十进制整数

> **签名**：`*** to_decimal = [[*n, integer]] => { ... }` 将「二进制形式的整数」转回十进制  
> **参数**：`n` (`Integer`) — 数字仅含 0/1 的整数  
> **返回值**：`Integer`  
> **示例**：
```tanex script
bit.to_decimal(`101);  # => `5 #;
bit.to_decimal(`0);    # => `0 #;
```

---

## 内部辅助(以下划线 `_` 前缀)

原文件所有函数均为导出函数，无额外内部辅助。

---

## 版本历史

| 版本 | 变更 |
|------|------|
| 1.0.0 | 基线实现：8 个位运算/转换函数(原文件无 public/注解) |
| 1.0.1 | 补充 `public` 导出列表、全函数注解、参数类型注解规范化 |