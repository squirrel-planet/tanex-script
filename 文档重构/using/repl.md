# REPL 交互模式详细指南

> Tanex Script REPL (Read-Eval-Print Loop) 使用手册。

---

## 启动 REPL

```bash
# 方式1：直接启动
tanex repl

# 方式2：通过 python 模块
python -m tanex repl

# 方式3：带参数启动
tanex repl --verbose
```

### 启动画面

```
Tanex Script REPL v1.0.0
输入 :h 显示帮助，:q 退出
>>>
```

---

## 基本操作

### 输入规则

- **单行输入**：以分号 `;` 结尾，按回车执行
- **多行输入**：未以 `;` 结尾时自动续行，提示符变为 `... `
- **取消当前输入**：`Ctrl+C` (不退出 REPL)
- **退出 REPL**：`:q` 或 `Ctrl+D` (EOF)

```tanex script
>>> `1` + `2`;          # 单行，立即执行
`3
>>> * x = `10;          # 单行声明
>>> if(true, {          # 多行开始
...     $ "yes";        # 提示符变为 ...
... }, {                # 继续
...     $ "no";         # 继续
... });                 # 以 ; 结束，执行
yes
```

### 提示符含义

| 提示符 | 状态 |
|--------|------|
| `>>>` | 等待新语句 |
| `... ` | 多行续行中 (未遇到分号) |

---

## REPL 专用命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `:h` / `:help` | 显示帮助 | `:h` |
| `:q` / `:quit` | 退出 REPL | `:q` |
| `:ast` | 显示最后一条语句的 AST | `:ast` |
| `:tokens` | 显示最后一条语句的 Token 列表 | `:tokens` |
| `:vars` | 显示当前作用域所有变量 | `:vars` |
| `:clear` | 清屏 | `:clear` |
| `:history` | 显示历史输入 | `:history` |
| `:load <file>` | 加载并执行文件 | `:load hello.tsuc` |
| `:save <file>` | 保存历史到文件 | `:save session.tsuc` |
| `:edit` | 用外部编辑器编辑多行输入 | `:edit` |

---

## 内置常量 (REPL 特有)

REPL 会话注入以下常量 (同脚本运行)：

| 常量 | REPL 值 | 说明 |
|------|---------|------|
| `path` | `none` | REPL 无脚本文件 |
| `program_path` | 解释器安装目录 | 如 `C:/Program Files/TanexScript` |
| `args` | `[]` | REPL 下通常为空 |

**用途**：在 REPL 中引用标准库相对路径资源：

```tanex script
>>> import program_path + "/lib/extra.tsuc";
```

---

## 历史与自动补全

### 历史文件

- 默认位置：`~/.tanex_history` (Windows: `%USERPROFILE%\.tanex_history`)
- 自动保存：每条执行的语句追加写入
- 上下键：浏览历史
- `Ctrl+R`：反向搜索历史

### 自动补全 (Tab 键)

- 标识符补全：变量名、函数名、类型名
- 关键字补全：`if`、`for`、`import` 等
- 成员补全：`std.` 按 Tab 显示 `standard_output` 等
- 模块路径补全：`import "` 按 Tab 列出可用库

---

## 多行编辑模式

### `:edit` 命令

```tanex script
>>> :edit
# 打开外部编辑器 (由 EDITOR 环境变量决定，默认 notepad/vim)
# 编辑完成保存退出后，自动作为多行输入执行
```

### 手动多行输入

```tanex script
>>> * factorial = [*n] => {
...     n <= `1 ? { $ `1; } : { $ n * factorial(n - `1); };
... };
>>> factorial(`5);
`120
```

---

## REPL 与脚本的差异

| 特性 | REPL | 脚本运行 |
|------|------|----------|
| `path` 常量 | `none` | 脚本绝对路径 |
| `args` 常量 | `[]` | 命令行参数列表 |
| 顶层 `$ n` | 打印返回值，不退出 | 以 n 为退出码退出进程 |
| 变量持久化 | 会话内全局保留 | 进程结束销毁 |
| 错误处理 | 捕获打印，继续运行 | 未捕获则退出进程 |

---

## 示例会话

```bash
$ tanex repl
Tanex Script REPL v1.0.0
输入 :h 显示帮助，:q 退出
>>> import "standard" = *std;
>>> std.println("Hello REPL!");
Hello REPL!
>>> * square = [*x] => { $ x * x; };
>>> square(`5);
`25
>>> :vars
square => Function
std => Library
>>> :ast
{"binary": {"operator": "*", "left": {"name": {"value": "x", ...}}, ...}}
>>> :q
Bye!
```

---

## 常见问题

| 问题 | 解决方案 |
|------|----------|
| 多行输入卡住 | 检查是否漏写分号 `;`；按 `Ctrl+C` 取消当前输入 |
| 变量名冲突 | 使用 `:vars` 查看现有变量；重启 REPL (`:q` 后重新启动) |
| 导入本地库失败 | 确保 `TANEX_LIB_PATH` 包含库目录；或用绝对路径 `import "/abs/path/lib"` |
| 自动补全不工作 | 检查终端是否支持 Tab 补全；尝试 `tanex repl --verbose` 看调试信息 |

---

## 相关链接

- [命令行参数](cmdline.md) — `repl` 子命令选项
- [环境变量](envvars.md) — `TANEX_VERBOSE` 等影响 REPL
- [教程：快速上手](../tutorial/intro.md#13-repl-交互模式基本操作) — 入门示例
- [扩展与嵌入：Python API](../extending/) — 程序化启动 REPL