# 完整目录

> 对标 [Python Complete Table of Contents](https://docs.python.org/zh-cn/3.16/contents.html)
>
> Tanex Script 文档所有章节和子章节的完整列表。

---

## 前言

- [首页](index.md) — 文档总览、快速导航
- [版本更新记录](whatsnew/index.md) — 1.0.0 基线、后续增量、破坏性变更预警
- [术语对照表](glossary.md) — 120+ 术语中英对照
- [全局索引](genindex.md) — 所有函数、类型、术语字母序检索
- [模块索引](modindex.md) — 标准库模块列表

---

## 第 1 部分：教程

### [快速上手](tutorial/intro.md)
- 启动解释器（安装、运行模式、REPL）
- 入门示例（Hello World、变量与基本类型、列表与代码块）
- 基础编程（表达式与语句、算术/比较/逻辑、字符串/列表操作）
- 控制流（if/for/while/cycle/$$ 循环符、break/continue）
- 函数（命名/匿名、参数形式、传地址、闭包）
- 模块系统（import/->、命名引入、列表批量、public、注解隔离）
- 错误处理（尝试结构、错误对象、警告）
- 注解与文档
- 进阶预览（自定义类型、地址操作、动态 import）

### [深入控制流](tutorial/controlflow.md)
- if 条件分支（真值判定、多重分支）
- for 遍历循环（可遍历类型、循环变量、break/continue）
- while 条件循环
- cycle 定次循环
- $$ 循环符（条件求值、收集语义、break/continue）
- 错误处理控制流（尝试结构、嵌套捕获）
- 多层跳出 $
- 最佳实践（选择循环构造、避免常见错误、性能提示）

### [函数与模块](tutorial/functions_modules.md)
- 函数定义（命名/匿名、参数形式、函数体与返回值）
- 参数传递机制（传地址、默认值、无可变参数）
- 作用域与闭包（词法作用域、闭包捕获、上级访问 ~）
- 高阶函数模式（函数作为值、柯里化、回调、管道 |>, 标准库工具）
- 递归（直接/相互递归、深度限制、尾递归改写）
- 控制流函数标准签名
- 模块系统（文件后缀、import/-> 语义对比、引入形式、路径解析、public、注解隔离、REPL 常量）
- 模块组织最佳实践（目录结构、public、内部模块、版本管理、测试组织）
- 常见错误与调试（参数副作用、闭包陷阱、递归栈溢出）

---

## 第 2 部分：语言参考

### [词法分析](reference/lexical.md)
- 源文件编码与行结构（UTF-8、行终止符、无续行语法、反斜杠是整除）
- 空白字符
- 注释（语法、规则、文档注释约定）
- 注解（语法、编译产物、作用域与读取、库隔离）
- 标识符规范（合法字符、非法示例、保留字、命名约定）
- 关键字别名（and/or/not/is → &&/||/!/==）
- 字面量语法（整数、数字、字符串转义、布尔、特殊字面量）
- 运算符符号表（完整符号列表、重载性）

### [语法结构](reference/lexical.md#语法结构) → [单独文件](reference/lexical.md)
- 语句与表达式统一定义
- 语句分类完备表
- 代码块与匿名函数语法异同
- 作用域规则（词法作用域、遮蔽、上级访问、闭包捕获）
- 程序结构与编译产物 JSON Schema

### [运算符优先级与结合性](reference/lexical.md#运算符优先级与结合性权威表) → [单独文件](reference/lexical.md)
- 权威优先级表（17 级、结合性、操作数位置）
- 关键解析规则（import 绑定优先级、&&/$/* 歧义解析）

### [类型系统](reference/types.md)
- 类型分类总览（原类型/基类型/复合类型、层级图）
- 原类型 Integer（特性、混合运算、除零、位运算）
- 基类型 Type_Type（结构字段、特殊成员槽位完备表、比较兜底规则、继承复制规则、成员查找顺序）
- 复合类型详解（Number/String/Boolean/None/NaN/Infinite/List/Code/Address/Error/Warning/Library/Function_Name/Type_Name）
- 类型构造与初始化（语法、机制、特殊情况）
- 继承机制（语义、成员查找顺序、示例）
- 真值判定规则（权威表、实现参考）
- 运算符重载协议（注册方式、签名约定、完整映射表、示例）
- 行为控制标记（addable/external_read_only/public）

### [表达式](reference/expressions.md)
- 求值顺序（一般原则、特殊规则表）
- 原子表达式（字面量、标识符、分组、代码块、列表）
- 一元运算符条目（~ ! * / ** *** & && &&& <- $ return ?? type_of + -）
- 二元运算符条目（算术、输出/输入、管道、循环符、比较、逻辑、in、赋值、成员、下标、实例创建、匿名函数、多层跳出）
- 三目与尝试结构（三目运算符、尝试结构详解）

### [语句](reference/statements.md)
- 语句分类完备表
- 表达式语句、空语句
- 声明语句（简单/引用/常量/数量/连续声明）
- 赋值语句（目标解析、复合赋值、特殊赋值目标）
- 导入语句
- 零元运算符语句（break/continue）
- 注解语句
- 程序结构与编译产物 JSON Schema

### [函数与过程](reference/functions.md)
- 函数声明语法（命名/匿名、参数列表语法、函数体、声明特性）
- 参数传递机制（传地址、绑定顺序与默认值、可变参数）
- 返回值（显式/隐式、类型）
- 作用域与闭包（定义时捕获、调用时子作用域、闭包捕获地址、上级访问 ~）
- 高阶函数模式（函数作为值、柯里化、回调、管道 |>, 标准库工具）
- 递归（直接/相互递归、深度限制、尾递归改写）
- 控制流函数标准签名

### [模块系统](reference/modules.md)
- 模块概念与文件后缀
- import 与 -> 语义对比
- 引入形式完备（单条/命名/列表批量/列表命名）
- 路径解析算法（预编译/运行时、歧义消除、标准库优先）
- 库初始化顺序（依赖拓扑、循环检测、main 入口、嵌套库展开）
- 可见性控制：public
- 库注解隔离机制
- REPL 内置常量

### [错误处理](reference/errors.md)
- 错误类型层级（用户抛出、运行时内部、编译期）
- 错误构造与抛出（error/warning、<- 抛出）
- 尝试结构详解（执行语义、错误绑定作用域、成功分支可选）
- 标准库错误分类与错误码约定
- 顶层未捕获错误处理
- 错误处理最佳实践

### [运算符重载](reference/operator_overloading.md)
- 注册方式
- 特殊成员完备映射表
- 比较兜底调用规则
- 完整注册示例（Vec2、Matrix、HashSet）
- 注意事项与最佳实践（签名规范、常见错误、性能建议、行为控制标记）
- 内置类型重载表

### [运行时内部机制](reference/runtime_internals.md)
- 启动流程总览（时序图、详细步骤、环境共享）
- 核心类型初始化规范（type_type/integer/空壳创建、Boolean/None/List/String/Number/控制流/IO）
- 引导库注解表
- 版本演进与兼容性
- 控制流信号机制（Break/Continue/Return/Error/MultiLevelReturn 信号、传播规则、$$ 内部实现、多层跳出）
- 模块加载器内部实现（load_library_module、路径解析、.tscc/.tscl/目录加载）
- 注解系统内部实现
- 标准库注册机制

---

## 第 3 部分：标准库参考

### [标准库总览](library/index.md)
- 模块总览表
- 通用引入方式
- 快速查找表（数学/字符串/编码/序列化/随机数/核心扩展）

### [standard 核心扩展](library/standard.md)
- 类型构造辅助、基础算术、字符串操作、列表操作、I/O 封装、反射/内省、控制流辅助、函数式工具

### [maths 数学库](library/maths.md)
- 基础算术、数论、数学常量、进阶数学函数

### [numeral_system 进制转换](library/numeral_system.md)
- 2/8/10/16 进制互转

### [encoding.ascii ASCII 编解码](library/encoding_ascii.md)
- 编解码、字符分类、大小写转换

### [encoding.base_sixty_four Base64](library/encoding_base64.md)
- 编解码

### [json JSON 序列化](library/json.md)
- stringify/parse、类型映射

### [random 随机数](library/random.md)
- LCG、种子、多种分布、洗牌

### [bit 位运算](library/bit.md)
- 逻辑运算、移位、二进制↔十进制转换

---

## 第 4 部分：Python API 参考

### [扩展与嵌入总览](extending/index.md)
- 快速开始：Python 嵌入、注册内置类型

### [嵌入指南](extending/embedding.md)
- 基础嵌入（创建解释器、运行源码/文件/AST、REPL）
- 配置与依赖注入（内置常量、自定义函数/类型）
- 高级场景（沙箱、多实例、状态持久化）
- 错误处理
- 性能优化建议
- 完整示例：表达式计算器服务

### [编译器 API](extending/compiler_api.md)
- 词法分析、语法分析、一体化编译、编译文件、依赖提取
- 诊断信息结构、错误码对照表
- 完整示例：构建工具链

### [运行时值模型](extending/values.md)
- 值类层级、具体值类（Integer/Number/String/Boolean/单例/List/Code/Address/Error/Warning/Library/Type/Instance/Function）
- 值构造工厂函数
- 真值判定与类型查询
- 真值判定规则表

### [地址空间与作用域 API](extending/environment.md)
- AddressSpace、Scope
- 赋值目标解析、上级访问 ~、闭包捕获机制
- 常用操作封装

### [核心执行器](extending/interpreter.md)
- 核心求值入口、控制流信号、特殊成员调度（二元/一元/比较分发）、特殊成员调用、内置运算符实现、代码块执行与收集模式、模块执行

### [模块加载器](extending/loader.md)
- 加载入口、路径解析算法、加载实现、模块缓存、注解隔离机制

### [注解系统](extending/annotations.md)
- AnnotationTable、合并策略、读取实现、作用域规则、编译期收集、性能考量

### [标准库注册机制](extending/stdlib_registration.md)
- 内置类型/函数/特殊成员注册、启动时注册顺序

### [错误与诊断](extending/errors.md)
- 异常类层级、诊断信息结构、错误码对照表（编译期/语义/运行时/警告）、输出示例、最佳实践、调试支持

---

## 第 5 部分：专题指南

### [类型设计模式](howto/type_design.md)
- 封装与不变量、继承与多态、运算符重载实战、容器与集合类型、行为控制清单、完整示例：不可变记录类型

### [错误处理模式](howto/error_handling.md)
- 基础捕获、资源管理（RAII、多资源嵌套、标准库辅助）、错误分类与自定义错误、警告机制、断言与契约、测试中的错误处理、调试技巧、最佳实践清单

### [性能优化](howto/performance.md)
- 性能特征概览、基准测试方法、常见优化模式（循环、避免重复计算、内联小函数、内置类型优先）、标准库选择指南、内存优化、算法层面优化、解释器配置调优、性能分析工具、实战案例：斐波那契优化、性能清单

### [模块组织](howto/module_organization.md)
- 推荐目录结构、库设计原则、入口文件 main.tsuc、内部模块、版本管理、编译与打包、测试组织、文档生成、迁移清单

### [元编程](howto/metaprogramming.md)
- 注解驱动开发、代码块操作、动态 Import、运行时类型构造、反射与内省、编译时元编程、实战案例：规则引擎

### [DSL 构建](howto/dsl_building.md)
- 设计原则、内部 DSL 模式（函数式构建器、管道式、控制流）、外部 DSL（解析器组合子、JSON 解析器）、模板 DSL、配置 DSL、测试 DSL、实战案例：HTTP 路由 DSL、最佳实践

### [测试策略](howto/testing.md)
- 测试层级、单元测试基础、测试运行器、属性测试、集成测试、端到端测试、测试组织最佳实践、CI 集成

### [互操作](howto/interop.md)
- Python 嵌入、编译器 API、运行时值操作、C API 计划、外部库调用、进程间通信、最佳实践清单

---

## 第 6 部分：常见问题

### [FAQ 总览](faq/index.md)
- 快速问答（语言定位、安装、运行、if/for 是函数、import/-> 区别、反斜杠、自定义类型、参数传地址、错误处理、Python 嵌入、标准库模块）

### [通用问题](faq/general.md)
- 语言定位与特性、安装与运行、版本与更新、学习资源、许可证与贡献

### [语法与语义](faq/syntax.md)
- 运算符与表达式、控制流、类型系统、作用域与闭包、模块系统

### [标准库](faq/stdlib.md)
- 模块导入、常用功能（输出/输入、字符串/列表/数学/进制/Base64/JSON/随机数/位运算）、性能与最佳实践、常见错误

### [嵌入与扩展](faq/embedding.md)
- Python 嵌入、编译器 API、运行时值操作、C API 计划、外部库调用、互操作场景、性能与调试、常见错误

### [故障排查](faq/troubleshooting.md)
- 常见报错分析（编译期/运行时）、语义陷阱排查、调试技巧、性能问题排查、调试工具、获取帮助

---

## 第 7 部分：附录

- [术语对照表](glossary.md) — 120+ 术语中英对照
- [全局索引](genindex.md) — 所有函数、类型、术语字母序检索
- [模块索引](modindex.md) — 标准库模块列表
- [版本更新记录](whatsnew/index.md) — 1.0.0 基线、后续增量、破坏性变更预警
- [完整目录](contents.md) — 本页

---

## 文档统计

| 部分 | 文件数 | 核心内容 |
|------|--------|----------|
| 教程 | 3 | 入门到进阶完整指引 |
| 语言参考 | 9 | 完整语法语义规范 |
| 标准库 | 9 | 8 个模块逐条目规范 |
| Python API | 9 | 解释器嵌入到错误诊断 |
| 专题指南 | 7 | 实战深度指南 |
| FAQ | 5 | 分类常见问题解答 |
| 辅助页面 | 4 | 术语/索引/模块/目录 |
| **总计** | **46** | **全覆盖** |

---

## 维护说明

- 本文档对标 [Python 3.16 官方文档结构](https://docs.python.org/zh-cn/3.16/)
- 语法已冻结，仅补示例/澄清/修勘误
- 版本变更同步更新 [whatsnew](whatsnew/index.md)
- 贡献指南见 [GitHub 仓库](https://github.com/tanex-script/tanex-script)