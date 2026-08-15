# Tanex Script

Tanex Script 是一种编程语言，允许人们使用它创作。

---

## Tanex Script 语法

Tanex Script 拥有强大的语法

### 基本语法示例

```Tanex Script
# 每行末尾都要有结束符分号(表示代码的一句话结束) #;
a = '1';
# 缩进可以不加 #;
to_do_list = [
    "新增项目内容",
    "测试功能",
    "提交到Github"
];
#
这是注释。
支持多行的注释。
#;
@ a #
给 a 的注解内容
#;
output(?? a); # 输出给 a 的注解内容 #;

```

### 类型

+ 原类型: `integer`
  + 无包裹、无成员、无需导入的类型，表示一个无符号整数(正整数)
  + 如 `1` 、 `2` 、 `100`

+ 基类型: `type_type`
  + 所有类型的基本
  + 由解释器内部提供，用于定义复合类型

+ 复合类型
  + `number`
    + 以 **`'`** 开头，以 **`'`** 结尾，表示一个数字
    + 如 `'1'` 、 `'3.14'`
  + `string`
    + 以 **`"`** 开头，以 **`"`** 结尾，表示一个字符串
    + 如 `"哈哈哈"` 、 `"hello world\n"`
  + `none_type`
    + 只有 `none` 一个值，表示无
  + `infinite_type`
    + 只有两个状态，正无限与负无限，通过 `+` / `-` 运算得到
  + `nan_type`
    + 只有 `nan` 一个值，表示非数字
  + `boolean`
    + 只有 `true` 与 `false` 两个值，表示真假
  + `list`
    + 用 `[` 与 `]` 包裹数个值，并用 `,` 隔开
    + 如 `['1', "hi", ["hello", nan], none]`
  + `function_name` 与 `type_name`
    + 定义函数或类型后，它的名字就是一个 `function_name` / `type_name`
  + `address`
    + 每个变量都有地址，可以用 `/` 获取
    + `a = ["hello"]; /a[0]; # 获取a[0]的地址 #;`
  + `error`
    + 在捕获错误后，存储的错误详情就是一个 `error` 类型的值
    + 操作
      + 可以它的获取 `name.what` 常量
      + 可以执行 `name.throw()` ，与 `error` 的效果一样，但一个是成员函数，一个是普通函数
  + `warning`
    + 与 `error` 类似，只不过执行 `name.throw()` 后不会结束程序
  + `code`
    + `code` 类型就是一个代码块，用花括号包裹
    + 如

    ```Tanex Script
    {
      output('1');
      #
      注释
      #;
      a = input();
      output(a);
    }
    ```

### 运算符优先级

**优先级(从高到低):**

| 优先级 | 内容 | 说明 |
| -------- | ------ | ------ |
| 1 | 单值 | 单值 |
| 2 | `()` | 括号 |
| 3 | `$` | 返回 |
| 4 | `*[]` | 下标 |
| 4 | `* (单值,单值... )` | 函数调用 |
| 5 | `*.*` | 成员访问 |
| 6 | `!*` `~*` `*` `/` `**` `***` `<-` `return` `??` | 一元运算符 |
| 7 | `+*` `-*` | 正负 |
| 8 | `*n` `/n` | 地址运算 |
| 9 | `n*m` `n/m` `n%m` `n^m` `n\m` `n<<m` `n>>m` `n$$m` | 基础运算/输出/输入/循环符 |
| 10 | `n+m` `n-m` | 基础运算 |
| 11 | `<` `<=` `>` `>=` `in` | 比较/存在 |
| 12 | `==` `!=` `?` `\|` | 比较/三目/尝试 |
| 13 | `&&` | 与 |
| 14 | `\|\|` | 或 |
| 15 | `=>` | 匿名函数 |
| 16 | `=` | 赋值 |
| 17 | `*=` `/=` `%=` `^=` `&=` `\|=` `+=` `-=` `\=` | 复式赋值 |

