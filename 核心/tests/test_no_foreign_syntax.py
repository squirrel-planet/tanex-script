import os
import re
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[2]
_skip_dirs = {'.git', '__pycache__', '.pytest_cache', 'build', '_internal', 'node_modules'}
_c_style_patterns = [
    re.compile('\\bif\\s*\\([^,()]*\\)\\s*\\{'),
    re.compile('\\}\\s*else\\s*\\{'),
    re.compile('\\bwhile\\s*\\([^,()]*\\)\\s*\\{'),
    re.compile('\\bfor\\s*\\([^,()]*\\)\\s*\\{'),
    re.compile('\\btry\\s*\\{'),
    re.compile('\\bcatch\\s*\\(')
]

# 把字符串、注释、注解替换成空格，避免它们里的示例被误判
def _strip_literals(source: str) -> str:
    result = []
    i = 0
    n = len(source)
    while i < n:
        ch = source[i]
        if ch == '"':
            result.append(' ')
            i += 1
            while i < n:
                c = source[i]
                if c == '\\' and i + 1 < n:
                    result.append('\n' if source[i + 1] == '\n' else ' ')
                    result.append(' ')
                    i += 2
                    continue
                result.append('\n' if c == '\n' else ' ')
                i += 1
                if c == '"':
                    break
        elif ch == '@':
            end = source.find('#;', i)
            if end == -1:
                result.append(' ')
                i += 1
                continue
            for c in source[i:end + 2]:
                result.append('\n' if c == '\n' else ' ')
            i = end + 2
        elif ch == '#':
            end = source.find('#', i + 1)
            if end == -1:
                end = n - 1
            for c in source[i:end + 1]:
                result.append('\n' if c == '\n' else ' ')
            i = end + 1
        else:
            result.append(ch)
            i += 1
    return ''.join(result)

def _iter_sources():
    for root, dirs, files in os.walk(_repo_root):
        dirs[:] = [d for d in dirs if d not in _skip_dirs]
        for name in files:
            if name.endswith('.tsuc'):
                yield (Path(root) / name)

def test_no_c_style_or_line_continuation():
    offenders = []
    for path in _iter_sources():
        source = path.read_text(encoding = 'utf-8')
        stripped = _strip_literals(source)
        for number, line in enumerate(stripped.split('\n'), 1):
            if line.rstrip().endswith('\\'):
                offenders.append(f'{path}:{number} 行尾反斜杠不是续行符')
                continue
            for pattern in _c_style_patterns:
                if pattern.search(line):
                    offenders.append(f'{path}:{number} C 风格控制结构: {line.strip()}')
                    break
    assert not offenders, '发现非 Tanex Script 语法:\n' + '\n'.join(offenders)
