# Tanex Script 可能的更新 TODO

> 基线：`核心` 当前 **180 项 pytest 全部通过**（约 23 秒），是干净的工作起点。
> 语言语法已冻结（见 AGENTS.md）。本清单分为三类：
>
> - 【文档】= 文档里已写出的规划/承诺（主要是 `文档重构/whatsnew/index.md` 路线图）
> - 【现状】= 实际代码观察到的缺口、Bug、不一致（逐一验证过）
> - 【建议】= 我的建议，**全部为库层/实现层**，不触碰语法
>
> 任何涉及语法变更的条目都单独放在第八节，**必须先经维护者评审授权**。

---

## 〇、P0：文档体系迁移收尾（进行中的大前提）

会话期间旧文档树 `核心/Tanex Script文档/`（24 个文件）被整体移除，git 状态为 D，内容已确认与 HEAD 一致（无丢失）。新树在顶层 `文档重构/`（46 文件，对标 Python 文档结构）。收尾工作：

- [ ] 把新文档树搬进 `核心/Tanex Script文档/`（或正式定址），两份 AGENTS.md 的"单一事实来源"指向同步更新（现在仍指向已删除的 `Tanex Script 语法.md`）
- [ ] 【现状】**反引号整数差异必须拍板**：新文档通篇写 `` `42 ``，但实现直接报「非法字符 '`'」（已实测 `standard_output << `42;`）。二选一：
  - 改文档，全部换成普通整数 `42`（旧规范就是普通整数）；
  - 或作为语法变更评审通过后实现反引号整数（涉及 tokenizer/文档/测试）
- [ ] 【现状】新文档缺失的**已实现特性**（均有测试佐证，属"文档落后于实现"）：
  - `delete` 运算符 + `renounce` 特殊成员（`tests/test_delete_op.py`）
  - 字符串插值 `"hello {a}"`（`tests/test_string_interpolation.py`，9 月 5 日拍板设计）
  - `===` 网络运算符（旧文档 `网络运算符 ===.md` 有，新树未见整合）
  - `|>` 管道、二元 `$` 多层跳出、数字下划线分隔符（新文档已有 ✓，核对无遗漏即可）
- [ ] 【现状】文档**超前于实现**的规范化 API（见第三节），先决定是实现还是改文档
- [ ] 顶层 `重写文档_第0~6部分_*.md`（8 个文件）与 `文档重构/` 内容重复——二选一保留
- [ ] `文档重构_backup/` 迁移完成后清理或归档
- [ ] 旧文档迁移到新树时顺手修正的**已知错误**（迁移素材校对清单，详见第十节）

---

## 一、1.1.0 已排期项（【文档】whatsnew/index.md 路线图）

- [ ] `encoding.utf8` 模块：UTF-8 编解码、Unicode 规范化
- [ ] `http` 模块：HTTP 客户端/服务端基础设施（`核心/python_api/web_fetch.py` 已有 fetch/fetch_json/post_json 雏形可对接）
- [ ] `fs` 模块：读/写/列目录/监视（`io` 类型已有 `"w"/"r"/"a"` 基础，缺目录级操作）
- [ ] `time` / `chrono` 模块：时间戳、格式化、睡眠、定时器（genindex.md 中 `chrono` 标注计划中）
- [ ] 解释器性能优化：字节码缓存、内联缓存
- [ ] 错误信息格式标准化：错误码 + 位置 + 代码片段（`errors.py` 的 `tanex_script_error.code` 字段已存在但未系统使用）
- [ ] `random` 算法升级：xoshiro256++ 替代 LCG
- [ ] `bit_not` 位宽 Bug 修复（最小位宽补码 vs 固定位宽语义）

---

## 二、1.0.0 遗留的 `[待确认]` 项（【文档】）

- [ ] `bootstrap.tscc` 版本字段位置（编译产物顶层或元数据中）
- [ ] `shuffle` 内部依赖公开性：`~clone_list`、`~node_set` 是否暴露为标准库函数（random.tsuc 经上级作用域引用主模块符号）
- [ ] `bit_not` 位宽语义（与第一节末条重复，一次拍板）
- [ ] JSON 解析错误格式：统一错误码与消息结构
- [ ] 标准输入具体实现：`standard_input` 对象缺失（见 3.1 的 `read_line`/`read_all`），`>>` 的 EOF 哨兵约定待定
- [ ] ~~Number 除法精度~~ 已确认 3 位小数（bootstrap.tsuc 刚从 `bd < 10` 改为 `bd < 3`）——但注意连锁影响，见 5.6

---

## 三、标准库：文档已承诺的规范化 API（最大缺口，【现状】逐一 grep 验证未实现）

