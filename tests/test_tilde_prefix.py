# ~ 前缀（上级作用域）运算符回归测试
# 绑定力 prec_prefix_scope = 130 > 函数调用 / 成员访问 prec_postfix = 120
# 注意：裸赋值 `x = v` 在函数内新建局部变量（_resolve_or_declare 函数边界停），
#       不再沿链向上写外层 cell；更新外层需显式用 ** 引用声明。
# 输出说明：standard_output << 整数按字节输出（97='a'、98='b'、1=\x01、0=\x00）
def test_tilde_reads_parent_scope(run_tsuc):
    # 裸赋值在函数内新建局部，~x 取父作用域值
    source = """x = 97;
*** main = [] => {
x = 98;
standard_output << x;
standard_output << ~x;
};
main();"""
    assert run_tsuc(source) == 'ba'


def test_plain_assign_does_not_leak_to_parent(run_tsuc):
    # 函数内裸赋值不再沿链写外层：外层 x 保持原值
    source = """x = 97;
*** main = [] => {
x = 98;
};
main();
standard_output << x;"""
    assert run_tsuc(source) == 'a'


def test_tilde_binds_tighter_than_member(run_tsuc):
    # ~obj.member 解析为 (~obj).member：取父作用域的 obj 再访问成员
    source = """obj = [97];
*** main = [] => {
obj = [98];
standard_output << obj.index(0);
standard_output << ~obj.index(0);
};
main();"""
    assert run_tsuc(source) == 'ba'


def test_tilde_binds_tighter_than_call(run_tsuc):
    # ~f(x) 解析为 (~f)(x)：调用父作用域的 f
    source = """*** f = [] => { return 97; };
*** main = [] => {
*** f = [] => { return 98; };
standard_output << f();
standard_output << ~f();
};
main();"""
    assert run_tsuc(source) == 'ba'


def test_tilde_nested_function_parent_chain(run_tsuc):
    # ~ 只取直接父作用域（env.parent）：inner 内 ~x 取 main 作用域参数，main 内 ~x 取文件作用域
    source = """x = 97;
*** main = [*x] => {
*** inner = [] => {
standard_output << ~x;
};
inner();
standard_output << ~x;
};
main(98);"""
    assert run_tsuc(source) == 'ba'


def test_tilde_cross_library_path(run_tsuc):
    # ~standard.encoding.ascii 跨库调用全链路（解析 → 加载 → 成员链 → 调用）
    source = """import "standard" = *standard;
*** main = [] => {
standard_output << (~standard.encoding.ascii.is_digit(50) ? 1 : 0);
standard_output << (~standard.encoding.ascii.is_upper(97) ? 1 : 0);
standard_output << (~standard.encoding.ascii.is_lower(97) ? 1 : 0);
};
main();"""
    # is_digit(50)=true, is_upper(97)=false, is_lower(97)=true；整数按字节输出
    assert run_tsuc(source) == '\x01\x00\x01'
