# 错误处理

> 对标 [Python Exceptions](https://docs.python.org/zh-cn/3.16/reference/compound_stmts.html#try-statements)
>
> Tanex Script 错误处理基于**表达式级尝试结构** `left | *err : catch : else`，配合一元 `<-` 抛出。无 `try/catch` 语句块语法。

---

## 1. 错误类型层级

| 类型 | 来源 | 特征 | 处理方式 |
|------|------|------|----------|
| **用户抛出错误** | `<- error{...}` | `Error` 实例，含 `what`、`throw()` | `|` 捕获，`catch` 块处理 |
| **用户抛出警告** | `<- warning{...}` | `Warning` 实例，`throw()` 不结束程序 | `|` 捕获，`catch` 块处理 |
| **运行时内部错误** | 变量未定义、成员不存在、类型不支持运算、除零(整除/取余)、跳出层数不足等 | 运行时构造错误信息字符串 | `|` 捕获(错误值为信息字符串或 `Error` 对象) |
| **编译期错误** | 语法错误、类型错误(静态)、导入歧义 | 编译器报错，不产生 `.tscc` | 无法用 `|` 捕获(编译阶段失败) |

### 1.1 错误对象成员

| 成员 | 类型 | 说明 |
|------|------|------|
| `what` | `String` | 错误信息文本 |
| `throw()` | 方法 | 重新抛出：`Error.throw()` 等价 `<- self;`；`Warning.throw()` 打印警告继续 |

---

## 2. 错误构造与抛出

### 2.1 `error{...}` / `warning{...}`

- **语法**：`error{"message"}`、`warning{"message"}`(类似类型构造，实为引导库提供的构造函数)
- 返回对应类型实例

### 2.2 `<-` 抛出

- **签名**：`<- expression`
- 求值 `expression` 得值 `v`，抛出内部 `ErrorSignal(v)`
- 传播规则：向上穿透函数调用、代码块执行、控制流函数，直到遇到 `|` 尝试结构或顶层入口

```tanex script
<- error{"invalid argument"};           # 抛出 Error
<- warning{"deprecated: use v2"};       # 抛出 Warning
<- "raw string error";                  # 抛出任意值(字符串)
```

---

## 3. 尝试结构详解

> **签名**：`left | *err : catch_block : else_block`  
> 详见 [表达式：尝试结构](expressions.md#尝试结构-lefterr--catch--else)

### 3.1 执行语义步骤

1. 执行 `left`(任意表达式)
2. **成功**：
   - 若有 `else_block`：执行 `else_block`，返回其值
   - 无 `else_block`：返回 `left` 的值
3. **报错**：
   - 捕获错误值 `err_val`(`<-` 抛出的值、运行时错误信息等)
   - 在**当前作用域**声明/覆盖 `*err` 绑定 `err_val`
   - 执行 `catch_block`，返回其值
4. `catch_block`/`else_block` 内部异常可被外层 `|` 捕获(嵌套捕获)

### 3.2 错误绑定作用域

- `*err` 在**尝试结构所在作用域**声明/覆盖
- `catch_block` 可直接访问 `err`
- `catch_block` 执行完毕后，`err` 变量保留在作用域中(可后续访问)

```tanex script
{ <- error{"oops"}; } | *e : { $ e.what; } : { $ "ok"; };
e.what;  # => "oops" (catch 结束后仍可访问) #;
```

### 3.3 成功分支可选

```tanex script
# 无 else 分支
{ $ "success"; } | *e : { $ "caught: " + e.what; };  # => "success" #;

{ <- error{"fail"}; } | *e : { $ "caught: " + e.what; };  # => "caught: fail" #;
```

---

## 4. 标准库错误分类与错误码约定

> Tanex Script **无统一整数错误码体系**。错误以**值**形式携带信息，主要通过 `Error.what` 文本区分。标准库约定以下错误消息前缀：

| 前缀 | 含义 | 示例 |
|------|------|------|
| `arg_error:` | 参数类型/数量/值不合法 | `arg_error: expected integer, got string` |
| `index_error:` | 下标越界 | `index_error: index 5 out of range [0, 3)` |
| `type_error:` | 类型不支持运算/操作 | `type_error: Type has no addition special member` |
| `import_error:` | 模块导入失败 | `import_error: ambiguous path 'lib'` |
| `const_error:` | 常量修改尝试 | `const_error: cannot assign to constant` |
| `arith_error:` | 算术域错误(整除/取余除零) | `arith_error: division by zero in integer divide` |
| `control_error:` | 控制流错误(跳出层数不足等) | `control_error: multi-level return depth exceeded` |

**建议**：用户代码抛出错误时遵循前缀约定，便于 `catch` 块按前缀分类处理。

---

## 5. 顶层未捕获错误处理

- 程序执行过程中抛出错误且**无 `|` 捕获**到达顶层入口：
  1. 打印错误信息到 stderr(格式：`Error: <what>` 或 `Runtime Error: <message>`)
  2. 进程**非零退出**(退出码 1)
- 顶层显式 `$ n` / `return n`：
  - `n` 为 `Integer`：以 `n` 为退出码正常退出
  - `n` 非 `Integer`：报错“顶层返回值必须为整数”，退出码 1
- 正常结束(无顶层返回、无错误)：退出码 0

---

## 6. 错误处理最佳实践

```tanex script
# 1. 细粒度捕获，避免吞掉无关错误
{ risky_operation(); } | *e : {
    e.what.startswith("arg_error:") ? { handle_arg_error(e); } : {
        e.what.startswith("import_error:") ? { handle_import_error(e); } : {
            e.throw();  # 重新抛出未知错误
        }
    };
};

# 2. 资源清理用 else 分支(成功时执行)
{ acquire(); risky(); release(); } | *e : { release(); e.throw(); } : { release(); };

# 3. 警告不中断流程
{ <- warning{"slow path"}; } | *w : { std.standard_output << "WARN: " + w.what; } : { $ "ok"; };
```

---

## 7. 控制流信号 vs 错误

以下**不是错误**，不被 `|` 捕获，由解释器内部信号处理：

| 信号 | 触发语法 | 处理位置 |
|------|----------|----------|
| `BreakSignal` | `break;` | `$$` 循环 |
| `ContinueSignal` | `contiune;` | `$$` 循环 |
| `ReturnSignal` | `$ expr` / `return expr` | 函数调用、代码块 |
| `ErrorSignal` | `<- expr` | `|` 尝试结构 |

---

## 相关链接

- [表达式：尝试结构](expressions.md#尝试结构-lefterr--catch--else) — 语法与语义
- [语句：零元运算符](statements.md#零元运算符语句) — `break`/`contiune`
- [语言参考：运行时内部](runtime_internals.md) — 控制流信号机制
- [标准库：random](../library/random.md) — 错误示例
- [教程：错误处理](../tutorial/controlflow.md#6-错误处理控制流) — 入门示例