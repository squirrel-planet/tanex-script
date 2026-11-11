# 全局索引

> 对标 [Python Global Module Index](https://docs.python.org/zh-cn/3.16/py-modindex.html)
>
> Tanex Script 所有函数、类型、术语、运算符的字母序检索表。

---

## 符号与运算符

| 条目 | 类型 | 所在章节 |
|------|------|----------|
| `;` | 语句终结符 | [语句](../reference/statements.md) |
| `,` | 参数/列表分隔符 | [表达式](../reference/expressions.md) |
| `(` `)` | 分组/函数调用 | [表达式](../reference/expressions.md) |
| `[` `]` | 下标/列表字面量 | [表达式](../reference/expressions.md#下标访问-)、[列表类型](../reference/types.md#46-list--单向链表容器) |
| `{` `}` | 代码块/实例创建 | [表达式](../reference/expressions.md#代码块字面量-)、[实例创建](../reference/expressions.md#实例创建-) |
| `#` `#` | 注释 | [词法：注释](../reference/lexical.md#注释) |
| `@` `#` `#;` | 注解 | [词法：注解](../reference/lexical.md#注解) |
| `+` | 加法/拼接 | [运算符重载](../reference/operator_overloading.md) |
| `-` | 减法/一元负号 | [运算符重载](../reference/operator_overloading.md) |
| `*` | 乘法/重复/解地址/声明符 | [运算符重载](../reference/operator_overloading.md) |
| `/` | 除法/取地址 | [运算符重载](../reference/operator_overloading.md) |
| `\` | 整除 | [运算符重载](../reference/operator_overloading.md) |
| `%` | 取余 | [运算符重载](../reference/operator_overloading.md) |
| `^` | 幂运算 | [运算符重载](../reference/operator_overloading.md) |
| `<<` | 输出 | [表达式](../reference/expressions.md#输出输入-<<-) |
| `>>` | 输入 | [表达式](../reference/expressions.md#输出输入-<<-) |
| `$$` | 循环符 | [表达式](../reference/expressions.md#循环符-$$) |
| `|>` | 管道 | [表达式](../reference/expressions.md#管道-|>) |
| `<` `<=` `>` `>=` | 比较 | [运算符重载](../reference/operator_overloading.md) |
| `==` `!=` | 相等/不等 | [运算符重载](../reference/operator_overloading.md) |
| `&&` `||` | 逻辑与/或 | [表达式](../reference/expressions.md#逻辑与或-&&-||-短路) |
| `in` | 存在判断 | [表达式](../reference/expressions.md#存在判断-in) |
| `=` `+=` `-=` `*=` `/=` `\=` `%=` `^=` `&=` `|=` | 赋值/复合赋值 | [语句](../reference/statements.md#5-赋值语句) |
| `$` | 返回/多层跳出 | [表达式](../reference/expressions.md#一元返回)、[表达式](../reference/expressions.md#多层跳出-二元) |
| `return` | 返回 | [表达式](../reference/expressions.md#一元返回) |
| `<-` | 抛出错误 | [表达式](../reference/expressions.md#一元抛出错误) |
| `??` | 注解读取 | [表达式](../reference/expressions.md#一元注解读取) |
| `type_of` | 类型查询 | [表达式](../reference/expressions.md#一元类型查询) |
| `~` | 上级访问 | [表达式](../reference/expressions.md#一元上级访问) |
| `*` | 解地址/声明符 | [表达式](../reference/expressions.md#一元解地址) |
| `/` | 取地址 | [表达式](../reference/expressions.md#一元取地址) |
| `**` `***` | 引用/常量声明符 | [表达式](../reference/expressions.md#一元引用声明) |
| `&` `&&` `&&&` | 连续声明符 | [表达式](../reference/expressions.md#一元连续声明) |
| `? :` | 三目运算符 | [表达式](../reference/expressions.md#三目运算符-cond--t--f) |
| `\| : :` | 尝试结构 | [表达式](../reference/expressions.md#尝试结构-left-err--catch--else) |
| `break` `contiune` | 零元运算符 | [语句](../reference/statements.md#7-零元运算符语句) |
| `import` `->` | 表达式符号 | [模块系统](../reference/modules.md) |

---

## A

| 条目 | 类型 | 所在章节 |
|------|------|----------|
| `abs` | 函数 | [standard](../library/standard.md#abs-绝对值)、[maths](../library/maths.md#abs-绝对值) |
| `addition` | 特殊成员 | [运算符重载](../reference/operator_overloading.md) |
| `address` | 类型 | [内置类型](../reference/types.md#48-address--地址值) |
| `Address` | 类型名 | [内置对象](../builtins/index.md#110-address--地址值) |
| `addable` | 特殊成员 | [类型系统](../reference/types.md#81-addable--类型可新增标记) |
| `alias` | 关键字别名 | [词法：关键字别名](../reference/lexical.md#关键字别名) |
| `and` | 关键字别名 | [词法：关键字别名](../reference/lexical.md#关键字别名) |
| `Annotation` | 注解 | [词法：注解](../reference/lexical.md#注解) |
| `Annotation Table` | 标注表 | [注解系统](../extending/annotations.md) |
| `arg_error` | 错误前缀 | [错误处理](../howto/error_handling.md#31-标准错误前缀约定) |
| `ArithError` | 错误类型 | [错误码](../extending/errors.md#33-运行时错误-e2xx) |

## B

| 条目 | 类型 | 所在章节 |
|------|------|----------|
| `Base Type` | 基类型 | [类型系统](../reference/types.md#3-基类型-typetype) |
| `Base64` | 编码 | [encoding.base_sixty_four](../library/encoding_base64.md) |
| `bit_and` `bit_or` `bit_xor` `bit_not` | 函数 | [bit](../library/bit.md) |
| `bit_left_shift` `bit_right_shift` | 函数 | [bit](../library/bit.md) |
| `boolean` | 特殊成员 | [类型系统](../reference/types.md#布尔特殊成员) |
| `Boolean` | 类型 | [内置类型](../reference/types.md#43-boolean--布尔类型) |
| `Bootstrap Library` | 自举库 | [引导库内部](../reference/runtime_internals.md#2-核心类型初始化规范) |
| `break` | 零元运算符 | [语句](../reference/statements.md#7-零元运算符语句) |
| `Builtins` | 内置对象 | [内置对象](../builtins/index.md) |

## C

| 条目 | 类型 | 所在章节 |
|------|------|----------|
| `Call by Address` | 参数传地址 | [函数](../reference/functions.md#21-传地址) |
| `catch` | 尝试结构分支 | [表达式](../reference/expressions.md#尝试结构-left-err--catch--else) |
| `chrono` | 时间模块 | [计划中](../howto/interop.md#4-c-api-计划中) |
| `clamp` | 函数 | [standard](../library/standard.md#clamp-区间限制)、[maths](../library/maths.md#clamp-区间限制) |
| `Closure` | 闭包 | [函数](../reference/functions.md#4-作用域与闭包) |
| `Code Block` | 代码块 | [表达式](../reference/expressions.md#代码块字面量-) |
| `Code` | 类型 | [内置类型](../reference/types.md#47-code--代码块类型) |
| `compare` | 特殊成员 | [运算符重载](../reference/operator_overloading.md) |
| `compile` | 编译器 API | [编译器 API](../extending/compiler_api.md#4-一体化编译) |
| `compile_file` | 编译器 API | [编译器 API](../extending/compiler_api.md#42-compile_filetsuc_path-str-output_tscc_path-str-none-astdict) |
| `Constant` | 常量 | [语句](../reference/statements.md#43-常量声明) |
| `Constant Declaration Sigil` | 常量声明符 | [表达式](../reference/expressions.md#一元常量声明) |
| `contains` | 列表操作 | [standard](../library/standard.md#list_contains) |
| `const_error` | 错误前缀 | [错误处理](../howto/error_handling.md#31-标准错误前缀约定) |
| `Control Flow Function` | 控制流函数 | [语言参考](../reference/runtime_internals.md#24-控制流函数定义) |
| `contiune` | 零元运算符 | [语句](../reference/statements.md#7-零元运算符语句) |
| `Count` | 连续声明数量 | [语句](../reference/statements.md#44-数量声明) |
| `Cycle` | 控制流函数 | [教程](../tutorial/controlflow.md#4-cycle-定次循环) |

## D

| 条目 | 类型 | 所在章节 |
|------|------|----------|
| `Debug` | 调试 | [故障排查](../faq/troubleshooting.md#3-调试技巧) |
| `Declaration` | 声明 | [语句](../reference/statements.md#4-声明语句) |
| `Dereference` | 解地址 | [表达式](../reference/expressions.md#一元解地址) |
| `Dictionary` | 类型 | [标准库](../library/standard.md#类型构造辅助) |
| `digits_of` | 辅助函数 | [引导库](../reference/runtime_internals.md#24-引导库执行填充核心类型) |
| `divide` | 特殊成员 | [运算符重载](../reference/operator_overloading.md) |
| `Dynamic Load` | 动态加载 | [模块系统](../reference/modules.md#动态加载) |

## E

| 条目 | 类型 | 所在章节 |
|------|------|----------|
| `else` | 尝试结构分支 | [表达式](../reference/expressions.md#尝试结构-left-err--catch--else) |
| `Embedding` | 嵌入 | [嵌入指南](../extending/embedding.md) |
| `encoding.ascii` | 模块 | [标准库](../library/encoding_ascii.md) |
| `encoding.base_sixty_four` | 模块 | [标准库](../library/encoding_base64.md) |
| `Environment` | 环境/作用域 | [地址空间与作用域](../extending/environment.md) |
| `Error` | 类型 | [内置类型](../reference/types.md#411-error--错误类型) |
| `ErrorSignal` | 错误信号 | [运行时内部](../reference/runtime_internals.md#3-控制流信号机制) |
| `escape sequence` | 转义序列 | [词法：字符串字面量](../reference/lexical.md#83-字符串字面量-string) |
| `eval` | 核心求值 | [核心执行器](../extending/interpreter.md#1-核心求值入口) |
| `exactly_divisible` | 特殊成员 | [运算符重载](../reference/operator_overloading.md) |
| `Exception` | 异常层级 | [错误与诊断](../extending/errors.md#1-异常类层级) |
| `Expression Symbol` | 表达式符号 | [词法：运算符符号表](../reference/lexical.md#9-运算符符号表) |
| `extending` | 扩展 | [扩展与嵌入](../extending/index.md) |
| `external_read_only` | 特殊成员 | [类型系统](../reference/types.md#82-external_read_only--成员外部只读标记) |

## F

| 条目 | 类型 | 所在章节 |
|------|------|----------|
| `factorial` | 函数 | [maths](../library/maths.md#factorial-阶乘) |
| `Fallback Dispatch` | 兜底调用 | [运算符重载](../reference/operator_overloading.md#3-比较兜底调用规则解释器层实现) |
| `fibonacci` | 函数 | [maths](../library/maths.md#fibonacci-斐波那契数) |
| `For` | 控制流函数 | [教程](../tutorial/controlflow.md#2-for-遍历循环) |
| `forall` | 属性测试 | [测试策略](../howto/testing.md#41-forall-框架) |

## G

| 条目 | 类型 | 所在章节 |
|------|------|----------|
| `genindex` | 全局索引 | [本页] |
| `GCD` | 最大公约数 | [maths](../library/maths.md#gcd-最大公约数) |
| `gen_int` `gen_list` | 测试数据生成 | [测试策略](../howto/testing.md#41-forall-框架) |

## H

| 条目 | 类型 | 所在章节 |
|------|------|----------|
| `HOWTO` | 专题指南 | [专题指南](../howto/index.md) |
| `hash` | 哈希 | [类型设计](../howto/type_design.md#41-高效-in-判定-include) |

## I

| 条目 | 类型 | 所在章节 |
|------|------|----------|
| `If` | 控制流函数 | [教程](../tutorial/controlflow.md#1-if-条件分支) |
| `Import` | 导入 | [模块系统](../reference/modules.md) |
| `import_error` | 错误前缀 | [错误处理](../howto/error_handling.md#31-标准错误前缀约定) |
| `Inheritance` | 继承 | [类型系统](../reference/types.md#6-继承机制) |
| `Initialize` | 构造器 | [类型系统](../reference/types.md#构造器) |
| `Integer` | 原类型 | [内置类型](../reference/types.md#2-原类型-integer) |
| `index` | 特殊成员 | [类型系统](../reference/types.md#索引特殊成员) |
| `index_error` | 错误前缀 | [错误处理](../howto/error_handling.md#31-标准错误前缀约定) |
| `include` | 特殊成员 | [类型系统](../reference/types.md#包含特殊成员) |
| `Interpreter` | 解释器 | [嵌入指南](../extending/embedding.md) |
| `Infinite` | 类型 | [内置类型](../reference/types.md#45-nantype--nan、infinitetype--infinite、-infinite) |
| `Inheritance Copy Rule` | 继承复制规则 | [类型系统](../reference/types.md#6-继承机制) |

## J

| 条目 | 类型 | 所在章节 |
|------|------|----------|
| `JSON` | 模块 | [标准库](../library/json.md) |

## K

| 条目 | 类型 | 所在章节 |
|------|------|----------|
| `Keyword Alias` | 关键字别名 | [词法：关键字别名](../reference/lexical.md#关键字别名) |

## L

| 条目 | 类型 | 所在章节 |
|------|------|----------|
| `Lexical Scope` | 词法作用域 | [语言参考](../reference/lexical.md#作用域与闭包) |
| `Library` | 类型 | [内置类型](../reference/types.md#412-library--模块句柄) |
| `list` | 类型 | [内置类型](../reference/types.md#46-list--单向链表容器) |
| `List` | 类型名 | [内置对象](../builtins/index.md#18-list--单向链表容器) |
| `list_map` `list_filter` `list_reduce` | 函数 | [standard](../library/standard.md#列表操作) |
| `list_append` `list_index` | 方法 | [内置对象](../builtins/index.md#18-list--单向链表容器) |
| `Loop Operator` | 循环符 | [表达式](../reference/expressions.md#循环符-$$) |

## M

| 条目 | 类型 | 所在章节 |
|------|------|----------|
| `Member` | 成员 | [表达式](../reference/expressions.md#成员访问-) |
| `Member Lookup Order` | 成员查找顺序 | [类型系统](../reference/types.md#成员查找顺序) |
| `Method` | 方法 | [内置对象](../builtins/index.md) |
| `metaprogramming` | 元编程 | [专题指南](../howto/metaprogramming.md) |
| `Module` | 模块 | [模块系统](../reference/modules.md) |
| `modindex` | 模块索引 | [模块索引](modindex.md) |
| `Multi-level Return` | 多层跳出 | [表达式](../reference/expressions.md#多层跳出-二元) |

## N

| 条目 | 类型 | 所在章节 |
|------|------|----------|
| `NaN` | 类型 | [内置类型](../reference/types.md#45-nantype--nan、infinitetype--infinite、-infinite) |
| `Named Import` | 命名引入 | [模块系统](../reference/modules.md#32-命名引入仅-import) |
| `Negative` | 特殊成员 | [运算符重载](../reference/operator_overloading.md) |
| `None` | 空值 | [内置类型](../reference/types.md#44-nonetype--none--空类型与单例) |
| `NoneType` | 空类型 | [内置类型](../reference/types.md#44-nonetype--none--空类型与单例) |
| `Nullary Operator` | 零元运算符 | [语句](../reference/statements.md#7-零元运算符语句) |
| `Number` | 数字类型 | [内置类型](../reference/types.md#41-number--精确十进制数) |
| `numeral_system` | 模块 | [标准库](../library/numeral_system.md) |

## O

| 条目 | 类型 | 所在章节 |
|------|------|----------|
| `Object Identity Fallback` | 对象同一性兜底 | [运算符重载](../reference/operator_overloading.md) |
| `Operator Overloading` | 运算符重载 | [运算符重载](../reference/operator_overloading.md) |
| `or` | 关键字别名 | [词法：关键字别名](../reference/lexical.md#关键字别名) |

## P

| 条目 | 类型 | 所在章节 |
|------|------|----------|
| `Parameter` | 参数 | [函数](../reference/functions.md#12-参数列表语法) |
| `parse` | 编译器 API | [编译器 API](../extending/compiler_api.md#31-parsetokens-tokenlist-filename-str-string-astdict) |
| `parse` | JSON 函数 | [标准库](../library/json.md#parse-解析-json-字符串) |
| `Pipeline Operator` | 管道运算符 | [表达式](../reference/expressions.md#管道-|>) |
| `Positive` | 特殊成员 | [运算符重载](../reference/operator_overloading.md) |
| `power` | 特殊成员 | [运算符重载](../reference/operator_overloading.md) |
| `power_integer` | 函数 | [maths](../library/maths.md#power_integer-整数幂) |
| `Precompilation` | 预编译 | [模块系统](../reference/modules.md#41-预编译阶段静态字符串字面量) |
| `print` `println` | 函数 | [standard](../library/standard.md#io-封装) |
| `private` | 约定 | [模块组织](../howto/module_organization.md#2-库设计原则) |
| `Public` | 公开列表 | [模块系统](../reference/modules.md#6-可见性控制public) |
| `public` | 特殊成员 | [类型系统](../reference/types.md#83-public--文件导出控制) |

## Q

| 条目 | 类型 | 所在章节 |
|------|------|----------|
| `quickcheck` | 测试工具 | [测试策略](../howto/testing.md#62-属性测试) |

## R

| 条目 | 类型 | 所在章节 |
|------|------|----------|
| `random` | 模块 | [标准库](../library/random.md) |
| `random_integer` `random_range` | 函数 | [random](../library/random.md#random_integer--生成-0-max-随机整数) |
| `read_line` `read_all` | 函数 | [standard](../library/standard.md#io-封装) |
| `Reference Declaration` | 引用声明 | [语句](../reference/statements.md#42-引用声明语句) |
| `Reference Declaration Sigil` | 引用声明符 | [表达式](../reference/expressions.md#一元引用声明) |
| `register_builtin_function` | 标准库注册 | [标准库注册](../extending/stdlib_registration.md#2-内置函数注册) |
| `register_special_member` | 标准库注册 | [标准库注册](../extending/stdlib_registration.md#3-特殊成员注册) |
| `Return` | 返回 | [表达式](../reference/expressions.md#一元返回) |
| `Return Signal` | 返回信号 | [运行时内部](../reference/runtime_internals.md#3-控制流信号机制) |
| `Runtime` | 运行时 | [运行时内部](../reference/runtime_internals.md) |
| `Runtime Annotation` | 运行时注解 | [注解系统](../extending/annotations.md) |

## S

| 条目 | 类型 | 所在章节 |
|------|------|----------|
| `Scope` | 作用域 | [环境](../extending/environment.md) |
| `Short-circuit Evaluation` | 短路求值 | [表达式](../reference/expressions.md#逻辑与或-&&-||-短路) |
| `sign` | 函数 | [standard](../library/standard.md#sign-符号函数)、[maths](../library/maths.md#sign-符号函数) |
| `Special Member` | 特殊成员 | [类型系统](../reference/types.md#特殊成员槽位完备表) |
| `Special Variable` | 特殊变量 | [特殊成员](../reference/types.md#特殊成员槽位完备表) |
| `Standard Library` | 标准库 | [标准库](../library/index.md) |
| `Standard Output/Input` | 标准输出/输入 | [内置对象](../builtins/index.md#2-核心常量) |
| `Static Resolution` | 静态解析 | [模块系统](../reference/modules.md#41-预编译阶段静态字符串字面量) |
| `String` | 类型 | [内置类型](../reference/types.md#42-string--unicode-字符串) |
| `String Special Member` | 字符串特殊成员 | [类型系统](../reference/types.md#字符串特殊成员) |
| `stringify` | JSON 函数 | [标准库](../library/json.md#stringify-序列化为-json-字符串) |
| `subtract` | 特殊成员 | [运算符重载](../reference/operator_overloading.md) |
| `Standard Library` | 标准库 | [标准库](../library/index.md) |
| `subscript` | 下标 | [表达式](../reference/expressions.md#下标访问-) |

## T

| 条目 | 类型 | 所在章节 |
|------|------|----------|
| `tanex` | 命令行 | [命令行参数](../using/cmdline.md) |
| `TanexInterpreter` | 解释器类 | [嵌入指南](../extending/embedding.md#11-创建解释器实例) |
| `TanexScript` | 语言名 | [教程](../tutorial/intro.md) |
| `Ternary Operator` | 三目运算符 | [表达式](../reference/expressions.md#三目运算符-cond--t--f) |
| `tokenize` | 编译器 API | [编译器 API](../extending/compiler_api.md#21-tokenizesource-str-filename-str-string-tokenlist) |
| `to_binary` `to_decimal` | 函数 | [bit](../library/bit.md#to_binary--to_decimal--二进制十进制转换) |
| `to_string` | 函数 | [standard](../library/standard.md#to_string-通用字符串转换) |
| `Tutorial` | 教程 | [教程](../tutorial/index.md) |
| `Type` | 类型对象 | [内置类型](../reference/types.md#3-基类型-typetype) |
| `Type Construction` | 类型构造 | [类型系统](../reference/types.md#5-类型构造与初始化) |
| `Type_Name` | 类型名类型 | [内置类型](../reference/types.md#413-function_name--type_name--函数名与类型名类型) |
| `type_error` | 错误前缀 | [错误处理](../howto/error_handling.md#31-标准错误前缀约定) |
| `type_of` | 运算符 | [表达式](../reference/expressions.md#一元类型查询) |
| `Try Expression` | 尝试结构 | [表达式](../reference/expressions.md#尝试结构-left-err--catch--else) |

## U

| 条目 | 类型 | 所在章节 |
|------|------|----------|
| `Unsigned Integer` | 无符号整数 | [内置类型](../reference/types.md#2-原类型-integer) |

## V

| 条目 | 类型 | 所在章节 |
|------|------|----------|
| `Value` | 运行时值 | [运行时值模型](../extending/values.md) |

## W

| 条目 | 类型 | 所在章节 |
|------|------|----------|
| `Warning` | 类型 | [内置类型](../reference/types.md#411-error--错误类型) |
| `While` | 控制流函数 | [教程](../tutorial/controlflow.md#3-while-条件循环) |
| `What` | 错误成员 | [内置对象](../builtins/index.md#111-error--warning--错误与警告) |
| `What's New` | 版本更新 | [版本更新记录](../whatsnew/index.md) |

## X Y Z

| 条目 | 类型 | 所在章节 |
|------|------|----------|
| `Zero-argument Operator` | 零元运算符 | [语句](../reference/statements.md#7-零元运算符语句) |

---

## 相关链接

- [模块索引](modindex.md) — 标准库模块列表
- [完整目录](contents.md) — 所有章节和子章节
- [术语对照表](glossary.md) — 术语中英对照
- [版本更新记录](../whatsnew/index.md) — 版本历史