# 教程：函数与模块

> 对标 [Python Tutorial - Functions](https://docs.python.org/zh-cn/3.16/tutorial/controlflow.html#defining-functions)、[Modules](https://docs.python.org/zh-cn/3.16/tutorial/modules.html)

---

## 1. 函数定义

### 1.1 命名函数

```tanex script
*** 函数名 = [参数列表] => { 函数体 };
```

- `***` 声明常量标识符，绑定函数值（不可重新赋值）
- 函数值为带参数信息的 `code` 类型

### 1.2 参数列表语法

| 形式 | 语法 | 说明 |
|------|------|------|
| 必填参数 | `*name` | 传地址参数，在函数作用域声明同名变量 |
| 可选参数 | `[*name, 类型注解, 默认值表达式]` | 类型注解运行时不强制，默认值调用时求值 |

```tanex script
# 无参
*** greet = [] => { $ "Hello!"; };

# 必填参数
*** add = [*a, *b] => { $ a + b; };

# 可选参数带默认值
*** greet2 = [[*name, string, "World"]] => { $ "Hello, " + name + "!"; };

# 混合参数
*** demo = [*required, [*opt, integer, `0], [*flag, boolean, false]] => { ... };
```

### 1.3 函数体与返回值

```tanex script
*** fn = [*x] => {
    * y = x * `2;      # 局部变量
    $ y;               # 显式返回（提前结束）
    # 后续代码不执行
};

*** implicit = [*x] => { x * `2; };  # 隐式返回最后一句值
```

| 返回方式 | 语法 | 行为 |
|----------|------|------|
| 显式返回 | `$ expr` / `return expr` | 提前结束，携带值返回 |
| 隐式返回 | 无显式 `$` | 最后一条语句的值作为返回值 |
| 空函数 | `{;}` | 返回 `none` |

### 1.4 匿名函数

```tanex script
* fn = [*x] => { $ x * `2; };  # 赋值给变量
[*x, *y] => { $ x + y; }       # 直接作为实参传递
```

- 语法：`[参数列表] => { 函数体 }`
- 产生带参数信息的 `code` 值，可调用、传递、存储

---

## 2. 参数传递机制

### 2.1 传地址

**核心规则**：所有参数**传地址**（Call by Address）。

```tanex script
*** modify = [*x] => { x = `999; };
* a = `1;
modify(a);
a;  # => `999 (外部变量被修改) #;
```

- 调用方为每个实参在**调用方地址空间**分配临时存储单元
- 被调函数在**新建子作用域**声明同名变量，绑定到传入地址
- 函数内对参数赋值直接修改调用方对应变量

### 2.2 参数绑定顺序与默认值

1. 实参按位置顺序与形参一一对应
2. 实参数 < 形参数：缺失位置按**默认值表达式求值**补齐；无默认值补 `none`
3. 实参数 > 形参数：报错“参数过多”
4. 默认值求值发生在**调用时**，按参数顺序左到右求值

```tanex script
*** fn = [*a, [*b, integer, `10], [*c, integer, `20]] => { $ a + b + c; };
fn(`1`);        # => `31 (b=10, c=20) #;
fn(`1`, `2`);   # => `23 (b=2, c=20) #;
fn(`1`, `2`, `3`); # => `6 #;
# fn(`1`, `2`, `3`, `4`); # 报错：参数过多
```

### 2.3 无可变参数

当前版本不支持 `*args`、`**kwargs`。变长参数约定传入 `List` 并在函数内遍历。

```tanex script
*** sum_all = [*list] => {
    * total = `0;
    for(* item, list, { total = total + item; });
    $ total;
};
sum_all([`1`, `2`, `3`, `4`]);  # => `10 #;
```

---

## 3. 作用域与闭包

### 3.1 词法作用域

- 函数创建时捕获**当前作用域引用**（定义时作用域）
- 函数调用时基于捕获的作用域建立**新子作用域**
- 变量查找：当前层 → 父层 → 祖先层 → 顶层

### 3.2 闭包捕获外部变量

```tanex script
*** make_counter = [*init] => {
    * count = init;  # 在 make_counter 局部作用域
    [*] => {         # 匿名函数捕获外层作用域
        count = count + `1;
        $ count;
    };
};

* c1 = make_counter(`0);
* c2 = make_counter(`100);
c1();  # => `1 #;
c1();  # => `2 #;
c2();  # => `101 (独立环境) #;
```

- 捕获的是**变量地址**（存储单元），非值快照
- 外层修改对闭包可见，闭包内修改对外层可见
- 每次调用 `make_counter` 创建新的 `count` 存储单元

### 3.3 上级访问 `~`

```tanex script
* x = `1;
{
    * x = `2;
    ~x;    # => `1 (父作用域的 x) #;
    ~~x;   # => `1 (祖父层) #;
}
```

- `~expr` 在**父作用域**求值 `expr`
- 可穿透闭包层级访问外层变量

---

## 4. 高阶函数模式

### 4.1 函数作为值

```tanex script
* fns = [add, sub, mul];  # 函数列表
fns[`0`](`5`, `3`);       # => `8 (动态调用) #;

*** apply = [*fn, *x, *y] => { $ fn(x, y); };
apply(add, `10`, `20`);   # => `30 #;
```

### 4.2 柯里化

```tanex script
*** curry_add = [*a] => {
    [*b] => { $ a + b; };
};
* add5 = curry_add(`5`);
add5(`3`);  # => `8 #;
```

### 4.3 回调与高阶工具

```tanex script
*** map = [*list, *fn] => {
    * result = List{};
    for(* item, list, { result.append(fn(item)); });
    $ result;
};

* doubled = map([`1`,`2`,`3`], [*x] => { $ x * `2; });
# => [`2`, `4`, `6`] #;

*** filter = [*list, *pred] => {
    * result = List{};
    for(* item, list, { pred(item) ? { result.append(item); } : {}; });
    $ result;
};

* evens = filter([`1`,`2`,`3`,`4`], [*x] => { $ x % `2 == `0; });
# => [`2`, `4`] #;
```

### 4.4 管道操作符 `|>`

```tanex script
`5` |> [*x] => { $ x * `2; } |> [*y] => { $ y + `1; };  # => `11 #;

# 等价于嵌套调用
[*y] => { $ y + `1; }(([*x] => { $ x * `2; })(`5));
```

---

## 5. 递归

### 5.1 直接递归

```tanex script
*** factorial = [*n] => {
    n <= `1 ? { $ `1; } : { $ n * factorial(n - `1); };
};
factorial(`5`);  # => `120 #;
```

### 5.2 相互递归

```tanex script
*** even = [*n] => { n == `0 ? { $ true; } : { $ odd(n - `1); }; };
*** odd = [*n] => { n == `0 ? { $ false; } : { $ even(n - `1); }; };
even(`4`);  # => true #;
```

### 5.3 递归深度限制

- 无尾调用优化（TCO）
- 默认递归限制 ~1000 层（可配置 `recursion_limit`）
- 深度递归建议改用 `$$` 循环或 `cycle`

```tanex script
# 尾递归改写为循环
*** fact_iter = [*n, *acc] => {
    n <= `1 ? { $ acc; } : { $ fact_iter(n - `1, n * acc); };
};
*** factorial = [*n] => { $ fact_iter(n, `1); };
```

---

## 6. 模块系统

### 6.1 文件后缀

| 后缀 | 含义 |
|------|------|
| `.tsuc` | 源码（Uncompiled Code） |
| `.tscc` | 编译产物（Compiled Code，JSON AST） |
| `.tscl` | 编译库（Compiled Library，二进制打包） |
| 目录/ | 库文件夹（含 `main.tsuc` 等） |

### 6.2 `import` vs `->`

```tanex script
# import：生成 Library 句柄，命名空间隔离
import "standard" = *std;
std.standard_output << "hi\n";

# ->：直接展开顶层声明到当前作用域
-> "standard";
standard_output << "hi\n";  # 直接可用
```

| 特性 | `import` | `->` |
|------|----------|------|
| 产生句柄 | ✅ | ❌ |
| 作用域污染 | 无 | 是 |
| 命名引入 | ✅ | ❌ |
| 列表批量 | ✅ | ✅(无命名) |
| 注解隔离 | ✅ | 合并到全局 |

### 6.3 引入形式完备

```tanex script
# 单条引入
import "standard";           # 绑定到 standard
-> "standard";               # 展开所有顶层声明

# 命名引入（仅 import，必须 *name）
import "maths.tsuc" = *m;        # 库实例地址引用绑定到 m
import "lib_" + suffix = *mylib; # 动态路径 + 命名

# 列表批量引入
import ["maths", "random"];           # 绑定到 maths、random
import ["maths", "random"] = [*m, *r]; # 绑定到 m、r
-> ["maths", "random"];               # 依次展开

# 动态路径（运行时求值）
import "lib_" + suffix + ".tsuc";
```

### 6.4 路径解析规则

1. **静态字符串字面量**：预编译阶段解析绝对路径、编译 `.tsuc`→`.tscc`、收集依赖
2. **动态表达式**：运行时求值路径、动态加载
3. **歧义消除**：同名多内容报错，建议加后缀（`/`、`.tsuc`、`.tscc`、`.tscl`）
4. **标准库优先**：裸名 `"standard"` 优先解析安装目录标准库

### 6.5 可见性控制：`public`

```tanex script
# lib.tsuc
*** internal_helper = [*x] => { $ x + `1; };
*** public_api = [*x] => { $ x * `2; };
*** public = ["public_api"];  # 仅导出 public_api
```

```tanex script
# 用户代码
import "lib" = *lib;
lib.public_api(`5`);   # => `10 ✅ #;
# lib.internal_helper(`5`);  # ❌ 报错：成员不存在
```

- 仅文件级有效（模块顶层声明）
- 未声明 `public` 时默认全部公开
- `->` 引入不受 `public` 限制

### 6.6 库注解隔离

```tanex script
# lib.tsuc
@ my_func # 库内文档 #;
*** my_func = [] => { $ `1; };

# 用户代码
import "lib" = *lib;
?? my_func;        # => none (顶层无此注解) #;
?? lib.my_func;    # => "库内文档" ✅ #;
?? lib;            # 文件级注解
```

- `import`：库注解写入独立空间，跨库读取需 `?? lib.member`
- `->`：库注解合并到当前顶层 `annotations`

---

## 7. 模块组织最佳实践

### 7.1 目录结构

```
my_lib/
  main.tsuc          # 入口，含 public 列表
  core.tsuc          # 核心实现
  utils/
    string.tsuc
    math.tsuc
  _internal.tsuc     # 下划线开头，不在 public 中，内部使用
```

### 7.2 main.tsuc 示例

```tanex script
@ # My Library v1.0 #;

*** public = ["public_api", "Config"];

import "./core" = *core;
import "./utils/string" = *str;

*** public_api = [*x] => { core.process(str.normalize(x)); };

# 导出类型
*** Config = core.Config;
```

### 7.3 导入策略

```tanex script
# 推荐：显式命名引入，避免命名冲突
import "standard" = *std;
import "maths" = *math;
import "encoding.ascii" = *ascii;

# 避免：裸 import 污染命名空间
# import "standard";  # 绑定到 standard，可能冲突
```

---

## 8. 常见错误与调试

### 8.1 参数副作用陷阱

```tanex script
# ❌ 意外修改外部变量
*** process = [*list] => {
    for(* item, list, { item = `0; });  # 修改列表元素（若 item 为引用）
};

