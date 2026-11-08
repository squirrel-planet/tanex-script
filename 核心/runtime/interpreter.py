# 运行时解释器

import os
import sys
import json
import socket
import types
import importlib
from collections.abc import Iterator
from errors import warning, output_message
from runtime.environment import address_space
from runtime.environment import scope
from runtime.environment import storage_cell
from runtime.values import type_object
from runtime.values import instance
from runtime.values import code_value
from runtime.values import builtin_function
from runtime.values import python_function
from runtime.values import python_lazy_module
from runtime.values import runtime_error
from runtime.values import throw_signal
from runtime.values import return_signal
from runtime.values import break_signal
from runtime.values import contiune_signal

_arith_slot = {
    '+': 'addition',
    '-': 'subtract',
    '*': 'multiply',
    '/': 'divide',
    '\\': 'exactly_divisible',
    '%': 'modulo',
    '^': 'power'
}
_cmp_slot = {
    '>': 'greater',
    '<': 'less',
    '>=': 'greater_equal',
    '<=': 'less_equal',
    '==': 'equal',
    '!=': 'not_equal'
}
_fallback_map = {
    '>': [['less', 'equal'], 'or'],
    '<': [['greater', 'equal'], 'or'],
    '>=': [['less'], 'not'],
    '<=': [['greater'], 'not'],
    '==': [['not_equal'], 'not'],
    '!=': [['equal'], 'not']
}

# 运算符反向兜底映射：左操作数无对应方法时，尝试右操作数的 other_<method>
# 例如 a + b：先试 a.addition(b)，失败则试 b.other_addition(a)
_other_arith_slot = {op: 'other_' + method for op, method in _arith_slot.items()}
_other_cmp_slot = {op: 'other_' + method for op, method in _cmp_slot.items()}

# python_api 桥接：不能用作 TanexScript 成员名的保留词。
# 与 tokenizer 的 _non_value_words / _keyword_aliases 保持一致，避免
# python_api.foo.return 这类成员名在解析阶段被当成关键字。
_py_reserved_names = frozenset(
    {
        'return', 'break', 'contiune', 'in', 'type_of', 'import',
        'and', 'or', 'not', 'is', 'delete', 'help', 'self',
        'true', 'false', 'none', 'public'
    }
)
# 写回失败回滚时用来区分「属性原本不存在」与「属性值恰好是 None」
_py_missing = object()

# 投影时不能展开的 Python 内部对象：generator.gi_frame -> f_globals -> 整个
# 模块命名空间这类对象图会无限 / 爆炸式展开，曾导致解释器卡死。
_py_internal_types = tuple(
    t for t in (
        getattr(types, 'ModuleType', None),
        getattr(types, 'FrameType', None),
        getattr(types, 'CodeType', None),
        getattr(types, 'TracebackType', None),
        getattr(types, 'GeneratorType', None),
        getattr(types, 'CoroutineType', None),
        getattr(types, 'AsyncGeneratorType', None)
    ) if t is not None
)
# 一次转换最多产生的投影节点数 / 迭代器最多物化的元素数（兜底，防卡死）
_py_max_projection_nodes = 2000
_py_max_iter_items = 10000
_copy_skip = frozenset(
    {
        'addable',
        'external_read_only',
        'inherit',
        'readonly',
        'sealed',
        'closed'
    }
)
_dump_skip = frozenset(
    {
        'inherit',
        'initialize',
        'boolean',
        'string',
        'index',
        'addition',
        'subtract',
        'multiply',
        'divide',
        'exactly_divisible',
        'modulo',
        'power',
        'greater',
        'less',
        'greater_equal',
        'less_equal',
        'equal',
        'not_equal',
        'compare',
        'positive',
        'negative',
        'addable',
        'external_read_only',
        'public'
    }
)

