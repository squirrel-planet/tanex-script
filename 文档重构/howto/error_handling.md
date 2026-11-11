# 错误处理模式

> Tanex Script 错误处理的实战模式与最佳实践。

---

## 1. 基础捕获模式

### 1.1 单一错误类型捕获

```tanex script
{ risky_operation(); } | *e : {
    std.standard_output << "Error: " + e.what;
} : { $ "OK"; };
```

### 1.2 按错误前缀分类处理

```tanexcript
{ risky(); } | *e : {
    e.what.startswith("arg_error:") ? { handle_arg(e); } : {
        e.what.startswith("import_error:") ? { handle_import(e); } : {
            e.what.startswith("type_error:") ? { handle_type(e); } : {
                e.throw();  # 重新抛出未知错误
            }
        }
    };
};
```

### 1.3 捕获后记录并重新抛出

```tanexscript
{ acquire(); risky(); release(); } | *e : {
    log_error(e);      # 记录日志
    release();         # 清理资源
    e.throw();         # 重新抛出给上层
} : { release(); };    # 成功也要清理
```

---

## 2. 资源管理模式

### 2.1 RAII 风格 (获取即初始化)

```tanexscript
*** with_resource = [*acquire_fn, *release_fn, *body_fn] => {
    * resource = acquire_fn();
    { body_fn(resource); } | *e : {
        release_fn(resource);
        e.throw();
    } : {
        release_fn(resource);
    };
};

# 使用
with_resource(
    { $ open_file("data.txt"); },      # 获取
    { *f => { close_file(f); } },      # 释放
    { *f => { process(f); } }          # 业务逻辑
);
```

### 2.2 多资源嵌套清理

```tanexscript
{ 
    * f1 = open("a.txt");
    { 
        * f2 = open("b.txt");
        { 
            process(f1, f2); 
        } | *e : { 
            close(f2); 
            e.throw(); 
        } : { close(f2); }; 
    } | *e : { 
        close(f1); 
        e.throw(); 
    } : { close(f1); }; 
};
```

### 2.3 标准库辅助 (计划中)

```tanexscript
# 标准库拟提供
std.with_open("file.txt", { *f => { process(f); } });
std.with_lock(mutex, { critical_section(); });
std.with_transaction(db, { *tx => { tx.execute(...); } });
```

---

## 3. 错误分类与自定义错误

### 3.1 标准错误前缀约定

| 前缀 | 含义 | 示例 |
|------|------|------|
| `arg_error:` | 参数类型/数量/值不合法 | `arg_error: expected integer, got string` |
| `index_error:` | 下标越界 | `index_error: index 5 out of range [0, 3)` |
| `type_error:` | 类型不支持运算/操作 | `type_error: Type has no addition special member` |
| `import_error:` | 模块导入失败 | `import_error: ambiguous path 'lib'` |
| `const_error:` | 常量修改尝试 | `const_error: cannot assign to constant` |
| `arith_error:` | 算术域错误(整除/取余除零) | `arith_error: division by zero in integer divide` |
| `control_error:` | 控制流错误(跳出层数不足等) | `control_error: multi-level return depth exceeded` |

### 3.2 自定义错误类型

```tanexscript
* ValidationError = type_type{};
*** ValidationError.initialize = [* self, * field, * msg] => {
    self.field = field;
    self.msg = msg;
};
*** ValidationError.string = [* self] => {
    $ "ValidationError(" + self.field + ": " + self.msg + ")";
};

*** validate_user = [*user] => {
    user.age < `0 ? { 
        <- error{"arg_error: age cannot be negative"}; 
    } : {};
    user.email == "" ? { 
        <- error{"arg_error: email is required"}; 
    } : {};
    $ true;
};
```

### 3.3 错误包装与上下文

```tanexscript
*** wrap_error = [*ctx, *fn] => {
    { fn(); } | *e : {
        <- error{ctx + ": " + e.what};
    };
};

wrap_error("database.connect", { connect_db(); });
# 若 connect_db 抛出 "connection refused"
# 捕获到的错误: "database.connect: connection refused"
```

---

## 4. 警告机制

### 4.1 非阻断警告

```tanexscript
*** deprecated_api = [*msg] => {
    <- warning{"DEPRECATED: " + msg};
    # 程序继续执行
};

