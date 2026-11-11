# 内置对象参考

> 对标 [Python Built-in Types](https://docs.python.org/zh-cn/3.16/library/stdtypes.html)
>
> Tanex Script 内置对象分为：**核心类型**、**核心常量**、**核心函数**、**特殊成员槽位**。均由引导库 `bootstrap.tscc` 初始化，无需导入直接可用。

---

## 1. 核心类型

所有核心类型均为 `type_type` 的实例，在全局作用域以常量标识符绑定。

### 1.1 `type_type` — 基类型（元类型）

> **标识符**：`type_type`  
> **分类**：基类型  
> **一句话描述**：所有类型的模板，自身继承自身，由解释器内部提供。

#### 结构字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `initialize` | `Function` / `None` | 构造器，`Type{...}` 调用 |
| `inherit` | `Type` | 继承目标，`type_type` 指向自身 |
| `addable` | `Boolean` | 可新增标记，`true`/缺失=允许，`false`=封闭 |
| `external_read_only` | `Dict<MemberName, Boolean>` | 外部只读成员映射 |
| `public` | `List<String>` | 文件级导出列表 |
| `special_members` | `Dict` | 特殊成员槽位（见下） |

#### 特殊成员槽位完备表

| 类别 | 槽位名 | 触发运算符/协议 | 签名 | 返回期望 |
|------|--------|-----------------|------|----------|
| **构造/转换** | `initialize` | `Type{...}`、`Type(...)` | `(self, args...)` | 通常无/返回 self |
| | `boolean` | 真值判定(`if`/`!`/`&&`/`||`/`?`) | `(self)` | `Integer`/`Boolean` |
| | `string` | `<<`输出、字符串转换 | `(self)` | `String`(字符码链表) |
| | `include` | `in` 优先判定 | `(container, element)` | `Boolean` |
| | `index` | `a[b]` 下标、`in` 兜底遍历 | `(self, key)` | 值/`Address`/带`value`实例 |
| **算术(7)** | `addition` | `+` | `(self, other)` | 运算结果 |
| | `subtract` | `-` | `(self, other)` | 运算结果 |
| | `multiply` | `*` | `(self, other)` | 运算结果 |
| | `divide` | `/` | `(self, other)` | 运算结果 |
| | `exactly_divisible` | `\`(整除) | `(self, other)` | 运算结果 |
| | `modulo` | `%` | `(self, other)` | 运算结果 |
| | `power` | `^` | `(self, other)` | 运算结果 |
| **一元(2)** | `positive` | `+n`(一元) | `(self)` | 运算结果 |
| | `negative` | `-n`(一元) | `(self)` | 运算结果 |
| **比较(6)** | `greater` | `>` | `(self, other)` | `Boolean` |
| | `less` | `<` | `(self, other)` | `Boolean` |
| | `greater_equal` | `>=` | `(self, other)` | `Boolean` |
| | `less_equal` | `<=` | `(self, other)` | `Boolean` |
| | `equal` | `==` | `(self, other)` | `Boolean` |
| | `not_equal` | `!=` | `(self, other)` | `Boolean` |
| **三路比较** | `compare` | 最后兜底 | `(self, other)` | `Integer`/`Number`(负/零/正) |
| **行为控制** | `addable` | 类型可新增标记 | 布尔值 | — |
| | `external_read_only` | 成员外部只读标记 | 成员名→布尔映射 | — |
| | `inherit` | 继承目标 | `Type` | — |
| | `public` | 文件导出列表 | `List<String>` | — |

#### 继承复制规则

执行 `Child.inherit = Parent` 时：
1. 设置 `Child.inherit = Parent`
2. 全量复制 `Parent` 成员字典到 `Child`
3. **跳过三字段**：`addable`、`external_read_only`、`inherit` 不复制

---

### 1.2 `integer` — 原类型

> **标识符**：`integer`  
> **分类**：原类型  
> **一句话描述**：无符号任意精度整数，运行时直接以整数形式存在，不包装实例，无成员。

#### 特性

| 项目 | 说明 |
|------|------|
| 取值范围 | 理论无上限（受限内存），最小值 `0` |
| 字面量 | 十进制数字，支持 `_` 分隔：`` `1_000_000` `` |
| 负数表示 | 一元 `-` 运算符：`-` `42` |
| 运行时表示 | 非对象，不分配存储单元，解释器内部直接以整数运算 |
| 溢出行为 | 无溢出，任意精度算术 |
| 真值判定 | 非零为真，零为假 |
| 成员访问 | **不支持**，报错“类型不支持成员访问” |

#### 与 `Number` 混合运算

```tanex script
`10` + '0.5';    # => '10.5' (Integer 自动提升为 Number) #;
`10` / `3`;      # => '3.3333333333' (Number) #;
```

#### 除零行为

| 运算 | 结果 |
|------|------|
| `/` | `infinite` (符号随被除数)，`0/0` → `nan` |
| `\` | **报错**“整除除数不能为零” |
| `%` | **报错**“取余除数不能为零” |

---

### 1.3 `number` — 精确十进制数

> **标识符**：`number`  
> **分类**：复合类型  
> **一句话描述**：精确十进制数，内部 `front`(整数部分 `Integer`) + `back`(小数部分 `Integer`) + 隐含 `scale`(小数位数)。

#### 字面量语法

```tanex script
'3.14'; '-2.5'; '0'; '100'; '0.0001';
# 必须含小数点，单引号包裹
```

#### 内部表示

```tanex script
# '3.14' 表示为：
front = `3;      # 整数部分
back  = `14;     # 小数部分(去前导零)
scale = 2;      # 隐含小数位数
```

#### 构造方式

| 形式 | 语法 | 说明 |
|------|------|------|
| 字面量 | `'3.14'` | 标准 |
| 单参构造 | `Number{`42`}` | 整数部分=42，小数部分=0 |
| 双参快捷构造 | `Number{`3`, `14`}` | 直接指定 front/back (算术内部用) |
| 从 Number 拷贝 | `Number{'3.14'}` | 解构现有 Number |

#### 已注册特殊成员（引导库）

| 槽位 | 行为 |
|------|------|
| `initialize` | 单参：尝试取参数 `front` 成员，失败视参数为整数部分；双参：直接赋 front/back |
| `addition` | 对齐小数位(补零)、整数加法、处理进位、重组 front/back |
| `string` | 逐位提取数字 +48 得字符码，返回字符码链表 |
| `boolean` | 非零为真 |
| `greater`/`less`/`equal`/`not_equal` | 基于数值比较(已对齐小数位) |

#### 精度保证

```tanex script
'0.1' + '0.2';     # => '0.3' (精确，无 0.30000000000000004) #;
'2.7' + '2.3';     # => '5.0' #;
'1000000.1' - '1000000';  # => '0.1' #;
```

#### 注意事项

- 除法 `/` 可能产生无限循环小数，**当前实现截断到小数点后 3 位精度**
- 幂运算 `^` 指数为 `Number` 时按实数幂计算(可能引入近似) [待确认]
- 除零 → `infinite`，不报错

---

### 1.4 `string` — Unicode 字符串

> **标识符**：`string`  
> **分类**：复合类型  
> **一句话描述**：Unicode 字符串，底层单向链表(`List`)存储字符码点。

#### 字面量语法

```tanex script
"hello"; "中文\n"; "\"quoted\""; "\\path\\to\\file";
# 双引号包裹，支持转义序列
```

#### 转义序列

| 转义 | 码点 | 字符 |
|------|------|------|
| `\n` | 10 | LF 换行 |
| `\t` | 9 | HT 制表符 |
| `\"` | 34 | 双引号 |
| `\\` | 92 | 反斜杠 |
| `\r` | 13 | CR 回车 |
| `\b` | 8 | BS 退格 |
| `\f` | 12 | FF 换页 |
| `\v` | 11 | VT 垂直制表符 |

#### 内部结构

```tanex script
# "hello" 表示为：
data = List{  # 成员 data 持有链表
    head -> Node{value=`104`('h'), next->...}
    tail -> Node{value=`111`('o'), next=none}
    size = `5
}
```

#### 核心成员/方法

| 成员 | 类型 | 说明 |
|------|------|------|
| `data` | `List` | 内部字符码链表 |
| `push_char(code)` | 方法 | 追加单字符(码点 `Integer`) |
| `size` | `Integer` | 字符数(码点数，非字节数) |

#### 特殊成员

| 槽位 | 行为 |
|------|------|
| `string` | 返回 `data` 链表，供 `<<` 逐字符输出 |
| `boolean` | 非空串为真，空串为假 |
| `index` | `s[i]` 返回第 i 字符码点(`Integer`)，越界报错 |
| `include` | `"a" in "abc"` → `true` (逐字符比较) |

#### 示例

```tanex script
* s = "hello";
s.push_char(`33`);        # => "hello!" (码点 33 = '!') #;
s.data.size;              # => `6 #;
s[`0`];                   # => `104 ('h') #;
"hello" in "hello world"; # => true #;
```

---

### 1.5 `boolean` — 布尔类型

> **标识符**：`boolean`  
> **分类**：复合类型  
> **一句话描述**：仅两个值 `true`(存储 `1`) 和 `false`(存储 `0`)，算术运算返回 `Integer`。

#### 内部表示

实例含成员 `value` (`Integer`，`0` 或 `1`)。

#### 特殊成员

| 槽位 | 行为 |
|------|------|
| `boolean` | 返回自身 `value` |
| `addition` | `true + true` → `2` (`Integer`) |
| `subtract` | `true - false` → `1` |
| `multiply` | `true * false` → `0` |
| `divide` | `true / true` → `'1'` (`Number`) |
| `exactly_divisible` | `true \ true` → `1` |
| `modulo` | `true % true` → `0` |
| `power` | `true ^ false` → `1` |
| `string` | `"true"` / `"false"` 字符码链表 |

#### 常量

| 常量 | 值 | 类型 |
|------|------|------|
| `true` | 存储 `1` | `Boolean` |
| `false` | 存储 `0` | `Boolean` |

---

### 1.6 `none_type` / `none` — 空类型与单例

> **标识符**：`none_type`、`none`  
> **分类**：复合类型 / 单例  
> **一句话描述**：空类型，唯一值 `none`，全局单例，真值恒假，未初始化变量默认值。

#### 特殊成员

| 槽位 | 行为 |
|------|------|
| `boolean` | 恒返回 `false` |
| `string` | `"none"` 字符码链表 |

#### 示例

```tanex script
none;              # => none #;
none == none;      # => true (全局单例) #;
if(none, { $ "t"; }, { $ "f"; });  # => "f" #;
* x;               # 未赋值变量默认指向 none
x == none;         # => true #;
```

---

### 1.7 `nan_type` / `nan`、`infinite_type` / `infinite`、`-infinite` — 特殊数值

| 标识符 | 类型 | 说明 |
|--------|------|------|
| `nan` | `NaNType` | 非数字标记(如 `0/0`、`infinite - infinite`) |
| `infinite` | `InfiniteType` | 正无穷(除零产生) |
| `-infinite` | `InfiniteType` | 负无穷 |

#### 特殊成员行为

| 类型 | `boolean` | `string` | 算术运算 |
|------|-----------|----------|----------|
| `nan` | `false` | `"nan"` | 任意运算 → `nan` |
| `infinite` | `true` | `"infinite"` | 与有限数运算 → `infinite`；`infinite - infinite` → `nan` |
| `-infinite` | `true` | `"-infinite"` | 同理 |

---

### 1.8 `list` — 单向链表容器

> **标识符**：`list`  
> **分类**：复合类型  
> **一句话描述**：单向链表，头尾指针，O(1) 追加，O(n) 索引。字符串内部数据、字面量列表均共用此结构。

#### 字面量语法

```tanex script
[`1`, "hi", none];  # 方括号、逗号分隔
[];                 # 空列表
[`1`,];             # 尾部逗号自动填充 none
[`1`,, `2`];        # 中间空位填充 none
```

#### 内部结构

```tanex script
# ["a", "b", "c"]
head -> Node{value="a", next->Node{value="b", next->Node{value="c", next=none}}}
tail -> 最后节点
size = `3
```

