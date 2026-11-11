# 类型设计模式

> Tanex Script 自定义类型的实战设计模式。

---

## 1. 封装与不变量

### 1.1 只读成员 (`external_read_only`)

```tanex script
* Config = type_type{};
*** Config.initialize = [* self, * api_key, * timeout] => {
    self.api_key = api_key;
    self.timeout = timeout;
};

# api_key 仅内部可写，外部只读
*** Config.external_read_only = {"api_key": true};

* cfg = Config{"secret_key", `30};
cfg.timeout = `60;      # ✅ 允许
# cfg.api_key = "hacked";  # ❌ 报错：成员外部只读
```

### 1.2 封闭类型 (`addable = false`)

```tanex script
* ImmutablePoint = type_type{};
*** ImmutablePoint.initialize = [* self, * x, * y] => { self.x = x; self.y = y; };
*** ImmutablePoint.addable = false;  # 禁止外部新增成员

* p = ImmutablePoint{`1`, `2`};
# p.z = `3;  # ❌ 报错：类型不可新增成员
```

### 1.3 私有成员约定 (下划线前缀)

```tanex script
* Counter = type_type{};
*** Counter.initialize = [* self] => { self._count = `0; };
*** Counter.increment = [* self] => { self._count = self._count + `1; };
*** Counter.get = [* self] => { $ self._count; };

* c = Counter{};
c.increment();
c.get();  # => `1 #;
# 约定：_count 为内部实现细节，外部不应直接访问
```

---

## 2. 继承与多态

### 2.1 基础继承

```tanex script
* Animal = type_type{};
*** Animal.initialize = [* self, * name] => { self.name = name; };
*** Animal.speak = [* self] => { $ "... (silence)"; };

* Dog = type_type{};
*** Dog.inherit = Animal;  # 复制 Animal 所有成员(除三字段)
*** Dog.speak = [* self] => { $ "Woof! " + self.name; };

* Cat = type_type{};
*** Cat.inherit = Animal;
*** Cat.speak = [* self] => { $ "Meow~ " + self.name; };

* dog = Dog{"Buddy"};
* cat = Cat{"Whiskers"};
dog.speak();  # => "Woof! Buddy" #;
cat.speak();  # => "Meow~ Whiskers" #;
```

### 2.2 抽象基类模式

```tanex script
* Shape = type_type{};
# 未实现 area，子类必须实现
*** Shape.area = [* self] => { <- error{"area() not implemented"}; };

* Circle = type_type{};
*** Circle.inherit = Shape;
*** Circle.initialize = [* self, * r] => { self.r = r; };
*** Circle.area = [* self] => { $ '3.14159' * self.r * self.r; };

* Rect = type_type{};
*** Rect.inherit = Shape;
*** Rect.initialize = [* self, * w, * h] => { self.w = w; self.h = h; };
*** Rect.area = [* self] => { $ self.w * self.h; };
```

### 2.3 Mixin 组合 (通过手动复制成员)

```tanex script
* Loggable = type_type{};
*** Loggable.log = [* self, * msg] => { std.standard_output << "[LOG] " + msg + "\n"; };

* Serializable = type_type{};
*** Serializable.to_json = [* self] => { $ json.stringify(self); };

* User = type_type{};
*** User.initialize = [* self, * name] => { self.name = name; };
# 手动混入成员
*** User.log = Loggable.log;
*** User.to_json = Serializable.to_json;

* u = User{"Alice"};
u.log("User created");  # => [LOG] User created #;
```

---

## 3. 运算符重载实战

### 3.1 数学向量 `Vec2`

```tanex script
* Vec2 = type_type{};
*** Vec2.initialize = [* self, * x, * y] => { self.x = x; self.y = y; };
*** Vec2.string = [* self] => { $ "Vec2(" + self.x.string() + ", " + self.y.string() + ")"; };

# 向量加法
*** Vec2.addition = [* self, * other] => { $ Vec2{self.x + other.x, self.y + other.y}; };
# 数乘
*** Vec2.multiply = [* self, * k] => { $ Vec2{self.x * k, self.y * k}; };
# 点积 (自定义运算符用函数)
*** Vec2.dot = [* self, * other] => { $ self.x * other.x + self.y * other.y; };
# 模长
*** Vec2.norm = [* self] => { math.square_root(self.x * self.x + self.y * self.y); };

* v1 = Vec2{`3`, `4`};
* v2 = Vec2{`1`, `2`};
std.standard_output << (v1 + v2);  # => Vec2(4, 6) #;
std.standard_output << (v1 * `2`); # => Vec2(6, 8) #;
v1.dot(v2);  # => `11 #;
v1.norm();   # => '5.0 #;
```

### 3.2 复数类型 `Complex`

```tanex script
* Complex = type_type{};
*** Complex.initialize = [* self, * re, * im] => { self.re = re; self.im = im; };
*** Complex.string = [* self] => { $ self.re.string() + (self.im >= `0 ? "+" : "") + self.im.string() + "i"; };

*** Complex.addition = [* a, * b] => { $ Complex{a.re + b.re, a.im + b.im}; };
*** Complex.multiply = [* a, * b] => {
    $ Complex{a.re * b.re - a.im * b.im, a.re * b.im + a.im * b.re};
};
*** Complex.equal = [* a, * b] => { $ a.re == b.re && a.im == b.im; };

* c1 = Complex{`1`, `2`};
* c2 = Complex{`3`, `4`};
std.standard_output << (c1 + c2);   # => 4+6i #;
std.standard_output << (c1 * c2);   # => -5+10i #;
```

### 3.3 矩阵类型 `Matrix` (下标重载)

```tanex script
* Matrix = type_type{};
*** Matrix.initialize = [* self, * rows, * cols] => {
    self.rows = rows;
    self.cols = cols;
    self.data = List{};
    * r = `0;
    { r < rows } $$ {
        * c = `0;
        { c < cols } $$ { self.data.append(`0); c = c + `1; };
        r = r + `1;
    };
};

