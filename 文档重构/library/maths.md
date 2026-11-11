# `maths` 数学库

> **导入**：`import "maths" = *math;`
> **来源**：`核心/standard_src/maths.tsuc`，纯 Tanex Script 实现

---

## 模块概述

提供常用数学函数与常量：算术辅助、数论、组合数学、常用常量。所有函数均为纯函数，无副作用。

**依赖**：`standard` 库（内部使用 `standard` 的基础算术与比较）。

---

## 导出列表 (`public`)

```tanex script
*** public = [
    "abs", "sign", "min", "max", "clamp",
    "gcd", "lcm", "is_even", "is_odd", "is_prime",
    "factorial", "power_integer", "square_root_integer",
    "pi", "e", "square_root_two",
    "square_root", "fibonacci", "is_perfect_square",
    "nth_root_integer", "combinations", "permutations"
];
```

---

## 逐条目规范

### 基础算术

#### `abs` — 绝对值

> **签名**：`*** abs = [*value] => { value < 0 ? -value : value; }`  
> **参数**：`value` (`Integer` \| `Number`) — 目标数值  
> **返回值**：同类型绝对值  
> **示例**：
```tanex script
math.abs(`-10);     # => `10 #;
math.abs('-3.14);   # => '3.14 #;
```

---

#### `sign` — 符号函数

> **签名**：`*** sign = [*value] => { value > 0 ? 1 : (value < 0 ? -1 : 0); }`  
> **参数**：`value` (`Integer` \| `Number`)  
> **返回值**：`Integer` (`1`/`0`/`-1`)  
> **示例**：
```tanex script
math.sign(`5);    # => `1 #;
math.sign(`-3);   # => -`1 #;
math.sign(`0);    # => `0 #;
```

---

#### `min` / `max` — 两数最小/最大值

> **签名**：`*** min = [*a, *b] => { a < b ? a : b; }`  
> **签名**：`*** max = [*a, *b] => { a > b ? a : b; }`  
> **参数**：`a`, `b` (`Integer` \| `Number`)  
> **返回值**：保留较高精度类型  
> **示例**：
```tanex script
math.min(`3`, `5`);     # => `3 #;
math.max('2.5', '3.1'); # => '3.1' #;
```

---

#### `clamp` — 区间限制

> **签名**：`*** clamp = [*v, *lo, *hi] => { v < lo ? lo : (v > hi ? hi : v); }`  
> **参数**：`v`(值), `lo`(下界), `hi`(上界) 均为 `Integer` \| `Number`  
> **返回值**：限制后的数值  
> **异常**：`lo > hi` 时行为未定义 [待确认：TODO 明确边界行为并同步实现]  
> **示例**：
```tanex script
math.clamp(`5`, `0`, `10`);   # => `5 #;
math.clamp(`-5`, `0`, `10`);  # => `0 #;
math.clamp(`15`, `0`, `10`);  # => `10 #;
```

---

### 数论函数

#### `gcd` — 最大公约数

> **签名**：`*** gcd = [*a, *b] => { *** r = b == 0 ? a : gcd(b, a % b); $ r; }` (欧几里得算法)  
> **参数**：`a`, `b` (`Integer`) — 非负整数  
> **返回值**：`Integer` (≥0)  
> **异常**：参数非 `Integer` 报错  
> **复杂度**：O(log min(a,b))  
> **示例**：
```tanex script
math.gcd(`48`, `18`);  # => `6 #;
math.gcd(`0`, `5`);    # => `5 #;
```

---

#### `lcm` — 最小公倍数

> **签名**：`*** lcm = [*a, *b] => { $ a * b \ gcd(a, b); }`  
> **参数**：`a`, `b` (`Integer`)  
> **返回值**：`Integer`  
> **示例**：
```tanex script
math.lcm(`4`, `6`);  # => `12 #;
```

---

#### `is_even` / `is_odd` — 奇偶判断

> **签名**：`*** is_even = [*v] => { $ v % 2 == 0; }`  
> **签名**：`*** is_odd = [*v] => { $ v % 2 != 0; }`  
> **参数**：`v` (`Integer`)  
> **返回值**：`Boolean`  
> **示例**：
```tanex script
math.is_even(`4);  # => true #;
math.is_odd(`5);   # => true #;
```

---

#### `is_prime` — 质数判断

> **签名**：`*** is_prime = [*v] => { *r = true; v < 2 ? { r = false; } : {}; *i = 2; { r && i * i <= v } $$ { v % i == 0 ? { r = false; } : {}; i = i + 1; }; $ r; }` (试除法至 √n)  
> **参数**：`v` (`Integer`) — ≥0  
> **返回值**：`Boolean`  
> **异常**：`v < 0` 返回 `false`  
> **复杂度**：O(√n)  
> **示例**：
```tanex script
math.is_prime(`7);   # => true #;
math.is_prime(`8);   # => false #;
math.is_prime(`1);   # => false #;
```

---

#### `factorial` — 阶乘

> **签名**：`*** factorial = [*v] => { v < 0 ? { <- error{"factorial: 参数不能为负数"}; } : {}; *** r = v <= 1 ? 1 : v * factorial(v - 1); $ r; }`  
> **参数**：`v` (`Integer`) — 非负整数  
> **返回值**：`Integer`  
> **异常**：`v < 0` 抛出 `error{"factorial: 参数不能为负数"}`  
> **复杂度**：O(n) 递归调用  
> **注意**：大数阶乘增长极快，注意内存  
> **示例**：
```tanex script
math.factorial(`5);  # => `120 #;
math.factorial(`0);  # => `1 #;
```

---

#### `power_integer` — 整数幂（快速幂）

> **签名**：`*** power_integer = [*base, *exponent] => { ... }` (二分快速幂 O(log exp))  
> **参数**：`base`(`Integer`), `exp`(`Integer` ≥0)  
> **返回值**：`Integer`  
> **异常**：`exp < 0` 返回 `0`  
> **复杂度**：O(log exp) 快速幂算法  
> **示例**：
```tanex script
math.power_integer(`2`, `10);  # => `1024
math.power_integer(`5`, `0);   # => `1
```

---

#### `square_root_integer` — 整数平方根(向下取整)

> **签名**：牛顿法实现  
> **参数**：`v` (`Integer`) — 非负整数  
> **返回值**：`Integer` (⌊√v⌋)  
> **异常**：`v < 0` 抛出错误  
> **复杂度**：O(log n) 牛顿迭代  
> **示例**：
```tanex script
math.square_root_integer(`10);  # => `3 #;
math.square_root_integer(`16);  # => `4 #;
```

---

### 数学常量

| 常量 | 签名 | 类型 | 近似值 | 说明 |
|------|------|------|--------|------|
| `pi` | `*** pi = number{3, 1416};` | `Number` | 3.1416 | 圆周率 |
| `e` | `*** e = number{2, 718};` | `Number` | 2.718 | 自然对数底 |
| `square_root_two` | `*** square_root_two = number{1, 414};` | `Number` | 1.414 | √2 |

> **注意**：精度仅 4 位小数，高精度计算需自行实现更精确版本。

---

### 进阶数学函数

#### `square_root` — 通用平方根

> **签名**：`*** square_root = [*v] => { *** r = v.front | _ : _sqrt_int(v) : _sqrt_num(v); $ r; }`  
> **参数**：`v` (`Integer` \| `Number`) — 非负数值  
> **返回值**：`Number`  
> **异常**：`v < 0` 抛出错误  
> **内部辅助**：`_sqrt_int`(整数牛顿法)、`_sqrt_num`(Number 牛顿法，固定 10 次迭代)  
> **复杂度**：整数 O(log n)，Number 固定 10 次迭代  
> **示例**：
```tanex script
math.square_root(`4);      # => '2.0 #;
math.square_root('2.0);    # => '1.4142... #;
```

---

#### `fibonacci` — 斐波那契数

> **签名**：迭代 O(n) 实现  
> **参数**：`n` (`Integer`) — ≥0  
> **返回值**：`Integer` (F(n))  
> **异常**：`n < 0` 抛出错误  
> **复杂度**：O(n)  
> **示例**：
```tanex script
math.fibonacci(`0);  # => `0 #;
math.fibonacci(`1);  # => `1 #;
math.fibonacci(`10); # => `55 #;
```

---

#### `is_perfect_square` — 完全平方数判断

> **签名**：`*** is_perfect_square = [*v] => { *r = false; v >= 0 ? { *rt = square_root_integer(v); r = rt * rt == v; } : {}; $ r; }`  
> **参数**：`v` (`Integer`)  
> **返回值**：`Boolean`  
> **示例**：
```tanex script
math.is_perfect_square(`16);  # => true #;
math.is_perfect_square(`15);  # => false #;
```

---

#### `nth_root_integer` — N 次方根(整数近似)

> **签名**：牛顿法求整数近似(向下取整)  
> **参数**：`v`(`Integer`), `deg`(`Integer` ≥1)  
> **返回值**：`Integer` (⌊v^(1/deg)⌋)  
> **异常**：
> - `deg <= 0` 抛出错误
> - `v < 0` 且 `deg` 为偶数抛出错误  
> **复杂度**：O(log v) 牛顿迭代  
> **示例**：
```tanex script
math.nth_root_integer(`27`, `3);  # => `3 #;
math.nth_root_integer(`16`, `4);  # => `2 #;
```

---

#### `combinations` / `permutations` — 组合数与排列数

> **签名**：
> - `*** combinations = [*total, *count] => { ... }` — C(total, count)
> - `*** permutations = [*total, *count] => { ... }` — P(total, count)

| 参数 | 类型 | 说明 |
|------|------|------|
| `total` | `Integer` | 总元素数(≥0) |
| `count` | `Integer` | 选择数(≥0) |

**返回值**：`Integer`  
**异常**：`count < 0` 或 `count > total` 返回 `0`  
**复杂度**：O(min(count, total-count))  
**示例**：
```tanex script
math.combinations(`5`, `2);   # => `10 (C(5,2)) #;
math.permutations(`5`, `2);   # => `20 (P(5,2)) #;
```

---

## 内部辅助(以下划线 `_` 前缀)

| 函数 | 用途 |
|------|------|
| `_square_root_integer` | 整数牛顿法平方根(供 `square_root` 内部调用) |
| `_square_root_number` | Number 牛顿法平方根(固定 10 次迭代) |

---

## 版本历史

| 版本 | 变更 |
|------|------|
| 1.0.0 | 基线导出：25 个函数/常量 |
| 1.1.0 | 优化 `power_integer` 为快速幂、修复 `nth_root_integer` 负数处理 |