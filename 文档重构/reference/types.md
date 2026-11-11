# 类型系统

> 对标 [Python Data Model](https://docs.python.org/zh-cn/3.16/reference/datamodel.html)
>
> Tanex Script 类型系统的完整规范：分类、内部表示、构造、继承、真值判定、运算符重载协议。

---

## 1. 类型分类总览

Tanex Script 类型仅三大类：

| 大类 | 成员 | 关键特征 |
|------|------|----------|
| **原类型** | `integer` | 无包裹、无成员、运行时直接以整数形式存在、无需导入 |
| **基类型** | `type_type` | 所有类型的模板、自身继承自身、解释器内部提供 |
| **复合类型** | 7 种内置 + 用户自定义 | 有成员、支持继承、可注册特殊成员重载运算符、实例含类型指针与成员字典 |

### 类型层级图

```
type_type (基类型，元类型)
  └─ integer (原类型，特殊：非复合类型)
  └─ number
  └─ string
  └─ boolean
  └─ none_type
  └─ nan_type
  └─ infinite_type
  └─ list
  └─ code
  └─ address
  └─ error
  └─ warning
  └─ library
  └─ function_name
  └─ type_name
  └─ 用户自定义类型 (继承 type_type 或其子类型)
```

- 所有复合类型**直接或间接继承** `type_type`
- `type_type` 的 `inherit` 指向自身，形成闭环
- 用户自定义类型通过 `type_type{}` 创建，再设置 `inherit` 指定父类型

---

## 2. 原类型 `Integer`

> **标识符**：`integer` (类型对象)，`Integer` (类型名)
> **分类**：原类型

### 2.1 特性

| 项目 | 说明 |
|------|------|
| 取值范围 | 理论无上限(受限内存)，最小值 `0` |
| 字面量 | 十进制数字，支持 `_` 分隔：`` `1_000_000` `` |
| 负数表示 | 一元 `-` 运算符：`-` `42` |
| 运行时表示 | **非对象**，不分配存储单元，不经过地址空间，解释器内部以 Python `int` 直接运算 |
| 溢出行为 | **无溢出**，任意精度算术 |
| 真值判定 | 非零为真，零为假 |
| 成员访问 | **不支持**，报错“类型不支持成员访问” |

### 2.2 与 `Number` 混合运算

```tanex script
`10` + '0.5';    # => '10.5' (Integer 自动提升为 Number) #;
`10` / `3`;      # => '3.3333333333' (Number) #;
```

### 2.3 除零行为

| 运算 | 结果 |
|------|------|
| `/` | `infinite` (符号随被除数)，`0/0` → `nan` |
| `\` | **报错**“整除除数不能为零” |
| `%` | **报错**“取余除数不能为零” |

### 2.4 位运算

标准库 `bit` 模块提供：`bit_and`/`bit_or`/`bit_xor`/`bit_not`/`bit_left_shift`/`bit_right_shift`，按二进制位操作(将整数视为无符号二进制串)。

---

## 3. 基类型 `Type_Type`

> **标识符**：`type_type`
> **分类**：基类型(元类型)

### 3.1 定义

`type_type` 是所有类型的模板，**自身继承自身**，由解释器内部提供，用户代码**不可直接实例化**(仅通过 `type_type{}` 创建新类型对象)。

### 3.2 类型对象结构

`type_type` 的实例(即**类型对象**)包含以下核心字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `initialize` | `Function` / `None` | 构造器。`Type{...}` 调用。缺失则该类型不可带参构造(空参 `Type{}` 仍可创建空实例) |
| `inherit` | `Type` | 继承目标类型对象。成员查找沿此链向上。`type_type` 自身 `inherit` 指向自己 |
| `addable` | `Boolean` | 可新增标记。`true`/缺失=允许外部新增成员；`false`=封闭类型 |
| `external_read_only` | `Dict<MemberName, Boolean>` | 外部只读标记。标记成员仅类型内部可写，外部赋值报错 |
| `public` | `List<String>` | 文件级导出控制。未声明时默认全公开 |
| `special_members` | `Dict` | 特殊成员槽位(见下) |

### 3.3 特殊成员槽位完备表

| 类别 | 槽位名 | 触发运算符/语义 | 签名 | 返回期望 |
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

### 3.4 比较兜底调用规则

当运算符对应的特殊成员未定义时，解释器按以下顺序**自动组合**：

| 运算符 | 直接特殊成员 | 组合兜底(优先) | `compare` 兜底 | 对象同一性兜底 |
|--------|--------------|----------------|----------------|----------------|
| `>` | `greater` | `!(less \|\| equal)` | `compare > 0` | `false` |
| `<` | `less` | `!(greater \|\| equal)` | `compare < 0` | `false` |
| `>=` | `greater_equal` | `!less` | `compare >= 0` | 同一对象 |
| `<=` | `less_equal` | `!greater` | `compare <= 0` | 同一对象 |
| `==` | `equal` | `!not_equal` | `compare == 0` | 同一对象 |
| `!=` | `not_equal` | `!equal` | `compare != 0` | 非同一对象 |

- **机制**：被兜底调用的方法通过调用参数标记知晓“兜底场景”，避免无限递归
- **最小实现**：类型仅定义 `less` 与 `equal`(或仅 `compare`)，即可获得全部六个比较运算符
- **`type_type` 自身**：不内置 `equal`，无默认比较行为，比较退化到对象同一性

### 3.5 继承复制规则

执行 `Child.inherit = Parent` 时：
1. 设置 `Child.inherit = Parent`
2. **全量复制** `Parent` 的成员字典到 `Child` (浅拷贝地址引用)
3. **跳过三字段**：`addable`、`external_read_only`、`inherit` **不复制** (子类型需显式声明)

### 3.6 成员查找顺序

```
实例成员 → 类型成员 → inherit 父类型成员 → 祖先类型成员 → ... → type_type
```

- 实例成员**优先于**类型成员(实例可覆盖类型默认值)
- 继承链查找在类型成员未命中时触发

---

## 4. 复合类型详解

### 4.1 `Number` — 精确十进制数

> **标识符**：`number`  
> **一句话描述**：精确十进制数，内部 `front`(整数部分 `Integer`) + `back`(小数部分 `Integer`) + 隐含 `scale`(小数位数)，无浮点误差。

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
| 字面量 | `'3.14'`、`'-2.5'`、`'0'`、`'100'` | 单引号包裹，必须有小数点 |
| 单参构造 | `Number{`42`}` | 整数部分=42，小数部分=0 |
| 双参快捷构造 | `Number{`3`, `14`}` | 直接指定 `front`、`back` (算术内部用) |
| 从 Number 拷贝 | `Number{'3.14'}` | 解构现有 Number 的 front/back |

#### 已注册特殊成员(引导库)

| 槽位 | 行为 |
|------|------|
| `initialize` | 单参：尝试取参数 `front` 成员，失败则视参数为整数部分；双参：直接赋 front/back |
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

### 4.2 `String` — Unicode 字符串

> **标识符**：`string`  
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

---

### 4.3 `Boolean` — 布尔类型

> **标识符**：`boolean`  
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

### 4.4 `NoneType` / `none` — 空类型与单例

> **标识符**：`none_type`、`none`  
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

### 4.5 `NaNType` / `nan`、`InfiniteType` / `infinite`、`-infinite`

> **标识符**：`nan_type`/`nan`、`infinite_type`/`infinite`/`infinite`  
> **一句话描述**：特殊数值标记。

#### 特殊成员行为

| 类型 | `boolean` | `string` | 算术运算 |
|------|-----------|----------|----------|
| `nan` | `false` | `"nan"` | 任意运算 → `nan` |
| `infinite` | `true` | `"infinite"` | 与有限数运算 → `infinite`；`infinite - infinite` → `nan` |
| `-infinite` | `true` | `"-infinite"` | 同理 |

---

### 4.6 `List` — 单向链表容器

> **标识符**：`list`  
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

### 4.7 `Code` — 代码块类型

> **标识符**：`code`  
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

### 4.8 `Address` — 地址值

> **标识符**：`address`  
> **一句话描述**：地址值，内部保存地址空间中的整数地址。

#### 操作

| 操作 | 语法 | 结果 |
|------|------|------|
| 取地址 | `/x` | `Address` 值 |
| 解地址读取 | `*addr` | 读取该地址存储单元的值 |
| 解地址赋值 | `*addr = val` | 写入该地址存储单元 |

---

### 4.9 `Error` / `Warning` — 错误与警告

> **标识符**：`error`、`warning`  
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

### 4.10 `Library` — 模块句柄

> **标识符**：`library`  
> **一句话描述**：`import` 返回的模块句柄，内容通过成员访问，注解空间隔离。

#### 特性
- `import` 绑定的标识符为**常量**(不可重新赋值)
- 库内容**不展开**到全局作用域
- 库注解独立：`?? lib.member` 访问，**不**污染顶层 `?? member`

---

### 4.11 `Function_Name` / `Type_Name` — 函数名与类型名类型

> **标识符**：`function_name`、`type_name`  
> **一句话描述**：定义后的函数/类型标识符类型，作为值可传递、赋值、动态调用。

---

## 5. 类型构造与初始化

### 5.1 构造语法

| 形式 | 语法 | 适用场景 |
|------|------|----------|
| **大括号构造** | `Type{arg1, arg2, ...}` | 标准构造，调用 `initialize` |
| **函数调用构造** | `Type(arg1, arg2, ...)` | 等价大括号构造(类型对象可调用) |
| **双参快捷构造** | `Number{front, back}` | 仅 `Number`，供算术内部使用 |
| **空参构造** | `Type{}` | 创建空实例(不调用 `initialize`) |

### 5.2 机制详解

1. 求值类型表达式得类型对象 `T`
2. 创建 `T` 的新实例 `inst`(类型指针指向 `T`，成员字典空)
3. 求值构造参数列表
4. 若 `T` 有 `initialize` 特殊成员：
   - 调用 `initialize(inst, args...)`(`self` 绑定到新实例地址)
   - `initialize` 可在 `self` 上设置成员、执行逻辑
5. 若无 `initialize`：
   - 空参 `Type{}`：正常返回空实例
   - 带参 `Type{...}`：报错“类型没有定义 init 构造器，不能传参构造”

### 5.3 特殊情况

| 类型 | 构造行为 |
|------|----------|
| `type_type{}` | 创建**新裸类型对象**(非实例)，用于定义用户类型 |
| `number{front, back}` | 双参快捷构造，直接组装 `front`/`back`，不调用 `initialize` |
| `none_type{...}` | 任意参数均返回共享单例 `none` |
| 用户类型无 `initialize` | `MyType{}` ✅ 返回空实例；`MyType{arg}` ❌ 报错 |

---

## 6. 真值判定规则(权威)

| 值类型 | 真值判定结果 |
|--------|--------------|
| `Integer` (原类型) | 非零为真，零为假 |
| 实例 (复合类型) | 若类型有 `boolean` 特殊成员 → 调用得结果按真值；否则 **默认真** |
| 类型对象 (`type_type` 实例) | **默认真** |
| `Code`、`Address`、`Library`、`Function_Name`、`Type_Name` | **默认真** |
| `None` (`none`) | **恒假**(`none_type.boolean` 恒返回假) |
| `NaN` (`nan`) | **恒假** |
| `Infinite` (`infinite`/`-infinite`) | **恒真** |

---

## 7. 运算符重载协议

### 7.1 注册方式

```tanex script
*** Type.special_member = [* self, * other] => { ... };
```

- 左操作数类型决定调用哪个类型的特殊成员(`a + b` 查 `type(a).addition`)
- 一元运算符查操作数类型(`-a` 查 `type(a).negative`)
- `<<` 输出查**右**操作数类型 `string`
- `a[b]` 下标查**左**操作数类型 `index`
- `a in b` 优先查**右**操作数类型 `include`，兜底查左类型 `index`

### 7.2 特殊成员签名约定

| 特殊成员 | 签名 | 返回值期望 |
|----------|------|------------|
| `addition` 等 7 算术 | `(self, other)` | 运算结果(任意类型) |
| `positive`/`negative` | `(self)` | 运算结果 |
| `boolean` | `(self)` | `Integer`/`Boolean` (按真值解释) |
| `string` | `(self)` | `String` (字符码链表) |
| `index` | `(self, key)` | 值 / `Address` / 带 `value` 成员的实例 |
| `include` | `(container, element)` | `Boolean`/`Integer` (按真值) |
| `greater`/`less`/... 6 比较 | `(self, other)` | `Boolean` |
| `compare` | `(self, other)` | `Integer`/`Number` (负/零/正) |
| `initialize` | `(self, args...)` | 无要求(通常无返回或返回 self) |

### 7.3 完整映射表

| 运算符 | 查找特殊成员 | 备注 |
|--------|--------------|------|
| `+` | `addition` | |
| `-` | `subtract` | |
| `*` | `multiply` | |
| `/` | `divide` | |
| `\` | `exactly_divisible` | 整除 |
| `%` | `modulo` | |
| `^` | `power` | |
| `>` | `greater` | 兜底组合 |
| `<` | `less` | 兜底组合 |
| `>=` | `greater_equal` | 兜底 `!less` |
| `<=` | `less_equal` | 兜底 `!greater` |
| `==` | `equal` | 兜底 `!not_equal` |
| `!=` | `not_equal` | 兜底 `!equal` |
| `+` (一元) | `positive` | 缺失时内置数值类型保持行为，其他报错 |
| `-` (一元) | `negative` | 同上 |
| `<<` | `string` (右操作数) | 必须返回字符码链表 |
| `a[b]` | `index` (左操作数) | 返回值/地址/`value`成员实例 |
| `a in b` | `include` (右操作数) → 兜底 `index` (左操作数) | 优先 `include` |

---

## 8. 行为控制标记

### 8.1 `addable` — 类型可新增标记

| 值 | 效果 |
|----|------|
| 未声明 / `true` | 允许外部在该类型上新增成员(`Type.new_member = ...`) |
| `false` | **封闭类型**，外部新增成员报错“类型不可新增成员” |

**机制**：向类型新增成员时(成员名在该类型上不存在)，运行时检查 `addable`。实例新增成员不受影响。

### 8.2 `external_read_only` — 成员外部只读标记

| 用法 | 效果 |
|------|------|
| `*** Type.external_read_only = {"field": true};` | `field` 仅类型内部代码可写，外部赋值报错“成员外部只读” |

- 该标记为成员名→布尔映射
- 继承时**不复制**(子类型需显式声明)

### 8.3 `public` — 文件导出控制

| 声明 | 效果 |
|------|------|
| `*** public = ["func1", "Type1"];` | 仅列出的标识符可被外部 `import` 访问 |
| 未声明 | 默认所有顶层标识符公开 |

- 仅在**文件级**有效(模块文件顶层声明)
- 库文件夹 `main.tsuc` 中的 `public` 控制整个库的导出面

---

## 相关链接

- [内置对象参考](../builtins/) — 核心类型/常量/函数/特殊成员完整规范
- [语言参考：表达式](expressions.md) — 运算符优先级、求值顺序
- [语言参考：运算符重载](operator_overloading.md) — 特殊成员详细语义
- [标准库：standard](../library/standard.md) — 基于内置类型的封装函数
- [教程：自定义类型](../tutorial/advanced.md#自定义类型与运算符重载) — 实战示例