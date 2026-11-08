# TanexScript IDLE

一个模仿 Python IDLE 的 TanexScript 集成开发与学习环境，基于 Tkinter，
提供「交互式 Shell 窗口」与「文件编辑器窗口」，共用同一套菜单栏。

**Shell 不自己实现任何执行逻辑**：它直接启动官方的 `python -u main.py -s`，
把子进程的 stdin / stdout / stderr 接到文本控件上，等价于在终端里跑官方 REPL。
语句完整性判断、续行缩进、静默语句规则、回显格式、错误排版全部由官方 REPL 决定。

```
IDLE/
├── idle.py            入口：IDLEApp（窗口管理、运行调度、退出）
├── shell.py           Shell 窗口：终端式驱动官方 main.py -s
├── editor.py          编辑器窗口：新建/打开/保存/运行 .tsuc
├── codeview.py        文本控件：行号栏、语法着色、Shell 标签
├── lexer.py           容错词法扫描：着色、输入运算符识别、自动缩进
├── runner.py          子进程管理：官方 REPL / 编译 / 运行命令
├── menus.py           菜单栏定义（Shell / Editor 共用）
├── window.py          窗口公共行为：撤销/重做/剪切/复制/粘贴/查找
├── config.py          路径、字体、配色、图标
├── tanex-script.ico   应用图标（Windows 标题栏 / 任务栏）
└── logo.png           应用图标（其他平台的备用，iconphoto）
```

### 图标

Shell 与每个编辑器窗口启动时都会调用 `config.apply_icon()`：
Windows 下用 `iconbitmap('tanex-script.ico')` 设置标题栏图标，再用
`WM_SETICON` 补挂 32×32（任务栏）与 48×48（Alt+Tab）两档图标；
失败或非 Windows 平台则退回 `iconphoto` 用 `logo.png`。

**任务栏图标**还需要 `config.set_app_user_model_id()`：不显式声明
AppUserModelID 的话，Windows 会把窗口归入 `python.exe` 组，任务栏显示的是
Python 的图标而不是我们的。它在 `main()` 里、`IDLEApp` 创建任何窗口之前调用
（必须早于窗口创建）。

两个坑：

- `wm iconbitmap` 查询会返回空串，这是 Tk 对文件型图标的正常表现，
  图标其实已生效；要验证请用 `WM_GETICON`（0x7F）读窗口句柄。
- 拿真正的顶层窗口句柄要用 `root.frame()`，`winfo_id()` 给的是子窗口。

`tanex-script.ico` 内嵌 16/32/48 三档尺寸。

## 启动

需要带有 Tkinter 与 prompt_toolkit 的 Python（本机为 `D:/python/python.exe`，
3.14 + Tk 8.6 + prompt_toolkit 3.0.53）。

```bash
python IDLE/idle.py                 # 只打开 Shell
python IDLE/idle.py standard/json.tsuc
python IDLE/idle.py a.tsuc b.tsuc   # 打开 Shell 并载入指定文件
```

启动后 Shell 会加载 `runtime/bootstrap.tsuc`（约 0.6 秒），就绪后出现 `>>>`。

## Shell 窗口

行为与官方 `main.py -s` 完全一致：

- 每条语句以 `;` 结尾后立即执行；语句未完整时官方 REPL 自己输出 `... ` 续行
  并带上自动缩进，IDLE 只负责把它显示出来。
- 表达式语句回显结果（蓝色），声明（`*` / `**` / `***`）、赋值、import 静默。
- 错误排版就是官方 `errors.py` 的排版：

```
>>> 1 +;

·语法错误
  ·意外的标记: ;
·代码
1 +;
   ^

>>> not_defined_xyz;

·运行时错误
  ·变量未定义: not_defined_xyz
```

- 程序用 `>>` 读取输入时，Shell 显示 `输入 > ` 并把内容交给子进程 stdin，
  不会和命令行本身冲突（通过词法扫描判断源码里是否含 `>>` 来触发）。
- `↑` / `↓` 或 `Alt+P` / `Alt+N` 回溯历史命令（历史由 IDLE 本地维护）。
- 输出区只读，程序输出永远插在末尾，不会覆盖你正在输入的内容。

**关于 Ctrl+C**：官方 REPL 在键盘中断时会按 `main.py` 的逻辑退出进程，
因此 IDLE 中断后会提示"Shell 进程已退出，正在重新启动…"并自动重连。
这与终端里按 Ctrl+C 的行为一致，代价是中断后变量会丢失。

