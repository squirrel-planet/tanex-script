# 地址空间与作用域 API

> 运行时值存储（地址空间）与名字查找（作用域）的 Python 侧实现。

---

## 1. 地址空间 `AddressSpace`

```python
class AddressSpace:
    def __init__(self):
        self._cells: Dict[int, StorageCell] = {}
        self._next_addr: int = 0
    
    def allocate(self) -> int:
        """分配新地址，创建存储单元（初值 none），返回地址"""
        addr = self._next_addr
        self._next_addr += 1
        self._cells[addr] = StorageCell(TSNone.INSTANCE)
        return addr
    
    def read(self, addr: int) -> TSValue:
        """读取地址值，地址不存在抛 TSAddressError"""
        if addr not in self._cells:
            raise TSAddressError(f"Address {addr} not allocated")
        return self._cells[addr].value
    
    def write(self, addr: int, value: TSValue) -> None:
        """写入地址，常量单元抛 TSConstError"""
        if addr not in self._cells:
            raise TSAddressError(f"Address {addr} not allocated")
        if self._cells[addr].is_const:
            raise TSConstError(f"Address {addr} is constant")
        self._cells[addr].value = value
    
    def mark_const(self, addr: int) -> None:
        """标记地址为只读"""
        if addr in self._cells:
            self._cells[addr].is_const = True
    
    def exists(self, addr: int) -> bool:
        return addr in self._cells
    
    def get_cell(self, addr: int) -> 'StorageCell':
        """获取存储单元（内部用）"""
        return self._cells.get(addr)
```

### 存储单元

```python
class StorageCell:
    def __init__(self, value: TSValue):
        self.value = value
        self.is_const = False
```

---

## 2. 作用域 `Scope`

```python
class Scope:
    def __init__(self, parent: 'Scope' = None):
        self._bindings: Dict[str, int] = {}  # name -> address
        self._parent = parent
    
    def declare(self, name: str, addr: int) -> None:
        """在当前层声明/覆盖名字绑定"""
        self._bindings[name] = addr
    
    def resolve(self, name: str) -> Optional[int]:
        """查找名字，返回地址或 None（不报错）"""
        if name in self._bindings:
            return self._bindings[name]
        if self._parent:
            return self._parent.resolve(name)
        return None
    
    def resolve_or_error(self, name: str) -> int:
        """查找名字，未找到抛 TSNameError"""
        addr = self.resolve(name)
        if addr is None:
            raise TSNameError(f"Variable '{name}' not defined")
        return addr
    
    def local_has(self, name: str) -> bool:
        """仅查当前层，用于 *name 声明判断新建/复用"""
        return name in self._bindings
    
    def parent(self) -> Optional['Scope']:
        return self._parent
    
    def set_parent(self, parent: 'Scope') -> None:
        self._parent = parent
    
    def get_all_bindings(self) -> Dict[str, int]:
        """获取当前层所有绑定（不含父层）"""
        return self._bindings.copy()
```

---

## 3. 赋值目标解析

```python
def resolve_assignment_target(ast_node: dict, scope: Scope, addr_space: AddressSpace) -> int:
    """
    根据左侧 AST 节点解析出写入地址。
    节点类型：name、member、subscript、unary(*/**/***)
    """
    node_type = list(ast_node.keys())[0]
    
    if node_type == "name":
        # 标识符：查找/分配地址
        name = ast_node["name"]["value"]
        if scope.local_has(name):
            return scope.resolve_or_error(name)
        else:
            # 隐式声明
            addr = addr_space.allocate()
            scope.declare(name, addr)
            return addr
    
    elif node_type == "member":
        # 成员访问：obj.field
        obj_addr = eval_ast(ast_node["member"]["left"], scope, addr_space)
        obj_val = addr_space.read(obj_addr)
        if isinstance(obj_val, TSInstance):
            field_name = ast_node["member"]["right"]["name"]["value"]
            if field_name in obj_val.members:
                return obj_val.members[field_name]
            elif obj_val.type.addable:
                # 新建成员
                new_addr = addr_space.allocate()
                obj_val.members[field_name] = new_addr
                return new_addr
            else:
                raise TSTypeError(f"Type {obj_val.type} is not addable")
        elif isinstance(obj_val, TSType):
            # 类型对象成员
            field_name = ast_node["member"]["right"]["name"]["value"]
            if field_name in obj_val.members:
                return obj_val.members[field_name]
            elif obj_val.addable:
                new_addr = addr_space.allocate()
                obj_val.members[field_name] = new_addr
                return new_addr
            else:
                raise TSTypeError(f"Type {obj_val} is not addable")
        else:
            raise TSTypeError(f"Type {obj_val.ts_type()} does not support member access")
    
    elif node_type == "subscript":
        # 下标访问：obj[key] - 取地址场景
        obj_val = eval_ast(ast_node["subscript"]["left"], scope, addr_space)
        key_val = eval_ast(ast_node["subscript"]["right"], scope, addr_space)
        
        if isinstance(obj_val, TSInstance):
            type_obj = obj_val.type
            index_fn = type_obj.special_members.get("index")
            if index_fn:
                result = call_special(index_fn, obj_val, key_val)
                if isinstance(result, TSAddress):
                    return result.addr
                elif isinstance(result, TSInstance) and "value" in result.members:
                    return result.members["value"]
                else:
                    return addr_space.allocate()  # 回退
            elif type_obj.initialize:
                # 无 index 但有构造器
                result = call_special(type_obj.initialize, obj_val, key_val)
                return result
        raise TSTypeError(f"Type {obj_val.ts_type()} does not support subscript assignment")
    
    elif node_type == "unary":
        op = ast_node["unary"]["operator"]
        if op in ("*", "**", "***"):
            # 声明符：*name、**name、***name
            operand = ast_node["unary"]["operand"]
            if operand.get("type") == "name":
                name = operand["name"]["value"]
                addr = addr_space.allocate()
                if op == "***":
                    addr_space.mark_const(addr)
                scope.declare(name, addr)
                return addr
            elif op == "***" and operand.get("type") == "member":
                # *** Type.member
                type_name = operand["member"]["left"]["name"]["value"]
                member_name = operand["member"]["right"]["name"]["value"]
                type_obj = resolve_type(type_name, scope)
                if member_name in type_obj.members:
                    if addr_space.get_cell(type_obj.members[member_name]).is_const:
                        raise TSConstError("Constant member already exists")
                new_addr = addr_space.allocate()
                addr_space.mark_const(new_addr)
                type_obj.members[member_name] = new_addr
                return new_addr
    
    raise TSTypeError(f"Invalid assignment target: {ast_node}")
```

