# 通用问题

> Tanex Script 语言概况、安装、版本、学习资源等通用问题。

---

## 语言定位与特性

### Q: Tanex Script 是什么类型的语言？
**A**: Tanex Script 是一门**面向元编程与嵌入场景**的动态类型编程语言。主要特性：
- **语法统一化**：所有控制结构（`if`、`for`、`while`、`cycle`、错误处理）均为函数调用，无特殊关键字语法
- **代码块一等公民**：`{...}` 产生 `code` 类型值，可赋值、传参、存储、动态构造
- **运算符重载协议**：通过类型特殊成员（28 个槽位）自定义 30+ 运算符行为
- **显式地址操作**：`/` 取地址、`*` 解地址、`**` 引用声明、`***` 常量声明
- **精确十进制数值**：`Number` 类型内部 `front/back` 表示，无浮点误差
- **编译时/运行时分离**：`.tsuc` → `.tscc` (JSON AST) → 解释器执行

### Q: 适用场景有哪些？
**A**: 
- **嵌入式脚本**：游戏逻辑、配置规则、插件系统
- **元编程/DSL**：代码生成、模板引擎、规则引擎
- **教学/实验**：语法极简、语义清晰，适合编程语言教学
- **快速原型**：REPL 交互、动态类型、高阶函数

### Q: 与 Python/JavaScript/Lua 有何异同？
**A**: 核心差异对比：

| 特性 | Tanex Script | Python | JavaScript | Lua |
|------|--------------|--------|------------|-----|
| 控制结构 | 函数调用 | 语句 | 语句 | 语句 |
| 代码块 | 一等值 | 不可直接操作 | 函数/箭头函数 | 函数 |
| 运算符重载 | 特殊成员槽位 | 特殊方法 `__add__` | 无 | 元表 |
| 地址操作 | 显式 `/` `*` `**` `***` | 无 | 无 | 无 |
| 数字语义 | 精确十进制 | IEEE 754 | IEEE 754 | IEEE 754 |
| 模块 | `import`/`->` 表达式符号 | `import` 语句 | `import` 语句 | `require` |

---

## 安装与运行

### Q: 系统要求是什么？
**A**: 
- **Windows**: 安装包自带 Python 运行时，无需额外安装
- **源码构建**: Python 3.10+、pip、Git
- **内存**: 建议 100MB+ 可用内存

### Q: 如何验证安装成功？
**A**: 
```bash
tanex --version
# Tanex Script 1.0.0

tanex run 核心/examples/hello.tsuc
# Hello, Tanex Script!
```

### Q: 可以在 Linux/macOS 上运行吗？
**A**: 官方提供 Windows 安装包。Linux/macOS 需从源码构建（需 Python 3.10+），或使用 Docker/Wine。原生支持在规划中。

### Q: 如何卸载？
**A**: Windows 设置 → 应用 → Tanex Script → 卸载，或运行安装目录下的 `uninstall.exe`。

---

## 版本与更新

### Q: 当前版本是多少？
**A**: **1.0.0**（基线版本，语法已冻结）。查看 `tanex --version` 确认。

### Q: 版本号规则？
**A**: 语义化版本 `MAJOR.MINOR.PATCH`：
- **MAJOR**: 语法/核心语义破坏性变更（需迁移指南）
- **MINOR**: 向后兼容新增功能（标准库、性能优化）
- **PATCH**: Bug 修复、文档勘误

### Q: 如何获取最新版本？
**A**: 
- [GitHub Releases](https://github.com/tanex-script/tanex-script/releases)
- `git pull` 后重新构建

### Q: 语法会变吗？
**A**: **语法已冻结**。1.x 系列保证语法稳定、语义兼容。破坏性变更仅在 2.0.0+ 且经核心团队评审。

---

## 学习资源

### Q: 从哪里开始学习？
**A**: 
1. [教程：快速上手](../tutorial/intro.md) — 30 分钟入门
2. [教程：控制流](../tutorial/controlflow.md) — if/for/while/cycle/$$
3. [教程：函数与模块](../tutorial/functions_modules.md) — 高阶函数、模块组织
4. [语言参考](../reference/) — 完整规范

### Q: 有交互式教程吗？
**A**: 
```bash
tanex repl
# Tanex Script REPL v1.0.0
# >>> `1` + `2`;
# `3
```

### Q: 哪里可以提问/反馈？
**A**: 
- GitHub Issues: Bug 报告、功能请求
- GitHub Discussions: 使用交流、设计讨论
- 文档勘误: PR 直接修改对应 `.md` 文件

---

## 许可证与贡献

### Q: 许可证是什么？
**A**: MIT License。允许商业使用、修改、分发，保留版权声明。

### Q: 如何贡献代码/文档？
**A**: 
1. Fork 仓库
2. 创建分支 `feature/xxx` 或 `fix/xxx`
3. 提交 PR，遵循《松鼠星球 Python 代码风格指南》
4. 通过 CI 检查后合并

### Q: 核心团队如何联系？
**A**: GitHub @tanex-script/core-team，或邮件 core@tanex-script.org

---

## 相关链接

- [安装说明](../using/install.md) — 详细安装步骤
- [命令行参数](../using/cmdline.md) — 完整 CLI 参考
- [教程：快速上手](../tutorial/intro.md) — 从零开始
- [GitHub 仓库](https://github.com/tanex-script/tanex-script) — 源码、Issues、Releases