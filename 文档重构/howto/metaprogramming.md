# 元编程指南

> Tanex Script 元编程能力：注解、代码块操作、动态 import、运行时类型构造。

---

## 1. 注解驱动开发

### 1.1 文档生成

```tanexscript
@ my_func #
计算两数之和。
@param a 第一个加数 (Integer)
@param b 第二个加数 (Integer)
@return 两数之和 (Integer)
@since 1.0.0
#;

*** my_func = [*a, *b] => { $ a + b; };

# 读取注解生成文档
* doc = ?? my_func;
std.standard_output << doc;
# 输出:
# 计算两数之和。
# @param a 第一个加数 (Integer)
# @param b 第二个加数 (Integer)
# @return 两数之和 (Integer)
# @since 1.0.0
```

### 1.2 运行时验证

```tanexscript
@ validate #
字段验证规则：{type: "string", min: 1, max: 100}
#;

*** validated_func = [*input] => {
    * rules = ?? validate;
    # 解析 rules (假设为 JSON 字符串)
    # 运行时验证 input
    # ...
};

# 跨库读取
import "lib" = *lib;
lib.?? lib.validate_func;  # 读取 lib 的注解
```

### 1.3 API 版本废弃标记

```tanexscript
@ deprecated #
使用 v2_version 替代。将在 2.0.0 移除。
#;

*** old_api = [*x] => {
    <- warning{"old_api deprecated, use v2_version"};
    $ v2_version(x);
};
```

---

## 2. 代码块操作

### 2.1 代码块作为数据

