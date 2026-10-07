import json
import sys
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings
from compile.highlighter import tanex_lexer
from compile.highlighter import tanex_style
from compile.highlighter import scan_spans
from compile.main import compile_source
from errors import output_message
from errors import print_error_brief
from runtime.interpreter import interpreter
from runtime.values import runtime_error
from runtime.values import type_object
from runtime.values import instance

_open_close = {'(': ')', '[': ']', '{': '}'}
_close_open = {v: k for k, v in _open_close.items()}

def _scan(source: str) -> tuple[int, str | None]:
    stack = []
    last_significant = None
    for start, end, kind in scan_spans(source):
        if kind in ('comment', 'annotation', 'plain'):
            continue
        text = source[start:end]
        last_significant = text
        if kind == 'operator':
            if text in _open_close:
                stack.append(text)
            elif text in _close_open and stack and stack[-1] == _close_open[text]:
                stack.pop()
    return len(stack), last_significant

def _indent_text(source: str) -> str:
    lines = source.split('\n')
    last = lines[-1]
    lead = len(last) - len(last.lstrip(' \t'))
    i = len(last)
    trailing = 0
    while i > lead:
        i -= 1
        if last[i] in _open_close:
            trailing += 1
        elif last[i] in _close_open:
            trailing -= 1
        else:
            break
    width = lead + trailing * 4
    if width < 0:
        width = 0
    return ' ' * width

def _is_complete(source: str) -> bool:
    depth, last_significant = _scan(source)
    if last_significant is None:
        return True
    if depth:
        return False
    return last_significant == ';'

def _format_value(interp, value) -> str:
    return interp._display_string(value)

def _is_silent_statement(stmt) -> bool:
    kind = next(iter(stmt))
    if kind in ('assignment', 'import'):
        return True
    if kind == 'unary':
        return stmt['unary']['operator'] in ('*', '**', '***', '&', '&&', '&&&')
    return False

def _print_result(interp, statements, result):
    if not statements:
        return
    if _is_silent_statement(statements[-1]):
        return
    print(_format_value(interp, result))

# 执行一段完整源码，返回退出码（None 表示继续）
def _exec_source(interp, source: str) -> int | None:
    try:
        ast = json.loads(compile_source(source, '<shell-mode-input>',
            exit_on_error = False))
    except Exception as e:
        print_error_brief(e, source)
        return None
    statements = ast['Tanex Script']
    interp.annotations.update(ast.get('annotations', {}))
    try:
        result, returned = interp.run_statements(statements)
    except Exception as e:
        if isinstance(e, runtime_error):
            e.annotate(interp._current_file, interp._current_pos)
        # 交互环境用精简模式展示：不含文件/行号/列号，但带源码代码定位
        print_error_brief(e, source)
        return None
    if returned and isinstance(result, int):
        return result
    _print_result(interp, statements, result)
    return None

# 交互式 shell，每条完整语句立即编译执行
def repl_entry() -> int | None:
    interp = interpreter()
    interp.init_core()
    interp.load_bootstrap()
    # REPL 环境下同样填充内置引导常量：program_path/args 保持原逻辑，
    # path 因无用户程序目录填充为 none
    interp.inject_args(repl_mode = True)
    if not sys.stdin.isatty():
        return _repl_entry_plain(interp)
    try:
        session = PromptSession(
            lexer = tanex_lexer(),
            style = tanex_style,
            history = InMemoryHistory(),
            key_bindings = _shell_key_bindings(),
        )
    except Exception:
        return _repl_entry_plain(interp)
    output_message([
        'Tanex Script 交互式环境',
        '每条语句以 ; 结尾后立即执行',
        'Ctrl+D 打开菜单(包括 退出、帮助模式)，Ctrl+C 清除当前输入',
    ], False)
    buffer_lines = []
    while True:
        prompt_text = '>>> ' if not buffer_lines else '... '
        try:
            prompt = FormattedText([('class:tanex.prompt', prompt_text)])
            line = session.prompt(prompt, default = _indent_text('\n'.join(buffer_lines)))
        except KeyboardInterrupt:
            buffer_lines = []
            continue
        except EOFError:
            action = _ctrl_d_menu(interp, in_help = False)
            if action == 'exit':
                break
            if action == 'enter_help':
                if _help_shell(interp) == 'exit':
                    break
            buffer_lines = []
            continue
        buffer_lines.append(line)
        source = '\n'.join(buffer_lines)
        if not _is_complete(source):
            continue
        rc = _exec_source(interp, source)
        if rc is not None:
            return rc
        buffer_lines = []
    return None

