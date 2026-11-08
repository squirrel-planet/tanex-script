# 连续声明一元运算符回归测试：& / && / &&&
# 语法：`& N` 声明 N 个普通连续空间（等价 `* N`）
#       `&& N` 声明 N 个引用连续空间（等价 `** N`）
#       `&&& N` 声明 N 个常量连续空间（等价 `*** N`）
# 注意：&& 在二元位置仍是 bool and（and 关键词等价）；一元位置才是连续声明
# 限制：操作数必须是 integer/number 字面量；`& a`（名字）语法层报错。
# 输出说明：standard_output << 整数按字节输出（2='\x02'）
def test_amp_quantity_decl_explicit(run_tsuc):
    # & 3：声明 3 个普通连续空间，返回 [start, end] 两元素列表
    source = """a = & 3;
standard_output << a.size;"""
    assert run_tsuc(source) == '\x02'


def test_double_amp_quantity_decl(run_tsuc):
    # && 3：声明 3 个引用连续空间，返回 [start, end]
    source = """a = && 3;
standard_output << a.size;"""
    assert run_tsuc(source) == '\x02'


def test_triple_amp_quantity_decl(run_tsuc):
    # &&& 3：声明 3 个常量连续空间，返回 [start, end]
    source = """a = &&& 3;
standard_output << a.size;"""
    assert run_tsuc(source) == '\x02'


def test_amp_quantity_equals_legacy(run_tsuc):
    # & 3 与 * 3 行为一致（显式形式与旧形式等价）
    source = """a = & 3;
b = * 3;
standard_output << a.size;
standard_output << b.size;"""
    assert run_tsuc(source) == '\x02\x02'


def test_triple_amp_const_cells(run_tsuc):
    # &&& 声明的空间是常量：通过地址解地址写入应报错（验证 is_const 生效）
    import pytest
    source = """a = &&& 3;
b = a[0];
/b = 97;"""
    with pytest.raises(Exception):
        run_tsuc(source)


def test_amp_quantity_in_function(run_tsuc):
    # & 连续声明可出现在函数体内
    source = """*** main = [] => {
a = & 3;
standard_output << a.size;
};
main();"""
    assert run_tsuc(source) == '\x02'


def test_amp_rejects_name_operand(run_tsuc):
    # & a：a 是名字（未定义），不是数量字面量，语法层报错（SystemExit）
    import pytest
    source = """a = & a;"""
    with pytest.raises(SystemExit):
        run_tsuc(source)


def test_amp_rejects_declarator_operand(run_tsuc):
    # & * 3：& 直接接声明符的旧形式不再支持，操作数必须是整数，语法层报错
    import pytest
    source = """a = & * 3;"""
    with pytest.raises(SystemExit):
        run_tsuc(source)


def test_double_amp_binary_and(run_tsuc):
    # && 二元位置仍是 bool and（and 关键词等价），一元位置才是连续声明
    source = """a = 1 && 0;
standard_output << a;"""
    assert run_tsuc(source) == 'false'


def test_and_keyword_still_binary_and(run_tsuc):
    # and 关键词仍等价于二元 &&（bool and）
    source = """a = 1 and 0;
standard_output << a;"""
    assert run_tsuc(source) == 'false'


def test_amp_quantity_decl_legacy(run_tsuc):
    # 旧数量声明语法不受影响：* 3 仍是连续声明，返回 [start, end]
    source = """a = * 3;
standard_output << a.size;"""
    assert run_tsuc(source) == '\x02'


def test_amp_number_operand_integral(run_tsuc):
    # number 字面量整数值（'3.0'）可用于连续声明
    source = """a = & '3.0';
standard_output << a.size;"""
    assert run_tsuc(source) == '\x02'


def test_amp_number_operand_non_integral(run_tsuc):
    # number 字面量非整数值（'3.5'）报错
    import pytest
    source = """a = & '3.5';"""
    with pytest.raises(Exception):
        run_tsuc(source)


def test_ref_decl_binds_to_nameless_space(run_tsuc):
    # **b = /(a[0])：声明引用变量，绑定到 & 3 连续声明所得的无名开头空间
    # （a[0] 为地址包装，解地址得到该空间；b 即该空间）
    source = """a = & 3;
**b = /(a[0]);
/b = 97;
standard_output << /b;
standard_output << /(a[0]);"""
    assert run_tsuc(source) == 'aa'


def test_ref_decl_binds_without_predeclare(run_tsuc):
    # **b = 42：b 无需预先存在，声明引用变量并绑定到新空间
    source = """**b = 42;
standard_output << /b;"""
    assert run_tsuc(source) == '*'


def test_ref_decl_chain_same_space(run_tsuc):
    # 二次引用绑定：**c = /(b) 与 b 指向同一空间，写 c 读 b 穿透
    source = """a = & 3;
**b = /(a[0]);
**c = /(b);
/c = 100;
standard_output << /b;
standard_output << /(a[0]);"""
    assert run_tsuc(source) == 'dd'
