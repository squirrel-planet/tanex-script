# 运行时解释器

import os
import sys
import json
from errors import warning, output_message
from runtime.environment import address_space
from runtime.environment import scope
from runtime.environment import storage_cell
from runtime.values import type_object
from runtime.values import instance
from runtime.values import code_value
from runtime.values import builtin_function
from runtime.values import runtime_error
from runtime.values import throw_signal
from runtime.values import return_signal
from runtime.values import break_signal

_arith_slot = {
    '+': 'addition', '-': 'subtract', '*': 'multiply',
    '/': 'divide', '\\': 'exactly_divisible', '%': 'modulo',
    '^': 'power',
}
_cmp_slot = {
    '>': 'greater', '<': 'less', '>=': 'greater_equal',
    '<=': 'less_equal', '==': 'equal', '!=': 'not_equal',
}
_fallback_map = {
    '>': [['less', 'equal'], 'or'],
    '<': [['greater', 'equal'], 'or'],
    '>=': [['less'], 'not'],
    '<=': [['greater'], 'not'],
    '==': [['not_equal'], 'not'],
    '!=': [['equal'], 'not'],
}
_copy_skip = frozenset({'addable', 'external_read_only', 'inherit'})
_dump_skip = frozenset({
    'inherit', 'init', 'boolean', 'string', 'index',
    'addition', 'subtract', 'multiply', 'divide',
    'exactly_divisible', 'modulo', 'power',
    'greater', 'less', 'greater_equal', 'less_equal',
    'equal', 'not_equal', 'compare', 'positive', 'negative',
    'addable', 'external_read_only', 'public',
})

