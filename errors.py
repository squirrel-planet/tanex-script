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

def error(error_list):
    if isinstance(error_list, tanex_script_error):
        is_runtime = error_list.__class__.__name__ == 'runtime_error'
        message_list = ['运行时错误' if is_runtime else '语法错误',
            _format_error(error_list)]
        code = _code_block(error_list.file, error_list.line, error_list.col)
        if code:
            message_list.append(f'代码\n{code}')
        output_message(message_list, True, '\033[91m', suppressible = False)
    else:
        output_message(['错误', _format_error(error_list)], True, '\033[91m', suppressible = False)

def print_error(error_list):
    if isinstance(error_list, tanex_script_error):
        is_runtime = error_list.__class__.__name__ == 'runtime_error'
        message_list = ['运行时错误' if is_runtime else '语法错误',
            _format_error(error_list)]
        code = _code_block(error_list.file, error_list.line, error_list.col)
        if code:
            message_list.append(f'代码\n{code}')
        output_message(message_list, False, '\033[91m', suppressible = False)
    else:
        output_message(['错误', _format_error(error_list)], False, '\033[91m', suppressible = False)

def print_error_brief(error_list, source = None):
    if isinstance(error_list, tanex_script_error):
        is_runtime = error_list.__class__.__name__ == 'runtime_error'
        message_list = ['运行时错误' if is_runtime else '语法错误',
            [error_list.message]]
        code = _code_block(error_list.file, error_list.line, error_list.col,
            source, False)
        if code:
            message_list.append(f'代码\n{code}')
        output_message(message_list, False, '\033[91m', suppressible = False)
    else:
        output_message(['错误', [str(error_list)]], False, '\033[91m', suppressible = False)

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