#### 核心成员/方法

| 成员 | 类型/签名 | 说明 |
|------|-----------|------|
| `data` | `List` | 自身(字符串转换返回数据链表) |
| `head` | `Node`/`none` | 头节点 |
| `tail` | `Node`/`none` | 尾节点 |
| `size` | `Integer` | 元素数 |
| `append(value)` | 方法 | 追加元素到尾部，O(1) |
| `index(i)` | 方法 | 返回第 i 个元素值，O(n)，越界报错 |

#### 特殊成员

| 槽位 | 行为 |
|------|------|
| `string` | 返回 `data`(自身)，供 `<<` 输出 |
| `boolean` | 非空列表为真，空列表为假 |
| `index` | 支持 `list[i]` 下标访问 |
| `include` | `elem in list` 逐元素比较(`==`) |

---

### 1.9 `code` — 代码块类型

> **标识符**：`code`  
> **分类**：复合类型  
> **一句话描述**：惰性求值的代码块，含语句列表、定义时作用域、参数信息(仅匿名函数)。

#### 内部字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `statements` | `List<AST>` | 待执行语句 AST |
| `scope` | `Scope` | 定义时所在作用域(闭包捕获基础) |
| `params` | `List<ParamInfo>`/`None` | 匿名函数参数信息 |

