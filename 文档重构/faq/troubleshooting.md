# 故障排查指南

> Tanex Script 常见报错分析、调试技巧、性能问题排查。

---

## 1. 常见报错分析

### 1.1 编译期错误

#### E001: Illegal character
```
Error: E001 Illegal character: '中'
  at test.tsuc:1:5
  > 变量 = 1;
  >     ^
```
**原因**: 源文件编码非 UTF-8，或包含不支持的字符。
**解决**: 确保源文件保存为 UTF-8 无 BOM。

#### E002: Unexpected token
```
Error: E002 Unexpected token: '+'
  at test.tsuc:3:10
  >     a = `1 + `2;
  >          ^
```
**原因**: 语法错误，常见于：
- 缺少分号导致语句粘连
- 运算符用法错误（如一元/二元位置混淆）
- 关键字别名用在错误位置

#### E003: Unclosed string literal
```
Error: E003 Unclosed string literal
  at test.tsuc:5:1
  >     s = "hello
  >     ^
```
**原因**: 字符串缺少结束引号，或换行未转义。
**解决**: 补全双引号，换行用 `\n`。

#### E100: Ambiguous import path
```
Error: E100 Ambiguous import path: 'lib'
  Found: lib.tsuc, lib.tscc, lib/
```
**原因**: 同名多内容。加后缀消除歧义：
```tanexscript
import "lib/";      # 文件夹
import "lib.tsuc";  # 源码文件
import "lib.tscl";  # 编译库
```

#### E101: Circular dependency detected
```
Error: E101 Circular dependency detected: a -> b -> a
```
**原因**: 模块间形成循环依赖。重构为共享依赖或延迟导入。

---

### 1.2 运行时错误

#### E200: Variable not defined
```
Runtime Error: E200 Variable 'x' not defined
  at test.tsuc:10:5
  >     x + `1;
  >     ^
```
**原因**: 变量未声明就使用。检查拼写、作用域、声明顺序。

#### E201: Member not found
```
Runtime Error: E201 Member 'push' not found
  at test.tsuc:5:1
  >     s.push("x");
  >     ^
```
**原因**: 类型不支持该成员。检查类型定义、拼写、`external_read_only`。

#### E202: Type does not support operator
```
Runtime Error: E202 Type 'MyType' does not support operator '+'
  at test.tsuc:8:10
  >     a + b;
  >         ^
```
**原因**: 类型未注册对应特殊成员。需定义：
```tanexscript
*** MyType.addition = [*self, *other] => { ... };
```

#### E205: Cannot assign to constant
```
Runtime Error: E205 Cannot assign to constant
  at test.tsuc:3:1
  >     PI = `3.15;
  >     ^
```
**原因**: `***` 声明的常量不可修改。检查声明、拼写。

#### E207/E208: Division/Modulo by zero
```
Runtime Error: E207 Division by zero in integer divide
  at test.tsuc:2:1
  >     `10 \ `0;
  >     ^
```
**原因**: 整除/取余除数为零。**注意**: `/` 除零返回 `infinite` 不报错，但 `\` 和 `%` 报错。

#### E210: Multi-level return depth exceeded
```
Runtime Error: E210 Multi-level return depth exceeded
  at test.tsuc:5:1
  >     3 $ "escaped";
  >     ^
```
**原因**: 二元 `$` 跳出层数超过当前嵌套深度。检查层数计算。

#### E213: Annotation not found
```
Runtime Error: E213 Annotation not found: 'func'
  at test.tsuc:3:1
  >     ?? func;
  >     ^
```
**原因**: 注解不存在。检查注解名、作用域、库隔离。

---

## 2. 语义陷阱排查

### 2.1 行尾反斜杠被解析为整除
```tanexscript
# 现象：a 变成 5 而非 10
a = `10 \
`2;
# 实际解析为：a = `10 \ `2; (整除)
```
**排查**: 搜索行尾 `\`，直接换行即可。

### 2.2 闭包捕获循环变量
```tanexscript
# 现象：所有函数输出 3
* funcs = [];
for(* i, [`1`,`2`,`3`], {
    funcs.append([*] => { $ i; });
});
funcs[`0]();  # => `3 (预期 `1)

# 原因：闭包捕获的是 i 的地址，循环结束后 i 为 3
```
**修复**: 循环体内创建新绑定：
```tanexscript
for(* i, [`1`,`2`,`3`], {
    * captured = i;  # 新地址
    funcs.append([*] => { $ captured; });
});
```

### 2.3 参数传地址副作用
```tanexscript
# 现象：外部变量被意外修改
*** process = [*list] => {
    for(* item, list, { item = `0; });  # 修改列表元素
};

