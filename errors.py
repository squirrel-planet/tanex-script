import re
from dataclasses import dataclass

# --clear 全局开关：True 时抑制所有普通输出（仅保留错误与警告）
clear_mode = False

@dataclass
class tanex_script_error(Exception):
    message: str
    file: str | None = None
    line: int | None = None
    col: int | None = None
    code: str | None = None

    def __post_init__(self):
        super().__init__(self.message)

def output_message(message_list: list, should_exit: bool = True, color: str = '\033[0m', suppressible: bool = True):
    if message_list:

        def get_content(value, level = 0):
            content = ''
            for s in value:
                if isinstance(s, str):
                    indent = level * '  '
                    if '\n' in s:
                        lines = s.split('\n')
                        content += '\n' + indent + '·' + lines[0]
                        for line in lines[1:]:
                            content += '\n' + indent + line
                    else:
                        content += f'\n{indent}·{s}'
                else:
                    content += get_content(s, level + 1)
            return content

        if not (clear_mode and suppressible):
            content = get_content(message_list)
            print(f'\n{color}{content}\033[0m\n')
    if should_exit:
        exit(1)

def warning(warning_list: list):
    output_message(['警告', warning_list], False, '\033[38;5;208m', suppressible = False)

def _code_block(file, line, col, source = None, show_line = True) -> str | None:
    if not line or not col:
        return None
    if source is None:
        if not file:
            return None
        # 代码行展示仅对 .tsuc 源码有效；编译产物（.tscc/.tscl）按 JSON 读会错乱
        if not file.endswith('.tsuc'):
            return None
        try:
            with open(file, 'r', encoding = 'utf-8') as f:
                source = f.read()
        except OSError:
            return None
    lines = source.split('\n')
    if line < 1 or line > len(lines):
        return None
    code = lines[line - 1]
    idx = col - 1
    if idx < 0:
        idx = 0
    if idx >= len(code):
        idx = max(len(code) - 1, 0)
    delimiters = "()[]{};,.:~!+-*/\\%^<>=?|$#'\""
    start = idx
    while start > 0 and code[start - 1] not in delimiters and not code[start - 1].isspace():
        start -= 1
    end = idx + 1
    while end < len(code) and code[end] not in delimiters and not code[end].isspace():
        end += 1
    caret = ' ' * start + '^' * (end - start)
    if not show_line:
        return f'{code}\n{caret}'
    width = len(str(line))
    prefix = ' ' * width
    return f'{line:>{width}} | {code}\n{prefix} | {caret}'

def _format_error(error_list) -> list:
    if isinstance(error_list, tanex_script_error):
        parts = [error_list.message]
        if error_list.file:
            parts.append(f'文件: {error_list.file}')
        if error_list.line or error_list.col:
            location = []
            if error_list.line:
                location.append(f'第 {error_list.line} 行')
            if error_list.col:
                location.append(f'第 {error_list.col} 列')
            parts.append('位置: ' + '，'.join(location))
        return parts
    if isinstance(error_list, Exception):
        return [str(error_list)]
    return error_list

# 回溯帧对应的源码行（仅 .tsuc 源码有效）
def _source_line(file, line) -> str | None:
    if not file or not file.endswith('.tsuc') or not line:
        return None
    try:
        with open(file, 'r', encoding = 'utf-8') as f:
            lines = f.read().split('\n')
    except OSError:
        return None
    if 1 <= line <= len(lines):
        return lines[line - 1]
    return None

# 将调用链回溯帧列表渲染为嵌套列表（每帧：文件+行号+函数名，附该行源码）
def _trace_block(frames) -> list:
    block = ['回溯（调用链）']
    for file, line, col, label in frames:
        if line:
            frame_item = [
                f'文件: {file}，第 {line} 行，in {label}',
            ]
            src = _source_line(file, line)
            if src:
                frame_item.append([src])
            block.append(frame_item)
        else:
            where = file or '未知文件'
            block.append([f'文件: {where}（顶层）'])
    return block

def error(error_list, just_print: bool = False, brief: bool = False, source: str | None = None):
    # 统一错误处理函数
    # error_list: 错误对象（tanex_script_error / Exception / list）
    # just_print: 是否只打印不退出（False=退出，True=继续运行）
    # brief: 是否精简模式（False=显示完整信息，True=只显示错误信息+代码行无行号）
    # source: 源代码内容（仅在 brief 为 True 时可传入，避免重复读文件）
    if isinstance(error_list, tanex_script_error):
        is_runtime = error_list.__class__.__name__ == 'runtime_error'
        if brief:
            # 只显示错误消息，不显示文件路径和详细位置
            message_list = [
                '运行时错误' if is_runtime else '语法错误',
                [error_list.message]
            ]
            code = _code_block(
                error_list.file,
                error_list.line,
                error_list.col,
                source,
                show_line = False
                # 不显示行号
            )
        else:
            # 显示完整错误信息和位置
            message_list = [
                '运行时错误' if is_runtime else '语法错误',
            ]
            # 运行时错误带调用链回溯时，先输出回溯再输出错误详情
            if is_runtime and getattr(error_list, 'trace', None):
                message_list.append(_trace_block(error_list.trace))
            message_list.append(_format_error(error_list))
            code = _code_block(
                error_list.file,
                error_list.line,
                error_list.col,
                source,
                show_line = True
                # 显示行号
            )
        if code:
            message_list.append(f'代码\n{code}')
        output_message(
            message_list,
            should_exit = not just_print,
            # just_print = True 时不退出
            color = '\033[91m',
            suppressible = False
        )
    elif isinstance(error_list, Exception):
        # 普通 Exception
        if brief:
            output_message(
                ['错误', [str(error_list)]],
                should_exit = not just_print,
                color = '\033[91m',
                suppressible = False
            )
        else:
            output_message(
                ['错误', _format_error(error_list)],
                should_exit = not just_print,
                color = '\033[91m',
                suppressible = False
            )
    else:
        # 其他（应该是 list）
        if brief:
            # 如果是 list，只取第一个元素作为简要信息
            msg = error_list[0] if isinstance(error_list, list) and error_list else str(error_list)
            output_message(
                ['错误', [str(msg)]],
                should_exit = not just_print,
                color = '\033[91m',
                suppressible = False
            )
        else:
            output_message(
                ['错误', _format_error(error_list)],
                should_exit = not just_print,
                color = '\033[91m',
                suppressible = False
            )

def print_error(error_list):
    error(error_list, just_print = True, brief = False)

def print_error_brief(error_list, source = None):
    error(error_list, just_print = True, brief = True, source = source)

def hex_to_ansi(hex_color):
    pattern = r'^#([0-9a-fA-F]{3}){1,2}$'
    if not re.match(pattern, hex_color):
        error([f'无效的十六进制颜色代码: {hex_color}'])
    if len(hex_color) == 4:
        hex_color = '#' + ''.join([c * 2 for c in hex_color[1:]])
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    return f'\033[38;2;{r};{g};{b}m'
