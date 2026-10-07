# import 引用绑定语义测试：
# 推荐 `import <路径> = *name`（传地址引用绑定），
# 绑定结果为引用库实例本身，访问方式为 `库名.成员`。
# 命名引入右值只能是地址引用（* 前缀）：
#   - 裸标识符右值（import "xxx" = std）必须报错；
#   - 提前声明变量后取地址（import "xxx" = *std）合法；
#   - 直接写新声明地址（import "xxx" = *xxx）合法。
# 裸名引入（import "xxx"; 不带 = 改名，默认取路径最后一段为名）。
# 注：-> 已改为"引入文件所有内容到当前作用域"，不再支持命名/引用绑定；

import json

def _write_lib(tmp_path, name, value):
    # 在临时目录写一个最小 tsuc 库文件，返回正斜杠绝对路径
    lib = tmp_path / name
    lib.write_text(f'*** lib_value = {value};', encoding = 'utf-8')
    return str(lib).replace('\\', '/')


def test_import_single_star_name_ast(tmp_path):
    from compile.main import compile_source
    lib = _write_lib(tmp_path, 'lib.tsuc', 42)
    source = f'import "{lib}" = *lib;'
    data = json.loads(compile_source(source, str(tmp_path / 'main.tsuc')))
    imports = [s for s in data['Tanex Script'] if 'import' in s]
    star = [i for i in imports if i['import'].get('name') == 'lib'
        and i['import'].get('by_ref') is True]
    assert star, f'缺少 by_ref=true 的 import 节点: {imports}'


def test_import_single_star_name_run(tmp_path, run_tsuc):
    lib = _write_lib(tmp_path, 'lib.tsuc', 42)
    source = f'import "{lib}" = *lib;\n' + """*** main = [] => {
standard_output << lib.lib_value;
};
main();"""
    assert run_tsuc(source, str(tmp_path)) == '*'


def test_import_bare_name_rhs_error(tmp_path):
    # 命名引入右值为裸标识符（import "xxx" = std）必须报错，
    # 提示右值只能是地址引用（* 前缀）
    import pytest
    from compile.main import compile_source
    lib = _write_lib(tmp_path, 'lib.tsuc', 42)
    source = f'import "{lib}" = std;'
    with pytest.raises(Exception) as ei:
        compile_source(source, str(tmp_path / 'main.tsuc'), exit_on_error=False)
    msg = str(ei.value)
    assert '右值只能是地址引用' in msg
    assert '*std' in msg or '*xxx' in msg


def test_import_list_bare_name_rhs_error(tmp_path):
    # 名称列表元素为裸标识符（[la]）必须报错，提示元素应为地址引用
    import pytest
    from compile.main import compile_source
    lib = _write_lib(tmp_path, 'lib.tsuc', 42)
    source = f'import ["{lib}"] = [la];'
    with pytest.raises(Exception) as ei:
        compile_source(source, str(tmp_path / 'main.tsuc'), exit_on_error=False)
    msg = str(ei.value)
    assert '地址引用' in msg and '*n' in msg


def test_import_star_name_new_decl_run(tmp_path, run_tsuc):
    # 直接写新声明地址写法（import "xxx" = *xxx）仍然合法
    lib = _write_lib(tmp_path, 'lib.tsuc', 42)
    source = f'import "{lib}" = *xxx;\n' + """*** main = [] => {
standard_output << xxx.lib_value;
};
main();"""
    assert run_tsuc(source, str(tmp_path)).strip() == '*'


def test_import_star_name_predeclared_run(tmp_path, run_tsuc):
    # 提前声明变量后取地址放右值（import "xxx" = *std，std 已声明）仍然合法
    lib = _write_lib(tmp_path, 'lib.tsuc', 42)
    source = f'std = 0;\nimport "{lib}" = *std;\n' + """*** main = [] => {
standard_output << std.lib_value;
};
main();"""
    # std 已存在会输出覆盖警告到 stdout，只看末尾实际输出
    assert run_tsuc(source, str(tmp_path)).strip().endswith('*')


