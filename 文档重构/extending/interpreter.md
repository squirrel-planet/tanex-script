# 核心执行器

> Tanex Script 解释器核心执行逻辑：AST 节点求值分发、控制流信号、特殊成员调度。

---

## 1. 核心求值入口

```python
def eval(ast_node: dict, scope: Scope, addr_space: AddressSpace) -> TSValue:
    """
    递归求值单个 AST 节点，返回运行时值。
    按节点类型键分发到对应处理函数。
    """
    if not ast_node:
        return TSNone.INSTANCE
    
    node_type = list(ast_node.keys())[0]
    node_data = ast_node[node_type]
    
    # 分发表
    handlers = {
        # 字面量
        "integer": eval_integer,
        "number": eval_number,
        "string": eval_string,
        "boolean": eval_boolean,
        "none_type": eval_none,
        "nan_type": eval_nan,
        "infinite_type": eval_infinite,
        
        # 标识符
        "name": eval_name,
        
        # 一元运算符
        "unary": eval_unary,
        
        # 二元运算符
        "binary": eval_binary,
        
        # 赋值
        "assignment": eval_assignment,
        
        # 三目/尝试
        "ternary": eval_ternary,
        "try": eval_try,
        
        # 复合结构
        "subscript": eval_subscript,
        "member": eval_member,
        "new": eval_new,
        "function": eval_function,
        "code": eval_code,
        "list": eval_list,
        
        # 零元/控制流
        "break": eval_break,
        "contiune": eval_continue,
        
        # 导入
        "import": eval_import,
        "include": eval_include,
    }
    
    handler = handlers.get(node_type)
    if not handler:
        raise TSCompileError(f"Unknown AST node type: {node_type}")
    
    return handler(node_data, scope, addr_space)
```

---

## 2. 控制流信号

```python
class BreakSignal(Exception):
    """break 零元运算符"""
    pass

class ContinueSignal(Exception):
    """contiune 零元运算符"""
    pass

class ReturnSignal(Exception):
    """$ / return 一元运算符"""
    def __init__(self, value: TSValue):
        self.value = value

class ErrorSignal(Exception):
    """<- 抛出错误"""
    def __init__(self, value: TSValue):
        self.value = value

class MultiLevelReturnSignal(Exception):
    """二元 $ 多层跳出"""
    def __init__(self, levels: int, value: TSValue):
        self.levels = levels
        self.value = value
```

### 信号处理约定

| 信号 | 捕获位置 | 行为 |
|------|----------|------|
| `BreakSignal` | `$$` 循环 | 立即退出循环，返回已收集列表 |
| `ContinueSignal` | `$$` 循环 | 结束本轮迭代，重新求值条件 |
| `ReturnSignal` | 函数调用、代码块 | 携带值提前结束，作为调用结果 |
| `ErrorSignal` | `\|` 尝试结构 | 携带错误值，绑定到 `*err` |
| `MultiLevelReturnSignal` | 函数/代码块边界 | 递减层数，层数归零时作为返回值 |

---

## 3. 特殊成员调度

### 3.1 二元运算符分发

```python
BINARY_OP_TO_SPECIAL = {
    "+": "addition", "-": "subtract", "*": "multiply", "/": "divide",
    "\\": "exactly_divisible", "%": "modulo", "^": "power",
    ">": "greater", "<": "less", ">=": "greater_equal", "<=": "less_equal",
    "==": "equal", "!=": "not_equal",
    "<<": "string",  # 特殊：右操作数
    "in": "include",  # 特殊：右操作数
    "|>": "pipe",     # 不可重载
    "&&": None, "||": None,  # 短路，不分发
    "?": None, ":": None,  # 三目/尝试，不分发
}

def dispatch_binary(op: str, left: TSValue, right: TSValue, 
                    scope: Scope, addr_space: AddressSpace) -> TSValue:
    """二元运算符分发：查左操作数类型特殊成员，回退内置"""
    
    # 短路运算符
    if op == "&&":
        return left if not ts_truthy(left) else right
    if op == "||":
        return left if ts_truthy(left) else right
    
    # 管道、三目、尝试结构不分发
    if op in ("|>", "?", ":", "in"):
        return eval_special_binary(op, left, right, scope, addr_space)
    
    # 常规二元运算符：查左类型特殊成员
    type_obj = left.ts_type()
    special_name = BINARY_OP_TO_SPECIAL.get(op)
    if special_name:
        member = type_obj.special_members.get(special_name)
        if member:
            return call_special(member, left, right, scope, addr_space)
    
    # 内置类型兜底
    return builtin_binary_op(op, left, right, scope, addr_space)
```

### 3.2 一元运算符分发

