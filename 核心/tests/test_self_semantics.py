# *self 值传递 / **self 引用传递语义测试：
# 形参 [*v] 是值传递（深拷贝副本），[**v] 是引用传递（写回原实例）。
# 实例方法内部写自身成员一律使用 [**self]；普通读取使用 [*self]。
def test_value_param_is_copy(run_tsuc):
    # * 值传递：函数内 append 作用于副本，外部 size 不变
    source = '*** f = [*v] => {\nv.append(98);\n};\n*** main = [] => {\nx = [97];\nf(x);\nstandard_output << x.size;\n};\nmain();'
    assert run_tsuc(source) == '\x01'

def test_ref_param_writes_original(run_tsuc):
    # ** 引用传递：函数内 append 写回原实例，外部 size 增加
    source = '*** g = [**v] => {\nv.append(98);\n};\n*** main = [] => {\nx = [97];\ng(x);\nstandard_output << x.size;\n};\nmain();'
    assert run_tsuc(source) == '\x02'

def test_list_append_writes_member(run_tsuc):
    # list.append 内部用 [**self]，size 与链头均写回
    source = 'x = [];\n*** main = [] => {\nx.append(1);\nx.append(2);\nstandard_output << x.size;\n};\nmain();'
    assert run_tsuc(source) == '\x02'

def test_list_delete_end_writes_member(run_tsuc):
    source = 'x = [97, 98];\n*** main = [] => {\nx.delete_end();\nstandard_output << x.size;\n};\nmain();'
    assert run_tsuc(source) == '\x01'

def test_list_index_set_writes_node(run_tsuc):
    # 下标取元素后原地修改必须写回（index_set 内部使用 **self）
    source = 'x = [97];\n*** main = [] => {\nx.index_set(0, 9);\nstandard_output << x.index(0);\n};\nmain();'
    assert run_tsuc(source) == '\t'

def test_dictionary_insert_writes_members(run_tsuc):
    # dictionary 未命中分支重建 buckets 写回，插入对原实例可见
    source = 'd = dictionary{};\n*** main = [] => {\nd.index_set(1, 10);\nstandard_output << d.index(1);\n};\nmain();'
    assert run_tsuc(source) == '\n'

def test_string_push_char_writes_member(run_tsuc):
    source = 's = string{};\n*** main = [] => {\ns.push_char(97);\ns.push_char(98);\nstandard_output << s.string();\n};\nmain();'
    assert run_tsuc(source) == 'ab'