工作目录决定 import 的解析基准，默认项目根目录，可通过
`Shell → 设置工作目录…` 修改（会重启 Shell）。

## 编辑器窗口

- 行号栏、语法着色（关键字/字符串/数字/注释/标识符）。
- 自动缩进：回车继承上一行缩进，行尾为 `{` `[` `(` 时额外加 4 空格；
  `Tab` / `Shift+Tab` 整块缩进；`Backspace` 一次退 4 空格。
- 自动配对括号；输入闭括号时若右侧已有相同字符则跳过。
- 标题栏用 `*` 标记未保存的修改，关闭或退出时逐个询问。
- 状态栏显示 行/列、总行数、文件路径、是否已修改。

## 运行相关

F5 / 检查语法 / 编译同样走官方 `main.py`，不是自己实现的编译：

| 命令 | 快捷键 | 底层命令 |
| --- | --- | --- |
| 运行模块 | `F5` | `main.py -c <tmp>.tscc <src>.tsuc` 然后 `main.py -r <tmp>.tscc` |
| 检查语法 | `Alt+X` | `main.py -c <tmp>.tscc <src>.tsuc`（产物随后删除） |
| 编译为 .tscc | `Ctrl+Shift+C` | `main.py -c <输出.tscc> <src>.tsuc` |
| 中断执行 | `Ctrl+C` | 向子进程发 CTRL_C_EVENT |
| 重启 Shell | `Ctrl+F6` | 重启 `main.py -s` 进程 |

> 注意 `main.py` 的参数顺序是 `-c <输出> <输入>`，输出在前。

编辑器未保存时，缓冲区会先落成 `<原名>._idle_<pid>.tsuc` 放在**源文件同目录**
（保证相对 import 仍可解析），任务结束后自动删除，不污染你的源码。

完整快捷键：

```
Ctrl+N  新建文件        Ctrl+O  打开文件
Ctrl+S  保存            Ctrl+W  关闭窗口
Ctrl+Z  撤销            Ctrl+Y  重做
Ctrl+X  剪切            Ctrl+C  复制（Shell 中为中断）
Ctrl+V  粘贴            Ctrl+A  全选
Ctrl+F  查找            F5      运行模块
Alt+X   检查语法        Ctrl+Shift+C  编译为 .tscc
Ctrl+F6 重启 Shell      Ctrl+Q  退出
↑ / ↓   历史命令        Alt+P / Alt+N  上一条 / 下一条
```

## 实现要点

**终端式子进程。** `runner.Proc` 负责起进程、并发读 stdout/stderr、写 stdin。
输出按块读取（`read1`）而不是按行读，否则没有换行结尾的 `>>> ` 提示符会被卡住；
退出由专门的 `wait()` 线程报告（流 EOF 时 `poll()` 可能尚未回收完进程）。
每个进程带一个代次号，重启后旧进程残留的输出与退出事件会被丢弃。

**提示符识别。** 官方 REPL 在非 tty 下用 `input(prompt)`，提示符会写进 stdout。
IDLE 收到输出后检查最后一行是否匹配 `^(>>>|\.\.\.) *$`，是就改用 prompt 配色，
并把输入起点标记在它后面。

**不依赖 prompt_toolkit 做界面。** 输入内容的语法高亮由 `IDLE/lexer.py` 自己做
（与 `compile/highlighter.py` 的 `scan_spans` 保持一致）。子进程侧仍需要
prompt_toolkit，因为 `runtime/repl.py` 在导入时就依赖它。

## 已知问题

解释器层面的问题都属于语言本身，与 IDLE 无关（用官方 `main.py` 直接跑同样复现）。
本 worktree（`7531c24`）早于主检出的 `f92746c`（"回归修复与历史特性改动"），
后者重写了 `runtime/interpreter.py`，链表缺陷已在那里修掉。

在旧版本上 `standard.output << "hello";` 只会输出 `h`，根因是
`runtime/interpreter.py` 的 `eval_assignment` 对「右操作数为标识符」的赋值
一律深拷贝：

1. `none` 单例被 `_deep_copy` 复制成空实例，`_list_to_py` 的
   `node is not none` 判定失效，链表遍历提前终止；
2. `list.append` 里 `self.head = node; self.tail = node;` 各自拿到一份副本，
   `self.tail.next = node` 写到另一份上，链表根本连不起来。

已验证的修复方向（会改动语言语义，未擅自提交）：
`_deep_copy` 遇到 `none` 单例直接返回原值；成员赋值 / 下标赋值不做深拷贝。
