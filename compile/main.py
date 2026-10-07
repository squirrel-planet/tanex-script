import os
import json
from errors import error
from errors import tanex_script_error
from compile.preprocessor import preprocessor
from compile.tokenizer import tokenizer
from compile.parser import parser

def compile_source(source: str, file_path: str, exit_on_error: bool = True,
    output_mode: str = 'standard') -> str:
    try:
        tok = tokenizer(source, file_path)
        tokens = tok.tokenize()
        pp = preprocessor(tokens, file_path)
        pp_result = pp.process()
        merged_tokens = pp_result.tokens
        p = parser(merged_tokens)
        ast = p.parse()
        ast['dependencies'] = list(pp_result.dependencies)
        return _serialize_ast(ast, output_mode)
    except Exception as e:
        if exit_on_error:
            error(e)
        raise

# 递归剔除 AST 中的元信息字段（pos 位置、annotations/annotation 注解），供 min 模式使用
def _strip_meta(node) -> None:
    if isinstance(node, dict):
        for k in list(node.keys()):
            if k in ('pos', 'annotations', 'annotation'):
                del node[k]
            else:
                _strip_meta(node[k])
    elif isinstance(node, list):
        for item in node:
            _strip_meta(item)

# 按输出模式序列化 AST：
#   standard（默认）: 无 JSON 格式化（紧凑，无空白分隔）
#   min:             无 JSON 格式化，并忽略 pos 信息（产物更小）
#   tidy:            JSON 格式化（indent=4）
def _serialize_ast(ast, output_mode: str) -> str:
    if output_mode == 'min':
        _strip_meta(ast)
        return json.dumps(ast, ensure_ascii = False, separators = (',', ':'))
    if output_mode == 'tidy':
        return json.dumps(ast, ensure_ascii = False, indent = 4)
    return json.dumps(ast, ensure_ascii = False, separators = (',', ':'))

def _listdir_full(folder_path: str) -> list[str]:
    try:
        return sorted(os.listdir(folder_path))
    except PermissionError:
        return []

# 检查一个目录内是否有多个同名内容（如 main.tsuc main.tscc main/ main.tscl），
# 有则报错，避免歧义。.tscc 若是同名 .tsuc 的编译产物，不算同名内容。
def _check_no_ambiguous(folder_path: str) -> None:
    by_base: dict[str, list[str]] = {}
    for entry in _listdir_full(folder_path):
        full = os.path.join(folder_path, entry)
        if os.path.isfile(full) and entry.endswith('.tscc') \
            and os.path.isfile(os.path.join(folder_path, entry[:-5] + '.tsuc')):
            continue
        base = entry.rsplit('.', 1)[0] if os.path.isfile(full) else entry
        by_base.setdefault(base, []).append(entry)
    conflicts = [entries for entries in by_base.values() if len(entries) > 1]
    if not conflicts:
        return
    detail_parts = [f'库中不能有多个同名内容，避免歧义:']
    for entries in conflicts:
        detail_parts.append('  - ' + ', '.join(
            os.path.join(folder_path, e) for e in entries))
    raise tanex_script_error(
        message = '\n'.join(detail_parts),
        file = folder_path,
    )

# 展开已编译库(.tscl)，把内部文件重新写入编译后的文件
def _extract_tscl_entries(tscl_path: str, base_rel: str) -> dict[str, object]:
    with open(tscl_path, 'r', encoding = 'utf-8') as f:
        data = json.load(f)
    result: dict[str, object] = {}
    for name, content in data.items():
        # 兼容旧产物：旧 .tscl 把文件内容双重序列化成了字符串，还原为对象
        if isinstance(content, str):
            content = json.loads(content)
        result['/' + base_rel + name] = content
    return result

# 递归收集库内文件：.tsuc 逐个编译为 .tscc，.tscl 展开为内部文件，每个目录检查同名歧义
def _collect_folder_entries(folder_path: str, base_rel: str,
    output_mode: str = 'standard') -> dict[str, object]:
    _check_no_ambiguous(folder_path)
    result: dict[str, object] = {}
    for entry in _listdir_full(folder_path):
        full = os.path.join(folder_path, entry)
        rel = (os.path.join(base_rel, entry) if base_rel else entry).replace('\\', '/')
        if os.path.isdir(full):
            if entry.endswith('.tscl'):
                continue
            result.update(_collect_folder_entries(full, rel, output_mode))
        elif entry.endswith('.tsuc'):
            with open(full, 'r', encoding = 'utf-8') as f:
                source = f.read()
            compiled = compile_source(source, full, output_mode = output_mode)
            tscc_name = rel.rsplit('.', 1)[0] + '.tscc'
            # 编译产物是 JSON 字符串，须解析回对象再存放，
            # 否则外层 json.dumps 会把它二次序列化转义成字符串
            result['/' + tscc_name] = json.loads(compiled)
        elif entry.endswith('.tscl'):
            base_name = rel.rsplit('.', 1)[0]
            result.update(_extract_tscl_entries(full, base_name))
    return result

def compile_folder(folder_path: str, output_mode: str = 'standard') -> str:
    try:
        folder_path = os.path.normpath(folder_path)
        entries = _collect_folder_entries(folder_path, '', output_mode)
        if output_mode == 'min':
            _strip_meta(entries)
            return json.dumps(entries, ensure_ascii = False, separators = (',', ':'))
        if output_mode == 'tidy':
            return json.dumps(entries, ensure_ascii = False, indent = 4)
        return json.dumps(entries, ensure_ascii = False, separators = (',', ':'))
    except Exception as e:
        error(e)
        raise
