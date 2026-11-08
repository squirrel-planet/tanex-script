# 取地址符 * 与声明符冲突回归测试
# 语义：* 一元取地址（名字操作数）/ 连续声明（整数字面量操作数）
#       ** 引用声明、*** 常量声明、& / && / &&& 显式连续声明
# 重点验证：* 作为取地址符时，不与 ** / *** / * N 声明形式冲突
# 输出说明：standard_output << 整数按字节输出（42='*', 7='\x07', 5='\x05', 100='d'）
def test_star_addr_vs_quantity_decl(run_tsuc):
    # * 对名字是取地址，对整数字面量是连续声明，两者按操作数类型区分
    source = 'a = 42;\naddr = *a;\nstandard_output << /addr;\nb = * 3;\nstandard_output << b.size;'
    assert run_tsuc(source) == '*\x02'

def test_star_addr_spacing_insensitive(run_tsuc):
    # *a 与 * a 同为取地址，结果一致
    source = 'a = 7;\nx = *a;\ny = * a;\nstandard_output << /x;\nstandard_output << /y;'
    assert run_tsuc(source) == '\x07\x07'

def test_star_addr_on_ref_var(run_tsuc):
    # 引用变量 b 上取地址：得到 b 绑定空间的地址，解地址得原值
    source = '**b = 42;\naddr = *b;\nstandard_output << /addr;'
    assert run_tsuc(source) == '*'

def test_double_star_decl_not_split_by_star_addr(run_tsuc):
    # **b 仍是引用声明，不被 * 取地址拆成 * *b；*a 取地址 + / 解地址协作可用
    source = 'a = 7;\n**b = /(*a);\naddr = *a;\nstandard_output << /addr;\nstandard_output << /b;'
    assert run_tsuc(source) == '\x07\x07'

def test_star_addr_chain_after_ref_bind(run_tsuc):
    # a = & 3 无名空间场景：b 引用绑定 a[0]，*b 取到无名空间地址，解地址穿透
    source = 'a = & 3;\n**b = /(a[0]);\n/(a[0]) = 97;\nc = *b;\nstandard_output << /c;\nstandard_output << /(a[0]);'
    assert run_tsuc(source) == 'aa'

def test_triple_star_const_vs_star_addr(run_tsuc):
    # ***k 常量声明与 *k 取地址并存：取地址后解地址回读原值
    source = '***k = 5;\naddr = *k;\nstandard_output << /addr;'
    assert run_tsuc(source) == '\x05'
