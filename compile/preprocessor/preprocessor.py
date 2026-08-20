import os
import sys
from dataclasses import dataclass
from dataclasses import field
from compile.preprocessor.source_map import source_map

sys.path.append('..')

from errors import *

# 预处理器的输出结果，包含合并后的 token 流和源映射信息
@dataclass
class preprocessor_result(object):
    tokens: list
    source_map: source_map
    dependencies: list[str]


# 预处理器，在 tokenizer 之后运行，按 token 模式匹配 import 语句并合并多文件 token 流
class preprocessor(object):
    def __init__(self, tokens: list, file_path: str,
        imported_paths: set[tuple[str, str]] | None = None):
        # 原始输入
        self._tokens = tokens
        self._file_path = os.path.abspath(file_path)
        self._file_dir = os.path.dirname(self._file_path)
        self._file_name = os.path.basename(self._file_path)
        # 输出缓冲区
        self._output_tokens: list = []
        self._source_map = source_map()
        self._dependencies: list[str] = []
        # 已导入 (路径, 名称) 集合，用于去重
        self._imported_paths: set[tuple[str, str]] = imported_paths if imported_paths is not None else set()

    # 执行预处理，返回结果
    def process(self) -> preprocessor_result:
        self._merge_tokens()
        self._build_source_map()
        return preprocessor_result(
            tokens = self._output_tokens,
            source_map = self._source_map,
            dependencies = self._dependencies,
        )

    # 主合并循环，扫描 token 流，
    # -> 与 import 等价：-> "路径"; / import "路径"; 引入为 library 类型，
    # 未改名时默认以路径名为标识符；-> "路径" = 名称; / import "路径" = 名称; 改名引入
    def _merge_tokens(self):
        i = 0
        while i < len(self._tokens):
            tok = self._tokens[i]
            if tok[0] == '->' or tok[0] == 'import':
                i = self._try_runtime_import(i)
            else:
                self._output_tokens.append(tok)
                i += 1

    # 解析运行时 import 语句：解析路径并按需编译，保留 import 语句本身
    def _try_runtime_import(self, i: int) -> int:
        tok = self._tokens[i]
        if i + 2 >= len(self._tokens):
            raise self._make_error(
                'import 语句格式错误: 后应为字符串文件路径',
                tok[1], tok[2], tok[3],
            )
        path_tok = self._tokens[i + 1]
        # 列表批量导入: import ["a", "b"]; / import ["a", "b"] = [x, y];
        if path_tok[0] == '[':
            return self._try_list_import(i, tok)
        if not (path_tok[0].startswith('"') and path_tok[0].endswith('"')):
            raise self._make_error(
                'import 语句格式错误: 后应为字符串文件路径',
                path_tok[1], path_tok[2], path_tok[3],
            )
        # 检查是否有 = name 改名语法
        eq_i = i + 2
        has_rename = (eq_i < len(self._tokens)
            and self._tokens[eq_i][0] == '=')
        if has_rename:
            if eq_i + 2 >= len(self._tokens):
                raise self._make_error(
                    'import = 语句格式错误: 后应为标识符和分号',
                    self._tokens[eq_i][1], self._tokens[eq_i][2],
                    self._tokens[eq_i][3],
                )
            name_tok = self._tokens[eq_i + 1]
            semi_tok = self._tokens[eq_i + 2]
            if semi_tok[0] != ';':
                raise self._make_error(
                    'import 语句格式错误: 缺少结束的分号',
                    semi_tok[1], semi_tok[2], semi_tok[3],
                )
            self._emit_single_import(tok, path_tok, name_tok, semi_tok)
            return i + 5
        semi_tok = self._tokens[eq_i]
        if semi_tok[0] != ';':
            raise self._make_error(
                'import 语句格式错误: 缺少结束的分号',
                semi_tok[1], semi_tok[2], semi_tok[3],
            )
        self._emit_single_import(tok, path_tok, None, semi_tok)
        return i + 3

    # 解析列表批量导入：import ["a", "b"]; 或 import ["a", "b"] = [x, y];
    # 对每条路径调用与单条导入一致的逻辑，分别输出 import 语句
    def _try_list_import(self, i: int, keyword_tok: tuple) -> int:
        path_tokens, after = self._parse_string_list(i + 1, keyword_tok)
        if not path_tokens:
            raise self._make_error(
                'import 列表导入: 路径列表不能为空',
                keyword_tok[1], keyword_tok[2], keyword_tok[3],
            )
        eq_i = after
        name_tokens: list[tuple] = []
        has_rename = (eq_i < len(self._tokens)
            and self._tokens[eq_i][0] == '=')
        if has_rename:
            if eq_i + 1 >= len(self._tokens):
                raise self._make_error(
                    'import = 语句格式错误: 后应为标识符列表',
                    self._tokens[eq_i][1], self._tokens[eq_i][2],
                    self._tokens[eq_i][3],
                )
            name_tokens, after = self._parse_name_list(eq_i + 1, keyword_tok)
            if len(name_tokens) != len(path_tokens):
                raise self._make_error(
                    f'import 列表导入: 名称数量 ({len(name_tokens)}) '
                    f'与路径数量 ({len(path_tokens)}) 不一致',
                    keyword_tok[1], keyword_tok[2], keyword_tok[3],
                )
        semi_tok = self._tokens[after]
        if semi_tok[0] != ';':
            raise self._make_error(
                'import 语句格式错误: 缺少结束的分号',
                semi_tok[1], semi_tok[2], semi_tok[3],
            )
        for idx, path_tok in enumerate(path_tokens):
            name_tok = name_tokens[idx] if name_tokens else None
            self._emit_single_import(keyword_tok, path_tok, name_tok, semi_tok)
        return after + 1

    # 解析字符串路径列表 [ "a", "b" ]，返回 (路径 token 列表, 列表后的索引)
    def _parse_string_list(self, start_i: int, keyword_tok: tuple) -> tuple:
        if start_i >= len(self._tokens) or self._tokens[start_i][0] != '[':
            raise self._make_error(
                'import 语句格式错误: 后应为字符串文件路径或路径列表',
                keyword_tok[1], keyword_tok[2], keyword_tok[3],
            )
        items: list[tuple] = []
        j = start_i + 1
        while j < len(self._tokens) and self._tokens[j][0] != ']':
            t = self._tokens[j]
            if not (t[0].startswith('"') and t[0].endswith('"')):
                raise self._make_error(
                    'import 路径列表: 元素应为字符串文件路径',
                    t[1], t[2], t[3],
                )
            items.append(t)
            j += 1
            if j < len(self._tokens) and self._tokens[j][0] == ',':
                j += 1
        if j >= len(self._tokens) or self._tokens[j][0] != ']':
            raise self._make_error(
                'import 路径列表: 缺少右括号 ]',
                keyword_tok[1], keyword_tok[2], keyword_tok[3],
            )
        return items, j + 1

    # 解析标识符名称列表 [ a, b ]，返回 (名称 token 列表, 列表后的索引)
    def _parse_name_list(self, start_i: int, keyword_tok: tuple) -> tuple:
        if start_i >= len(self._tokens) or self._tokens[start_i][0] != '[':
            raise self._make_error(
                'import = 语句格式错误: 后应为标识符列表',
                keyword_tok[1], keyword_tok[2], keyword_tok[3],
            )
        items: list[tuple] = []
        j = start_i + 1
        while j < len(self._tokens) and self._tokens[j][0] != ']':
            t = self._tokens[j]
            # 只需检查首字符：tokenizer 已保证 name token 后续字符
            # 都是合法标识符字符（数字会被拆开，如 std1 -> std + 1），
            # 这里只区分 name 与字符串/整数等其他 token
            if not (t[0][0].isalpha() or t[0][0] == '_' or ord(t[0][0]) > 127):
                raise self._make_error(
                    'import 名称列表: 元素应为标识符',
                    t[1], t[2], t[3],
                )
            items.append(t)
            j += 1
            if j < len(self._tokens) and self._tokens[j][0] == ',':
                j += 1
        if j >= len(self._tokens) or self._tokens[j][0] != ']':
            raise self._make_error(
                'import 名称列表: 缺少右括号 ]',
                keyword_tok[1], keyword_tok[2], keyword_tok[3],
            )
        return items, j + 1

    # 解析并输出一条 import 语句：解析路径、编译并按需添加依赖，
    # 未改名时用默认名，改名时用给定名称
    def _emit_single_import(self, keyword_tok: tuple[str, int, int, str],
        path_tok: tuple[str, int, int, str], name_tok: tuple[str, int, int, str] | None,
        semi_tok: tuple[str, int, int, str]) -> None:
        raw_path = path_tok[0][1:-1]
        abs_path, import_type = self._resolve_import_path(
            raw_path, path_tok[1], path_tok[2], path_tok[3])
        if abs_path == self._file_path:
            warning([
                f'检测到循环导入: {raw_path}',
                f'文件 {abs_path} 不能导入自身，将跳过',
            ])
            return
        resolved_path = self._resolve_to_runtime_file(
            abs_path, import_type, path_tok)
        if resolved_path is None:
            warning([
                f'文件夹 "{raw_path}" 中没有主内容 (main.tsuc / main.tscc / main.tscl)',
                '将不导入任何内容，需要手动引入库中需要的文件',
            ])
            return
        if name_tok is None:
            default_name = self._default_import_name(raw_path, path_tok)
            name_token = (
                default_name, path_tok[1], path_tok[2], path_tok[3])
        else:
            name_token = name_tok
        # 同一路径同一名称只导入一次；同一路径不同名称（如重复引入同一内容）
        # 也允许，重复的去重交给运行时处理
        import_key = (abs_path, name_token[0])
        if import_key in self._imported_paths:
            return
        self._imported_paths.add(import_key)
        # 输出: import "resolved_path" = 名称 ;
        # 导入不再写入 dependencies：运行时按命名空间加载，内容仅通过库句柄访问
        resolved_val = '"' + resolved_path + '"'
        self._output_tokens.append(
            ('import', keyword_tok[1], keyword_tok[2], keyword_tok[3]))
        self._output_tokens.append(
            (resolved_val, path_tok[1], path_tok[2], path_tok[3]))
        self._output_tokens.append(
            ('=', path_tok[1], path_tok[2], path_tok[3]))
        self._output_tokens.append(name_token)
        self._output_tokens.append(semi_tok)

    # 未改名导入时的默认标识符：取路径最后一段，去掉扩展名和结尾斜杠
    def _default_import_name(self, raw_path: str, tok: tuple) -> str:
        clean = raw_path.rstrip('/\\')
        name = os.path.splitext(os.path.basename(clean))[0]
        if not name or not (name[0].isalpha() or name[0] == '_'
            or ord(name[0]) > 127):
            raise self._make_error(
                f'导入 "{raw_path}" 的默认名称 "{name}" 不能作为标识符，'
                '请使用 import "..." = 名称; 显式命名',
                tok[1], tok[2], tok[3],
            )
        return name

    # 把导入目标解析为可被运行时 import 的 .tscc/.tscl 文件，
    # 文件夹取主内容；.tsuc 先编译再使用
    def _resolve_to_runtime_file(self, abs_path: str, import_type: str,
        tok: tuple) -> str | None:
        if import_type == 'folder':
            main_path = self._find_main_in_folder(abs_path, tok)
            if main_path is None:
                return None
            abs_path, import_type = main_path
        if import_type == 'tsuc':
            resolved = abs_path.rsplit('.', 1)[0] + '.tscc'
            if not os.path.exists(resolved):
                self._compile_tsuc(abs_path, tok)
            return resolved
        return abs_path

    # 根据合并后的 token 流构建行级源映射
    def _build_source_map(self):
        resolved = 1
        prev = None
        for tok in self._output_tokens:
            file_name, line = tok[3], tok[1]
            if prev is None:
                resolved = 1
            elif file_name == prev[0]:
                resolved += max(0, line - prev[1])
            else:
                resolved += 1
            if resolved not in self._source_map._map:
                self._source_map.set_line(resolved, file_name, line)
            prev = (file_name, line)

    # 编译 .tsuc 为 .tscc
    def _compile_tsuc(self, abs_path: str, tok: tuple):
        from compile.main import compile_source
        try:
            with open(abs_path, 'r', encoding = 'utf-8') as f:
                source = f.read()
        except Exception as e:
            raise self._make_error(
                f'读取导入文件失败: {abs_path} ({e})',
                tok[1], tok[2], tok[3],
            )
        try:
            compiled = compile_source(source, abs_path)
        except Exception as e:
            raise self._make_error(
                f'编译导入文件失败: {abs_path} ({e})',
                tok[1], tok[2], tok[3],
            )
        tscc_path = abs_path.rsplit('.', 1)[0] + '.tscc'
        with open(tscc_path, 'w', encoding = 'utf-8') as f:
            f.write(compiled)

    # 构造预处理器错误
    def _make_error(self, message: str, line: int = 1, col: int = 1,
        file: str | None = None):
        return tanex_script_error(
            message = message,
            file = file or self._file_path,
            line = line,
            col = col,
            code = 'preprocessor',
        )

    # 标准库根路径（编译器安装目录）
    @staticmethod
    def _stdlib_root() -> str:
        compiler_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.normpath(os.path.join(compiler_dir, '..', '..'))

    # 在指定根路径下搜索导入候选
    @staticmethod
    def _search_candidates(base: str) -> list[tuple[str, str]]:
        result: list[tuple[str, str]] = []
        if os.path.isfile(base):
            ext = os.path.splitext(base)[1].lower()
            if ext == '.tsuc':
                result.append((base, 'tsuc'))
            elif ext == '.tscc':
                result.append((base, 'tscc'))
            elif ext == '.tscl':
                result.append((base, 'tscl'))
        tsuc_path = base + '.tsuc'
        if os.path.isfile(tsuc_path):
            result.append((tsuc_path, 'tsuc'))
        tscc_path = base + '.tscc'
        # .tscc 若是同名 .tsuc 的编译产物，不算独立内容，避免歧义
        if os.path.isfile(tscc_path) and not os.path.isfile(tsuc_path):
            result.append((tscc_path, 'tscc'))
        tscl_path = base + '.tscl'
        if os.path.isfile(tscl_path):
            result.append((tscl_path, 'tscl'))
        if os.path.isdir(base):
            result.append((base, 'folder'))
        return result

    # 解析导入路径，返回绝对路径和导入类型
    def _resolve_import_path(self, raw_path: str, error_line: int,
        error_col: int, error_file: str):
        # 以 / 或 \ 结尾的路径只匹配文件夹（文件夹加 / 避免歧义）
        wants_folder = raw_path.endswith('/') or raw_path.endswith('\\')
        clean_path = raw_path.rstrip('/\\')
        if os.path.isabs(clean_path):
            base = clean_path
            local_candidates = self._search_candidates(base)
            stdlib_candidates: list[tuple[str, str]] = []
        else:
            base = os.path.normpath(os.path.join(self._file_dir, clean_path))
            local_candidates = self._search_candidates(base)
            # 搜索标准库
            stdlib_base = os.path.normpath(os.path.join(
                self._stdlib_root(), clean_path))
            stdlib_candidates = self._search_candidates(stdlib_base)
        if wants_folder:
            local_candidates = [c for c in local_candidates if c[1] == 'folder']
            stdlib_candidates = [c for c in stdlib_candidates if c[1] == 'folder']
        # 合并候选并去重（本地与标准库可能指向同一路径）
        seen: set[str] = set()
        all_candidates: list[tuple[str, str]] = []
        for path, typ in local_candidates + stdlib_candidates:
            if path not in seen:
                seen.add(path)
                all_candidates.append((path, typ))
        if not wants_folder:
            # .tscl 优先：同名文件夹是 .tscl 的编译来源，不算独立内容
            tscl_bases: set[str] = {
                path[:-5] for path, typ in all_candidates if typ == 'tscl'}
            all_candidates = [
                (path, typ) for path, typ in all_candidates
                if typ != 'folder' or path not in tscl_bases]
        if len(all_candidates) > 1:
            detail_parts: list[str] = [
                f'导入 "{raw_path}" 存在多个可引用的内容，避免歧义:']
            for path, typ in all_candidates:
                detail_parts.append(f'  - {path} (类型: {typ})')
            detail_parts.append(
                '可以加后缀避免歧义（文件夹加 /，文件加后缀名），也可以直接写绝对路径')
            raise self._make_error(
                '\n'.join(detail_parts), error_line, error_col, error_file)
        if all_candidates:
            return all_candidates[0]
        raise self._make_error(
            f'无法找到导入目标: {raw_path}',
            error_line,
            error_col,
            error_file,
        )

    # 检查一个目录内是否有多个同名内容，有则报错，避免歧义。
    # .tscc 若是同名 .tsuc 的编译产物，不算同名内容。
    def _check_folder_no_ambiguous(self, dir_path: str,
        tok: tuple) -> None:
        try:
            entries = os.listdir(dir_path)
        except OSError:
            return
        by_base: dict[str, list[str]] = {}
        for entry in entries:
            full = os.path.join(dir_path, entry)
            if os.path.isfile(full) and entry.endswith('.tscc') \
                and os.path.isfile(os.path.join(dir_path, entry[:-5] + '.tsuc')):
                continue
            base = entry.rsplit('.', 1)[0] if os.path.isfile(full) else entry
            by_base.setdefault(base, []).append(entry)
        conflicts = [value for value in by_base.values() if len(value) > 1]
        if not conflicts:
            return
        detail_parts: list[str] = [f'库 "{dir_path}" 中不能有多个同名内容，避免歧义:']
        for entries in conflicts:
            detail_parts.append('  - ' + ', '.join(sorted(entries)))
        raise self._make_error('\n'.join(detail_parts),
            tok[1], tok[2], tok[3])

    # 在文件夹中查找 main 入口文件，支持递归嵌套
    def _find_main_in_folder(self, dir_path: str,
        tok: tuple) -> tuple[str, str] | None:
        self._check_folder_no_ambiguous(dir_path, tok)
        candidates: list[tuple[str, str]] = []
        for ext, typ in [('tsuc', 'tsuc'), ('tscc', 'tscc'), ('tscl', 'tscl')]:
            p = os.path.join(dir_path, f'main.{ext}')
            if os.path.isfile(p):
                if ext == 'tscc' and os.path.isfile(
                    os.path.join(dir_path, 'main.tsuc')):
                    continue
                candidates.append((p, typ))
        main_dir = os.path.join(dir_path, 'main')
        if os.path.isdir(main_dir):
            candidates.append((main_dir, 'folder'))
        if len(candidates) > 1:
            detail_parts: list[str] = [f'文件夹 "{dir_path}" 中存在多个主内容:']
            for path, typ in candidates:
                detail_parts.append(f'  - {path} (类型: {typ})')
            detail_parts.append('不能有多个主内容，请移除多余的 main')
            raise self._make_error('\n'.join(detail_parts),
                tok[1], tok[2], tok[3])
        if not candidates:
            return None
        path, typ = candidates[0]
        if typ == 'folder':
            # 递归查找最深层 main
            return self._find_main_in_folder(path, tok)
        return (path, typ)
