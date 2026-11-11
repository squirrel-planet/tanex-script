# 性能优化指南

> Tanex Script 程序性能分析与优化实战。

---

## 1. 性能特征概览

| 维度 | 特征 | 优化建议 |
|------|------|----------|
| **解释执行** | AST 树遍历，无 JIT | 减少热路径函数调用、内联小函数 |
| **动态分发** | 运行时查找特殊成员 | 热路径使用内置类型、避免过度重载 |
| **精确十进制** | `Number` 对齐小数位、进位 | 高频计算用 `Integer`、定点数手动实现 |
| **链表存储** | `List`/`String` 单向链表 | 批量操作用 `append`、避免 `+` 拼接大字符串 |
| **传地址调用** | 参数传地址、共享存储 | 避免不必要的副作用、显式复制 |
| **无 TCO** | 递归无尾调用优化 | 深度递归改写为 `$$` 循环或 `cycle` |

---

## 2. 基准测试方法

### 2.1 简单计时

```tanexscript
*** bench = [*fn, *iterations] => {
    * start = time_now();  # 假设有 time_now()
    * i = `0;
    { i < iterations } $$ { fn(); i = i + `1; };
    * end = time_now();
    $ end - start;
};

* elapsed = bench({ *x => { compute(); } }, `10000);
std.println("Elapsed: " + elapsed.string() + "ms");
```

### 2.2 标准库 `time` (计划中)

```tanexscript
import "time" = *time;
* start = time.perf_counter();
compute();
* elapsed = time.perf_counter() - start;
```

---

## 3. 常见优化模式

### 3.1 循环优化

#### ❌ 低效：列表拼接
```tanexscript
* result = "";
for(* i, [`1`..`10000`], {
    result = result + i.string();  # 每次创建新字符串，O(n²)
});
```

#### ✅ 高效：StringBuilder 模式
```tanexscript
* sb = String{};
for(* i, [`1`..`10000`], {
    sb.push_str(i.string());  # O(1) 追加
});
* result = sb.string();
```

#### ✅ 高效：预分配列表
```tanexscript
* result = List{};
for(* i, [`1`..`10000`], {
    result.append(i.string());  # O(1) 追加
});
```

### 3.2 避免重复计算

```tanexscript
# ❌ 每次循环重新计算 list.size
for(* i, list, {
    do_something(list.size);  # size 每次遍历链表 O(n)
});

# ✅ 缓存 size
* sz = list.size;
for(* i, list, {
    do_something(sz);
});
```

### 3.3 内联小函数

```tanexscript
# ❌ 热路径调用小函数
*** add1 = [*x] => { $ x + `1; };
for(* i, list, { $ add1(i); });

# ✅ 手动内联
for(* i, list, { $ i + `1; });
```

### 3.4 使用内置类型而非用户类型

```tanexscript
# ❌ 用户类型封装整数
* Counter = type_type{};
*** Counter.initialize = [*self, *v] => { self.v = v; };
*** Counter.inc = [*self] => { self.v = self.v + `1; };

* c = Counter{`0};
for(* i, [`1`..`1000000`], { c.inc(); });  # 每次方法调用、属性访问

# ✅ 直接用 Integer
* c = `0;
for(* i, [`1`..`1000000`], { c = c + `1; });  # 纯整数运算
```

---

## 4. 标准库选择指南

| 任务 | 推荐 | 避免 | 理由 |
|------|------|------|------|
| 列表映射 | `std.list_map` | 手写 `for` + `append` | 内部优化、减少解释器开销 |
| 列表过滤 | `std.list_filter` | 手写 `for` + `if` | 同上 |
| 列表归约 | `std.list_reduce` | 手写循环累加 | 同上 |
| 字符串拼接 | `String.push_str` / `List` + `join` | `+` 循环拼接 | 避免 O(n²) |
| 随机数 | `random.random_integer` | 手写 LCG | 标准库实现更优 |
| 排序 | `std.list_sort` | 手写排序 | 内部优化算法 |

---

## 5. 内存优化

### 5.1 避免不必要的闭包捕获

```tanexscript
# ❌ 捕获大对象
* big_data = load_huge_list();
* process = [*item] => {  # 捕获 big_data
    do_something(big_data, item);
};

# ✅ 传参而非捕获
*** process = [*data, *item] => { ... };
for(* item, list, { process(big_data, item); });
```

### 5.2 及时释放大对象引用

```tanexscript
* huge = load_huge();
process(huge);
huge = none;  # 显式释放引用，便于 GC (若有)
```

### 5.3 复用对象而非重新创建

```tanexscript
# ❌ 每次创建新 StringBuilder
for(* i, items, {
    * sb = String{};
    sb.push_str(item.string());
    output(sb);
});

