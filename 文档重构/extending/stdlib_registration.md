# 标准库注册机制

> 解释器启动时如何注册内置类型、函数、特殊成员。

---

## 1. 内置类型注册

```python
def register_builtin_type(name: str, type_obj: TSType) -> None:
    """在全局作用域声明常量类型标识符"""
    addr = interpreter.address_space.allocate()
    interpreter.global_scope.declare(name, addr)
    interpreter.address_space.write(addr, type_obj)
    interpreter.address_space.mark_const(addr)

# 引导库初始化时调用
register_builtin_type("type_type", type_type_obj)
register_builtin_type("integer", integer_type_obj)
register_builtin_type("number", number_type_obj)
register_builtin_type("string", string_type_obj)
register_builtin_type("boolean", boolean_type_obj)
register_builtin_type("none_type", none_type_obj)
register_builtin_type("nan_type", nan_type_obj)
register_builtin_type("infinite_type", infinite_type_obj)
register_builtin_type("list", list_type_obj)
register_builtin_type("code", code_type_obj)
register_builtin_type("address", address_type_obj)
register_builtin_type("error", error_type_obj)
register_builtin_type("warning", warning_type_obj)
register_builtin_type("library", library_type_obj)
```

---

## 2. 内置函数注册

```python
def register_builtin_function(name: str, py_callable: Callable) -> None:
    """将 Python 函数包装为 TSFunction 注册到全局作用域"""
    fn_val = make_function_from_python(py_callable)
    addr = interpreter.address_space.allocate()
    interpreter.global_scope.declare(name, addr)
    interpreter.address_space.write(addr, fn_val)
    interpreter.address_space.mark_const(addr)

def make_function_from_python(py_callable: Callable) -> TSFunction:
    """将 Python 函数包装为可被 Tanex 调用的 TSFunction"""
    # 创建参数信息 (从函数签名推断)
    params = inspect_signature(py_callable)
    code = TSCode(
        statements=[],  # 空语句，实际执行在 Python 侧
        scope=None,
        params=params
    )
    return TSFunction(code, closure_scope=interpreter.global_scope)

# 标准库函数注册示例
register_builtin_function("print", py_print)
register_builtin_function("read_line", py_read_line)
register_builtin_function("time_now", py_time_now)
```

### Python 函数签名约定

```python
def py_print(*args: TSValue) -> TSValue:
    """Python 实现的 print，参数为 TSValue 列表"""
    for arg in args:
        print(arg.ts_repr(), end=" ")
    print()
    return args[-1] if args else TSNone.INSTANCE

def py_factorial(n: TSInteger) -> TSInteger:
    """单参数函数"""
    val = n.value
    if val < 0:
        raise TSArithError("factorial: argument cannot be negative")
    result = 1
    for i in range(2, val + 1):
        result *= i
    return make_integer(result)
```

---

## 3. 特殊成员注册

```python
def register_special_member(type_obj: TSType, member_name: str, py_callable: Callable) -> None:
    """在类型对象上注册特殊成员 (运算符重载)"""
    fn_val = make_function_from_python(py_callable)
    type_obj.special_members[member_name] = fn_val

# 引导库初始化时注册核心类型特殊成员
# Boolean 类型
register_special_member(boolean_type, "boolean", py_boolean_truthy)
register_special_member(boolean_type, "addition", py_boolean_add)
register_special_member(boolean_type, "subtract", py_boolean_sub)
# ... 7 个算术

# Number 类型
register_special_member(number_type, "addition", py_number_add)
register_special_member(number_type, "string", py_number_str)
# ...

# String 类型
register_special_member(string_type, "string", py_string_str)
register_special_member(string_type, "index", py_string_index)
# ...

# List 类型
register_special_member(list_type, "string", py_list_str)
register_special_member(list_type, "index", py_list_index)
register_special_member(list_type, "include", py_list_include)
# ...

# type_type 自身
register_special_member(type_type, "initialize", py_type_initialize)
```

### 特殊成员 Python 实现模板

```python
def py_boolean_truthy(self_val: TSBoolean) -> TSValue:
    """Boolean.boolean: 返回自身存储值"""
    return make_integer(self_val.value)

def py_number_add(left: TSNumber, right: TSNumber) -> TSNumber:
    """Number.addition: 精确十进制加法"""
    # 对齐小数位
    d1 = left.scale
    d2 = right.scale
    max_d = max(d1, d2)
    b1 = left.back * (10 ** (max_d - d1))
    b2 = right.back * (10 ** (max_d - d2))
    carry = (b1 + b2) // (10 ** max_d)
    new_back = (b1 + b2) % (10 ** max_d)
    new_front = left.front + right.front + carry
    return make_number(new_front, new_back, max_d)

def py_string_str(self_val: TSString) -> TSString:
    """String.string: 返回自身数据链表"""
    return self_val  # String 已持有 List 数据

def py_list_index(self_val: TSList, key: TSInteger) -> TSValue:
    """List.index: 返回第 key 个元素"""
    return self_val.index(key.value)
```

---

## 4. 标准库模块注册

```python
def register_standard_library(interpreter: TanexInterpreter) -> None:
    """注册标准库模块 (编译为 .tscl，启动时加载)"""
    # 标准库以 .tscl 形式分发，放在安装目录 run/standard.tscl
    # 解释器启动时自动加载 (通过 import "standard")
    pass

# 用户代码中
# import "standard" = *std;
# std.standard_output << "hello\n";
```

---

## 5. 启动时注册顺序

```python
def initialize_builtins(interpreter: TanexInterpreter):
    """按依赖顺序注册所有内置内容"""
    
    # 1. 创建基础类型对象 (空壳)
    create_core_type_shells(interpreter)
    
    # 2. 注册基础类型到全局作用域
    register_core_types(interpreter)
    
    # 3. 注册特殊成员 (引导库负责，或此处预注册)
    register_core_special_members(interpreter)
    
    # 4. 注册内置函数
    register_core_functions(interpreter)
    
    # 5. 注册核心常量 (true/false/none 等)
    register_core_constants(interpreter)
    
    # 6. 引导库执行 (填充特殊成员、定义控制流函数)
    execute_bootstrap(interpreter)
    
    # 7. 注册标准库模块路径
    register_stdlib_paths(interpreter)
```

---

## 相关链接

- [解释器嵌入](embedding.md) — 使用注册机制进行嵌入开发
- [核心执行器](interpreter.md) — 特殊成员调度
- [运行时值模型](values.md) — 值类型定义
- [语言参考：类型系统](../reference/types.md) — 特殊成员槽位完备表
- [引导库内部规范](../reference/runtime_internals.md#2-核心类型初始化规范) — 引导库初始化逻辑