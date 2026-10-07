# 字符串插值语法测试：
# 拍板设计（9 月 5 日）："hello {a}" 等价 "hello " + a.string；
# 花括号内为完整表达式；两端均未转义才算插值；
# \{ 与 \} 输出字面花括号；无配对 } 的裸 { 按普通字符处理。
# 实现落点：parser 把插值字符串拆成 + 拼接链，解释器零新语义（复用 string.addition）。

import json

import pytest


def _ast(source, exit_on_error = True):
    from compile.main import compile_source
    return json.loads(compile_source(source, 'main.tsuc',
        exit_on_error = exit_on_error))


def _stmt(source):
    return _ast(source)['Tanex Script'][0]


def _is_binary_plus(node):
    return 'binary' in node and node['binary']['operator'] == '+'


def test_interpolation_simple_ast():
    stmt = _stmt('x = "hello {a}";')
    right = stmt['assignment']['right']
    assert _is_binary_plus(right)
    assert right['binary']['left']['string']['value'] == '"hello "'
    assert right['binary']['right']['name']['value'] == 'a'


def test_interpolation_no_interp_ast():
    # 无插值时保持旧行为：直接返回 string 节点
    stmt = _stmt('x = "plain";')
    right = stmt['assignment']['right']
    assert 'string' in right
    assert right['string']['value'] == '"plain"'


def test_interpolation_simple_run(run_tsuc):
    source = '''*** main = [] => {
a = 42;
standard_output << "hello {a}";
};
main();'''
    assert run_tsuc(source) == 'hello 42'


def test_interpolation_multi_run(run_tsuc):
    source = '''*** main = [] => {
a = 1;
b = 2;
standard_output << "{a} and {b}";
};
main();'''
    assert run_tsuc(source) == '1 and 2'


def test_interpolation_pure_run(run_tsuc):
    # 纯插值串以空串开头拼接，结果必须是 string 类型
    source = '''*** main = [] => {
a = 42;
standard_output << "{a}";
};
main();'''
    assert run_tsuc(source) == '42'


def test_interpolation_adjacent_run(run_tsuc):
    source = '''*** main = [] => {
a = 1;
b = 2;
standard_output << "{a}{b}";
};
main();'''
    assert run_tsuc(source) == '12'


def test_interpolation_expression_run(run_tsuc):
    # 花括号内是完整表达式
    source = '''*** main = [] => {
a = 1;
b = 2;
standard_output << "{a + b}";
};
main();'''
    assert run_tsuc(source) == '3'


def test_interpolation_function_call_run(run_tsuc):
    source = '''*** main = [] => {
double = [*n] => { return n * 2; };
standard_output << "{double(21)}";
};
main();'''
    assert run_tsuc(source) == '42'


def test_interpolation_mixed_types_run(run_tsuc):
    # int 与 string 混合：string.addition 对任意值转字符串
    source = '''*** main = [] => {
a = 42;
b = "!";
standard_output << "x{a}{b}";
};
main();'''
    assert run_tsuc(source) == 'x42!'


def test_interpolation_escaped_braces_run(run_tsuc):
    # \{ 与 \} 输出字面花括号（反斜杠消失）
    source = '*** main = [] => {\nstandard_output << "\\{a\\}";\n};\nmain();'
    assert run_tsuc(source) == '{a}'


def test_interpolation_lone_brace_run(run_tsuc):
    # 无配对 } 的裸 { 按普通字符处理
    source = '*** main = [] => {\nstandard_output << "{";\n};\nmain();'
    assert run_tsuc(source) == '{'


def test_interpolation_escaped_newline_run(run_tsuc):
    # 非花括号转义原样保留
    source = '*** main = [] => {\nstandard_output << "a\\nb";\n};\nmain();'
    assert run_tsuc(source) == 'a\nb'


def test_interpolation_empty_expr_error():
    from errors import tanex_script_error
    with pytest.raises(tanex_script_error):
        _ast('x = "{}";', exit_on_error = False)


def test_interpolation_import_path_run(tmp_path, run_tsuc):
    # 用户核心场景：插值字符串作为 import 路径（运行时求值）
    lib = tmp_path / 'hello_world.tsuc'
    lib.write_text('*** msg = "hi";', encoding = 'utf-8')
    dir_path = str(tmp_path).replace('\\', '/')
    source = f'''*** main = [] => {{
# 插值路径作为 import 动态路径（运行时求值） #;
p = "{dir_path}";
import "{{p}}/hello_world.tsuc" = *hw;
standard_output << hw.msg;
}};
main();'''
    assert run_tsuc(source).strip().endswith('hi')
