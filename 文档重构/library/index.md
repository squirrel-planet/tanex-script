# 标准库参考

> 对标 [Python Library Reference](https://docs.python.org/zh-cn/3.16/library/)
>
> Tanex Script 标准库包含 8 个核心模块，均为纯 Tanex Script 实现，随解释器分发。用户通过 `import "模块名" = *别名;` 引入。

---

## 模块总览

| 模块名 | 导入名 | 核心功能 | 导出数量 |
|--------|--------|----------|----------|
| [`standard`](standard.md) | `standard` | 核心扩展：类型构造、基础算术、字符串/列表操作、I/O封装、反射、控制流辅助、函数式工具 | 20+ |
| [`maths`](maths.md) | `maths` | 数学函数与常量：gcd/lcm/素数/阶乘/幂/平方根/斐波那契/组合数、π/e/√2 | 25 |
| [`numeral_system`](numeral_system.md) | `numeral_system` | 2/8/10/16 进制互转 | 10 |
| [`encoding.ascii`](encoding_ascii.md) | `encoding.ascii` | ASCII 编解码、字符分类、大小写转换 | 14 |
| [`encoding.base_sixty_four`](encoding_base64.md) | `encoding.base_sixty_four` | Base64 编解码 (RFC 4648) | 2 |
| [`json`](json.md) | `json` | JSON 序列化/反序列化 | 2 |
| [`random`](random.md) | `random` | LCG 随机数生成器、多种分布采样、洗牌 | 7 |
| [`bit`](bit.md) | `bit` | 位运算、二进制↔十进制转换 | 8 |

---

## 通用引入方式

```tanex script
# 推荐：显式命名引入，避免命名冲突
import "standard" = *std;
import "maths" = *math;
import "encoding.ascii" = *ascii;
import "json" = *json;

# 然后通过句柄访问
std.standard_output << "hello\n";
math.abs(`-10`);
ascii.upper("hello");
json.stringify(`42`);
```

> **注意**：所有模块均使用 `import` 引入（生成 `Library` 句柄），不推荐使用 `->` 直接展开，避免命名空间污染。

---

## 模块条目规范

每个模块文档遵循统一结构：

1. **模块概述** — 功能定位、依赖关系、设计意图
2. **导出列表** — `public` 声明的所有公开标识符
3. **逐条目规范** — 每导出函数/常量/类型按统一模板：
   - **签名** — 完整声明
   - **参数表** — 名称、类型、必填、默认值、说明
   - **返回值** — 类型 + 语义
   - **异常/错误** — 触发条件、错误类型、说明
   - **示例** — 可运行代码 + 预期输出
   - **复杂度** — 时间/空间复杂度
   - **注意事项** — 易错点、平台差异、未定义行为
   - **版本** — 引入/变更版本
4. **内部辅助** — 以下划线 `_` 前缀标识，仅供维护者参考
5. **版本历史** — 模块级变更记录

---

## 快速查找表

### 数学与数值
| 需求 | 模块.函数 |
|------|-----------|
| 绝对值/符号/最值/区间限制 | `math.abs` / `math.sign` / `math.min` / `math.max` / `math.clamp` |
| 最大公约数/最小公倍数 | `math.gcd` / `math.lcm` |
| 奇偶/素数判断 | `math.is_even` / `math.is_odd` / `math.is_prime` |
| 阶乘/整数幂 | `math.factorial` / `math.power_integer` |
| 整数平方根/N次方根 | `math.square_root_integer` / `math.nth_root_integer` |
| 通用平方根 | `math.square_root` |
| 斐波那契/完全平方/组合数/排列数 | `math.fibonacci` / `math.is_perfect_square` / `math.combinations` / `math.permutations` |
| 数学常量 | `math.pi` / `math.e` / `math.square_root_two` |
| 进制转换(2/8/10/16) | `numeral_system.*` |
| 位运算 | `bit.bit_and` / `bit.bit_or` / `bit.bit_xor` / `bit.bit_not` / `bit.bit_left_shift` / `bit.bit_right_shift` |

### 字符串与编码
| 需求 | 模块.函数 |
|------|-----------|
| ASCII 编解码 | `ascii.ascii_decode` / `ascii.ascii_encode` |
| 字符分类(数字/字母/空白/可打印) | `ascii.is_digit` / `ascii.is_alpha` / `ascii.is_space` / `ascii.is_printable` |
| 大小写转换 | `ascii.to_upper` / `ascii.to_lower` / `ascii.upper` / `ascii.lower` |
| Base64 编解码 | `base64.base_sixty_four_encode` / `base64.base_sixty_four_decode` |

### 数据序列化
| 需求 | 模块.函数 |
|------|-----------|
| JSON 序列化/解析 | `json.stringify` / `json.parse` |

### 随机数
| 需求 | 模块.函数 |
|------|-----------|
| 设置种子 | `random.set_seed` |
| [0, 2^31-1] 随机整数 | `random.random` |
| [0, max) 随机整数 | `random.random_integer` |
| [min, max) 随机整数 | `random.random_range` |
| 列表随机选元素 | `random.random_choice` |
| 洗牌(返回新列表) | `random.shuffle` |
| 随机布尔值 | `random.random_boolean` |

### 核心扩展
| 需求 | 模块.函数 |
|------|-----------|
| 通用字符串转换 | `std.to_string` |
| 字符串长度/拼接/子串/分割/连接/大小写 | `std.string_length` / `std.string_concat` / `std.string_substring` / `std.string_split` / `std.string_join` / `std.string_upper` / `std.string_lower` |
| 列表映射/过滤/归约/查找/排序/反转/切片/包含 | `std.list_map` / `std.list_filter` / `std.list_reduce` / `std.list_find` / `std.list_sort` / `std.list_reverse` / `std.list_slice` / `std.list_contains` |
| 便捷 I/O | `std.print` / `std.println` / `std.read_line` / `std.read_all` |
| 反射/内省 | `std.type_name` / `std.members_of` / `std.has_member` / `std.get_member` |
| 控制流辅助 | `std.retry` / `std.times` / `std.until` |
| 函数式工具 | `std.identity` / `std.constant` / `std.pipe` |

---

## 相关链接

- [教程：标准库使用](../tutorial/standard_library.md) — 实战示例
- [语言参考：模块系统](../reference/modules.md) — import/->、路径解析、public、注解隔离
- [内置对象：核心类型](../builtins/) — 标准库构建基础
- [专题指南：性能优化](../howto/performance.md) — 标准库函数性能特征