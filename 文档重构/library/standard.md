# `standard` 核心扩展模块

> **导入**：`import "standard" = *std;`
> **来源**：引导库扩展，提供开箱即用的基础设施

---

## 模块概述

`standard` 是语言内置的基础功能集合，在引导库 `bootstrap.tsuc` 之上进一步封装的常用工具函数、类型构造辅助、I/O 封装、反射/内省接口。设计意图：减少用户重复造轮子，提供统一的基础 API。

**依赖**：仅依赖引导库核心类型（无外部依赖）。

---

## 导出列表 (`public`)

```tanex script
*** public = [
    # 类型构造辅助
    "Integer", "Number", "String", "Boolean", "List", "Code", "Dictionary",
    # 基础算术与比较
    "abs", "sign", "min", "max", "clamp",
    # 字符串操作
    "to_string", "string_length", "string_concat", "string_substring",
    "string_split", "string_join", "string_upper", "string_lower",
    # 列表操作
    "list_map", "list_filter", "list_reduce", "list_find", "list_sort",
    "list_reverse", "list_slice", "list_contains",
    # I/O 封装
    "print", "println", "read_line", "read_all",
    # 反射/内省
    "type_name", "members_of", "has_member", "get_member",
    # 控制流辅助
    "retry", "times", "until",
    # 函数式工具
    "identity", "constant", "pipe"
];
```

---

## 逐条目规范

### 类型构造辅助

#### `Integer` — 整数类型构造器

