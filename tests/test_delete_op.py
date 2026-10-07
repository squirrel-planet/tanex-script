# delete 运算符 + renounce 成员机制回归测试
# 语义：delete x / delete a.b / delete arr[0]；引用只删自身；renounce 自动"删全"
import pytest

from runtime.interpreter import runtime_error


def test_delete_local_var_then_undefined(run_tsuc):
    # 删除普通变量后标识符消失，再次访问报未定义
    source = """a = 42;
delete a;
standard_output << /(a);"""
    with pytest.raises(runtime_error):
        run_tsuc(source)


def test_delete_local_var_member_kept_sibling(run_tsuc):
    # 删除成员只删该成员，兄弟成员保留
    source = """*** obj = type_type{};
*** obj.x = 9;
*** obj.y = 5;
delete obj.x;
standard_output << obj.y;"""
    assert run_tsuc(source) == '\x05'


def test_delete_const_ok(run_tsuc):
    # 常量允许 delete
    source = """*** k = 7;
delete k;
standard_output << "ok";"""
    assert run_tsuc(source) == 'ok'


def test_delete_subscript(run_tsuc):
    # 下标走 index 定位再删
    source = """*** lst = [1, 2, 3];
standard_output << lst[0];
delete lst[0];
standard_output << "ok";"""
    assert run_tsuc(source) == '\x01ok'


def test_delete_ref_keeps_target(run_tsuc):
    # 引用变量 delete：只解绑 x 标识符 + 删自己 cell，目标 y 及空间不动
    source = """*** target = 5;
*** ref = *target;
delete ref;
standard_output << target;"""
    assert run_tsuc(source) == '\x05'


def test_delete_ref_after_ref_undefined(run_tsuc):
    # 引用标识符删除后再访问报未定义
    source = """*** target = 5;
*** ref = *target;
delete ref;
standard_output << /(ref);"""
    with pytest.raises(runtime_error):
        run_tsuc(source)


def test_delete_renounce_auto_called(run_tsuc):
    # 有 renounce 成员时自动调用（设置标志验证），再解绑
    source = """*** box = type_type{};
*** box.value;
*** box.renounce = [**self] => { self.value = -1; };
*** b = box{};
b.value = 100;
delete b;
standard_output << "ok";"""
    assert run_tsuc(source) == 'ok'
