# 管道运算符 |> 回归测试
# 设计：a |> f 等价于 f(a)，首参注入。右侧必须是函数引用（标识符或成员），
# 不允许带参调用形式（如 a |> f(1)），带参会按设计直接报错。
# 优先级低于函数调用；支持链式（左结合）与跨库/成员调用。
# 输出说明：standard_output << 整数按字节输出（65='A'、66='B'、64='@'）
def test_basic_first_argument_injection(run_tsuc):
    # a |> f 等价于 f(a)
    source = """*** inc = [*x] => { return x + 1; };
standard_output << (64 |> inc);"""
    assert run_tsuc(source) == 'A'


def test_chain_left_associative(run_tsuc):
    # 链式左结合：(32 |> inc) |> times_two = 66
    source = """*** inc = [*x] => { return x + 1; };
*** times_two = [*x] => { return x * 2; };
standard_output << (32 |> inc |> times_two);"""
    assert run_tsuc(source) == 'B'


def test_member_method_receiver_injection(run_tsuc):
    # 成员方法：a |> obj.f 等价于 obj.f(a)，receiver 自动注入
    source = """*** obj = type_type{};
*** obj.double = [**self, *x] => { return x * 2; };
standard_output << (32 |> obj.double);"""
    assert run_tsuc(source) == '@'


def test_cross_library_call(run_tsuc, tmp_path):
    # 跨库调用：a |> lib.f 等价于 lib.f(a)
    lib = tmp_path / 'lib.tsuc'
    lib.write_text('*** inc = [*x] => { return x + 1; };',
        encoding = 'utf-8')
    lib_path = str(lib).replace('\\', '/')
    source = f'import "{lib_path}" = *lib;\n' + \
        """standard_output << (64 |> lib.inc);"""
    assert run_tsuc(source, str(tmp_path)) == 'A'


def test_unary_binding_ok(run_tsuc):
    # 管道与一元同层：-64 先求值再注入
    source = """*** neg = [*x] => { return 0 - x; };
standard_output << (-64 |> neg);"""
    assert run_tsuc(source) == '@'


def test_priority_below_function_call(run_tsuc):
    # 管道优先级低于函数调用：右侧先解析函数引用再整体调用
    source = """*** inc = [*x] => { return x + 1; };
standard_output << (64 |> inc);"""
    assert run_tsuc(source) == 'A'


def test_call_form_rejected(run_tsuc):
    # 不允许带参调用形式 a |> f(1)
    source = """*** f = [*x] => { return x; };
5 |> f(1);"""
    from runtime.interpreter import runtime_error
    import pytest
    with pytest.raises(runtime_error):
        run_tsuc(source)


def test_non_function_right_side_rejected(run_tsuc):
    # 右侧必须是函数引用，非函数表达式报错
    source = """5 |> (1 + 2);"""
    from runtime.interpreter import runtime_error
    import pytest
    with pytest.raises(runtime_error):
        run_tsuc(source)


def test_chain_with_member_then_name(run_tsuc):
    # 混合链：32 |> obj.double |> inc = 65
    source = """*** inc = [*x] => { return x + 1; };
*** obj = type_type{};
*** obj.double = [**self, *x] => { return x * 2; };
standard_output << (32 |> obj.double |> inc);"""
    assert run_tsuc(source) == 'A'
