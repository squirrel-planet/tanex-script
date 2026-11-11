# 教程：深入控制流

> 对标 [Python Tutorial - Control Flow](https://docs.python.org/zh-cn/3.16/tutorial/controlflow.html)

---

## 1. `if` 条件分支

### 1.1 基本形式

```tanex script
if(条件, {成立代码块}, {不成立代码块});
```

- **条件**：任意表达式，按真值判定规则求值
- **成立代码块**：`code` 类型，条件为真时执行
- **不成立代码块**：`code` 类型，条件为假时执行（可选，默认 `{;}`）

### 1.2 真值判定规则

| 值类型 | 真值 |
|--------|------|
| `Integer` | 非零为真，零为假 |
| `Number` | 非零为真（`front != 0 || back != 0`） |
| `String` | 非空为真，空串为假 |
| `List` | 非空为真，空列表为假 |
| `Boolean` | `true` 为真，`false` 为假 |
| `None` | 恒假 |
| `NaN` | 恒假 |
| `Infinite` | 恒真 |
| 实例/类型/代码块/地址/库/函数 | 默认真（除非类型定义了 `boolean` 特殊成员） |

### 1.3 示例

```tanex script
# 基本用法
if(`5` > `3`, { $ "yes"; }, { $ "no"; });  # => "yes" #;

# 省略 else 分支
if(flag, { do_something(); });  # flag 为真时执行

# 嵌套 if
if(cond1, {
    if(cond2, { $ "both"; }, { $ "only1"; });
}, { $ "neither"; });
```

### 1.4 多重分支模式

```tanex script
# 使用三目运算符链式
* result = cond1 ? val1 : (cond2 ? val2 : val3);

# 或使用 if 嵌套
if(cond1, { $ val1; }, {
    if(cond2, { $ val2; }, { $ val3; });
});
```

---

## 2. `for` 遍历循环

### 2.1 签名

```tanex script
for(*循环变量声明, 可遍历值, {循环体代码块});
```

### 2.2 可遍历值类型

| 类型 | 遍历行为 |
|------|----------|
| `List` | 从头到尾依次取元素 |
| `String` | 逐字符取码点 (`Integer`) |
| 有 `index` + `size` 的实例 | 索引 0 到 `size-1` 调用 `index` |
| 有 `include` 的类型 | 不直接支持 `for`，需转为列表 |

### 2.3 循环变量声明

- 必须带 `*` 前缀：`* i`、`* item`
- 每轮迭代在**循环作用域**重新绑定（非重新声明）
- 循环结束后变量保留最后一次绑定的值

### 2.4 示例

```tanex script
# 遍历列表
for(* item, [`a`, `b`, `c`], {
    std.standard_output << item;
    std.standard_output << "\n";
});

# 遍历字符串（得字符码点）
for(* ch, "abc", {
    std.standard_output << ch;  # 输出 97, 98, 99
});

# 索引遍历（配合 range 模式需自行实现）
* i = `0;
for(* _, [`0`..`5`], {  # 假设有范围语法，实际需用 while 或自定义
    std.standard_output << i;
    i = i + `1;
});
```

### 2.5 `break` / `contiune` 在 `for` 中

```tanex script
# break 退出循环
for(* i, [`1`, `2`, `3`, `4`, `5`], {
    i == `3 ? { break; } : {};
    std.standard_output << i;
});
# => 1 2 #;

# contiune 跳过本轮
for(* i, [`1`, `2`, `3`, `4`], {
    i == `3 ? { contiune; } : {};
    std.standard_output << i;
});
# => 1 2 4 #;
```

> **实现原理**：标准库 `for` 基于 `$$` 循环符实现，`break`/`contiune` 为零元运算符，仅在 `$$` 内生效，`for` 通过封装使其生效。

---

## 3. `while` 条件循环

### 3.1 签名

```tanex script
while(条件代码块, 循环体代码块);
```

- **条件代码块**：每轮执行前求值，结果按真值判定
- **循环体代码块**：条件为真时执行

### 3.2 示例

```tanex script
* cnt = `0;
while({ $ cnt < `5; }, {
    std.standard_output << cnt;
    std.standard_output << "\n";
    cnt = cnt + `1;
});
# => 0 1 2 3 4 #;

# 无限循环需手动 break
while({ $ true; }, {
    * input = read_line();
    input == "quit" ? { break; } : { process(input); };
});
```

### 3.3 与 `for` 对比

| 特性 | `for` | `while` |
|------|-------|---------|
| 适用场景 | 已知遍历对象 | 条件动态判断 |
| 循环变量 | 自动绑定元素 | 自行管理 |
| 底层实现 | 基于 `$$` | 基于 `$$` |

---

## 4. `cycle` 定次循环

### 4.1 签名

```tanex script
cycle(次数, 循环体代码块);
```

- **次数**：`Integer` 或整数值 `Number`，非负
- 执行循环体指定次数

### 4.2 示例

```tanex script
cycle(`3`, { std.standard_output << "!\n"; });
# => ! x3 #;

# 配合循环变量（需自行管理）
* i = `0;
cycle(`5`, {
    std.standard_output << i;
    i = i + `1;
});
# => 0 1 2 3 4 #;
```

---

## 5. `$$` 循环符（核心循环构造）

### 5.1 签名

```tanex script
条件 $$ 循环体
```

- **条件**：左操作数，按以下规则求值判定真假
- **循环体**：右操作数，通常为代码块
- **返回**：收集所有 `$` 返回值形成 `List`

### 5.2 条件求值规则

| 条件类型 | 求值方式 |
|----------|----------|
| 实例且类型有 `initialize` | 调用 `initialize(实例自身)`，结果按真值判定 |
| 实例但类型无 `initialize` | 直接视为假，立即退出 |
| 代码块 | 作为条件函数执行，结果按真值判定 |
| 其他值 | 直接按真值判定规则判定 |

### 5.3 收集语义

- 循环体内 `$ expr`：**收集模式**——值追加到收集列表，**不**结束循环
- `break`：立即退出，返回已收集列表
- `contiune`：结束本轮迭代，重新求值条件
- 条件变假：退出，返回收集列表

### 5.4 示例

```tanex script
# 基础收集
* i = `1;
{ $ i <= `5; } $$ { $ i; i = i + `1; };
# => [`1`, `2`, `3`, `4`, `5`] #;

# 条件为代码块
* cnt = `0;
{ $ cnt < `3; } $$ { $ cnt; cnt = cnt + `1; };
# => [`0`, `1`, `2`] #;

# break 提前退出
* i = `1;
{ $ true; } $$ {
    i = i + `1;
    i > `3 ? { break; } : {};
    $ i;
};
# => [`2`, `3`] #;

# 实例条件（迭代器模式）
* iter = Iterator{data: [`a`,`b`,`c`]};
*** Iterator.initialize = [* self, * data] => { self.data = data; self.idx = `0; };
*** Iterator.initialize = [* self] => {  # 无参 initialize 用于 $$ 条件
    self.idx < self.data.size ? { $ true; } : { $ false; };
};
iter $$ {
    $ self.data.index(self.idx);
    self.idx = self.idx + `1;
};
# => [`a`, `b`, `c`] #;
```

---

## 6. 错误处理控制流

### 6.1 尝试结构

```tanex script
尝试表达式 | *错误变量 : 捕获代码块 : 成功代码块;
```

### 6.2 执行流程

1. 执行尝试表达式
2. **成功**：执行成功代码块（可选），返回其值
3. **报错**：绑定错误到错误变量，执行捕获代码块，返回其值

### 6.3 示例

```tanex script
# 基本捕获
{ risky(); } | *e : {
    std.standard_output << "Error: " + e.what;
} : { $ "OK"; };

# 无成功分支
{ <- error{"oops"}; } | *e : { $ e.what; };  # => "oops" #;

# 嵌套捕获
{ { <- error{"inner"}; } | *e : { $ "caught inner"; }; } | *e : { $ "caught outer"; };
# => "caught inner" #;

# 捕获后重新抛出
{ risky(); } | *e : {
    log(e);
    e.throw();  # 重新抛出给外层
};
```

---

## 7. 多层跳出：`$`（二元）

### 7.1 签名

```tanex script
层数 $ 返回值
```

- **层数**：正整数，向上穿透指定层数的代码块/函数边界
- `1 $ v` 等价 `return v` / `$ v`（一元）
- 层数不足报错

### 7.2 示例

```tanex script
*** outer = [] => {
    *** inner = [] => {
        2 $ "escaped";  # 跳出 inner + outer
    };
    inner();
    $ "not reached";
};
outer();  # => "escaped" #;
```

---

## 8. 最佳实践

### 8.1 选择合适的循环构造

| 场景 | 推荐 |
|------|------|
| 遍历列表/字符串 | `for(*x, list, {...})` |
| 条件循环、未知次数 | `while({cond}, {...})` |
| 固定次数 | `cycle(n, {...})` |
| 需收集结果列表 | `条件 $$ {体}` |
| 复杂迭代器 | 自定义类型 + `initialize` + `$$` |

### 8.2 避免常见错误

```tanex script
# ❌ 错误：for 中直接修改循环变量不影响原列表
for(* item, list, { item = `0; });  # 仅修改局部绑定

# ✅ 正确：通过下标修改
for(* i, list, { list[i] = `0; });  # 或用索引遍历

# ❌ 错误：while 条件忘记更新变量导致死循环
while({ $ x > `0; }, { do_something(); });  # x 未更新

# ✅ 正确：在循环体内更新条件相关变量
while({ $ x > `0; }, { do_something(); x = x - `1; });
```

### 8.3 性能提示

- `$$` 收集列表会分配内存，大量迭代考虑流式处理
- `for`/`while`/`cycle` 基于 `$$` 实现，有函数调用开销
- 紧凑循环优先用 `cycle` 或 `$$` 避免函数调用

---

## 下一步

- [教程：函数与模块](functions_modules.md) — 高阶函数、模块组织、public 控制
- [语言参考：表达式](reference/expressions.md) — 运算符优先级、求值顺序完整规范
- [语言参考：语句](reference/statements.md) — 声明、赋值、导入、零元、错误处理语句
- [标准库：standard 控制流辅助](library/standard.md) — `retry`/`times`/`until` 封装