`文档重构/library/standard.md` 声明的导出 vs 现有 `standard_src/main.tsuc`（25 个 public）：

- [ ] `list_map` / `list_reduce` / `list_sort` / `list_slice` / `list_contains`（现在只有 `filter`/`any`/`all`/`find`，**没有 map/reduce/sort/slice**）
- [ ] `string_split` / `string_join` / `string_substring` / `string_upper` / `string_lower`（现在只有 `reverse_string`）
- [ ] `to_string`（顺带：旧语法文档示例用了不存在的 `to_number`，字符串→数字转换是真缺口）
- [ ] `print` / `println`（现名 `output` / `print_line`——命名规范冲突见 3.3）
- [ ] `read_line` / `read_all` + `standard_input` 对象（`>>` 已能读 stdin，缺封装）
- [ ] 反射三件套：`type_name` / `members_of` / `has_member` / `get_member`
- [ ] 控制流辅助：`retry(times, fn, delay)` / `times(n, fn)`（直接包 `cycle`）/ `until(cond, fn)`
- [ ] 函数式工具：`identity` / `constant` / `pipe`
- [ ] 类型构造别名：`Integer` / `Number` / `String` / `Boolean` / `List` / `Code` / `Dictionary`

### 3.1 风格参照（新增函数一律按现有库风格写）

```Tanex Script
@ list_map # 对列表每个元素应用函数，返回新列表 #;
*** list_map = [*source, *function] => {
    * result = list{};
    * node = source.head;
    { return  !_is_none(node); } $$ {
        result.append(function(node.value));
        node = node.next;
    };
    return result;
};

@ read_line # 从控制台读取一行输入，返回字符串 #;
*** read_line = [] => {
    * buffer = "";
    standard_output >> buffer;
    return buffer;
};
```

要点：`@ 名字 # 注释 #;` 注解、`*** 名字 = [参数] => {}` 常量声明、`*参数` 传地址、
`{ ... } $$ { ... }` 循环、私有函数 `_` 前缀、模块尾部 `*** public = [...];`。

### 3.2 参数顺序统一（【现状】）

现有 `filter(*fn, *list)` / `any(*fn, *list)` / `find(*fn, *list)` 是**函数在前**；
新文档 `list_map(list, fn)` 是**列表在前**。规范化时统一（建议列表在前，与 `for(*var, list, code)` 一致）。

### 3.3 命名规范统一（文档称"规范化导出名"，1.x 双名过渡、2.0 收口）

| 现有 | 规范化目标 | 动作 |
|---|---|---|
| `output` / `print_line` | `print` / `println` | 重命名 |
| `filter` / `find` / `any` / `all` | `list_filter` / `list_find` / ... | 重命名 + 调参序 |
| `length_of` | `string_length` + `list_length` | 语义拆分 |
| `concatenate` | `string_concat` / `list_concat` | 语义拆分 |
| `abs`/`sign`/`min`/`max`/`clamp`（在 maths） | 文档规划到 standard | 归属调整或双导出 |

---

## 四、标准库：我建议的新增（【建议】，全部库层）

### 4.1 列表

- [ ] `sort(list, [*compare])`（配合 `compare` 三路比较特殊成员）与 `sort_by`
- [ ] `index_of(list, value)` / `contains` / `unique` / `flatten` / `zip(list, list)`
- [ ] `insert(list, index, value)` / `remove_at(list, index)` / `first` / `last`
- [ ] 统计套件：`sum` / `average` / `min_of` / `max_of` / `median`
- [ ] 链表特化：`node_insert` / `node_remove`（O(1) 定位后操作，与现有 `node_set` 配套）

### 4.2 字符串

- [ ] `to_number(text)` / `to_integer(text)`（**最痛缺口**：目前只能靠字面量或 json 私有函数）
- [ ] `trim` / `index_of` / `starts_with` / `ends_with` / `replace` / `count` / `repeat`
- [ ] `pad_left` / `pad_right`
- [ ] `to_character_list` / `from_character_list`（字符串↔码点列表互转）
- [ ] `compare_text`（字典序，供字符串排序用）

### 4.3 字典（dictionary 已有，桶数固定 16）

- [ ] `keys(dict)` / `values(dict)` / `has_key` / `remove_key` / `copy` / `merge`（现在只有 `entries()`）
- [ ] 【现状】哈希桶**固定 16、无扩容**——大数据量退化为 O(n)。库层 rehash 辅助或实现层扩容

### 4.4 maths（现有 25 个全是整数论向）

- [ ] `floor` / `ceil` / `round` / `absolute_difference`
- [ ] `sin` / `cos` / `tan` / `log` / `log2` / `exp`（**先拍精度**，见 5.6）
- [ ] 列表统计版：`average` / `sum_list` / `median`

