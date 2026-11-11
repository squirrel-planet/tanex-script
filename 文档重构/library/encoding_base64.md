# `encoding.base_sixty_four` Base64 编解码库

> **导入**：`import "encoding.base_sixty_four" = *b64;`
> **来源**：`核心/standard_src/encoding/base_sixty_four.tsuc`，纯 Tanex Script 实现

---

## 模块概述

提供字节列表 ↔ Base64 字符串编解码，遵循 RFC 4648 标准字母表 (`A-Z a-z 0-9 + /`，填充字符 `=`)。

**依赖**：仅依赖引导库核心类型。

---

## 导出列表 (`public`)

```tanex script
*** public = [
    "base_sixty_four_encode", "base_sixty_four_decode"
];
```

---

## 逐条目规范

### `base_sixty_four_encode` — 字节列表转 Base64 字符串

> **签名**：`*** base_sixty_four_encode = [*data] => { ... }` (标准 3 字节→4 字符分组，不足补 `=`)  
> **参数**：`data` (`List<Integer>`) — 字节列表，每元素 0-255  
> **返回值**：`String` (Base64 编码)  
> **复杂度**：O(N)  
> **示例**：
```tanex script
b64.base_sixty_four_encode([`72`, `101`, `108`, `108`, `111`]);  # => "SGVsbG8=" #;
```

---

### `base_sixty_four_decode` — Base64 字符串转字节列表

> **签名**：`*** base_sixty_four_decode = [*text] => { ... }` (解码，填充字符 `=` 被忽略，**非法字符抛出错误**)  
> **参数**：`text` (`String`) — Base64 字符串  
> **返回值**：`List<Integer>` (字节列表)  
> **复杂度**：O(N)  
> **示例**：
```tanex script
b64.base_sixty_four_decode("SGVsbG8=");  # => [`72`, `101`, `108`, `108`, `111`]
b64.base_sixty_four_decode("SGVsbG8!");  # 抛出错误: "base_sixty_four_decode: 第 7 个字符 '!' 不是合法 Base64 字符"
```

---

## 内部辅助(以下划线 `_` 前缀)

| 函数 | 用途 |
|------|------|
| `_base_sixty_four_table` | Base64 字母表常量 `"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"` |
| `_base_sixty_four_index` | 字符码 → 字母表索引(0-63)，未找到返回 -1 |

---

## 版本历史

| 版本 | 变更 |
|------|------|
| 1.0.0 | 基线导出：2 个编解码函数 |