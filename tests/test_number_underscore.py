# 数字字面量下划线数位分隔支持测试
# 语法：integer（裸数字）与 number（单引号包裹）允许下划线作数位分隔，
#       语义与不含下划线写法一致（下划线不改变数值）。
# 非法形式：连续下划线、数字开头/结尾的下划线、小数点前后的下划线，
#           在词法/语法层报错（SystemExit）。
# 说明：standard_output << 整数按字节输出；布尔输出 true/false 字符串。
# ---- 合法：integer 下划线 ----
def test_integer_underscore_equal_plain(run_tsuc):
    # 1234_5678 与 12345678 数值一致
    source = """a = 1234_5678;
b = 12345678;
standard_output << (a == b);"""
    assert run_tsuc(source) == 'true'


def test_integer_multi_underscore_equal_plain(run_tsuc):
    # 多组分隔：12_354_23352 与 1235423352 数值一致
    source = """a = 12_354_23352;
b = 1235423352;
standard_output << (a == b);"""
    assert run_tsuc(source) == 'true'


def test_integer_underscore_arithmetic(run_tsuc):
    # 含下划线整数参与算术，语义与普通整数一致
    source = """a = 1_000 + 2_000;
standard_output << (a == 3000);"""
    assert run_tsuc(source) == 'true'


def test_integer_underscore_in_amp_decl(run_tsuc):
    # & 连续声明的数量可用含下划线 integer（返回 [start, end]，size 为 2）
    source = """a = & 1_0;
standard_output << a.size;"""
    assert run_tsuc(source) == '\x02'


# ---- 合法：number 下划线 ----

def test_number_underscore_equal_plain(run_tsuc):
    # '314_314.567_567' 与 '314314.567567' 数值一致（含小数位数语义）
    source = """a = '314_314.567_567';
b = '314314.567567';
standard_output << (a == b);"""
    assert run_tsuc(source) == 'true'


def test_number_underscore_fraction_digits(run_tsuc):
    # 小数部分下划线不改变位数语义：0.001_234 == 0.001234
    source = """a = '0.001_234';
b = '0.001234';
standard_output << (a == b);"""
    assert run_tsuc(source) == 'true'


def test_number_underscore_plain_fraction(run_tsuc):
    # 整数部分多组分隔：'1_000.5_5' 与 '1000.55' 数值一致
    source = """a = '1_000.5_5';
b = '1000.55';
standard_output << (a == b);"""
    assert run_tsuc(source) == 'true'


def test_number_underscore_negative(run_tsuc):
    # 负数 number 也支持下划线：'-1_000.5_5' 与 '-1000.55' 数值一致
    source = """a = '-1_000.5_5';
b = '-1000.55';
standard_output << (a == b);"""
    assert run_tsuc(source) == 'true'


def test_number_underscore_in_amp_decl(run_tsuc):
    # number 字面量整数值（含下划线）可用于连续声明
    source = """a = & '1_0.0';
standard_output << a.size;"""
    assert run_tsuc(source) == '\x02'


def test_number_no_underscore_regression(run_tsuc):
    # 无下划线 number 行为不变：'3.14' 可正常解析运行
    source = """a = '3.14';
standard_output << (a == '3.14');"""
    assert run_tsuc(source) == 'true'


# ---- 非法：integer 下划线 ----

def test_integer_underscore_leading_rejected(run_tsuc):
    import pytest
    with pytest.raises(SystemExit):
        run_tsuc('a = _123;')


def test_integer_underscore_trailing_rejected(run_tsuc):
    import pytest
    with pytest.raises(SystemExit):
        run_tsuc('a = 123_;')


def test_integer_underscore_double_rejected(run_tsuc):
    import pytest
    with pytest.raises(SystemExit):
        run_tsuc('a = 123___456;')


def test_integer_underscore_consecutive_rejected(run_tsuc):
    import pytest
    with pytest.raises(SystemExit):
        run_tsuc('a = 1__2;')


# ---- 非法：number 下划线 ----

def test_number_underscore_before_dot_rejected(run_tsuc):
    # 小数点前的下划线非法：'123_.1'
    import pytest
    with pytest.raises(SystemExit):
        run_tsuc("a = '123_.1';")


def test_number_underscore_after_dot_rejected(run_tsuc):
    # 小数点后的下划线非法：'234._13'
    import pytest
    with pytest.raises(SystemExit):
        run_tsuc("a = '234._13';")


def test_number_underscore_trailing_rejected(run_tsuc):
    # 数字结尾的下划线非法：'123_'
    import pytest
    with pytest.raises(SystemExit):
        run_tsuc("a = '123_';")


def test_number_underscore_leading_rejected(run_tsuc):
    # 数字开头的下划线非法：'_123'
    import pytest
    with pytest.raises(SystemExit):
        run_tsuc("a = '_123';")


def test_number_underscore_consecutive_rejected(run_tsuc):
    # 连续下划线非法：'123___456'
    import pytest
    with pytest.raises(SystemExit):
        run_tsuc("a = '123___456';")