#### 构造方式

| 形式 | 语法 | 说明 |
|------|------|------|
| 代码块字面量 | `{ stmt1; stmt2; }` | 产生无参 `code` 值 |
| 匿名函数 | `[*x, *y] => { $ x + y; }` | 产生带参数信息的 `code` 值 |

#### 执行机制

- 函数调用/控制流函数/`$$` 接收 `code` 值时，建立子作用域、绑定参数、逐句执行
- 代码块内 `$ expr` 提前返回值(或被 `$$` 收集)
- 无显式 `$` 时，最后一条语句的值为返回值

---

### 1.10 `address` — 地址值

> **标识符**：`address`  
> **分类**：复合类型  
> **一句话描述**：地址值，内部保存地址空间中的整数地址。

#### 操作

| 操作 | 语法 | 结果 |
|------|------|------|
| 取地址 | `/x` | `Address` 值 |
| 解地址读取 | `*addr` | 读取该地址存储单元的值 |
| 解地址赋值 | `*addr = val` | 写入该地址存储单元 |

---

### 1.11 `error` / `warning` — 错误与警告

> **标识符**：`error`、`warning`  
> **分类**：复合类型  
> **一句话描述**：错误/警告对象。`<- error{...}` 抛出，`|` 捕获。`warning` 类似但 `throw()` 不结束程序。

