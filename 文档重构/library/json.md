# `json` JSON 序列化库

> **导入**：`import "json" = *json;`
> **来源**：`核心/standard_src/json.tsuc`，纯 Tanex Script 实现

---

## 模块概述

提供 TSuc 值 ↔ JSON 字符串序列化与反序列化。支持 `Integer`、`Number`、`String`、`Boolean`、`none`、`List`、`Dictionary`(对象)。`nan`/`infinite` 不合法 JSON，序列化时报错。

**依赖**：`standard` 库（内部使用列表/字符串操作）。

---

## 类型映射表

| TSuc 类型 | JSON 形式 | 备注 |
|-----------|-----------|------|
| `Integer` | 数字 | 如 `42` |
| `Number` | 数字 | 如 `3.14` |
| `String` | 字符串 | 转义 `"` `\` 等 |
| `Boolean` | `true`/`false` | |
| `NoneType` | `null` | `none` → `null` |
| `List` | 数组 | 如 `[1,2,3]` |
| `Dictionary` | 对象 | 如 `{"a":1}` |
| `NaNType` | **不支持** | 序列化报错 |
| `InfiniteType` | **不支持** | 序列化报错 |
| `Code`/`Address`/等 | **不支持** | 序列化报错 |

---

## 导出列表 (`public`)

```tanex script
*** public = ["stringify", "parse"];
```

---

## 逐条目规范

### `stringify` — 序列化为 JSON 字符串

> **签名**：`*** stringify = [*value] => { $ _stringify_value(value); }`  
> **参数**：`value` (任意) — 待序列化值  
> **返回值**：`String` (JSON 文本)  
> **异常**：
> - `nan`/`infinite` 抛出 `error{"stringify: nan/infinite 不是合法的 JSON 值"}`
> - 不支持类型(`Code`、`Address`、`Error` 等) 抛出 `error{"stringify: 该值类型无法序列化为 JSON"}`
> **复杂度**：O(N) 值大小  
> **示例**：
```tanex script
json.stringify(`42);                    # => "42" #;
json.stringify("hello");                 # => "\"hello\"" #;
json.stringify([`1`, `2`, `3`]);         # => "[1,2,3]" #;
json.stringify(dictionary{["a", `1`]});  # => "{\"a\":1}" #;
```

---

### `parse` — 解析 JSON 字符串

> **签名**：`*** parse = [*text] => { _position = 0; $ _parse_value(text); }`  
> **参数**：`text` (`String`) — JSON 文本  
> **返回值**：对应 TSuc 值  
> **返回类型映射**：

| JSON 形式 | TSuc 类型 |
|-----------|-----------|
| 数字(整数) | `Integer` |
| 数字(小数) | `Number` |
| 字符串 | `String` |
| `true`/`false` | `Boolean` |
| `null` | `NoneType` (`none`) |
| 数组 | `List` |
| 对象 | `Dictionary` |

> **异常**：语法错误抛出运行时错误 [待确认：具体错误格式]  
> **复杂度**：O(N) 文本长度  
> **示例**：
```tanex script
json.parse("42");              # => `42 #;
json.parse("3.14");            # => '3.14 #;
json.parse("[1,2,3]");         # => [`1`, `2`, `3`] #;
json.parse("{\"a\":1}");       # => dictionary{["a", `1`]} #;
```

---

## 内部辅助(以下划线 `_` 前缀)

| 函数 | 用途 |
|------|------|
| `_stringify_value` | 递归序列化分发 |
| `_stringify_integer` | 整数 → 十进制字符串 |
| `_stringify_boolean` | 布尔 → "true"/"false" |
| `_stringify_list` | 列表 → JSON 数组 |
| `_stringify_dictionary` | 字典 → JSON 对象 |
| `_escape_string` | 字符串 JSON 转义(`"` `\` 等) |
| `_parse_value` | 递归解析分发 |
| `_parse_null`/`_parse_true`/`_parse_false` | 字面量解析 |
| `_parse_string` | 字符串解析(处理转义) |
| `_parse_number` | 数字解析(整数/小数) |
| `_parse_array` | 数组解析 |
| `_parse_object` | 对象解析 |
| `_skip_whitespace`/`_peek`/`_next` | 词法分析工具 |

---

## 版本历史

| 版本 | 变更 |
|------|------|
| 1.0.0 | 基线导出：`stringify`、`parse` |