# 非交互输入时使用的普通 shell，无高亮但保持脚本可用
def _repl_entry_plain(interp) -> int | None:
    buffer_lines = []
    while True:
        prompt_text = '>>> ' if not buffer_lines else '... '
        prompt_text += _indent_text('\n'.join(buffer_lines))
        try:
            line = input(prompt_text)
        except EOFError:
            break
        except KeyboardInterrupt:
            buffer_lines = []
            print()
            continue
        buffer_lines.append(line)
        source = '\n'.join(buffer_lines)
        if not _is_complete(source):
            continue
        rc = _exec_source(interp, source)
        if rc is not None:
            return rc
        buffer_lines = []
    return None

# Ctrl+D 菜单：普通 shell 下选择进入帮助模式或退出；帮助模式 shell 下选择退出帮助或退出
def _ctrl_d_menu(interp, in_help: bool):
    if in_help:
        output_message([
            'Ctrl+D 菜单（帮助模式）',
            '1. 退出',
            '2. 退出帮助 shell',
        ], False)
    else:
        output_message([
            'Ctrl+D 菜单',
            '1. 退出',
            '2. 帮助模式 shell',
        ], False)
    while True:
        try:
            choice = input('请选择: ').strip()
        except (EOFError, KeyboardInterrupt):
            return None
        if choice == '1':
            return 'exit'
        if choice == '2':
            return 'exit_help' if in_help else 'enter_help'
        output_message(['无效选择'], False)

# 帮助模式 shell：输入 + 列出所有已定义类型的 addition 注解与 integer 注解
# 输入其他名称时查询对应注解，无则输出"无帮助内容"
def _help_shell(interp) -> str:
    output_message([
        '已进入帮助模式',
        '使用方法:',
        [
            '输入运算符（如 +） 查看所有类型 addition 注解与 integer 注解',
            '输入名称（如 standard.output）查看对应注解'
        ],
        'Ctrl+D 打开菜单可选择退出帮助 shell'
    ], False)
    try:
        session = PromptSession(
            lexer = tanex_lexer(),
            style = tanex_style,
            history = InMemoryHistory(),
            key_bindings = _shell_key_bindings(),
        )
    except Exception:
        return _help_shell_plain(interp)
    while True:
        try:
            prompt = FormattedText([('class:tanex.prompt', 'help> ')])
            line = session.prompt(prompt)
        except KeyboardInterrupt:
            print()
            continue
        except EOFError:
            action = _ctrl_d_menu(interp, in_help = True)
            if action == 'exit':
                return 'exit'
            if action == 'exit_help':
                return 'back'
            continue
        text = line.strip()
        if not text:
            continue
        if text == '+':
            _show_addition_help(interp)
        else:
            _show_annotation_help(interp, text)

# 非交互输入时使用的帮助 shell，无高亮但保持脚本可用
def _help_shell_plain(interp) -> str:
    while True:
        try:
            line = input('help> ')
        except KeyboardInterrupt:
            print()
            continue
        except EOFError:
            action = _ctrl_d_menu(interp, in_help = True)
            if action == 'exit':
                return 'exit'
            if action == 'exit_help':
                return 'back'
            continue
        text = line.strip()
        if not text:
            continue
        if text == '+':
            _show_addition_help(interp)
        else:
            _show_annotation_help(interp, text)

# 遍历已定义类型，输出各类型 addition 成员注解与 integer 类型注解
def _show_addition_help(interp) -> None:
    lines = []
    type_names = []
    for name, cell in interp.global_scope.names.items():
        value = cell.value
        if value is not None and interp._is_type(value):
            type_names.append(name)
    for name in sorted(type_names):
        typ = interp.global_scope.names[name].value
        member = interp._find_member_cell(typ, 'addition')
        if member is None:
            continue
        ann = interp.annotations.get(name + '.addition')
        lines.append(f'{name}.addition(): {ann if ann else "无帮助内容"}')
    int_ann = interp.annotations.get('integer')
    lines.append(f'integer: {int_ann if int_ann else "无帮助内容"}')
    output_message(lines, False)

# 按名称查询注解：先匹配完整名称，再尝试去括号后的成员名；
# 查不到注解时若名称在作用域中能解析出值（实例/类型对象），输出其实例 help
def _show_annotation_help(interp, text: str) -> None:
    name = _normalize_help_name(text)
    ann = interp.annotations.get(name)
    if ann is None and '.' in name:
        left, right = name.split('.', 1)
        lib_table = interp.lib_annotations.get(left)
        if lib_table is not None:
            ann = lib_table.get(right)
        if ann is None:
            ann = interp.annotations.get(right)
    if ann:
        output_message([f'{name}: {ann}'], False)
        return
    # 名称是已导入库名时优先显示库本体帮助（文件级注解 + 带注解成员清单），
    # 而不是把库实例当作普通 library 实例遍历其类型成员
    lib_table = interp.lib_annotations.get(name)
    if lib_table is not None:
        _show_library_help(name, lib_table)
        return
    cell = interp.global_scope.names.get(name)
    if cell is not None and cell.value is not None:
        help_text = _help_value_text(interp, cell.value)
        if help_text is not None:
            output_message([help_text], False)
            return
    output_message([f'{text}: 无帮助内容'], False)

