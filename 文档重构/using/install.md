# 安装说明

> Tanex Script 解释器安装指南。

---

## 1. Windows 安装包 (推荐)

### 下载

- 访问 [GitHub Releases](https://github.com/tanex-script/tanex-script/releases/latest)
- 下载 `TanexScript_Setup.exe` (约 50 MB，含 Python 运行时、标准库、示例)

### 安装步骤

1. 双击运行 `TanexScript_Setup.exe`
2. 选择安装目录(默认 `C:\Program Files\TanexScript`)
3. 勾选“添加到 PATH”(推荐)
4. 点击安装，等待完成
5. 打开新终端验证：
   ```cmd
   tanex --version
   # Tanex Script 1.0.0
   ```

### 卸载

- Windows 设置 → 应用 → Tanex Script → 卸载
- 或运行安装目录下的 `uninstall.exe`

---

## 2. 从源码构建

### 系统要求

| 组件 | 版本要求 |
|------|----------|
| Python | 3.10+ (推荐 3.11+) |
| pip | 最新版 |
| Git | 任意版本 |

### 构建步骤

```bash
# 1. 克隆仓库
git clone https://github.com/tanex-script/tanex-script.git
cd tanex-script

# 2. 进入核心目录
cd 核心

# 3. 安装依赖
pip install -r requirements.txt

# 4. 验证构建
python -m tanex --version
# Tanex Script 1.0.0

# 5. (可选) 运行测试套件
python -m pytest 核心/tests/ -v
```

### 开发模式安装

```bash
# 以可编辑模式安装，修改源码即时生效
pip install -e 核心/
```

---

## 3. 验证安装

### 基础验证

```bash
# 版本信息
tanex --version
# Tanex Script 1.0.0

# 运行内置示例
tanex run 核心/examples/hello.tsuc
# Hello, Tanex Script!

# 启动 REPL
tanex repl
# Tanex Script REPL v1.0.0
# >>> `1` + `2`;
# `3
# >>> :q
```

### 完整功能测试

```bash
# 运行标准库测试
python -m pytest 核心/tests/test_standard_lib.py -v

# 运行语言核心测试
python -m pytest 核心/tests/test_language_core.py -v
```

---

## 4. 常见安装问题

| 问题 | 解决方案 |
|------|----------|
| `tanex` 命令未找到 | 重启终端；检查 PATH 是否包含安装目录；手动添加 `C:\Program Files\TanexScript` 到 PATH |
| Python 版本过低 | 升级至 Python 3.10+ |
| 依赖安装失败 | 升级 pip：`python -m pip install --upgrade pip`；使用国内镜像：`pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple` |
| 权限错误(Windows) | 以管理员身份运行安装包；或安装到用户目录(无需管理员权限) |
| 杀毒软件拦截 | 添加安装目录到白名单；或暂时关闭实时保护 |

---

## 5. 目录结构说明

安装后目录结构：

```
TanexScript/
├── tanex.exe              # 入口可执行文件(Windows)
├── python311.dll          # Python 运行时
├── lib/
│   ├── python3.11/        # 标准库
│   └── tanex/             # Tanex Script 标准库(.tscl)
├── run/
│   ├── bootstrap.tscc     # 引导库编译产物
│   └── standard.tscl      # 标准库编译产物
├── examples/              # 示例程序
├── docs/                  # 文档(本文档)
└── uninstall.exe          # 卸载程序
```

---

## 5. 卸载

```cmd
# 方式1：Windows 设置 → 应用 → Tanex Script → 卸载
# 方式2：运行安装目录下的 uninstall.exe
# 方式3：命令行静默卸载
"C:\Program Files\TanexScript\uninstall.exe" /S
```

---

## 相关链接

- [命令行参数](cmdline.md) — 完整 CLI 参考
- [环境变量](envvars.md) — 配置解释器行为
- [REPL 指南](repl.md) — 交互模式详细用法
- [教程：快速上手](../tutorial/intro.md) — 从零开始编程