### 4.5 random

- [ ] `random_float`（受精度限制）/ `random_string(length)` / `sample(list, count)` / `weighted_choice`
- [ ] xoshiro256++（路线图已列）

### 4.6 错误与调试辅助

- [ ] `error_of(name, message)`（现在必须 `error{["Error", "..."]}` 裸构造列表）
- [ ] `assert(condition, [*message])`
- [ ] `stack_trace()`（配合第六节堆栈追踪计划）

### 4.7 遍历能力

- [ ] 【现状】`for` 只支持 list 下标遍历，不能遍历 string / dictionary（加转换辅助或文档明示）
- [ ] 【现状】`match` 注解自述"多个条件同时为真时命中顺序不确定"（哈希桶序）——考虑稳定排序或文档固化

---

## 五、标准库源码质量修复（【现状】，多为小改动）

- [ ] `standard_src/main.tsuc:239-240`：`@ for_each` 注解行**重复两行**
- [ ] `standard_src/bit.tsuc`：唯一**没有 `@` 注解、没有 `public` 列表**的模块，与其余 7 个风格不一致
- [ ] `bit.tsuc` 用"十进制模拟二进制"做位运算（`to_binary`→逐位→`to_decimal`），慢且 `bit_not` 位宽未定义——重写为直接位运算
- [ ] `bit.tsuc` 的 `to_binary`/`to_decimal` 与 `numeral_system.tsuc` 的 `integer_to_binary`/`binary_to_integer` **功能重复、命名不同**——合并
- [ ] `maths.tsuc:96-102`：`pi = number{3, 1416}`（4 位）与除法截断 3 位不一致；json.tsuc 解析小数上限 4 位——**精度规则三处不一致**（3/4/4），统一
- [ ] `standard_src/main.tscc` 编译产物混在源码目录；`核心/library/` 下有 `hello_world.tscc`、`this.tscc` 历史示例——纳入构建规范或 gitignore
- [ ] bootstrap 里的 `object` 类型（L9）**未公开、未文档化**——要么文档化并导出，要么移除

---

## 六、运行时 / 解释器（不动语法）

- [ ] 【现状】**递归深度保护**：无 `RecursionError` 捕获（grep 验证），深递归以 Python 原始 traceback 泄漏；教程自己写了"递归栈溢出"是常见错误——包一层「递归过深」运行时错误
- [ ] 【现状】`===` 网关硬编码：连接/读取超时各 10 秒、协议固定单行 JSON（`interpreter.py:3641-3676`）——参数化（io 对象成员或库函数），不动运算符
- [ ] 性能（路线图已列）：节点类型→方法分派表、`$$` 循环条件 AST 复用、常量折叠、`.tscc` 缓存指纹
- [ ] 错误码系统：给编译期/运行时错误编号，IDLE 可据此做快捷修复提示
- [ ] 堆栈追踪（【文档】计划中）：`runtime_error` 附 Tanex 层调用栈
- [ ] 内置函数文档核对：`type_of` / `param_types` / `invoke` / `arg_matches_type` / `help` / `import` 逐一进 builtins 文档
- [ ] 调试器增强：`-d=<n>` 行断点已存在——变量查看、单步、条件断点、IDLE 集成（【文档】计划中）
- [ ] REPL 增强：结果变量（如 `it`）、`?? name` 快捷打印注解
- [ ] CLI 可加：`--check`（只编译不跑）、`--ast-dump`、`--time`

---

## 七、2.0.0 探讨项（【文档】，全部需语法解冻评审，仅列出待你决策）

- [ ] 模式匹配 `match expr { pat => body }`（注意与标准库字典分派式 `match` 区分定位）
- [ ] 静态类型注解 `*name: Type`（运行时忽略，供工具链）
- [ ] 模块版本锁定 `import "lib@1.2.3"`
- [ ] 并发原语 `spawn`/`channel`/`select`（**纯库层可先起步**，用 `code` 值 + `===` 网关或 Python 侧线程）
- [ ] 原始字符串 `r"..."`（【文档】lexical.md 标注"暂不支持"）

---

## 八、工具链与生态

