# 常见问题 (FAQ)

> 对标 [Python FAQ](https://docs.python.org/zh-cn/3.16/faq/)
>
> Tanex Script 常见问题分类解答。

---

## 章节导航

| 类别 | 文档 | 说明 |
|------|------|------|
| [general.md](general.md) | 通用问题 | 语言定位、安装、版本、学习资源 |
| [syntax.md](syntax.md) | 语法与语义 | 运算符、控制流、类型、作用域 |
| [stdlib.md](stdlib.md) | 标准库 | 模块导入、常用函数、性能 |
| [embedding.md](embedding.md) | 嵌入与扩展 | Python API、C API、互操作 |
| [troubleshooting.md](troubleshooting.md) | 故障排查 | 报错分析、调试、性能问题 |

---

## 快速问答

### Q: Tanex Script 是什么？
**A**: 一门面向元编程与嵌入场景的动态类型编程语言。核心特性：语法统一化(控制流即函数)、代码块一等公民、运算符重载协议、显式地址操作、精确十进制数值。

### Q: 如何安装？
**A**: 下载 Windows 安装包 `TanexScript_Setup.exe`，或从源码构建（需 Python 3.10+）：`pip install -r requirements.txt`。

### Q: 如何运行代码？
**A**: 
```bash
# 直接运行源码
tanex run hello.tsuc

# 编译后运行
tanex compile hello.tsuc -o hello.tscc
tanex run hello.tscc
```

### Q: 为什么 `if`、`for` 是函数不是关键字？
**A**: 语言设计追求**语法统一化**。所有控制结构均为标准库函数，参数含代码块(`code`类型)。这样：
- 语法规则极简一致
- 代码块可像值一样传递、组合
- 可自定义新控制结构（如 `retry`、`until`）

### Q: `import` 和 `->` 有什么区别？
**A**: 
- `import "lib"`：生成 `Library` 句柄，命名空间隔离，访问需 `lib.member`
- `-> "lib"`：直接展开文件所有顶层声明到当前作用域，无句柄

### Q: 为什么行尾不能写 `\` 续行？
**A**: `\` 是**二元整除运算符** (`n \ m`)，行尾写 `\` 会被解析为整除。直接换行即可，无需任何符号。

### Q: 如何定义自定义类型并重载运算符？
**A**: 
```tanexscript
* Vec2 = type_type{};
*** Vec2.initialize = [*self, *x, *y] => { self.x = x; self.y = y; };
*** Vec2.string = [*self] => { $ "Vec2(" + self.x.string() + ", " + self.y.string() + ")"; };
*** Vec2.addition = [*self, *other] => { $ Vec2{self.x + other.x, self.y + other.y}; };
```

### Q: 参数传递是传值还是传引用？
**A**: **传地址**。函数内对参数赋值直接修改调用方变量。

### Q: 如何处理错误？
**A**: 使用尝试结构：
```tanexscript
{ risky(); } | *e : {
    std.println("Error: " + e.what);
} : { $ "OK"; };
```

### Q: 如何在 Python 中嵌入 Tanex Script？
**A**: 
```python
from tanex.runtime.interpreter import TanexInterpreter
interp = TanexInterpreter()
result = interp.run_source('std.println("Hello")')
```

### Q: 标准库有哪些模块？
**A**: `standard`、`maths`、`numeral_system`、`encoding.ascii`、`encoding.base_sixty_four`、`json`、`random`、`bit`。

---

## 相关链接

- [教程：快速上手](../tutorial/intro.md) — 从零开始
- [语言参考](../reference/) — 完整语法语义规范
- [标准库参考](../library/) — 8 个模块逐条目规范
- [专题指南](../howto/) — 深入实战指南
- [扩展与嵌入](../extending/) — Python API 完整参考
- [故障排查](troubleshooting.md) — 报错分析、调试技巧