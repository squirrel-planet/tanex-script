# 测试策略指南

> Tanex Script 程序的测试方法与最佳实践。

---

## 1. 测试层级

| 层级 | 目标 | 工具/模式 | 运行频率 |
|------|------|-----------|----------|
| **单元测试** | 纯函数、类型方法 | `expect`/`assert`、属性测试 | 每次提交 |
| **集成测试** | 模块交互、I/O | 临时文件、内存模拟 | CI 流水线 |
| **端到端测试** | 完整程序流程 | CLI 调用、输出断言 | 发布前 |
| **属性测试** | 代数定律、不变量 | `forall` 生成随机输入 | 夜ly/每周 |
| **性能测试** | 回归检测 | `bench` 计时 | 发布前 |

---

## 2. 单元测试基础

### 2.1 断言库

```tanexscript
*** assert_eq = [*actual, *expected, *msg] => {
    actual != expected ? {
        <- error{"assertion_error: " + (msg ? msg : "") + " expected " + expected.string() + ", got " + actual.string()};
    } : {};
};

*** assert_true = [*cond, *msg] => {
    cond ? {} : { <- error{"assertion_error: " + (msg ? msg : "") + " expected true"; }; };
};

*** assert_false = [*cond, *msg] => {
    cond ? { <- error{"assertion_error: " + (msg ? msg : "") + " expected false"; }; } : {};
};

*** assert_raises = [*fn, *expected_prefix] => {
    { fn(); } | *e : {
        e.what.startswith(expected_prefix) ? {} : {
            <- error{"assertion_error: expected error prefix '" + expected_prefix + "', got '" + e.what + "'"};
        };
    } : {
        <- error{"assertion_error: expected error but succeeded"};
    };
};
```

### 2.2 测试用例结构

```tanexscript
* test_addition = [] => {
    assert_eq(`1 + `2, `3, "1+2=3");
    assert_eq(`-1 + `1, `0, "-1+1=0");
    assert_eq('0.1' + '0.2', '0.3', "0.1+0.2=0.3 (精确十进制)");
};

* test_list_map = [] => {
    * doubled = std.list_map([`1`,`2`,`3`], [*x] => { $ x * `2; });
    assert_eq(doubled, [`2`,`4`,`6`], "map doubles each element");
};

* test_error_handling = [] => {
    assert_raises({ divide(`1`, `0); }, "arith_error:");
    assert_raises({ import "nonexistent"; }, "import_error:");
};
```

---

## 3. 测试运行器

### 3.1 简单运行器

```tanexscript
* test_runner = [] => {
    * tests = [
        ["addition", test_addition],
        ["list_map", test_list_map],
        ["error_handling", test_error_handling]
    ];
    
    * passed = `0;
    * failed = `0;
    
    for(* t, tests, {
        * name = t[`0];
        * fn = t[`1];
        { fn(); } | *e : {
            std.println("✗ " + name + ": " + e.what);
            failed = failed + `1;
        } : {
            std.println("✓ " + name);
            passed = passed + `1;
        };
    });
    
    std.println("Passed: " + passed.string() + ", Failed: " + failed.string());
    failed > `0 ? { $ false; } : { $ true; };
};

test_runner();
```

### 3.2 JUnit XML 输出 (CI 集成)

```tanexscript
*** junit_xml = [*results] => {
    * xml = '<?xml version="1.0" encoding="UTF-8"?>\n<testsuite>\n';
    for(* r, results, {
        xml = xml + '  <testcase name="' + r.name + '"';
        r.passed ? { xml = xml + '"/>\n'; } : {
            xml = xml + '">\n    <failure message="' + r.error + '"/>\n  </testcase>\n';
        };
    });
    xml = xml + '</testsuite>';
    $ xml;
};
```

---

## 4. 属性测试

### 4.1 `forall` 框架

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

*** gen_int = [*min, *max] => {
    [*] => { $ min + random() % (max - min + `1); };
};