class interpreter(object):

    def __init__(self):
        self.address_space = address_space()
        self.global_scope = scope()
        self.type_type: type_object | None = None
        self._none_fallback: instance | None = None
        self._core_placeholders = {}
        # python_api 桥接：Python 对象 → TanexScript wrapper 的缓存。
        # {id(py_obj): (py_obj, wrapper)}，强引用 py_obj 防止 id 被复用；
        # 保证同一 Python 对象始终映射为同一个 wrapper（身份一致）。
        self._py_obj_cache = {}
        # 实时投影刷新时的重入保护：记录正在同步的 wrapper id，
        # 避免 Python 侧循环引用（a.b -> b.a）造成无限递归。
        self._py_sync_active = set()
        # 执行容器自身的方法（list.append / dictionary.index_set 等）期间，
        # 必须暂停该容器的读时同步：引导库会先改 head/tail 再改 size，
        # 中途同步会把半完成的结构当成「TS 侧写入」提前吸收，破坏 size。
        self._py_sync_suppressed = {}
        # 单次 Python→TanexScript 转换的投影节点计数（防对象图爆炸卡死）
        self._py_projection_count = 0
        self.annotations = {}
        self._public_names = set()
        self._bootstrap_names = set()
        self._outside_bootstrap = False
        self._io_type: instance | None = None
        self._loaded_libs: dict[str, instance] = {}

        # 库注解空间：{导入名: {目标: 注解内容}}，import 时单独存放，不污染全局
        self.lib_annotations: dict[str, dict[str, str]] = {}

        # 按库路径暂存注解表，供 eval_import 绑定到导入名
        self._lib_annotation_tables: dict[str, dict[str, str]] = {}

        # 运行时错误定位上下文：当前正在执行的源文件与最近求值节点位置
        self._current_file: str | None = None
        self._current_pos: list | None = None

        # 调用链回溯帧栈：[(文件, 行, 列, 描述)]，进入函数/代码块时压帧，退出时弹帧
        self._frame_stack: list[tuple] = []

        # 断点调试器：-d/--debug 启动时注入
        self._debugger = None

        # -r 透传的程序参数：set_program_args 注入，运行用户程序前生成 args 引导库
        self.program_args: list | None = None

        # 程序目录：set_program_dir 注入，运行用户程序前生成 path 引导库
        self._program_dir: str | None = None

    # 接收 -r 后透传的程序参数（list[str]），供 args 引导库使用
    def set_program_args(self, program_args):
        self.program_args = list(program_args or [])

    # 接收用户程序所在目录（绝对路径），供 path 引导库使用
    def set_program_dir(self, program_dir):
        self._program_dir = os.path.abspath(program_dir) if program_dir else None

    # 在当前文件上下文执行语句列表；错误冒泡出边界时补上定位信息
    def _run_in_file(self, statements, file):
        saved_file = self._current_file
        saved_pos = self._current_pos
        if file:
            self._current_file = file
        self._current_pos = None
        self._push_frame('<模块>')
        try:
            return self.run_statements(statements)
        except runtime_error as e:
            self._attach_trace(e)
            e.annotate(self._current_file, self._current_pos)
            raise
        finally:
            self._pop_frame()
            self._current_file = saved_file
            self._current_pos = saved_pos

    # 调用链回溯：压入一帧（用进入前的文件与最近求值位置作为调用点）
    def _push_frame(self, label):
        pos = self._current_pos
        self._frame_stack.append(
            (
                self._current_file,
                pos[0] if pos else None,
                pos[1] if pos else None,
                label
            )
        )

    # 调用链回溯：弹出最外层帧
    def _pop_frame(self):
        if self._frame_stack:
            self._frame_stack.pop()

    # 异常冒泡时挂一次完整调用链快照（只挂首次，避免外层覆盖）
    def _attach_trace(self, e):
        if getattr(e, 'trace', None) is None:
            e.trace = list(self._frame_stack)

    # 从函数调用表达式提取回溯帧描述（foo 或 obj.method）
    def _frame_label_from_call(self, name_node):
        if next(iter(name_node)) == 'name':
            return name_node['name']['value']
        if next(iter(name_node)) == 'member':
            left = name_node['member']['left']
            right = name_node['member']['right']
            if next(iter(left)) == 'name' and next(iter(right)) == 'name':
                return left['name']['value'] + '.' + right['name']['value']
            return '<方法>'
        return '<调用>'

    # 在指定文件上下文中求值单个节点（如函数默认值表达式），求值后恢复上下文
    def _eval_in_file(self, node, env, file):
        saved_file = self._current_file
        saved_pos = self._current_pos
        if file:
            self._current_file = file
        self._current_pos = None
        try:
            return self.eval_node(node, env)
        finally:
            self._current_file = saved_file
            self._current_pos = saved_pos

    # 从编译产物路径推导同名源码路径（.tscc/.tscl -> .tsuc），
    # 源码存在时优先指向源码，便于错误展示代码行
    @staticmethod
    def _resolve_source_path(compiled_path):
        if compiled_path.endswith('.tsuc'):
            return compiled_path
        if compiled_path.endswith(('.tscc', '.tscl')):
            cand = compiled_path[:-5] + '.tsuc'
            if os.path.exists(cand):
                return cand
        return compiled_path

    # 启动阶段：建立核心类型骨架
    def init_core(self):
        self.type_type = type_object('type_type')
        self.type_type.inherit = self.type_type
        self.type_type.members['addable'] = self.address_space.allocate(1)
        self.type_type.members['initialize'] = self.address_space.allocate(
            builtin_function(self._builtin_type_initialize, 'type_type.initialize')
        )
        cell = self.address_space.allocate(self.type_type)
        cell.is_const = True
        self.global_scope.declare('type_type', cell)
        for name in (
            'integer',
            'string',
            'number',
            'boolean',
            'none_type',
            'infinite_type',
            'nan_type',
            'list',
            'code',
            'address',
            'error',
            'warning',
            'library'
        ):
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

        # poly_function 分派辅助：读取函数（lambda / code_value）的参数类型标注，
        # 返回“参数类型列表的列表”，每个元素是该位置参数允许的类型对象列表。
        param_types_fn = builtin_function(self._builtin_param_types, 'param_types')
        cell = self.address_space.allocate(param_types_fn)
        cell.is_const = True
        self.global_scope.declare('param_types', cell)

        # poly_function 分派辅助：把列表元素作为位置参数展开调用函数，
        # 即 invoke(func, args_list) 等价于 func(args_list[0], args_list[1], ...)。
        invoke_fn = builtin_function(self._builtin_invoke, 'invoke')
        cell = self.address_space.allocate(invoke_fn)
        cell.is_const = True
        self.global_scope.declare('invoke', cell)

        # poly_function 分派辅助：判断实参值是否匹配某位置的声明类型列表。
        # 在解释器内部按类型名比较（带 integer/number 互认），不依赖 TanexScript 层 == 身份。
        arg_matches_fn = builtin_function(self._builtin_arg_matches, 'arg_matches_type')
        cell = self.address_space.allocate(arg_matches_fn)
        cell.is_const = True
        self.global_scope.declare('arg_matches_type', cell)

    def _builtin_param_types(self, interp, receiver, args):
        func = receiver
        cv = self._as_code_value(func)
        name_lists = []
        for i in range(len(cv.params)):
            names = self._declared_type_names(cv, i)
            name_lists.append(
                self._build_list([self._build_string_from_py(n) for n in names])
            )
        return self._build_list(name_lists)

    def _declared_type_names(self, cv, index):
        # 直接从参数类型标注 AST 读取类型名字符串（不经过类型对象查找，
        # 避免类型对象经列表深拷贝克隆后在全局作用域中无法定位、导致按名比较失效）。
        types = getattr(cv, 'types', None)
        if not types or index >= len(types):
            return []
        ast = types[index]
        if ast is None:
            return []
        kind = next(iter(ast))
        if kind == 'name':
            return [ast['name']['value']]
        if kind == 'list':
            names = []
            for it in ast['list']['items']:
                if next(iter(it)) != 'name':
                    raise runtime_error('类型标注必须是类型名或类型名列表')
                names.append(it['name']['value'])
            return names
        raise runtime_error('类型标注必须是类型名或类型名列表')

    def _as_code_value(self, func):
        if isinstance(func, code_value):
            return func
        if isinstance(func, instance) and self._is_current('function_type', func.type):
            code_cell = func.members.get('code')
            if code_cell is None or not isinstance(code_cell.value, code_value):
                raise runtime_error('function 值缺少 code')
            return code_cell.value
        raise runtime_error('param_types 仅支持函数（lambda / code_value / function_type 实例）')

    def _builtin_invoke(self, interp, receiver, args):
        func = receiver
        if not args:
            raise runtime_error('invoke 需要两个参数：函数与实参列表')
        arg_list = args[0]
        if not (isinstance(arg_list, instance) and self._is_current('list', arg_list.type)):
            raise runtime_error('invoke 第二个参数必须是列表')
        py_args = self._list_to_py(arg_list)
        cells = [self.address_space.allocate(v) for v in py_args]
        return self._call(func, cells)

    def _builtin_arg_matches(self, interp, receiver, args):
        # receiver：实际实参值；args[0]：该位置声明的类型名字符串列表（list of string）。
        # 在解释器内部用 _type_of 取实参类型名，再与声明类型名逐个比较（含 integer/number 互认），
        # 不依赖类型对象身份或 TanexScript 层 ==，分派稳健。
        actual = self._type_of(receiver)
        actual_name = self._type_name(actual)
        if not args:
            raise runtime_error('arg_matches_type 需要两个参数：实参与声明类型名称列表')
        decl_list = args[0]
        if not (isinstance(decl_list, instance) and self._is_current('list', decl_list.type)):
            raise runtime_error('arg_matches_type 第二个参数必须是类型名称列表')
        for item in self._list_to_py(decl_list):
            decl_name = self._string_to_py(item) if isinstance(item, instance) else str(item)
            if self._type_name_equal(actual_name, decl_name):
                return True
        return False

    def _type_name_equal(self, a, b):
        # 类型名相容：同名，或 integer/number 互认
        if a == b:
            return True
        if a == 'integer' and b == 'number' or (a == 'number' and b == 'integer'):
            return True
        return False

    def _builtin_type_initialize(self, interp, receiver, args):
        inherit = args[0] if args else self.type_type

        # Validate that inherit is actually a type (type_type instance)
        # Check if inherit is a type (type_type or its instance)
        # Allow self.type_type as a valid inherit (parent type)
        if not isinstance(inherit, (instance, type_object)):
            raise runtime_error('type_type: 继承必须是类型')

        # For instances, check that their type is type_type
        if isinstance(inherit, instance) and inherit.type != self.type_type:
            raise runtime_error('type_type: 继承必须是类型')
        self.set_member(receiver, 'inherit', inherit)
        return receiver

    # 解析 JSON 内容，失败时给出中文报错
    def _parse_json_or_raise(self, content, path):
        # 兼容新 .tscl：块内容已是解析后的对象（dict/list），直接使用
        if isinstance(content, (dict, list)):
            return content
        try:
            return json.loads(content)
        except (json.JSONDecodeError, TypeError) as e:
            raise runtime_error(
                f'无法解析文件: {path}，无法运行（JSON 解析错误: 第 {e.lineno} 行 第 {e.colno} 列）'
            )

    # 读取并解析 JSON 文件，失败时给出中文报错
    def _load_json_file(self, path):
        with open(path, 'r', encoding = 'utf-8') as f:
            content = f.read()
        return self._parse_json_or_raise(content, path)

    # 运行用户程序前注入运行时引导常量（在 init_core / load_bootstrap 之后调用）。
    # 注入三件套：
    #   args          仅当已接收 program_args（-r 透传）时注入，list of string，
    #                 argv[0] 为程序名，其余为 -r 后透传的参数；长度用 args.size，
    #                 按下标 args[i] 取第 i 个参数。
    #   path          程序目录（用户程序所在目录），string；未显式设置时回退当前工作目录。
    #                 REPL 模式下没有用户程序，填充为 none。
    #   program_path  TanexScript 安装目录，string；用于 import program_path + "/libary/xxx"
    #                 以绝对路径引入库文件，适配不同环境。
    def inject_args(self, repl_mode = False):
        # program_path：优先复用预编译器的安装目录解析（libary 所在上级），
        # 失败时回退为解释器所在目录的上级
        here = os.path.dirname(os.path.abspath(__file__))
        try:
            from compile.preprocessor.preprocessor import preprocessor

            program_path = preprocessor._stdlib_root()
        except Exception:
            program_path = os.path.normpath(os.path.join(here, '..'))
        if self.program_args is not None:
            args = self._build_list([self._build_string_from_py(a) for a in self.program_args])
            cell = self.address_space.allocate(args)
            cell.is_const = True
            cell.initialized = True
            self.global_scope.declare('args', cell)
        if repl_mode:
            # REPL 没有"用户程序目录"，path 填充为 none（而非字符串）
            cell = self.address_space.allocate(self._get_none())
            cell.is_const = True
            cell.initialized = True
            self.global_scope.declare('path', cell)
        else:
            self._declare_const_string('path', self._program_dir or os.getcwd())
        self._declare_const_string('program_path', program_path)

    # 以 string 常量形式声明全局引导库
    def _declare_const_string(self, name, text):
        obj = self._build_string_from_py(text)
        cell = self.address_space.allocate(obj)
        cell.is_const = True
        cell.initialized = True
        self.global_scope.declare(name, cell)

    # ==================================================================
    # python_api 桥接层
    # ------------------------------------------------------------------
    # 目标：把 核心/python_api/ 下的 .py 文件投影成 TanexScript 可访问的
    # python_api 标识符，并支持 Python 值与 TanexScript 值双向转换。
    # 约定：
    #   - 文件名（去 .py）与目录名即成员名，必须是合法 TanexScript 标识符，
    #     非法或大小写折叠冲突时立即报错中止。
    #   - 每个 .py 模块投影为 library 类型的容器，成员来自 __all__，
    #     未定义 __all__ 时取 dir() 的公开名 + obj.__dict__ 的公开键。
    #   - Python 可调用对象 → python_function；其余对象 → object 类型投影。
    #   - 投影对象持有 py_obj 引用，ts_to_py 时直接还原原 Python 对象。
    # ==================================================================

    # TanexScript 标识符规则与 tokenizer 完全一致：每个字符都必须是
    # isalpha() / '_' / 非 ASCII（ord > 127），数字一律不允许。
    def _py_valid_identifier(self, name):
        if not isinstance(name, str) or not name:
            return False
        for ch in name:
            if not (ch.isalpha() or ch == '_' or ord(ch) > 127):
                return False
        return name not in _py_reserved_names

    # 取一个 Python 对象应暴露的成员名（__all__ 优先，否则公开名 + __dict__）
    def _py_member_names(self, obj):
        all_names = getattr(obj, '__all__', None)
        if isinstance(all_names, (list, tuple)) and all(isinstance(n, str) for n in all_names):
            for n in all_names:
                if not self._py_valid_identifier(n):
                    raise runtime_error('python_api: __all__ 中的名字不是合法标识符: ' + n)
            return list(all_names)
        names = set()
        # dir() 已涵盖类属性、方法、继承成员；再跳过「模块 / frame / code /
        # generator」这类内部对象，否则展开 os/sys 或 gi_frame 会派生出
        # 成百上千个成员甚至无限递归。__all__ 分支不做过滤（尊重显式导出）。
        try:
            dir_names = dir(obj)
        except Exception:
            dir_names = []
        for n in dir_names:
            if not isinstance(n, str) or n.startswith('_'):
                continue
            try:
                if isinstance(getattr(obj, n), _py_internal_types):
                    continue
            except Exception:
                continue
            names.add(n)
        # 动态注入的实例属性（某些对象不出现在 dir() 中）
        try:
            d = getattr(obj, '__dict__', None)
        except Exception:
            d = None
        if isinstance(d, dict):
            names.update(
                k for k in d
                if isinstance(k, str) and not k.startswith('_')
                and not isinstance(d[k], _py_internal_types)
            )
        # __slots__ 类没有 __dict__，显式沿继承链收集槽名
        try:
            for cls in type(obj).__mro__:
                slots = cls.__dict__.get('__slots__')
                if slots is None:
                    continue
                if isinstance(slots, str):
                    slots = (slots,)
                try:
                    names.update(
                        s for s in slots
                        if isinstance(s, str) and not s.startswith('_')
                    )
                except TypeError:
                    continue
        except Exception:
            pass
        return sorted(n for n in names if self._py_valid_identifier(n))

    # 引导库里 `*** object = type_type{}` 定义的类型。
    # bootstrap.tscc 已与 bootstrap.tsuc 同步、包含该声明；这里保留兜底：
    # 若使用者换回旧版编译产物或自行裁剪引导库，仍按同样语义补建，
    # 保证投影挂在 object 类型上，而不是悄悄退化成 type_type。
    def _py_ensure_object_type(self):
        typ = self._resolve_global('object')
        if typ is not None:
            return typ
        typ = instance(self.type_type)
        typ.inherit = self.type_type
        cell = self.address_space.allocate(typ)
        cell.is_const = True
        cell.initialized = True
        self.global_scope.declare('object', cell)
        return typ

    # 建一个「透明句柄」实例：值传递时不被深拷贝，并持有原始 Python 对象
    def _py_make_object(self, obj, type_name = 'object'):
        if type_name == 'object':
            typ = self._py_ensure_object_type()
        else:
            typ = self._resolve_global(type_name)
        if typ is None:
            typ = self.type_type
        wrapper = instance(typ)
        wrapper._py_opaque = True
        wrapper.py_obj = obj
        return wrapper

    # python_api / 子包 / 模块容器统一用 library 类型（库语义 + 调用时不注入 receiver）
    def _py_make_container(self, obj = None):
        return self._py_make_object(obj, 'library')

    def _py_merge_module(self, container, mod, _seen = None):
        if mod is None:
            return container
        if _seen is None:
            _seen = {}
        for name in self._py_member_names(mod):
            try:
                attr = getattr(mod, name)
            except Exception:
                continue
            self._set_own_member(container, name, self._py_to_ts(attr, _seen))
        return container

    def _py_wrap_module(self, mod):
        key = id(mod)
        cached = self._py_obj_cache.get(key)
        if cached is not None and cached[0] is mod:
            return cached[1]
        wrapper = self._py_make_container(mod)
        self._py_obj_cache[key] = (mod, wrapper)
        self._py_merge_module(wrapper, mod, {key: wrapper})
        self._py_mark_live(wrapper, mod, 'named')
        return wrapper

    # ------------------------------------------------------------------
    # 投影「惰性实时读取」
    # ------------------------------------------------------------------
    # 静态快照的问题：投影生成之后，Python 侧再修改 list / dict / 对象属性 /
    # 模块成员时，TanexScript 侧看到的仍是旧值。这里改成「读时同步」：
    # 投影 wrapper 打 _py_live 标记，每次成员 / 方法 / 下标访问之前，
    # 才按 Python 侧当前状态按需刷新，而不是转换时一次性复制全部内容。
    #   named    : 对象 / 模块，逐成员 getattr 实时取值，支持新增 / 移除成员
    #   sequence : list / tuple / set，签名变化时才重建 TS 链表 head/tail/size
    #   mapping  : dict，签名变化时才重建 TS dictionary 的 buckets/size
    # 刷新只覆盖已有 cell 的 value，不替换 cell 对象，因此引用别名、
    # _py_writeback 标记都不会丢失。
    # ------------------------------------------------------------------

    def _py_same(self, a, b):
        if a is b:
            return True
        try:
            eq = (a == b)
            return isinstance(eq, bool) and eq
        except Exception:
            return False

    # 容器签名：标量按值、其它对象按 id。这样既能在 append / 替换 / 删除时
    # 触发重建，又能在「同一个嵌套对象原地改属性」时不必重建（嵌套对象
    # 自己也是 named 投影，其成员访问会各自实时同步）。
    def _py_scalar_signature(self, v):
        name = type(v).__name__
        if v is None or isinstance(v, (bool, int, float, str, bytes)):
            try:
                hash(v)
            except Exception:
                return (name, id(v))
            return (name, v)
        return (name, id(v))

    def _py_container_signature(self, raw, kind):
        try:
            if kind == 'sequence':
                return tuple(self._py_scalar_signature(v) for v in raw)
            return tuple(
                (self._py_scalar_signature(k), self._py_scalar_signature(v))
                for k, v in raw
            )
        except Exception:
            return None

    def _py_mark_live(self, wrapper, py_obj, kind):
        # 透明句柄：值传递不克隆，ts_to_py 直接还原原 Python 对象
        wrapper._py_opaque = True
        wrapper.py_obj = py_obj
        wrapper._py_live = kind
        wrapper._py_live_names = set()
        wrapper._py_live_values = {}
        wrapper._py_live_sig = None
        if kind in ('sequence', 'mapping'):
            # 首次登记时记下签名，避免第一次访问就做一次无意义的重建
            try:
                raw = tuple(py_obj) if kind == 'sequence' else tuple(py_obj.items())
                wrapper._py_live_sig = self._py_container_signature(raw, kind)
            except Exception:
                pass
            # 记录「上一次同步后 TS 侧的内容」，用于识别 TS 侧是否发生了写入
            wrapper._py_live_ts_snapshot = self._py_ts_container_values(wrapper, kind)
        return wrapper

    def _py_sync_live(self, obj):
        if not isinstance(obj, instance):
            return
        kind = getattr(obj, '_py_live', None)
        if kind is None:
            return
        key = id(obj)
        if key in self._py_sync_active or self._py_sync_suppressed.get(key, 0):
            return
        py_obj = getattr(obj, 'py_obj', None)
        if py_obj is None:
            return
        self._py_sync_active.add(key)
        try:
            if kind == 'named':
                self._py_sync_named(obj, py_obj)
            elif kind in ('sequence', 'mapping'):
                self._py_sync_container(obj, py_obj, kind)
        finally:
            self._py_sync_active.discard(key)

    # 只写 value，保留 cell 身份（引用别名 / 写回标记都挂在 cell 上）
    def _py_write_live_cell(self, obj, name, value):
        cell = obj.members.get(name)
        if cell is None:
            cell = self.address_space.allocate()
            obj.members[name] = cell
        try:
            self.address_space.write(cell, value)
        except Exception:
            cell.value = value
        return cell

    def _py_sync_named(self, obj, py_obj):
        try:
            names = self._py_member_names(py_obj)
        except Exception:
            return
        prev_values = getattr(obj, '_py_live_values', None)
        if prev_values is None:
            prev_values = {}
            obj._py_live_values = prev_values
        current = set()
        for name in names:
            try:
                attr = getattr(py_obj, name)
            except Exception:
                continue
            current.add(name)
            # 值未变化时不做转换、也不重写 cell，避免每次访问都产生新 wrapper；
            # 但成员本身若是容器投影，仍需单独同步（TS 侧可能刚写过它）
            if name in prev_values and self._py_same(prev_values[name], attr):
                projected = obj.members.get(name)
                if (projected is not None and isinstance(projected.value, instance)
                        and getattr(projected.value, '_py_live', None) is not None):
                    self._py_sync_live(projected.value)
                continue
            try:
                value = self._py_to_ts(attr)
            except Exception:
                continue
            self._py_write_live_cell(obj, name, value)
            prev_values[name] = attr
        prev_names = getattr(obj, '_py_live_names', None) or set()
        for name in prev_names - current:
            if obj.members.get(name) is not None:
                self._py_write_live_cell(obj, name, self._get_none())
            prev_values.pop(name, None)
        obj._py_live_names = current

    # 读取 TanexScript 侧容器当前内容，转换成 Python 值，用于判断 TS 侧是否改写过。
    # 注意必须直接读 members，不能走 _find_member_cell，否则会重入同步。
    def _py_ts_container_values(self, obj, kind):
        try:
            if kind == 'sequence':
                return [self._ts_to_py(v) for v in self._list_to_py(obj)]
            return self._ts_dict_to_py(obj)
        except Exception:
            return None

    # TanexScript 侧写过容器时，把内容写回原 Python 容器（list / dict 原地更新）。
    # tuple / set 等不可变容器保持只读语义：TS 侧的改动不会污染原对象。
    def _py_absorb_container(self, py_obj, ts_values, kind):
        try:
            if kind == 'sequence':
                if isinstance(py_obj, list):
                    py_obj[:] = ts_values
            elif isinstance(py_obj, dict):
                py_obj.clear()
                py_obj.update(ts_values)
        except Exception:
            pass

    def _py_sync_container(self, obj, py_obj, kind):
        # 双向同步：先判断 TS 侧是否发生过写入（append / index_set / delete_end …）。
        # 若 TS 侧内容与上次同步后的快照不同，说明是 TS 侧改的，把它推回 Python；
        # 否则按 Python 侧当前状态刷新 TS。两侧同时改时以 TS 侧写入为准。
        ts_now = self._py_ts_container_values(obj, kind)
        snapshot = getattr(obj, '_py_live_ts_snapshot', _py_missing)
        ts_changed = (
            ts_now is not None and snapshot is not _py_missing
            and not self._py_same(ts_now, snapshot)
        )
        if ts_changed:
            self._py_absorb_container(py_obj, ts_now, kind)
        try:
            raw = tuple(py_obj) if kind == 'sequence' else tuple(py_obj.items())
        except Exception:
            return
        sig = self._py_container_signature(raw, kind)
        if (not ts_changed and sig is not None
                and getattr(obj, '_py_live_sig', None) == sig):
            return
        if kind == 'sequence':
            values = []
            for v in raw:
                try:
                    values.append(self._py_to_ts(v))
                except Exception:
                    return
            fresh = self._build_list(values)
            member_names = ('head', 'tail', 'size')
        else:
            fresh = self._make_dictionary_from_py({})
            for k, v in raw:
                key_text = k if isinstance(k, str) else str(k)
                try:
                    self._dictionary_set_key(
                        fresh, key_text, self._py_to_ts(v)
                    )
                except Exception:
                    return
            member_names = ('buckets', 'bucket_count', 'size')
        for name in member_names:
            fc = fresh.members.get(name)
            if fc is None:
                continue
            self._py_write_live_cell(obj, name, fc.value)
        obj._py_live_sig = sig
        obj._py_live_ts_snapshot = self._py_ts_container_values(obj, kind)

    # 兼容旧的刷新入口：_py_to_ts 命中缓存时，改为触发一次读时同步
    def _py_refresh_object(self, wrapper, obj, _seen):
        self._py_sync_live(wrapper)

    # 为 python_api 对象投影的成员赋值登记「写回原始 Python 对象」信息。
    # 只挂在赋值目标 cell 上：解释器内部刷新成员不走赋值路径，不会误触发写回。
    def _py_tag_writeback(self, obj, name, cell):
        # 只认「透明句柄 + 持有原 Python 对象」，不依赖类型对象身份比较
        #（bootstrap 里的类型副本曾导致按身份判断失效）。
        if isinstance(obj, instance) and getattr(obj, '_py_opaque', False):
            # 容器投影（list / dict）的结构成员 head / tail / size / buckets
            # 由引导库方法内部维护，不能当作 Python 对象属性写回；
            # 容器内容的双向同步由 _py_sync_container 统一处理。
            if getattr(obj, '_py_live', None) in ('sequence', 'mapping'):
                return cell
            py_obj = getattr(obj, 'py_obj', None)
            if py_obj is not None:
                cell._py_writeback = (py_obj, name)
        return cell

    # 写回 Python 对象。TS 侧 cell 在调用本方法前已经写入新值，
    # 因此失败时必须把 cell 与 Python 属性一起回滚，否则会出现
    # 「TS 显示新值、Python 仍是旧值」的撕裂状态。
    # old_value 用 _py_missing 区分「调用方没提供旧值」与「旧值就是 None」。
    def _py_apply_writeback(self, cell, value, old_value = _py_missing):
        wb = getattr(cell, '_py_writeback', None)
        if wb is None:
            return
        py_obj, name = wb
        had_old = old_value is not _py_missing
        # 记录 Python 侧旧值：property setter 可能在抛错前已经改了内部状态
        had_py = False
        py_old = None
        try:
            py_old = getattr(py_obj, name)
            had_py = True
        except Exception:
            pass
        try:
            py_value = self._ts_to_py(value)
            setattr(py_obj, name, py_value)
        except Exception as e:
            # 1) 回滚 TanexScript 侧 cell
            if had_old:
                try:
                    self.address_space.write(cell, old_value)
                except Exception:
                    cell.value = old_value
            # 2) 回滚 Python 侧属性（尽力而为，恢复失败不再二次抛错）
            try:
                if had_py:
                    setattr(py_obj, name, py_old)
                else:
                    try:
                        delattr(py_obj, name)
                    except Exception:
                        pass
            except Exception:
                pass
            raise runtime_error(
                'python_api: 无法写入成员 ' + name + ': ' + str(e) + '（已回滚）'
            )
        # 3) 成功但 setter 归一化 / 转换了值时（property / __setattr__），
        #    以 Python 侧读回值为准更新 TS cell，避免两侧语义分叉。
        try:
            read_back = getattr(py_obj, name)
        except Exception:
            return
        if not self._py_same(read_back, py_value):
            try:
                normalized = self._py_to_ts(read_back)
                self.address_space.write(cell, normalized)
            except Exception:
                cell.value = normalized

    # Python 值 → TanexScript 值
    def _py_to_ts(self, obj, _seen = None):
        if _seen is None:
            _seen = {}
            # 顶层调用开启一次新的投影预算；递归调用都带着 _seen，
            # 因此计数覆盖整棵对象图，超限时降级为不透明占位而非无限展开。
            self._py_projection_count = 0
        # 已经是 TanexScript 侧的值，原样返回
        if isinstance(obj, (python_function, type_object, code_value, builtin_function)):
            return obj
        if isinstance(obj, instance):
            # 已是 TanexScript 值（含 _py_opaque 透明句柄），原样返回
            return obj
        # 基础类型（值语义，不入缓存）
        if obj is None:
            return self._get_none()
        if isinstance(obj, bool):
            return self._boolean(obj)
        if isinstance(obj, int):
            return obj
        if isinstance(obj, float):
            return self._make_number_from_float(obj)
        if isinstance(obj, str):
            return self._build_string_from_py(obj)
        # 容器 / 对象：先查缓存防环、保身份
        key = id(obj)
        if key in _seen:
            return _seen[key]
        cached = self._py_obj_cache.get(key)
        if cached is not None and cached[0] is obj:
            wrapper = cached[1]
            _seen[key] = wrapper
            # 同一 Python 对象再次出现（例如方法返回 self）时触发读时同步，
            # 使 Python 侧的状态变更对 TanexScript 可见，同时保持 wrapper 身份不变。
            if isinstance(wrapper, instance) and getattr(wrapper, '_py_opaque', False):
                self._py_refresh_object(wrapper, obj, _seen)
            return wrapper
        # 预算兜底：对象图异常庞大时不再展开成员，只给一个透明句柄
        self._py_projection_count += 1
        if self._py_projection_count > _py_max_projection_nodes:
            wrapper = self._py_make_object(obj)
            self._py_obj_cache[key] = (obj, wrapper)
            _seen[key] = wrapper
            return wrapper
        # 迭代器 / 生成器：TanexScript 没有迭代器概念，直接投影会展开
        # gi_frame / gi_code 内部对象图（卡死）。一次性物化为 TS list，
        # 结果缓存到原对象，避免同一生成器被消耗两次。无限生成器按上限截断。
        if isinstance(obj, Iterator):
            items = []
            try:
                for item in obj:
                    if len(items) >= _py_max_iter_items:
                        break
                    items.append(item)
            except Exception:
                pass
            wrapper = self._py_to_ts(items, _seen)
            self._py_obj_cache[key] = (obj, wrapper)
            _seen[key] = wrapper
            return wrapper
        if isinstance(obj, (list, tuple, set, frozenset, bytes, bytearray)):
            wrapper = self._build_list([])
            self._py_obj_cache[key] = (obj, wrapper)
            _seen[key] = wrapper
            for item in obj:
                self._call_member(wrapper, 'append', [self._py_to_ts(item, _seen)])
            self._py_mark_live(wrapper, obj, 'sequence')
            return wrapper
        if isinstance(obj, dict):
            wrapper = self._make_dictionary_from_py({})
            self._py_obj_cache[key] = (obj, wrapper)
            _seen[key] = wrapper
            for k, v in obj.items():
                key_text = k if isinstance(k, str) else str(k)
                self._dictionary_set_key(wrapper, key_text, self._py_to_ts(v, _seen))
            self._py_mark_live(wrapper, obj, 'mapping')
            return wrapper
        if isinstance(obj, types.ModuleType):
            return self._py_wrap_module(obj)
        # 可调用（函数 / bound method / 类）→ python_function
        if callable(obj):
            wrapper = python_function(obj)
            self._py_obj_cache[key] = (obj, wrapper)
            _seen[key] = wrapper
            return wrapper
        # 其余 Python 对象 → 引导库 object 类型投影
        wrapper = self._py_make_object(obj)
        self._py_obj_cache[key] = (obj, wrapper)
        _seen[key] = wrapper
        for name in self._py_member_names(obj):
            try:
                attr = getattr(obj, name)
            except Exception:
                continue
            self._set_own_member(wrapper, name, self._py_to_ts(attr, _seen))
        self._py_mark_live(wrapper, obj, 'named')
        return wrapper

    # TanexScript 值 → Python 值（作为 python_function 的实参 / 返回值还原）
    def _ts_to_py(self, value):
        if isinstance(value, python_function):
            return value.py_callable
        if getattr(value, '_py_opaque', False):
            return value.py_obj
        if value is None or isinstance(value, (bool, int, float, str)):
            return value
        if isinstance(value, instance):
            if self._is_current('string', value.type):
                return self._string_to_py(value)
            if self._is_current('boolean', value.type):
                c = value.members.get('value')
                return bool(c.value) if c is not None else None
            if self._is_current('number', value.type):
                return self._number_to_py(value)
            if self._is_current('none_type', value.type):
                return None
            if self._is_current('list', value.type):
                return [self._ts_to_py(e) for e in self._list_to_py(value)]
            if self._is_current('dictionary', value.type):
                return self._ts_dict_to_py(value)
            # 原生 TanexScript 对象：尽力投影为 dict
            result = {}
            for name, c in value.members.items():
                if name.startswith('_') or c is None:
                    continue
                try:
                    result[name] = self._ts_to_py(c.value)
                except Exception:
                    continue
            return result
        return value

    # dictionary 实例 → Python dict（与 _dict_to_py 结构一致，但递归用 _ts_to_py）
    def _ts_dict_to_py(self, obj):
        result = {}
        buckets_cell = obj.members.get('buckets')
        if buckets_cell is None:
            return result
        for bucket in self._list_to_py(buckets_cell.value):
            if not isinstance(bucket, instance):
                continue
            for pair in self._list_to_py(bucket):
                items = self._list_to_py(pair)
                if len(items) < 2:
                    continue
                k = self._ts_to_py(items[0])
                try:
                    hash(k)
                except TypeError:
                    k = str(k)
                result[k] = self._ts_to_py(items[1])
        return result

    # 按 python_api 包路径导入模块（core 目录需在 sys.path 中）
    def _py_import_module(self, dotted):
        full = 'python_api' + ('.' + dotted if dotted else '')
        try:
            return importlib.import_module(full)
        except Exception as e:
            raise runtime_error('python_api: 导入模块失败 ' + full + ': ' + str(e))

    # 递归扫描 python_api 目录，组装成员；非法标识符立即报错中止
    def _py_fill_package(self, container, dir_path, rel):
        entries = sorted(os.listdir(dir_path))

        def entry_name(entry):
            full = os.path.join(dir_path, entry)
            if os.path.isdir(full):
                if entry.startswith('__'):
                    return None
                return entry
            if entry.endswith('.py') and entry != '__init__.py':
                return entry[:-3]
            return None

        named = [(e, entry_name(e)) for e in entries]
        named = [(e, n) for e, n in named if n is not None]
        # 大小写折叠冲突（Windows 大小写不敏感）
        seen_lower = {}
        for _, name in named:
            low = name.lower()
            if low in seen_lower:
                raise runtime_error(
                    'python_api: 成员名大小写冲突: ' + seen_lower[low] + ' 与 ' + name
                )
            seen_lower[low] = name
            if not self._py_valid_identifier(name):
                raise runtime_error(
                    'python_api: 文件名不是合法标识符: ' + name +
                    '（不能含数字、-、.、空格等）'
                )
        # 只登记名字，不在这里 import：某个模块自身导入失败不会拖垮整个启动，
        # 错误会延迟到首次访问该成员时才抛（可被 TanexScript try/catch 捕获）。
        # 文件名合法性校验仍在启动阶段完成，非法名依旧立即中止。
        for entry, name in named:
            full = os.path.join(dir_path, entry)
            if os.path.isdir(full):
                sub = self._py_make_container()
                self._py_fill_package(sub, full, rel + name + '.')
                self._set_own_member(container, name, sub)
            else:
                self._set_own_member(container, name, python_lazy_module(rel + name))
        # 包自身 __init__.py 的公开内容同样延迟到首次访问时合并
        if os.path.isfile(os.path.join(dir_path, '__init__.py')):
            container._py_lazy_init = rel.rstrip('.')

    # 运行用户程序前填充全局 python_api 标识符（在 load_bootstrap 之后调用）
    def inject_python_api(self):
        here = os.path.dirname(os.path.abspath(__file__))
        core_dir = os.path.normpath(os.path.join(here, '..'))
        api_dir = os.path.join(core_dir, 'python_api')
        # 保证引导库源里声明的 object 类型在运行时可用
        #（旧版 bootstrap.tscc 未含该声明时补建，不与已有定义冲突）
        self._py_ensure_object_type()
        root = self._py_make_container()
        if os.path.isdir(api_dir):
            if core_dir not in sys.path:
                sys.path.insert(0, core_dir)
            self._py_fill_package(root, api_dir, '')
        cell = self.address_space.allocate(root)
        cell.is_const = True
        cell.initialized = True
        self.global_scope.declare('python_api', cell)

    # 引导库加载
    def load_bootstrap(self):
        here = os.path.dirname(os.path.abspath(__file__))
        candidates = [
            os.path.join(here, 'bootstrap.tscc'),
            os.path.join(here, '..', 'run', 'bootstrap.tscc')
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
        self._run_in_file(data['Tanex Script'], self._resolve_source_path(path))
        self._bootstrap_names = set(self.global_scope.names.keys())
        public_cell = self.global_scope.find('public')
        if public_cell is not None and public_cell.value is not None:
            entries = self._list_to_py(public_cell.value)
            self._public_names = set(
                (''.join((chr(c) for c in self._list_to_py(item))) for item in entries)
            )
            self._public_names.add('public')
        self._public_names.add('import')
        self._public_names.add('library')
        for name in ('io',):
            cell = self.global_scope.find(name)
            if cell is not None:
                setattr(self, f'_{name}_type', cell.value)
        # python_api 在引导库类型（object / library / list / dictionary ...）就绪后注入，
        # 与 args / path / program_path 一样属于运行前全局标识符填充。
        self.inject_python_api()

    # 运行用户文件
    def run_file(self, path):
        if path.endswith('.tscl'):
            self._outside_bootstrap = False
            for _, content in self._iter_tscl_blocks(path):
                data = self._parse_json_or_raise(content, path)
                self.annotations.update(data.get('annotations', {}))
                self._run_in_file(data['Tanex Script'], path)
            self._outside_bootstrap = True
            return None, False
        data = self._load_json_file(path)
        return self._run_compiled_data(data, self._resolve_source_path(path))

    # 运行内存中的编译产物（不落地文件），供 -t/--temp 内联代码使用
    def run_compiled(self, compiled, source_path):
        data = self._parse_json_or_raise(compiled, source_path)
        return self._run_compiled_data(data, source_path)

    def _run_compiled_data(self, data, source_path):
        self._outside_bootstrap = False
        self._outside_bootstrap = True
        self.annotations.update(data.get('annotations', {}))
        return self._run_in_file(data['Tanex Script'], source_path)

    # 解析 .tscl 库文件，逐块产出（路径, JSON 内容）
    def _iter_tscl_blocks(self, tscl_path):
        data = self._load_json_file(tscl_path)
        for name, content in data.items():
            yield name, content

    # 以库命名空间方式加载模块（隔离的 library 实例，成员为模块顶层声明）。
    # 多子文件库(.tscl)按块路径分组建作用域：
    #   /main.tscc            -> 库根（模块作用域）
    #   /json.tscc            -> 库根下的文件作用域
    #   /encoding/ascii.tscc  -> 库根下 encoding 子库里的文件作用域
    # 因此支持 `库.子库.成员` 访问，库内文件也能经上级作用域（~name）引用库根符号。
    def _load_library_module(self, path):
        abs_path = os.path.abspath(path)
        if abs_path in self._loaded_libs:
            return self._loaded_libs[abs_path]
        lib_type = self._resolve_global('library')
        if lib_type is None:
            raise runtime_error('library 类型未就绪')
        if abs_path.endswith('.tscl'):
            blocks = [(name, self._parse_json_or_raise(content, abs_path)) for name, content in self._iter_tscl_blocks(abs_path)]
        else:
            blocks = [(None, self._load_json_file(abs_path))]
        saved_outside = self._outside_bootstrap
        module_scope = scope(parent = self.global_scope)
        module_scope.is_module = True
        self._outside_bootstrap = True
        lib_ann_table: dict[str, str] = {}
        saved_file = self._current_file
        self._current_file = None

        # public 是文件级特殊变量：各子文件在自己的文件作用域里声明各自的 public，
        # 这里逐块捕获 public 白名单与顶层声明，待全部执行完后再合并出库的公开面。
        block_entries: list = []
        directory_scopes: dict[tuple, scope] = {(): module_scope}
        try:
            for block_name, data in blocks:
                parts = self._block_path_parts(block_name, abs_path)
                lib_ann_table.update(data.get('annotations', {}))
                if data.get('annotation'):
                    lib_ann_table[''] = data['annotation']
                block_file = data.get('source_file') or abs_path
                self._current_file = block_file
                is_main = block_name is None or parts == ['main']
                if is_main:
                    block_scope = module_scope
                else:
                    block_scope = scope(
                        parent = self._directory_scope(
                            parts[:-1],
                            module_scope,
                            directory_scopes
                        )
                    )
                names_before = set(block_scope.names.keys())
                public_before = block_scope.names.get('public')
                for stmt in data['Tanex Script']:
                    try:
                        self.eval_node(stmt, block_scope)
                    except runtime_error as e:
                        e.annotate(self._current_file, self._current_pos)
                        raise
                public_after = block_scope.names.get('public')
                declared = set(block_scope.names.keys()) - names_before
                declared.discard('public')
                if public_after is not None and public_after is not public_before:
                    names = self._public_names_of_cell(public_after)
                else:
                    names = None
                block_entries.append(
                    {
                        'parts': parts,
                        'scope': block_scope,
                        'declared': declared,
                        'public': names,
                        'is_main': is_main
                    }
                )
        finally:
            self._current_file = saved_file
        self._outside_bootstrap = saved_outside
        self._lib_annotation_tables[abs_path] = lib_ann_table
        lib = instance(lib_type)

        # 库根成员：主文件在模块作用域里的全部声明
        for name, cell in module_scope.names.items():
            lib.members[name] = cell

        # 合并各块 public（按出现顺序去重）；同时把非主文件的顶层声明提升到库根，
        # 保持旧行为下 `库.成员` 能直接访问到任一子文件的符号。
        merged_public: list[str] = []
        seen_public: set[str] = set()
        declared_any = False
        visible: set[str] = set()
        sub_libraries: dict[tuple, instance] = {}
        for entry in block_entries:
            names = entry['public']
            if names is None:
                # 未声明 public 的子文件：其顶层名默认可被外部引用
                visible |= entry['declared']
            else:
                declared_any = True
                visible |= set(names)
                for n in names:
                    if n not in seen_public:
                        seen_public.add(n)
                        merged_public.append(n)
            if entry['is_main']:
                continue

            # 非主文件：按路径包装成子库（目录）与文件库（叶子），并把其顶层声明提升到库根
            file_lib = self._make_block_library(
                lib_type,
                entry['scope'],
                entry['public']
            )
            parent_lib = self._sub_library(
                entry['parts'][:-1],
                lib,
                lib_type,
                sub_libraries
            )
            parent_lib.members[entry['parts'][-1]] = self.address_space.allocate(file_lib)
            for n in entry['declared']:
                cell = entry['scope'].names.get(n)
                if cell is not None:
                    lib.members[n] = cell

            # 子库/文件句柄名同样需要通过库的公开性检查，
            # 以便按 `库.子库.成员` 逐级访问
            visible.add(entry['parts'][0])
        if merged_public:
            merged_value = self._build_list(
                [self._build_string_from_py(n) for n in merged_public]
            )

            # public 通常是 `*** public = [...]` 声明的常量单元，不能被写入，
            # 因此这里直接换上一个新单元承载合并结果
            pub_cell = self.address_space.allocate(merged_value)
            module_scope.declare('public', pub_cell)
            lib.members['public'] = pub_cell
        visible.add('public')

        # 库实例挂公开名单：None 表示该库没有声明 public，不做可见性过滤
        lib.public_names = visible if declared_any else None
        self._loaded_libs[abs_path] = lib
        return lib

    # 把 .tscl 内部的键（如 /encoding/ascii.tscc）解析为路径片段列表；
    # 非库文件（单个 .tscc/.tsuc）没有键，返回 [文件名]
    def _block_path_parts(self, block_name, abs_path):
        if block_name is None:
            return [os.path.splitext(os.path.basename(abs_path))[0]]
        name = str(block_name).replace('\\', '/').strip('/')
        for suffix in ('.tscc', '.tsuc'):
            if name.endswith(suffix):
                name = name[:-len(suffix)]
                break
        parts = [p for p in name.split('/') if p]
        if not parts:
            parts = [os.path.splitext(os.path.basename(abs_path))[0]]
        return parts

    # 取（必要时新建）某个目录对应的子作用域，parent 链最终指向库根作用域
    def _directory_scope(self, parts, root_scope, cache):
        key = tuple(parts)
        if key in cache:
            return cache[key]
        parent = self._directory_scope(parts[:-1], root_scope, cache) if len(parts) > 1 else root_scope
        s = scope(parent = parent)
        cache[key] = s
        return s

    # 把某个子文件的文件作用域包装成叶子 library 实例（成员为其顶层声明）
    def _make_block_library(self, lib_type, block_scope, public_names):
        file_lib = instance(lib_type)
        for name, cell in block_scope.names.items():
            file_lib.members[name] = cell
        if public_names is None:
            file_lib.public_names = None
        else:
            file_visible = set(public_names)
            file_visible.add('public')
            file_lib.public_names = file_visible
        return file_lib

    # 取（必要时新建）某级子库实例，parent 链最终指向库根实例
    def _sub_library(self, parts, root_lib, lib_type, cache):
        key = tuple(parts)
        if key in cache:
            return cache[key]
        if not parts:
            return root_lib
        parent = self._sub_library(parts[:-1], root_lib, lib_type, cache)
        sub = instance(lib_type)
        sub.public_names = None
        cache[key] = sub
        parent.members[parts[-1]] = self.address_space.allocate(sub)
        return sub

    # 解析 public 特殊变量的值（字符串链表）为 Python 名字列表；
    # 解析失败返回 None，此时按"未声明 public"处理（默认公开，避免误封）
    def _public_names_of_cell(self, cell):
        try:
            items = self._list_to_py(cell.value)
        except Exception:
            return None
        names = []
        for item in items:
            if isinstance(item, instance) and self._is_current('string', item.type):
                names.append(self._string_to_py(item))
            elif isinstance(item, int):
                names.append(chr(item))
            elif isinstance(item, str):
                names.append(item)
        return names

    def eval_import(self, node, env):
        # 动态引入：path 是表达式 AST 节点（单条或列表），运行时求值后加载
        path_node = node['import']['path']
        name = node['import'].get('name')
        by_ref = node['import'].get('by_ref')
        path_value = self.eval_node(path_node, env)

        # 列表批量引入：元素运行时求值为字符串路径；
        # 路径列表不能为空，命名时名称数量与路径数量须一致
        if isinstance(path_value, instance) and self._is_current('list', path_value.type):
            paths = self._list_to_py(path_value)
            if not paths:
                raise runtime_error('import 列表引入: 路径列表不能为空')
            if isinstance(name, list) and len(name) != len(paths):
                raise runtime_error(
                    f'import 列表引入: 名称数量 ({len(name)}) 与路径数量 ({len(paths)}) 不一致'
                )
            lib = None
            for idx, item in enumerate(paths):
                path_str = self._item_to_path(item)
                if path_str is None:
                    raise runtime_error('import 路径必须是字符串')
                item_name = name[idx] if isinstance(name, list) else None
                item_by_ref = by_ref[idx] if isinstance(by_ref, list) else None
                lib = self._import_single(
                    path_str,
                    item_name,
                    node,
                    env,
                    by_ref = item_by_ref
                )
            return lib
        path_str = self._item_to_path(path_value)
        if path_str is None:
            raise runtime_error('import 路径必须是字符串')
        return self._import_single(path_str, name, node, env, by_ref = by_ref)

    # 将值转换为 Python 路径字符串；非字符串返回 None
    def _item_to_path(self, item):
        if isinstance(item, instance) and self._is_current('string', item.type):
            return self._string_to_py(item)
        return None

    # 导入单条路径：运行时解析路径（支持动态表达式求值结果），
    # 按名称（默认取路径最后一段）绑定为 library 常量。
    # by_ref 语义标记：`import <path> = *name` 为传地址引用绑定写法，
    # 绑定结果均为引用库实例本身（共享同一对象，改动互相可见）
    def _import_single(self, path, name, node, env, by_ref = None):
        line, col = 0, 0
        pos = node['import'].get('pos')
        if pos:
            line, col = pos[0], pos[1]
        abs_path = self._resolve_import_target(path, line, col)
        module_name = name
        if module_name is None:
            module_name = self._default_import_name(path)
            if not (module_name and (module_name[0].isalpha() or module_name[0] == '_' or ord(module_name[0]) > 127)):
                raise runtime_error(
                    f'导入 "{path}" 的默认名称不能作为标识符，请使用 import <路径表达式> = *name; 显式命名'
                )
        if abs_path in self._loaded_libs:
            lib = self._loaded_libs[abs_path]
        else:
            lib = self._load_library_module(abs_path)
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

    # -> 引入文件所有内容：path 是表达式 AST 节点（单条或列表），
    # 运行时求值后加载目标文件，不打包为 library，
    # 而是把目标文件顶层声明全部展开到当前作用域；
    # 展开后若与当前作用域存在同名标识符，产生警告
    # （不静默覆盖、不报致命错误）
    def eval_include(self, node, env):
        path_node = node['include']['path']
        path_value = self.eval_node(path_node, env)

        # 列表批量引入：元素运行时求值为字符串路径，依次展开每个文件
        if isinstance(path_value, instance) and self._is_current('list', path_value.type):
            paths = self._list_to_py(path_value)
            if not paths:
                raise runtime_error('-> 引入列表: 路径列表不能为空')
            lib = None
            for item in paths:
                path_str = self._item_to_path(item)
                if path_str is None:
                    raise runtime_error('-> 引入路径必须是字符串')
                lib = self._include_single(path_str, node, env)
            return lib
        path_str = self._item_to_path(path_value)
        if path_str is None:
            raise runtime_error('-> 引入路径必须是字符串')
        return self._include_single(path_str, node, env)

    # 引入单条路径：运行时解析路径（支持动态表达式求值结果），
    # 不打包为 library，而是把目标文件的顶层声明（library 实例的
    # members）全部展开到当前作用域（env.declare 直接写入当前作用域）。
    # 展开前逐个检查同名标识符：与当前作用域已有绑定冲突时发出警告并覆盖
    # （不静默覆盖、不报致命错误）；同一 cell（如重复引入同一文件）幂等跳过
    def _include_single(self, path, node, env):
        line, col = 0, 0
        pos = node['include'].get('pos')
        if pos:
            line, col = pos[0], pos[1]
        abs_path = self._resolve_import_target(path, line, col)
        if abs_path in self._loaded_libs:
            lib = self._loaded_libs[abs_path]
        else:
            lib = self._load_library_module(abs_path)

        # 展开全部顶层声明；public 是文件级可见性白名单（特殊变量），
        # 不属于用户内容，不展开
        conflicts = []
        for name, cell in lib.members.items():
            if name == 'public':
                continue
            existing = env.find(name)
            if existing is not None and existing is not cell and (existing.value is not None):
                conflicts.append(name)
            env.declare(name, cell)
        if conflicts:
            warning(
                [
                    f'-> 引入 "{path}" 时，与当前作用域存在同名标识符: ' + '、'.join(sorted(conflicts)),
                    '已用引入的内容覆盖原有绑定，请注意命名冲突'
                ]
            )
        return lib

    # 从路径字符串推导默认标识符名：取最后一段去掉扩展名与结尾斜杠
    @staticmethod
    def _default_import_name(path):
        clean = path.rstrip('/\\')
        return os.path.splitext(os.path.basename(clean))[0]

    # 运行时解析导入路径：复用预编译器的候选搜索/歧义检查/库目录搜索，
    # 返回可加载的绝对路径（.tscc/.tscl/文件夹 main 等）；
    # .tsuc 源码在此兜底编译为 .tscc
    def _resolve_import_target(self, path, line, col):
        try:
            from compile.preprocessor.preprocessor import preprocessor

            pp = preprocessor([], self._current_file or '')
            abs_path, import_type = pp._resolve_import_path(
                path,
                line,
                col,
                self._current_file or '<runtime>'
            )
            tok = (path, line, col, self._current_file or '<runtime>')
            resolved = pp._resolve_to_runtime_file(abs_path, import_type, tok)
        except runtime_error:
            raise
        except Exception as e:
            msg = getattr(e, 'message', None)
            if isinstance(msg, list):
                msg = '；'.join((str(m) for m in msg))
            raise runtime_error(msg if isinstance(msg, str) else str(e))
        if resolved is None:
            raise runtime_error(
                f'文件夹 "{path}" 中没有主内容 (main.tsuc / main.tscc / main.tscl)'
            )
        return resolved

    def _builtin_import(self, interp, receiver, args):
        path_obj = receiver
        if not isinstance(path_obj, instance):
            raise runtime_error('import 参数必须是字符串')
        codes = self._list_to_py(path_obj)
        path = ''.join((chr(c) for c in codes))
        if not os.path.isabs(path):
            here = os.path.dirname(os.path.abspath(__file__))
            candidates = [
                os.path.join(here, path),
                os.path.join(here, '..', path)
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
            self._step_check(stmt, self.global_scope)
            try:
                result = self.eval_node(stmt, self.global_scope)
            except return_signal as rs:
                if rs.depth > 1:
                    raise runtime_error('$ 跳出深度超出调用层级: ' + str(rs.depth))
                return rs.value, True
        return result, False

    # 断点/单步检查：命中断点或单步模式下交给调试器交互
    def _step_check(self, stmt, env):
        if self._debugger is not None:
            self._debugger.maybe_break(stmt, env)

    # 基础工具
    def _resolve(self, name, env):
        cell = env.find(name)
        if cell is None:
            raise runtime_error('变量未定义: ' + name)
        if self._outside_bootstrap and env.parent is None and (name in self._bootstrap_names) and (name not in self._public_names):
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
        if cell is not None and cell.initialized and (cell.value is not None):
            return cell.value
        none_type = self._resolve_global('none_type')
        fallback = self._none_fallback
        if none_type is not None and fallback is not None and (fallback.type is not none_type):
            self._none_fallback = instance(none_type)
        return self._none_fallback

    def _boolean(self, py_bool):
        bool_type = self._resolve_global('boolean')
        obj = instance(bool_type) if bool_type is not None else instance(self._core_placeholders['boolean'])
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
            # python_api 实时投影：读之前按 Python 侧当前状态刷新一次。
            # _find_method / _get_member / eval_subscript 都经过这里，
            # 因此成员、方法、下标访问全部能读到最新值。
            self._py_sync_live(obj)
            # python_api 惰性加载（1）：包自身 __init__.py 的公开内容，
            # 在该包首次发生成员访问时才导入并合并进来。
            lazy_init = getattr(obj, '_py_lazy_init', None)
            if lazy_init is not None:
                obj._py_lazy_init = None
                try:
                    self._py_merge_module(
                        obj, self._py_import_module(lazy_init), {id(obj): obj}
                    )
                except Exception:
                    obj._py_lazy_init = lazy_init
                    raise
            own = obj.members.get(name)
            if own is not None:
                # python_api 惰性加载（2）：.py 模块首次被访问时才真正 import，
                # 解析结果写回同一个 cell，后续访问直接命中。
                if isinstance(own.value, python_lazy_module):
                    resolved = self._py_wrap_module(
                        self._py_import_module(own.value.dotted)
                    )
                    self.address_space.write(own, resolved)
                return own
        if isinstance(obj, instance):
            if self._is_current('function_type', obj.type):
                cell = self._ensure_function_member(obj, name)
                if cell is not None:
                    return cell

                # 未命中函数元信息（params/defaults/statements）时沿
                # function_type 类型链查找（支持在类型上追加 hash 等成员）
                return self._find_in_chain(obj.type, name)
            return self._find_in_chain(obj.type, name)
        if isinstance(obj, type_object):
            return self._find_in_chain(obj, name)
        if isinstance(obj, code_value):
            cell = self._find_code_member_cell(obj, name)
            if cell is not None:
                return cell

            # code 元信息仅含 params/defaults/statements；其余成员沿 code 类型链查找
            code_type = self._resolve_global('code')
            if code_type is not None:
                return self._find_in_chain(code_type, name)
            return None
        return None

    def _ensure_function_member(self, fn, name):
        code_cell = fn.members.get('code')
        if code_cell is None or not isinstance(code_cell.value, code_value):
            return None
        cv = code_cell.value
        if name == 'params':
            value = self._build_list(
                [self._build_string_from_py(p) for p in cv.params]
            )
        elif name == 'defaults':
            value = self._build_list(
                [self._boolean(d is not None) for d in cv.defaults]
            )
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
        value = self._call(
            index,
            [
                self.address_space.allocate(meta),
                self.address_space.allocate(self._build_string_from_py(name))
            ]
        )
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
            self._check_inherit_allowed(value)
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
        # python_api 的 Python 对象投影是「透明句柄」：值传递时不能克隆，
        # 否则会丢失其持有的原始 Python 对象引用（ts_to_py 无法还原）。
        if getattr(value, '_py_opaque', False):
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

        # 类型对象深拷贝后仍属于原声明文件（readonly/sealed/closed 的文件级判定依赖 source_file）
        new_obj.source_file = getattr(value, 'source_file', None)
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

    # 库实例的公开性检查：加载标准库时，各子文件的 public 白名单会被合并
    # 记到实例的 public_names 属性上（None 表示不做过滤）。
    # 未公开的符号不允许经 `库.成员` 语法访问。
    def _check_library_visible(self, obj, name):
        visible = getattr(obj, 'public_names', None)
        if visible is not None and name not in visible:
            raise runtime_error('未公开符号: ' + name)

    # readonly 声明查找：从对象的类型链向上找第一个声明了 readonly 的类型对象，
    # 返回 (owner, readonly 列表值) 或 None。类型对象自身写成员时从自身链查找。
    def _find_readonly_decl(self, obj):
        if not isinstance(obj, (instance, type_object)):
            return None

        # 语言层类型对象（instance 且 type 为 type_type）自身即承载 readonly 声明；
        # 数据实例则从它的类型链向上查找。
        if isinstance(obj, type_object) or self._is_type(obj):
            typ = obj
        else:
            typ = obj.type
        seen = set()
        while typ is not None and id(typ) not in seen:
            seen.add(id(typ))
            cell = typ.members.get('readonly')
            if cell is not None:
                return typ, cell.value
            nxt = self._get_inherit(typ)
            if nxt is typ or nxt is None:
                break
            typ = nxt
        return None

    # readonly 名单（list of string）是否包含指定成员名
    def _readonly_has(self, lst, name):
        if not isinstance(lst, instance):
            return False
        head_cell = lst.members.get('head')
        if head_cell is None:
            return False
        node = head_cell.value
        none = self._get_none()
        while node is not None and node is not none:
            val_cell = node.members.get('value')
            if val_cell is not None:
                item = val_cell.value
                if isinstance(item, instance) and self._is_current('string', item.type):
                    codes = self._list_to_py(item)
                    if ''.join((chr(c) for c in codes)) == name:
                        return True
            next_cell = node.members.get('next')
            node = next_cell.value if next_cell is not None else none
        return False

    # readonly 写/删检查：成员名在 readonly 名单、且当前文件不是声明文件时拒绝
    def _check_readonly_write(self, obj, name):
        found = self._find_readonly_decl(obj)
        if found is None:
            return
        owner, lst = found
        if not self._readonly_has(lst, name):
            return
        src = getattr(owner, 'source_file', None)
        if src is not None and src == self._current_file:
            return
        raise runtime_error('成员外部只读: ' + name)

    # sealed/closed 状态：沿类型链向上找第一个声明了 sealed/closed 的类型。
    # 子类型未自行声明时继承直接父的设置（子类定义则以子类为准）。
    # 返回 (sealed, closed, 声明源文件)
    def _seal_status(self, typ):
        cur = typ
        seen = set()
        while cur is not None and id(cur) not in seen:
            seen.add(id(cur))
            sc = cur.members.get('sealed')
            cc = cur.members.get('closed')
            if sc is not None or cc is not None:
                sealed = sc is not None and self.truthy(sc.value)
                closed = cc is not None and self.truthy(cc.value)
                return sealed, closed, getattr(cur, 'source_file', None)
            nxt = self._get_inherit(cur)
            if nxt is cur or nxt is None:
                break
            cur = nxt
        return False, False, None

    # 继承许可检查：parent 作为父类型被继承时调用。
    # sealed 全挡（任何来源不可继承）；closed 仅挡声明文件之外的来源。
    def _check_inherit_allowed(self, parent):
        if not isinstance(parent, (instance, type_object)):
            return
        sealed, closed, src = self._seal_status(parent)
        if sealed:
            raise runtime_error('类型不可被继承（sealed）')
        if closed and src is not None and (src != self._current_file):
            raise runtime_error('类型不可在外部被继承（closed）')

    def _get_member(self, obj, name):
        self._check_library_visible(obj, name)
        cell = self._find_member_cell(obj, name)
        if cell is None:
            raise runtime_error('成员不存在: ' + name)
        return cell.value

    # 调用与构造
    # 外层包装：当接收者是 python_api 的容器投影时，在整个方法执行期间暂停
    # 它的读时同步，避免引导库「先改链、再改 size」的中间态被误判成 TS 侧写入。
    # 用计数器支持嵌套调用（同一个容器的方法内部还可能再调用自身的方法）。
    def _call(self, callable_obj, cells, frame_label = None, deep_copy_params = True):
        receiver = cells[0].value if cells else None
        suppress = (
            isinstance(receiver, instance)
            and getattr(receiver, '_py_live', None) in ('sequence', 'mapping')
        )
        key = id(receiver) if suppress else None
        if suppress:
            self._py_sync_suppressed[key] = self._py_sync_suppressed.get(key, 0) + 1
        try:
            return self._call_impl(
                callable_obj, cells, frame_label, deep_copy_params
            )
        finally:
            if suppress:
                left = self._py_sync_suppressed.get(key, 0) - 1
                if left > 0:
                    self._py_sync_suppressed[key] = left
                else:
                    self._py_sync_suppressed.pop(key, None)

    def _call_impl(self, callable_obj, cells, frame_label = None, deep_copy_params = True):
        if isinstance(callable_obj, instance) and self._is_current('function_type', callable_obj.type):
            code_cell = callable_obj.members.get('code')
            if code_cell is None or not isinstance(code_cell.value, code_value):
                raise runtime_error('function 值缺少 code')
            return self.execute_function(
                code_cell.value,
                cells,
                frame_label = frame_label,
                deep_copy_params = deep_copy_params
            )
        if isinstance(callable_obj, code_value):
            result = self.execute_function(
                callable_obj,
                cells,
                frame_label = frame_label,
                deep_copy_params = deep_copy_params
            )
            return result
        if isinstance(callable_obj, builtin_function):
            receiver = cells[0].value if cells else None
            args = [c.value for c in cells[1:]]
            return callable_obj.fn(self, receiver, args)
        if isinstance(callable_obj, python_function):
            # Python 函数/方法不需要 TanexScript 的 receiver，cells 全部按位置实参处理。
            # bound method 经 getattr 取得时已自带 self，调用语义天然正确。
            py_args = [self._ts_to_py(c.value) for c in cells]
            try:
                result = callable_obj.py_callable(*py_args)
            except Exception as e:
                raise runtime_error(
                    'python_function 调用失败 (' + str(callable_obj.name) + '): ' +
                    type(e).__name__ + ': ' + str(e)
                )
            return self._py_to_ts(result)
        if self._is_type(callable_obj) or isinstance(callable_obj, type_object):
            return self.construct(callable_obj, [c.value for c in cells])

        # 可调用实例：若实例带有 apply 成员，则把调用转发给 apply（接收者为实例自身）。
        # 用于 poly_function 等按参数类型分派的可调用类型，使 func(args) 等价于 func.apply(func, args)。
        if isinstance(callable_obj, instance):
            apply_method = self._find_method(callable_obj, 'apply')
            if apply_method is not None:
                receiver = self.address_space.allocate(callable_obj)
                args_list = self._build_list([c.value for c in cells])
                args_cell = self.address_space.allocate(args_list)
                return self._call(apply_method, [receiver, args_cell])
        raise runtime_error('不可调用的值')

    def _call_member(self, obj, name, arg_values):
        self._check_library_visible(obj, name)
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

        # 类型对象（type_type{} 构造结果）打标声明所在源文件，
        # 供 readonly/closed 的文件级权限判断使用
        if typ is self.type_type:
            obj.source_file = self._current_file
        init = self._find_method(typ, 'initialize')
        if isinstance(init, builtin_function) and typ is not self.type_type:
            type_type = self.type_type
            if type_type is not None:
                cell = type_type.members.get('initialize')
                if cell is not None and init is cell.value:
                    init = None
        if init is not None:
            receiver_cell = self.address_space.allocate(obj)
            args = [self.address_space.allocate(v) for v in arg_values]

            # 构造初始化是内部流程：self 直绑新建对象（不深拷贝），
            # 否则 *self 值传递会把 initialize 的修改写到副本上，新对象不被初始化
            self._call(
                init,
                [receiver_cell] + args,
                deep_copy_params = False
            )
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

    # 参数类型位：把 [*name, 类型, 默认值] 的类型标注解析为类型对象列表
    def _declared_types(self, cv, index):
        types = getattr(cv, 'types', None)
        if not types or index >= len(types):
            return []
        ast = types[index]
        if ast is None:
            return []
        kind = next(iter(ast))
        if kind == 'name':
            names = [ast['name']['value']]
        elif kind == 'list':
            names = []
            for it in ast['list']['items']:
                if next(iter(it)) != 'name':
                    raise runtime_error('类型标注必须是类型名或类型名列表')
                names.append(it['name']['value'])
        else:
            raise runtime_error('类型标注必须是类型名或类型名列表')
        env = getattr(cv, 'env', None)
        resolved = []
        for name in names:
            cell = env.find(name) if env is not None else None
            if cell is None:
                raise runtime_error('类型未定义: ' + name)
            if cell.value is not self.type_type and (not self._is_type(cell.value)):
                raise runtime_error('类型标注必须是类型: ' + name)
            resolved.append(cell.value)
        return resolved

    def _type_name(self, typ):
        if isinstance(typ, type_object) and typ.name:
            return typ.name
        for name, cell in self.global_scope.names.items():
            if cell.value is typ:
                return name
        return '<未知类型>'

    # 调用时按声明类型校验显式传入的实参（缺省参数用默认值补齐，不校验）
    def _check_param_type(self, cv, index, value):
        allowed = self._declared_types(cv, index)
        if not allowed:
            return
        actual = self._type_of(value)
        actual_name = self._type_name(actual)
        for t in allowed:
            if actual is t:
                return

        # integer 与 number 互认（整数是数的子集），使 number 形参可接受整数实参
        for t in allowed:
            if self._type_name(t) in ('number', 'integer') and actual_name in ('number', 'integer'):
                return
        names = ' / '.join((self._type_name(t) for t in allowed))
        raise runtime_error(
            '参数类型不匹配: ' + cv.params[index] + ' 期望 ' + names + '，实际 ' + actual_name
        )

    # 形参传递模式：'*' 值传递（深拷贝实参）或 '**' 引用传递（直绑原 cell）
    def _param_mode(self, cv, index):
        modes = getattr(cv, 'param_modes', None)
        if modes and index < len(modes):
            return modes[index]
        return '*'

    def execute_function(self, cv, cells, frame_label = None, deep_copy_params = True):
        fscope = scope(cv.env)
        fscope.is_function = True
        for i, name in enumerate(cv.params):
            if i < len(cells):
                self._check_param_type(cv, i, cells[i].value)
                if deep_copy_params and self._param_mode(cv, i) != '**':
                    # * 值传递：深拷贝实参值到新 cell 再绑定，改副本不影响原对象
                    fscope.declare(
                        name,
                        self.address_space.allocate(
                            self._deep_copy(cells[i].value)
                        )
                    )
                else:
                    # ** 引用传递：直接绑定实参原 cell，修改直接作用原对象
                    # （构造初始化场景 deep_copy_params=False 时 *self 也直绑）
                    fscope.declare(name, cells[i])
            else:
                default = cv.defaults[i] if i < len(cv.defaults) else None
                if default is not None:
                    # 默认值表达式属于函数定义处，用定义文件的上下文求值
                    v = self._eval_in_file(
                        default,
                        fscope,
                        getattr(cv, 'file', None)
                    )
                    cell = self.address_space.allocate(v)
                    fscope.declare(name, cell)
                else:
                    raise runtime_error('缺少参数: ' + name)
        if len(cells) > len(cv.params):
            raise runtime_error(
                '参数过多: 期望 ' + str(len(cv.params)) + ' 个参数，实际传入 ' + str(len(cells)) + ' 个'
            )
        saved_file = self._current_file
        saved_pos = self._current_pos
        self._push_frame(frame_label or '<函数>')
        if getattr(cv, 'file', None):
            self._current_file = cv.file
        self._current_pos = None
        try:
            result = None
            for stmt in cv.statements:
                self._step_check(stmt, fscope)
                try:
                    result = self.eval_node(stmt, fscope)
                except return_signal as rs:
                    if rs.depth > 1:
                        rs.depth -= 1
                        raise
                    return rs.value
            return self._get_none()
        except runtime_error as e:
            self._attach_trace(e)
            e.annotate(self._current_file, self._current_pos)
            raise
        finally:
            self._pop_frame()
            self._current_file = saved_file
            self._current_pos = saved_pos

    def execute_code_value(self, cv, take_last = False):
        fscope = scope(cv.env)
        for i, name in enumerate(cv.params):
            cell = self.address_space.allocate(self._get_none())
            fscope.declare(name, cell)
        saved_file = self._current_file
        saved_pos = self._current_pos
        self._push_frame('<代码块>')
        if getattr(cv, 'file', None):
            self._current_file = cv.file
        self._current_pos = None
        try:
            result = None
            for stmt in cv.statements:
                self._step_check(stmt, fscope)
                try:
                    result = self.eval_node(stmt, fscope)
                except return_signal as rs:
                    if rs.depth > 1:
                        rs.depth -= 1
                        raise
                    return rs.value
            if take_last:
                return result
            return self._get_none()
        except runtime_error as e:
            self._attach_trace(e)
            e.annotate(self._current_file, self._current_pos)
            raise
        finally:
            self._pop_frame()
            self._current_file = saved_file
            self._current_pos = saved_pos

    def _eval_branch(self, ast, env):
        if next(iter(ast)) == 'code':
            cv = code_value(
                ast['code']['statements'],
                env,
                file = self._current_file
            )
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
                cv.params,
                cv.defaults,
                len(cv.statements)
            )
        return cv.meta

    def _build_code_meta(self, params, defaults, statement_count) -> 'instance | None':
        dict_type = self._resolve_global('dictionary')
        if dict_type is None:
            return None
        meta = self.construct(dict_type, [])
        if not isinstance(meta, instance):
            return None
        name_list = self._build_list(
            [self._build_string_from_py(p) for p in params]
        )
        self._dictionary_set_key(meta, 'params', name_list)
        has_defaults = self._build_list(
            [self._boolean(d is not None) for d in defaults]
        )
        self._dictionary_set_key(meta, 'defaults', has_defaults)
        self._dictionary_set_key(meta, 'statements', statement_count)
        return meta

    def _dictionary_set_key(self, d, key, value):
        index_set = self._find_method(d.type, 'index_set')
        if index_set is None:
            raise runtime_error('dictionary 未定义 index_set')
        self._call(
            index_set,
            [
                self.address_space.allocate(d),
                self.address_space.allocate(self._build_string_from_py(key)),
                self.address_space.allocate(value)
            ]
        )

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

        # 小数位位数按实际数字个数计算（下划线仅为数位分隔，不计入位数）
        back_digits = len(frac_part.replace('_', ''))
        if neg:
            front = -front
        number_type = self._resolve_global('number')
        obj = instance(number_type) if number_type is not None else instance(self._core_placeholders['number'])
        self._set_own_member(obj, 'front', front)
        self._set_own_member(obj, 'back', back)
        self._set_own_member(obj, 'back_digits', back_digits)
        return obj

    def _make_infinite_literal(self):
        inf_type = self._resolve_global('infinite_type')
        obj = instance(inf_type) if inf_type is not None else instance(self._core_placeholders['infinite_type'])
        self._set_own_member(obj, 'sign', 1)
        self._set_own_member(obj, 'infinity', True)
        return obj

    def _make_nan_literal(self):
        nan_type = self._resolve_global('nan_type')
        obj = instance(nan_type) if nan_type is not None else instance(self._core_placeholders['nan_type'])
        self._set_own_member(obj, 'nan_marker', True)
        return obj

    # 求值分发
    def eval_node(self, node, env):
        kind = next(iter(node))
        inner = node[kind]
        if isinstance(inner, dict) and isinstance(inner.get('pos'), list):
            self._current_pos = inner.get('pos')
        if kind == 'integer':
            return int(node['integer']['value'])
        if kind == 'number':
            return self._make_number_literal(node['number']['value'])
        if kind == 'string':
            # Tanex 字符串允许跨行（tokenizer 按源码原文收集）；
            # Python eval 不接受未转义的真实换行，先统一转义为 \n 再求值。
            raw = node['string']['value']
            text = eval(
                raw.replace('\r\n', '\\n').replace(
                    '\r',
                    '\\n'
                ).replace(
                    '\n',
                    '\\n'
                )
            )
            return self._build_string_from_py(text)
        if kind == 'nan_type':
            return self._make_nan_literal()
        if kind == 'infinite_type':
            return self._make_infinite_literal()
        if kind == 'name':
            return self._resolve(node['name']['value'], env).value
        if kind == 'code':
            return code_value(
                node['code']['statements'],
                env,
                file = self._current_file
            )
        if kind == 'list':
            return self._eval_list(node, env)
        if kind == 'dictionary_literal':
            return self._eval_dictionary_literal(node, env)
        if kind == 'break':
            raise break_signal()
        if kind == 'contiune':
            raise contiune_signal()
        if kind == 'unary':
            return self.eval_unary(node, env)
        if kind == 'binary':
            return self.eval_binary(node, env)
        if kind == 'brackets':
            # 括号表达式：直接透传求值内部表达式，不引入任何新语义，
            # 运行行为与裸表达式完全一致。
            return self.eval_node(node['brackets']['expr'], env)
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
        if kind == 'include':
            return self.eval_include(node, env)
        raise runtime_error('未知的节点类型: ' + kind)

    def _eval_list(self, node, env):
        lst = self._build_list([])
        for item in node['list']['items']:
            self._call_member(lst, 'append', [self.eval_node(item, env)])
        return lst

    # 裸花括号 {k: v, k2: v2} 字典字面量：求值为 [k, v] 成对列表，
    # 复用 dictionary 的构造/init 机制（与 dictionary{[[k, v], ...]} 等价）
    def _eval_dictionary_literal(self, node, env):
        pairs = self._build_list([])
        for kv in node['dictionary_literal']['items']:
            k = self.eval_node(kv[0], env)
            v = self.eval_node(kv[1], env)
            pair = self._build_list([k, v])
            self._call_member(pairs, 'append', [pair])
        dict_type = self._resolve_global('dictionary')
        if dict_type is None:
            raise runtime_error('dictionary 类型未就绪')
        return self.construct(dict_type, [pairs])

    # 一元运算符
    def _is_builtin_value(self, value):
        if not isinstance(value, instance):
            return True
        return self._is_current('number', value.type) or self._is_current('boolean', value.type) or self._is_current('string', value.type) or self._is_current('list', value.type) or self._is_current('address', value.type) or self._is_current('error', value.type) or self._is_current('warning', value.type) or self._is_current('infinite_type', value.type) or self._is_current('nan_type', value.type) or self._is_current('library', value.type)

    # 解地址：求值操作数得到地址整数，返回被指向的 cell（无名空间地址亦可）
    def _deref_cell(self, operand, env):
        addr = self.eval_node(operand, env)
        if isinstance(addr, instance):
            # 地址包装实例：优先取 value 成员（须为地址整数）
            vc = addr.members.get('value')
            if vc is not None and isinstance(vc.value, int) and self.address_space.exists(vc.value):
                addr = vc.value
        if not isinstance(addr, int):
            raise runtime_error('解地址目标不是地址')
        cell = self.address_space.get(addr)
        if cell is None:
            raise runtime_error('无效的地址')
        return cell

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
                return -value
            if isinstance(value, instance):
                method = self._find_method(value, 'negative')
                if method is not None:
                    return self._call(method, [self.address_space.allocate(value)])
                return self._unary_minus(value)
            raise runtime_error('不支持一元负号')
        if op == '*':
            if next(iter(operand)) in ('integer', 'number'):
                return self._declare_many(operand, env, False)
            if next(iter(operand)) != 'name':
                raise runtime_error('声明符的操作数必须是名字')
            cell = self._resolve_or_declare(operand['name']['value'], env)
            if cell.is_ref and cell.initialized:
                # 引用变量：b 即绑定目标空间，取地址返回目标空间地址
                return cell.value
            return cell.address
        if op == '/':
            # 解地址：操作数可为任意表达式，值为地址整数（无名空间地址亦可）
            cell = self._deref_cell(operand, env)
            return cell.value
        if op == '**':
            if next(iter(operand)) in ('integer', 'number'):
                return self._declare_many(operand, env, False)
            if next(iter(operand)) == 'name':
                # 引用变量声明：不要求预先存在，新变量绑定到独立空间并标记引用属性
                name = operand['name']['value']
                cell = self._resolve_or_declare(name, env)
                if not cell.is_ref:
                    cell.is_ref = True
                    if cell.initialized:
                        cell.value = None
                return cell.address
            if next(iter(operand)) == 'member':
                # 引用表达式支持成员目标：返回成员 cell 的地址（引用语义，不深拷贝）
                obj = self.eval_node(operand['member']['left'], env)
                name = operand['member']['right']['name']['value']
                if not isinstance(obj, (instance, type_object)):
                    raise runtime_error('无法读取成员: ' + name)
                cell = obj.members.get(name)
                if cell is None:
                    raise runtime_error('成员不存在: ' + name)
                return cell.address
            raise runtime_error('引用声明的操作数必须是名字或成员')
        if op == '***':
            if next(iter(operand)) in ('integer', 'number'):
                return self._declare_many(operand, env, True)
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
        if op == '&' or op == '&&' or op == '&&&':
            # 连续（数量）声明：& N 普通连续空间 / && N 引用连续空间 / &&& N 常量连续空间
            if next(iter(operand)) not in ('integer', 'number'):
                raise runtime_error('连续声明操作数必须是整数')
            return self._declare_many(operand, env, op == '&&&')
        if op == 'type_of':
            return self._type_of(self.eval_node(operand, env))
        if op == 'delete':
            return self._delete_target(operand, env)
        raise runtime_error('不支持的一元运算符: ' + op)

    # 数量声明：*N / **N / ***N 声明 N 个连续空间，返回 [start, end]（首末地址）
    def _declare_many(self, operand, env, is_const):
        if next(iter(operand)) == 'integer':
            n = int(operand['integer']['value'])
        else:
            value = self.eval_node(operand, env)
            if not isinstance(value, instance) or not self._is_current('number', value.type):
                raise runtime_error('声明符的数量必须是整数')
            num = self._number_to_py(value)
            if num != int(num):
                raise runtime_error(operand['number']['value'] + ' 不是整数')
            n = int(num)
        if n < 1:
            raise runtime_error('声明空间的数量必须 >= 1')
        cells = [self.address_space.allocate() for _ in range(n)]
        if is_const:
            for c in cells:
                c.is_const = True
                c.initialized = True
        return self._build_list(
            [
                cells[0].address,
                cells[-1].address
            ]
        )

    def _unary_minus(self, value):
        if isinstance(value, int):
            return -value
        if isinstance(value, instance):
            if self._is_current('number', value.type):
                front_cell = value.members.get('front')
                back_cell = value.members.get('back')
                bd_cell = value.members.get('back_digits')
                number_type = self._resolve_global('number')
                obj = instance(number_type) if number_type is not None else instance(self._core_placeholders['number'])
                front = -front_cell.value if front_cell is not None else 0
                self._set_own_member(obj, 'front', front)
                self._set_own_member(obj, 'back', back_cell.value if back_cell else 0)
                self._set_own_member(obj, 'back_digits', bd_cell.value if bd_cell else 0)
                return obj
            if self._is_current('infinite_type', value.type):
                sign_cell = value.members.get('sign')
                sign = sign_cell.value if sign_cell else 1
                inf_type = self._resolve_global('infinite_type')
                obj = instance(inf_type) if inf_type is not None else instance(self._core_placeholders['infinite_type'])
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

        # 处理括号表达式：(expr) 与 expr 具有相同的赋值目标属性
        if kind == 'brackets':
            return self._assign_target(left['brackets']['expr'], env)
        if kind == 'name':
            return self._resolve_or_declare(left['name']['value'], env)
        if kind == 'unary':
            op = left['unary']['operator']
            operand = left['unary']['operand']
            if op == '*':
                if next(iter(operand)) != 'name':
                    raise runtime_error('声明符的操作数必须是名字')
                return self._resolve_or_declare(operand['name']['value'], env)
            if op == '**':
                if next(iter(operand)) == 'name':
                    # 引用变量声明：不要求预先存在，标记引用属性
                    cell = self._resolve_or_declare(operand['name']['value'], env)
                    cell.is_ref = True
                    return cell
                if next(iter(operand)) == 'member':
                    # 引用别名支持成员目标：`**obj.x = v` 对成员做引用写入（不深拷贝）
                    obj = self.eval_node(operand['member']['left'], env)
                    name = operand['member']['right']['name']['value']
                    if not isinstance(obj, (instance, type_object)):
                        raise runtime_error('无法设置成员: ' + name)
                    self._check_readonly_write(obj, name)
                    cell = obj.members.get(name)
                    if cell is None:
                        self._check_addable(obj)
                        cell = self.address_space.allocate()
                        obj.members[name] = cell
                    return cell
                raise runtime_error('引用声明的操作数必须是名字或成员')
            if op == '***':
                if next(iter(operand)) == 'name':
                    cell = self._resolve_or_declare(operand['name']['value'], env)
                    cell.is_const = True
                    return cell
                if next(iter(operand)) == 'member':
                    obj = self.eval_node(operand['member']['left'], env)
                    name = operand['member']['right']['name']['value']
                    if not isinstance(obj, (instance, type_object)):
                        raise runtime_error('无法设置成员: ' + name)
                    self._check_readonly_write(obj, name)
                    cell = obj.members.get(name)
                    if cell is None:
                        self._check_addable(obj)
                        cell = self.address_space.allocate()
                        obj.members[name] = cell
                    cell.is_const = True
                    return cell
                raise runtime_error('常量声明的操作数必须是名字或成员')
            if op == '/':
                # 解地址赋值：操作数可为任意表达式，值为地址整数（无名空间地址亦可）
                return self._deref_cell(operand, env)
            raise runtime_error('无效的赋值目标')
        if kind == 'member':
            obj = self.eval_node(left['member']['left'], env)
            name = left['member']['right']['name']['value']
            if not isinstance(obj, (instance, type_object)):
                raise runtime_error('无法设置成员: ' + name)
            # 赋值目标解析前同步：保证写回打在最新的 cell 上，
            # 且 Python 侧刚发生的变更不会被过期的 TS 值覆盖。
            self._py_sync_live(obj)
            self._check_readonly_write(obj, name)
            cell = obj.members.get(name)
            if cell is None:
                self._check_addable(obj)
                cell = self.address_space.allocate()
                obj.members[name] = cell
            return self._py_tag_writeback(obj, name, cell)
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

        # 列表解构赋值语法已取消：左侧为列表字面量一律视为无效赋值目标
        if next(iter(target)) == 'list':
            raise runtime_error('无效的赋值目标')

        # 引用变量绑定：`**name = RHS` 声明引用变量（不要求预先存在）。
        # RHS 为一元解地址表达式时绑定到被解出的空间；否则新建空间保存 RHS 值。
        if next(iter(target)) == 'unary' and target['unary']['operator'] == '**' and (next(iter(target['unary']['operand'])) == 'name'):
            name = target['unary']['operand']['name']['value']
            cell = self._resolve_or_declare(name, env)
            cell.is_ref = True
            if next(iter(right)) == 'unary' and right['unary']['operator'] == '/':
                target_cell = self._deref_cell(right['unary']['operand'], env)
                if target_cell is None:
                    raise runtime_error('无效的地址')
            else:
                v = self.eval_node(right, env)
                target_cell = self.address_space.allocate(v)
            cell.value = target_cell.address
            cell.initialized = True
            return cell.value

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
            if next(iter(right)) == 'name' and (not self._is_ref_decl_target(target)):
                v = self._deep_copy(v)

            # 常量首次绑定时标记其指向对象的成员树；仅在非函数作用域生效，
            # 避免 bootstrap/用户函数内部 `*** node = ...` 等局部常量声明
            # 把共享对象（如 list 元素节点）误标为常量。
            if cell.is_const and (not cell.initialized) and (not self._in_function_scope(env)):
                self._mark_tree_const(v)
            # 写回可能失败，先留旧值供回滚
            old_value = cell.value
            self.address_space.write(cell, v)
            self._py_apply_writeback(cell, v, old_value)
            return v
        cell = self._assign_target(target, env)
        old = cell.value
        r = self.eval_node(right, env)
        inner = op[:-1]
        v = self._binary_apply(inner, old, r)
        self.address_space.write(cell, v)
        self._py_apply_writeback(cell, v, old)
        return v

    # 下标统一写入：index 返回可写地址则写，未命中时走 index_set 插入
    def _subscript_store(self, obj, idx, value):
        if not isinstance(obj, instance):
            raise runtime_error('类型不支持下标写入')
        index_method = self._find_method(obj, 'index')
        if index_method is None:
            raise runtime_error('类型不支持下标写入')
        result = self._call(
            index_method,
            [
                self.address_space.allocate(obj),
                self.address_space.allocate(idx)
            ]
        )
        cell = self._addr_to_cell(result)
        if cell is not None:
            self.address_space.write(cell, value)
            return
        set_method = self._find_method(obj, 'index_set')
        if set_method is None:
            raise runtime_error('下标结果不提供可写地址')
        self._call(
            set_method,
            [
                self.address_space.allocate(obj),
                self.address_space.allocate(idx),
                self.address_space.allocate(value)
            ]
        )

    # 判断赋值目标是否为引用声明目标（** 或 & **）：右操作数为标识符时不深拷贝
    def _is_ref_decl_target(self, target):
        if next(iter(target)) != 'unary':
            return False
        op = target['unary']['operator']
        if op == '**':
            return True
        return False

    # 把 index 返回值转换为可写 cell：int 视为地址，instance 取其 value 成员 cell
    def _addr_to_cell(self, result):
        if isinstance(result, int):
            cell = self.address_space.get(result)
            if cell is None:
                raise runtime_error('无效的地址')
            return cell
        if isinstance(result, instance):
            value_cell = result.members.get('value')
            if value_cell is not None:
                return value_cell
        return None

    # delete 目标定位：name / member / subscript，返回目标 cell
    # name      —— 沿作用域链解析，仅解绑自身标识符并物理移除 cell
    # member    —— 从对象 own members 中取出并移除该成员 cell
    # subscript —— 调用对象 index 获取目标 cell（list 返回元素值所在 cell）
    def _delete_target(self, target, env):
        kind = next(iter(target))
        if kind == 'name':
            name = target['name']['value']
            cell = env.find(name)
            if cell is None:
                raise runtime_error('变量未定义: ' + name)

            # 引用变量：**x 只解绑 x 标识符 + 删自己 cell，目标 y 及其空间不动
            if cell.is_ref:
                env.unbind(name)
                self.address_space.deallocate(cell.address)
                return self._get_none()

            # 普通/常量变量：有 renounce 先调"删全"，再清空 own members、解绑并移除 cell
            if not self._maybe_renounce(cell.value):
                self._clear_own_members(cell.value)
            env.unbind(name)
            self.address_space.deallocate(cell.address)
            return self._get_none()
        if kind == 'member':
            obj = self.eval_node(target['member']['left'], env)
            name = target['member']['right']['name']['value']
            if not isinstance(obj, (instance, type_object)):
                raise runtime_error('无法删除成员: ' + name)
            self._check_readonly_write(obj, name)
            cell = obj.members.get(name)
            if cell is None:
                raise runtime_error('成员不存在: ' + name)
            if cell.is_ref:
                del obj.members[name]
                self.address_space.deallocate(cell.address)
                return self._get_none()
            if not self._maybe_renounce(cell.value):
                self._clear_own_members(cell.value)
            del obj.members[name]
            self.address_space.deallocate(cell.address)
            return self._get_none()
        if kind == 'subscript':
            obj = self.eval_node(target['subscript']['left'], env)
            idx = self.eval_node(target['subscript']['right'], env)
            if not isinstance(obj, instance):
                raise runtime_error('类型不支持下标删除')
            index_method = self._find_method(obj, 'index')
            if index_method is None:
                raise runtime_error('类型不支持下标删除')
            result = self._call(
                index_method,
                [
                    self.address_space.allocate(obj),
                    self.address_space.allocate(idx)
                ]
            )
            cell = self._addr_to_cell(result)
            if cell is None:
                raise runtime_error('下标结果不提供可删除地址')
            if cell.is_ref:
                self.address_space.deallocate(cell.address)
                return self._get_none()
            if not self._maybe_renounce(cell.value):
                self._clear_own_members(cell.value)
            self.address_space.deallocate(cell.address)
            return self._get_none()
        raise runtime_error('delete 目标不受支持: ' + kind)

    # 清空值对象 own members（只删本体：标识符 + cell + 值对象自身成员表）
    def _clear_own_members(self, value):
        if isinstance(value, (instance, type_object)):
            value.members.clear()
        elif isinstance(value, code_value):
            value.params = []
            value.defaults = []
            value.statements = []

    # 若值对象类型链上有 renounce 成员则调用它做"删全"，返回是否已调用
    def _maybe_renounce(self, value):
        renounce = self._find_method(value, 'renounce')
        if renounce is None:
            return False
        self._call(renounce, [self.address_space.allocate(value)])
        return True

    # 二元运算符
    def eval_binary(self, node, env):
        op = node['binary']['operator']
        if op == '=>':
            return self._eval_arrow(node, env)
        if op == '$':
            left = self.eval_node(node['binary']['left'], env)
            right = self.eval_node(node['binary']['right'], env)
            return self._eval_multiple_return(left, right)
        if op == '|>':
            return self._eval_pipe(node, env)
        if op == '$$':
            return self._eval_loop(node, env)
        if op == '<<':
            return self._eval_output(node, env)
        if op == '>>':
            return self._eval_input(node, env)
        if op == 'in':
            return self._eval_in(node, env)
        if op == '===':
            return self._eval_network(node, env)
        if op in ('&&', '||'):
            return self._eval_logic(node, env)
        left = self.eval_node(node['binary']['left'], env)
        right = self.eval_node(node['binary']['right'], env)
        return self._binary_apply(op, left, right)

    # $ 二元跳出：n $ value，n 层返回，n 必须为正整数（bool 不是合法层数）
    def _eval_multiple_return(self, depth_value, value):
        if not isinstance(depth_value, int) or isinstance(depth_value, bool):
            raise runtime_error('$ 二元跳出的左操作数必须是整数层数')
        if depth_value < 1:
            raise runtime_error('$ 二元跳出层数必须 >= 1')
        raise return_signal(value, depth = depth_value)

    # 管道 |>：a |> f 等价于 f(a)，首参注入。右侧必须是函数引用（name/member），
    # 不允许带参调用形式（如 a |> f(1)），带参会按设计直接报错。
    def _eval_pipe(self, node, env):
        right_ast = node['binary']['right']
        kind = next(iter(right_ast))
        if kind not in ('name', 'member'):
            raise runtime_error(
                '管道 |> 右侧必须是函数引用（标识符或成员），' + '不支持带参调用形式，请改用 f(a, ...) 直接调用'
            )
        call_ast = {
            'function': {
                'name': right_ast,
                'arg': [node['binary']['left']],
                'pos': node['binary'].get('pos')
            }
        }
        return self.eval_function(call_ast, env)

    def _binary_apply(self, op, left, right):
        if op in _arith_slot:
            return self._arith(op, left, right)
        if op in _cmp_slot:
            return self._compare(op, left, right)
        raise runtime_error('不支持的运算符: ' + op)

    def _arith(self, op, left, right):
        if isinstance(left, int) and isinstance(right, int):
            return self._int_arith(op, left, right)

        # 字符串插值胶水：string + 非 string 时先把右操作数按 string
        # 特殊成员转成字符串（拍板设计 "{a}" 等价 "hello " + a.string），
        # 再复用 string.addition 拼接
        if op == '+' and isinstance(left, instance) and self._is_current('string', left.type) and (not (isinstance(right, instance) and self._is_current('string', right.type))):
            if isinstance(right, int):
                right = self._build_string_from_py(str(right))
            else:
                codes = self._list_to_py(self._get_string_value(right))
                right = self._build_string_from_py(
                    ''.join((chr(c) for c in codes))
                )
        method = self._find_method(left, _arith_slot[op])
        if method is not None:
            receiver = self.address_space.allocate(left)
            arg = self.address_space.allocate(right)
            return self._call(method, [receiver, arg])

        # 反向兜底：左操作数无对应方法时，尝试右操作数的 other_<method>
        # 例如 a + b：先试 a.addition(b)，失败则试 b.other_addition(a)
        other_method_name = _other_arith_slot.get(op)
        if other_method_name:
            other_method = self._find_method(right, other_method_name)
            if other_method is not None:
                receiver = self.address_space.allocate(right)
                arg = self.address_space.allocate(left)
                return self._call(other_method, [receiver, arg])
        raise runtime_error('类型不支持运算: ' + op)

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
        if self._is_type(left) or self._is_type(right) or isinstance(left, type_object) or isinstance(right, type_object):
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

        # 反向兜底：左操作数无对应比较方法时，尝试右操作数的 other_<method>
        other_method_name = _other_cmp_slot.get(op)
        if other_method_name:
            other_method = self._find_method(right, other_method_name)
            if other_method is not None:
                receiver = self.address_space.allocate(right)
                arg = self.address_space.allocate(left)
                result = self._call(other_method, [receiver, arg])
                return result
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
        params, defaults, types, modes = self._extract_params(
            node['binary']['left'],
            env
        )
        right_ast = node['binary']['right']
        if next(iter(right_ast)) != 'code':
            raise runtime_error('=> 右侧必须是代码块 { ... }')
        cv = code_value(
            right_ast['code']['statements'],
            env,
            params = params,
            defaults = defaults,
            types = types,
            param_modes = modes,
            file = self._current_file
        )
        fn_type = self._resolve_global('function_type')
        if fn_type is None:
            raise runtime_error('function_type 类型未就绪')
        fn = instance(fn_type)
        self._set_own_member(fn, 'code', cv)
        return fn

    def _extract_params(self, left, env):
        # 参数声明支持两种写法：
        #   *name / **name                 按地址传参 / 引用传参的参数
        #   [*name, 类型, 默认值]          带类型约束和默认值的参数（类型可为类型名列表）
        #   [**name, 类型, 默认值]         引用传参 + 类型约束 + 默认值
        # 裸名不是 *name 的语法糖：它是一条普通变量表达式，未声明时按运行时
        # 错误（变量未定义）报出，不再是合法参数声明。
        # 传递模式：'*' 值传递（调用时深拷贝实参到新 cell，改副本不影响原对象）、
        # '**' 引用传递（调用时直接绑定实参原 cell，修改直接作用原对象）。
        params = []
        defaults = []
        types = []
        modes = []
        for item in left['list']['items']:
            kind = next(iter(item))
            if kind == 'unary':
                operator = item['unary']['operator']
                if operator not in ('*', '**'):
                    raise runtime_error('声明符必须是 * 或 ** 引用声明')
                operand = item['unary']['operand']
                if next(iter(operand)) != 'name':
                    raise runtime_error('声明符的操作数必须是名字')
                params.append(operand['name']['value'])
                defaults.append(None)
                types.append(None)
                modes.append(operator)
                continue
            if kind == 'list':
                items = item['list']['items']
                if not items:
                    raise runtime_error('无效的参数声明: []')
                first = items[0]
                if next(iter(first)) != 'unary' or next(iter(first['unary']['operand'])) != 'name':
                    # 裸名/其它表达式：求值使其按普通表达式报错（变量未定义等）
                    self.eval_node(first, env)
                    raise runtime_error('参数声明应为 *name 或 [*name, 类型, 默认值]')
                operator = first['unary']['operator']
                if operator not in ('*', '**'):
                    raise runtime_error('声明符必须是 * 或 ** 引用声明')
                params.append(first['unary']['operand']['name']['value'])
                modes.append(operator)
                if len(items) >= 2:
                    types.append(items[1])
                else:
                    types.append(None)
                if len(items) >= 3:
                    defaults.append(items[2])
                else:
                    defaults.append(None)
                continue

            # 裸名参数：不再作为 *name 的语法糖
            self.eval_node(item, env)
            raise runtime_error('参数声明应为 *name 或 [*name, 类型, 默认值]')
        return params, defaults, types, modes

    # $$ 循环
    def _eval_loop(self, node, env):
        results = []
        while True:
            try:
                cond_value = self.eval_node(node['binary']['left'], env)
                cond_result = self._eval_condition_value(cond_value)
            except return_signal as rs:
                # 循环条件块中的 return 是条件返回值，不作为函数返回；
                # 多层跳出在此穿透，由外层函数/代码块承接
                if rs.depth > 1:
                    rs.depth -= 1
                    raise
                cond_result = rs.value
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
            except contiune_signal:
                continue
        return self._build_list(results)

    def _eval_condition_value(self, value):
        if isinstance(value, instance):
            init = self._find_method(value, 'initialize')
            if init is not None:
                return self._call(init, [self.address_space.allocate(value)])
            return self._boolean(False)
        if isinstance(value, code_value):
            return self.execute_code_value(value)
        return value

    # 输出 <<（左操作数为 output 对象；兼容旧函数式）
    def _eval_output(self, node, env):
        right = self.eval_node(node['binary']['right'], env)
        char_list = self._get_string_value(right)
        left = self.eval_node(node['binary']['left'], env)
        if self._is_io_object(left):
            stream = self._read_member_string(left, 'target')
            handler = self._read_member_value(left, 'handler')
            mode = self._read_member_string(left, 'mode') or 'w'
            list_cell = self.address_space.allocate(char_list)
            if self._is_none_value(handler):
                processed = char_list
            else:
                processed = self._call(handler, [list_cell])
            codes = self._list_to_py(processed)
            text = ''.join((chr(c) for c in codes))
            if stream == 'console':
                sys.stdout.write(text)
            else:
                cell = left.members.get('_handle')
                handle = cell.value if cell is not None else None
                if handle is None:
                    try:
                        handle = open(stream, mode, encoding = 'utf-8')
                    except OSError as e:
                        raise runtime_error('无法打开输出文件: ' + stream + '（' + str(e) + '）')
                    left.members['_handle'] = self.address_space.allocate(handle)
                handle.write(text)
                handle.flush()
            return self._get_none()
        handler = left
        list_cell = self.address_space.allocate(char_list)
        processed = self._call(handler, [list_cell])
        codes = self._list_to_py(processed)
        sys.stdout.write(''.join((chr(c) for c in codes)))
        return self._get_none()

    # 输入 >>（左操作数为 input 对象；兼容旧函数式）
    def _eval_input(self, node, env):
        left = self.eval_node(node['binary']['left'], env)
        target = self._assign_target(node['binary']['right'], env)
        if self._is_io_object(left):
            stream = self._read_member_string(left, 'target')
            handler = self._read_member_value(left, 'handler')
            if stream == 'console':
                line = sys.stdin.readline()
                if line.endswith('\n'):
                    line = line[:-1]
                if line.endswith('\r'):
                    line = line[:-1]
                text = self._build_string_from_py(line)
            else:
                try:
                    with open(stream, 'r', encoding = 'utf-8') as f:
                        content = f.read()
                except OSError as e:
                    raise runtime_error('无法读取输入文件: ' + stream + '（' + str(e) + '）')
                text = self._build_string_from_py(content)
            char_list = self._get_string_value(text)
            list_cell = self.address_space.allocate(char_list)
            if self._is_none_value(handler):
                processed = char_list
            else:
                processed = self._call(handler, [list_cell])
            codes = self._list_to_py(processed)
            result_text = self._build_string_from_py(''.join((chr(c) for c in codes)))
            self.address_space.write(target, result_text)
            return result_text
        line = sys.stdin.readline()
        if line.endswith('\n'):
            line = line[:-1]
        if line.endswith('\r'):
            line = line[:-1]
        text = self._build_string_from_py(line)
        handler = left
        text_cell = self.address_space.allocate(text)
        processed = self._call(handler, [text_cell])
        self.address_space.write(target, processed)
        return processed

    # 判断值是否为 io 类型的实例
    def _is_io_object(self, obj):
        typ = self._io_type
        if typ is None or not isinstance(obj, instance):
            return False
        return obj.type is typ

    # 读取实例成员值（cell.value）
    def _read_member_value(self, obj, name):
        cell = self._find_member_cell(obj, name)
        if cell is None:
            raise runtime_error('成员不存在: ' + name)
        return cell.value

    # 读取实例字符串成员值（如 stream / mode），返回 Python 字符串
    def _read_member_string(self, obj, name):
        value = self._read_member_value(obj, name)
        if value is None:
            return None
        char_list = self._get_string_value(value)
        codes = self._list_to_py(char_list)
        return ''.join((chr(c) for c in codes))

    # 判断值是否为 none
    def _is_none_value(self, value):
        if not isinstance(value, instance):
            return False
        none_type = self._resolve_global('none_type')
        return none_type is not None and value.type is none_type

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
            # 类型对象（type_type 实例）与函数不是普通数据实例：
            # 它们没有面向实例数据的 string/hash 特殊成员语义，
            # 若沿用实例特殊成员查找会崩（dictionary.hash 读 bucket_count）、
            # 错显（list.string 返回 self 被 dump 成 []）或显示成 hash 值（函数 hash 恒 0）。
            if isinstance(obj, type_object) or self._is_type(obj):
                return self._display_type_object(obj)
            if isinstance(obj, instance) and self._is_current('function_type', obj.type):
                return '<function>'
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
                            (self._display_string_indented(e, pad, seen) for e in elements)
                        ) + ']'
                    finally:
                        seen.discard(oid)
                codes = self._list_to_py(char_list)
                return ''.join((chr(c) for c in codes))
            except Exception:
                hash_method = self._find_method(obj, 'hash')
                if hash_method is not None:
                    result = self._call(
                        hash_method,
                        [self.address_space.allocate(obj)]
                    )
                    if isinstance(result, int):
                        return str(result)
                    return self._display_string_indented(result, pad, seen)
                return self._dump_object(obj, pad, seen)
        if isinstance(obj, code_value):
            return '<code>'
        if isinstance(obj, builtin_function):
            return '<builtin ' + obj.name + '>'
        if isinstance(obj, python_function):
            return '<python_function ' + obj.name + '>'
        return repr(obj)

    # 类型对象（type_type 实例 / Python type_object）的专用显示：
    # 只给 `<type 名称: 地址>`，不展开其上挂载的成员（实例级 string/hash 等
    # 特殊方法属于该类型的实例语义，不应作用于类型对象本身）。
    def _display_type_object(self, obj):
        label = self._type_label(obj)
        addr = self._find_cell_address(obj)
        if addr == '<addr>':
            return '<%s>' % label
        return '<%s: %s>' % (label, addr)

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
            visible = getattr(obj, 'public_names', None)
            for name, cell in obj.members.items():
                if cell is None or name in _dump_skip:
                    continue
                if visible is not None and name not in visible:
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

    # === 网络运算符：把右侧值序列化为 JSON，发送给左侧地址的网关服务，并返回响应
    # 地址格式为 "主机:端口"（如 "127.0.0.1:12345"）；协议约定每条消息为一行 JSON（换行结尾）。
    # 网关不可达、请求失败、响应非法时抛出 runtime_error，可被 try 语句捕获。
    def _eval_network(self, node, env):
        left = self.eval_node(node['binary']['left'], env)
        right = self.eval_node(node['binary']['right'], env)
        if not isinstance(left, instance) or not self._is_current('string', left.type):
            raise runtime_error('=== 左侧必须是字符串地址')
        address = self._string_to_py(left)
        payload = self._value_to_py(right)
        host, sep, port_text = address.rpartition(':')
        if not sep or not port_text.isdigit():
            raise runtime_error('无效的网关地址: ' + address)
        port = int(port_text)
        if not host:
            host = '127.0.0.1'
        try:
            sock = socket.create_connection((host, port), timeout = 10)
        except OSError as e:
            raise runtime_error('无法连接网关: ' + str(e))
        try:
            sock.settimeout(10)
            data = json.dumps(payload, ensure_ascii = False)
            sock.sendall(data.encode('utf-8') + b'\n')
            buffer = b''
            while b'\n' not in buffer:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                buffer += chunk
            line = buffer.split(b'\n', 1)[0]
            if not line:
                raise runtime_error('网关无响应')
            response = json.loads(line.decode('utf-8'))
        except (OSError, ValueError) as e:
            raise runtime_error('网关请求失败: ' + str(e))
        finally:
            sock.close()
        return self._py_to_value(response)

    # 字符串实例 → Python 字符串
    def _string_to_py(self, obj):
        char_list = self._get_string_value(obj)
        codes = self._list_to_py(char_list)
        return ''.join((chr(c) for c in codes))

    # TSuc 值 → Python 对象（JSON 可序列化），支持整数、字符串、布尔、number、none、list、dictionary
    def _value_to_py(self, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            return value
        if isinstance(value, instance):
            if self._is_current('string', value.type):
                return self._string_to_py(value)
            if self._is_current('boolean', value.type):
                cell = value.members.get('value')
                return bool(cell.value) if cell is not None else None
            if self._is_current('number', value.type):
                return self._number_to_py(value)
            if self._is_current('none_type', value.type):
                return None
            if self._is_current('list', value.type):
                return [self._value_to_py(e) for e in self._list_to_py(value)]
            if self._is_current('dictionary', value.type):
                return self._dict_to_py(value)
        raise runtime_error('=== 右侧包含无法序列化为 JSON 的值')

    # number 实例 → Python float
    def _number_to_py(self, obj):
        front_cell = obj.members.get('front')
        back_cell = obj.members.get('back')
        digits_cell = obj.members.get('back_digits')
        if front_cell is None or back_cell is None or digits_cell is None:
            raise runtime_error('number 实例结构不完整')
        front = front_cell.value
        back = back_cell.value
        digits = digits_cell.value
        sign = -1 if front < 0 else 1
        value = abs(front) + (back / 10 ** digits if digits else 0)
        return value * sign

    # dictionary 实例 → Python dict（遍历哈希桶，桶内每个元素为 [key, value] 列表）
    def _dict_to_py(self, obj):
        result = {}
        buckets_cell = obj.members.get('buckets')
        if buckets_cell is None:
            return result
        buckets = self._list_to_py(buckets_cell.value)
        for bucket in buckets:
            if not isinstance(bucket, instance):
                continue
            for pair in self._list_to_py(bucket):
                items = self._list_to_py(pair)
                if len(items) < 2:
                    continue
                key = self._value_to_py(items[0])
                result[key] = self._value_to_py(items[1])
        return result

    # Python 对象（JSON 解析结果）→ TSuc 值
    def _py_to_value(self, obj):
        if obj is None:
            return self._get_none()
        if isinstance(obj, bool):
            return self._boolean(obj)
        if isinstance(obj, int):
            return obj
        if isinstance(obj, float):
            return self._make_number_from_float(obj)
        if isinstance(obj, str):
            return self._build_string_from_py(obj)
        if isinstance(obj, list):
            return self._build_list([self._py_to_value(e) for e in obj])
        if isinstance(obj, dict):
            return self._make_dictionary_from_py(obj)
        raise runtime_error('网关返回了无法转换的值: ' + type(obj).__name__)

    # Python float → number 实例（front/back/back_digits 结构，与 number 字面量一致）
    def _make_number_from_float(self, value):
        if value != value or value in (float('inf'), float('-inf')):
            raise runtime_error('网关返回了非有限数值')

        from decimal import Decimal

        text = format(Decimal(repr(value)), 'f')
        neg = text.startswith('-')
        if neg:
            text = text[1:]
        if '.' in text:
            int_part, frac_part = text.split('.', 1)
        else:
            int_part, frac_part = text, ''
        front = int(int_part) if int_part else 0
        back = int(frac_part) if frac_part else 0
        back_digits = len(frac_part)
        if neg:
            front = -front
        number_type = self._resolve_global('number')
        obj = instance(number_type) if number_type is not None else instance(self._core_placeholders['number'])
        self._set_own_member(obj, 'front', front)
        self._set_own_member(obj, 'back', back)
        self._set_own_member(obj, 'back_digits', back_digits)
        return obj

    # Python dict → dictionary 实例（键经 _dictionary_set_key 转为 TSuc 字符串）
    def _make_dictionary_from_py(self, obj):
        dict_type = self._resolve_global('dictionary')
        if dict_type is None:
            raise runtime_error('dictionary 类型未就绪')
        d = self.construct(dict_type, [])
        for key, value in obj.items():
            self._dictionary_set_key(d, key, self._py_to_value(value))
        return d

    # in 运算符
    def _eval_in(self, node, env):
        left = self.eval_node(node['binary']['left'], env)
        right = self.eval_node(node['binary']['right'], env)
        if not isinstance(right, instance):
            raise runtime_error('in 的右侧必须是实例')

        # 特殊成员 include：类型链上定义 include 时以其调用结果作为 in 判定
        include_method = self._find_method(right, 'include')
        if include_method is not None:
            result = self._call(
                include_method,
                [
                    self.address_space.allocate(right),
                    self.address_space.allocate(left)
                ]
            )
            return self._boolean(self.truthy(result))
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
            if size is not None and isinstance(size, int) and (i >= size):
                return self._boolean(False)
            try:
                element = self._call(
                    index_method,
                    [
                        self.address_space.allocate(right),
                        self.address_space.allocate(i)
                    ]
                )
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
                warning(['error 类型构造失败，已回退为字符串'])
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
            if isinstance(result, instance):
                value_cell = result.members.get('value')
                if value_cell is not None:
                    return value_cell.value
            return result
        init = self._find_method(obj, 'initialize')
        if init is not None:
            return self.construct(obj.type, [idx])
        raise runtime_error('类型不支持下标操作')

    # 实参 cell 构建：普通实参求值后分配新 cell；
    # **name / **obj.x 引用实参求值得到地址整数，还原为原 cell（引用传递载体）
    def _eval_arg_cell(self, a, env):
        if next(iter(a)) == 'unary' and a['unary']['operator'] == '**':
            addr = self.eval_node(a, env)
            if isinstance(addr, int):
                cell = self.address_space.get(addr)
                if cell is not None:
                    # **name 求值得到的是存原地址的新 cell，继续解一层取原 cell
                    inner = cell.value
                    if isinstance(inner, int):
                        inner_cell = self.address_space.get(inner)
                        if inner_cell is not None:
                            return inner_cell
                    return cell
            return self.address_space.allocate(addr)
        return self.address_space.allocate(self.eval_node(a, env))

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

        # 实参 cell：普通实参求值后分配新 cell（值传递的载体）；
        # **name / **obj.x 引用实参求值得到原 cell 的地址，还原为原 cell 直传，
        # 供 ** 形参引用传递使用（直接改原对象）。
        arg_cells = [self._eval_arg_cell(a, env) for a in arg_asts]
        if next(iter(name_node)) == 'member':
            receiver = self.eval_node(name_node['member']['left'], env)
            member_name = name_node['member']['right']['name']['value']
            callable_obj = self._get_member(receiver, member_name)
            # python_function 一律不注入 receiver（无论接收者是否为 library 类型），
            # 使 python_api.demo.fn(a, b) 与 f = python_api.demo.fn; f(a, b) 语义一致。
            if isinstance(callable_obj, python_function):
                return self._call(
                    callable_obj,
                    arg_cells,
                    frame_label = self._frame_label_from_call(name_node)
                )
            lib_type = self._resolve_global('library')
            if lib_type is not None and receiver.type is lib_type:
                return self._call(
                    callable_obj,
                    arg_cells,
                    frame_label = self._frame_label_from_call(name_node)
                )
            receiver_cell = self.address_space.allocate(receiver)
            return self._call(
                callable_obj,
                [receiver_cell] + arg_cells,
                frame_label = self._frame_label_from_call(name_node)
            )
        callable_obj = self.eval_node(name_node, env)
        return self._call(
            callable_obj,
            arg_cells,
            frame_label = self._frame_label_from_call(name_node)
        )