```python
UNARY_OP_TO_SPECIAL = {
    "+": "positive", "-": "negative", "!": "boolean", "~": "string",
    "*": None, "/": None, "**": None, "***": None,  # 声明/地址，特殊处理
    "&": None, "&&": None, "&&&": None,  # 连续声明
    "<-": None, "return": None, "$": None, "??": None, "type_of": None,
}

def dispatch_unary(op: str, operand: TSValue, 
                   scope: Scope, addr_space: AddressSpace) -> TSValue:
    """一元运算符分发"""
    
    special_name = UNARY_OP_TO_SPECIAL.get(op)
    if special_name:
        type_obj = operand.ts_type()
        member = type_obj.special_members.get(special_name)
        if member:
            return call_special(member, operand, scope, addr_space)
        # 内置数值类型兜底
        return builtin_unary_op(op, operand)
    
    # 声明/地址/控制流/注解运算符特殊处理
    return eval_special_unary(op, operand, scope, addr_space)
```

### 3.3 比较运算符分发 (含兜底链)

```python
def dispatch_compare(op: str, left: TSValue, right: TSValue,
                     scope: Scope, addr_space: AddressSpace) -> TSValue:
    """
    比较运算符分发：含兜底组合逻辑
    顺序：直接特殊成员 → 组合兜底 → compare 三路比较 → 对象同一性兜底
    """
    
    type_obj = left.ts_type()
    direct_member = COMPARE_OP_TO_SPECIAL.get(op)  # "greater", "less" 等
    
    # 1. 直接特殊成员
    member = type_obj.special_members.get(direct_member)
    if member:
        return call_special(member, left, right, scope, addr_space)
    
    # 2. 组合兜底
    fallback_result = try_fallback_compare(op, left, right, type_obj, scope, addr_space)
    if fallback_result is not None:
        return fallback_result
    
    # 3. compare 三路比较
    compare_member = type_obj.special_members.get("compare")
    if compare_member:
        cmp_result = call_special(compare_member, left, right, scope, addr_space)
        if isinstance(cmp_result, (TSInteger, TSNumber)):
            return interpret_compare_result(op, cmp_result)
        else:
            raise TSTypeError("compare must return integer or number")
    
    # 4. 对象同一性兜底
    return object_identity_fallback(op, left, right)
```

### 3.4 组合兜底实现

```python
def try_fallback_compare(op: str, left: TSValue, right: TSValue,
                         type_obj: TSType, scope: Scope, addr_space: AddressSpace):
    """尝试组合兜底：根据兜底规则调用其他特殊成员"""
    
    fallback_rules = {
        "greater": (["less", "equal"], lambda l, e: not (l or e)),      # !(less || equal)
        "less": (["greater", "equal"], lambda g, e: not (g or e)),      # !(greater || equal)
        "greater_equal": (["less"], lambda l: not l),                     # !less
        "less_equal": (["greater"], lambda g: not g),                     # !greater
        "equal": (["not_equal"], lambda ne: not ne),                      # !not_equal
        "not_equal": (["equal"], lambda e: not e),                        # !equal
    }
    
    if op not in fallback_rules:
        return None
    
    required_members, combiner = fallback_rules[op]
    
    # 检查所需特殊成员是否存在
    members = {}
    for m_name in required_members:
        m = type_obj.special_members.get(m_name)
        if not m:
            return None
        members[m_name] = m
    
    # 调用并组合结果
    results = {}
    for m_name, member in members.items():
        result = call_special(member, left, right, scope, addr_space)
        results[m_name] = ts_truthy(result)
    
    return make_boolean(combiner(**results))
```

---

## 4. 特殊成员调用

```python
def call_special(member_fn: TSValue, *args: TSValue, 
                 scope: Scope, addr_space: AddressSpace) -> TSValue:
    """
    调用特殊成员函数。
    member_fn: TSFunction 或 TSCode (带参数信息)
    args: 已求值的参数值列表
    """
    # 为每个参数分配临时地址
    arg_addrs = []
    for arg_val in args:
        addr = addr_space.allocate()
        addr_space.write(addr, arg_val)
        arg_addrs.append(addr)
    
    # 调用函数 (复用函数调用逻辑)
    return call_function(member_fn, arg_addrs, scope, addr_space)

def call_function(fn_val: TSValue, arg_addrs: List[int],
                  caller_scope: Scope, addr_space: AddressSpace) -> TSValue:
    """函数调用核心逻辑"""
    # ... 见 environment.md call_function 实现
    pass
```

---

## 5. 内置运算符实现

### 5.1 内置二元运算

