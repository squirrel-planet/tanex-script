import os
import json
from errors import error
from errors import tanex_script_error
from compile.preprocessor import preprocessor
from compile.tokenizer import tokenizer
from compile.parser import parser

def compile_source(source: str, file_path: str, exit_on_error: bool = True) -> str:
    try:
        tok = tokenizer(source, file_path)
        tokens = tok.tokenize()
        pp = preprocessor(tokens, file_path)
        pp_result = pp.process()
        merged_tokens = pp_result.tokens
        p = parser(merged_tokens)
        ast = p.parse()
        ast['dependencies'] = list(pp_result.dependencies)
        return json.dumps(ast, ensure_ascii = False, indent = 2)
    except Exception as e:
        if exit_on_error:
            error(e)
        raise

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
def _extract_tscl_entries(tscl_path: str, base_rel: str) -> dict[str, str]:
    with open(tscl_path, 'r', encoding = 'utf-8') as f:
        data = json.load(f)
    result: dict[str, str] = {}
    for name, content in data.items():
        result['/' + base_rel + name] = content
    return result

# 递归收集库内文件：.tsuc 逐个编译为 .tscc，.tscl 展开为内部文件，每个目录检查同名歧义
def _collect_folder_entries(folder_path: str, base_rel: str) -> dict[str, str]:
    _check_no_ambiguous(folder_path)
    result: dict[str, str] = {}
    for entry in _listdir_full(folder_path):
        full = os.path.join(folder_path, entry)
        rel = (os.path.join(base_rel, entry) if base_rel else entry).replace('\\', '/')
        if os.path.isdir(full):
            if entry.endswith('.tscl'):
                continue
            result.update(_collect_folder_entries(full, rel))
        elif entry.endswith('.tsuc'):
            with open(full, 'r', encoding = 'utf-8') as f:
                source = f.read()
            compiled = compile_source(source, full)
            tscc_name = rel.rsplit('.', 1)[0] + '.tscc'
            result['/' + tscc_name] = compiled
        elif entry.endswith('.tscl'):
            base_name = rel.rsplit('.', 1)[0]
            result.update(_extract_tscl_entries(full, base_name))
    return result

def compile_folder(folder_path: str) -> str:
    try:
        folder_path = os.path.normpath(folder_path)
        entries = _collect_folder_entries(folder_path, '')
        return json.dumps(entries, ensure_ascii = False, indent = 2)
    except Exception as e:
        error(e)
        raise
