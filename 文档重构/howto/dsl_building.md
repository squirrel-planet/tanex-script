# DSL 构建指南

> 基于 Tanex Script 代码块一等公民、管道操作符、控制流函数构建领域特定语言 (DSL)。

---

## 1. DSL 设计原则

| 原则 | 说明 |
|------|------|
| **语法统一** | 复用语言现有语法，不引入新关键字 |
| **类型安全** | 利用类型系统约束 DSL 结构 |
| **可组合** | 小型原语组合成复杂表达 |
| **可调试** | 错误信息指向 DSL 层而非实现细节 |
| **渐进式** | 简单用例简单，复杂用例可行 |

---

## 2. 内部 DSL 模式

### 2.1 函数式构建器

```tanexscript
* QueryBuilder = type_type{};
*** QueryBuilder.initialize = [*self] => {
    self.selects = List{};
    self.wheres = List{};
    self.limit_val = none;
};

*** QueryBuilder.select = [*self, *fields] => {
    self.selects = fields;
    $ self;  # 链式调用
};

*** QueryBuilder.where = [*self, *cond] => {
    self.wheres.append(cond);
    $ self;
};

*** QueryBuilder.limit = [*self, *n] => {
    self.limit_val = n;
    $ self;
};

*** QueryBuilder.build = [*self] => {
    * sql = "SELECT " + std.string_join(self.selects, ", ") + " FROM table";
    self.wheres.size > `0 ? {
        sql = sql + " WHERE " + std.string_join(self.wheres, " AND ");
    } : {};
    self.limit_val != none ? {
        sql = sql + " LIMIT " + self.limit_val.string();
    } : {};
    $ sql;
};

# 使用
* q = QueryBuilder{};
q.select(["id", "name"])
 .where("age > 18")
 .where("status = 'active'")
 .limit(`10)
 .build();
# => "SELECT id, name FROM table WHERE age > 18 AND status = 'active' LIMIT 10"
```

### 2.2 管道式 DSL

```tanexscript
* users = [
    {name: "Alice", age: `25, active: true},
    {name: "Bob", age: `17, active: true},
    {name: "Carol", age: `30, active: false}
];

* adults = users
    |> std.list_filter({ *u => u.active; })
    |> std.list_filter({ *u => u.age >= `18; })
    |> std.list_map({ *u => u.name; });

# adults => ["Alice", "Carol"]
```

### 2.3 控制流 DSL

```tanexscript
*** when = [*cond, *then_block, *else_block] => {
    cond ? { then_block(); } : { else_block ? { else_block(); } : {}; };
};

*** unless = [*cond, *block] => {
    !cond ? { block(); } : {};
};

# 使用
when(user.is_admin, {
    grant_access();
}, {
    deny_access();
});

unless(cache.has(key), {
    compute_and_store(key);
});
```

---

## 3. 外部 DSL (解析器组合子)

### 3.1 简单表达式解析器

```tanexscript
* Parser = type_type{};
*** Parser.initialize = [*self, *input] => {
    self.input = input;
    self.pos = `0;
};

*** Parser.peek = [*self] => {
    self.pos < self.input.data.size ? {
        $ self.input.data.index(self.pos);
    } : { $ -`1; };
};

*** Parser.consume = [*self, *expected] => {
    self.peek() == expected ? {
        self.pos = self.pos + `1;
        $ true;
    } : { $ false; };
};

*** Parser.parse_number = [*self] => {
    * start = self.pos;
    { self.peek() >= `48 && self.peek() <= `57 } $$ {
        self.pos = self.pos + `1;
    };
    * num_str = self.input.slice(start, self.pos);
    $ std.to_string(num_str);  # 假设有 slice
};

# 组合子
*** Parser.seq = [*self, *parsers] => {
    * results = List{};
    for(* p, parsers, {
        * r = p(self);
        r ? { results.append(r); } : { $ none; };  # 失败回溯
    });
    $ results;
};

*** Parser.alt = [*self, *parsers] => {
    for(* p, parsers, {
        * saved = self.pos;
        * r = p(self);
        r ? { $ r; } : { self.pos = saved; };
    });
    $ none;
};
```

### 3.2 JSON 解析器示例

```tanexscript
*** json_parser = [*input] => {
    * p = Parser{input};
    p.parse_value();
};

*** Parser.parse_value = [*self] => {
    self.alt([
        self.parse_null,
        self.parse_bool,
        self.parse_number,
        self.parse_string,
        self.parse_array,
        self.parse_object
    ]);
};

# 使用
* result = json_parser('{"name": "Alice", "age": 30}');
# result => dictionary{["name", "Alice"], ["age", `30]}
```

---

## 4. 模板 DSL

### 4.1 字符串模板引擎

```tanexscript
*** render = [*template, *context] => {
    * result = template;
    for(* key, context.members_of(), {
        * placeholder = "{{" + key + "}}";
        * value = context.get_member(key);
        * value_str = value.string();
        result = result.replace_all(placeholder, value_str);
    };
    $ result;
};

* tmpl = "Hello {{name}}, you are {{age}} years old.";
* ctx = dictionary{["name", "Alice"], ["age", `30]};
render(tmpl, ctx);
# => "Hello Alice, you are 30 years old."
```

### 4.2 条件/循环模板

```tanexscript
*** render_advanced = [*template, *context] => {
    # 简化版：支持 {{#if cond}}...{{/if}} {{#each list}}...{{/each}}
    # 完整实现需状态机解析
    $ template;  # 占位
};
```

---

## 5. 配置 DSL

### 5.1 声明式配置

```tanexscript
* ServerConfig = type_type{};
*** ServerConfig.initialize = [*self, *host, *port, *workers] => {
    self.host = host;
    self.port = port;
    self.workers = workers;
};

*** server = [*config_fn] => {
    * cfg = ServerConfig{"localhost", `8080, `4};  # 默认值
    config_fn(cfg);  # 用户自定义
    $ start_server(cfg.host, cfg.port, cfg.workers);
};

# 使用
server({ *cfg => {
    cfg.host = "0.0.0.0";
    cfg.port = `3000;
    # workers 保持默认 4
}});
```

### 5.2 分层配置合并

```tanexscript
*** merge_config = [*base, *override] => {
    * result = base;
    for(* key, override.members_of(), {
        result.(key) = override.get_member(key);  # 覆盖
    });
    $ result;
};

* default_cfg = {host: "localhost", port: `8080, debug: false};
* env_cfg = {port: `3000, debug: true};
* final_cfg = merge_config(default_cfg, env_cfg);
# => {host: "localhost", port: `3000, debug: true}
```

---

## 6. 测试 DSL

### 6.1 BDD 风格测试框架

```tanexscript
* describe = [*name, *fn] => {
    std.println("=== " + name + " ===");
    fn();
};

* it = [*name, *fn] => {
    { fn(); } | *e : {
        std.println("  ✗ " + name + ": " + e.what);
    } : {
        std.println("  ✓ " + name);
    };
};

* expect = [*actual] => {
    *** to_be = [*expected] => {
        actual != expected ? {
            <- error{"assertion_error: expected " + expected.string() + ", got " + actual.string()};
        } : {};
    };
    $ {to_be: to_be};
};

# 使用
describe("math", {
    it("addition", {
        expect(`1 + `2).to_be(`3);
    });
    it("multiplication", {
        expect(`3 * `4).to_be(`12);
    });
});
```

### 6.2 属性测试

```tanexscript
*** forall = [*gen, *prop, *trials] => {
    * i = `0;
    { i < trials } $$ {
        * input = gen();
        { prop(input); } | *e : {
            std.println("Failed: " + e.what + " (input: " + input.string() + ")");
            $ false;
        };
        i = i + `1;
    };
    $ true;
};

