# $ 二元跳出（n 层返回）运算符回归测试
# 设计：中缀 `n $ value`，n 必须为正整数；信号逐层递减，n 超深报错。
# 语义分层：1 $ 等价 return；n $ 从当前层起向上跳出 n 层返回目标
#（函数、代码块、$$ 循环条件块各算一层，顶层文件也算一层）。
# 输出说明：standard_output << 整数按字节输出（88='X'、77='M'、99='c'）
def test_two_level_return_skips_middle_function(run_tsuc):
    # 2 $ 88 在内层 g 触发，穿透 f 直接返回 88
    source = """*** f = [] => {
*** g = [] => { 2 $ 88; };
return g();
};
standard_output << f();"""
    assert run_tsuc(source) == 'X'


def test_one_level_equals_return(run_tsuc):
    # 1 $ 等价 return：跳过后续语句直接返回
    source = """*** f = [] => {
1 $ 88;
return 99;
};
standard_output << f();"""
    assert run_tsuc(source) == 'X'


def test_three_level_return(run_tsuc):
    # 3 $ 77 从 h 穿透 g、f 返回 77
    source = """*** f = [] => {
*** g = [] => {
*** h = [] => { 3 $ 77; };
return h();
};
return g();
};
standard_output << f();"""
    assert run_tsuc(source) == 'M'


def test_code_block_2_penetrates_function(run_tsuc):
    # 代码块（三元分支）内 2 $ 穿透代码块与函数，直接返回 88
    source = """*** f = [] => {
1 == 1 ? { 2 $ 88; } : 0;
return 99;
};
standard_output << f();"""
    assert run_tsuc(source) == 'X'


def test_code_block_1_exits_only_block(run_tsuc):
    # 代码块内 1 $ 只退出代码块（与 return 一致），函数继续执行
    source = """*** f = [] => {
1 == 1 ? { 1 $ 88; } : 0;
return 99;
};
standard_output << f();"""
    assert run_tsuc(source) == 'c'


def test_non_integer_left_operand_error(run_tsuc):
    # bool 不是合法层数（bool 是 int 子类，需显式排除）
    source = """*** f = [] => { true $ 88; };
f();"""
    from runtime.interpreter import runtime_error
    import pytest
    with pytest.raises(runtime_error):
        run_tsuc(source)


def test_zero_depth_error(run_tsuc):
    # 层数必须 >= 1
    source = """*** f = [] => { 0 $ 88; };
f();"""
    from runtime.interpreter import runtime_error
    import pytest
    with pytest.raises(runtime_error):
        run_tsuc(source)


def test_depth_overflow_error(run_tsuc):
    # 3 层函数 + 顶层文件 = 4 层可用；5 $ 超深报错
    source = """*** f = [] => {
*** g = [] => {
*** h = [] => { 5 $ 77; };
return h();
};
return g();
};
f();"""
    from runtime.interpreter import runtime_error
    import pytest
    with pytest.raises(runtime_error):
        run_tsuc(source)


def test_top_level_n_return(run_tsuc):
    # 顶层文件也算一层：文件顶层 1 $ 把值作为文件结果（等价顶层 return）
    source = """1 $ 97;
standard_output << 98;"""
    # run_file 顶层捕获 depth=1 直接返回 97，不执行后续语句
    assert run_tsuc(source) == ''
