# `random` 随机数库

> **导入**：`import "random" = *rand;`
> **来源**：`核心/standard_src/random.tsuc`，纯 Tanex Script 实现，线性同余生成器 (LCG)

---

## 模块概述

提供伪随机数生成：种子设置、多种分布采样、列表随机操作。内部使用 LCG (Linear Congruential Generator)，参数：乘数 `1664525`、增量 `1013904223`、模数 `2147483647` (2^31-1)。

**依赖**：仅依赖引导库核心类型。

**注意**：非加密安全，不可用于密码学用途。

---

## 导出列表 (`public`)

```tanex script
*** public = [
    "set_seed", "random", "random_integer", "random_range",
    "random_choice", "shuffle", "random_boolean"
];
```

---

## 逐条目规范

### `set_seed` — 设置随机种子

> **签名**：`*** set_seed = [*seed] => { random_seed = seed < 0 ? -seed : seed; }`  
> **参数**：`seed` (`Integer`) — 种子值，负数取绝对值  
> **返回值**：`none`  
> **示例**：
```tanex script
rand.set_seed(`12345);
```

---

### `random` — 生成 [0, 2^31-1] 随机整数

> **签名**：`*** random = [] => { random_seed = _lcg_next(random_seed); $ random_seed; }`  
> **返回值**：`Integer` (0 到 2,147,483,646)  
> **复杂度**：O(1)  
> **示例**：
```tanex script
rand.random();  # => `123456789 (依赖种子) #;
```

---

### `random_integer` — 生成 [0, max) 随机整数

> **签名**：`*** random_integer = [*max] => { $ max > 0 ? random() % max : 0; }`  
> **参数**：`max` (`Integer`) — 上界(不含，>0)  
> **返回值**：`Integer` (0 到 max-1)，`max <= 0` 返回 `0`  
> **示例**：
```tanex script
rand.random_integer(`10);  # => `0 到 `9 #;
```

---

### `random_range` — 生成 [min, max) 随机整数

> **签名**：`*** random_range = [*min, *max] => { $ max > min ? min + random() % (max - min) : min; }`  
> **参数**：
> - `min` (`Integer`) — 下界(含)
> - `max` (`Integer`) — 上界(不含)  
> **返回值**：`Integer`，`max <= min` 返回 `min`  
> **示例**：
```tanex script
rand.random_range(`5`, `15);  # => `5 到 `14 #;
```

---

### `random_choice` — 从列表随机选元素

> **签名**：`*** random_choice = [*list] => { $ list.size > 0 ? list.index(random() % list.size) : none; }`  
> **参数**：`list` (`List`) — 非空列表  
> **返回值**：列表元素类型，空列表返回 `none`  
> **示例**：
```tanex script
rand.random_choice(["a", "b", "c"]);  # => "a" 或 "b" 或 "c" #;
```

---

### `shuffle` — Fisher-Yates 洗牌

> **签名**：`*** shuffle = [*list] => { *r = ~clone_list(list); *i = r.size - 1; { i > 0 } $$ { *j = random() % (i + 1); *tmp = r.index(i); ~node_set(r, i, r.index(j)); ~node_set(r, j, tmp); i = i - 1; }; $ r; }`  
> **参数**：`list` (`List`) — 待洗牌列表  
> **返回值**：`List` (新列表，元素顺序随机，原列表不变)  
> **内部依赖**：`~clone_list`、`~node_set` (引导库/标准库内部辅助) [待确认：是否公开]  
> **复杂度**：O(N)  
> **示例**：
```tanex script
rand.shuffle([`1`, `2`, `3`, `4`, `5`]);  # => 如 [`3`, `1`, `5`, `2`, `4`] #;
```

---

### `random_boolean` — 随机布尔值

> **签名**：`*** random_boolean = [] => { $ random() % 2 == 0; }`  
> **返回值**：`Boolean` (等概率 `true`/`false`)  
> **示例**：
```tanex script
rand.random_boolean();  # => true 或 false #;
```

---

## 内部辅助(以下划线 `_` 前缀)

| 函数 | 用途 |
|------|------|
| `_lcg_next` | LCG 核心步进：`(1664525 * seed + 1013904223) % 2147483647` |
| `random_seed` | 内部状态变量 (初始值 `12345`) |

---

## 版本历史

| 版本 | 变更 |
|------|------|
| 1.0.0 | 基线导出：7 个随机函数 |
| 1.1.0 | 计划升级算法为 xoshiro256++，提升统计质量 |