# 教程：快速上手

> 对标 [Python Tutorial](https://docs.python.org/zh-cn/3.16/tutorial/index.html)

---

## 1. 启动解释器

### 1.1 安装

```bash
# Windows 安装包
# 下载：https://github.com/tanex-script/tanex-script/releases/latest/TanexScript_Setup.exe

# 或从源码构建（需 Python 3.10+）
git clone https://github.com/tanex-script/tanex-script.git
cd tanex-script/核心
pip install -r requirements.txt
```

### 1.2 运行模式

| 命令 | 说明 |
|------|------|
| `python -m tanex run hello.tsuc` | 直接运行源码（内部自动编译） |
| `python -m tanex compile hello.tsuc -o hello.tscc` | 编译为 `.tscc` |
| `python -m tanex run hello.tscc` | 运行编译产物 |
| `python -m tanex repl` | 启动交互模式 |

### 1.3 REPL 交互模式

```bash
$ python -m tanex repl
Tanex Script REPL v1.0.0 - 输入 :q 退出, :h 帮助
>>> `1` + `2`;
# => `3`
>>> import "standard" = *std;
>>> std.standard_output << "Hello\n";
Hello
# => "Hello\n"
>>> :q
Bye!
```

**REPL 特有常量**：
- `path = none`（无脚本文件）
- `program_path` = 解释器安装目录
- `args = []`（通常为空）

---

## 2. 入门示例

### 2.1 Hello World

**文件 `hello.tsuc`**：
```tanex script
@ # Hello World 示例程序 #;
import "standard" = *std;
std.standard_output << "Hello, Tanex Script!\n";
```

**运行**：
```bash
python -m tanex run hello.tsuc
# =>
# Hello, Tanex Script!
```

### 2.2 变量与基本类型

```tanex script
# 整数（原类型，无符号任意精度）
* a = `42;
* b = `1_000_000;

# 数字（精确十进制，单引号包裹）
* pi = '3.14159;
* neg = '-2.5;

# 字符串（双引号包裹，支持转义）
* name = "Tanex";
* multi = "Line 1\nLine 2\tTab";

# 布尔
* flag = true;
* empty = false;

# 空值
* nothing = none;
```

### 2.3 列表与代码块

```tanex script
# 列表（方括号，逗号分隔，尾部逗号自动填充 none）
* nums = [`1`, `2`, `3`];
* mixed = [`1`, "hi", true, none];
* empty_list = [];

# 代码块（花括号，惰性求值，产生 code 类型值）
* block = {
    std.standard_output << "in block\n";
    $ `42;  # 返回值
};
block();  # 执行代码块 => 输出 "in block", 返回 `42
```

---

## 3. 基础编程

### 3.1 表达式与语句

- **语句以分号 `;` 结尾**，换行只是空白，**无续行符**
- **反斜杠 `\` 是整除运算符**，行尾写 `\` 会被解析为整除

```tanex script
# 正确：自由换行
a = `10
+ `20
+ `30;  # => `60 #;

# 错误：行尾 \ 被解析为整除
# a = `10 \   # 整除左操作数
# `2;         # 右操作数，整体等价 a = `10 \ `2 结果 5
```

### 3.2 算术运算

```tanex script
`10` + `3`;      # => `13 (Integer) #;
`10` - `3`;      # => `7 #;
`10` * `3`;      # => `30 #;
`10` / `3`;      # => '3.3333333333' (Number，精确十进制) #;
`10` \ `3`;      # => `3 (整除) #;
`10` % `3`;      # => `1 (取余) #;
`2` ^ `10`;      # => `1024 (幂) #;

