import sys
sys.path.append('..')
from errors import tanex_script_error

# 优先级常量定义，数值越大优先级越高
prec_postfix = 120
prec_unary = 110
prec_unary_sign = 100
prec_unary_addr = 90
prec_factor = 80
prec_term = 70
prec_compare = 60
prec_equal = 50
prec_and = 40
prec_or = 30
prec_arrow = 20
prec_assign = 10
prec_min = 0
# 中缀运算符的优先绑定能力
_infix_lbp: dict[str, int] = {
    '[': prec_postfix, '(': prec_postfix,
    '{': prec_postfix, '.': prec_postfix,
    '*': prec_factor, '/': prec_factor,
    '\\': prec_factor, '%': prec_factor,
    '^': prec_factor, '<<': prec_factor,
    '>>': prec_factor, '$$': prec_factor,
    '+': prec_term, '-': prec_term,
    '<': prec_compare, '<=': prec_compare,
    '>': prec_compare, '>=': prec_compare,
    'in': prec_compare,
    '==': prec_equal, '!=': prec_equal,
    '?': prec_equal, '|': prec_equal,
    '&&': prec_and,
    '||': prec_or,
    '=>': prec_arrow,
    '=': prec_assign,
    '+=': prec_assign, '-=': prec_assign,
    '*=': prec_assign, '/=': prec_assign,
    '\\=': prec_assign, '%=': prec_assign,
    '^=': prec_assign, '&=': prec_assign,
    '|=': prec_assign,
}
# 前缀运算符的优先绑定能力
_prefix_rbp: dict[str, int] = {
    '$': prec_min,
    '!': prec_unary, '~': prec_unary,
    '**': prec_unary, '***': prec_unary,
    '<-': prec_unary, '??': prec_unary,
    'return': prec_min, 'type_of': prec_unary,
    '+': prec_unary_sign, '-': prec_unary_sign,
    '*': prec_unary_addr, '/': prec_unary_addr,
}
# 右结合运算符集合
_right_assoc = frozenset({'=', '=>', '+=', '-=', '*=', '/=', '\\=',
    '%=', '^=', '&=', '|=', '?', '|'})
