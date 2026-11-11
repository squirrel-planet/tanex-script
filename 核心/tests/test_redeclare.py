# 标识符重声明规则回归测试
# 语义：标识符一经 * / ** / *** 显式声明，不得改用另一种声明符重新声明
#       （否则会把普通变量静默变成引用/常量）。更换种类必须先 delete 解绑。
# 特例：单星 * 兼作「取地址」运算符，对已声明标识符一律放行，不改其种类。
#       delete 之后可任意重新声明；同一种类的重复声明允许（如 **a 重新绑定）。

import pytest

from runtime.interpreter import runtime_error

redeclare_msg = '需先 delete 再声明'

def test_var_then_const_is_rejected(run_tsuc):
    # 核心 bug：*a 之后 ***a 曾把 a 静默变成常量
    source = '*a = 1;\n***a = 2;\nstandard_output << "ok";'
    with pytest.raises(runtime_error, match = redeclare_msg):
        run_tsuc(source)

def test_var_then_const_bare_declarator_is_rejected(run_tsuc):
    # 不带赋值的裸声明符同样要拦截
    source = '*a;\n***a;\nstandard_output << "ok";'
    with pytest.raises(runtime_error, match = redeclare_msg):
        run_tsuc(source)

def test_var_then_ref_is_rejected(run_tsuc):
    source = '*a = 1;\n**a = 2;\nstandard_output << "ok";'
    with pytest.raises(runtime_error, match = redeclare_msg):
        run_tsuc(source)

def test_const_then_ref_is_rejected(run_tsuc):
    source = '***a = 1;\n**a = 2;\nstandard_output << "ok";'
    with pytest.raises(runtime_error, match = redeclare_msg):
        run_tsuc(source)

def test_ref_then_const_is_rejected(run_tsuc):
    source = '**a = 1;\n***a = 2;\nstandard_output << "ok";'
    with pytest.raises(runtime_error, match = redeclare_msg):
        run_tsuc(source)

def test_var_then_var_address_of_allowed(run_tsuc):
    # *a 后可再 *a（取地址）：b 绑定到 a 的空间，写 b 即写 a
    source = '*a = 1;\n*b = *a;\n/b = 65;\nstandard_output << a;'
    assert run_tsuc(source) == 'A'

def test_taking_address_of_const_allowed(run_tsuc):
    # 对常量取地址是合法的，不应触发重声明检查（写入常量仍由写保护拦截）
    source = '***a = 1;\n*b = *a;\nstandard_output << "ok";'
    assert run_tsuc(source) == 'ok'

def test_repeated_var_assignment_allowed(run_tsuc):
    source = '*a = 1;\n*a = 2;\nstandard_output << a;'
    assert run_tsuc(source) == '\x02'

def test_same_kind_ref_rebind_allowed(run_tsuc):
    source = '**a = 1;\n**a = 2;\nstandard_output << /a;'
    assert run_tsuc(source) == '\x02'

def test_delete_then_redeclare_as_const_allowed(run_tsuc):
    # delete 解绑后可重新声明为任意种类
    source = '*a = 1;\ndelete a;\n***a = 2;\nstandard_output << a;'
    assert run_tsuc(source) == '\x02'

def test_delete_then_redeclare_as_ref_allowed(run_tsuc):
    source = '***a = 1;\ndelete a;\n**a = 2;\nstandard_output << /a;'
    assert run_tsuc(source) == '\x02'

def test_delete_then_redeclare_as_var_allowed(run_tsuc):
    source = '***a = 1;\ndelete a;\n*a = 2;\nstandard_output << a;'
    assert run_tsuc(source) == '\x02'

def test_redeclare_const_no_longer_turns_var_readonly(run_tsuc):
    # 修复前：***a = 2 生效，随后的 a = 3 报「常量不可修改」；
    # 修复后：应在 ***a 这一步就直接拒绝。
    source = '*a = 1;\n***a = 2;\na = 3;'
    with pytest.raises(runtime_error, match = redeclare_msg):
        run_tsuc(source)
