# 教程

> 对标 [Python Tutorial](https://docs.python.org/zh-cn/3.16/tutorial/index.html)
>
> 从零开始循序渐进学习 Tanex Script，建议按下列顺序阅读。

---

## 章节导航

| 文档 | 说明 |
|------|------|
| [intro.md](intro.md) | 快速上手：启动解释器、第一个程序、变量与基本类型 |
| [controlflow.md](controlflow.md) | 深入控制流：代码块、`if` 条件、`while`/`for` 循环、错误处理 |
| [functions_modules.md](functions_modules.md) | 函数与模块：函数定义、闭包、`import` 与 `->`、库组织 |

---

## 学习路径

1. [快速上手](intro.md)：先跑通第一个程序，理解 `*`/`**`/`***` 声明与地址、引用语义。
2. [深入控制流](controlflow.md)：所有控制结构都是函数调用形式，配合代码块 `{...}` 使用。
3. [函数与模块](functions_modules.md)：把代码拆成函数与库，掌握注解读取与 `public` 导出。

> 标识符一经 `*`/`**`/`***` 显式声明，不得换种类重新声明；如需更换请先 `delete`。详见[声明语句](../reference/statements.md)。

---

## 相关章节

- [语言参考](../reference/index.md)：语法与语义的权威说明
- [标准库参考](../library/index.md)：8 个内置模块
- [常见问题](../faq/index.md)：常见报错与排查思路
- [专题指南](../howto/index.md)：面向具体任务的实战指南
