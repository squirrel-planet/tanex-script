# 标准库常见问题

> Tanex Script 标准库模块导入、常用函数、性能等问题。

---

## 模块导入

### Q: 如何导入标准库？
**A**: 推荐显式命名引入，避免命名冲突：

```tanexscript
import "standard" = *std;
import "maths" = *math;
import "encoding.ascii" = *ascii;
import "json" = *json;
import "random" = *rand;
import "bit" = *bit;
import "numeral_system" = *ns;
```

### Q: `import "standard"` 和 `-> "standard"` 有什么区别？
**A**: 
- `import "standard" = *std`：生成 `Library` 句柄，访问 `std.println()`，命名空间隔离
- `-> "standard"`：直接展开所有顶层声明到当前作用域，直接用 `println()`

### Q: 为什么推荐 `import` 不推荐 `->`？
**A**: `import` 保持**命名空间隔离**，避免污染全局作用域，便于大型项目维护。`->` 适合小脚本快速测试。

---

## 常用功能

### Q: 如何输出/打印？
**A**: 
```tanexscript
import "standard" = *std;
std.print("hello");       # 无换行
std.println("world");     # 自动换行
std.standard_output << "直接用输出运算符\n";
```

### Q: 如何读取输入？
**A**: 
```tanexscript
* line = std.read_line();      # 读取一行
* all = std.read_all();        # 读取全部直到 EOF
```

### Q: 字符串常用操作？
**A**: 
```tanexscript
std.string_length("hello");    # => `5
std.string_concat("a", "b");   # => "ab"
std.string_substring("hello", `1, `4);  # => "ell"
std.string_split("a,b,c", ","); # => ["a", "b", "c"]
std.string_join(["a","b"], "-"); # => "a-b"
std.string_upper("Hi");        # => "HI"
std.string_lower("HI");        # => "hi"
```

### Q: 列表常用操作？
**A**: 
```tanexscript
std.list_map([`1`,`2`], [*x] => { $ x * `2; });      # => [`2`,`4`]
std.list_filter([`1`,`2`,`3`], [*x] => { $ x % `2 == `0; });  # => [`2`]
std.list_reduce([`1`,`2`,`3`], [*acc,*x] => { $ acc + x; }, `0); # => `6
std.list_find([`1`,`2`,`3`], [*x] => { $ x > `2; });  # => `3
std.list_sort([`3`,`1`,`2`]);  # => [`1`,`2`,`3`]
std.list_reverse([`1`,`2`]);   # => [`2`,`1`]
std.list_slice([`1`,`2`,`3`], `1, `3); # => [`2`,`3`]
std.list_contains([`1`,`2`], `2);       # => true
```

### Q: 数学函数有哪些？
**A**: 
```tanexscript
import "maths" = *math;
math.abs(`-10);           # => `10
math.gcd(`48`, `18);      # => `6
math.factorial(`5);       # => `120
math.sqrt(`16);           # => '4.0
math.pi;                  # => '3.1416
math.fibonacci(`10);      # => `55
```

### Q: 进制转换怎么用？
**A**: 
```tanexscript
import "numeral_system" = *ns;
ns.binary_to_hexadecimal("1010");   # => "A"
ns.hexadecimal_to_binary("FF");     # => "11111111"
ns.integer_to_binary(`10);          # => "1010"
ns.binary_to_integer("1010");       # => `10
```

### Q: Base64 编解码？
**A**: 
```tanexscript
import "encoding.base_sixty_four" = *b64;
b64.base_sixty_four_encode([`72`,`101`,`108`,`108`,`111`]); # => "SGVsbG8="
b64.base_sixty_four_decode("SGVsbG8=");                      # => [`72`,`101`,`108`,`108`,`111`]
```

### Q: JSON 序列化/解析？
**A**: 
```tanexscript
import "json" = *json;
json.stringify(`42);              # => "42"
json.stringify(["a", `1`]);       # => "[\"a\",1]"
json.parse("42");                 # => `42
json.parse("[1,2,3]");            # => [`1`,`2`,`3`]
```

### Q: 随机数怎么生成？
**A**: 
```tanexscript
import "random" = *rand;
rand.set_seed(`12345);
rand.random();               # => 0 到 2^31-1
rand.random_integer(`10);    # => 0-9
rand.random_range(`5`, `15); # => 5-14
rand.random_choice(["a","b"]); # => "a" 或 "b"
rand.shuffle([`1`,`2`,`3`]); # => 打乱顺序
rand.random_boolean();       # => true/false
```

### Q: 位运算函数？
**A**: 
```tanexscript
import "bit" = *bit;
bit.bit_and(`5`, `3);    # => `1
bit.bit_or(`5`, `3);     # => `7
bit.bit_xor(`5`, `3);    # => `6
bit.bit_not(`5);         # => `2
bit.bit_left_shift(`3`, `2);  # => `12
bit.bit_right_shift(`12`, `2); # => `3
```

---

## 性能与最佳实践

### Q: 标准库函数比手写循环快吗？
**A**: **是的**。标准库高阶函数（`list_map`/`list_filter`/`list_reduce` 等）内部优化，减少解释器开销，比手写 `for` 循环更快。

### Q: 字符串拼接用 `+` 还是 `String.push_str`？
**A**: 大量拼接用 `String.push_str` 或 `List` + `join`，**避免** `+` 循环拼接（O(n²)）。

```tanexscript
# 慢
* s = "";
for(* i, list, { s = s + i.string(); });

# 快
* sb = String{};
for(* i, list, { sb.push_str(i.string()); });
```

### Q: 如何避免递归栈溢出？
**A**: 
- 改写为 `$$` 循环或 `cycle`
- 调大 `TANEX_RECURSION_LIMIT` 环境变量
- 使用尾递归优化模式（手动实现迭代）

### Q: 标准库有哪些模块？
**A**: 8 个核心模块：

| 模块 | 导入名 | 核心功能 |
|------|--------|----------|
| `standard` | `standard` | 核心扩展：类型构造、I/O、反射、控制流辅助 |
| `maths` | `maths` | 数学函数与常量 |
| `numeral_system` | `numeral_system` | 2/8/10/16 进制互转 |
| `encoding.ascii` | `encoding.ascii` | ASCII 编解码、字符分类 |
| `encoding.base_sixty_four` | `encoding.base_sixty_four` | Base64 编解码 |
| `json` | `json` | JSON 序列化/解析 |
| `random` | `random` | LCG 随机数生成器 |
| `bit` | `bit` | 位运算、二进制转换 |

---

## 常见错误

### Q: `import "maths"` 报错 "Module not found"？
**A**: 确保：
1. 标准库文件在安装目录 `run/` 下
2. `TANEX_LIB_PATH` 包含标准库路径
3. 拼写正确（区分大小写）

### Q: `std.list_map` 报错 "Type does not support operator"？
**A**: 确保回调函数返回值类型正确，且列表元素类型兼容。

### Q: `json.stringify` 报错 "nan/infinite 不是合法的 JSON 值"？
**A**: JSON 标准不支持 `nan`/`infinite`，序列化前过滤或转换。

---

## 相关链接

- [标准库参考](../library/) — 8 个模块逐条目规范
- [教程：快速上手](../tutorial/intro.md) — 入门示例
- [专题指南：性能优化](../howto/performance.md) — 标准库性能指南
- [语言参考：模块系统](../reference/modules.md) — import/-> 语义