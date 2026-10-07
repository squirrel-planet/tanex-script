# TanexScript 容错词法扫描
# 与 compile/highlighter.py 的 scan_spans 保持一致，但独立实现，
# 使 IDLE 不依赖 prompt_toolkit，随便哪个解释器都能直接跑起来。

_keywords = frozenset({
    'return', 'break', 'in', 'type_of', 'import',
    'and', 'or', 'not', 'is',
})
_open_close = {'(': ')', '[': ']', '{': '}'}
_close_open = {v: k for k, v in _open_close.items()}
_ignored = frozenset({'plain', 'comment', 'annotation'})

# 容错扫描器：不抛异常，产出 (开始, 结束, 类型) 三元组，覆盖全部字符
def scan_spans(text: str) -> list:
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
            # 注解：@ [标识符][.成员] # 内容 #;
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

# 括号深度与最后一个有效符号，用于判断语句是否写完
def scan_state(source: str) -> tuple:
    stack = []
    last = None
    for start, end, kind in scan_spans(source):
        if kind in _ignored or kind == 'plain':
            continue
        text = source[start:end]
        last = text
        if kind == 'operator':
            if text in _open_close:
                stack.append(text)
            elif text in _close_open and stack and stack[-1] == _close_open[text]:
                stack.pop()
    return len(stack), last

# 语句是否完整：括号配平且以 ; 结尾
def is_complete(source: str) -> bool:
    depth, last = scan_state(source)
    if last is None:
        return True
    if depth:
        return False
    return last == ';'

# 源码中是否出现输入运算符 >>（用于判断语句会不会向 stdin 读取）
def has_input_operator(source: str) -> bool:
    ops = [source[s:e] for s, e, kind in scan_spans(source)
        if kind == 'operator']
    for i in range(len(ops) - 1):
        if ops[i] == '>' and ops[i + 1] == '>':
            return True
    return False


# 续行缩进：复制上一行缩进，并按行尾未闭合括号增加一级
def next_indent(source: str) -> str:
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