class interpreter(object):
    def __init__(self):
        self.address_space = address_space()
        self.global_scope = scope()
        self.type_type: type_object | None = None
        self._none_fallback: instance | None = None
        self._core_placeholders = {}
        self.annotations = {}
        self._public_names = set()
        self._bootstrap_names = set()
        self._outside_bootstrap = False
        self._loaded_dependencies = set()
        self._loaded_libs: dict[str, instance] = {}
        self._dep_declarations: dict[str, set[str]] = {}
        # 库注解空间：{导入名: {目标: 注解内容}}，import 时单独存放，不污染全局
        self.lib_annotations: dict[str, dict[str, str]] = {}
        # 按库路径暂存注解表，供 eval_import 绑定到导入名
        self._lib_annotation_tables: dict[str, dict[str, str]] = {}

    # 启动阶段：建立核心类型骨架
    def init_core(self):
        self.type_type = type_object('type_type')
        self.type_type.inherit = self.type_type
        self.type_type.members['addable'] = self.address_space.allocate(1)
        self.type_type.members['init'] = self.address_space.allocate(
            builtin_function(self._builtin_type_init, 'type_type.init'))
        cell = self.address_space.allocate(self.type_type)
        cell.is_const = True
        self.global_scope.declare('type_type', cell)
        for name in ('integer', 'string', 'number', 'boolean', 'none_type',
            'infinite_type', 'nan_type', 'list', 'code', 'address',
            'error', 'warning', 'library'):
            typ = instance(self.type_type)
            typ.inherit = self.type_type
            cell = self.address_space.allocate(typ)
            cell.is_const = True
            self.global_scope.declare(name, cell)
            self._core_placeholders[name] = typ
        self._none_fallback = instance(self._core_placeholders['none_type'])
        import_fn = builtin_function(self._builtin_import, 'import')
        cell = self.address_space.allocate(import_fn)
        cell.is_const = True
        self.global_scope.declare('import', cell)

    def _builtin_type_init(self, interp, receiver, args):
        inherit = args[0] if args else self.type_type
        self.set_member(receiver, 'inherit', inherit)
        return receiver

    # 解析 JSON 内容，失败时给出中文报错
    def _parse_json_or_raise(self, content, path):
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise runtime_error(
                f'无法解析文件: {path}，无法运行'
                f'（JSON 解析错误: 第 {e.lineno} 行 第 {e.colno} 列）')

    # 读取并解析 JSON 文件，失败时给出中文报错
    def _load_json_file(self, path):
        with open(path, 'r', encoding = 'utf-8') as f:
            content = f.read()
        return self._parse_json_or_raise(content, path)

    # 引导库加载
    def load_bootstrap(self):
        here = os.path.dirname(os.path.abspath(__file__))
        candidates = [
            os.path.join(here, 'bootstrap.tscc'),
            os.path.join(here, '..', 'run', 'bootstrap.tscc'),
        ]
        path = None
        for cand in candidates:
            if os.path.exists(cand):
                path = cand
                break
        if path is None:
            output_message(['未找到 bootstrap.tscc，跳过引导阶段'])
            return
        data = self._load_json_file(path)
        self.annotations.update(data.get('annotations', {}))
        self.run_statements(data['Tanex Script'])
        self._bootstrap_names = set(self.global_scope.names.keys())
        public_cell = self.global_scope.find('public')
        if public_cell is not None and public_cell.value is not None:
            entries = self._list_to_py(public_cell.value)
            self._public_names = set(
                ''.join(chr(c) for c in self._list_to_py(item))
                for item in entries
            )
            self._public_names.add('public')
        self._public_names.add('import')
        self._public_names.add('library')

    # 运行用户文件
    def run_file(self, path):
        if path.endswith('.tscl'):
            self._outside_bootstrap = False
            for _, content in self._iter_tscl_blocks(path):
                self._load_dependency_data(self._parse_json_or_raise(content, path))
            self._outside_bootstrap = True
            return None, False
        data = self._load_json_file(path)
        self._outside_bootstrap = False
        for dep in data.get('dependencies', []):
            self._load_dependency(dep)
        self._outside_bootstrap = True
        self.annotations.update(data.get('annotations', {}))
        return self.run_statements(data['Tanex Script'])

    # 加载单个依赖（库文件），以受信身份执行
    def _load_dependency(self, dep):
        dep_key = os.path.abspath(dep)
        if dep_key in self._loaded_dependencies:
            return
        self._loaded_dependencies.add(dep_key)
        before = set(self.global_scope.names.keys())
        if dep.endswith('.tscl'):
            for _, content in self._iter_tscl_blocks(dep):
                self._load_dependency_data(self._parse_json_or_raise(content, dep))
        elif dep.endswith('.tscc'):
            self._load_dependency_data(self._load_json_file(dep))
        else:
            raise runtime_error('不支持的依赖类型: ' + dep)
        after = set(self.global_scope.names.keys())
        self._dep_declarations[dep_key] = after - before

    # 执行一个库文件块，先处理其自身依赖
    def _load_dependency_data(self, data):
        for sub in data.get('dependencies', []):
            self._load_dependency(sub)
        self.annotations.update(data.get('annotations', {}))
        self.run_statements(data['Tanex Script'])

    # 解析 .tscl 库文件，逐块产出（路径, JSON 内容）
    def _iter_tscl_blocks(self, tscl_path):
        data = self._load_json_file(tscl_path)
        for name, content in data.items():
            yield name, content

    # 以库命名空间方式加载模块（隔离的 library 实例，成员为模块顶层声明）
    def _load_library_module(self, path):
        abs_path = os.path.abspath(path)
        if abs_path in self._loaded_libs:
            return self._loaded_libs[abs_path]
        lib_type = self._resolve_global('library')
        if lib_type is None:
            raise runtime_error('library 类型未就绪')
        if abs_path in self._loaded_dependencies:
            raise runtime_error('库已加载: ' + path)
        if abs_path.endswith('.tscl'):
            blocks = [self._parse_json_or_raise(content, abs_path)
                for _, content in self._iter_tscl_blocks(abs_path)]
        else:
            blocks = [self._load_json_file(abs_path)]
        saved_outside = self._outside_bootstrap
        self._outside_bootstrap = False
        for data in blocks:
            for dep in data.get('dependencies', []):
                self._load_dependency(dep)
        self._outside_bootstrap = saved_outside
        module_scope = scope(parent = self.global_scope)
        module_scope.is_module = True
        self._outside_bootstrap = True
        lib_ann_table: dict[str, str] = {}
        for data in blocks:
            lib_ann_table.update(data.get('annotations', {}))
            if data.get('annotation'):
                lib_ann_table[''] = data['annotation']
            for stmt in data['Tanex Script']:
                self.eval_node(stmt, module_scope)
        self._outside_bootstrap = saved_outside
        self._lib_annotation_tables[abs_path] = lib_ann_table
        lib = instance(lib_type)
        for name, cell in module_scope.names.items():
            lib.members[name] = cell
        self._loaded_dependencies.add(abs_path)
        self._loaded_libs[abs_path] = lib
        return lib

    def eval_import(self, node, env):
        path = node['import']['path']
        abs_path = os.path.abspath(path)
        module_name = node['import'].get('name',
            os.path.splitext(os.path.basename(path))[0])
        if abs_path in self._loaded_libs:
            lib = self._loaded_libs[abs_path]
        elif abs_path in self._loaded_dependencies:
            lib = self._library_from_declarations(abs_path)
        else:
            lib = self._load_library_module(path)
        cell = env.find(module_name)
        if cell is not None and cell.value is not None:
            warning([f'标识符 "{module_name}" 已存在，将被新引入的内容覆盖'])
        if cell is None:
            cell = self._resolve_or_declare(module_name, env)
            cell.is_const = True
        self.address_space.write(cell, lib)
        # 导入后把库的注解整体放入独立空间（按导入名），不污染全局注解表
        self.lib_annotations[module_name] = self._lib_annotation_tables.get(abs_path, {})
        return lib

    def _library_from_declarations(self, abs_path):
        lib_type = self._resolve_global('library')
        if lib_type is None:
            raise runtime_error('library 类型未就绪')
        lib = instance(lib_type)
        names = self._dep_declarations.get(abs_path, set())
        for name in names:
            cell = self.global_scope.find(name)
            if cell is not None:
                lib.members[name] = cell
        return lib

    def _builtin_import(self, interp, receiver, args):
        path_obj = receiver
        if not isinstance(path_obj, instance):
            raise runtime_error('import 参数必须是字符串')
        codes = self._list_to_py(path_obj)
        path = ''.join(chr(c) for c in codes)
        if not os.path.isabs(path):
            here = os.path.dirname(os.path.abspath(__file__))
            candidates = [
                os.path.join(here, path),
                os.path.join(here, '..', path),
            ]
            resolved = None
            for cand in candidates:
                if os.path.exists(cand):
                    resolved = cand
                    break
            if resolved is None:
                if not path.endswith('.tscc'):
                    path_tscc = path + '.tscc'
                    for cand in candidates:
                        cand_tscc = os.path.join(os.path.dirname(cand), path_tscc)
                        if os.path.exists(cand_tscc):
                            resolved = cand_tscc
                            break
                if resolved is None:
                    raise runtime_error('找不到库文件: ' + path)
            path = resolved
        elif not os.path.exists(path):
            raise runtime_error('找不到库文件: ' + path)
        return self._load_library_module(path)

    def run_statements(self, statements):
        result = None
        for stmt in statements:
            try:
                result = self.eval_node(stmt, self.global_scope)
            except return_signal as rs:
                return rs.value, True
        return result, False

    # 基础工具

    def _resolve(self, name, env):
        cell = env.find(name)
        if cell is None:
            raise runtime_error('变量未定义: ' + name)
        if self._outside_bootstrap \
                and env.parent is None \
                and name in self._bootstrap_names \
                and name not in self._public_names:
            raise runtime_error('未公开符号: ' + name)
        return cell

    def _resolve_or_declare(self, name, env):
        # public 是文件级特殊变量，每个文件声明自己的 public，
        # 不沿作用域链复用外层（如 bootstrap）的 public 常量单元
        if name == 'public':
            cell = self.address_space.allocate()
            env.declare(name, cell)
            return cell
        s = env
        while s is not None:
            if name in s.names:
                return s.names[name]
            if getattr(s, 'is_module', False):
                break
            if getattr(s, 'is_function', False):
                break
            s = s.parent
        cell = self.address_space.allocate()
        env.declare(name, cell)
        return cell

    def _resolve_assign(self, name, env):
        s = env
        while s is not None:
            if name in s.names:
                return s.names[name]
            s = s.parent
        cell = self.address_space.allocate()
        env.declare(name, cell)
        return cell

    def _resolve_global(self, name):
        cell = self.global_scope.find(name)
        if cell is None:
            return None
        return cell.value

    def _is_current(self, name, typ):
        cell = self.global_scope.find(name)
        return cell is not None and cell.value is typ

    def _is_type(self, value):
        return isinstance(value, instance) and value.type is self.type_type

    def _get_none(self):
        cell = self.global_scope.find('none')
        if cell is not None and cell.initialized and cell.value is not None:
            return cell.value
        none_type = self._resolve_global('none_type')
        fallback = self._none_fallback
        if none_type is not None and fallback is not None \
            and fallback.type is not none_type:
            self._none_fallback = instance(none_type)
        return self._none_fallback

    def _boolean(self, py_bool):
        bool_type = self._resolve_global('boolean')
        obj = instance(bool_type) if bool_type is not None \
            else instance(self._core_placeholders['boolean'])
        self._set_own_member(obj, 'value', 1 if py_bool else 0)
        return obj

    # 成员机制

    def _get_inherit(self, cur):
        if isinstance(cur, (instance, type_object)):
            cell = cur.members.get('inherit')
            if cell is not None:
                return cell.value
            return getattr(cur, 'inherit', None)
        return None

    def _find_in_chain(self, typ, name):
        cur = typ
        seen = set()
        while cur is not None and id(cur) not in seen:
            seen.add(id(cur))
            if isinstance(cur, (instance, type_object)):
                c = cur.members.get(name)
                if c is not None:
                    return c
            cur = self._get_inherit(cur)
        return None

    def _find_member_cell(self, obj, name):
        if isinstance(obj, (instance, type_object)):
            own = obj.members.get(name)
            if own is not None:
                return own
        if isinstance(obj, instance):
            if self._is_current('function_type', obj.type):
                return self._ensure_function_member(obj, name)
            return self._find_in_chain(obj.type, name)
        if isinstance(obj, type_object):
            return self._find_in_chain(obj, name)
        if isinstance(obj, code_value):
            return self._find_code_member_cell(obj, name)
        return None

    def _ensure_function_member(self, fn, name):
        code_cell = fn.members.get('code')
        if code_cell is None or not isinstance(code_cell.value, code_value):
            return None
        cv = code_cell.value
        if name == 'params':
            value = self._build_list(
                [self._build_string_from_py(p) for p in cv.params])
        elif name == 'defaults':
            value = self._build_list(
                [self._boolean(d is not None) for d in cv.defaults])
        elif name == 'statements':
            value = len(cv.statements)
        else:
            return None
        cell = self.address_space.allocate(value)
        fn.members[name] = cell
        return cell

    def _find_code_member_cell(self, cv, name):
        meta = self._ensure_code_meta(cv)
        if meta is None:
            return None
        index = self._find_method(meta.type, 'index')
        if index is None:
            return None
        value = self._call(index, [
            self.address_space.allocate(meta),
            self.address_space.allocate(self._build_string_from_py(name)),
        ])
        none_type = self._resolve_global('none_type')
        if isinstance(value, instance) and value.type is none_type:
            return None
        return self.address_space.allocate(value)

    def _find_method(self, obj, name):
        cell = self._find_member_cell(obj, name)
        if cell is None:
            return None
        return cell.value

    def _check_addable(self, obj):
        if isinstance(obj, (instance, type_object)):
            own = obj.members.get('addable')
            if own is not None and self.truthy(own.value):
                return
            if isinstance(obj, instance):
                cell = self._find_in_chain(obj.type, 'addable')
                if cell is not None and self.truthy(cell.value):
                    return
        raise runtime_error('类型未声明 addable，无法新增成员')

    def _set_own_member(self, obj, name, value):
        cell = obj.members.get(name)
        if cell is None:
            cell = self.address_space.allocate()
            obj.members[name] = cell
        self.address_space.write(cell, value)
        return cell

    def set_member(self, obj, name, value):
        if not isinstance(obj, (instance, type_object)):
            raise runtime_error('无法设置成员: ' + name)
        cell = obj.members.get(name)
        if cell is None:
            self._check_addable(obj)
            cell = self.address_space.allocate()
            obj.members[name] = cell
        if name == 'inherit' and isinstance(value, (instance, type_object)):
            for mname, mcell in list(value.members.items()):
                if mname in _copy_skip:
                    continue
                new_cell = self.address_space.allocate(mcell.value)
                obj.members[mname] = new_cell
        self.address_space.write(cell, value)
        return cell

    # 常量树标记：常量标识符首次绑定时，把其指向对象的所有成员 cell（及递归子对象成员）
    # 标注为常量并视为已初始化，使常量对象的内容（成员/下标写入）不可再被修改。
    # type_type 类型的实例（类型对象）豁免：保证 bootstrap 中 `*** string = type_type{}` 后
    # 继续添加成员（如 string.index = ...）不受影响；Python 层 type_object 同样直接返回。
    def _mark_tree_const(self, value, _seen = None):
        if isinstance(value, type_object):
            return
        if not isinstance(value, instance):
            return
        if self._is_type(value):
            return
        if _seen is None:
            _seen = set()
        oid = id(value)
        if oid in _seen:
            return
        _seen.add(oid)
        for name, cell in value.members.items():
            if cell is None:
                continue
            cell.is_const = True
            cell.initialized = True
            self._mark_tree_const(cell.value, _seen)

    # 判断 env 是否处于函数执行作用域内（用于常量树标记豁免函数内局部常量）
    def _in_function_scope(self, env):
        s = env
        while s is not None:
            if getattr(s, 'is_function', False):
                return True
            s = s.parent
        return False

    # 深拷贝：`=` 右操作数为标识符时调用，使赋值得到独立副本而非共享引用。
    # type_object 与基本值（非 instance）直接返回原值；instance 则新建同 type 实例，
    # 遍历 members 为每个成员分配新 cell 并递归拷贝 cell.value（新 cell 的 is_const 保持默认 False）。
    # inherit 实例属性保持原引用；_seen 字典按 id 防环。
    def _deep_copy(self, value, _seen = None):
        if isinstance(value, type_object):
            return value
        if not isinstance(value, instance):
            return value
        if _seen is None:
            _seen = {}
        oid = id(value)
        if oid in _seen:
            return _seen[oid]
        new_obj = instance(value.type)
        new_obj.inherit = value.inherit
        _seen[oid] = new_obj
        for name, cell in value.members.items():
            if cell is None:
                continue
            if name == 'inherit':
                new_cell = self.address_space.allocate(cell.value)
            else:
                new_cell = self.address_space.allocate(self._deep_copy(cell.value, _seen))
            new_obj.members[name] = new_cell
        return new_obj

    def _get_member(self, obj, name):
        cell = self._find_member_cell(obj, name)
        if cell is None:
            raise runtime_error('成员不存在: ' + name)
        return cell.value

    # 调用与构造

    def _call(self, callable_obj, cells):
        if isinstance(callable_obj, instance) and self._is_current('function_type', callable_obj.type):
            code_cell = callable_obj.members.get('code')
            if code_cell is None or not isinstance(code_cell.value, code_value):
                raise runtime_error('function 值缺少 code')
            return self.execute_function(code_cell.value, cells)
        if isinstance(callable_obj, code_value):
            result = self.execute_function(callable_obj, cells)
            return result
        if isinstance(callable_obj, builtin_function):
            receiver = cells[0].value if cells else None
            args = [c.value for c in cells[1:]]
            return callable_obj.fn(self, receiver, args)
        if self._is_type(callable_obj) or isinstance(callable_obj, type_object):
            return self.construct(callable_obj, [c.value for c in cells])
        raise runtime_error('不可调用的值')

    def _call_member(self, obj, name, arg_values):
        method = self._find_method(obj, name)
        if method is None:
            raise runtime_error('成员不存在: ' + name)
        receiver = self.address_space.allocate(obj)
        args = [self.address_space.allocate(v) for v in arg_values]
        return self._call(method, [receiver] + args)

    def construct(self, typ, arg_values):
        if self._is_current('integer', typ):
            return self._integer_construct(arg_values)
        if self._is_current('none_type', typ):
            return self._get_none()
        if not self._is_type(typ) and isinstance(typ, instance):
            typ = typ.type
        obj = instance(typ)
        init = self._find_method(typ, 'init')
        if isinstance(init, builtin_function) and typ is not self.type_type:
            type_type = self.type_type
            if type_type is not None:
                cell = type_type.members.get('init')
                if cell is not None and init is cell.value:
                    init = None
        if init is not None:
            receiver_cell = self.address_space.allocate(obj)
            args = [self.address_space.allocate(v) for v in arg_values]
            self._call(init, [receiver_cell] + args)
        elif self._is_current('function_type', typ):
            raise runtime_error('类型没有定义 init 构造器，无法构造')
        elif arg_values:
            raise runtime_error('类型没有定义 init 构造器，不能传参构造')
        return obj

    def _integer_construct(self, args):
        if not args:
            return 0
        v = args[0]
        if isinstance(v, int):
            return v
        if isinstance(v, instance):
            value_cell = v.members.get('value')
            if value_cell is not None:
                return value_cell.value
            front_cell = v.members.get('front')
            if front_cell is not None:
                return front_cell.value
        raise runtime_error('integer 构造失败')

    def execute_function(self, cv, cells):
        fscope = scope(cv.env)
        fscope.is_function = True
        for i, name in enumerate(cv.params):
            if i < len(cells):
                fscope.declare(name, cells[i])
            else:
                default = cv.defaults[i] if i < len(cv.defaults) else None
                if default is not None:
                    v = self.eval_node(default, fscope)
                    cell = self.address_space.allocate(v)
                    fscope.declare(name, cell)
                else:
                    raise runtime_error('缺少参数: ' + name)
        if len(cells) > len(cv.params):
            raise runtime_error(
                '参数过多: 期望 ' + str(len(cv.params))
                + ' 个参数，实际传入 ' + str(len(cells)) + ' 个')
        result = None
        for stmt in cv.statements:
            try:
                result = self.eval_node(stmt, fscope)
            except return_signal as rs:
                return rs.value
        return self._get_none()

    def execute_code_value(self, cv, take_last = False):
        fscope = scope(cv.env)
        for i, name in enumerate(cv.params):
            cell = self.address_space.allocate(self._get_none())
            fscope.declare(name, cell)
        result = None
        for stmt in cv.statements:
            try:
                result = self.eval_node(stmt, fscope)
            except return_signal as rs:
                return rs.value
        if take_last:
            return result
        return self._get_none()

    def _eval_branch(self, ast, env):
        if next(iter(ast)) == 'code':
            cv = code_value(ast['code']['statements'], env)
            return self.execute_code_value(cv)
        return self.eval_node(ast, env)

    # 真值

    def truthy(self, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        if isinstance(value, instance):
            method = self._find_method(value, 'boolean')
            if method is not None:
                result = self._call(method, [self.address_space.allocate(value)])
                return self.truthy(result)
            return True
        return True

    # 字面量构建

    def _build_string_from_py(self, text):
        codes = [ord(c) for c in text]
        str_type = self._resolve_global('string')
        if str_type is None:
            raise runtime_error('字符串类型未就绪')
        obj = self.construct(str_type, [])
        self.set_member(obj, 'data', self._build_list(codes))
        return obj

    # code 值元信息：把函数/代码块字面量的 AST 信息解析为 TSuc dictionary
    def _ensure_code_meta(self, cv) -> 'instance | None':
        if cv.meta is None:
            cv.meta = self._build_code_meta(
                cv.params, cv.defaults, len(cv.statements))
        return cv.meta

    def _build_code_meta(self, params, defaults, statement_count) -> 'instance | None':
        dict_type = self._resolve_global('dictionary')
        if dict_type is None:
            return None
        meta = self.construct(dict_type, [])
        if not isinstance(meta, instance):
            return None
        name_list = self._build_list(
            [self._build_string_from_py(p) for p in params])
        self._dictionary_set_key(meta, 'params', name_list)
        has_defaults = self._build_list(
            [self._boolean(d is not None) for d in defaults])
        self._dictionary_set_key(meta, 'defaults', has_defaults)
        self._dictionary_set_key(meta, 'statements', statement_count)
        return meta

    def _dictionary_set_key(self, d, key, value):
        index_set = self._find_method(d.type, 'index_set')
        if index_set is None:
            raise runtime_error('dictionary 未定义 index_set')
        self._call(index_set, [
            self.address_space.allocate(d),
            self.address_space.allocate(self._build_string_from_py(key)),
            self.address_space.allocate(value),
        ])

    def _build_list(self, py_values):
        list_type = self._resolve_global('list')
        if list_type is None:
            raise runtime_error('链表类型未就绪')
        lst = self.construct(list_type, [])
        for v in py_values:
            self._call_member(lst, 'append', [v])
        return lst

    def _make_number_literal(self, raw):
        s = raw[1:-1]
        neg = s.startswith('-')
        if neg:
            s = s[1:]
        if '.' in s:
            int_part, frac_part = s.split('.', 1)
        else:
            int_part, frac_part = s, ''
        front = int(int_part) if int_part else 0
        back = int(frac_part) if frac_part else 0
        back_digits = len(frac_part)
        if neg:
            front = -front
        number_type = self._resolve_global('number')
        obj = instance(number_type) if number_type is not None \
            else instance(self._core_placeholders['number'])
        self._set_own_member(obj, 'front', front)
        self._set_own_member(obj, 'back', back)
        self._set_own_member(obj, 'back_digits', back_digits)
        return obj

    def _make_infinite_literal(self):
        inf_type = self._resolve_global('infinite_type')
        obj = instance(inf_type) if inf_type is not None \
            else instance(self._core_placeholders['infinite_type'])
        self._set_own_member(obj, 'sign', 1)
        self._set_own_member(obj, 'infinity', True)
        return obj

    def _make_nan_literal(self):
        nan_type = self._resolve_global('nan_type')
        obj = instance(nan_type) if nan_type is not None \
            else instance(self._core_placeholders['nan_type'])
        self._set_own_member(obj, 'nan_marker', True)
        return obj

    # 求值分发

    def eval_node(self, node, env):
        kind = next(iter(node))
        if kind == 'integer':
            return int(node['integer']['value'])
        if kind == 'number':
            return self._make_number_literal(node['number']['value'])
        if kind == 'string':
            text = eval(node['string']['value'])
            return self._build_string_from_py(text)
        if kind == 'nan_type':
            return self._make_nan_literal()
        if kind == 'infinite_type':
            return self._make_infinite_literal()
        if kind == 'name':
            return self._resolve(node['name']['value'], env).value
        if kind == 'code':
            return code_value(node['code']['statements'], env)
        if kind == 'list':
            return self._eval_list(node, env)
        if kind == 'break':
            raise break_signal()
        if kind == 'unary':
            return self.eval_unary(node, env)
        if kind == 'binary':
            return self.eval_binary(node, env)
        if kind == 'assignment':
            return self.eval_assignment(node, env)
        if kind == 'subscript':
            return self.eval_subscript(node, env)
        if kind == 'member':
            obj = self.eval_node(node['member']['left'], env)
            return self._get_member(obj, node['member']['right']['name']['value'])
        if kind == 'function':
            return self.eval_function(node, env)
        if kind == 'new':
            typ = self.eval_node(node['new']['type'], env)
            args = [self.eval_node(a, env) for a in node['new']['include']]
            return self.construct(typ, args)
        if kind == 'ternary':
            cond = self.eval_node(node['ternary']['condition'], env)
            if isinstance(cond, code_value):
                cond = self.execute_code_value(cond)
            if self.truthy(cond):
                return self._eval_branch(node['ternary']['true_branch'], env)
            return self._eval_branch(node['ternary']['false_branch'], env)
        if kind == 'try':
            return self.eval_try(node, env)
        if kind == 'import':
            return self.eval_import(node, env)
        raise runtime_error('未知的节点类型: ' + kind)

    def _eval_list(self, node, env):
        lst = self._build_list([])
        for item in node['list']['items']:
            self._call_member(lst, 'append', [self.eval_node(item, env)])
        return lst

    # 一元运算符

    def _is_builtin_value(self, value):
        if not isinstance(value, instance):
            return True
        return (self._is_current('number', value.type)
            or self._is_current('boolean', value.type)
            or self._is_current('string', value.type)
            or self._is_current('list', value.type)
            or self._is_current('address', value.type)
            or self._is_current('error', value.type)
            or self._is_current('warning', value.type)
            or self._is_current('infinite_type', value.type)
            or self._is_current('nan_type', value.type)
            or self._is_current('library', value.type))

    def eval_unary(self, node, env):
        op = node['unary']['operator']
        operand = node['unary']['operand']
        if op == '??':
            # 注解读取有作用域：
            #   ??name        → 查当前文件/顶层作用域注解表
            #   ??lib.member  → lib 是已导入的库名，查该库独立注解空间
            #   ??type.member → 查当前作用域中的成员级注解（key 为 "type.member"）
            # 查不到一律报错（不再静默返回 none）
            if next(iter(operand)) == 'name':
                name = operand['name']['value']
                if name in self.annotations:
                    return self._build_string_from_py(self.annotations[name])
                if name in self.lib_annotations and '' in self.lib_annotations[name]:
                    return self._build_string_from_py(self.lib_annotations[name][''])
                raise runtime_error('注解不存在: ' + name)
            if next(iter(operand)) == 'member':
                left = operand['member']['left']
                right = operand['member']['right']
                if next(iter(left)) != 'name' or next(iter(right)) != 'name':
                    raise runtime_error('注解运算符 ?? 的成员链最多一层（库.成员）')
                lib_name = left['name']['value']
                member_name = right['name']['value']
                if lib_name in self.lib_annotations:
                    table = self.lib_annotations[lib_name]
                    if member_name in table:
                        return self._build_string_from_py(table[member_name])
                    raise runtime_error('注解不存在: ' + lib_name + '.' + member_name)
                key = lib_name + '.' + member_name
                if key in self.annotations:
                    return self._build_string_from_py(self.annotations[key])
                raise runtime_error('注解不存在: ' + key)
            raise runtime_error('注解运算符 ?? 的操作数必须是标识符或 库.成员')
        if op == '~':
            if env.parent is None:
                raise runtime_error('没有上级作用域')
            return self.eval_node(operand, env.parent)
        if op == '$' or op == 'return':
            raise return_signal(self.eval_node(operand, env))
        if op == '<-':
            raise throw_signal(self.eval_node(operand, env))
        if op == '!':
            return self._boolean(not self.truthy(self.eval_node(operand, env)))
        if op == '+':
            value = self.eval_node(operand, env)
            if isinstance(value, int):
                return value
            if isinstance(value, instance):
                method = self._find_method(value, 'positive')
                if method is not None:
                    return self._call(method, [self.address_space.allocate(value)])
                if self._is_builtin_value(value):
                    return value
                raise runtime_error('类型不支持一元正号')
            return value
        if op == '-':
            value = self.eval_node(operand, env)
            if isinstance(value, int):
                return - value
            if isinstance(value, instance):
                method = self._find_method(value, 'negative')
                if method is not None:
                    return self._call(method, [self.address_space.allocate(value)])
                return self._unary_minus(value)
            raise runtime_error('不支持一元负号')
        if op == '*':
            if next(iter(operand)) != 'name':
                raise runtime_error('声明符的操作数必须是名字')
            cell = self._resolve_or_declare(operand['name']['value'], env)
            return cell.address
        if op == '/':
            if next(iter(operand)) != 'name':
                raise runtime_error('解引用的操作数必须是名字')
            addr = self._resolve(operand['name']['value'], env).value
            if not isinstance(addr, str):
                raise runtime_error('解引用目标不是地址')
            cell = self.address_space.get(addr)
            if cell is None:
                raise runtime_error('无效的地址')
            return cell.value
        if op == '**':
            if next(iter(operand)) != 'name':
                raise runtime_error('引用声明的操作数必须是名字')
            name = operand['name']['value']
            old = self._resolve(name, env)
            new_cell = self.address_space.allocate(old.address)
            env.declare(name, new_cell)
            return new_cell.address
        if op == '***':
            if next(iter(operand)) == 'name':
                cell = self._resolve_or_declare(operand['name']['value'], env)
                cell.is_const = True
                return cell.address
            if next(iter(operand)) == 'member':
                obj = self.eval_node(operand['member']['left'], env)
                name = operand['member']['right']['name']['value']
                cell = obj.members.get(name)
                if cell is None:
                    self._check_addable(obj)
                    cell = self.address_space.allocate()
                    obj.members[name] = cell
                cell.is_const = True
                return cell.address
            raise runtime_error('常量声明的操作数必须是名字或成员')
        if op == 'type_of':
            return self._type_of(self.eval_node(operand, env))
        raise runtime_error('不支持的一元运算符: ' + op)

    def _unary_minus(self, value):
        if isinstance(value, int):
            return - value
        if isinstance(value, instance):
            if self._is_current('number', value.type):
                front_cell = value.members.get('front')
                back_cell = value.members.get('back')
                bd_cell = value.members.get('back_digits')
                number_type = self._resolve_global('number')
                obj = instance(number_type) if number_type is not None \
                    else instance(self._core_placeholders['number'])
                front = -front_cell.value if front_cell is not None else 0
                self._set_own_member(obj, 'front', front)
                self._set_own_member(obj, 'back', back_cell.value if back_cell else 0)
                self._set_own_member(obj, 'back_digits', bd_cell.value if bd_cell else 0)
                return obj
            if self._is_current('infinite_type', value.type):
                sign_cell = value.members.get('sign')
                sign = sign_cell.value if sign_cell else 1
                inf_type = self._resolve_global('infinite_type')
                obj = instance(inf_type) if inf_type is not None \
                    else instance(self._core_placeholders['infinite_type'])
                self._set_own_member(obj, 'sign', -sign)
                self._set_own_member(obj, 'infinity', True)
                return obj
            if self._is_current('nan_type', value.type):
                return self._make_nan_literal()
        raise runtime_error('不支持一元负号')

    def _type_of(self, value):
        if isinstance(value, int):
            return self._resolve_global('integer')
        if isinstance(value, instance):
            return value.type
        if isinstance(value, str):
            return self._resolve_global('address')
        if isinstance(value, code_value):
            return self._resolve_global('code')
        if isinstance(value, builtin_function):
            return self._resolve_global('code')
        if isinstance(value, type_object):
            return self.type_type
        raise runtime_error('无法获取值的类型')

    # 赋值

    def _assign_target(self, left, env):
        kind = next(iter(left))
        if kind == 'name':
            return self._resolve_assign(left['name']['value'], env)
        if kind == 'unary':
            op = left['unary']['operator']
            operand = left['unary']['operand']
            if op == '*':
                if next(iter(operand)) != 'name':
                    raise runtime_error('声明符的操作数必须是名字')
                return self._resolve_or_declare(operand['name']['value'], env)
            if op == '**':
                if next(iter(operand)) != 'name':
                    raise runtime_error('引用声明的操作数必须是名字')
                name = operand['name']['value']
                old = self._resolve(name, env)
                new_cell = self.address_space.allocate(old.address)
                env.declare(name, new_cell)
                return new_cell
            if op == '***':
                if next(iter(operand)) == 'name':
                    cell = self._resolve_or_declare(operand['name']['value'], env)
                    cell.is_const = True
                    return cell
                if next(iter(operand)) == 'member':
                    obj = self.eval_node(operand['member']['left'], env)
                    name = operand['member']['right']['name']['value']
                    cell = obj.members.get(name)
                    if cell is None:
                        self._check_addable(obj)
                        cell = self.address_space.allocate()
                        obj.members[name] = cell
                    cell.is_const = True
                    return cell
                raise runtime_error('常量声明的操作数必须是名字或成员')
            if op == '/':
                if next(iter(operand)) != 'name':
                    raise runtime_error('解引用的操作数必须是名字')
                addr = self._resolve(operand['name']['value'], env).value
                if not isinstance(addr, str):
                    raise runtime_error('解引用目标不是地址')
                cell = self.address_space.get(addr)
                if cell is None:
                    raise runtime_error('无效的地址')
                return cell
            raise runtime_error('无效的赋值目标')
        if kind == 'member':
            obj = self.eval_node(left['member']['left'], env)
            name = left['member']['right']['name']['value']
            if not isinstance(obj, (instance, type_object)):
                raise runtime_error('无法设置成员: ' + name)
            cell = obj.members.get(name)
            if cell is None:
                self._check_addable(obj)
                cell = self.address_space.allocate()
                obj.members[name] = cell
            return cell
        if kind == 'subscript':
            obj = self.eval_node(left['subscript']['left'], env)
            idx = self.eval_node(left['subscript']['right'], env)
            if isinstance(obj, instance):
                index_method = self._find_method(obj, 'index')
                if index_method is not None:
                    receiver = self.address_space.allocate(obj)
                    idx_cell = self.address_space.allocate(idx)
                    result = self._call(index_method, [receiver, idx_cell])
                    cell = self._addr_to_cell(result)
                    if cell is not None:
                        return cell
            raise runtime_error('类型不支持下标操作')
        raise runtime_error('无效的赋值目标')

    def eval_assignment(self, node, env):
        op = node['assignment']['operator']
        target = node['assignment']['left']
        right = node['assignment']['right']
        # 下标赋值：统一调用对象的 index 函数，根据返回的可写地址进行更改；
        # index 未命中（返回 none 等非地址结果）时，若对象提供 index_set（插入语义）则调用
        if next(iter(target)) == 'subscript':
            obj = self.eval_node(target['subscript']['left'], env)
            idx = self.eval_node(target['subscript']['right'], env)
            if not isinstance(obj, instance):
                raise runtime_error('类型不支持下标写入')
            if op == '=':
                v = self.eval_node(right, env)
                self._subscript_store(obj, idx, v)
                return v
            old = self.eval_subscript(target, env)
            r = self.eval_node(right, env)
            v = self._binary_apply(op[:-1], old, r)
            self._subscript_store(obj, idx, v)
            return v
        if op == '=':
            cell = self._assign_target(target, env)
            v = self.eval_node(right, env)
            # `=` 右操作数为标识符时深拷贝其存储内容（引用别名用 `**`，不拷贝）
            if next(iter(right)) == 'name' and not (next(iter(target)) == 'unary' and target['unary']['operator'] == '**'):
                v = self._deep_copy(v)
            # 常量首次绑定时标记其指向对象的成员树；仅在非函数作用域生效，
            # 避免 bootstrap/用户函数内部 `*** node = ...` 等局部常量声明
            # 把共享对象（如 list 元素节点）误标为常量。
            if cell.is_const and not cell.initialized and not self._in_function_scope(env):
                self._mark_tree_const(v)
            self.address_space.write(cell, v)
            return v
        cell = self._assign_target(target, env)
        old = cell.value
        r = self.eval_node(right, env)
        inner = op[:-1]
        v = self._binary_apply(inner, old, r)
        self.address_space.write(cell, v)
        return v

    # 下标统一写入：index 返回可写地址则写，未命中时走 index_set 插入
    def _subscript_store(self, obj, idx, value):
        if not isinstance(obj, instance):
            raise runtime_error('类型不支持下标写入')
        index_method = self._find_method(obj, 'index')
        if index_method is None:
            raise runtime_error('类型不支持下标写入')
        result = self._call(index_method, [
            self.address_space.allocate(obj),
            self.address_space.allocate(idx)])
        cell = self._addr_to_cell(result)
        if cell is not None:
            self.address_space.write(cell, value)
            return
        set_method = self._find_method(obj, 'index_set')
        if set_method is None:
            raise runtime_error('下标结果不提供可写地址')
        self._call(set_method, [
            self.address_space.allocate(obj),
            self.address_space.allocate(idx),
            self.address_space.allocate(value)])

    # 把 index 返回值转换为可写 cell：str 视为地址，instance 取其 value 成员 cell
    def _addr_to_cell(self, result):
        if isinstance(result, str):
            cell = self.address_space.get(result)
            if cell is None:
                raise runtime_error('无效的地址')
            return cell
        if isinstance(result, instance):
            value_cell = result.members.get('value')
            if value_cell is not None:
                return value_cell
        return None

    # 二元运算符

    def eval_binary(self, node, env):
        op = node['binary']['operator']
        if op == '=>':
            return self._eval_arrow(node, env)
        if op == '$$':
            return self._eval_loop(node, env)
        if op == '<<':
            return self._eval_output(node, env)
        if op == '>>':
            return self._eval_input(node, env)
        if op == 'in':
            return self._eval_in(node, env)
        if op in ('&&', '||'):
            return self._eval_logic(node, env)
        left = self.eval_node(node['binary']['left'], env)
        right = self.eval_node(node['binary']['right'], env)
        return self._binary_apply(op, left, right)

    def _binary_apply(self, op, left, right):
        if op in _arith_slot:
            return self._arith(op, left, right)
        if op in _cmp_slot:
            return self._compare(op, left, right)
        raise runtime_error('不支持的运算符: ' + op)

    def _arith(self, op, left, right):
        if isinstance(left, int) and isinstance(right, int):
            return self._int_arith(op, left, right)
        method = self._find_method(left, _arith_slot[op])
        if method is None:
            raise runtime_error('类型不支持运算: ' + op)
        receiver = self.address_space.allocate(left)
        arg = self.address_space.allocate(right)
        return self._call(method, [receiver, arg])

    def _int_arith(self, op, a, b):
        if op == '+':
            return a + b
        if op == '-':
            return a - b
        if op == '*':
            return a * b
        if op == '/' or op == '\\':
            if b == 0:
                raise runtime_error('除数不能为 0')
            return a // b
        if op == '%':
            if b == 0:
                raise runtime_error('模运算除数不能为 0')
            return a % b
        if op == '^':
            if b < 0:
                raise runtime_error('不支持负指数')
            return a ** b
        raise runtime_error('不支持的运算符: ' + op)

    def _compare(self, op, left, right):
        if self._is_type(left) or self._is_type(right) \
            or isinstance(left, type_object) or isinstance(right, type_object):
            return self._compare_identity(op, left, right)
        if isinstance(left, int) and isinstance(right, int):
            if op == '>':
                return self._boolean(left > right)
            if op == '<':
                return self._boolean(left < right)
            if op == '>=':
                return self._boolean(left >= right)
            if op == '<=':
                return self._boolean(left <= right)
            if op == '==':
                return self._boolean(left == right)
            if op == '!=':
                return self._boolean(left != right)
        method = self._find_method(left, _cmp_slot[op])
        if method is not None:
            receiver = self.address_space.allocate(left)
            arg = self.address_space.allocate(right)
            return self._call(method, [receiver, arg])
        slots, combine = _fallback_map[op]
        results = []
        for slot in slots:
            m = self._find_method(left, slot)
            if m is None:
                return self._compare_fallback(op, left, right)
            receiver = self.address_space.allocate(left)
            arg = self.address_space.allocate(right)
            results.append(self.truthy(self._call(m, [receiver, arg])))
        if combine == 'or':
            return self._boolean(not any(results))
        return self._boolean(not results[0])

    def _compare_fallback(self, op, left, right):
        method = self._find_method(left, 'compare')
        if method is not None:
            receiver = self.address_space.allocate(left)
            arg = self.address_space.allocate(right)
            sign = self._compare_sign(self._call(method, [receiver, arg]))
            if op == '>':
                return self._boolean(sign > 0)
            if op == '<':
                return self._boolean(sign < 0)
            if op == '>=':
                return self._boolean(sign >= 0)
            if op == '<=':
                return self._boolean(sign <= 0)
            if op == '==':
                return self._boolean(sign == 0)
            if op == '!=':
                return self._boolean(sign != 0)
            raise runtime_error('不支持的运算符: ' + op)
        return self._compare_identity(op, left, right)

    def _compare_identity(self, op, left, right):
        identical = left is right
        if op == '==':
            return self._boolean(identical)
        if op == '!=':
            return self._boolean(not identical)
        if op == '<=' or op == '>=':
            return self._boolean(identical)
        if op == '<' or op == '>':
            return self._boolean(False)
        raise runtime_error('不支持的运算符: ' + op)

    def _compare_sign(self, value):
        if isinstance(value, int):
            return value
        if isinstance(value, instance):
            if self._is_current('number', value.type):
                front_cell = value.members.get('front')
                back_cell = value.members.get('back')
                front = front_cell.value if front_cell is not None else 0
                back = back_cell.value if back_cell is not None else 0
                return front if front != 0 else back
        raise runtime_error('compare 特殊成员的返回值必须是 integer 或 number')

    def _eval_logic(self, node, env):
        op = node['binary']['operator']
        left = self.eval_node(node['binary']['left'], env)
        if op == '&&':
            if not self.truthy(left):
                return self._boolean(False)
            return self._boolean(self.truthy(self.eval_node(node['binary']['right'], env)))
        if self.truthy(left):
            return self._boolean(True)
        return self._boolean(self.truthy(self.eval_node(node['binary']['right'], env)))

    # 匿名函数
    def _eval_arrow(self, node, env):
        params, defaults = self._extract_params(node['binary']['left'])
        right_ast = node['binary']['right']
        if next(iter(right_ast)) != 'code':
            raise runtime_error('=> 右侧必须是代码块 { ... }')
        cv = code_value(right_ast['code']['statements'], env,
            params = params, defaults = defaults)
        fn_type = self._resolve_global('function_type')
        if fn_type is None:
            raise runtime_error('function_type 类型未就绪')
        fn = instance(fn_type)
        self._set_own_member(fn, 'code', cv)
        return fn

    def _extract_params(self, left):
        params = []
        defaults = []
        for item in left['list']['items']:
            kind = next(iter(item))
            if kind == 'name':
                params.append(item['name']['value'])
                defaults.append(None)
            elif kind == 'unary':
                params.append(item['unary']['operand']['name']['value'])
                defaults.append(None)
            elif kind == 'list':
                first = item['list']['items'][0]
                params.append(first['unary']['operand']['name']['value'])
                if len(item['list']['items']) >= 3:
                    defaults.append(item['list']['items'][2])
                else:
                    defaults.append(None)
            else:
                raise runtime_error('无效的参数声明')
        return params, defaults

    # $$ 循环
    def _eval_loop(self, node, env):
        results = []
        while True:
            cond_value = self.eval_node(node['binary']['left'], env)
            cond_result = self._eval_condition_value(cond_value)
            if not self.truthy(cond_result):
                break
            body_value = self.eval_node(node['binary']['right'], env)
            try:
                if isinstance(body_value, code_value):
                    result = self.execute_code_value(body_value)
                else:
                    result = body_value
                results.append(result)
            except break_signal:
                break
        return self._build_list(results)

    def _eval_condition_value(self, value):
        if isinstance(value, instance):
            init = self._find_method(value, 'init')
            if init is not None:
                return self._call(init, [self.address_space.allocate(value)])
            return self._boolean(False)
        if isinstance(value, code_value):
            return self.execute_code_value(value)
        return value

    # 输出 <<
    def _eval_output(self, node, env):
        right = self.eval_node(node['binary']['right'], env)
        char_list = self._get_string_value(right)
        handler = self.eval_node(node['binary']['left'], env)
        list_cell = self.address_space.allocate(char_list)
        processed = self._call(handler, [list_cell])
        codes = self._list_to_py(processed)
        sys.stdout.write(''.join(chr(c) for c in codes))
        return self._get_none()

    # 输入 >>
    def _eval_input(self, node, env):
        line = sys.stdin.readline()
        if line.endswith('\n'):
            line = line[:-1]
        if line.endswith('\r'):
            line = line[:-1]
        text = self._build_string_from_py(line)
        handler = self.eval_node(node['binary']['left'], env)
        text_cell = self.address_space.allocate(text)
        processed = self._call(handler, [text_cell])
        target = self._assign_target(node['binary']['right'], env)
        self.address_space.write(target, processed)
        return processed

    def _get_string_value(self, obj):
        if isinstance(obj, int):
            if not 0 <= obj <= 0x10FFFF:
                raise runtime_error('无效的字符码: ' + str(obj))
            return self._build_list([obj])
        method = self._find_method(obj, 'string')
        if method is None:
            raise runtime_error('缺少 string 特殊成员')
        return self._call(method, [self.address_space.allocate(obj)])

    def _list_to_py(self, obj):
        if not isinstance(obj, instance):
            raise runtime_error('输出结果必须是字符链表')
        node = None
        head_cell = obj.members.get('head')
        if head_cell is not None:
            node = head_cell.value
        else:
            data_cell = obj.members.get('data')
            if data_cell is not None and isinstance(data_cell.value, instance):
                inner = data_cell.value.members.get('head')
                if inner is not None:
                    node = inner.value
        result = []
        none = self._get_none()
        while node is not None and node is not none:
            value_cell = node.members.get('value')
            if value_cell is None:
                break
            result.append(value_cell.value)
            next_cell = node.members.get('next')
            node = next_cell.value if next_cell is not None else none
        return result

    # 值的显示转换：优先 string 特殊成员，缺失时结构化转储

    def _display_string(self, obj) -> str:
        return self._display_string_indented(obj, '', set())

    def _display_string_indented(self, obj, pad, seen):
        if obj is None:
            return '<none>'
        if isinstance(obj, bool):
            return 'true' if obj else 'false'
        if isinstance(obj, int):
            return str(obj)
        if isinstance(obj, str):
            return obj
        if isinstance(obj, (instance, type_object)):
            try:
                char_list = self._get_string_value(obj)
                if char_list is obj:
                    oid = id(obj)
                    if oid in seen:
                        return '<循环引用>'
                    seen.add(oid)
                    try:
                        elements = self._list_to_py(char_list)
                        return '[' + ', '.join(
                            self._display_string_indented(e, pad, seen) for e in elements) + ']'
                    finally:
                        seen.discard(oid)
                codes = self._list_to_py(char_list)
                return ''.join(chr(c) for c in codes)
            except Exception:
                hash_method = self._find_method(obj, 'hash')
                if hash_method is not None:
                    result = self._call(
                        hash_method, [self.address_space.allocate(obj)])
                    if isinstance(result, int):
                        return str(result)
                    return self._display_string_indented(result, pad, seen)
                return self._dump_object(obj, pad, seen)
        if isinstance(obj, code_value):
            return '<code>'
        if isinstance(obj, builtin_function):
            return '<builtin ' + obj.name + '>'
        return repr(obj)

    def _dump_object(self, obj, pad, seen):
        oid = id(obj)
        if oid in seen:
            return '<循环引用>'
        seen.add(oid)
        try:
            type_name = self._type_label(obj)
            addr = self._find_cell_address(obj)
            head = type_name if addr == '<addr>' else '%s: %s' % (type_name, addr)
            parts = []
            for name, cell in obj.members.items():
                if cell is None or name in _dump_skip:
                    continue
                value = cell.value
                text = self._display_string_indented(value, pad, seen)
                parts.append('%s = %s' % (name, text))
            if parts:
                return '<%s, %s>' % (head, ', '.join(parts))
            return '<%s>' % head
        finally:
            seen.discard(oid)

    def _type_label(self, obj):
        if isinstance(obj, type_object):
            return 'type ' + obj.name if obj.name else 'type'
        if isinstance(obj, instance):
            if self._is_type(obj):
                gname = self._global_name_of(obj)
                return 'type ' + gname if gname else 'type'
            return self._name_of_type(obj.type)
        return type(obj).__name__

    def _name_of_type(self, typ):
        name = getattr(typ, 'name', None)
        if name:
            return name
        return self._global_name_of(typ) or 'instance'

    def _global_name_of(self, value):
        for gname, gcell in self.global_scope.names.items():
            if gcell.value is value:
                return gname
        return None

    def _find_cell_address(self, obj):
        for cell in self.address_space.cells.values():
            if cell.value is obj:
                return cell.address
        return '<addr>'

    # in 运算符
    def _eval_in(self, node, env):
        left = self.eval_node(node['binary']['left'], env)
        right = self.eval_node(node['binary']['right'], env)
        if not isinstance(right, instance):
            raise runtime_error('in 的右侧必须是实例')
        index_method = self._find_method(right, 'index')
        if index_method is None:
            raise runtime_error('in 要求右侧类型注册 index 特殊成员')
        size_cell = right.members.get('size')
        size = size_cell.value if size_cell is not None else None
        if size is None:
            size_method = self._find_method(right, 'size')
            if size_method is not None:
                size = self._call(size_method, [self.address_space.allocate(right)])
        i = 0
        while True:
            if size is not None and isinstance(size, int) and i >= size:
                return self._boolean(False)
            try:
                element = self._call(index_method, [
                    self.address_space.allocate(right),
                    self.address_space.allocate(i),
                ])
            except runtime_error:
                return self._boolean(False)
            if self.truthy(self._compare('==', left, element)):
                return self._boolean(True)
            i += 1

    # 尝试结构

    def eval_try(self, node, env):
        try:
            result = self._eval_branch(node['try']['left'], env)
        except (throw_signal, runtime_error) as e:
            if isinstance(e, throw_signal):
                error_value = e.value
            else:
                error_value = self._build_error_value(e.message)
            self._bind_error_arg(node['try']['error_arg'], error_value, env)
            return self._eval_branch(node['try']['catch_block'], env)
        else_block = node['try']['else_block']
        if else_block is not None:
            return self._eval_branch(else_block, env)
        return result

    def _build_error_value(self, message):
        err_type = self._resolve_global('error')
        if err_type is not None:
            try:
                return self.construct(err_type, [self._build_string_from_py(message)])
            except Exception:
                pass
        return self._build_string_from_py(message)

    def _bind_error_arg(self, error_arg, value, env):
        node = error_arg
        if next(iter(node)) == 'unary':
            node = node['unary']['operand']
        if next(iter(node)) != 'name':
            raise runtime_error('try 的错误参数必须是名字')
        cell = self._resolve_or_declare(node['name']['value'], env)
        self.address_space.write(cell, value)

    # 下标 / 调用

    def eval_subscript(self, node, env):
        obj = self.eval_node(node['subscript']['left'], env)
        idx = self.eval_node(node['subscript']['right'], env)
        if not isinstance(obj, instance):
            raise runtime_error('类型不支持下标操作')
        index_method = self._find_method(obj, 'index')
        if index_method is not None:
            receiver = self.address_space.allocate(obj)
            idx_cell = self.address_space.allocate(idx)
            result = self._call(index_method, [receiver, idx_cell])
            if isinstance(result, str):
                cell = self.address_space.get(result)
                if cell is None:
                    raise runtime_error('无效的地址')
                return cell.value
            if isinstance(result, instance):
                value_cell = result.members.get('value')
                if value_cell is not None:
                    return value_cell.value
            return result
        init = self._find_method(obj, 'init')
        if init is not None:
            return self.construct(obj.type, [idx])
        raise runtime_error('类型不支持下标操作')

    def eval_function(self, node, env):
        name_node = node['function']['name']
        arg_asts = node['function']['arg']
        if next(iter(name_node)) == 'name' and name_node['name']['value'] == 'help':
            if len(arg_asts) != 1 or next(iter(arg_asts[0])) != 'name':
                raise runtime_error('help 的参数必须是标识符')
            target = arg_asts[0]['name']['value']
            content = self.annotations.get(target)
            if content is None:
                return self._get_none()
            return self._build_string_from_py(content)
        args = [self.eval_node(a, env) for a in arg_asts]
        arg_cells = [self.address_space.allocate(v) for v in args]
        if next(iter(name_node)) == 'member':
            receiver = self.eval_node(name_node['member']['left'], env)
            member_name = name_node['member']['right']['name']['value']
            callable_obj = self._get_member(receiver, member_name)
            lib_type = self._resolve_global('library')
            if lib_type is not None and receiver.type is lib_type:
                return self._call(callable_obj, arg_cells)
            receiver_cell = self.address_space.allocate(receiver)
            return self._call(callable_obj, [receiver_cell] + arg_cells)
        callable_obj = self.eval_node(name_node, env)
        return self._call(callable_obj, arg_cells)
