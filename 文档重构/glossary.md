# 术语对照表

> 对标 [Python Glossary](https://docs.python.org/zh-cn/3.16/glossary.html)
>
> Tanex Script 核心术语中英对照，按拼音/字母序排列。

---

## A

| 中文术语 | 英文术语 | 定义 |
|---------|---------|------|
| 地址空间 | Address Space | 运行时存储所有值的大仓库，地址为整数，单调递增分配 |
| 地址值 | Address Value | `address` 类型值，内部保存地址空间中的整数地址，`/` 解地址取值 |
| 注解 | Annotation | 源码中 `@ ident # content #;` 形式的元数据，编译期收集、运行时 `??` 读取 |
| 标注表 | Annotation Table | 解释器维护的注解字典，键为目标标识符，值为内容字符串，支持作用域隔离 |
| 原子表达式 | Atomic Expression | 优先级最高的表达式：字面量、标识符、分组 `()` |

## B

| 中文术语 | 英文术语 | 定义 |
|---------|---------|------|
| 基类型 | Base Type | `type_type`，所有类型的模板，自身继承自身，由解释器内部提供 |
| 代码块 | Code Block | `code` 类型值，包裹语句列表、定义时作用域、参数信息，惰性求值 |
| 编译产物 | Compiled Artifact | `.tscc` 文件，JSON 格式 AST，含 `Tanex Script` 语句列表、`annotations`、`annotation` |
| 编译库 | Compiled Library | `.tscl` 文件，二进制打包多个 `.tscc`，键为相对路径、值为编译内容 |
| 复合类型 | Composite Type | 有成员、非原类型的类型（`number`、`string`、`boolean`、`list`、`code` 等） |
| 连续声明 | Consecutive Declaration | `& N`、`&& N`、`&&& N` 一次声明 N 个连续存储单元，返回 `[start, end]` |
| 控制流函数 | Control Flow Function | `if`/`for`/`while`/`cycle` 等以函数形式实现的控制结构 |
| 短路求值 | Short-circuit Evaluation | `&&`、`||`、`?:`、`|` 尝试结构仅求值必要分支 |

## C

| 中文术语 | 英文术语 | 定义 |
|---------|---------|------|
| 词法作用域 | Lexical Scope | 变量查找沿定义时作用域链向上，支持遮蔽与闭包捕获 |
| 循环符 | Loop Operator | `$$` 二元运算符，左操作数为条件、右为循环体，收集 `$` 值返回列表 |

## D

| 中文术语 | 英文术语 | 定义 |
|---------|---------|------|
| 模块 | Module | 可被 `import`/`->` 引入的单元：`.tsuc`、`.tscc`、文件夹库、`.tscl` |
| 命名引入 | Named Import | `import expr = *name`，将库实例地址引用绑定到指定标识符 |

## E

| 中文术语 | 英文术语 | 定义 |
|---------|---------|------|
| 空类型 | None Type | `none_type`，唯一值 `none`，真值恒假，全局单例 |
| 空值 | Null Value | `none`，`none_type` 的唯一实例 |

## F

| 中文术语 | 英文术语 | 定义 |
|---------|---------|------|
| 管道运算符 | Pipeline Operator | `|>` 首参注入，`n |> f` 等价 `f(n)`，右侧必须为函数引用，左结合 |
| 预编译 | Precompilation | 静态字符串 import 路径解析、依赖收集、`.tsuc`→`.tscc` 编译阶段 |

## G

| 中文术语 | 英文术语 | 定义 |
|---------|---------|------|
| 运行时 | Runtime | 解释器、地址空间、作用域、值模型、模块加载器的总称 |

## H

| 中文术语 | 英文术语 | 定义 |
|---------|---------|------|

## I

| 中文术语 | 英文术语 | 定义 |
|---------|---------|------|

## J

| 中文术语 | 英文术语 | 定义 |
|---------|---------|------|

## K

| 中文术语 | 英文术语 | 定义 |
|---------|---------|------|

## L

| 中文术语 | 英文术语 | 定义 |
|---------|---------|------|

## M

| 中文术语 | 英文术语 | 定义 |
|---------|---------|------|

## N

| 中文术语 | 英文术语 | 定义 |
|---------|---------|------|

## O

| 中文术语 | 英文术语 | 定义 |
|---------|---------|------|

## P

| 中文术语 | 英文术语 | 定义 |
|---------|---------|------|

## Q

| 中文术语 | 英文术语 | 定义 |
|---------|---------|------|

## R

| 中文术语 | 英文术语 | 定义 |
|---------|---------|------|

## S

| 中文术语 | 英文术语 | 定义 |
|---------|---------|------|
| 特殊成员 | Special Member | 类型上具有运行时语义的成员（`initialize`、`boolean`、`string`、`index`、`include`、7算术、2一元、6比较、`compare`、`addable`、`external_read_only`、`inherit`、`public`） |
| 特殊变量 | Special Variable | 同“特殊成员”，旧称 |
| 三目运算符 | Ternary Operator | `cond ? true_expr : false_expr` |
| 尝试结构 | Try Expression | `left | *err : catch : else` 错误捕获结构，唯一能拦截报错的语法 |
| 类型对象 | Type Object | `type_type` 的实例，记录 `initialize`、`inherit`、特殊成员槽位、成员字典 |
| 类型构造 | Type Construction | `Type{...}` 或 `Type(...)` 创建实例，调用 `initialize` |
| 无符号整数 | Unsigned Integer | 原类型 `integer` 仅表示非负整数，负数由 `-` 一元运算符表示 |
| 引用声明 | Reference Declaration | `** name` 声明引用变量，赋值必须为标识符，此后与目标共享存储单元 |
| 运算符重载 | Operator Overloading | 通过在类型上注册特殊成员（`addition`、`greater` 等）自定义运算符行为 |
| 真值判定 | Truthiness Test | 条件上下文中值的真假：`integer` 非零为真、实例调用 `boolean` 特殊成员、其余默认真 |
| 表达式符号 | Expression Symbol | `import`/`->` Pratt 前缀运算符，操作数为任意表达式，运行时求值加载 |
| 遮蔽 | Shadowing | 内层作用域声明同名变量覆盖外层，查找优先内层 |
| 作用域 | Scope | 变量名→地址的映射表，支持嵌套与父链查找 |
| 赋值目标解析 | Assignment Target Resolution | 根据左侧 AST（名字/成员/下标/声明符）解析出写入地址 |
| 字面量 | Literal | 源码中直接表示的固定值（整数、数字、字符串、布尔、none、nan、infinite） |
| 自举库 | Bootstrap Library | `bootstrap.tsuc` 编译为 `bootstrap.tscc`，运行时最先加载，填充核心类型血肉 |
| 标准库 | Standard Library | `standard_src/` 下的 `.tsuc` 源码，编译后随解释器分发，用户通过 `import "standard"` 引入 |
| 标准输出 | Standard Output | `standard_output` 全局常量，作为 `<<` 左操作数的处理函数，透传字符码链表 |
| 标准输入 | Standard Input | `standard_input` 全局常量，作为 `>>` 左操作数的处理函数，处理输入字符串 |
| 数字类型 | Number Type | `number`，内部 `front`(整数部分) + `back`(小数部分) 精确十进制表示 |
| 字符串类型 | String Type | `string`，底层链表存储 Unicode 码点，支持追加、索引、转换 |
| 列表类型 | List Type | `list`，单向链表、头尾指针、O(1) 追加、O(n) 索引 |
| 布尔类型 | Boolean Type | `boolean`，存储 0/1，算术运算返回 `integer`，真值直接取存储值 |
| 错误类型 | Error Type | `error`，捕获错误后的值，成员 `what`、方法 `throw()` |
| 警告类型 | Warning Type | `warning`，类似 `error` 但 `throw()` 不结束程序 |
| 库类型 | Library Type | `library`，import 返回的模块句柄，内容通过成员访问，注解空间隔离 |
| 函数名类型 | Function Name Type | `function_name`，定义后的函数标识符类型 |
| 类型名类型 | Type Name Type | `type_name`，定义后的类型标识符类型 |
| 索引特殊成员 | Index Special Member | `index`，支持 `a[b]` 下标访问与 `in` 兜底遍历 |
| 包含特殊成员 | Include Special Member | `include`，`in` 运算符优先判定，`include(container, element)` |
| 布尔特殊成员 | Boolean Special Member | `boolean`，真值判定回调，返回值按真值规则解释 |
| 字符串特殊成员 | String Special Member | `string`，`<<` 输出与字符串转换回调，返回字符码链表 |
| 构造器 | Initializer | `initialize` 特殊成员，类型构造时调用，接收参数列表 |
| 继承 | Inheritance | `inherit` 特殊成员指向父类型，成员全量复制（三字段除外） |
| 三路比较 | Three-way Comparison | `compare` 特殊成员，返回负/零/正表示小于/等于/大于 |
| 对象同一性兜底 | Object Identity Fallback | 无任何比较机制时退化为：`==`/`!=`/`<=`/`>=` 比对象地址，`<`/`>` 恒假 |
| 兜底调用 | Fallback Dispatch | 比较特殊成员缺失时解释器自动组合其他特殊成员结果（如 `>=` 兜底 `!less`） |
| 正/负特殊成员 | Positive/Negative Special Member | `positive`/`negative`，一元 `+n`/`-n` 在用户类型上的重载 |
| 可新增标记 | Addable Flag | `addable` 布尔标记，控制类型是否允许外部新增成员 |
| 外部只读标记 | External Read-only Flag | `external_read_only` 标记成员仅内部可写、外部只读 |
| 公开列表 | Public List | `public` 文件级特殊变量，列出允许外部引用的标识符 |
| 零元运算符 | Nullary Operator | 无操作数、独立成句：`break`、`contiune` |
| 多层跳出 | Multi-level Return | 二元 `$`，`n $ m` 向上跳出 n 层返回 m，`1 $ m` 等价 `return m` |
| 返回运算符 | Return Operator | 一元 `$`/`return`，携带值提前结束代码块/函数 |
| 抛出运算符 | Throw Operator | 一元 `<-`，携带错误值，被 `|` 尝试结构捕获 |
| 注解读取 | Annotation Read | 一元 `??`，按作用域读取注解内容，支持 `?? lib.member` 跨库读取 |
| 类型查询 | Type Query | 一元 `type_of`，返回值的类型对象 |
| 上级访问 | Parent Scope Access | 一元 `~`，在父作用域中求值操作数 |
| 解地址 | Dereference | 一元 `*`，地址值→存储单元值；也用作简单声明符 `* name` |
| 取地址 | Address-of | 一元 `/`，变量/表达式→地址值 |
| 引用声明符 | Reference Declaration Sigil | `**`，声明引用变量或作为一元运算符声明引用空间 |
| 常量声明符 | Const Declaration Sigil | `***`，声明常量变量/常量成员/注册特殊成员 |
| 连续声明符 | Consecutive Declaration Sigil | `&`/`&&`/`&&&`，一元位置声明 N 个连续空间 |
| 复合赋值 | Compound Assignment | `+=` `-=` `*=` `/=` `\=` `%=` `^=` `&=` `|=` |
| 列表尾部逗号 | Trailing Comma | `[a,]` 自动填充 `none`，`(a,,b)` 中间空位填充 `none` |
| 代码块参数 | Code Block Parameter | `if`/`for` 等控制流函数接收的 `code` 类型实参 |
| 闭包 | Closure | 代码块捕获定义时作用域，调用时建立子作用域，可读写外部变量 |
| 参数传地址 | Call by Address | 函数调用时参数存入地址空间、传递地址而非值，函数内赋值影响调用方 |
| 缺省参数 | Default Parameter | 参数不足时按默认值求值补齐、无默认值补 `none` |
| 成员查找顺序 | Member Lookup Order | 实例成员 → 类型成员 → 继承链向上 |
| 实例成员优先 | Instance Member Priority | 实例可覆盖类型上定义的同名成员 |
| 继承复制规则 | Inheritance Copy Rule | 父类型成员全量复制到子类型，`addable`/`external_read_only`/`inherit` 跳过 |
| 动态加载 | Dynamic Load | import 操作数为非字面量表达式时，运行时求值路径再加载 |
| 静态解析 | Static Resolution | import 操作数为字符串字面量时，预编译阶段解析绝对路径 |
| 歧义消除 | Ambiguity Resolution | 同名可引用内容多个时报错，建议加后缀（`/`、`.tsuc`、`.tscc`、`.tscl`） |
| 标准库优先 | Standard Library Priority | 裸名 `"standard"` 优先解析为安装目录标准库，本地同名需绝对路径 |
| 编译期注解 | Compile-time Annotation | 源码 `@` 注解，编译期收集进 `annotations`，不参与运行时求值 |
| 运行时注解 | Runtime Annotation | 通过 `??` 读取的注解内容，按需构建字符串返回 |

## T

| 中文术语 | 英文术语 | 定义 |
|---------|---------|------|

## U

| 中文术语 | 英文术语 | 定义 |
|---------|---------|------|

## V

| 中文术语 | 英文术语 | 定义 |
|---------|---------|------|

## W

| 中文术语 | 英文术语 | 定义 |
|---------|---------|------|

## X

| 中文术语 | 英文术语 | 定义 |
|---------|---------|------|

## Y

| 中文术语 | 英文术语 | 定义 |
|---------|---------|------|

## Z

| 中文术语 | 英文术语 | 定义 |
|---------|---------|------|

---

## 符号与运算符

| 符号 | 名称 | 类型 |
|------|------|------|
| `;` | 分号/语句终结符 | 结构 |
| `,` | 逗号/分隔符 | 结构 |
| `(` `)` | 括号/分组/调用 | 结构 |
| `[` `]` | 方括号/下标/列表 | 结构 |
| `{` `}` | 花括号/代码块/实例创建 | 结构 |
| `#` `#` | 注释 | 结构 |
| `@` `#` `#;` | 注解 | 结构 |
| `+` `-` `*` `/` `\` `%` `^` | 算术运算符 | 二元 |
| `<<` `>>` | 输出/输入 | 二元 |
| `$$` | 循环符 | 二元 |
| `|>` | 管道 | 二元 |
| `<` `<=` `>` `>=` `==` `!=` | 比较 | 二元 |
| `&&` `||` | 逻辑与/或 | 二元 |
| `in` | 存在判断 | 二元 |
| `=` `+=` `-=` `*=` `/=` `\=` `%=` `^=` `&=` `|=` | 赋值/复合赋值 | 二元 |
| `$` | 返回/多层跳出 | 一元/二元 |
| `return` | 返回 | 一元 |
| `<-` | 抛出错误 | 一元 |
| `??` | 注解读取 | 一元 |
| `type_of` | 类型查询 | 一元 |
| `~` | 上级访问 | 一元 |
| `*` | 解地址/声明符 | 一元 |
| `/` | 取地址 | 一元 |
| `**` `***` | 引用/常量声明符 | 一元 |
| `&` `&&` `&&&` | 连续声明符 | 一元 |
| `? :` | 三目运算符 | 三目 |
| `\| : :` | 尝试结构 | 三元 |
| `break` `contiune` | 零元运算符 | 零元 |
| `import` `->` | 表达式符号 | 前缀 |

---

## 文件后缀

| 后缀 | 全称 | 说明 |
|------|------|------|
| `.tsuc` | Tanex Script Uncompiled Code | 源码文件 |
| `.tscc` | Tanex Script Compiled Code | 编译产物 (JSON AST) |
| `.tscl` | Tanex Script Compiled Library | 编译库 (二进制打包) |

---

## 相关链接

- [语言参考：词法](../reference/lexical.md) — 完整词法规范
- [语言参考：类型系统](../reference/types.md) — 类型详细规范
- [语言参考：运算符重载](../reference/operator_overloading.md) — 特殊成员完整映射
- [FAQ：语法与语义](../faq/syntax.md) — 语法常见问题
- [专题指南：类型设计](../howto/type_design.md) — 自定义类型实战