---

## 4. 上级访问 `~`

```python
def eval_parent_scope_access(operand_ast: dict, scope: Scope, addr_space: AddressSpace) -> TSValue:
    """~expr: 在父作用域中求值操作数"""
    if scope.parent() is None:
        raise TSControlError("No parent scope for ~ operator")
    
    # 临时切换到父作用域
    parent_scope = scope.parent()
    return eval_ast(operand_ast, parent_scope, addr_space)
```

---

## 5. 闭包捕获机制

```python
def make_closure(code_ast: dict, defining_scope: Scope) -> TSCode:
    """创建闭包：捕获定义时作用域"""
    return TSCode(
        statements=code_ast["code"]["statements"],
        scope=defining_scope,  # 捕获定义时作用域
        params=code_ast["code"].get("params", [])
    )

def call_function(fn_val: TSValue, arg_addrs: List[int], 
                  scope: Scope, addr_space: AddressSpace) -> TSValue:
    """函数调用：建立子作用域，绑定参数"""
    if isinstance(fn_val, TSFunction):
        closure_scope = fn_val.closure_scope
        code = fn_val.code
    elif isinstance(fn_val, TSCode):
        closure_scope = fn_val.scope
        code = fn_val
    elif isinstance(fn_val, TSType):
        # 类型构造
        return construct_type(fn_val, arg_addrs, scope, addr_space)
    else:
        raise TSTypeError(f"{fn_val.ts_type()} is not callable")
    
    # 建立子作用域（父作用域为闭包捕获的作用域）
    call_scope = Scope(parent=closure_scope)
    
    # 绑定参数
    param_infos = code.params
    for i, param_info in enumerate(param_infos):
        if i < len(arg_addrs):
            call_scope.declare(param_info.name, arg_addrs[i])
        elif param_info.default_ast is not None:
            # 求值默认值
            default_val = eval_ast(param_info.default_ast, scope, addr_space)
            default_addr = addr_space.allocate()
            addr_space.write(default_addr, default_val)
            call_scope.declare(param_info.name, default_addr)
        else:
            # 补 none
            none_addr = addr_space.allocate()
            call_scope.declare(param_info.name, none_addr)
    
    # 执行函数体
    return eval_code_block(code, call_scope, addr_space)
```

---

## 5. 常用操作封装

```python
# 便捷函数
def get_variable(scope: Scope, addr_space: AddressSpace, name: str) -> TSValue:
    addr = scope.resolve_or_error(name)
    return addr_space.read(addr)

def set_variable(scope: Scope, addr_space: AddressSpace, name: str, value: TSValue) -> None:
    addr = scope.resolve_or_error(name)
    addr_space.write(addr, value)

def declare_variable(scope: Scope, addr_space: AddressSpace, name: str, 
                     value: TSValue = None, const: bool = False) -> int:
    addr = addr_space.allocate()
    if value is not None:
        addr_space.write(addr, value)
    if const:
        addr_space.mark_const(addr)
    scope.declare(name, addr)
    return addr

def declare_reference(scope: Scope, addr_space: AddressSpace, name: str, target_name: str) -> int:
    """** name = target_name"""
    target_addr = scope.resolve_or_error(target_name)
    scope.declare(name, target_addr)  # 共享地址
    return target_addr

def declare_constant(scope: Scope, addr_space: AddressSpace, name: str, value: TSValue) -> int:
    """*** name = value"""
    addr = addr_space.allocate()
    addr_space.write(addr, value)
    addr_space.mark_const(addr)
    scope.declare(name, addr)
    return addr
```

---

## 相关链接

- [运行时值模型](values.md) — 值的存储与操作
- [核心执行器](interpreter.md) — 作用域在执行中的使用
- [模块加载器](loader.md) — 模块作用域隔离
- [语言参考：作用域](../reference/lexical.md#作用域与闭包) — 语言层面作用域规则
- [语言参考：声明语句](../reference/statements.md#4-声明语句) — 声明语法语义