import sys
from compile.preprocessor.source_map import source_map
sys.path.append('..')
from errors import tanex_script_error

# 非值关键字集合，这些关键字不作为值参与表达式
_non_value_words = frozenset({
    'return', 'break', 'in', 'type_of', 'import',
})
# 关键字别名，分词时直接映射为对应运算符
_keyword_aliases = {
    'and': '&&', 'or': '||',
    'not': '!', 'is': '==',
}
# 分词器，将源码字符串分解为 token 流
class tokenizer(object):
    def __init__(self, source: str, filename: str = '<unknown>',
        source_map: source_map | None = None):
        self._source = source
        self._filename = filename
        self._source_map = source_map
        self._pos = 0
        self._line = 1
        self._col = 1

    # 执行分词，返回 (值, 行, 列, 文件名) 元组列表
    def tokenize(self) -> list[tuple[str, int, int, str]]:
        result: list[tuple[str, int, int, str]] = []
        while self._pos < len(self._source):
            self._skip_whitespace()
            if self._pos >= len(self._source):
                break
            ch = self._source[self._pos]
            if ch == '@':
                result.append(self._read_annotation())
            elif ch == '#':
                result.append(self._read_comment())
            elif ch == '"':
                result.append(self._read_string())
            elif ch == "'":
                result.append(self._read_number_literal())
            elif ch.isdigit():
                result.append(self._read_integer())
            elif self._is_identifier_start(ch):
                result.append(self._read_name())
            else:
                result.append(self._read_operator_or_delimiter())
        self._validate(result)
        return result

    # 判断 token 是否为值（参与表达式计算）
    @staticmethod
    def _is_value(val: str) -> bool:
        if not val:
            return False
        if val in _non_value_words:
            return False
        if val in (']', ')', '}'):
            return False
        if len(val) >= 2:
            if val[0] == '"' and val[-1] == '"' or val[0] == "'" and val[-1] == "'":
                return True
        if val.isdigit():
            return True
        if val[0].isalpha() or val[0] == '_' or ord(val[0]) > 127:
            return True
        return False

    # 判断 token 是否为运算符或分隔符
    @staticmethod
    def _is_operator_or_delim(val: str) -> bool:
        if not val:
            return False
        if val in _non_value_words:
            return True
        if val in (';', ',', ':', '.', '?', '~'):
            return True
        if val.startswith('#') and val.endswith('#'):
            return True
        if val.startswith('@') and val.endswith('#;'):
            return True
        return False

    # 验证 token 序列：相邻 value 之间必须用分号或运算符分隔
    def _validate(self, tokens: list[tuple[str, int, int, str]]):
        for i in range(len(tokens) - 1):
            v1, l1, c1, f1 = tokens[i]
            v2, l2, c2, f2 = tokens[i + 1]
            if self._is_value(v1) and self._is_value(v2):
                raise self._make_error_at(
                    f'语句缺少结束符分号: "{v1}" 后应为分号或运算符',
                    l2, c2, f2,
                )

    # 前进一个字符并更新行号列号，返回被跳过的字符
    def _advance(self) -> str:
        ch = self._source[self._pos]
        self._pos += 1
        if ch == '\n':
            self._line += 1
            self._col = 1
        else:
            self._col += 1
        return ch

    # 向前查看当前或偏移位置的字符
    def _peek(self, offset: int = 0) -> str:
        idx = self._pos + offset
        if 0 <= idx < len(self._source):
            return self._source[idx]
        return ''

    # 通过源映射解析实际文件名
    def _resolve_file(self, line: int) -> str:
        if self._source_map:
            mapped = self._source_map.lookup(line)
            if mapped:
                return mapped[0]
        return self._filename

    # 构造 token 元组，可指定行列（用于起始标记）
    def _make_token(self, value: str, line: int | None = None,
        col: int | None = None) -> tuple[str, int, int, str]:
        l = line or self._line
        c = col or self._col
        f = self._resolve_file(l)
        return (value, l, c, f)

    # 构造当前行/列的错误
    def _error(self, message: str):
        return tanex_script_error(
            message = message,
            file = self._filename,
            line = self._line,
            col = self._col,
            code = 'tokenizer',
        )

    # 构造指定行列的错误（用于验证阶段）
    def _make_error_at(self, message: str, line: int, col: int,
        file: str | None = None):
        return tanex_script_error(
            message = message,
            file = file or self._filename,
            line = line,
            col = col,
            code = 'tokenizer',
        )

    # 跳过空白字符（空格、制表符、回车、换行）
    def _skip_whitespace(self):
        while self._pos < len(self._source):
            ch = self._source[self._pos]
            if ch in ' \t\r\n':
                self._advance()
            else:
                break

    # 读取注释 token（# ... #）
    def _read_comment(self):
        start_line = self._line
        start_col = self._col
        self._advance()
        value_chars: list[str] = ['#']
        while self._pos < len(self._source):
            ch = self._source[self._pos]
            self._advance()
            value_chars.append(ch)
            if ch == '#':
                break
        else:
            raise self._error('未闭合的注释')
        return self._make_token(''.join(value_chars), start_line, start_col)

    # 读取注解 token（@ [标识符][.成员] # ... #;），注解为注释的变种。
    # 新语法：@ 标识符 # 内容 #;，标识符可省略（省略时表示文件级注解）。
    # 支持成员级注解：@ boolean.addition # 内容 #;
    def _read_annotation(self):
        start_line = self._line
        start_col = self._col
        self._advance()  # 跳过 '@'
        value_chars: list[str] = ['@']
        # 跳过空白
        while self._pos < len(self._source) and self._source[self._pos] in ' \t\r\n':
            value_chars.append(self._source[self._pos])
            self._advance()
        # 可选标识符（含成员级 类型.成员）
        if self._pos < len(self._source) and self._is_identifier_start(self._source[self._pos]):
            while self._pos < len(self._source) and self._is_identifier_continue(self._source[self._pos]):
                value_chars.append(self._source[self._pos])
                self._advance()
            while self._pos < len(self._source) and self._source[self._pos] == '.':
                value_chars.append('.')
                self._advance()
                if self._pos >= len(self._source) or not self._is_identifier_start(self._source[self._pos]):
                    raise self._error('注解成员名不完整')
                while self._pos < len(self._source) and self._is_identifier_continue(self._source[self._pos]):
                    value_chars.append(self._source[self._pos])
                    self._advance()
        # 跳过空白
        while self._pos < len(self._source) and self._source[self._pos] in ' \t\r\n':
            value_chars.append(self._source[self._pos])
            self._advance()
        if self._pos >= len(self._source) or self._source[self._pos] != '#':
            raise self._error('注解语句缺少 "#" 分隔符')
        value_chars.append('#')
        self._advance()
        # 读内容直到 '#;' 结束
        while self._pos < len(self._source):
            ch = self._source[self._pos]
            self._advance()
            value_chars.append(ch)
            if ch == '#':
                if self._pos < len(self._source) and self._source[self._pos] == ';':
                    value_chars.append(';')
                    self._advance()
                    break
        else:
            raise self._error('未闭合的注解')
        return self._make_token(''.join(value_chars), start_line, start_col)

    # 读取字符串 token（" ... "），支持转义
    def _read_string(self):
        start_line = self._line
        start_col = self._col
        self._advance()
        value_chars: list[str] = ['"']
        while self._pos < len(self._source):
            ch = self._source[self._pos]
            self._advance()
            value_chars.append(ch)
            if ch == '\\':
                if self._pos < len(self._source):
                    value_chars.append(self._source[self._pos])
                    self._advance()
            elif ch == '"':
                return self._make_token(''.join(value_chars), start_line, start_col)
        raise self._error('未闭合的字符串')

    # 读取数字字面量 token（' ... '），支持转义
    def _read_number_literal(self):
        start_line = self._line
        start_col = self._col
        self._advance()
        value_chars: list[str] = ["'"]
        while self._pos < len(self._source):
            ch = self._source[self._pos]
            self._advance()
            value_chars.append(ch)
            if ch == '\\':
                if self._pos < len(self._source):
                    value_chars.append(self._source[self._pos])
                    self._advance()
            elif ch == "'":
                return self._make_token(''.join(value_chars), start_line, start_col)
        raise self._error('未闭合的数字字面量')

    # 读取整数 token
    def _read_integer(self):
        start_line = self._line
        start_col = self._col
        digits: list[str] = []
        while self._pos < len(self._source) and self._source[self._pos].isdigit():
            digits.append(self._source[self._pos])
            self._advance()
        return self._make_token(''.join(digits), start_line, start_col)

    # 判断字符能否作为标识符开头
    def _is_identifier_start(self, ch: str) -> bool:
        return ch.isalpha() or ch == '_' or ord(ch) > 127

    # 判断字符能否在标识符中延续
    def _is_identifier_continue(self, ch: str) -> bool:
        return self._is_identifier_start(ch)

    # 读取标识符/关键字 token，遇到别名时映射为对应运算符
    def _read_name(self):
        start_line = self._line
        start_col = self._col
        chars: list[str] = []
        while self._pos < len(self._source) and self._is_identifier_continue(self._source[self._pos]):
            chars.append(self._source[self._pos])
            self._advance()
        name = ''.join(chars)
        alias = _keyword_aliases.get(name)
        if alias is not None:
            return self._make_token(alias, start_line, start_col)
        return self._make_token(name, start_line, start_col)

    # 读取运算符或分隔符 token，优先匹配多字符运算符
    def _read_operator_or_delimiter(self):
        ch = self._source[self._pos]
        start_line = self._line
        start_col = self._col
        # 三元、二元、赋值运算符匹配
        if ch == '*' and self._peek(1) == '*' and self._peek(2) == '*':
            return self._multi_char('***', start_line, start_col)
        if ch == '*' and self._peek(1) == '*':
            return self._multi_char('**', start_line, start_col)
        if ch == '*' and self._peek(1) == '=':
            return self._multi_char('*=', start_line, start_col)
        if ch == '<' and self._peek(1) == '<':
            return self._multi_char('<<', start_line, start_col)
        if ch == '<' and self._peek(1) == '=':
            return self._multi_char('<=', start_line, start_col)
        if ch == '<' and self._peek(1) == '-':
            return self._multi_char('<-', start_line, start_col)
        if ch == '>' and self._peek(1) == '>':
            return self._multi_char('>>', start_line, start_col)
        if ch == '>' and self._peek(1) == '=':
            return self._multi_char('>=', start_line, start_col)
        if ch == '=' and self._peek(1) == '=':
            return self._multi_char('==', start_line, start_col)
        if ch == '=' and self._peek(1) == '>':
            return self._multi_char('=>', start_line, start_col)
        if ch == '!' and self._peek(1) == '=':
            return self._multi_char('!=', start_line, start_col)
        if ch == '&' and self._peek(1) == '&':
            return self._multi_char('&&', start_line, start_col)
        if ch == '&' and self._peek(1) == '=':
            return self._multi_char('&=', start_line, start_col)
        if ch == '|' and self._peek(1) == '|':
            return self._multi_char('||', start_line, start_col)
        if ch == '|' and self._peek(1) == '=':
            return self._multi_char('|=', start_line, start_col)
        if ch == '$' and self._peek(1) == '$':
            return self._multi_char('$$', start_line, start_col)
        if ch == '+' and self._peek(1) == '=':
            return self._multi_char('+=', start_line, start_col)
        if ch == '-' and self._peek(1) == '=':
            return self._multi_char('-=', start_line, start_col)
        if ch == '-' and self._peek(1) == '>':
            return self._multi_char('->', start_line, start_col)
        if ch == '/' and self._peek(1) == '=':
            return self._multi_char('/=', start_line, start_col)
        if ch == '\\' and self._peek(1) == '=':
            return self._multi_char('\\=', start_line, start_col)
        if ch == '%' and self._peek(1) == '=':
            return self._multi_char('%=', start_line, start_col)
        if ch == '^' and self._peek(1) == '=':
            return self._multi_char('^=', start_line, start_col)
        if ch == '?' and self._peek(1) == '?':
            return self._multi_char('??', start_line, start_col)
        # 单字符运算符和分隔符
        single_map = {
            '(': '(', ')': ')', '[': '[', ']': ']',
            '{': '{', '}': '}', ';': ';', ',': ',', ':': ':',
            '~': '~', '!': '!', '+': '+', '-': '-', '*': '*',
            '/': '/', '\\': '\\', '%': '%', '^': '^',
            '<': '<', '>': '>', '=': '=', '|': '|',
            '?': '?', '.': '.', '$': '$',
        }
        if ch in single_map:
            self._advance()
            return self._make_token(single_map[ch], start_line, start_col)
        raise self._error(f'非法字符: {repr(ch)}')

    # 生成多字符运算符 token
    def _multi_char(self, op: str, line: int, col: int):
        for _ in op:
            self._advance()
        return self._make_token(op, line, col)
