from prompt_toolkit.lexers import Lexer
from prompt_toolkit.styles import Style

_keywords = frozenset({
    'return', 'break', 'in', 'type_of', 'import',
    'and', 'or', 'not', 'is',
})
_style_map = {
    'plain': 'class:tanex.name',
    'name': 'class:tanex.name',
    'keyword': 'class:tanex.keyword',
    'string': 'class:tanex.string',
    'number_literal': 'class:tanex.number',
    'number': 'class:tanex.number',
    'comment': 'class:tanex.comment',
    'annotation': 'class:tanex.comment',
    'operator': '',
}
tanex_style = Style.from_dict({
    'tanex.prompt': '#e5c07b',
    'tanex.keyword': 'bold #c678dd',
    'tanex.string': '#d19a66',
    'tanex.number': '#98c379',
    'tanex.comment': '#5c6370',
    'tanex.name': '#61afef',
})

# 容错扫描器，不抛异常，产出 (开始, 结束, 类型) 三元组，覆盖全部字符
def scan_spans(text: str) -> list[tuple[int, int, str]]:
    spans = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch in ' \t\r\n':
            j = i
            while j < n and text[j] in ' \t\r\n':
                j += 1
            spans.append((i, j, 'plain'))
            i = j
        elif ch == '@':
            # 注解：@ [标识符][.成员] # 内容 #;（容错扫描；进入内容分隔符前遇换行视为未闭合）
            j = i + 1
            in_content = False
            while j < n:
                if text[j] == '#' and j + 1 < n and text[j + 1] == ';':
                    j += 2
                    break
                if text[j] == '#':
                    in_content = True
                elif text[j] in '\r\n' and not in_content:
                    break
                j += 1
            spans.append((i, j, 'annotation'))
            i = j
        elif ch == '#':
            j = i + 1
            while j < n and text[j] != '#':
                j += 1
            if j < n:
                j += 1
            spans.append((i, j, 'comment'))
            i = j
        elif ch == '"' or ch == "'":
            quote = ch
            j = i + 1
            while j < n:
                if text[j] == '\\':
                    j += 2
                    continue
                if text[j] == quote:
                    j += 1
                    break
                j += 1
            kind = 'string' if quote == '"' else 'number_literal'
            spans.append((i, j, kind))
            i = j
        elif ch.isdigit():
            j = i
            while j < n and text[j].isdigit():
                j += 1
            spans.append((i, j, 'number'))
            i = j
        elif ch.isalpha() or ch == '_' or ord(ch) > 127:
            j = i
            while j < n and (text[j].isalpha() or text[j] == '_'
                or ord(text[j]) > 127):
                j += 1
            kind = 'keyword' if text[i:j] in _keywords else 'name'
            spans.append((i, j, kind))
            i = j
        else:
            spans.append((i, i + 1, 'operator'))
            i += 1
    return spans

# prompt_toolkit 词法器，把整段缓冲实时着色
class tanex_lexer(Lexer):
    def lex_document(self, document):
        text = document.text
        spans = scan_spans(text)
        line_fragments = []
        current_line = []
        for start, end, kind in spans:
            style = _style_map[kind]
            part_start = start
            while part_start < end:
                nl = text.find('\n', part_start, end)
                if nl == -1:
                    current_line.append((style, text[part_start:end]))
                    break
                current_line.append((style, text[part_start:nl]))
                line_fragments.append(current_line)
                current_line = []
                part_start = nl + 1
        line_fragments.append(current_line)
        while len(line_fragments) < document.line_count:
            line_fragments.append([])
        def get_line(lineno):
            if 0 <= lineno < len(line_fragments):
                return line_fragments[lineno]
            return []
        return get_line
