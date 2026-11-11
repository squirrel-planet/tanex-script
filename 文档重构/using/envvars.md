# 环境变量

> Tanex Script 解释器支持的环境变量完整列表。

---

## 环境变量总览

| 环境变量 | 对应 CLI 选项 | 说明 | 示例值 |
|----------|---------------|------|--------|
| `TANEX_BOOTSTRAP_PATH` | `--bootstrap-path` | 引导库 `bootstrap.tscc` 路径 | `C:/custom/bootstrap.tscc` |
| `TANEX_LIB_PATH` | `--lib-path` | 库搜索路径列表 (分隔符: Windows `;` / Unix `:`) | `C:/my_libs;/shared/libs` |
| `TANEX_RECURSION_LIMIT` | `--recursion-limit` | 递归深度限制 (正整数) | `2000` |
| `TANEX_STACK_SIZE` | `--stack-size` | 解释器操作栈大小 (正整数) | `16384` |
| `TANEX_VERBOSE` | `--verbose` | 详细输出模式 (`1`=开启) | `1` |
| `TANEX_QUIET` | `--quiet` | 静默模式 (`1`=开启) | `1` |

---

## 优先级规则

**命令行选项 > 环境变量 > 默认值**

```bash
# 环境变量设置
export TANEX_LIB_PATH="/my/libs:/shared/libs"
export TANEX_RECURSION_LIMIT=2000

# 命令行覆盖
tanex run app.tsuc --lib-path "/override/libs" --recursion-limit 5000
# 实际使用: lib-path="/override/libs", recursion-limit=5000
```

---

## 详细说明

### `TANEX_BOOTSTRAP_PATH`

指定引导库编译产物 `bootstrap.tscc` 的路径。

- **用途**：自定义引导库位置、测试不同版本引导库
- **默认**：`run/bootstrap.tscc` (相对于解释器安装目录)
- **要求**：必须为有效的 `.tscc` 文件

```bash
export TANEX_BOOTSTRAP_PATH="/custom/bootstrap.tscc"
```

### `TANEX_LIB_PATH`

库搜索路径列表，用于解析相对路径的 `import`/`->`。

- **分隔符**：Windows `;`，Unix-like `:`
- **搜索顺序**：当前文件目录 → `TANEX_LIB_PATH` 列表顺序 → 安装目录标准库
- **可多次指定**：对应 CLI `--lib-path` 可多次使用

```bash
# Windows
set TANEX_LIB_PATH=C:\my_libs;D:\shared\libs

# Unix-like
export TANEX_LIB_PATH="/home/user/tanex_libs:/opt/tanex_libs"
```

### `TANEX_RECURSION_LIMIT`

递归深度限制，防止栈溢出。

- **单位**：调用层数
- **默认**：`1000`
- **建议范围**：`100` ~ `10000`
- **过小**：正常递归报错“递归深度超限”
- **过大**：可能导致解释器崩溃

```bash
export TANEX_RECURSION_LIMIT=2000
```

### `TANEX_STACK_SIZE`

解释器操作栈大小。

- **单位**：栈帧数
- **默认**：`8192`
- **影响**：深度嵌套表达式、大量局部变量的函数

```bash
export TANEX_STACK_SIZE=16384
```

### `TANEX_VERBOSE` / `TANEX_QUIET`

控制输出详细程度。

| 变量 | 值 | 效果 |
|------|----|------|
| `TANEX_VERBOSE` | `1` | 启用详细输出：编译耗时、模块加载路径、AST 节点数等 |
| `TANEX_QUIET` | `1` | 静默模式：仅错误输出到 stderr，抑制普通输出 |

```bash
# 详细模式
export TANEX_VERBOSE=1
tanex run app.tsuc
# [VERBOSE] Compiling app.tsuc... 12ms
# [VERBOSE] Loading bootstrap.tscc... 3ms
# [VERBOSE] Executing... 5ms

# 静默模式
export TANEX_QUIET=1
tanex run app.tsuc
# (无输出，除非程序主动打印或发生错误)
```

**冲突处理**：同时设置 `VERBOSE=1` 和 `QUIET=1` 时，**静默模式优先**。

---

## 配置文件 (计划中)

> 未来版本将支持配置文件 `tanex.toml` / `.tanexrc`，优先级：**CLI > 环境变量 > 配置文件 > 默认值**。

计划支持的配置项：
```toml
# tanex.toml 示例
[interpreter]
recursion_limit = 2000
stack_size = 16384
verbose = false

[paths]
bootstrap = "run/bootstrap.tscc"
lib_paths = ["libs", "/shared/tanex_libs"]

[repl]
history_file = "~/.tanex_history"
auto_complete = true
```

---

## 相关链接

- [命令行参数](cmdline.md) — 对应 CLI 选项
- [安装说明](install.md) — 获取解释器
- [REPL 指南](repl.md) — 交互模式环境变量
- [扩展与嵌入：Python API](../extending/) — 程序化配置解释器