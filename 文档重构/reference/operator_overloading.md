# 运算符重载

> 对标 [Python Special Method Names](https://docs.python.org/zh-cn/3.16/reference/datamodel.html#special-method-names)
>
> Tanex Script 通过**类型特殊成员**实现运算符重载。用户在类型上注册特殊成员，运行时识别并调用，实现自定义运算符行为。

---

## 1. 注册方式

```tanex script
*** TypeName.special_member = [*self, *args...] => { ... };
```

- 在类型对象上用 `***` 声明常量成员，绑定函数值
- 运行时遇到对应运算符时，查找左操作数类型(或特定规则)的特殊成员并调用
- 特殊成员为常量，注册后不可修改(除非类型 `addable=true` 允许外部新增)

---

## 2. 特殊成员完备映射表

| 运算符 | 查找特殊成员 | 查找位置 | 签名 | 返回期望 | 备注 |
|--------|--------------|----------|------|----------|------|
| `+` | `addition` | 左类型 | `(self, other)` | 运算结果 |  |
| `-` | `subtract` | 左类型 | `(self, other)` | 运算结果 |  |
| `*` | `multiply` | 左类型 | `(self, other)` | 运算结果 |  |
| `/` | `divide` | 左类型 | `(self, other)` | 运算结果 |  |
| `\` | `exactly_divisible` | 左类型 | `(self, other)` | 运算结果 | 整除 |
| `%` | `modulo` | 左类型 | `(self, other)` | 运算结果 |  |
| `^` | `power` | 左类型 | `(self, other)` | 运算结果 |  |
| `>` | `greater` | 左类型 | `(self, other)` | `Boolean` | 兜底组合 |
| `<` | `less` | 左类型 | `(self, other)` | `Boolean` | 兜底组合 |
| `>=` | `greater_equal` | 左类型 | `(self, other)` | `Boolean` | 兜底 `!less` |
| `<=` | `less_equal` | 左类型 | `(self, other)` | `Boolean` | 兜底 `!greater` |
| `==` | `equal` | 左类型 | `(self, other)` | `Boolean` | 兜底 `!not_equal` |
| `!=` | `not_equal` | 左类型 | `(self, other)` | `Boolean` | 兜底 `!equal` |
| `+` (一元) | `positive` | 操作数类型 | `(self)` | 运算结果 | 缺失报错(内置数值类除外) |
| `-` (一元) | `negative` | 操作数类型 | `(self)` | 运算结果 | 同上 |
| `<<` | `string` | **右**类型 | `(self)` | `String`(字符码链表) | 必须返回字符码链表 |
| `a[b]` | `index` | **左**类型 | `(self, key)` | 值/`Address`/带`value`实例 |  |
| `a in b` | `include` | **右**类型 | `(container, element)` | `Boolean` | 优先，兜底 `index`+`size` |
| 真值判定 | `boolean` | 操作数类型 | `(self)` | `Integer`/`Boolean` | 缺失默认真 |
| 构造 | `initialize` | 类型对象 | `(self, args...)` | 无要求 | 缺失不可带参构造 |
| 三路比较 | `compare` | 左类型 | `(self, other)` | `Integer`/`Number`(负/零/正) | 最后兜底 |

---

## 3. 比较兜底调用规则(解释器层实现)

当运算符对应的特殊成员未定义时，解释器按以下顺序**自动组合**：

| 运算符 | 直接特殊成员 | 组合兜底(优先) | `compare` 兜底 | 对象同一性兜底 |
|--------|--------------|----------------|----------------|----------------|
| `>` | `greater` | `!(less \|\| equal)` | `compare > 0` | `false` |
| `<` | `less` | `!(greater \|\| equal)` | `compare < 0` | `false` |
| `>=` | `greater_equal` | `!less` | `compare >= 0` | 同一对象 |
| `<=` | `less_equal` | `!greater` | `compare <= 0` | 同一对象 |
| `==` | `equal` | `!not_equal` | `compare == 0` | 同一对象 |
| `!=` | `not_equal` | `!equal` | `compare != 0` | 非同一对象 |

- **机制**：被兜底调用的方法通过调用参数标记知晓“兜底场景”，避免无限递归
- **最小实现**：类型仅定义 `less` 与 `equal`(或仅 `compare`)，即可获得全部六个比较运算符
- **`type_type` 自身**：不内置 `equal`，无默认比较行为，比较退化到对象同一性

---

## 4. 完整注册示例

### 4.1 向量类型 `Vec2`

```tanex script
* Vec2 = type_type{};

# 构造器
*** Vec2.initialize = [* self, * x, * y] => {
    self.x = x;
    self.y = y;
};

# 字符串转换(供 << 输出)
*** Vec2.string = [* self] => {
    $ "Vec2(" + self.x.string() + ", " + self.y.string() + ")";
};

# 加法重载
*** Vec2.addition = [* self, * other] => {
    $ Vec2{self.x + other.x, self.y + other.y};
};

# 数乘重载
*** Vec2.multiply = [* self, * scalar] => {
    $ Vec2{self.x * scalar, self.y * scalar};
};

# 比较(仅实现 less + equal，自动获得其余四个)
*** Vec2.less = [* self, * other] => {
    $ (self.x < other.x) || (self.x == other.x && self.y < other.y);
};
*** Vec2.equal = [* self, * other] => {
    $ self.x == other.x && self.y == other.y;
};

# 封闭类型(禁止外部新增成员)
*** Vec2.addable = false;
```

**使用**：
```tanex script
* v1 = Vec2{`1`, `2`};
* v2 = Vec2{`3`, `4`};
std.standard_output << (v1 + v2);  # => Vec2(4, 6) #;
std.standard_output << (v1 * `2`); # => Vec2(2, 4) #;
v1 < v2;  # => true (自动兜底) #;
v1 >= v2; # => false (自动兜底) #;
```

---

### 4.2 矩阵类型 `Matrix`(演示索引重载)

```tanex script
* Matrix = type_type{};
*** Matrix.initialize = [* self, * rows, * cols] => {
    self.rows = rows;
    self.cols = cols;
    self.data = List{};
    * r = `0;
    { r < rows } $$ {
        * c = `0;
        { c < cols } $$ {
            self.data.append(`0);
            c = c + `1;
        };
        r = r + `1;
    };
};

# 下标访问：m[row, col] 语法需用列表键
*** Matrix.index = [* self, * key] => {
    * row = key[`0];
    * col = key[`1];
    * idx = row * self.cols + col;
    $ self.data.index(idx);
};

# 赋值支持：m[row, col] = val
```

**使用**：
```tanex script
* m = Matrix{`2`, `3`};
m[`0`, `1`] = `42;
m[`0`, `1`];  # => `42 #;
```

---

### 4.3 容器类型实现 `include`(高效 `in` 判定)

```tanex script
* HashSet = type_type{};
*** HashSet.initialize = [* self] => {
    self.buckets = Dictionary{};  # 假设有字典类型
};

*** HashSet.include = [* self, * elem] => {
    $ self.buckets.has_key(elem.string());
};

*** HashSet.add = [* self, * elem] => {
    self.buckets.set(elem.string(), true);
};
```

**使用**：
```tanex script
* set = HashSet{};
set.add("hello");
set.add("world");
"hello" in set;  # => true (调用 include，O(1)) #;
"foo" in set;    # => false #;
```

---

## 5. 注意事项与最佳实践

### 5.1 特殊成员签名规范

| 特殊成员 | 推荐签名 | 说明 |
|----------|----------|------|
| 算术/比较 | `(self, other)` | `other` 类型不限，建议内部类型检查 |
| 一元正负 | `(self)` | 返回同类型或兼容类型 |
| `boolean` | `(self)` | 返回 `Integer`/`Boolean`，按真值解释 |
| `string` | `(self)` | **必须**返回 `String`(字符码链表) |
| `index` | `(self, key)` | 返回值/`Address`/带`value`实例 |
| `include` | `(container, element)` | 返回 `Boolean`/`Integer` |
| `initialize` | `(self, args...)` | 在 `self` 上设置成员，通常无返回 |

### 5.2 常见错误

```tanex script
# ❌ 错误：string 返回非 String 类型
*** BadType.string = [* self] => { $ `123; };  # 返回 Integer，<< 会报错

# ✅ 正确：string 返回字符码链表
*** GoodType.string = [* self] => { $ "GoodType"; };

# ❌ 错误：忘记注册 initialize 却带参构造
*** NoInit = type_type{};
NoInit{`1};  # 报错：类型没有定义 init 构造器

# ✅ 正确：显式注册 initialize
*** HasInit = type_type{};
*** HasInit.initialize = [* self, * v] => { self.value = v; };
HasInit{`1};  # 正常
```

### 5.3 性能建议

- **避免在特殊成员中分配大量临时对象**：`addition` 等高频调用应尽量原地计算或复用
- **实现 `compare` 替代 6 个比较成员**：仅一个三路比较即可获得全部比较运算符，减少代码量
- **优先实现 `include` 而非依赖 `index` 兜底**：`in` 判定时 `include` 为 O(1) 或 O(log n)，兜底遍历为 O(n)

### 5.4 行为控制标记配合

```tanex script
* Immutable = type_type{};
*** Immutable.addable = false;  # 封闭类型，外部不可新增成员
*** Immutable.external_read_only = {"config": true};  # config 仅内部可写
```

---

## 6. 内置类型重载表(参考)

| 类型 | 已注册特殊成员 | 可重载 |
|------|----------------|--------|
| `Integer` | 无(内置算术直接用数值运算) | 否(原类型特殊) |
| `Number` | `addition`、`subtract`...`string`、`boolean`、`greater`... | 是 |
| `String` | `string`、`boolean`、`index`、`include` | 是 |
| `Boolean` | 7算术、`string`、`boolean` | 是 |
| `List` | `string`、`boolean`、`index`、`include`、`append` | 是 |
| 用户类型 | 无(需显式注册) | 是 |

---

## 相关链接

- [类型系统](types.md) — 特殊成员槽位、真值判定、继承机制
- [表达式](expressions.md) — 运算符优先级、求值顺序
- [内置对象参考](../builtins/) — 核心类型完整规范
- [教程：自定义类型](../tutorial/advanced.md#自定义类型与运算符重载) — 入门示例
- [标准库：bit](../library/bit.md) — 位运算函数(非运算符重载)