# ✅ 明确复制
*** process = [*list] => {
    * copy = List{};
    for(* item, list, { copy.append(item); });
    # 对 copy 操作
};
```

### 8.2 闭包循环变量捕获

```tanex script
# ❌ 所有函数捕获同一个 i，最终值为最后值
* funcs = [];
for(* i, [`1`,`2`,`3`], {
    funcs.append([*] => { $ i; });
});
funcs[`0`]();  # => `3 (非预期) #;

# ✅ 在循环体内创建新绑定
* funcs = [];
for(* i, [`1`,`2`,`3`], {
    * captured = i;  # 新地址
    funcs.append([*] => { $ captured; });
});
funcs[`0`]();  # => `1 ✅ #;
```

### 8.3 递归栈溢出

```tanex script
# ❌ 深度递归溢出
*** sum = [*n] => { n == `0 ? `0 : n + sum(n - `1); };
sum(`10000`);  # 可能溢出

# ✅ 改用循环
*** sum = [*n] => {
    * total = `0;
    { $ n > `0; } $$ { total = total + n; n = n - `1; };
    $ total;
};
```

---

## 下一步

- [语言参考：函数](../reference/functions.md) — 完整语法语义规范
- [语言参考：模块](../reference/modules.md) — import/->、路径解析、初始化顺序
- [标准库：standard 函数式工具](../library/standard.md) — `map`/`filter`/`reduce`/`pipe` 等
- [专题指南：类型设计模式](../howto/type_design.md) — 封装、继承、运算符重载实战