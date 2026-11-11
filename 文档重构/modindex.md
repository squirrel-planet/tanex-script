# 模块索引

> 对标 [Python Module Index](https://docs.python.org/zh-cn/3.16/py-modindex.html)
>
> Tanex Script 标准库模块按字母序索引。

---

## 标准库模块

| 模块名 | 导入名 | 核心功能 | 文档链接 |
|--------|--------|----------|----------|
| `bit` | `bit` | 位运算、二进制↔十进制转换 | [bit.md](../library/bit.md) |
| `encoding.ascii` | `encoding.ascii` | ASCII 编解码、字符分类、大小写转换 | [encoding_ascii.md](../library/encoding_ascii.md) |
| `encoding.base_sixty_four` | `encoding.base_sixty_four` | Base64 编解码 (RFC 4648) | [encoding_base64.md](../library/encoding_base64.md) |
| `json` | `json` | JSON 序列化/反序列化 | [json.md](../library/json.md) |
| `maths` | `maths` | 数学函数与常量 | [maths.md](../library/maths.md) |
| `numeral_system` | `numeral_system` | 2/8/10/16 进制互转 | [numeral_system.md](../library/numeral_system.md) |
| `random` | `random` | LCG 随机数生成器 | [random.md](../library/random.md) |
| `standard` | `standard` | 核心扩展：类型构造、I/O、反射、控制流辅助、函数式工具 | [standard.md](../library/standard.md) |

---

## 核心模块（内置，无需导入）

| 名称 | 说明 | 文档链接 |
|------|------|----------|
| `type_type` | 基类型（元类型） | [基类型](../reference/types.md#3-基类型-typetype) |
| `integer` | 原类型 | [原类型](../reference/types.md#2-原类型-integer) |
| `number` | 精确十进制数 | [数字类型](../reference/types.md#41-number--精确十进制数) |
| `string` | Unicode 字符串 | [字符串类型](../reference/types.md#42-string--unicode-字符串) |
| `boolean` | 布尔类型 | [布尔类型](../reference/types.md#43-boolean--布尔类型) |
| `none_type` / `none` | 空类型/空值 | [空类型](../reference/types.md#44-nonetype--none--空类型与单例) |
| `nan_type` / `nan` | NaN 类型/值 | [特殊数值](../reference/types.md#45-nantype--nan、infinitetype--infinite、-infinite) |
| `infinite_type` / `infinite` / `-infinite` | 无穷类型/值 | [特殊数值](../reference/types.md#45-nantype--nan、infinitetype--infinite、-infinite) |
| `list` | 单向链表容器 | [列表类型](../reference/types.md#46-list--单向链表容器) |
| `code` | 代码块类型 | [代码块类型](../reference/types.md#47-code--代码块类型) |
| `address` | 地址值类型 | [地址值](../reference/types.md#48-address--地址值) |
| `error` / `warning` | 错误/警告类型 | [错误与警告](../reference/types.md#49-error--warning--错误与警告) |
| `library` | 模块句柄类型 | [库类型](../reference/types.md#410-library--模块句柄) |
| `function_name` / `type_name` | 函数名/类型名类型 | [函数名/类型名类型](../reference/types.md#413-function_name--type_name--函数名与类型名类型) |

---

## 内置函数（全局可用，无需导入）

| 函数 | 签名 | 说明 |
|------|------|------|
| `if` | `if(cond, then_code, else_code)` | 条件分支 |
| `for` | `for(*var, iterable, body_code)` | 遍历循环 |
| `while` | `while(cond_code, body_code)` | 条件循环 |
| `cycle` | `cycle(times, body_code)` | 定次循环 |
| `type_of` | `type_of(value)` | 返回类型对象 |

---

## 相关链接

- [标准库参考](../library/index.md) — 8 个模块逐条目规范
- [全局索引](genindex.md) — 所有函数、类型、术语检索
- [完整目录](contents.md) — 所有章节和子章节
- [术语对照表](glossary.md) — 术语中英对照