```python
def builtin_binary_op(op: str, left: TSValue, right: TSValue,
                      scope: Scope, addr_space: AddressSpace) -> TSValue:
    """内置类型运算符实现 (当无特殊成员时)"""
    
    # Integer 运算
    if isinstance(left, TSInteger) and isinstance(right, TSInteger):
        return builtin_integer_binary(op, left, right)
    
    # Number 运算
    if isinstance(left, TSNumber) or isinstance(right, TSNumber):
        # 提升 Integer 为 Number
        l = left if isinstance(left, TSNumber) else promote_to_number(left)
        r = right if isinstance(right, TSNumber) else promote_to_number(right)
        return builtin_number_binary(op, l, r)
    
    # String/List 拼接
    if op == "+" and isinstance(left, TSString) and isinstance(right, TSString):
        return concat_strings(left, right)
    if op == "+" and isinstance(left, TSList) and isinstance(right, TSList):
        return concat_lists(left, right)
    if op == "*" and isinstance(left, TSString) and isinstance(right, TSInteger):
        return repeat_string(left, right.value)
    if op == "*" and isinstance(left, TSList) and isinstance(right, TSInteger):
        return repeat_list(left, right.value)
    
    # Boolean 算术返回 Integer
    if isinstance(left, TSBoolean) and isinstance(right, TSBoolean):
        return builtin_boolean_binary(op, left, right)
    
    raise TSTypeError(f"No builtin implementation for {op} on {left.ts_type()} and {right.ts_type()}")

def builtin_integer_binary(op: str, a: TSInteger, b: TSInteger) -> TSValue:
    if op == "+": return make_integer(a.value + b.value)
    if op == "-": return make_integer(a.value - b.value)
    if op == "*": return make_integer(a.value * b.value)
    if op == "/": 
        if b.value == 0: return TSInfinite.POS_INF if a.value >= 0 else TSInfinite.NEG_INF
        return make_number(a.value, 0, 1)  # 简化
    if op == "\\": 
        if b.value == 0: raise TSArithError("Division by zero in integer divide")
        return make_integer(a.value // b.value)
    if op == "%": 
        if b.value == 0: raise TSArithError("Modulo by zero")
        return make_integer(a.value % b.value)
    if op == "^": return make_integer(pow(a.value, b.value))
    if op in ("<", "<=", ">", ">=", "==", "!="):
        return make_boolean(compare_int(a.value, b.value, op))
    raise TSTypeError(f"Unknown integer op: {op}")
```

### 5.2 内置一元运算

```python
def builtin_unary_op(op: str, operand: TSValue) -> TSValue:
    if isinstance(operand, TSInteger):
        if op == "-": return make_integer(-operand.value)
        if op == "+": return operand
        if op == "!": return make_boolean(operand.value == 0)
    
    if isinstance(operand, TSNumber):
        if op == "-": return negate_number(operand)
        if op == "+": return operand
    
    if isinstance(operand, TSBoolean):
        if op == "!": return make_boolean(operand.value == 0)
    
    raise TSTypeError(f"No builtin unary {op} for {operand.ts_type()}")
```

---

## 6. 代码块执行与收集模式

```python
def eval_code_block(code: TSCode, scope: Scope, addr_space: AddressSpace,
                    collect_mode: bool = False) -> TSValue:
    """执行代码块，可选收集模式 ($$ 内部)"""
    
    call_scope = Scope(parent=code.scope)
    
    # 绑定参数 (code.params 已在调用时绑定)
    # 此处假设参数已绑定到 call_scope
    
    result = TSNone.INSTANCE
    for stmt_ast in code.statements:
        try:
            stmt_result = eval(stmt_ast, call_scope, addr_space)
            
            if collect_mode:
                # $$ 收集模式：$ 语义改为收集
                # 此处需在 eval 内部处理 ReturnSignal
                pass
            
            result = stmt_result
        except ReturnSignal as rs:
            if collect_mode:
                # 收集模式：记录值，继续执行
                collected.append(rs.value)
                continue
            else:
                return rs.value
        except (BreakSignal, ContinueSignal, ErrorSignal):
            raise  # 传播给外层处理
    
    return result
```

---

## 7. 模块执行

```python
def exec_module(ast_dict: dict, scope: Scope, addr_space: AddressSpace) -> TSLibrary:
    """执行模块语句列表，返回 Library 对象"""
    
    statements = ast_dict.get("Tanex Script", [])
    annotations = ast_dict.get("annotations", {})
    file_annotation = ast_dict.get("annotation")
    
    # 合并注解
    merge_annotations(annotations, lib_name=None)
    if file_annotation:
        set_file_annotation(file_annotation)
    
    for stmt_ast in statements:
        try:
            eval(stmt_ast, scope, addr_space)
        except ReturnSignal as rs:
            # 顶层 $ n
            if isinstance(rs.value, TSInteger):
                exit(rs.value.value)
            else:
                raise TSTypeError("Top-level return must be integer")
        except ErrorSignal:
            raise  # 传播给入口处理
    
    # 收集顶层绑定构建 Library
    members = collect_top_level_bindings(scope)
    return TSLibrary(members, annotations)
```

---

## 相关链接

- [运行时值模型](values.md) — 值类型定义
- [地址空间与作用域](environment.md) — 存储与查找
- [模块加载器](loader.md) — 模块执行入口
- [语言参考：表达式](../reference/expressions.md) — 求值语义
- [语言参考：控制流](../reference/runtime_internals.md#3-控制流信号机制) — 信号机制