# 测试加法交换律
forall(
    { [*] => { [*rand.int(`100), rand.int(`100)]; } },
    { *args => { expect(args[`0] + args[`1]).to_be(args[`1] + args[`0]); } },
    `1000
);
```

---

## 7. 实战案例：构建 HTTP 路由 DSL

```tanexscript
* Router = type_type{};
*** Router.initialize = [*self] => {
    self.routes = Dictionary{};  # method -> path -> handler
};

*** Router.route = [*self, *method, *path, *handler] => {
    * key = method + ":" + path;
    self.routes.set(key, handler);
    $ self;
};

*** Router.get = [*self, *path, *handler] => { $ self.route("GET", path, handler); };
*** Router.post = [*self, *path, *handler] => { $ self.route("POST", path, handler); };

*** Router.handle = [*self, *method, *path, *request] => {
    * key = method + ":" + path;
    self.routes.has_key(key) ? {
        $ self.routes.get(key)(request);
    } : { $ {status: `404, body: "Not Found"}; };
};

# 使用
* app = Router{};
app.get("/users", { *req => { $ {status: `200, body: users.list()}; }})
   .post("/users", { *req => { $ users.create(req.body); }})
   .get("/users/:id", { *req => { $ users.get(req.params.id); }});

# 处理请求
* resp = app.handle("GET", "/users", {method: "GET", path: "/users"});
```

---

## 8. DSL 最佳实践

| 类别 | 建议 |
|------|------|
| **错误信息** | 在 DSL 层捕获错误，重新抛出带上下文的错误：`<- error{"router: " + e.what}` |
| **类型约束** | 为 DSL 参数定义类型，运行时检查或文档化 |
| **文档化** | 为每个 DSL 原语添加注解 `@ name # doc #;` |
| **测试覆盖** | 为 DSL 核心逻辑编写属性测试 |
| **性能** | 热路径避免过度动态分发，必要时内联 |
| **版本演进** | 保持向后兼容，废弃旧 API 用警告标记 |

---

## 相关链接

- [语言参考：表达式](../reference/expressions.md) — 管道 `|>`、代码块、匿名函数
- [语言参考：模块](../reference/modules.md) — 模块化 DSL 组织
- [专题指南：元编程](../howto/metaprogramming.md) — 运行时类型构造、动态 import
- [专题指南：测试策略](../howto/testing.md) — DSL 测试框架
- [标准库：standard](../library/standard.md) — `pipe`/`list_map` 等组合子