# Pratt 解析器，将 token 序列解析为 AST
class parser(object):
    def __init__(self, tokens: list[tuple[str, int, int, str]]):
        self._tokens = tokens
        self._pos = 0
        self._filename = tokens[0][3] if tokens else '<unknown>'
        self._annotations: dict[str, str] = {}
        self._file_annotation = ''

    # 解析入口，返回 {Tanex Script: [语句列表], annotations: {标识符: 注解内容}}
    # 存在文件级注解（@ # 内容 #;）时，额外返回 annotation 字段
    def parse(self) -> dict:
        # 逐语句解析。注释语句在语句级处理并忽略；注解语句在语句级处理并记录；
        # 表达式语句交由 _parse_statement。
        stmts = []
        while self._pos < len(self._tokens):
            if self._pos >= len(self._tokens):
                break
            if self._peek_is(';'):
                self._advance()
                continue
            # 注释语句：仅语句级，解析后丢弃
            tok = self._peek()
            if tok and tok[0].startswith('#') and tok[0].endswith('#'):
                self._advance()
                self._expect(';')
                continue
            # 注解语句：仅语句级，解析后记录到注解表
            if tok and tok[0].startswith('@') and tok[0].endswith('#;'):
                self._parse_annotation()
                continue
            # import 语句：仅语句级
            if tok and tok[0] == 'import':
                self._advance()
                stmts.append(self._parse_import())
                continue
            stmts.append(self._parse_statement())
        result = {'Tanex Script': stmts, 'annotations': self._annotations}
        if self._file_annotation:
            result['annotation'] = self._file_annotation
        return result

    # 解析单条表达式语句（分号结尾）
    def _parse_statement(self) -> dict:
        expr = self._parse_expression(prec_min)
        self._expect(';')
        return expr

    # 解析 import 语句：import "path" ;  或  import "path" = name ;
    def _parse_import(self) -> dict:
        pos = [self._tokens[self._pos - 1][1], self._tokens[self._pos - 1][2]]
        path_tok = self._advance()
        if not (path_tok[0].startswith('"') and path_tok[0].endswith('"')):
            raise self._error('import 后应为字符串文件路径',
                path_tok[1], path_tok[2], path_tok[3])
        raw_path = path_tok[0][1:-1]
        if self._pos < len(self._tokens) and self._peek_is('='):
            self._advance()
            name_tok = self._advance()
            # 只需检查首字符：tokenizer 已保证 name token 后续字符
            # 都是合法标识符字符（数字会被拆开，如 std1 -> std + 1），
            # 这里只区分 name 与字符串/整数等其他 token
            if not (name_tok[0][0].isalpha() or name_tok[0][0] == '_'
                or ord(name_tok[0][0]) > 127):
                raise self._error('import = 后应为标识符',
                    name_tok[1], name_tok[2], name_tok[3])
            self._expect(';')
            return {'import': {'path': raw_path, 'name': name_tok[0], 'pos': pos}}
        self._expect(';')
        return {'import': {'path': raw_path, 'pos': pos}}

    # 核心 Pratt 解析：先 nud 然后循环 led（表达式内部跳过注释）
    def _parse_expression(self, min_prec: int) -> dict:
        self._skip_comments()
        if self._pos >= len(self._tokens):
            raise self._error('意外的标记: 文件结束', 0, 0)
        tok = self._advance()
        left = self._nud(tok)
        while True:
            self._skip_comments()
            if self._pos >= len(self._tokens) or self._lbp(self._peek()) <= min_prec:
                break
            tok = self._advance()
            left = self._led(left, tok)
        return left

    # 前缀解析：字面量、一元运算符、括号、代码块、列表
    def _nud(self, tok: tuple[str, int, int, str]) -> dict:
        val, line, col, f = tok
        pos = [line, col]
        # 字面量节点
        if val.isdigit():
            return {'integer': {'value': val, 'pos': pos}}
        if val.startswith('"') and val.endswith('"'):
            return {'string': {'value': val, 'pos': pos}}
        if val.startswith("'") and val.endswith("'"):
            return {'number': {'value': val, 'pos': pos}}
        # 复合结构前缀
        if val == '{':
            return self._parse_code_block(tok)
        if val == '[':
            return self._parse_list(tok)
        if val == '(':
            inner = self._parse_expression(prec_min)
            self._expect(')')
            return inner
        # break 语句
        if val == 'break':
            return {'break': {'pos': pos}}
        # 一元运算符
        rbp = _prefix_rbp.get(val)
        if rbp is not None:
            operand = self._parse_expression(rbp)
            if val == '??':
                kind = next(iter(operand))
                if kind not in ('name', 'member'):
                    raise self._error('注解运算符 ?? 后必须跟标识符或 库.成员', line, col, f)
            return {'unary': {'operator': val, 'operand': operand, 'pos': pos}}
        # 标识符
        if val[0].isalpha() or val[0] == '_' or ord(val[0]) > 127:
            return {'name': {'value': val, 'pos': pos}}
        raise self._error('意外的标记: ' + val, line, col, f)

    # 中缀解析：二元运算、索引、调用、构造、成员访问、三目、try 等
    def _led(self, left: dict, tok: tuple[str, int, int, str]) -> dict:
        val, line, col, f = tok
        real = val
        pos = [line, col]
        # 索引：a[b]
        if real == '[':
            right = self._parse_expression(prec_min)
            self._expect(']')
            return {'subscript': {'left': left, 'right': right, 'pos': pos}}
        # 函数调用：a(b, c)
        if real == '(':
            args = self._parse_items(')')
            return {'function': {'name': left, 'arg': args, 'pos': pos}}
        # 构造：A{x: 1, y: 2}
        if real == '{':
            items = self._parse_items('}')
            return {'new': {'type': left, 'include': items, 'pos': pos}}
        # 成员访问：a.b
        if real == '.':
            name_tok = self._advance()
            nv, nl, nc, nf = name_tok
            if not (nv[0].isalpha() or nv[0] == '_' or ord(nv[0]) > 127):
                raise self._error('成员名应为标识符: ' + nv, nl, nc, nf)
            right = {'name': {'value': nv, 'pos': [nl, nc]}}
            return {'member': {'left': left, 'right': right, 'pos': pos}}
        # 三目运算符：a ? b : c
        if real == '?':
            true_branch = self._parse_expression(prec_min)
            col_tok = self._advance()
            if col_tok[0] != ':':
                raise self._error('三目运算符缺少 ":"', col_tok[1], col_tok[2], col_tok[3])
            false_bp = _infix_lbp.get(real, prec_equal) - 1
            false_branch = self._parse_expression(false_bp)
            return {'ternary': {'operator': '?', 'condition': left,
                'true_branch': true_branch,
                'false_branch': false_branch, 'pos': pos}}
        # try 语句：a | e : catch | : finally
        if real == '|':
            error_arg = self._parse_expression(prec_min)
            col_tok = self._advance()
            if col_tok[0] != ':':
                raise self._error('try 语句缺少 ":"', col_tok[1], col_tok[2])
            catch_block = self._parse_expression(prec_min)
            else_block: dict | None = None
            if self._pos < len(self._tokens) and self._peek_is(':'):
                self._advance()
                else_block = self._parse_expression(
                    _infix_lbp.get(real, prec_equal) - 1)
            return {'try': {'left': left, 'error_arg': error_arg,
                'catch_block': catch_block,
                'else_block': else_block, 'pos': pos}}
        # 普通二元运算符（含赋值）
        lbp = _infix_lbp.get(real)
        if lbp is not None:
            right_bp = lbp if real not in _right_assoc else lbp - 1
            right = self._parse_expression(right_bp)
            if real == '=>':
                if next(iter(left)) != 'list':
                    raise self._error('=> 左侧必须是参数列表 [a, b, ...]',
                        tok[1], tok[2], tok[3])
                if next(iter(right)) != 'code':
                    raise self._error('=> 右侧必须是代码块 { ... }',
                        tok[1], tok[2], tok[3])
            node: dict = {'operator': real, 'left': left, 'right': right,
                'pos': pos}
            if real in ('=', '+=', '-=', '*=', '/=', '\\=',
                '%=', '^=', '&=', '|='):
                return {'assignment': node}
            return {'binary': node}
        raise self._error('意外的运算符: ' + val, line, col, f)

    # 解析代码块 { ... }，返回 code 节点
    def _parse_code_block(self, tok: tuple[str, int, int, str]) -> dict:
        pos = [tok[1], tok[2]]
        stmts = []
        while self._pos < len(self._tokens):
            self._skip_comments()
            if self._pos >= len(self._tokens) or self._peek_is('}'):
                break
            if self._peek_is(';'):
                self._advance()
                continue
            # 注解语句：仅语句级，解析后记录到注解表
            cur = self._peek()
            if cur and cur[0].startswith('@') and cur[0].endswith('#;'):
                self._parse_annotation()
                continue
            stmts.append(self._parse_statement())
        self._expect('}')
        return {'code': {'statements': stmts, 'pos': pos}}

    # 解析注解语句（@ [标识符][.{标识符}] # 内容 #;），记录注解后丢弃。
    # 新语法：@ 标识符 # 内容 #;，标识符可省略（省略时表示文件级注解，
    # 如 @ # 这是标准库 #; 即 @ 后直接 #，无标识符）。
    # 支持成员级注解：@ boolean.addition # 内容 #; 记录到 key "boolean.addition"
    def _parse_annotation(self) -> None:
        tok = self._advance()
        raw = tok[0][1:]  # 去掉开头的 '@'
        i = 0
        while i < len(raw) and raw[i] in ' \t\r\n':
            i += 1
        target = ''
        if i < len(raw) and self._is_ident_start(raw[i]):
            j = i
            while j < len(raw) and self._is_ident_continue(raw[j]):
                j += 1
            target = raw[i:j]
            # 成员级注解：允许 类型名.成员名 形式（如 boolean.addition）
            while j < len(raw) and raw[j] == '.':
                k = j + 1
                if k >= len(raw) or not self._is_ident_start(raw[k]):
                    break
                while k < len(raw) and self._is_ident_continue(raw[k]):
                    k += 1
                target += '.' + raw[j + 1:k]
                j = k
            i = j
        while i < len(raw) and raw[i] in ' \t\r\n':
            i += 1
        if i >= len(raw) or raw[i] != '#':
            raise self._error('注解语句缺少 "#" 分隔符', tok[1], tok[2], tok[3])
        content = raw[i + 1:].strip()
        # 去掉结尾的 '#;'（token 已包含结束符）
        if content.endswith('#;'):
            content = content[:-2].rstrip()
        elif content.endswith('#'):
            content = content[:-1].rstrip()
        if target:
            self._annotations[target] = content
        else:
            self._file_annotation = content

    # 判断字符能否作为标识符开头
    @staticmethod
    def _is_ident_start(ch: str) -> bool:
        return ch.isalpha() or ch == '_' or ord(ch) > 127

    # 判断字符能否在标识符中延续
    @staticmethod
    def _is_ident_continue(ch: str) -> bool:
        return parser._is_ident_start(ch)

    # 解析列表 [ ... ]，返回 list 节点
    def _parse_list(self, tok: tuple[str, int, int, str]) -> dict:
        pos = [tok[1], tok[2]]
        items = self._parse_items(']')
        return {'list': {'items': items, 'pos': pos}}

    # 解析由分隔符（,）分隔的项序列，直到遇到 closing
    def _parse_items(self, closing: str) -> list:
        items: list[dict] = []
        expect_item = True
        while self._pos < len(self._tokens):
            self._skip_comments()
            if self._pos >= len(self._tokens) or self._peek_is(closing):
                break
            if self._peek_is(','):
                if expect_item:
                    items.append(self._make_none(
                        self._tokens[self._pos]))
                self._advance()
                expect_item = True
            else:
                items.append(self._parse_expression(prec_min))
                expect_item = False
        if expect_item and items:
            items.append(self._make_none(
                self._tokens[self._pos - 1] if self._pos > 0
                else self._tokens[0]))
        if self._pos < len(self._tokens):
            self._expect(closing)
        return items

    # 跳过注释 token（以 # 开头和结尾的）
    def _skip_comments(self) -> None:
        while (self._pos < len(self._tokens)
            and self._tokens[self._pos][0].startswith('#')):
            self._pos += 1

    # 查看当前 token
    def _peek(self) -> tuple[str, int, int, str] | None:
        if self._pos < len(self._tokens):
            return self._tokens[self._pos]
        return None

    # 判断当前 token 是否为指定值
    def _peek_is(self, val: str) -> bool:
        t = self._peek()
        return t is not None and t[0] == val

    # 前进一个 token
    def _advance(self) -> tuple[str, int, int, str]:
        t = self._tokens[self._pos]
        self._pos += 1
        return t

    # 期望当前 token 为指定值，否则报错
    def _expect(self, val: str) -> tuple[str, int, int, str]:
        self._skip_comments()
        t = self._peek()
        if t is None or t[0] != val:
            suffix = t[0] if t else '文件结束'
            raise self._error('期望 "' + val + '"，但遇到 ' + suffix,
                t[1] if t else 0, t[2] if t else 0, t[3] if t else None)
        return self._advance()

    # 获取 token 的中缀优先级
    def _lbp(self, tok: tuple[str, int, int, str] | None) -> int:
        if tok is None:
            return - 1
        real = tok[0]
        return _infix_lbp.get(real, - 1)

    # 构造空值节点（用于空列表项或空参数）
    @staticmethod
    def _make_none(tok: tuple[str, int, int, str]) -> dict:
        return {'name': {'value': 'none', 'pos': [tok[1], tok[2]]}}

    # 构造解析错误
    def _error(self, msg: str, line: int, col: int, file: str | None = None):
        return tanex_script_error(
            message = msg, file = file or self._filename,
            line = line, col = col, code = 'parser',
        )