- [ ] 【现状】IDLE 目录堆了 **9 个一次性字体修复脚本**（`fix_font*.py`、`find_font.py`、`fix_final.py`）——清理；字体问题配置化根治（字体回退链），别再打补丁
- [ ] IDLE `doc_viewer.py`（新增）对接新文档树
- [ ] 【现状】`打包器/`（PyInstaller 已能出 `TanexScript_Setup.exe`）、`安装包/` 整个目录 **untracked**——纳入 git、版本号注入、标准库 `.tscc` 打包校验
- [ ] `python_api/web_fetch.py`（已有测试）→ 对接 1.1.0 `http` 模块
- [ ] CI：把 180 项 pytest + 回归在 Windows/Linux 跑起来（现无 workflow）
- [ ] 测试补充：文档示例可运行性测试（防再出现 `to_number` 幻觉示例）、stdlib 每个公开函数表驱动回归、`test_no_foreign_syntax.py` 扩充
- [ ] 【文档】计划中：增量编译、`tanex.toml`、文档生成工具、性能分析工具、C API / FFI、JSON-RPC

---

## 九、仓库卫生（一次性收尾）

- [ ] `安装包/`、`打包器/`、`文档重构/`、`文档重构_backup/` untracked——迁移完成后入库
- [ ] 顶层 `fix_comments.py`、`fix_faq_syntax.py` 一次性脚本用完即删
- [ ] `核心/IDLE/repl_plain_backup.py` 备份文件处置
- [ ] 顶层 8 个 `重写文档_*.md` 与 `文档重构/` 去重（与〇节重复，同一件事）

---

## 十、旧文档迁移校对清单（迁移新树时逐条修正，来自旧 24 文件的核对）

**内部矛盾（旧树 5 处过时 vs 1 处正确）：**

- [ ] `import` 与 `->` 语义：旧 `语法.md`/`完整语句.md`/`表达式.md`/`运算符.md`/`优先级.md` 声称"完全等价"，实际（parser/interpreter）是分离语义：`import` 打包 library 句柄、`->` 展开到作用域且不支持命名引入——新树 `reference/modules.md` 已按正确语义写，确认其余页面无残留
- [ ] 旧 `语法.md` 内嵌优先级表（17 级）与 `优先级.md`（18 级）不同步：缺 `|>`、`& && &&&`、二元 `$`
- [ ] 旧 runtime-doc/bootstrap.md L160"只实现了加法"过时：bootstrap.tsuc 已有全套算术（subtract/multiply/divide/modulo/power）
- [ ] "每行末尾都要分号"（旧 语法.md L14）表述不准确：换行只是空白，语句结束只由 `;` 决定
- [ ] integer 描述为"无符号正整数"，但负整数经一元 `-` 大量存在

**内容缺口（新树大部分已在补，核对覆盖）：**

- [ ] 复合类型清单漏了 `dictionary` / `list_node` / `function_type` / `io` / `library` / `poly_function` / `object`
- [ ] `io` 与文件读写完全未文档化（旧树只字未提）
- [ ] REPL / 调试器（`-d` 断点）无文档
- [ ] `表达式.md` 链接到不存在的 `值.md`
- [ ] 旧 `网络运算符 ===.md` 引用的 `examples/gateway/gateway_server.py`、`test_gateway.tsuc` 在仓库中不存在——补示例或改引用
- [ ] runtime-doc 约 20 处相对链接路径错误（`Tanex%20Script%20文档` 带空格，实际无空格）
- [ ] 旧 main.md L20 说 bootstrap.tscc 在 `run/` 目录——实际在 `核心/runtime/`
- [ ] 旧语法.md 示例用了不存在的 `to_number(...)`、`input()`、双参 `type(my_type, {...})`（实际 `type()` 无参）、裸用 `output(...)` 未先引入 standard

**错别字：**

- [ ] "```Tanex Sccript"（旧语法.md L162）
- [ ] `.tscl` 全称 "Compiled **Libary**"（旧语法.md L619；bootstrap 已修为 `library`，后缀全称未修）
- [ ] 库逻辑.md L11"写**人**编译后的文件"→"写入"；声明.md L9"声明**种**"→"中"
- [ ] json 解析小数 4 位上限、stringify 不支持 nan/infinite 等实现限制未在任何文档说明

---

## 附：优先级总览

| 级别 | 内容 |
|---|---|
| **P0** | 〇：文档收口（迁移完成、反引号整数拍板、补 delete/插值/===）——文档是单一事实来源，现在与实现双向脱节 |
| **P1** | 三：规范化标准库 API（文档已承诺，用户价值最大） |
| **P1** | 五：已知 Bug（bit_not、bit.tsuc 重写、for_each 重复注解、精度三处不一致、字典扩容） |
| **P2** | 一：1.1.0 模块（time → fs → encoding.utf8 → http，前两个无外部依赖最稳） |
| **P2** | 六：运行时体验（错误码、堆栈追踪、递归保护） |
| **P3** | 八/九：性能、工具链、CI、仓库卫生 |
| **评审** | 七：2.0 语法层探讨项——全部等维护者明确授权 |
