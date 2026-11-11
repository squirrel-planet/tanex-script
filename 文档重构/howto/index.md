# 专题指南

> 对标 [Python HOWTOs](https://docs.python.org/zh-cn/3.16/howto/)
>
> 深入学习 Tanex Script 特定主题的实战指南。

---

## 章节导航

| 指南 | 说明 | 难度 |
|------|------|------|
| [type_design.md](type_design.md) | 类型设计模式：封装、继承、运算符重载 | ⭐⭐ |
| [error_handling.md](error_handling.md) | 错误处理模式：分类捕获、资源清理、警告机制 | ⭐⭐ |
| [performance.md](performance.md) | 性能优化：循环、内存、标准库选择 | ⭐⭐⭐ |
| [module_organization.md](module_organization.md) | 模块组织：目录结构、main.tsuc、public 控制 | ⭐ |
| [metaprogramming.md](metaprogramming.md) | 元编程：注解、代码块操作、动态 import | ⭐⭐⭐ |
| [dsl_building.md](dsl_building.md) | DSL 构建：代码块作为语法、管道操作符、控制流函数 | ⭐⭐⭐ |
| [testing.md](testing.md) | 测试策略：单元测试、集成测试、属性测试 | ⭐⭐ |
| [interop.md](interop.md) | 互操作：Python 嵌入、FFI、外部库调用 | ⭐⭐⭐ |

---

## 快速选择指南

| 你想... | 阅读指南 |
|---------|----------|
| 设计良好的自定义类型 | [类型设计模式](type_design.md) |
| 优雅处理错误与资源 | [错误处理模式](error_handling.md) |
| 让程序跑得更快 | [性能优化](performance.md) |
| 组织大型项目结构 | [模块组织](module_organization.md) |
| 利用注解/动态特性 | [元编程](metaprogramming.md) |
| 构建领域特定语言 | [DSL 构建](dsl_building.md) |
| 编写可靠的测试 | [测试策略](testing.md) |
| 与 Python/C 互操作 | [互操作](interop.md) |

---

## 相关链接

- [专题指南：类型设计模式](type_design.md) — 自定义类型、继承与运算符重载
- [语言参考：类型系统](../reference/types.md) — 完整类型规范
- [语言参考：运算符重载](../reference/operator_overloading.md) — 特殊成员详细语义
- [标准库参考](../library/) — 可复用的工具函数
- [扩展与嵌入](../extending/) — Python API 程序化控制