# 下标访问：m[row, col] 需用列表键 [row, col]
*** Matrix.index = [* self, * key] => {
    * row = key[`0];
    * col = key[`1];
    * idx = row * self.cols + col;
    $ self.data.index(idx);
};

# 赋值支持：m[row, col] = val
*** Matrix.addition = [* self, * other] => {  # 复用 addition 做逐元素加
    * r = Matrix{self.rows, self.cols};
    * i = `0;
    { i < self.data.size } $$ {
        r.data.index(i) = self.data.index(i) + other.data.index(i);
        i = i + `1;
    };
    $ r;
};

* m1 = Matrix{`2`, `2`};
m1[`0`, `1`] = `5;
m1[`0`, `1`];  # => `5 #;
```

---

## 4. 容器与集合类型

### 4.1 高效 `in` 判定 (`include`)

```tanex script
* HashSet = type_type{};
*** HashSet.initialize = [* self] => { self.buckets = Dictionary{}; };
*** HashSet.add = [* self, * elem] => { self.buckets.set(elem.string(), true); };
*** HashSet.include = [* self, * elem] => { $ self.buckets.has_key(elem.string()); };

* set = HashSet{};
set.add("hello");
set.add("world");
"hello" in set;  # => true (O(1) 调用 include) #;
"foo" in set;    # => false #;
```

### 4.2 有序映射 `TreeMap` (实现 `index` 兜底遍历)

```tanex script
* TreeMap = type_type{};
*** TreeMap.initialize = [* self] => { self.root = none; self.size = `0; };
*** TreeMap.set = [* self, * k, * v] => { /* BST 插入 */ };
*** TreeMap.get = [* self, * k] => { /* BST 查找 */ };
*** TreeMap.index = [* self, * idx] => { /* 中序遍历第 idx 个 */ };
*** TreeMap.size = [* self] => { $ self.size; };

# 现在可用 for 遍历、in 判定(兜底 index)
```

---

## 5. 行为控制清单

| 场景 | 推荐做法 |
|------|----------|
| 禁止外部扩展成员 | `*** Type.addable = false;` |
| 保护敏感字段只读 | `*** Type.external_read_only = {"field": true};` |
| 类型作为常量/单例 | `*** Type.addable = false; *** Type.initialize = [*self] => { ... }; *** instance = Type{}; *** public = ["instance"];` |
| 需要比较 | 仅实现 `less` + `equal`，或实现 `compare` |
| 需要 `in` 判定 | 优先实现 `include` (O(1)/O(log n))，否则实现 `index` + `size` (O(n)) |
| 需要 `<<` 输出 | 必须实现 `string` 返回字符码链表 |
| 需要下标访问 | 实现 `index` 返回值/`Address`/带`value`实例 |
| 需要一元 `+/-` | 实现 `positive`/`negative` |

---

## 6. 完整示例：不可变记录类型 `Record`

```tanex script
* Record = type_type{};

# 构造器：参数列表动态设置字段
*** Record.initialize = [* self, * fields] => {
    * i = `0;
    { i < fields.size } $$ {
        * kv = fields.index(i);
        self.(kv[`0]) = kv[`1];  # 动态成员名 (需解释器支持)
        i = i + `1;
    };
    # 封闭 & 只读
    *** self.addable = false;
    *** self.external_read_only = {};
    * k = `0;
    { k < fields.size } $$ {
        self.external_read_only[fields.index(k)[`0]] = true;
        k = k + `1;
    };
};

# 访问器
*** Record.get = [* self, * key] => { $ self.key; };

# 比较：逐字段比较
*** Record.equal = [* a, * b] => {
    * keys = a.members_of();
    * i = `0;
    { i < keys.size } $$ {
        a.get(keys.index(i)) != b.get(keys.index(i)) ? { $ false; } : {};
        i = i + `1;
    };
    $ true;
};

* person = Record{["name", "Alice"], ["age", `30]};
person.get("name");  # => "Alice" #;
# person.age = `31;  # ❌ 报错：成员外部只读
```

---

## 相关链接

- [语言参考：类型系统](../reference/types.md) — 完整类型规范
- [语言参考：运算符重载](../reference/operator_overloading.md) — 特殊成员完整映射
- [内置对象：核心类型](../builtins/) — 内置类型重载参考
- [专题指南：错误处理](error_handling.md) — 类型错误捕获
- [专题指南：性能优化](performance.md) — 类型设计性能影响