deprecated_api("use v2 instead");
# 输出: WARN: DEPRECATED: use v2 instead
# 程序不中断
```

### 4.2 警告捕获 (可选处理)

```tanexscript
{ <- warning{"slow path detected"}; } | *w : {
    std.standard_output << "WARN: " + w.what;
} : { $ "fast path"; };
# 输出 WARN..., 继续执行
```

### 4.3 警告聚合 (避免重复)

```tanexscript
* warned = Dictionary{};

*** warn_once = [*key, *msg] => {
    warned.has_key(key) ? {} : {
        warned.set(key, true);
        <- warning{msg};
    };
};

# 循环中只警告一次
for(* i, [1..100], {
    warn_once("deprecated_loop", "loop is slow");
});
```

---

## 5. 断言与契约

### 5.1 运行时断言

```tanexscript
*** assert = [*cond, *msg] => {
    cond ? {} : { <- error{"assertion_error: " + msg}; };
};

assert(x > `0, "x must be positive");
assert(list.size > `0, "list cannot be empty");
```

### 5.2 前置/后置条件

```tanexscript
*** require = [*cond, *msg] => { assert(cond, "precondition: " + msg); };
*** ensure = [*cond, *msg] => { assert(cond, "postcondition: " + msg); };

*** divide = [*a, *b] => {
    require(b != `0, "divisor cannot be zero");
    * result = a / b;
    ensure(result != nan, "result should not be NaN");
    $ result;
};
```

---

## 6. 测试中的错误处理

### 6.1 期望抛出错误

```tanexscript
*** expect_error = [*fn, *expected_prefix] => {
    { fn(); } | *e : {
        e.what.startswith(expected_prefix) ? { $ true; } : {
            std.standard_output << "Expected " + expected_prefix + ", got: " + e.what;
            $ false;
        };
    } : {
        std.standard_output << "Expected error but succeeded";
        $ false;
    };
};

# 测试用例
expect_error({ divide(`1`, `0); }, "arith_error:");  # => true
```

### 6.2 属性测试模式

```tanexscript
*** quickcheck = [*prop_fn, *gen_fn, *trials] => {
    * i = `0;
    { i < trials } $$ {
        * input = gen_fn();
        { prop_fn(input); } | *e : {
            std.standard_output << "Failed: " + e.what + " (input: " + input.string() + ")";
            $ false;
        };
        i = i + `1;
    };
    $ true;
};

# 测试加法交换律
quickcheck(
    { *args => { assert(args[`0] + args[`1] == args[`1] + args[`0], "add commutes"); } },
    { [*] => { [*random_integer(`100), random_integer(`100)]; } },
    `1000
);
```

---

## 7. 调试技巧

### 7.1 错误堆栈追踪 (计划中)

```tanexscript
# 未来版本支持
try {
    risky();
} catch (e) {
    e.stack_trace();  # 返回调用栈字符串
}
```

### 7.2 条件断点

```tanexscript
*** debug_break = [*cond] => {
    cond ? { <- error{"DEBUG_BREAK"}; } : {};
};

# 在特定条件下触发
for(* i, [1..100], {
    debug_break(i == `50);  # 第 50 次迭代触发
    process(i);
});
```

---

## 8. 最佳实践清单

| ✅ 做 | ❌ 不做 |
|------|--------|
| 细粒度捕获，按前缀分类 | 捕获所有错误后不处理直接 `e.throw()` |
| 用 `else` 分支做成功时清理 | 在 `catch` 里做清理(成功时不执行) |
| 遵循标准错误前缀约定 | 自造错误消息格式 |
| 警告用于非致命问题 | 用警告代替错误处理 |
| 自定义错误类型承载结构化信息 | 仅用字符串错误消息 |
| 编写期望错误的测试 | 忽略错误路径测试 |
| 资源获取即初始化(RAII) | 手动在多处调用清理函数 |

---

## 相关链接

- [语言参考：错误处理](../reference/errors.md) — 完整语法语义
- [语言参考：表达式](../reference/expressions.md#尝试结构-lefterr--catch--else) — 尝试结构详解
- [标准库：random](../library/random.md) — 随机测试数据生成
- [专题指南：测试策略](testing.md) — 完整测试框架
- [专题指南：类型设计](type_design.md) — 自定义错误类型设计