```tanexscript
* block1 = { $ `1; };
* block2 = { $ `2; };

* blocks = [block1, block2];

# 遍历执行
for(* b, blocks, { b(); });  # => `1, `2
```

### 2.2 运行时构造代码块

```tanexscript
*** make_adder = [*n] => {
    # 返回捕获 n 的代码块
    [*x] => { $ x + n; };
};

* add5 = make_adder(`5);
add5(`3);  # => `8
```

### 2.3 代码块转字符串 (反射)

```tanexscript
* code_str = ?? block1;  # 仅读取注解，不含代码本身

# 代码块本身无直接序列化为字符串的能力
# 如需动态生成代码，使用字符串拼接 + eval (需解释器支持 eval)
```

### 2.4 高阶组合器

```tanexscript
*** compose = [*f, *g] => { [*x] => { $ f(g(x)); }; };
*** pipe = [*fns...] => {
    [*x] => {
        * result = x;
        for(* fn, fns, { result = fn(result); });
        $ result;
    };
};

* add1 = [*x] => { $ x + `1; };
* mul2 = [*x] => { $ x * `2; };
* add1_mul2 = pipe(add1, mul2);
add1_mul2(`5);  # => `12
```

---

## 3. 动态 Import

### 3.1 插件系统

```tanexscript
* load_plugin = [*name] => {
    * path = "plugins/" + name + ".tsuc";
    import path = *plugin;
    $ plugin;
};

# 运行时根据配置加载不同插件
* plugin_name = config.plugin;  # 如 "auth"
* auth = load_plugin(plugin_name);
auth.login(user, pass);
```

### 3.2 热重载

```tanexscript
* hot_reload = [*module_path] => {
    # 使缓存失效
    interpreter.module_cache.invalidate(module_path);
    # 重新导入
    import module_path = *fresh;
    $ fresh;
};

# 监听文件变化 (需宿主环境支持)
# watch("lib/core.tsuc", { hot_reload("lib/core"); });
```

### 3.3 条件导入

```tanexscript
* platform_lib = os == "windows" ? "lib/win" : "lib/unix";
import platform_lib = *platform;

platform.init();
```

---

## 4. 运行时类型构造

### 4.1 动态创建类型

```tanexscript
*** create_record_type = [*field_names] => {
    * T = type_type{};
    *** T.initialize = [*self, *values] => {
        * i = `0;
        { i < field_names.size } $$ {
            self.(field_names.index(i)) = values.index(i);
            i = i + `1;
        };
        *** self.addable = false;
    };
    $ T;
};

* Person = create_record_type(["name", "age", "email"]);
* p = Person{["Alice", `30, "alice@example.com"]};
```

### 4.2 运行时添加方法

```tanexscript
* T = type_type{};
*** T.initialize = [*self] => { self.value = `0; };

# 运行时注册方法
*** T.increment = [*self] => { self.value = self.value + `1; };
*** T.decrement = [*self] => { self.value = self.value - `1; };

* t = T{};
t.increment();
t.value;  # => `1
```

### 4.3 Mixin 合成

```tanexscript
*** mixin = [*target_type, *source_type] => {
    * members = source_type.members_of();  # 假设有此反射
    for(* name, members, {
        * fn = source_type.get_member(name);
        *** target_type.(name) = fn;
    };
    $ target_type;
};

* WithLogging = type_type{};
mixin(WithLogging, LoggerMixin);
```

---

## 5. 反射与内省

### 5.1 类型信息查询

```tanexscript
import "standard" = *std;

std.type_name(`42);           # => "Integer"
std.type_name("hello");       # => "String"

std.members_of("hello");      # => ["data", "size", "push_char", ...]
std.has_member("hello", "size"); # => true
std.get_member("hello", "size"); # => `5
```

### 5.2 运行时类型判断

```tanexscript
*** is_type = [*value, *type_name] => {
    $ std.type_name(value) == type_name;
};

is_type(`42, "Integer");    # => true
is_type("hi", "Integer");   # => false
```

### 5.3 获取特殊成员

```tanexscript
*** get_special = [*type_obj, *member_name] => {
    $ type_obj.get_special_member(member_name);  # 假设有此反射
};

* add_fn = get_special(integer, "addition");  # 获取整数加法函数
add_fn(`1`, `2);  # => `3
```

---

## 6. 编译时元编程 (预处理)

### 6.1 条件编译 (通过动态 import)

```tanexscript
# debug.tsuc
*** DEBUG = true;
*** log = [*msg] => { std.println("[DEBUG] " + msg); };

# release.tsuc
*** DEBUG = false;
*** log = [*msg] => { ; };  # 空操作

# 主程序
import "config/debug" = *cfg;  # 或 release
cfg.log("Starting...");  # 根据导入的版本决定是否输出
```

### 6.2 代码生成 (构建时)

```tanexscript
# build_gen.tsuc - 构建时运行，生成代码文件
*** generate_constants = [] => {
    * content = "@ # Auto-generated #;\n";
    * i = `0;
    { i < `100 } $$ {
        content = content + "*** CONST_" + i.string() + " = `" + i.string() + ";\n";
        i = i + `1;
    };
    write_file("gen/constants.tsuc", content);
};

generate_constants();
```

---

## 6. 实战案例：简单规则引擎

```tanexscript
* RuleEngine = type_type{};
*** RuleEngine.initialize = [*self] => { self.rules = List{}; };

*** RuleEngine.add_rule = [*self, *condition, *action] => {
    self.rules.append([condition, action]);
};

*** RuleEngine.execute = [*self, *context] => {
    for(* rule, self.rules, {
        * cond = rule[`0];
        * act = rule[`1];
        cond(context) ? { act(context); } : {};
    });
};

# 使用
* engine = RuleEngine{};
engine.add_rule(
    { *ctx => { ctx.score > `90; } },
    { *ctx => { ctx.grade = "A"; } }
);
engine.add_rule(
    { *ctx => { ctx.score > `60; } },
    { *ctx => { ctx.grade = "B"; } }
);

* ctx = {score: `95, grade: ""};
engine.execute(ctx);
ctx.grade;  # => "A"
```

---

## 相关链接

- [语言参考：注解](../reference/lexical.md#注解) — 注解语法与作用域
- [语言参考：表达式](../reference/expressions.md) — 代码块、匿名函数
- [语言参考：模块](../reference/modules.md) — 动态 import
- [内置对象：反射](../builtins/) — type_name、members_of 等
- [专题指南：DSL 构建](dsl_building.md) — 基于元编程的 DSL 设计
- [扩展与嵌入](../extending/) — Python API 操作注解、代码块