> **签名**：`*** Integer = [*value] => { number{value, `0}; }`  
> **一句话描述**：将数值转为 `Number` 类型（整数部分=原值，小数部分=0）。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `value` | `Integer` \| `Number` | 是 | 源数值 |

**返回值**：`Number` 类型。

**示例**：
```tanex script
std.Integer(`42);     # => '42.0' #;
std.Integer('3.14');  # => '3.14' (保持原值) #;
```

---

#### `Number` — 数字类型构造器

> **签名**：`*** Number = [*front, [*back, integer, `0]] => { number{front, back}; }`  
> **一句话描述**：构造 `Number` 类型，支持单参(整数部分)或双参(整数/小数部分)。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `front` | `Integer` | 是 | — | 整数部分 |
| `back` | `Integer` | 否 | `0` | 小数部分 |

**返回值**：`Number` 类型。

**示例**：
```tanex script
std.Number(`3, `14);  # => '3.14' #;
std.Number(`42);      # => '42.0' #;
```

---

#### `String` / `Boolean` / `List` / `Code` / `Dictionary` — 类型构造器

> **签名**：对应类型的构造器别名，如 `*** String = [*items] => { string{items}; }`  
> **一句话描述**：提供统一的类型构造入口。

**示例**：
```tanex script
std.String([`72`, `101`]);  # => "He" (从码点列表) #;
std.List([`1`, `2`]);       # => [`1`, `2`] #;
std.Code({ $ `1; });        # => 代码块值 #;
```

---

### 基础算术与比较

#### `abs` — 绝对值

> **签名**：`*** abs = [*value] => { value < 0 ? -value : value; }`  
> **一句话描述**：返回数值的绝对值。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `value` | `Integer` \| `Number` | 是 | 目标数值 |

**返回值**：同类型绝对值。

**示例**：
```tanex script
std.abs(`-10);      # => `10 #;
std.abs('-3.14);    # => '3.14 #;
```

---

#### `sign` — 符号函数

> **签名**：`*** sign = [*value] => { value > 0 ? 1 : (value < 0 ? -1 : 0); }`  
> **一句话描述**：返回符号：正 `1`、负 `-1`、零 `0`。

**返回值**：`Integer`。

**示例**：
```tanex script
std.sign(`5);    # => `1 #;
std.sign(`-3);   # => -`1 #;
std.sign(`0);    # => `0 #;
```

---

#### `min` / `max` — 两数最小/最大值

> **签名**：`*** min = [*a, *b] => { a < b ? a : b; }`  
> **签名**：`*** max = [*a, *b] => { a > b ? a : b; }`  
> **一句话描述**：返回两数中较小/较大值。

**返回值**：保留较高精度类型。

**示例**：
```tanex script
std.min(`3`, `5`);     # => `3 #;
std.max('2.5', '3.1'); # => '3.1' #;
```

---

#### `clamp` — 区间限制

> **签名**：`*** clamp = [*v, *lo, *hi] => { v < lo ? lo : (v > hi ? hi : v); }`  
> **一句话描述**：将数值限制在 `[lo, hi]` 闭区间内。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `v` | `Integer` \| `Number` | 是 | 待限制数值 |
| `lo` | `Integer` \| `Number` | 是 | 下界(含) |
| `hi` | `Integer` \| `Number` | 是 | 上界(含) |

**返回值**：限制后的数值。

**异常**：`lo > hi` 时行为未定义 [待确认]。

**示例**：
```tanex script
std.clamp(`5`, `0`, `10`);   # => `5 #;
std.clamp(`-5`, `0`, `10`);  # => `0 #;
std.clamp(`15`, `0`, `10`);  # => `10 #;
```

---

### 字符串操作

#### `to_string` — 通用字符串转换

> **签名**：`*** to_string = [*value] => { "" + value; }`  
> **一句话描述**：将任意值转为字符串(调用值的 `string` 特殊成员)。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `value` | 任意 | 是 | 待转换值 |

**返回值**：`String`。

**异常**：值类型无 `string` 特殊成员时报错。

**示例**：
```tanex script
std.to_string(`42);       # => "42" #;
std.to_string('3.14);     # => "3.14" #;
std.to_string(true);      # => "true" #;
std.to_string(none);      # => "none" #;
```

---

#### `string_length` — 字符串长度

> **签名**：`*** string_length = [*s] => { s.data.size; }`  
> **一句话描述**：返回字符串的字符数(链表节点数)。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `s` | `String` | 是 | 目标字符串 |

**返回值**：`Integer`(字符数)。

**示例**：
```tanex script
std.string_length("hello");  # => `5 #;
std.string_length("");       # => `0 #;
```

**注意**：返回**字符数**(码点数)，非字节数。UTF-8 编码下多字节字符计为 1。

---

#### `string_concat` — 字符串拼接

> **签名**：`*** string_concat = [*a, *b] => { a + b; }`  
> **一句话描述**：拼接两个字符串。

**示例**：
```tanex script
std.string_concat("hello", " world");  # => "hello world" #;
```

---

#### `string_substring` — 子串提取

> **签名**：`*** string_substring = [*s, *start, *end] => { ... }`  
> **一句话描述**：返回字符串 `[start, end)` 区间的子串(字符索引)。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `s` | `String` | 是 | 目标字符串 |
| `start` | `Integer` | 是 | 起始索引(含，0-based) |
| `end` | `Integer` | 是 | 结束索引(不含) |

**返回值**：`String`。

**异常**：索引越界报错 [待确认]。

**示例**：
```tanex script
std.string_substring("hello", `1`, `4`);  # => "ell" #;
```

---

#### `string_split` / `string_join` — 分割与连接

> **签名**：
> - `*** string_split = [*s, *sep] => { ... }`
> - `*** string_join = [*list, *sep] => { ... }`

| 函数 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `string_split` | `s`(String), `sep`(String) | `List<String>` | 按分隔符分割 |
| `string_join` | `list`(List<String>), `sep`(String) | `String` | 用分隔符连接 |

**示例**：
```tanex script
std.string_split("a,b,c", ",");     # => ["a", "b", "c"] #;
std.string_join(["a", "b", "c"], "-"); # => "a-b-c" #;
```

---

#### `string_upper` / `string_lower` — 大小写转换

> **签名**：ASCII 范围大小写转换。

**示例**：
```tanex script
std.string_upper("Hello");  # => "HELLO" #;
std.string_lower("HELLO");  # => "hello" #;
```

**注意**：仅处理 ASCII 字母(A-Z/a-z)，非 ASCII 字符保持不变。

---

### 列表操作

#### `list_map` — 映射

> **签名**：`*** list_map = [*list, *fn] => { *r=List{}; for(*i,list,{r.append(fn(i));}); $r; }`  
> **一句话描述**：对列表每个元素应用函数，返回新列表。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `list` | `List` | 是 | 输入列表 |
| `fn` | `Function` | 是 | 映射函数 `(element) -> new_element` |

**返回值**：`List`(新元素列表)。

**示例**：
```tanex script
std.list_map([`1`,`2`,`3`], [*x] => { $ x * `2; });  # => [`2`,`4`,`6`] #;
```

---

#### `list_filter` — 过滤

> **签名**：`*** list_filter = [*list, *pred] => { *r=List{}; for(*i,list,{pred(i)?{r.append(i);}:{};}); $r; }`  
> **一句话描述**：返回满足谓词的元素列表。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `list` | `List` | 是 | 输入列表 |
| `pred` | `Function` | 是 | 谓词函数 `(element) -> Boolean` |

**返回值**：`List`(仅含满足谓词的元素)。

**示例**：
```tanex script
std.list_filter([`1`,`2`,`3`,`4`], [*x] => { $ x % `2 == `0; });  # => [`2`,`4`] #;
```

---

#### `list_reduce` — 归约

> **签名**：`*** list_reduce = [*list, *fn, *init] => { *acc=init; for(*i,list,{acc=fn(acc,i);}); $acc; }`  
> **一句话描述**：从左到右归约列表。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `list` | `List` | 是 | 输入列表 |
| `fn` | `Function` | 是 | 归约函数 `(acc, element) -> new_acc` |
| `init` | 任意 | 是 | 初始累积值 |

**返回值**：最终累积值。

**示例**：
```tanex script
std.list_reduce([`1`,`2`,`3`], [*acc, *x] => { $ acc + x; }, `0);  # => `6 #;
```

---

#### `list_find` — 查找首个满足谓词的元素

> **签名**：`*** list_find = [*list, *pred] => { for(*i,list,{pred(i)?{$i;}:{};}); $none; }`  
> **一句话描述**：返回首个满足谓词的元素，无则 `none`。

**返回值**：元素类型或 `none`。

**示例**：
```tanex script
std.list_find([`1`,`2`,`3`], [*x] => { $ x > `2; });  # => `3 #;
```

---

#### `list_sort` / `list_reverse` / `list_slice` / `list_contains`

| 函数 | 签名 | 返回值 | 示例 |
|------|------|--------|------|
| `list_sort` | `*** list_sort = [*list, *cmp?] => { ... }` | `List`(排序后) | `std.list_sort([`3`,`1`,`2`]) => [`1`,`2`,`3`] |
| `list_reverse` | `*** list_reverse = [*list] => { ... }` | `List`(反转) | `std.list_reverse([`1`,`2`,`3`]) => [`3`,`2`,`1`] |
| `list_slice` | `*** list_slice = [*list, *start, *end?] => { ... }` | `List`(切片) | `std.list_slice([`1`,`2`,`3`,`4`], `1`, `3`) => [`2`,`3`] |
| `list_contains` | `*** list_contains = [*list, *elem] => { elem in list; }` | `Boolean` | `std.list_contains([`1`,`2`], `2`) => true |

---

### I/O 封装

#### `print` / `println` — 便捷输出

> **签名**：
> - `*** print = [*v] => { std.standard_output << v; $ v; }`
> - `*** println = [*v] => { print(v); std.standard_output << "\n"; }`

**示例**：
```tanex script
std.print("hello");      # 输出 hello(无换行)
std.println("world");    # 输出 world\n
```

---

#### `read_line` / `read_all` — 便捷输入

> **签名**：
> - `*** read_line = [] => { *b=""; std.standard_input >> b; $ b; }`
> - `*** read_all = [] => { *r=""; *b=""; { std.standard_input >> b; b==""?{break;}:{r=r+b;}; } $$ {;}; $ r; }`

**示例**：
```tanex script
* line = std.read_line();  # 读取一行
* all = std.read_all();    # 读取全部直到 EOF
```

---

### 反射/内省

#### `type_name` — 获取类型名称

> **签名**：`*** type_name = [*v] => { type_of(v).name; }`  
> **一句话描述**：返回值的类型名称字符串。

**示例**：
```tanex script
std.type_name(`42);           # => "Integer" #;
std.type_name("hello");       # => "String" #;
```

---

#### `members_of` / `has_member` / `get_member` — 成员反射

> **签名**：
> - `*** members_of = [*obj] => { ... }` — 返回成员名列表
> - `*** has_member = [*obj, *name] => { ... }` — 判断是否有成员
> - `*** get_member = [*obj, *name] => { obj.name; }` — 获取成员值

**示例**：
```tanex script
std.members_of("hello");       # => ["data", "size", "push_char", ...] #;
std.has_member("hello", "size"); # => true #;
std.get_member("hello", "size"); # => `5 #;
```

---

### 控制流辅助

#### `retry` — 重试执行

> **签名**：`*** retry = [*times, *fn, *delay?] => { ... }`  
> **一句话描述**：执行 `fn`，失败等待 `delay` 重试，最多 `times` 次。

**示例**：
```tanex script
std.retry(`3, { risky(); }, '1.0);  # 最多重试 3 次，间隔 1 秒
```

---

#### `times` — 执行 N 次

> **签名**：`*** times = [*n, *fn] => { cycle(n, fn); }`  
> **一句话描述**：执行 `fn` n 次。

**示例**：
```tanex script
std.times(`3`, { std.println("hi"); });  # 输出 3 次 hi
```

---

#### `until` — 直到条件为真

> **签名**：`*** until = [*cond, *fn] => { while({ !cond(); }, fn); }`  
> **一句话描述**：重复执行 `fn` 直到 `cond` 返回真。

**示例**：
```tanex script
std.until({ $ flag; }, { do_work(); });  # 直到 flag 为真
```

---

### 函数式工具

#### `identity` — 恒等函数

> **签名**：`*** identity = [*x] => { $ x; }`  
> **示例**：`std.identity(`5) => `5`

---

#### `constant` — 常量函数

> **签名**：`*** constant = [*c] => { [*] => { $ c; }; }`  
> **示例**：`std.constant(`42)() => `42`

---

#### `pipe` — 函数管道组合

> **签名**：`*** pipe = [*fns...] => { [*x] => { ... } }`  
> **一句话描述**：将多个函数组合为管道，左到右依次应用。

**示例**：
```tanex script
* add1_then_mul2 = std.pipe([[*x] => { $ x + `1; }, [*x] => { $ x * `2; }]);
add1_then_mul2(`5);  # => `12 #;
```

---

## 内部辅助(以下划线 `_` 前缀)

以下函数为内部实现细节，**不在 `public` 列表中**，仅供维护者参考：

| 函数 | 用途 |
|------|------|
| `_clone_list` | 深拷贝列表(供 `shuffle` 等) |
| `_node_set` | 设置链表节点值(供 `shuffle` 等) |
| `_stringify_value` | JSON 序列化内部递归函数 |
| `_parse_value` | JSON 解析内部递归函数 |

---

## 版本历史

| 版本 | 变更 |
|------|------|
| 1.0.0 | 基线导出：20+ 函数/常量/类型构造器 |
| 1.1.0 | 新增 `retry`/`until`、完善 `list_sort` 可选比较函数 |