# 库本体帮助：先显示文件级注解（@# ... #;），再列出带注解成员供 standard.成员名 深入查询
def _show_library_help(name: str, table: dict) -> None:
    lines = []
    file_ann = table.get('')
    if file_ann:
        lines.append(f'{name}: {file_ann}')
    member_names = sorted(k for k in table if k and '.' not in k)
    if member_names:
        lines.append(f'{name} 库带注解成员（输入 {name}.成员名 查看详情）:')
        lines.append(member_names)
    if not lines:
        lines.append(f'{name}: 未定义任何库级注解或成员注解')
    output_message(lines, False)

# 值帮助文本：类型对象查类型注解；字符串实例按文本查注解；普通实例遍历成员输出实例 help；
# 无法处理时返回 None（由调用方输出"无帮助内容"）
def _help_value_text(interp, value) -> str | None:
    if isinstance(value, type_object):
        content = interp.annotations.get(value.name)
        return content if content is not None else '无帮助内容'
    if interp._is_type(value):
        name = _find_type_name(interp, value)
        content = interp.annotations.get(name)
        return content if content is not None else '无帮助内容'
    if isinstance(value, instance) and interp._is_current('string', value.type):
        text = _string_instance_to_py(interp, value)
        content = interp.annotations.get(text)
        return content if content is not None else '无帮助内容'
    if isinstance(value, instance):
        return _instance_help_text(interp, value)
    return None

def _string_instance_to_py(interp, obj) -> str:
    char_list = interp._get_string_value(obj)
    codes = interp._list_to_py(char_list)
    return ''.join(chr(c) for c in codes)

def _find_type_name(interp, typ) -> str:
    if isinstance(typ, type_object) and typ.name:
        return typ.name
    for name, cell in interp.global_scope.names.items():
        if cell.value is typ:
            return name
    return '<匿名>'

def _collect_member_names(typ) -> set:
    names = set()
    seen = set()
    cur = typ
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        if isinstance(cur, (instance, type_object)):
            names.update(cur.members.keys())
        if isinstance(cur, instance):
            cur = cur.inherit
        elif isinstance(cur, type_object):
            cur = cur.inherit
        else:
            break
    return names

# 实例 help：给出实例类型，遍历输出成员 help
def _instance_help_text(interp, value) -> str:
    type_name = _find_type_name(interp, value.type)
    lines = ['类型: ' + type_name]
    member_names = _collect_member_names(value.type)
    if interp._is_current('function_type', value.type):
        member_names.update(('params', 'defaults', 'statements'))
    for m in sorted(member_names):
        ann = interp.annotations.get(type_name + '.' + m)
        lines.append('  ' + m + ': ' + (ann if ann else '无帮助内容'))
    return '\n'.join(lines)

def _normalize_help_name(text: str) -> str:
    name = text.strip()
    while name.endswith('()'):
        name = name[:-2].rstrip()
    return name

# 批量输入模式，Ctrl+D 结束，整段代码实时高亮
def read_console_source() -> str:
    output_message([
        '请输入代码，Ctrl+D 结束输入',
    ], False)
    if not sys.stdin.isatty():
        return _read_console_source_plain()
    try:
        session = PromptSession(
            lexer = tanex_lexer(),
            style = tanex_style,
            key_bindings = _batch_key_bindings(),
            multiline = True,
        )
        text = session.prompt()
    except KeyboardInterrupt:
        return ''
    except EOFError:
        return ''
    except Exception:
        return _read_console_source_plain()
    return text

# 闭括号按键绑定：光标位于自动缩进的空白处时，先删除缩进再插入闭括号
def _register_close_brackets(bindings: KeyBindings) -> None:
    for bracket in (')', ']', '}'):
        @bindings.add(bracket)
        def _on_close(event, bracket = bracket):
            buffer = event.current_buffer
            before = buffer.document.current_line_before_cursor
            if before and before.isspace():
                buffer.delete_before_cursor(len(before))
            buffer.insert_text(bracket)

# 交互式 shell 使用的按键绑定
def _shell_key_bindings() -> KeyBindings:
    bindings = KeyBindings()
    _register_close_brackets(bindings)
    return bindings

# 批量输入使用的按键绑定，Enter 换行，Ctrl+D 结束输入
def _batch_key_bindings() -> KeyBindings:
    bindings = KeyBindings()
    _register_close_brackets(bindings)
    @bindings.add('enter')
    def _on_enter(event):
        buffer = event.current_buffer
        buffer.insert_text('\n' + _indent_text(buffer.text_before_cursor))
    @bindings.add('c-d')
    def _on_ctrl_d(event):
        event.current_buffer.validate_and_handle()

    return bindings

# 非交互输入时使用的普通批量输入，无高亮但保持脚本可用
def _read_console_source_plain() -> str:
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        lines.append(line)
    return '\n'.join(lines)
