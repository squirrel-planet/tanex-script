# 命令行参数完整参考

> `tanex` / `python -m tanex` 命令行接口完整规范。

---

## 总览

```bash
tanex <command> [options] [args...]

# 或
python -m tanex <command> [options] [args...]
```

### 子命令

| 命令 | 说明 |
|------|------|
| `run` | 编译并运行 / 直接运行 `.tscc` |
| `compile` | 编译源码为 `.tscc` |
| `repl` | 启动交互模式 |
| `ast` | 仅输出 AST JSON (调试用) |
| `tokenize` | 仅输出 Token 列表 (调试用) |
| `version` | 显示版本信息 |
| `help` | 显示帮助 |

---

## 通用选项

| 选项 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--bootstrap-path <path>` | `-b` | 指定 `bootstrap.tscc` 路径 | `run/bootstrap.tscc` |
| `--lib-path <path>` | `-L` | 添加库搜索路径 (可多次) | `[]` |
| `--recursion-limit <n>` | | 设置递归深度限制 | `1000` |
| `--stack-size <n>` | | 设置解释器栈大小 | `8192` |
| `--verbose` | `-v` | 详细输出(编译耗时、加载模块等) | 关闭 |
| `--quiet` | `-q` | 静默模式(仅错误输出) | 关闭 |
| `--help` | `-h` | 显示帮助 | — |
| `--version` | `-V` | 显示版本 | — |

---

## `run` — 运行程序

```bash
tanex run <input.tsuc|.tscc> [args...]
```

### 参数

| 参数 | 说明 |
|------|------|
| `input` | 输入文件：`.tsuc` (源码，内部自动编译) 或 `.tscc` (编译产物) |
| `args...` | 传递给程序的命令行参数 (在程序中通过内置 `args` 访问) |

### 示例

```bash
# 直接运行源码
tanex run hello.tsuc

# 运行编译产物
tanex run build/main.tscc

# 传递参数
tanex run app.tsuc arg1 arg2 "arg 3"
# 程序内: args => ["arg1", "arg2", "arg 3"]
```

### 退出码

| 码 | 含义 |
|----|------|
| `0` | 正常结束(无顶层返回、无错误) |
| `n` (非0) | 顶层 `$ n` 显式返回 (n 必为 Integer) |
| `1` | 未捕获错误、顶层返回非 Integer、编译失败 |

---

## `compile` — 编译源码

```bash
tanex compile <input.tsuc> [-o output.tscc]
```

### 参数

| 参数 | 说明 |
|------|------|
| `input.tsuc` | 源文件路径 |
| `-o, --output <path>` | 输出 `.tscc` 路径，省略则输出到同目录同名 `.tscc` |

### 示例

```bash
# 编译到同目录
tanex compile src/main.tsuc
# => src/main.tscc

# 指定输出路径
tanex compile src/main.tsuc -o build/main.tscc

# 批量编译 (配合 shell)
for f in src/*.tsuc; do tanex compile "$f" -o "build/$(basename "$f" .tsuc).tscc"; done
```

### 编译产物

输出为 JSON 格式 `.tscc`，结构见 [语言参考：语句](../reference/statements.md#92-编译产物-json-schema)。

---

## `repl` — 交互模式

```bash
tanex repl
```

详见 [REPL 指南](repl.md)。

---

## `ast` — 输出 AST (调试)

```bash
tanex ast <input.tsuc> [--pretty]
```

| 选项 | 说明 |
|------|------|
| `--pretty` | 格式化输出 JSON (缩进 2 空格) |

### 示例

```bash
tanex ast hello.tsuc | jq .
# {
#   "Tanex Script": [...],
#   "annotations": {},
#   "annotation": "Hello World 示例"
# }
```

---

## `tokenize` — 输出 Token 列表 (调试)

```bash
tanex tokenize <input.tsuc>
```

### 示例

```bash
tanex tokenize hello.tsuc
# [
#   {"type": "import", "value": "import", "pos": [1, 1]},
#   {"type": "string", "value": "\"standard\"", "pos": [1, 8]},
#   {"type": "semicolon", "value": ";", "pos": [1, 18]},
#   ...
# ]
```

---

## `version` — 版本信息

```bash
tanex version
# Tanex Script 1.0.0
# Python 3.11.5
# Bootstrap: run/bootstrap.tscc v1
```

---

## `help` — 帮助

```bash
tanex help [command]
```

| 用法 | 示例 |
|------|------|
| `tanex help` | 显示所有子命令概览 |
| `tanex help run` | 显示 `run` 详细帮助 |
| `tanex run --help` | 等价 |

---

## 环境变量影响

| 环境变量 | 对应选项 | 说明 |
|----------|----------|------|
| `TANEX_BOOTSTRAP_PATH` | `--bootstrap-path` | 引导库路径 |
| `TANEX_LIB_PATH` | `--lib-path` | 库搜索路径 (冒号/分号分隔) |
| `TANEX_RECURSION_LIMIT` | `--recursion-limit` | 递归限制 |
| `TANEX_STACK_SIZE` | `--stack-size` | 栈大小 |
| `TANEX_VERBOSE` | `--verbose` | 设为 `1` 启用详细输出 |

环境变量优先级：**命令行选项 > 环境变量 > 默认值**。

---

## 文件关联 (Windows)

安装包自动关联：
- `.tsuc` → `tanex run "%1" %*`
- `.tscc` → `tanex run "%1" %*`

双击 `.tsuc`/`.tscc` 文件即可运行。

---

## 完整示例：构建与运行流程

```bash
# 1. 创建项目结构
mkdir my_project
cd my_project
mkdir src build

# 2. 编写源码
cat > src/main.tsuc << 'EOF'
@ # My App #;
import "standard" = *std;
import "maths" = *math;

std.println("App started");
std.println("PI = " + math.pi.string());
std.println("2^10 = " + math.power_integer(`2`, `10`).string());
EOF

# 3. 编译
tanex compile src/main.tsuc -o build/main.tscc

# 4. 运行
tanex run build/main.tscc
# App started
# PI = 3.1416
# 2^10 = 1024

# 5. 直接运行源码 (开发时)
tanex run src/main.tsuc
```

---

## 相关链接

- [安装说明](install.md) — 获取解释器
- [环境变量](envvars.md) — 详细环境变量配置
- [REPL 指南](repl.md) — 交互模式详细用法
- [编译流程](compilation.md) — 编译器内部流程
- [教程：快速上手](../tutorial/intro.md) — 从零开始