# Number 精确十进制
'0.1' + '0.2';   # => '0.3' (无浮点误差) #;
'2.7' + '2.3';   # => '5.0' #;
```

### 3.3 比较与逻辑

```tanex script
`3` < `5`;        # => true #;
`3` == `3`;       # => true #;
true && false;    # => false (短路) #;
true || false;    # => true (短路) #;
! true;           # => false #;
`1` < `2` ? "yes" : "no";  # => "yes" (三目) #;
```

### 3.4 字符串操作

```tanex script
"hello" + " world";  # => "hello world" (拼接) #;
"hi" * `3`;          # => "hihihi" (重复) #;
"hello"[`1`];        # => `101 ('e' 码点) #;
```

### 3.5 列表操作

```tanex script
* l = [`1`, `2`, `3`];
l.append(`4`);       # l => [`1`, `2`, `3`, `4`]
l[`0`];              # => `1 #;
l.size;              # => `4 #;
`2` in l;            # => true #;
```

---

## 4. 控制流

> **核心设计**：所有控制结构均为**函数调用**，参数含代码块（`code` 类型）。

### 4.1 条件分支：`if`

```tanex script
if(`1` < `2`, {
    std.standard_output << "true\n";
}, {
    std.standard_output << "false\n";
});
# => true #;
```

### 4.2 遍历循环：`for`

```tanex script
for(* i, [`1`, `2`, `3`, `4`, `5`], {
    std.standard_output << i;
    std.standard_output << "\n";
});
# => 1 2 3 4 5 (各占一行) #;
```

### 4.3 条件循环：`while`

```tanex script
* cnt = `0;
while({ $ cnt < `3; }, {
    std.standard_output << cnt;
    std.standard_output << "\n";
    cnt = cnt + `1;
});
# => 0 1 2 #;
```

### 4.4 定次循环：`cycle`

```tanex script
cycle(`3`, {
    std.standard_output << "!\n";
});
# => ! x3 #;
```

### 4.5 循环符：`$$`（收集 `$` 返回值）

```tanex script
* i = `1;
{ $ i <= `5; } $$ { $ i; i = i + `1; };
# => [`1`, `2`, `3`, `4`, `5`] #;
```

### 4.6 跳出控制

```tanex script
# break - 退出循环
for(* i, [`1`, `2`, `3`, `4`], {
    i == `3 ? { break; } : {};
    std.standard_output << i;
});
# => 1 2 #;

# contiune - 跳过本轮
* i = `0;
{ $ i < `5; } $$ {
    i = i + `1;
    i == `3 ? { contiune; } : {};
    $ i;
};
# => [`1`, `2`, `4`, `5`] (跳过 3) #;
```

---

## 5. 函数

### 5.1 命名函数

```tanex script
*** add = [*a, *b] => { $ a + b; };
add(`3`, `4`);  # => `7 #;
```

### 5.2 匿名函数

```tanex script
* fn = [*x] => { $ x * `2; };
fn(`5`);  # => `10 #;
```

### 5.3 参数形式

```tanex script
*** demo = [
    * required,              # 必填
    [* opt, integer, `0]     # 可选，带类型注解与默认值
] => { $ required + opt; };

demo(`10`);      # => `10 #;
demo(`10`, `5`); # => `15 #;
```

### 5.4 参数传地址（副作用）

```tanex script
*** modify = [*x] => { x = `999; };
* a = `1;
modify(a);
a;  # => `999 (外部变量被修改) #;
```

### 5.5 闭包

```tanex script
*** make_counter = [*init] => {
    * count = init;
    [*] => { count = count + `1; $ count; };
};
* c1 = make_counter(`0);
* c2 = make_counter(`100);
c1();  # => `1 #;
c1();  # => `2 #;
c2();  # => `101 (独立环境) #;
```

---

## 6. 模块系统

### 6.1 `import` vs `->`

| 形式 | 句柄 | 作用域污染 | 典型场景 |
|------|------|------------|----------|
| `import "lib"` | ✅ `Library` 常量 | 无 | 标准用法 |
| `-> "lib"` | ❌ | 是(展开顶层声明) | 小工具库、快速引用 |

### 6.2 常用引入形式

```tanex script
# 单条引入
import "standard" = *std;
-> "standard";

# 命名引入（仅 import，必须 *name）
import "maths.tsuc" = *m;

# 列表批量引入
import ["maths", "random"];           # 绑定到 maths、random
import ["maths", "random"] = [*m, *r]; # 绑定到 m、r

# 动态路径（运行时求值）
import "lib_" + suffix + ".tsuc";
```

### 6.3 可见性控制：`public`

```tanex script
# lib.tsuc
*** internal = [*x] => { $ x + `1; };
*** public_api = [*x] => { $ x * `2; };
*** public = ["public_api"];  # 仅导出 public_api
```

```tanex script
# 用户代码
import "lib" = *lib;
lib.public_api(`5`);  # => `10 ✅ #;
# lib.internal(`5`);  # ❌ 报错：成员不存在
```

---

## 7. 错误处理

### 7.1 尝试结构：`|`

```tanex script
{ <- error{"divide by zero"}; } | *e : {
    std.standard_output << "caught: " + e.what;
} : {
    std.standard_output << "no error\n";
};
# => caught: divide by zero #;
```

### 7.2 错误对象

```tanex script
* err = error{"msg"};
err.what;     # => "msg" #;
err.throw();  # 重新抛出
```

### 7.3 警告（不结束程序）

```tanex script
warning{"deprecated"}.throw();  # 打印警告继续执行
```

---

## 8. 注解与文档

```tanex script
# 标识符注解
@ my_func # 这是文档 #;

# 文件级注解
@ # 模块文档 #;

# 成员级注解
@ String.length # 返回长度 #;

# 读取（有作用域）
?? my_func;           # 当前作用域
?? standard.for;      # 跨库读取
?? String.length;     # 成员级
```

---

## 9. 进阶预览

### 9.1 自定义类型与运算符重载

```tanex script
* Vec2 = type_type{};
*** Vec2.initialize = [* self, * x, * y] => { self.x = x; self.y = y; };
*** Vec2.string = [* self] => { $ "Vec2(" + self.x.string() + ", " + self.y.string() + ")"; };
*** Vec2.addition = [* self, * other] => { $ Vec2{self.x + other.x, self.y + other.y}; };

* v1 = Vec2{`1`, `2`};
* v2 = Vec2{`3`, `4`};
std.standard_output << (v1 + v2);  # => Vec2(4, 6) #;
```

### 9.2 地址操作

```tanex script
* x = `100;
* addr = /x;     # 取地址
*addr;           # => `100 (解地址读取) #;
*addr = `200;   # x 变为 `200
```

### 9.3 动态 Import

```tanex script
* plugin = "plugin_" + user_input;
import plugin;  # 运行时根据输入加载不同插件
```

---

## 下一步

- [教程：深入控制流](controlflow.md) — `if`/`for`/`while`/`cycle`/`$$` 详细语义
- [教程：函数与模块](functions_modules.md) — 高阶函数、模块组织、public 控制
- [语言参考：词法](reference/lexical.md) — 完整词法规范
- [标准库：maths](library/maths.md) — 数学函数完整条目