*** gen_list = [*gen_elem, *max_len] => {
    [*] => {
        * len = random() % (max_len + `1);
        * result = List{};
        * i = `0;
        { i < len } $$ { result.append(gen_elem()); i = i + `1; };
        $ result;
    };
};
```

### 4.2 代数定律测试

```tanexscript
* test_monoid_laws = [] => {
    # 结合律
    forall(
        gen_list(gen_int(`0, `100), `5),
        { *args => {
            * a = args[`0]; * b = args[`1]; * c = args[`2];
            assert_eq((a + b) + c, a + (b + c), "addition associativity");
        }},
        `1000
    );
    
    # 单位元
    forall(
        gen_int(`-100, `100),
        { *x => { assert_eq(x + `0, x, "addition identity"); }},
        `1000
    );
};
```

### 4.3 圆周性质测试

```tanexscript
* test_serialization_roundtrip = [] => {
    forall(
        { [*] => { dictionary{["key", random_integer(`1000)]; } } },
        { *obj => {
            * json_str = json.stringify(obj);
            * parsed = json.parse(json_str);
            assert_eq(obj, parsed, "json roundtrip");
        }},
        `100
    );
};
```

---

## 5. 集成测试

### 5.1 临时文件测试

```tanexscript
* with_temp_file = [*body_fn] => {
    * tmp = "/tmp/test_" + random().string() + ".txt";
    { body_fn(tmp); } | *e : {
        std.fs.remove(tmp);  # 假设有 fs 模块
        e.throw();
    } : {
        std.fs.remove(tmp);
    };
};

* test_file_io = [] => {
    with_temp_file({ *path => {
        std.fs.write(path, "hello");
        * content = std.fs.read(path);
        assert_eq(content, "hello");
    }});
};
```

### 5.2 模拟外部依赖

```tanexscript
* MockHttp = type_type{};
*** MockHttp.initialize = [*self] => { self.responses = Dictionary{}; };
*** MockHttp.set_response = [*self, *url, *response] => { self.responses.set(url, response); };
*** MockHttp.get = [*self, *url] => { $ self.responses.get(url); };

* test_api_client = [] => {
    * mock = MockHttp{};
    mock.set_response("/api/user", {name: "Alice"});
    
    * client = ApiClient{mock};  # 注入 mock
    * user = client.get_user();
    assert_eq(user.name, "Alice");
};
```

---

## 6. 端到端测试

### 6.1 CLI 程序测试

```tanexscript
* run_cli = [*args] => {
    * cmd = "tanex run main.tscc " + std.string_join(args, " ");
    * result = std.process.run(cmd);  # 假设有 process 模块
    $ result;  # {exit_code, stdout, stderr}
};

* test_cli_help = [] => {
    * r = run_cli(["--help"]);
    assert_eq(r.exit_code, `0);
    assert_true(r.stdout.contains("Usage:"));
};

* test_cli_version = [] => {
    * r = run_cli(["--version"]);
    assert_true(r.stdout.contains("Tanex Script"));
};
```

### 6.2 黄金文件测试

```tanexscript
* test_golden = [*name, *actual_fn] => {
    * golden_path = "tests/golden/" + name + ".golden";
    * actual = actual_fn();
    * expected = std.fs.read(golden_path);
    assert_eq(actual, expected, name + " matches golden file");
};

# 更新黄金文件: tanex run tests/update_golden.tsuc
```

---

## 7. 测试组织最佳实践

| 实践 | 说明 |
|------|------|
| **命名规范** | `test_<功能>_<场景>` 如 `test_divide_by_zero_raises` |
| **单一职责** | 每个测试函数只验证一个行为 |
| **独立性** | 测试间无共享状态，使用 `with_temp_file` 等隔离 |
| **确定性** | 避免依赖时间、随机数、外部服务；用 mock 替代 |
| **快速反馈** | 单元测试 < 100ms，集成测试 < 1s |
| **覆盖率目标** | 核心逻辑 > 90%，工具函数 100% |

---

## 8. CI 集成

```yaml
# .github/workflows/test.yml
name: Test
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v5
        with: {python-version: '3.11'}
      - name: Install Tanex
        run: pip install tanex-script
      - name: Run tests
        run: tanex run tests/run_all.tsuc
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## 相关链接

- [语言参考：错误处理](../reference/errors.md) — 尝试结构、错误类型
- [标准库：random](../library/random.md) — 测试数据生成
- [专题指南：错误处理](../howto/error_handling.md) — 测试中的错误模式
- [专题指南：性能优化](../howto/performance.md) — 性能回归测试
- [扩展与嵌入](../extending/) — Python API 测试工具