+ 运算符详解
  + 一元运算符
    + `~`
      + 上一级的变量
      + 如

      ```Tanex Script
      str = "Hello ";
      for(*str, ["XiaoMin", "YeYe", "World"], {
        output(~str + str);
      });
      ```

    + `( )`
      + 括号里的内容先算
    + `+`
      + `+` 可以表示正数
      + 如 `+'1'`，表示正一
      + (注: 可以直接使用 `'+1'` 来表示)
    + `-`
      + `-` 可以表示负数（与 `+` 相反）
      + `-'1'` 则表示负一
      + (注: 可以直接使用 `'-1'` 来表示)
    + `*`
      + `*` 是解地址符
        + 可用于 `address` 类型
        + 如 `addr = /a; *addr; # 解地址获取a的值 #;`
      + `*` 也是声明符
        + `* name`
        + 返回声明 name 的地址
    + `/`
      + `/` 是取址符
      + 如 `a = none; /a; # 这里取了地址 #;`
    + `!`
      + `!` 表示非
      + 如 `a = true; output(! a); # 这里输出了 ! true (等于false) #;`
    + `**`
      + 声明引用变量
      + 如 `a = '1'; ** b = a; b = '5'; output(a); # 输出5 #;`
      + 返回声明 name 的地址
    + `<-`
      + 报错
      + 如 `<- error{["Error", "..."]};`
    + `***`
      + 声明常量/定义特殊name
      + 常量声明： `*** a = '100'`
      + 返回声明 name 的地址
      + 定义特殊函数：

      ```Tanex Sccript
      type(my_type, {
        # 定义类型 #;
        self.name = "";
        *** init = function([], {
          output("Hello, Welcome to use my type!\n");
        });
      });
      ```

    + `$`
      + 返回
      + 可以返回一个值
      + 如

      ```Tanex Script
      [] => {$"Hello World";};
      ```

    + `return`
      + 返回（与 `$` 功能相同，关键字别名）
      + 如 `return "Hello World";`

    + `# ... #`
      + 注释
      + 语法
        + `#...#` 多行注释，如

        ```Tanex Script
        #
        这是注释
        #;
        ```

    + `@ ... # ... #;`
      + 注解，注释的变种
      + 语法：`@ {标识符} # xxx #;`
      + `@` 与 `#` 之间为目标标识符，`#` 与 `#;` 之间为注解内容；标识符可省略，省略时表示文件级注解
      + 例如

        ```Tanex Script
        @ for #
        可以遍历一个可遍历值，每遍历一次执行一次操作。
        #;
        ```

      + 可在运行时通过 `?? n` 读取标识符 `n` 的注解内容字符串

    + `??`
      + 注解读取（有作用域）
      + 语法：`?? n` 或 `?? 库.成员`
      + 读取当前作用域中标识符的注解内容字符串；`?? 库.成员` 读取已导入库独立注解空间中的注解；查不到则报错「注解不存在」
      + 如 `output(?? for);` 输出 `for` 的注解内容；`output(?? standard.for);` 输出标准库 `for` 的注解内容

    + `break`
      + 退出一个循环
      + 例如

      ```Tanex Script
      for(*i, [1, 3, 5, 7, 9, 10, 11], {
        if(i % 2 == 0, {
          break;
        }, {
          output(i);
        })
      }); # 偶数后退出循环 #;
      ```

    + `->` (`import`)
      + 引入/导入
      + 用于引入 Tanex Script 文件(.tsuc)、已编译文件(.tscc)、文件夹(库)或已编译库(.tscl)
      + 在预编译阶段解析为 `import` 语句节点，运行时加载
      + 引入后只创建一个 `library` 类型的常量标识符，库内容通过该句柄访问（如 `lib.成员`），不会展开到全局作用域
      + 如 `-> "code.tsuc";`
      + 列表批量导入：`-> ["a", "b"];`，等价于 `-> "a"; -> "b";`
      + 列表批量导入并命名：`-> ["a", "b"] = [x, y];`，将 `a` 引入为 `x`，`b` 引入为 `y`
      + `import` 与 `->` 完全等价，如 `import ["a", "b"] = [x, y];`

  + 二元运算符
    + `+`
      + 可以对 `number` 类型进行加法处理，也可以对两个 `list` / `string` 类型值进行连接，还可以处理其他的表达式
      + 示例
        + `'20' + '15'`
        + `["28", "NuiYeYe"] + ["70", "LiDaYe"]`
        + `"hello" + " " + "world"`
        + `infinite + -infinite`
    + `-`
      + 可以对 `number` 类型进行减法处理，还可以处理其他的表达式
      + 示例
        + `'1' - '0.1'`
        + `-'1' - '1'`
        + `infinite - '1'`
    + `*`
      + 可以对 `number` 类型进行乘法处理，也可以处理多个 `list` / `string` 的拼接，还可以处理别的表达式
      + 示例
        + `'3.5' * '30'`
        + `-'5' * '4'`
        + `infinite * '1'`
        + `["XiaoMi", "HuaWei", "SanXin"] * 3`
        + `"HelloWorld" * 5`
      + 使用 `infinite` 或 `-infinite` 乘 `'0'` 会返回 `nan`
    + `/`
      + 可以对 `number` 类型进行除法处理，还可以处理其他的表达式
      + 示例
        + `'270' / '2.7'`
        + `infinite / '0'`
      + 可以用 `number` 除以 `'0'`，不会报错，会返回 `infinite`
    + `\`
      + `\` 相当于 `/` 的"整数版"，是整数除法
    + `%`
      + 可以对 `number` 类型进行取余处理，还可以处理其他的表达式
      + 示例
        + `'271' % '2.7'`
        + `infinite % '0'`
      + 可以用 `number` 取余 `'0'`，不会报错，会返回 `0`
    + `^`
      + 获取一个 `number` 类型值的 `number` 类型值次方，可以处理其他的表达式
      + 如 `'3' ^ '9'` 、`'3' ^ infinite`
    + `<<`
      + 输出。右操作数必须是注册了 `string` 特殊成员的对象，调用该成员得到字符码链表，交给左操作数（处理函数）处理，再逐字符输出
      + 如 `standard_output << "Hello"` 输出 `"Hello"`
    + `>>`
      + 输入。读取输入得到字符串，交给左操作数（处理函数）处理，结果填入右操作数（地址）
      + 如 `standard_output >> b` 把处理后的输入写入变量 `b`
    + `[ ]`
      + 获取值1的值2项内容(从`'0'`计算)
      + 如 `["1", true, '2']['0']`
    + `{ }`
      + 获取一个新的值
      + 如 `my_type{"Hello", "World"}` 返回一个 `my_type` 类型、属性值为 `"Hello"` 与 `"World"` 的值
    + `<` 、`>` 、`<=` 、`>=`
      + 做数字的比较，也有别的用法
    + `==` 、`!=`
      + 如果第一个值等于第二个值，`==` 返回 `true` ， `!=` 返回 `false`
      + 反之则结果相反
    + `=` 等相关操作符
      + `=` 可以为变量/常量赋值
      + 其他操作可以给变量/常量赋它与操作值的操作符操作后的值
    + `.`
      + 可以获取库中的某值/函数/类型等内容
      + 可以获取值的某成员
    + `in`
      + 存在符
      + 如果右值的类型有 `*** index` 成员函数，会对右值进行遍历，如果左值存在于右值，返回 `true`，否则返回 `false`
      + 如果右值不符合条件，报错
    + `=>`
      + 匿名函数
      + 与函数功能相同，但语法简单，不需要名字
      + 如
      + `[arg1, arg2] => { return(arg1 + arg2); }`

    + `$$`
      + 循环符
      + 返回循环结果
      + 如

      ```Tanex Script
      i = '1';
      {$i <= '10';} $$ {i += 1; $i - 1;};  # ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10'] #;
      ```

  + 三目运算符
    + `* ? * : *` 表示如果 ... 就返回 ... 否则返回 ...
    + `* | * : * | *`
      + 表示尝试
      + 如 `{this_is_a_error_function();} | *error_msg : {output("Find out a error! " + error_msg.what)} : {output("No error!")}` 表示尝试运行 `{this_is_a_error_function();}` ，报错就运行 `{output("Find out a error! " + error_msg.what)}` ，没报错就运行 `{output("No error!")}` ，声明一个变量 `error_msg` ，把它的地址传入，由于记录错误信息
  + 其他运算符
    + `;`
      + 每一句代码末尾都要加分号
    + `,`
      + 分割 `list` 值的每一项
+ 其他语法
  + 关键字别名（词法分析时自动转换）
    + `and` 等价于 `&&`
    + `or` 等价于 `||`
    + `not` 等价于 `!`
    + `is` 等价于 `==`
  + 函数调用
    + `function_name(参数, 参数, 参数, ...)`
  + 字符串特殊语法
    + 可以在字符串中写转义符
    + 含义:
      + \\n: 换行
      \\t: 制表符
      \\": "
      \\\\: \
      \\r: 回车
      \\b: 删除
      \\f: 翻页
      \\v: 垂直制表符

## 特殊函数

在Tanex Script中，`if`、`for`、`while`、`cycle`这些看似"控制结构"的语法，本质上确实是**函数调用**——这是Tanex Script语法设计的一个核心特点：用"函数+代码块参数"替代传统的"关键字+语法块"。

这些函数全部通过原生 Tanex Script 代码编写。

### 为什么会这样设计？

这种设计的核心思路是**"语法统一化"**：把所有逻辑控制（条件、循环等）都统一为"函数调用"的形式，减少语言中的"特殊关键字语法"，让语法规则更一致。

具体来说，这些结构本质上是**接受"代码块（`code`类型）"作为参数的函数**：
传统语言中，`if`是关键字，后面跟条件和语法块（如`if () {}`）；
但在Tanex Script中，`if`是一个函数，它的参数包括：条件（第一个参数）、成立时执行的代码块（第二个参数）、不
成立时执行的代码块（第三个参数）。

### 举个例子对比

以`if`为例：

**传统语言（如JavaScript）**：`if`是关键字，语法是特殊的

  ```js
  if (条件) {  // 关键字+语法块，非函数调用
  // 成立时的代码
  } else {
  // 不成立时的代码
  }
  ```

**Tanex Script**：`if`是函数，参数是条件和两个代码块

  ```Tanex Script
  if(条件, { # 函数名(参数1, 参数2, 参数3)，完全是函数 #;
  # 调用成立时的代码（参数2：code类型）#;
  }, {
  # 不成立时的代码（参数3：code类型） #;
  });

  ```

### 其他结构的函数本质

同样的逻辑适用于`for`、`while`、`cycle`：

`for(变量, 列表, {代码})`：`for`是函数，参数为"循环变量""遍历对象""循环体代码块"，函数内部逻辑是"遍历列

表，每次将元素赋值给变量，执行代码块"。

`while(条件, {代码})`：`while`是函数，参数为"循环条件""循环体代码块"，函数内部逻辑是"反复判断条件，为true时执行代码块"。

`cycle(次数, {代码})`：`cycle`是函数，参数为"循环次数""循环体代码块"，函数内部逻辑是"执行代码块指定次数"。

### 这种设计的优势

1. **语法规则更统一**：不需要记忆"关键字+特殊语法"（如`if`的`else`、`for`的`in`等），所有控制逻辑都遵循"函数名(参数列表)"的格式。
2. **代码块作为"一等公民"**：`code`类型的代码块可以像普通值一样传递给函数，这让逻辑复用更灵活（比如可以将代码块赋值给变量，再传递给`if`/`for`等函数）。
3. **扩展性更强**：如果需要自定义控制结构（比如"重试3次的循环"），可以直接定义一个类似的函数，而不需要修改语言本身的语法规则。

简单说，Tanex Script用"函数调用"的形式"模拟"了传统控制结构的功能，本质上是将"逻辑控制"封装成了可调用的函数，让语言更简洁、一致。这种设计在一些函数式编程语言（如Lisp）中也很常见，核心是"用函数抽象一切逻辑"。

---

## Tanex Script 解释器要求

### 编译时的token类型判定

| 类型 | 示例 | 说明 | 写法 |
| ------ | ------ | ------ | ------ |
| integer | 123 | 原类型，正整数 | `*` |
| string | "I'm a string\n" | 可以在字符串中放很多字符 | `"*"` |
| number | '123.1' | number可以表示数字(不分int/float) | `'*'` |
| list | ["1",["1","1"],"1", {to_number("1");}] | 可以在列表中放很多东西 | `[*, *, *...]` |
| code | {a = "12345678";output(a);} | 可以在代码块中放很多代码 | `{*; *; *; ...;}` |
| name | a | 变量/函数名/类名 | `*` |

**重要语法规则：**

+ **列表使用方括号**：`["1", "2", "3"]`
+ **代码块使用花括号**：`{a = "1"; output(a);}`
+ **数组访问使用后缀**：`arr[0]`
+ **name不可以包含数字**，如`1gr`, `4f5`是不合法的命名

### AST (抽象语法树) 格式

#### 解析示例

```tanex script
output(to_number("1") + to_number("3"));
```

解析结果：

```json
{
    "Tanex Script": [
        {
            "function": {
                "name": { "name": { "value": "output", "pos": [1, 1] } },
                "arg": {
                    "binary": {
                        "operator": "+",
                        "left": {
                            "function": {
                                "name": { "name": { "value": "to_number", "pos": [1, 8] } },
                                "arg": { "string": { "value": "\"1\"", "pos": [1, 18] } },
                                "pos": [1, 8]
                            }
                        },
                        "right": {
                            "function": {
                                "name": { "name": { "value": "to_number", "pos": [1, 23] } },
                                "arg": { "string": { "value": "\"3\"", "pos": [1, 33] } },
                                "pos": [1, 23]
                            }
                        },
                        "pos": [1, 20]
                    }
                },
                "pos": [1, 1]
            }
        }
    ]
}
```

若程序中含有[注解](注解.md)，编译结果的顶层还会增加 `annotations` 字段，以目标标识符为键、注解内容为值；存在文件级注解时还会增加 `annotation` 字段，如：

```json
{
    "Tanex Script": [],
    "annotations": {
        "for": "可以遍历一个可遍历值。"
    }
}
```

#### AST 映射规则

| 表达式 | AST格式 | 说明 |
| -------- | --------- | ------ |
| `~n` | `{"unary":{"operator":"~","operand":n,"pos":[l,c]}}` | 上级访问 |
| `!n` | `{"unary":{"operator":"!","operand":n,"pos":[l,c]}}` | 非 |
| `+n` | `{"unary":{"operator":"+","operand":n,"pos":[l,c]}}` | 正数 |
| `-n` | `{"unary":{"operator":"-","operand":n,"pos":[l,c]}}` | 负数 |
| `*n` | `{"unary":{"operator":"*","operand":n,"pos":[l,c]}}` | 解地址 |
| `/n` | `{"unary":{"operator":"/","operand":n,"pos":[l,c]}}` | 取地址 |
| `** n` | `{"unary":{"operator":"**","operand":n,"pos":[l,c]}}` | 声明引用变量 |
| `*** n` | `{"unary":{"operator":"***","operand":n,"pos":[l,c]}}` | 声明常量 |
| `<- n` | `{"unary":{"operator":"<-","operand":n,"pos":[l,c]}}` | 报错 |
| `$ n` | `{"unary":{"operator":"$","operand":n,"pos":[l,c]}}` | 返回 |
| `return n` | `{"unary":{"operator":"return","operand":n,"pos":[l,c]}}` | 返回 |
| `?? n` | `{"unary":{"operator":"??","operand":n,"pos":[l,c]}}` | 注解读取 |
| `n+m` | `{"binary":{"operator":"+","left":n,"right":m,"pos":[l,c]}}` | 加法 |
| `n-m` | `{"binary":{"operator":"-","left":n,"right":m,"pos":[l,c]}}` | 减法 |
| `n*m` | `{"binary":{"operator":"*","left":n,"right":m,"pos":[l,c]}}` | 乘法 |
| `n/m` | `{"binary":{"operator":"/","left":n,"right":m,"pos":[l,c]}}` | 除法 |
| `n\m` | `{"binary":{"operator":"\\","left":n,"right":m,"pos":[l,c]}}` | 整除 |
| `n%m` | `{"binary":{"operator":"%","left":n,"right":m,"pos":[l,c]}}` | 模运算 |
| `n^m` | `{"binary":{"operator":"^","left":n,"right":m,"pos":[l,c]}}` | 幂运算 |
| `n<<m` | `{"binary":{"operator":"<<","left":n,"right":m,"pos":[l,c]}}` | 输出 |
| `n>>m` | `{"binary":{"operator":">>","left":n,"right":m,"pos":[l,c]}}` | 输入 |
| `n$$m` | `{"binary":{"operator":"$$","left":n,"right":m,"pos":[l,c]}}` | 循环符 |
| `[n,m...]=>{n;}` | `{"binary":{"operator":"=>","left":{"list":...},"right":{"code":...},"pos":[l,c]}}` | 匿名函数 |
| `n < m` | `{"binary":{"operator":"<","left":n,"right":m,"pos":[l,c]}}` | 小于 |
| `n<=m` | `{"binary":{"operator":"<=","left":n,"right":m,"pos":[l,c]}}` | 小于等于 |
| `n==m` | `{"binary":{"operator":"==","left":n,"right":m,"pos":[l,c]}}` | 等于 |
| `n>m` | `{"binary":{"operator":">","left":n,"right":m,"pos":[l,c]}}` | 大于 |
| `n>=m` | `{"binary":{"operator":">=","left":n,"right":m,"pos":[l,c]}}` | 大于等于 |
| `n!=m` | `{"binary":{"operator":"!=","left":n,"right":m,"pos":[l,c]}}` | 不等于 |
| `n&&m` | `{"binary":{"operator":"&&","left":n,"right":m,"pos":[l,c]}}` | 逻辑与 |
| `n\|\|m` | `{"binary":{"operator":"\|\|","left":n,"right":m,"pos":[l,c]}}` | 逻辑或 |
| `n in m` | `{"binary":{"operator":"in","left":n,"right":m,"pos":[l,c]}}` | 存在符 |
| `n=m` | `{"assignment":{"operator":"=","left":n,"right":m,"pos":[l,c]}}` | 赋值 |
| `n+=m` | `{"assignment":{"operator":"+=","left":n,"right":m,"pos":[l,c]}}` | 加法赋值 |
| `n-=m` | `{"assignment":{"operator":"-=","left":n,"right":m,"pos":[l,c]}}` | 减法赋值 |
| `n*=m` | `{"assignment":{"operator":"*=","left":n,"right":m,"pos":[l,c]}}` | 乘法赋值 |
| `n/=m` | `{"assignment":{"operator":"/=","left":n,"right":m,"pos":[l,c]}}` | 除法赋值 |
| `n\=m` | `{"assignment":{"operator":"\\=","left":n,"right":m,"pos":[l,c]}}` | 整除赋值 |
| `n%=m` | `{"assignment":{"operator":"%=","left":n,"right":m,"pos":[l,c]}}` | 模赋值 |
| `n^=m` | `{"assignment":{"operator":"^=","left":n,"right":m,"pos":[l,c]}}` | 幂赋值 |
| `n&=m` | `{"assignment":{"operator":"&=","left":n,"right":m,"pos":[l,c]}}` | 与赋值 |
| `n\|=m` | `{"assignment":{"operator":"\|=","left":n,"right":m,"pos":[l,c]}}` | 或赋值 |
| `n ? a : b` | `{"ternary":{"operator":"?","condition":n,"true_branch":a,"false_branch":b,"pos":[l,c]}}` | 三目运算符 |
| `left \| err : catch : else` | `{"try":{"left":left,"error_arg":err,"catch_block":catch,"else_block":else,"pos":[l,c]}}` | 尝试/错误处理 |
| `n[m]` | `{"subscript":{"left":n,"right":m,"pos":[l,c]}}` | 下标访问 |
| `n{m1,m2...}` | `{"new":{"type":n,"include":[m1,m2...],"pos":[l,c]}}` | 创建实例 |
| `n.m` | `{"member":{"left":n,"right":{"name":{"value":m,"pos":[l,c]}},"pos":[l,c]}}` | 成员访问 |
| `f()` | `{"function":{"name":f_ast,"arg":[],"pos":[l,c]}}` | 无参函数调用 |
| `f(n1)` | `{"function":{"name":f_ast,"arg":[n1],"pos":[l,c]}}` | 单参函数调用 |
| `f(n1,n2...)` | `{"function":{"name":f_ast,"arg":[n1,n2,...],"pos":[l,c]}}` | 多参函数调用 |
| `break;` | `{"break":{"pos":[l,c]}}` | 退出循环 |
| `#...#` | 忽略（不加入AST） | 注释 |
| `@ 标识符 # 内容 #;` | 记录到 `annotations`，不加入AST；无标识符时记录到顶层 `annotation` | 注解 |
| `123` | `{"integer":{"value":"123","pos":[l,c]}}` | 整数字面量 |
| `'num'` | `{"number":{"value":"'num'","pos":[l,c]}}` | 数字字面量 |
| `"str"` | `{"string":{"value":"\"str\"","pos":[l,c]}}` | 字符串字面量 |
| `true`/`false` | `{"boolean":{"value":"true/false","pos":[l,c]}}` | 布尔值 |
| `none` | `{"none_type":{"value":"none","pos":[l,c]}}` | 空值 |
| `nan` | `{"nan_type":{"value":"nan","pos":[l,c]}}` | 非数 |
| `infinite` | `{"infinite_type":{"value":"infinite","pos":[l,c]}}` | 无限 |
| `name` | `{"name":{"value":"name","pos":[l,c]}}` | 标识符 |
| `[a,b,c]` | `{"list":{"items":[a,b,c],"pos":[l,c]}}` | 列表字面量 |
| `[a,]` | `{"list":{"items":[a,{"none_type":{"value":"none","pos":...}}],"pos":[l,c]}}` | 列表尾部逗号自动填充 `none` |
| `{...}` | `{"code":{"statements":[...],"pos":[l,c]}}` | 代码块 |

