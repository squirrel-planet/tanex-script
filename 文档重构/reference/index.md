# 语言参考

> 对标 [Python Language Reference](https://docs.python.org/zh-cn/3.16/reference/)
>
> Tanex Script 语言的完整语法与语义规范。语法已冻结，本文档为唯一权威规范来源。

---

## 章节导航

| 章节 | 说明 | 对应 Python 参考 |
|------|------|------------------|
| [lexical.md](lexical.md) | 词法分析 | [Lexical Analysis](https://docs.python.org/zh-cn/3.16/reference/lexical_analysis.html) |
| [types.md](types.md) | 类型系统 | [Data Model](https://docs.python.org/zh-cn/3.16/reference/datamodel.html) |
| [expressions.md](expressions.md) | 表达式 | [Expressions](https://docs.python.org/zh-cn/3.16/reference/expressions.html) |
| [statements.md](statements.md) | 语句 | [Simple Statements](https://docs.python.org/zh-cn/3.16/reference/simple_stmts.html) |
| [functions.md](functions.md) | 函数与过程 | [Function Definitions](https://docs.python.org/zh-cn/3.16/reference/compound_stmts.html#function-definitions) |
| [modules.md](modules.md) | 模块系统 | [Modules](https://docs.python.org/zh-cn/3.16/reference/import.html) |
| [errors.md](errors.md) | 错误处理 | [Exceptions](https://docs.python.org/zh-cn/3.16/reference/compound_stmts.html#try-statements) |
| [operator_overloading.md](operator_overloading.md) | 运算符重载 | [Special Method Names](https://docs.python.org/zh-cn/3.16/reference/datamodel.html#special-method-names) |
| [runtime_internals.md](runtime_internals.md) | 运行时内部机制 | [Execution Model](https://docs.python.org/zh-cn/3.16/reference/executionmodel.html) |

---

## 核心设计原则

1. **语法统一化**：所有控制结构（`if`/`for`/`while`/`cycle`、错误处理）均为函数调用，无特殊关键字语法
2. **代码块一等公民**：`{...}` 产生 `code` 类型值，可赋值、传参、存储、动态构造
3. **运算符重载协议**：通过类型特殊成员（28 个槽位）自定义 30+ 运算符行为
4. **显式地址与引用语义**：`/` 取地址、`*` 解地址、`**` 引用声明、`***` 常量声明
5. **精确十进制数值**：`Number` 类型内部 `front/back` 表示，无浮点误差
6. **编译时/运行时分离**：`.tsuc` → `.tscc` (JSON AST) → 解释器执行，启动极快

---

## 词法约定速查

| 项目 | 规范 |
|------|------|
| 编码 | UTF-8 无 BOM |
| 行终止符 | LF/CR/CRLF 均视为空白，**不终结语句** |
| 语句终结 | 分号 `;`，**无续行符** |
| 标识符 | Unicode XID_Start/Continue，**禁止数字** |
| 关键字别名 | `and`→`&&`、`or`→`||`、`not`→`!`、`is`→`==` (词法阶段自动替换) |
| 字面量 | `` `123` `` (Integer)、`'3.14'` (Number)、`"hello"` (String)、`true`/`false`、`none`、`nan`、`infinite` |
| 注释 | `#...#` (不嵌套) |
| 注解 | `@ ident # content #;` (编译期收集、运行时 `??` 读取) |

---

## 运算符优先级总表 (高→低)

| 级 | 运算符 | 结合 | 类型 | 说明 |
|----|--------|------|------|------|
| 1 | 字面量 标识符 `()` | — | 原子 | 最高 |
| 2 | `[]` `()` | 左 | 后缀 | 下标、调用 |
| 3 | `.` | 左 | 后缀 | 成员访问 |
| 4 | `|>` | 左 | 二元 | 管道首参注入 |
| 5 | `!` `~` `*` `/` `**` `***` `&` `&&` `&&&` `<-` `return` `??` `type_of` | 右 | 前缀 | 一元/声明/控制/注解 |
| 6 | `+` `-` | 右 | 前缀 | 一元正负 |
| 7 | `*n` `/n` | 右 | 前缀 | 解/取地址 |
| 8 | `*` `/` `\` `%` `^` `<<` `>>` `$$` | 左 | 二元 | 算术/输出/输入/循环 |
| 9 | `+` `-` | 左 | 二元 | 加减/拼接 |
| 10 | `<` `<=` `>` `>=` `in` | 左 | 二元 | 比较/存在 |
| 11 | `==` `!=` `?:` `\| : :` | 右 | 二元/三目/三元 | 相等/三目/尝试 |
| 12 | `&&` | 左 | 二元 | 逻辑与(短路) |
| 13 | `||` | 左 | 二元 | 逻辑或(短路) |
| 14 | `=>` | 右 | 二元 | 匿名函数 |
| 15 | `=` | 右 | 二元 | 赋值 |
| 16 | `+=` `-=` `*=` `/=` `\=` `%=` `^=` `&=` `|=` | 右 | 二元 | 复合赋值 |
| 17 | `$` | 右 | 二元 | 多层跳出 |
| — | `break` `contiune` | — | 零元 | 独立语句 |
| — | `import` `->` | 右 | 前缀 | 表达式符号(Pratt) |

---

## 类型分类速查

| 大类 | 类型 | 关键特征 |
|------|------|----------|
| **原类型** | `integer` | 无包裹、无成员、任意精度、直接以整数形式运算 |
| **基类型** | `type_type` | 元类型、自身继承自身、所有类型为其实例 |
| **复合类型** | `number` | 精确十进制、`front/back` 表示 |
| | `string` | 底层链表存储 Unicode 码点 |
| | `boolean` | 存储 0/1，算术返回 `Integer` |
| | `none_type` | 单例 `none`，真值恒假 |
| | `nan_type` / `infinite_type` | 特殊数值标记 |
| | `list` | 单向链表、O(1)追加、O(n)索引 |
| | `code` | 惰性求值、捕获定义时作用域 |
| | `address` | 地址值、解地址取值 |
| | `error` / `warning` | 错误对象、`what`+`throw()` |
| | `library` | 模块句柄、注解空间隔离 |
| | `function_name` / `type_name` | 定义后的标识符类型 |

---

## 相关链接

- [教程：快速上手](../tutorial/intro.md) — 从零开始
- [内置对象参考](../builtins/) — 核心类型/常量/函数/特殊成员完整规范
- [标准库参考](../library/) — 8 个模块逐条目规范
- [专题指南](../howto/) — 类型设计、错误处理、性能优化
- [扩展与嵌入](../extending/) — Python API：解释器嵌入、编译器、值模型
- [版本更新记录](../whatsnew/) — 1.0.0 基线、后续增量
- [术语对照表](../glossary.md) — 120+ 术语中英对照