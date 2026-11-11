# Tanex Script 文档

> **版本**：1.0.0  
> **适用语言版本**：Tanex Script 1.x  
> **最后更新**：2025-01-15  
> **对标标准**：[Python 3.16 官方文档结构](https://docs.python.org/zh-cn/3.16/)

---

## 文档章节

| 章节 | 说明 | 对应 Python 文档 |
|------|------|------------------|
| [whatsnew/](whatsnew/) | 版本更新记录 | [What's New](https://docs.python.org/zh-cn/3.16/whatsnew/) |
| [tutorial/](tutorial/) | 教程 | [Tutorial](https://docs.python.org/zh-cn/3.16/tutorial/) |
| [builtins/](builtins/) | 内置对象参考 | [Built-in Types](https://docs.python.org/zh-cn/3.16/library/stdtypes.html) |
| [library/](library/) | 标准库参考 | [Library Reference](https://docs.python.org/zh-cn/3.16/library/) |
| [reference/](reference/) | 语言参考 | [Language Reference](https://docs.python.org/zh-cn/3.16/reference/) |
| [using/](using/) | 安装与使用 | [Using Python](https://docs.python.org/zh-cn/3.16/using/) |
| [howto/](howto/) | 专题指南 | [HOWTOs](https://docs.python.org/zh-cn/3.16/howto/) |
| [extending/](extending/) | 扩展与嵌入 (Python API) | [Extending](https://docs.python.org/zh-cn/3.16/extending/) |
| [faq/](faq/) | 常见问题 | [FAQ](https://docs.python.org/zh-cn/3.16/faq/) |
| [deprecations/](deprecations/) | 废弃项清单 | [Deprecations](https://docs.python.org/zh-cn/3.16/deprecations/) |

---

## 快速导航

### 初学者入门
1. [安装与运行](using/install.md) — 获取解释器、编译运行流程
2. [教程：快速上手](tutorial/intro.md) — 从 Hello World 到基础编程
3. [教程：控制流](tutorial/controlflow.md) — if/for/while/cycle/$$ 循环符
4. [教程：函数与模块](tutorial/functions_modules.md) — 函数定义、匿名函数、import/->

### 语言使用者
- [语言参考：词法](reference/lexical.md) — 编码、标识符、字面量、运算符、注释、注解
- [语言参考：类型系统](reference/types.md) — Integer/Number/String/Boolean/List/Code/Type_Type 等
- [语言参考：表达式](reference/expressions.md) — 运算符优先级、求值顺序、特殊形式
- [语言参考：语句](reference/statements.md) — 声明、赋值、导入、零元、错误处理
- [语言参考：函数](reference/functions.md) — 定义、参数传递、闭包、高阶函数
- [语言参考：模块](reference/modules.md) — import/->、路径解析、public、注解隔离
- [语言参考：错误处理](reference/errors.md) — 错误类型、尝试结构、错误码
- [内置对象](builtins/) — 核心类型、常量、函数、特殊成员完整规范
- [标准库](library/) — 8 个模块逐条目规范

### 库作者 / 深度开发者
- [标准库详细条目](library/) — maths/numeral_system/encoding/json/random/bit 等
- [专题指南](howto/) — 类型设计模式、错误处理模式、性能优化、模块组织
- [扩展与嵌入](extending/) — Python API：解释器嵌入、编译器、值模型、地址空间、模块加载器
- [语言参考：运行时内部](reference/runtime_internals.md) — 启动流程、引导库初始化、核心类型填充

### 维护者 / 贡献者
- [版本更新记录](whatsnew/) — 1.0.0 基线、后续增量
- [废弃项清单](deprecations/) — 无废弃语法（已冻结）、潜在未来废弃预警
- [FAQ](faq/) — 常见语法陷阱、语义陷阱、最佳实践

---

## 文档约定

| 标记 | 含义 | 示例 |
|------|------|------|
| `` `code` `` | 行内代码/标识符/关键字 | `` `if` ``、`` `integer` `` |
| ```tanex script\n...\n``` | 代码块 | 可运行示例 |
| `# =>` | 预期输出注释 | `` `1` + `2`; # => `3` `` |
| **[粗体]** | 关键术语/强调 | **原类型**、**特殊成员** |
| *斜体* | 参数名/占位符 | *`value`*、*`condition`* |
| `[待确认：原因]` | 不确定内容标注 | `[待确认：Number除法精度策略]` |

---

## 相关资源

- [GitHub 仓库](https://github.com/tanex-script/tanex-script) — 源码、Issues、PR
- [安装包下载](https://github.com/tanex-script/tanex-script/releases) — Windows Setup.exe
- [术语对照表](glossary.md) — 120+ 术语中英对照
- [全局索引](genindex.md) — 所有函数、类型、术语检索
- [模块索引](modindex.md) — 标准库模块列表
- [完整目录](contents.md) — 所有章节和子章节

---

> **对标说明**：本文档结构完全对标 [Python 3.16 官方文档](https://docs.python.org/zh-cn/3.16/)，采用相同的章节划分与导航体系，便于 Python 用户迁移学习。内容上保留 Tanex Script 独特语法（语法统一化、代码块一等公民、运算符重载、显式地址操作等）。