#### 成员/方法

| 成员 | 类型 | 说明 |
|------|------|------|
| `what` | `String` | 错误信息文本 |
| `throw()` | 方法 | 重新抛出：`Error.throw()` 等价 `<- self;`；`Warning.throw()` 打印警告继续 |

#### 构造

```tanex script
error{"divide by zero"};      # Error 实例
warning{"deprecated api"};    # Warning 实例
```

---

### 1.12 `library` — 模块句柄

> **标识符**：`library`  
> **分类**：复合类型  
> **一句话描述**：`import` 返回的模块句柄，内容通过成员访问，注解空间隔离。

#### 特性

- `import` 绑定的标识符为**常量**(不可重新赋值)
- 库内容**不展开**到全局作用域
- 库注解独立：`?? lib.member` 访问，**不**污染顶层 `?? member`

---

### 1.13 `function_name` / `type_name` — 函数名与类型名类型

> **标识符**：`function_name`、`type_name`  
> **分类**：复合类型  
> **一句话描述**：定义后的函数/类型标识符类型，作为值可传递、赋值、动态调用。

---

## 2. 核心常量

| 标识符 | 值 | 类型 | 说明 |
|--------|-----|------|------|
| `true` | 存储 `1` | `Boolean` | 布尔真 |
| `false` | 存储 `0` | `Boolean` | 布尔假 |
| `none` | 单例 | `NoneType` | 空值 |
| `nan` | 单例 | `NaNType` | 非数字 |
| `infinite` | 正无穷 | `InfiniteType` | `1/0` 产生 |
| `-infinite` | 负无穷 | `InfiniteType` | `-1/0` 产生 |
| `standard_output` | 透传处理函数 | `Function` | `<<` 左操作数默认处理函数 |
| `standard_input` | 读取处理函数 | `Function` | `>>` 左操作数默认处理函数 |

> `standard_output` / `standard_input` 可被替换以实现输出/输入管线定制。

---

## 3. 核心函数（引导库定义）

以下函数在引导库中以 Tanex Script 实现，作为全局函数可用：

| 函数 | 签名 | 说明 |
|------|------|------|
| `if` | `if(cond, then_code, else_code)` | 条件分支 |
| `for` | `for(*var, iterable, body_code)` | 遍历循环 |
| `while` | `while(cond_code, body_code)` | 条件循环 |
| `cycle` | `cycle(times, body_code)` | 定次循环 |
| `type_of` | `type_of(value)` | 一元运算符，返回类型对象 |