* data = [`1`,`2`,`3`];
process(data);
data;  # => [`0`,`0`,`0]
```
**修复**: 显式复制或不修改参数：
```tanexscript
*** process = [*list] => {
    * copy = List{};
    for(* item, list, { copy.append(item); });
    for(* item, copy, { item = `0; });
};
```

### 2.4 `Number` 除法精度截断
```tanexscript
# 现象：精度丢失
`1` / `3`;  # => '0.333' (非无限循环)
```
**说明**: 当前实现截断到小数点后 3 位精度。高精度需自行实现分数类型。

### 2.5 `&&` 一元/二元歧义
```tanexscript
# 现象：报错 "Unexpected token"
* refs = && 3;  # 一元位置 OK
a && b;         # 二元位置 OK
# 但如果在表达式中：
* x = && 3;     # 报错：&& 在二元位置被解析为逻辑与
```
**规则**: 一元位置（语句首、`(`后、一元后）为连续声明，其他为逻辑与。

---

## 3. 调试技巧

### 3.1 启用详细输出
```bash
tanex run app.tsuc --verbose
# [VERBOSE] Compiling app.tsuc... 12ms
# [VERBOSE] Loading bootstrap.tscc... 3ms
# [VERBOSE] Executing... 5ms
```

### 3.2 REPL 调试
```bash
tanex repl
>>> import "standard" = *std;
>>> std.println("test");
test
>>> :vars  # 查看当前变量
>>> :ast   # 查看最后语句 AST
>>> :tokens # 查看 Token 列表
```

### 3.3 打印调试
```tanexscript
import "standard" = *std;
std.println("DEBUG: x = " + x.string());
std.println("DEBUG: type = " + std.type_name(x));
```

### 3.4 条件断点
```tanexscript
*** debug_break = [*cond] => {
    cond ? { <- error{"DEBUG_BREAK"}; } : {};
};

for(* i, [`1`..`100`], {
    debug_break(i == `50);  # 第 50 次触发
    process(i);
});
```

---

## 4. 性能问题排查

### 4.1 程序启动慢
**原因**: 
- 引导库加载时间
- 大量模块编译
**优化**: 
- 复用编译产物 `.tscc`
- 减少动态 import
- 预热解释器

### 4.2 运行时内存增长
**原因**: 
- 闭包捕获大对象
- 列表/字符串频繁拼接
- 递归无尾调用优化
**优化**: 
- 显式释放引用 `var = none`
- 用 `String.push_str`/`List.append` 替代 `+`
- 改写递归为 `$$` 循环

### 4.3 递归栈溢出
```tanexscript
# 现象：Runtime Error: Maximum recursion depth exceeded
*** fact = [*n] => { n <= `1 ? `1 : n * fact(n - `1); };
fact(`10000);
```
**修复**: 改写为迭代：
```tanexscript
*** fact = [*n] => {
    * acc = `1;
    { n > `1 } $$ { acc = acc * n; n = n - `1; };
    $ acc;
};
```

---

## 5. 调试工具 (计划中)

| 工具 | 功能 | 状态 |
|------|------|------|
| 内置 Profiler | 函数调用统计、耗时分析 | 规划中 |
| 火焰图导出 | 可视化性能瓶颈 | 规划中 |
| 堆栈追踪 | 错误调用栈 | 规划中 |
| 断点调试 | 暂停/单步/变量查看 | 规划中 |
| 内存分析 | 对象分配、GC 统计 | 规划中 |

---

## 6. 获取帮助

### 6.1 错误信息不够清晰
- 使用 `--verbose` 获取更多上下文
- 检查错误码对照表 [错误与诊断](../extending/errors.md#3-错误码对照表)
- 在 REPL 中逐步复现

### 6.2 无法解决的问题
1. 搜索 [GitHub Issues](https://github.com/tanex-script/tanex-script/issues)
2. 提交新 Issue，包含：
   - Tanex 版本 (`tanex --version`)
   - 完整错误信息
   - 最小复现代码
   - 环境信息 (OS、Python 版本)

### 6.3 贡献修复
- 文档勘误：直接 PR 修改对应 `.md`
- Bug 修复：遵循代码风格指南，补充测试
- 功能建议：在 Discussions 讨论后再实现

---

## 相关链接

- [错误与诊断](../extending/errors.md) — 完整错误码表、异常层级
- [语言参考：错误处理](../reference/errors.md) — 尝试结构、错误类型
- [专题指南：错误处理](../howto/error_handling.md) — 实战模式
- [专题指南：性能优化](../howto/performance.md) — 性能分析
- [FAQ：语法与语义](syntax.md) — 语法常见问题
- [FAQ：标准库](stdlib.md) — 模块使用问题