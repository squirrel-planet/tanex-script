# 模块组织指南

> Tanex Script 项目模块结构的最佳实践。

---

## 1. 推荐目录结构

```
my_project/
├── main.tsuc              # 入口文件
├── lib/                   # 内部库 (不发布)
│   ├── core.tsuc          # 核心逻辑
│   ├── utils/
│   │   ├── string.tsuc
│   │   └── math.tsuc
│   └── _internal.tsuc     # 下划线开头 = 私有，不在 public 中
├── tests/                 # 测试文件
│   ├── test_core.tsuc
│   └── test_utils.tsuc
├── examples/              # 示例程序
│   └── hello.tsuc
├── build/                 # 编译输出 (gitignore)
│   ├── main.tscc
│   └── lib.tscl
├── tanex.toml             # 项目配置 (计划中)
└── README.md
```

---

## 2. 库设计原则

### 2.1 单一职责

每个 `.tsuc` 文件只负责一个领域：

```tanexscript
# utils/string.tsuc - 仅字符串工具
*** public = ["trim", "split", "join", "upper", "lower"];

*** trim = [*s] => { ... };
*** split = [*s, *sep] => { ... };
# ...
```

### 2.2 明确导出 (`public`)

```tanexscript
# lib/core.tsuc
*** internal_helper = [*x] => { ... };  # 不在 public，内部用
*** public_api = [*x] => { ... };       # 对外导出
*** Config = type_type{ ... };          # 导出类型

*** public = ["public_api", "Config"];  # 仅这两个可被 import 访问
```

### 2.3 避免循环依赖

```
# ❌ 循环依赖
# a.tsuc -> import "b"; b.tsuc -> import "a";

# ✅ 重构为共享依赖
# shared.tsuc -> 共用代码
# a.tsuc -> import "shared"; b.tsuc -> import "shared";
```

---

## 3. 入口文件 `main.tsuc`

### 3.1 标准库风格

```tanexscript
# main.tsuc
@ # My Library v1.2.0 #;

*** public = ["create_app", "Config", "ErrorCodes"];

import "./core" = *core;
import "./utils/string" = *str;
import "./utils/math" = *math;

# 组合导出
*** create_app = [*config] => {
    * app = core.create(config);
    app.use(str.middleware());
    $ app;
};

# 重新导出子模块类型
*** Config = core.Config;
*** ErrorCodes = core.ErrorCodes;
```

### 3.2 可执行程序风格

```tanexscript
# main.tsuc (可执行程序)
@ # My App Entry #;

import "standard" = *std;
import "lib/core" = *core;

*** main = [*args] => {
    std.println("Starting...");
    core.run();
};

main(args);  # 直接调用入口
```

---

## 4. 内部模块 (`_` 前缀)

```tanexscript
# lib/_internal.tsuc
# 不在 public 中，外部 import 不可见
*** secret_key = "internal_only";
*** internal_calc = [*x] => { ... };

# 外部无法访问
# import "lib" = *lib;
# lib.secret_key;  # ❌ 报错：成员不存在
```

---

## 5. 版本管理

### 5.1 库版本声明

```tanexscript
# lib/version.tsuc
*** VERSION = "1.2.3";
*** VERSION_INFO = "1.2.3 (2025-01-15)";

*** public = ["VERSION", "VERSION_INFO"];
```

### 5.2 语义化版本

| 版本部分 | 含义 | 示例 |
|----------|------|------|
| MAJOR | 破坏性 API 变更 | `2.0.0` |
| MINOR | 向后兼容新增功能 | `1.3.0` |
| PATCH | Bug 修复、文档更新 | `1.2.4` |

---

## 6. 编译与打包

### 6.1 开发时编译

```bash
# 编译入口
tanex compile main.tsuc -o build/main.tscc

# 编译整个库 (生成 .tscl)
tanex compile lib/ -o build/lib.tscl
```

### 6.2 发布打包

```
# 发布包结构
mylib-1.2.3/
├── main.tscc           # 编译后入口
├── lib.tscl            # 打包后库 (含所有 .tscc)
├── README.md
└── LICENSE
```

用户安装后：
```tanexscript
import "mylib" = *mylib;  # 从安装目录加载
```

---

## 7. 测试组织

```
tests/
├── unit/
│   ├── test_core.tsuc
│   └── test_utils.tsuc
├── integration/
│   └── test_api.tsuc
├── fixtures/            # 测试数据
│   └── sample.json
└── run_tests.tsuc       # 测试运行器
```

```tanexscript
# tests/run_tests.tsuc
import "standard" = *std;
import "../lib" = *lib;

*** run_all = [] => {
    std.println("Running unit tests...");
    import "./unit/test_core" = *t1;
    import "./unit/test_utils" = *t2;
    t1.run();
    t2.run();
    std.println("All tests passed!");
};

run_all();
```

---

## 8. 文档生成 (注解驱动)

```tanexscript
# 利用注解生成文档
@ my_func #
计算两数之和。
@param a 第一个加数
@param b 第二个加数
@return 两数之和
#;

*** my_func = [*a, *b] => { $ a + b; };

# 文档生成工具 (计划中)
# tanex docgen lib/ --output docs/
```

---

## 9. 迁移清单 (从扁平结构)

| 步骤 | 动作 |
|------|------|
| 1 | 创建 `lib/` 目录，按功能拆分 `.tsuc` |
| 2 | 每文件添加 `public` 列表 |
| 3 | 创建 `main.tsuc` 统一导出 |
| 4 | 内部模块重命名为 `_xxx.tsuc` |
| 5 | 更新所有 `import` 路径为相对路径 |
| 6 | 添加 `tanex.toml` 配置 (计划中) |
| 7 | 编写 `tests/` 与 `examples/` |
| 8 | 验证 `tanex compile lib/ -o build/lib.tscl` 无误 |

---

## 相关链接

- [语言参考：模块系统](../reference/modules.md) — import/->、public、注解隔离
- [标准库参考](../library/) — 标准库模块结构参考
- [专题指南：DSL 构建](dsl_building.md) — 模块化 DSL 设计
- [扩展与嵌入](../extending/) — Python API 动态加载模块