> 其余基础功能(算术、比较、I/O 等)通过**运算符特殊成员**提供，非函数形式。

---

## 4. 特殊成员注册协议

用户代码通过 `*** Type.member = fn` 注册特殊成员，运行时识别并重载对应运算符/协议。

### 注册语法

```tanex script
*** TypeName.special_member = [*self, *args...] => { ... };
```

### 完整注册表

| 类别 | 特殊成员 | 触发场景 | 签名 | 返回期望 |
|------|----------|----------|------|----------|
| **构造/转换** | `initialize` | `Type{...}`、`Type(...)` | `(self, args...)` | 通常无/返回 self |
| | `boolean` | 真值判定 | `(self)` | `Integer`/`Boolean` |
| | `string` | `<<` 输出、字符串转换 | `(self)` | `String`(字符码链表) |
| | `include` | `in` 优先判定 | `(container, element)` | `Boolean` |
| | `index` | `a[b]` 下标、`in` 兜底遍历 | `(self, key)` | 值/`Address`/带`value`实例 |
| **算术(7)** | `addition` | `+` | `(self, other)` | 运算结果 |
| | `subtract` | `-` | `(self, other)` | 运算结果 |
| | `multiply` | `*` | `(self, other)` | 运算结果 |
| | `divide` | `/` | `(self, other)` | 运算结果 |
| | `exactly_divisible` | `\`(整除) | `(self, other)` | 运算结果 |
| | `modulo` | `%` | `(self, other)` | 运算结果 |
| | `power` | `^` | `(self, other)` | 运算结果 |
| **一元(2)** | `positive` | `+n`(一元) | `(self)` | 运算结果 |
| | `negative` | `-n`(一元) | `(self)` | 运算结果 |
| **比较(6)** | `greater` | `>` | `(self, other)` | `Boolean` |
| | `less` | `<` | `(self, other)` | `Boolean` |
| | `greater_equal` | `>=` | `(self, other)` | `Boolean` |
| | `less_equal` | `<=` | `(self, other)` | `Boolean` |
| | `equal` | `==` | `(self, other)` | `Boolean` |
| | `not_equal` | `!=` | `(self, other)` | `Boolean` |
| **三路比较** | `compare` | 最后兜底 | `(self, other)` | `Integer`/`Number`(负/零/正) |
| **行为控制** | `addable` | 类型可新增标记 | 布尔值 | — |
| | `external_read_only` | 成员外部只读标记 | 成员名→布尔映射 | — |
| | `inherit` | 继承目标 | `Type` | — |
| | `public` | 文件导出列表 | `List<String>` | — |

### 注册示例

```tanex script
* MyType = type_type{};
*** MyType.initialize = [* self, * x] => { self.x = x; };
*** MyType.string = [* self] => { $ "MyType(" + self.x.string() + ")"; };
*** MyType.addition = [* self, * other] => { $ MyType{self.x + other.x}; };
*** MyType.less = [* self, * other] => { $ self.x < other.x; };
*** MyType.equal = [* self, * other] => { $ self.x == other.x; };
*** MyType.addable = false;  # 封闭类型
```

### 兜底调用规则

| 运算符 | 直接特殊成员 | 组合兜底(优先) | `compare` 兜底 | 对象同一性兜底 |
|--------|--------------|----------------|----------------|----------------|
| `>` | `greater` | `!(less \|\| equal)` | `compare > 0` | `false` |
| `<` | `less` | `!(greater \|\| equal)` | `compare < 0` | `false` |
| `>=` | `greater_equal` | `!less` | `compare >= 0` | 同一对象 |
| `<=` | `less_equal` | `!greater` | `compare <= 0` | 同一对象 |
| `==` | `equal` | `!not_equal` | `compare == 0` | 同一对象 |
| `!=` | `not_equal` | `!equal` | `compare != 0` | 非同一对象 |

---

## 相关链接

- [语言参考：类型系统](../reference/types.md) — 完整类型规范
- [语言参考：运算符重载](../reference/operator_overloading.md) — 特殊成员详细语义
- [标准库：standard](../library/standard.md) — 基于内置类型的封装函数
- [教程：自定义类型](../tutorial/advanced.md#自定义类型与运算符重载) — 实战示例