# 模块加载器

> 运行时模块加载、路径解析、缓存机制的 Python 侧实现。

---

## 1. 模块加载入口

```python
def load_library_module(path_expr_ast: dict, scope: Scope, addr_space: AddressSpace) -> TSLibrary:
    """
    运行时加载模块 (动态 import 路径求值后调用)。
    对应 import/-> 表达式符号的运行时语义。
    """
    # 1. 求值路径表达式得字符串路径
    path_val = eval(path_expr_ast, scope, addr_space)
    if not isinstance(path_val, TSString):
        raise TSTypeError("Import path must be string")
    
    path_str = path_val.to_python()
    
    # 2. 解析路径 -> 绝对路径列表
    resolved_paths = resolve_import_path(path_str)
    
    # 3. 尝试加载每个候选路径
    for rp in resolved_paths:
        try:
            if rp.type == 'tscc':
                return load_tscc_module(rp.path, scope, addr_space)
            elif rp.type == 'tscl':
                return load_tscl_module(rp.path, rp.internal_path, scope, addr_space)
            elif rp.type == 'dir':
                return load_dir_module(rp.path, scope, addr_space)
        except TSImportError:
            continue  # 尝试下一个候选
    
    raise TSImportError(f"Cannot resolve import path: {path_str}")
```

---

## 2. 路径解析算法

```python
from dataclasses import dataclass
from typing import List
import os
from pathlib import Path

@dataclass
class ResolvedPath:
    path: str           # 绝对路径
    type: str           # 'tscc' | 'tscl' | 'dir'
    internal_path: str = None  # tscl 内部路径
    priority: int = 0   # 优先级 (越小越优先)

def resolve_import_path(path_str: str) -> List[ResolvedPath]:
    """
    路径解析算法：歧义消除、标准库优先、后缀补全。
    """
    candidates = []
    
    # 1. 标准库优先：裸名 "standard" 优先安装目录
    if path_str == "standard":
        std_path = get_install_dir() / "run" / "standard.tscl"
        if std_path.exists():
            candidates.append(ResolvedPath(str(std_path), 'tscl', priority=0))
    
    # 2. 绝对路径
    if is_absolute(path_str):
        candidates.extend(resolve_absolute(path_str))
    
    # 3. 相对路径：基于当前文件目录
    if path_str.startswith("./") or path_str.startswith("../"):
        base = get_current_file_dir() or os.getcwd()
        candidates.extend(resolve_relative(base, path_str))
    
    # 4. 库搜索路径
    for lib_path in get_lib_paths():
        candidates.extend(resolve_relative(lib_path, path_str))
    
    # 5. 歧义消除
    return disambiguate_candidates(candidates)

def resolve_absolute(path_str: str) -> List[ResolvedPath]:
    """解析绝对路径"""
    path = Path(path_str)
    if not path.exists():
        return []
    
    if path.is_file():
        if path.suffix == '.tscc':
            return [ResolvedPath(str(path), 'tscc')]
        elif path.suffix == '.tscl':
            return [ResolvedPath(str(path), 'tscl')]
        elif path.suffix == '.tsuc':
            # 源码文件需先编译
            return [ResolvedPath(str(path.with_suffix('.tscc')), 'tscc')]
    elif path.is_dir():
        return [ResolvedPath(str(path), 'dir')]
    return []

def resolve_relative(base: str, rel_path: str) -> List[ResolvedPath]:
    """解析相对路径，尝试多种后缀"""
    base_path = Path(base)
    target = (base_path / rel_path).resolve()
    candidates = []
    
    # 尝试多种形式
    suffixes = [
        ('', 'dir'),           # 目录
        ('.tscl', 'tscl'),     # 编译库
        ('.tscc', 'tscc'),     # 编译产物
        ('.tsuc', 'tscc'),     # 源码 (编译后为 tscc)
    ]
    
    for suffix, rtype in suffixes:
        p = target.with_name(target.name + suffix) if suffix else target
        if p.exists():
            candidates.append(ResolvedPath(str(p), rtype))
    
    return candidates

def disambiguate_candidates(candidates: List[ResolvedPath]) -> List[ResolvedPath]:
    """歧义消除规则"""
    if not candidates:
        return []
    
    # 按优先级排序
    candidates.sort(key=lambda c: c.priority)
    
    # 1. 同名 .tscc 与 .tsuc 不算歧义 (.tscc 优先)
    # 2. 文件夹与 .tscl 同名：裸名优先 .tscl
    # 3. 同一类型同名多个：报错
    
    # 按类型分组
    by_type = {}
    for c in candidates:
        by_type.setdefault(c.type, []).append(c)
    
    result = []
    
    # tscl 优先 (标准库、编译库)
    if 'tscl' in by_type:
        if len(by_type['tscl']) > 1:
            raise TSImportError(f"Ambiguous import: multiple .tscl matches")
        result.append(by_type['tscl'][0])
    
    # tscc 次之
    if 'tscc' in by_type:
        if len(by_type['tscc']) > 1:
            raise TSImportError(f"Ambiguous import: multiple .tscc matches")
        result.append(by_type['tscc'][0])
    
    # dir 最后
    if 'dir' in by_type:
        if len(by_type['dir']) > 1:
            raise TSImportError(f"Ambiguous import: multiple directories match")
        result.append(by_type['dir'][0])
    
    return result
```

---

## 3. 模块加载实现

### 3.1 加载 `.tscc` 文件