def test_import_legacy_bare_name_ast(tmp_path):
    from compile.main import compile_source
    lib = _write_lib(tmp_path, 'lib.tsuc', 42)
    source = f'import "{lib}";'
    data = json.loads(compile_source(source, str(tmp_path / 'main.tsuc')))
    imports = [s for s in data['Tanex Script'] if 'import' in s]
    assert len(imports) == 1
    assert imports[0]['import']['name'] == 'lib'


def test_import_legacy_bare_name_run(tmp_path, run_tsuc):
    lib = _write_lib(tmp_path, 'lib.tsuc', 42)
    source = f'import "{lib}";\n' + """*** main = [] => {
standard_output << lib.lib_value;
};
main();"""
    assert run_tsuc(source, str(tmp_path)) == '*'


def test_import_list_star_names_ast(tmp_path):
    from compile.main import compile_source
    lib1 = _write_lib(tmp_path, 'lib_a.tsuc', 1)
    lib2 = _write_lib(tmp_path, 'lib_b.tsuc', 2)
    source = f'import ["{lib1}", "{lib2}"] = [*la, *lb];'
    data = json.loads(compile_source(source, str(tmp_path / 'main.tsuc')))
    imports = [s for s in data['Tanex Script'] if 'import' in s]
    assert len(imports) == 1
    assert imports[0]['import']['name'] == ['la', 'lb']
    assert imports[0]['import']['by_ref'] == [True, True]


def test_import_list_star_names_run(tmp_path, run_tsuc):
    lib1 = _write_lib(tmp_path, 'lib_a.tsuc', 42)
    lib2 = _write_lib(tmp_path, 'lib_b.tsuc', 43)
    source = f'import ["{lib1}", "{lib2}"] = [*la, *lb];\n' + """*** main = [] => {
standard_output << la.lib_value;
standard_output << lb.lib_value;
};
main();"""
    # 编译期自动生成 .tscc 时可能输出警告到 stdout，只看末尾实际输出
    assert run_tsuc(source, str(tmp_path)).rstrip().endswith('*+')


# ---- -> 引入语义测试（引入文件所有内容到当前作用域） ----
# -> 不等价 import，而是把目标文件顶层标识符直接展开到当前作用域；
# 不打包为 library；与当前作用域同名标识符冲突时发出警告并覆盖（不静默、不致命）。


def test_include_bare_ast(tmp_path):
    from compile.main import compile_source
    lib = _write_lib(tmp_path, 'lib.tsuc', 42)
    source = f'-> "{lib}";'
    data = json.loads(compile_source(source, str(tmp_path / 'main.tsuc')))
    includes = [s for s in data['Tanex Script'] if 'include' in s]
    assert len(includes) == 1
    assert 'name' not in includes[0]['include']


def test_include_bare_run(tmp_path, run_tsuc):
    # -> 引入后，目标文件顶层标识符直接可用（不打包为 library）
    lib = _write_lib(tmp_path, 'lib.tsuc', 42)
    source = f'-> "{lib}";\n' + """*** main = [] => {
standard_output << lib_value;
};
main();"""
    assert run_tsuc(source, str(tmp_path)).strip() == '*'


def test_include_conflict_warning(tmp_path, run_tsuc):
    # 同名冲突：当前作用域已有 lib_value，-> 引入后应产生警告并覆盖，不报致命错误
    lib = _write_lib(tmp_path, 'lib.tsuc', 42)
    source = f'lib_value = 100;\n-> "{lib}";\n' + """*** main = [] => {
standard_output << lib_value;
};
main();"""
    out = run_tsuc(source, str(tmp_path))
    # 警告信息出现在输出中，且最终运行成功（末尾输出 42 的字符 *）
    assert '同名标识符' in out or '覆盖' in out
    assert out.strip().endswith('*')
