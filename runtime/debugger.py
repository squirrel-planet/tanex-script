# 断点调试器

import os
import json
from errors import warning
from errors import output_message
from errors import print_error_brief
from compile.main import compile_source
from runtime.values import runtime_error

# 静默语句：求值后不输出结果（赋值/import/解地址一元运算）
def _is_silent_statement(stmt) -> bool:
    kind = next(iter(stmt))
    if kind in ('assignment', 'import'):
        return True
    if kind == 'unary':
        return stmt['unary']['operator'] in ('*', '**', '***', '&', '&&', '&&&')
    return False

class debugger(object):
    def __init__(self, interp, break_lines, main_source):
        self.interp = interp
        self.main_source = main_source
        self.step_pending = False
        # 断点行号按预处理行映射换算为 AST 实际行号
        self._break_lines = self._resolve_break_lines(break_lines)

    # 重建预处理行映射，把源文件断点行号换算为 AST 实际行号
    def _resolve_break_lines(self, break_lines):
        tsuc = self.main_source
        if not tsuc.endswith('.tsuc') or not os.path.exists(tsuc):
            return set(break_lines)
        try:
            from compile.tokenizer import tokenizer
            from compile.preprocessor import preprocessor
            with open(tsuc, 'r', encoding = 'utf-8') as f:
                source = f.read()
            tokens = tokenizer(source, tsuc).tokenize()
            pp = preprocessor(tokens, tsuc)
            pp.process()
        except Exception as e:
            warning([f'无法重建源码行映射，断点按原行号匹配: {e}'])
            return set(break_lines)
        # (文件, 原始行) -> 解析后行号
        reverse = {}
        main_key = os.path.normcase(os.path.basename(tsuc))
        for resolved, (file, original) in pp._source_map._map.items():
            key = (os.path.normcase(os.path.basename(file)), original)
            if key not in reverse:
                reverse[key] = resolved
        result = set()
        for line in break_lines:
            resolved = reverse.get((main_key, line), line)
            result.add(resolved)
        return result

    # 是否检查断点：仅主文件源码，避免库加载误断
    def should_check(self, file) -> bool:
        if not file:
            return False
        return os.path.normcase(os.path.basename(file)) == \
            os.path.normcase(os.path.basename(self.main_source))

    # 语句循环顶部调用：命中断点或单步模式时进入交互
    def maybe_break(self, stmt, env):
        if self.step_pending:
            self.step_pending = False
            self._interact(env, self._stmt_pos(stmt))
            return
        if not self._break_lines:
            return
        pos = self._stmt_pos(stmt)
        if pos is None:
            return
        if pos[0] in self._break_lines \
                and self.should_check(self.interp._current_file):
            self._interact(env, pos)

    # 取语句起始位置
    def _stmt_pos(self, stmt):
        kind = next(iter(stmt))
        inner = stmt[kind]
        if isinstance(inner, dict):
            return inner.get('pos')
        return None

    # 显示断点位置与当前语句源码
    def _show_location(self, pos):
        line, col = pos[0], pos[1]
        lines = [f'[断点] 文件: {self.main_source}  第 {line} 行 第 {col} 列']
        code = self._source_line(line)
        if code is not None:
            lines.append(f'    {line} | {code}')
        return lines

    # 读取源文件指定行
    def _source_line(self, line):
        if not self.main_source.endswith('.tsuc'):
            return None
        try:
            with open(self.main_source, 'r', encoding = 'utf-8') as f:
                lines = f.read().split('\n')
        except OSError:
            return None
        if 1 <= line <= len(lines):
            return lines[line - 1]
        return None

    # 主交互循环
    def _interact(self, env, pos):
        while True:
            output_message(self._show_location(pos), False, suppressible = False)
            output_message(
                ['操作: 1 表达式(e)  2 下一句(n)  3 继续(c)  4 退出调试(q)'],
                False,
                suppressible = False)
            try:
                choice = input().strip()
            except (EOFError, KeyboardInterrupt):
                choice = '3'
            if choice in ('1', 'e', '表达式'):
                self._expression_mode(env)
            elif choice in ('2', 'n', '下一句'):
                self.step_pending = True
                return
            elif choice in ('3', 'c', '继续'):
                return
            elif choice in ('4', 'q', '退出'):
                # 退出调试：清空断点后跑完剩余代码
                self._break_lines = set()
                self.step_pending = False
                return
            else:
                output_message(['无效操作，请重新输入'], False, suppressible = False)

    # 表达式模式：输入一个表达式求值后返回主菜单
    def _expression_mode(self, env):
        try:
            text = input().strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not text:
            return
        self._eval_expression(env, text)

    # 在断点作用域内编译并求值表达式
    def _eval_expression(self, env, text):
        text = text.strip()
        if not text:
            return
        # 表达式语句需要分号结尾，自动补齐
        if not text.endswith(';'):
            text = text + ';'
        try:
            ast = json.loads(compile_source(
                text, '<debug>', exit_on_error = False))
        except Exception as e:
            print_error_brief(e, text)
            return
        statements = ast['Tanex Script']
        try:
            result = None
            for stmt in statements:
                result = self.interp.eval_node(stmt, env)
        except Exception as e:
            if isinstance(e, runtime_error):
                e.annotate(self.interp._current_file, self.interp._current_pos)
            print_error_brief(e, text)
            return
        if not statements:
            return
        if not _is_silent_statement(statements[-1]):
            output_message(
                [self.interp._display_string(result)], False, suppressible = False)