# ✅ 复用 (需手动重置)
* sb = String{};
for(* i, items, {
    sb.clear();  # 假设有 clear()
    sb.push_str(item.string());
    output(sb);
});
```

---

## 6. 算法层面优化

### 6.1 选择合适数据结构

| 操作模式 | 推荐结构 | 复杂度 |
|----------|----------|--------|
| 频繁追加、顺序遍历 | `List` (链表) | 追加 O(1) |
| 频繁随机访问 | 暂无数组类型 | — |
| 频繁 `in` 判定 | 自定义 `HashSet` (`include`) | O(1) |
| 频繁键值查找 | `Dictionary` (哈希表) | O(1) |
| 有序遍历、范围查询 | `TreeMap` (BST) | O(log n) |

### 6.2 空间换时间

```tanexscript
# 预计算查找表
* squares = List{};
for(* i, [`0`..`10000`], { squares.append(i * i); });

# 后续 O(1) 查询
* square = squares.index(n);
```

---

## 7. 解释器配置调优

### 7.1 递归限制

```bash
# 深度递归程序
export TANEX_RECURSION_LIMIT=10000
tanex run deep_recursion.tsuc
```

### 7.2 栈大小

```bash
# 大量局部变量、深度嵌套表达式
export TANEX_STACK_SIZE=32768
tanex run complex_expr.tsuc
```

---

## 8. 性能分析工具 (计划中)

### 8.1 内置 Profiler

```tanexscript
# 计划中
import "profile" = *prof;
prof.start();
run_program();
prof.stop();
prof.print_stats();
# Function          Calls    Total(ms)  Per Call(ms)
# compute           10000    120.5      0.012
# list_map          5000     80.2       0.016
```

### 8.2 火焰图导出

```tanexscript
prof.export_flamegraph("profile.svg");
```

---

## 9. 实战案例：优化斐波那契计算

### 9.1 朴素递归 (指数级)

```tanexscript
*** fib = [*n] => {
    n <= `1 ? { $ n; } : { $ fib(n - `1) + fib(n - `2); };
};
fib(`35);  # 极慢，大量重复计算
```

### 9.2 记忆化 (线性)

```tanexscript
*** fib_memo = [*n] => {
    * memo = Dictionary{};
    *** helper = [*k] => {
        memo.has_key(k) ? { $ memo.get(k); } : {
            * v = k <= `1 ? k : helper(k - `1) + helper(k - `2);
            memo.set(k, v);
            $ v;
        };
    };
    $ helper(n);
};
```

### 9.3 迭代循环 (最优)

```tanexscript
*** fib_iter = [*n] => {
    n <= `1 ? { $ n; } : {
        * a = `0; * b = `1;
        * i = `2;
        { i <= n } $$ {
            * c = a + b;
            a = b; b = c;
            i = i + `1;
        };
        $ b;
    };
};
fib_iter(`100000);  # 极快，O(n) 时间 O(1) 空间
```

### 9.4 快速倍增 (对数级)

```tanexscript
# 矩阵快速幂或快速倍增公式
*** fib_fast = [*n] => {
    n == `0 ? { $ `0; } : {
        *** fib_pair = [*k] => {
            k == `1 ? { $ [`0`, `1`]; } : {
                * half = fib_pair(k \ `2);
                * a = half[`0]; * b = half[`1];
                * c = a * (b * `2 - a);
                * d = a * a + b * b;
                k % `2 == `0 ? { $ [c, d]; } : { $ [d, c + d]; };
            };
        };
        $ fib_pair(n)[`1];
    };
};
fib_fast(`1000000);  # 极快，O(log n)
```

---

## 10. 性能清单

| 类别 | 检查项 |
|------|--------|
| **循环** | 缓存 `size`、避免 `+` 拼接字符串/列表、使用 `append`/`push_str` |
| **函数** | 热路径内联小函数、避免不必要的闭包捕获、用内置类型替代用户类型 |
| **数据结构** | 选合适结构：`in` 判定用 `include`、频繁查找用 `Dictionary` |
| **算法** | 优先迭代而非递归、记忆化/DP 避免重复计算、快速幂加速 |
| **标准库** | 优先用标准库高阶函数 (`list_map` 等) 而非手写循环 |
| **配置** | 深度递归调大 `TANEX_RECURSION_LIMIT`、复杂表达式调大 `TANEX_STACK_SIZE` |

---

## 相关链接

- [语言参考：表达式](../reference/expressions.md) — 循环符 `$$`、管道 `|>`
- [标准库：standard](../library/standard.md) — `list_map`/`list_filter`/`list_reduce`
- [标准库：random](../library/random.md) — 随机数性能
- [专题指南：类型设计](type_design.md) — 类型设计性能影响
- [扩展与嵌入](../extending/) — Python API 性能分析