### 解析步骤

#### 第一步：词法分析

将字符串转换为多个token，按运算符、值、空格等区分，方便后面转JSON。

#### 第二步：语法分析

把token列表转换为AST字典，使用类似前缀表达式的算法解决，要考虑运算符的优先级。

例如：

```python
# "'1' + '1'" to tokens: {0: "'1'", 4: '+', 6: "'1'"}, so:
# input:
{0: "'1'", 4: '+', 6: "'1'"}
# output:
{
    "binary": {"operator": "+", "left": {"number": {"value": "'1'", "pos": [1, 1]}}, "right": {"number": {"value": "'1'", "pos": [1, 5]}}, "pos": [1, 4]}
}
```

### 实现要求

1. **词法分析器**：将Tanex Script代码分解为token序列
2. **语法分析器**：根据优先级规则构建AST
3. **错误处理**：提供清晰的错误信息和位置
4. **AST输出**：生成标准的JSON格式AST
5. **代码执行**：解释执行Tanex Script代码

### 核心特性

+ **语法统一化**：所有控制结构都是函数调用
+ **代码块一等公民**：code类型可以像普通值一样传递
+ **类型系统**：支持number、string、list、code、name、boolean、none_type、address等类型
+ **运算符重载**：支持自定义类型的运算符行为
+ **地址操作**：支持指针和地址操作
+ **错误处理**：内置try机制

这个设计让Tanex Script既保持了表达力，又具有很好的一致性和扩展性。

## 文件后缀

.tsuc (Tanex Script Uncompiled Code)

.tscc (Tanex Script Compiled Code)

.tscl (Tanex Script Compiled Libary)