```python
def load_tscc_module(path: str, scope: Scope, addr_space: AddressSpace) -> TSLibrary:
    """加载 .tscc 编译产物"""
    import json
    with open(path, 'r', encoding='utf-8') as f:
        ast_dict = json.load(f)
    
    # 执行模块语句
    return exec_module(ast_dict, scope, addr_space)
```

### 3.2 加载 `.tscl` 编译库

```python
import struct

def load_tscl_module(path: str, internal_path: str, scope: Scope, addr_space: AddressSpace) -> TSLibrary:
    """加载 .tscl 编译库，可指定内部路径"""
    with open(path, 'rb') as f:
        # 读取头部
        magic = f.read(4)
        if magic != b'TSCL':
            raise TSImportError(f"Invalid .tscl file: {path}")
        
        version = struct.unpack('<I', f.read(4))[0]
        file_count = struct.unpack('<I', f.read(4))[0]
        
        # 读取索引表
        index = {}
        for _ in range(file_count):
            name_len = struct.unpack('<I', f.read(4))[0]
            name = f.read(name_len).decode('utf-8')
            offset = struct.unpack('<Q', f.read(8))[0]
            size = struct.unpack('<Q', f.read(8))[0]
            index[name] = (offset, size)
        
        # 确定要加载的内部路径
        if internal_path is None:
            # 查找 main 入口
            main_candidates = [n for n in index if n.endswith('/main.tscc') or n == 'main.tscc']
            if main_candidates:
                # 取最深层
                internal_path = max(main_candidates, key=lambda x: x.count('/'))
            else:
                # 无 main，返回空库 (需用户手动引入)
                return TSLibrary({}, {})
        
        if internal_path not in index:
            raise TSImportError(f"Internal path not found in .tscl: {internal_path}")
        
        # 读取指定文件内容
        offset, size = index[internal_path]
        f.seek(offset)
        content = f.read(size)
        ast_dict = json.loads(content.decode('utf-8'))
        
        return exec_module(ast_dict, scope, addr_space)
```

### 3.3 加载库目录

```python
def load_dir_module(path: str, scope: Scope, addr_space: AddressSpace) -> TSLibrary:
    """加载库目录 (查找 main.tscc)"""
    dir_path = Path(path)
    main_path = find_deepest_main(dir_path)
    
    if main_path:
        with open(main_path, 'r', encoding='utf-8') as f:
            ast_dict = json.load(f)
        return exec_module(ast_dict, scope, addr_space)
    else:
        # 无 main 文件，返回空库
        return TSLibrary({}, {})

def find_deepest_main(dir_path: Path) -> Path:
    """查找最深层的 main.tscc"""
    mains = list(dir_path.rglob('main.tscc'))
    if not mains:
        return None
    # 按深度排序，取最深
    return max(mains, key=lambda p: len(p.relative_to(dir_path).parts))
```

---

## 4. 模块缓存

```python
class ModuleCache:
    def __init__(self):
        self._cache: Dict[str, TSLibrary] = {}  # 绝对路径 -> Library
        self._loading: Set[str] = set()         # 正在加载的路径 (检测循环依赖)
    
    def get(self, path: str) -> TSLibrary:
        return self._cache.get(path)
    
    def put(self, path: str, library: TSLibrary) -> None:
        self._cache[path] = library
    
    def invalidate(self, path: str) -> None:
        """使缓存失效 (热重载)"""
        self._cache.pop(path, None)
    
    def clear(self) -> None:
        self._cache.clear()
        self._loading.clear()
    
    def acquire_load_lock(self, path: str) -> bool:
        """尝试获取加载锁 (防止循环依赖)"""
        if path in self._loading:
            raise TSImportError(f"Circular import detected: {path}")
        self._loading.add(path)
        return True
    
    def release_load_lock(self, path: str) -> None:
        self._loading.discard(path)

# 使用示例
cache = ModuleCache()

def load_with_cache(path_expr_ast, scope, addr_space):
    path_val = eval(path_expr_ast, scope, addr_space)
    abs_path = resolve_to_absolute(path_val)
    
    # 检查缓存
    cached = cache.get(abs_path)
    if cached:
        return cached
    
    # 获取加载锁
    cache.acquire_load_lock(abs_path)
    try:
        lib = load_library_module(path_expr_ast, scope, addr_space)
        cache.put(abs_path, lib)
        return lib
    finally:
        cache.release_load_lock(abs_path)
```

---

## 5. 注解隔离机制

```python
def exec_module(ast_dict: dict, scope: Scope, addr_space: AddressSpace) -> TSLibrary:
    """执行模块，返回 Library (含独立注解空间)"""
    statements = ast_dict.get("Tanex Script", [])
    annotations = ast_dict.get("annotations", {})
    file_annotation = ast_dict.get("annotation")
    
    # 执行语句
    for stmt_ast in statements:
        eval(stmt_ast, scope, addr_space)
    
    # 收集顶层绑定
    members = collect_top_level_bindings(scope)
    
    # 返回 Library (注解将由调用者合并到独立空间)
    return TSLibrary(members, annotations)

# 调用者负责合并注解
def import_with_annotations(path_expr_ast, scope, addr_space, lib_name):
    lib = load_library_module(path_expr_ast, scope, addr_space)
    
    # 合并库注解到独立空间
    interpreter.annotation_table.merge(lib.annotations, lib_name=lib_name)
    
    return lib
```

---

## 相关链接

- [核心执行器](interpreter.md) — exec_module 实现
- [注解系统](annotations.md) — 注解表合并策略
- [语言参考：模块系统](../reference/modules.md) — import/-> 用户层面语义
- [错误与诊断](errors.md) — TSImportError 等
- [专题指南：元编程](../howto/metaprogramming.md) — 动态 import 实战