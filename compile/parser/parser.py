import sys

sys.path.append('..')

from errors import tanex_script_error
from compile.tokenizer.tokenizer import tokenizer

# 优先级常量定义，数值越大优先级越高
prec_postfix = 120
# ~ 为上级作用域一元运算符，绑定力高于后缀（调用/索引/成员）
prec_prefix_scope = 130
prec_unary = 110
# 管道 |>：首参注入，优先级低于函数调用（prec_postfix=120），与一元同层
prec_pipe = 110
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
# $ 二元跳出：语句级最低中缀，仅高于 prec_min（0 会被 Pratt 主循环跳过）
prec_break = 1
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
    '==': prec_equal, '!=': prec_equal, '===': prec_equal,
    '?': prec_equal, '|': prec_equal,
    '&&': prec_and, 'and': prec_and,
    '||': prec_or,
    '|>': prec_pipe,
    '=>': prec_arrow,
    '=': prec_assign,
    '$': prec_break,
    '+=': prec_assign, '-=': prec_assign,
    '*=': prec_assign, '/=': prec_assign,
    '\\=': prec_assign, '%=': prec_assign,
    '^=': prec_assign, '&=': prec_assign,
    '|=': prec_assign,
}
# 前缀运算符的优先绑定能力
_prefix_rbp: dict[str, int] = {
    '$': prec_min,
    '!': prec_unary, '~': prec_prefix_scope,
    '**': prec_unary, '***': prec_unary,
    '&&': prec_unary, '&&&': prec_unary,
    '<-': prec_unary, '??': prec_unary, '&': prec_unary,
    'return': prec_min, 'delete': prec_min, 'type_of': prec_unary,
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
    # recover=True 时启用错误恢复：语句解析失败被记录后跳过该语句继续解析，
    # 最终抛出聚合异常（message 为首条错误，errors 属性为全部错误列表）；
    # 默认 False 保持原行为（首个错误立即抛出），编译流程不受影响。
    def parse(self, recover: bool = False) -> dict:
        # 逐语句解析。注释语句在语句级处理并忽略；注解语句在语句级处理并记录；
        # 表达式语句交由 _parse_statement。
        stmts = []
        recovered: list[dict] = []
        while self._pos < len(self._tokens):
            if self._pos >= len(self._tokens):
                break
            try:
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
                # import / -> 是表达式符号（前缀运算符），由 _parse_expression
                # 经 _nud 解析（import 库命名引入、-> 引入所有内容），
                # 这里走普通表达式语句
                stmts.append(self._parse_statement())
            except tanex_script_error as e:
                if not recover:
                    raise
                recovered.append({
                    'line': e.line, 'col': e.col, 'message': e.message})
                # 错误恢复可能导致连锁误报，收集上限 50 条后终止
                if len(recovered) >= 50:
                    break
                # 先定位到报错 token 再跳过：_nud 等路径抛错时可能已消费
                # 报错 token，直接 _recover_statement 会连下一条语句一起吞掉
                if e.line and e.col:
                    self._recover_at(e.line, e.col)
                self._recover_statement()
        if recovered:
            first = recovered[0]
            err = tanex_script_error(
                message = first['message'], file = self._filename,
                line = first['line'], col = first['col'], code = 'parser')
            err.errors = recovered
            raise err
        result = {'Tanex Script': stmts, 'annotations': self._annotations}
        if self._file_annotation:
            result['annotation'] = self._file_annotation
        return result

    # EOF 报错时定位到最后一个 token 的位置，避免诊断指向文件开头
    # （旧行为报 (0,0)，VSCode 中会显示在第 1 行第 1 列）。
    # tokens 为空（空文件）时回退到 (0, 0, None)。
    def _eof_pos(self) -> tuple[int, int, str | None]:
        if self._tokens:
            last = self._tokens[-1]
            return last[1], last[2], last[3]
        return 0, 0, None

    # 定位解析位置到异常报错 token（token 与异常行列均为 1-based）。
    # 报错路径（如 _nud）可能已消费报错 token，导致 self._pos 在其之后，
    # 故从头向后找第一个 (line, col) 不小于报错位置的 token。
    def _recover_at(self, line: int, col: int) -> None:
        for i in range(len(self._tokens)):
            t = self._tokens[i]
            if t[1] > line or (t[1] == line and t[2] >= col):
                self._pos = i
                return

    # 错误恢复：跳过当前语句的 token，直到语句分隔符 ';' 或 EOF；
    # 跳过时感知 () [] {} 嵌套深度，避免块内分号提前终止。
    def _recover_statement(self) -> None:
        depth = 0
        while self._pos < len(self._tokens):
            val = self._tokens[self._pos][0]
            if val in ('{', '[', '('):
                depth += 1
            elif val in ('}', ']', ')'):
                if depth == 0:
                    break
                depth -= 1
            elif val == ';' and depth == 0:
                self._advance()
                return
            self._pos += 1

    # 解析单条表达式语句（分号结尾）
    def _parse_statement(self) -> dict:
        expr = self._parse_expression(prec_min)
        self._expect(';')
        return expr

    # 解析 import 表达式（库命名引入，表达式符号，与 -> 语义分离）：
    #   单条: import <expr>;           import <expr> = *name;
    #   列表: import [<expr>, ...];    import [<expr>, ...] = [*n1, *n2, ...];
    # 操作数是任意表达式（运行时求值为字符串路径或字符串路径列表），
    # 命名的 name 为静态标识符；命名引入右值必须是地址引用（* 前缀），
    # 裸标识符（import "xxx" = std）解析时报错。
    # AST 统一为
    # {"import": {"path": <表达式AST>, "name": <标识符或null|标识符列表>,
    #             "by_ref": <bool|null|bool列表>, "pos": [l,c]}}
    def _parse_import_expr(self, tok: tuple[str, int, int, str]) -> dict:
        pos = [tok[1], tok[2]]
        # 操作数右绑定优先级设为 prec_assign + 1：比赋值高一级，
        # 允许吞掉更高级运算符（如 + 拼接），但停在 '=' 前，
        # 避免 import <expr> = name; 的命名 '=' 被操作数吞掉
        operand = self._parse_expression(prec_assign + 1)
        kind = next(iter(operand))
        name = None
        by_ref = None
        if self._peek_is('='):
            self._advance()
            if kind == 'list':
                name, by_ref = self._parse_import_name_list()
            else:
                # = 后必须是 * 前缀（地址引用绑定）。
                # 裸标识符（import "xxx" = std）会报错，提示改用地址引用写法。
                if self._peek_is('*'):
                    self._advance()
                    by_ref = True
                else:
                    name_tok = self._peek()
                    if (name_tok[0][0].isalpha() or name_tok[0][0] == '_'
                        or ord(name_tok[0][0]) > 127):
                        raise self._error(
                            'import 命名引入右值只能是地址引用: '
                            '要么提前声明变量后取地址（import "xxx" = *std），'
                            '要么直接写 import "xxx" = *xxx',
                            name_tok[1], name_tok[2], name_tok[3])
                    raise self._error('import = 后应为标识符（可带 * 前缀）',
                        name_tok[1], name_tok[2], name_tok[3])
                name_tok = self._advance()
                if not (name_tok[0][0].isalpha() or name_tok[0][0] == '_'
                    or ord(name_tok[0][0]) > 127):
                    raise self._error('import = 后应为标识符（可带 * 前缀）',
                        name_tok[1], name_tok[2], name_tok[3])
                name = name_tok[0]
        # 列表形式校验：路径列表不能为空、名称数量与路径数量一致
        if kind == 'list':
            items = operand['list']['items']
            if not items:
                raise self._error('import 列表引入: 路径列表不能为空',
                    tok[1], tok[2], tok[3])
            if isinstance(name, list) and len(name) != len(items):
                raise self._error(
                    f'import 列表引入: 名称数量 ({len(name)}) '
                    f'与路径数量 ({len(items)}) 不一致',
                    tok[1], tok[2], tok[3])
        return {'import': {'path': operand, 'name': name,
            'by_ref': by_ref, 'pos': pos}}

    # 解析 -> 表达式（引入文件所有内容，表达式符号，与 import 语义分离）：
    #   -> <expr>;              （单文件，运行时求值为字符串路径）
    #   -> [<expr>, ...];       （多文件：依次引入每个文件的所有内容）
    # 语义：不打包为 library，把目标文件的顶层声明全部展开到当前作用域；
    # 展开后若与当前作用域存在同名标识符，产生警告（不静默覆盖、不报致命错误）。
    # -> 不再支持命名引入（= name / = *name 均报错，请改用 import 关键字）。
    # 操作数右绑定优先级设为 prec_assign + 1：允许吞掉更高级运算符
    # （如 + 拼接），但停在 '=' 前，便于检测命名写法并给出明确提示。
    # AST 统一为 {"include": {"path": <表达式AST>, "pos": [l,c]}}
    def _parse_include_expr(self, tok: tuple[str, int, int, str]) -> dict:
        pos = [tok[1], tok[2]]
        operand = self._parse_expression(prec_assign + 1)
        kind = next(iter(operand))
        if self._peek_is('='):
            raise self._error(
                '-> 已不再支持命名引入（= name / = *name），'
                '语义已改为引入文件所有内容到当前作用域；'
                '如需库命名引入请使用 import 关键字',
                tok[1], tok[2], tok[3])
        if kind == 'list':
            items = operand['list']['items']
            if not items:
                raise self._error('-> 引入列表: 路径列表不能为空',
                    tok[1], tok[2], tok[3])
        return {'include': {'path': operand, 'pos': pos}}

    # 解析 import 命名列表 [ *n1, *n2, ... ]，
    # 元素必须是带 * 前缀的静态标识符（地址引用绑定），
    # 裸标识符元素（[n1, n2]）直接报错。
    # 返回 (标识符字符串列表, 引用绑定标记列表)
    def _parse_import_name_list(self) -> tuple[list[str], list[bool]]:
        self._expect('[')
        names: list[str] = []
        by_refs: list[bool] = []
        while True:
            self._skip_comments()
            if self._peek_is(']'):
                self._advance()
                return names, by_refs
            # 元素必须带 * 前缀（地址引用绑定），裸标识符元素直接报错
            if self._peek_is('*'):
                self._advance()
                by_ref = True
            else:
                name_tok = self._peek()
                if (name_tok[0][0].isalpha() or name_tok[0][0] == '_'
                    or ord(name_tok[0][0]) > 127):
                    raise self._error(
                        'import 名称列表: 元素应为地址引用（带 * 前缀）: '
                        'import ["path1", "path2"] = [*n1, *n2]',
                        name_tok[1], name_tok[2], name_tok[3])
                raise self._error(
                    'import 名称列表: 元素应为标识符（可带 * 前缀）',
                    name_tok[1], name_tok[2], name_tok[3])
            name_tok = self._advance()
            if not (name_tok[0][0].isalpha() or name_tok[0][0] == '_'
                or ord(name_tok[0][0]) > 127):
                raise self._error('import 名称列表: 元素应为标识符（可带 * 前缀）',
                    name_tok[1], name_tok[2], name_tok[3])
            names.append(name_tok[0])
            by_refs.append(by_ref)
            self._skip_comments()
            if self._peek_is(','):
                self._advance()

    # 核心 Pratt 解析：先 nud 然后循环 led（表达式内部跳过注释）
    def _parse_expression(self, min_prec: int) -> dict:
        self._skip_comments()
        if self._pos >= len(self._tokens):
            line, col, f = self._eof_pos()
            raise self._error('意外的标记: 文件结束', line, col, f)
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
        # 整数允许下划线数位分隔（tokenizer 已校验合法形式，如 123_456）
        if val[0].isdigit() and val.replace('_', '').isdigit():
            return {'integer': {'value': val, 'pos': pos}}
        if val.startswith('"') and val.endswith('"'):
            return self._parse_string_literal(val, pos)
        if val.startswith("'") and val.endswith("'"):
            return {'number': {'value': val, 'pos': pos}}
        # 复合结构前缀
        if val == '{':
            return self._parse_brace_or_code(tok)
        if val == '[':
            return self._parse_list(tok)
        if val == '(':
            # 括号表达式：消费 '(' 后对内部做完整表达式解析（不是单个 factor），
            # 消费 ')' 后生成 Brackets 节点，保留左括号的 line/col 供报错定位；
            # 无括号的表达式仍走原 Expression 节点路径。
            inner = self._parse_expression(prec_min)
            self._expect(')')
            return {'brackets': {'expr': inner, 'pos': pos}}
        # break 语句（零元运算符，无操作数）
        if val == 'break':
            return {'break': {'pos': pos}}
        # contiune 语句（零元运算符，无操作数，跳出当前迭代）
        if val == 'contiune':
            return {'contiune': {'pos': pos}}
        # import 动态引入（表达式符号，前缀解析）：语义保持不变
        if val == 'import':
            return self._parse_import_expr(tok)
        # -> 引入文件所有内容（表达式符号，前缀解析）：与 import 语义分离，
        # 不再表示 import（打包为 library），而是展开全部顶层声明到当前作用域
        if val == '->':
            return self._parse_include_expr(tok)
        # 一元运算符
        rbp = _prefix_rbp.get(val)
        if rbp is not None:
            operand = self._parse_expression(rbp)
            if val == '??':
                kind = next(iter(operand))
                if kind not in ('name', 'member'):
                    raise self._error('注解运算符 ?? 后必须跟标识符或 库.成员', line, col, f)
            if val == 'delete':
                kind = next(iter(operand))
                if kind not in ('name', 'member', 'subscript'):
                    raise self._error('delete 后必须跟标识符、成员或下标', line, col, f)
            if val in ('&', '&&', '&&&'):
                if next(iter(operand)) not in ('integer', 'number'):
                    raise self._error('连续声明操作数必须是整数', line, col, f)
            return {'unary': {'operator': val, 'operand': operand, 'pos': pos}}
        # and 是二元逻辑与关键词，禁止作前缀（防止与一元 && 连续声明混淆）
        if val == 'and':
            raise self._error('and 是二元逻辑与运算符，不能用作前缀', line, col, f)
        # 标识符
        if val[0].isalpha() or val[0] == '_' or ord(val[0]) > 127:
            return {'name': {'value': val, 'pos': pos}}
        raise self._error('意外的标记: ' + val, line, col, f)

    # 字符串字面量解析：支持花括号插值 "{expr}"。
    # 设计（9 月 5 日拍板）：
    #   "hello {a}" 等价 "hello " + a.string；花括号内为完整表达式。
    #   转义规则：两端均未转义才算插值；\{ 与 \} 输出字面花括号（反斜杠消失）。
    #   无配对 } 的裸 { 按普通字符处理。
    # 无插值时行为与旧版完全一致（原样返回 string 节点，解释器零新语义）。
    def _parse_string_literal(self, val: str, pos: list) -> dict:
        inner = val[1:-1]
        segments = self._scan_string_segments(inner, pos)
        if not segments:
            return {'string': {'value': val, 'pos': pos}}
        if len(segments) == 1 and segments[0][0] == 'str':
            data = segments[0][1]
            # 无 \{ \} 转换时原样返回，与旧版行为完全一致；
            # 有字面花括号转义时按片段构造 value（\{ -> {、\} -> }）
            if data == inner:
                return {'string': {'value': val, 'pos': pos}}
            return {'string': {'value': '"' + data + '"', 'pos': pos}}
        nodes: list[dict] = []
        for seg in segments:
            if seg[0] == 'str':
                nodes.append({'string': {'value': '"' + seg[1] + '"',
                    'pos': pos}})
            else:
                el, ec = self._advance_pos(pos[0], pos[1] + 1, inner[:seg[2]])
                nodes.append(self._parse_interpolated_expr(seg[1], el, ec))
        # 串以插值开头（首节点非 string 字面量）时补空串，保证结果始终为 string
        if next(iter(nodes[0])) != 'string':
            nodes.insert(0, {'string': {'value': '""', 'pos': pos}})
        acc = nodes[0]
        for nd in nodes[1:]:
            acc = {'binary': {'operator': '+', 'left': acc, 'right': nd,
                'pos': pos}}
        return acc

    # 扫描字符串内容（不含外层引号），拆分为交替的字符串片段与插值表达式源码。
    # 返回 [('str', 片段字符), ('expr', 表达式源码), ...]。
    # 规则：\{ 输出字面 {；\} 输出字面 }；其余 \x 原样保留（保留转义语义）；
    #       裸 { 向后找配对的裸 }（跳过转义与表达式内字符串，嵌套 { 计深度），
    #       找到则进入插值段；找不到则 { 按普通字符处理。
    def _scan_string_segments(self, inner: str, pos: list) -> list:
        segments: list = []
        cur: list[str] = []
        i = 0
        n = len(inner)
        while i < n:
            ch = inner[i]
            if ch == '\\':
                if i + 1 < n:
                    nxt = inner[i + 1]
                    if nxt == '{' or nxt == '}':
                        cur.append(nxt)
                    else:
                        cur.append(ch)
                        cur.append(nxt)
                    i += 2
                else:
                    cur.append(ch)
                    i += 1
            elif ch == '{':
                j = i + 1
                depth = 1
                in_str = False
                while j < n:
                    c = inner[j]
                    if c == '\\':
                        j += 2
                        continue
                    if in_str:
                        if c == '"':
                            in_str = False
                        j += 1
                        continue
                    if c == '"':
                        in_str = True
                        j += 1
                        continue
                    if c == '{':
                        depth += 1
                    elif c == '}':
                        depth -= 1
                        if depth == 0:
                            break
                    j += 1
                if depth == 0:
                    if cur:
                        segments.append(('str', ''.join(cur), 0))
                        cur = []
                    expr_src = inner[i + 1:j]
                    if not expr_src.strip():
                        raise self._error('插值表达式不能为空',
                            pos[0], pos[1])
                    segments.append(('expr', expr_src, i + 1))
                    i = j + 1
                    continue
                cur.append(ch)
                i += 1
            else:
                cur.append(ch)
                i += 1
        if cur:
            segments.append(('str', ''.join(cur), 0))
        return segments

    # 将插值表达式源码重新分词并解析为表达式 AST，并把节点 pos 平移到原文坐标
    def _parse_interpolated_expr(self, src: str, line: int, col: int) -> dict:
        if not src.strip():
            raise self._error('插值表达式不能为空', line, col)
        tk = tokenizer(src, filename = self._filename)
        toks = tk.tokenize()
        if not toks:
            raise self._error('插值表达式不能为空', line, col)
        sub = parser(toks)
        expr = sub._parse_expression(prec_min)
        self._shift_node_pos(expr, line - 1, col - 1)
        return expr

    # 递归平移 AST 节点的 pos（dict 中 'pos': [line, col]）：
    # 行号整体加 dl；仅片段首行（原行号 1）的列号加 dc，
    # 跨行片段后续行的列保持片段内相对值。
    def _shift_node_pos(self, node, dl: int, dc: int) -> None:
        if isinstance(node, dict):
            for k, v in list(node.items()):
                if k == 'pos' and isinstance(v, list) and len(v) == 2:
                    orig_line = v[0]
                    v[0] += dl
                    if orig_line == 1:
                        v[1] += dc
                else:
                    self._shift_node_pos(v, dl, dc)
        elif isinstance(node, list):
            for item in node:
                self._shift_node_pos(item, dl, dc)

    # 从 (line, col) 出发前进 offset 个字符（跨行感知），返回新的 (line, col)
    @staticmethod
    def _advance_pos(line: int, col: int, text: str) -> tuple:
        for ch in text:
            if ch == '\n':
                line += 1
                col = 1
            else:
                col += 1
        return line, col

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
            if self._pos >= len(self._tokens):
                raise self._error('成员名应为标识符: 文件结束', line, col, f)
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
            node: dict = {'operator': '&&' if real == 'and' else real,
                'left': left, 'right': right,
                'pos': pos}
            if real in ('=', '+=', '-=', '*=', '/=', '\\=',
                '%=', '^=', '&=', '|='):
                if next(iter(left)) == 'list':
                    raise self._error('无效的赋值目标', line, col, f)
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

    # 裸花括号解析：先试探是否为 {k: v, k2: v2, ...} 字典字面量；
    # 若不存在顶层 ':' 或解析中途失败则回退为代码块 code 语义。
    # 空 {} 维持代码块语义（空字典需用 dictionary{} 构造）。
    def _parse_brace_or_code(self, tok: tuple[str, int, int, str]) -> dict:
        pos = [tok[1], tok[2]]
        if self._peek_is('}'):
            return self._parse_code_block(tok)
        saved = self._pos
        try:
            first_key = self._parse_expression(prec_min)
        except Exception:
            self._pos = saved
            return self._parse_code_block(tok)
        if not self._peek_is(':'):
            self._pos = saved
            return self._parse_code_block(tok)
        # 确认是字典字面量，后续错误直接抛出（错误信息清晰）
        # 消费 ':'
        self._advance()
        items = [[first_key, self._parse_expression(prec_min)]]
        while self._pos < len(self._tokens):
            self._skip_comments()
            if self._peek_is('}'):
                break
            if not self._peek_is(','):
                t = self._peek()
                suffix = t[0] if t else '文件结束'
                if t is None:
                    line, col, f = self._eof_pos()
                else:
                    line, col, f = t[1], t[2], t[3]
                raise self._error('期望 "," 或 "}"，但遇到 ' + suffix,
                    line, col, f)
            # 消费 ','
            self._advance()
            self._skip_comments()
            if self._peek_is('}'):
                raise self._error('期望键值对，但遇到 "}"',
                    self._tokens[self._pos][1],
                    self._tokens[self._pos][2],
                    self._tokens[self._pos][3])
            key = self._parse_expression(prec_min)
            if not self._peek_is(':'):
                t = self._peek()
                suffix = t[0] if t else '文件结束'
                if t is None:
                    line, col, f = self._eof_pos()
                else:
                    line, col, f = t[1], t[2], t[3]
                raise self._error('期望 ":"，但遇到 ' + suffix,
                    line, col, f)
            # 消费 ':'
            self._advance()
            value = self._parse_expression(prec_min)
            items.append([key, value])
        self._expect('}')
        return {'dictionary_literal': {'items': items, 'pos': pos}}

    # 解析注解语句（@ [标识符][.{标识符}] # 内容 #;），记录注解后丢弃。
    # 新语法：@ 标识符 # 内容 #;，标识符可省略（省略时表示文件级注解，
    # 如 @ # 这是标准库 #; 即 @ 后直接 #，无标识符）。
    # 支持成员级注解：@ boolean.addition # 内容 #; 记录到 key "boolean.addition"
    def _parse_annotation(self) -> None:
        tok = self._advance()
        # 去掉开头的 '@'
        raw = tok[0][1:]
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
            raise self._error('注解语句缺少 "#"', tok[1], tok[2], tok[3])
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
            if t is None:
                line, col, f = self._eof_pos()
            else:
                line, col, f = t[1], t[2], t[3]
            raise self._error('期望 "' + val + '"，但遇到 ' + suffix,
                line, col, f)
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
