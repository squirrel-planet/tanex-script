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
        # 已导入 (路径, 名称) 集合，用于去重
        self._imported_paths: set[tuple[str, str]] = imported_paths if imported_paths is not None else set()

    # 执行预处理，返回结果
    def process(self) -> preprocessor_result:
        self._merge_tokens()
        self._build_source_map()
        return preprocessor_result(
            tokens = self._output_tokens,
            source_map = self._source_map,
        )

    # 主合并循环，扫描 token 流，
    # import（关键字）与 ->（引入所有内容）语义分离：
    #   - import：单条静态字符串路径（后接 ; 或 = name;）保留预编译静态解析；
    #             表达式路径 / 列表形式一律动态化：保留 import token 序列原样输出，
    #             不静态解析依赖，运行时求值后加载
    #   - ->    ：单条静态字符串路径（后接 ;）保留预编译静态解析（输出 resolved_path）；
    #             其余（列表、表达式、= name 写法）原样输出，
    #             运行时动态求值 / 由 parser 报错
    def _merge_tokens(self):
        i = 0
        while i < len(self._tokens):
            tok = self._tokens[i]
            if tok[0] == 'import':
                i = self._try_runtime_import(i)
            elif tok[0] == '->':
                i = self._try_runtime_include(i)
            else:
                self._output_tokens.append(tok)
                i += 1

    # 处理 import / -> 表达式语句：
    # 单条静态字符串字面量走预编译解析（_try_static_import）；
    # 列表形式与表达式路径原样输出（_emit_import_raw），运行时动态加载
    def _try_runtime_import(self, i: int) -> int:
        tok = self._tokens[i]
        if i + 1 >= len(self._tokens):
            raise self._make_error(
                'import 语句格式错误: 后应为路径表达式',
                tok[1], tok[2], tok[3],
            )
        path_tok = self._tokens[i + 1]
        # 列表引入（元素可为表达式）一律动态化，原样输出
        if path_tok[0] == '[':
            return self._emit_import_raw(i)
        # 仅当操作数是静态字符串字面量（后接 ; 或 = name;，无运算符参与）
        # 时保留预编译解析；否则为表达式路径，动态化
        is_static_string = (path_tok[0].startswith('"')
            and path_tok[0].endswith('"')
            and i + 2 < len(self._tokens)
            and self._tokens[i + 2][0] in (';', '=')
            and not self._has_interpolation_mark(path_tok[0]))
        if is_static_string:
            return self._try_static_import(i, tok)
        return self._emit_import_raw(i)

    # 处理 -> 表达式语句（引入文件所有内容，与 import 语义分离）：
    # 单条静态字符串路径（后接 ;）走预编译解析（_try_static_include）；
    # 列表形式、表达式路径、以及 = name 写法一律原样输出
    # （_emit_import_raw），由运行时动态求值 / parser 报错
    def _try_runtime_include(self, i: int) -> int:
        tok = self._tokens[i]
        if i + 1 >= len(self._tokens):
            raise self._make_error(
                '-> 语句格式错误: 后应为路径表达式',
                tok[1], tok[2], tok[3],
            )
        path_tok = self._tokens[i + 1]
        # 列表引入（元素可为表达式）一律动态化，原样输出
        if path_tok[0] == '[':
            return self._emit_import_raw(i)
        # 仅当操作数是静态字符串字面量（后接 ;，无运算符参与）时保留预编译
        # 解析（输出 resolved_path）；= name 写法与表达式路径动态化
        is_static_string = (path_tok[0].startswith('"')
            and path_tok[0].endswith('"')
            and i + 2 < len(self._tokens)
            and self._tokens[i + 2][0] in (';', '=')
            and not self._has_interpolation_mark(path_tok[0]))
        if is_static_string and self._tokens[i + 2][0] == ';':
            return self._try_static_include(i, tok)
        return self._emit_import_raw(i)

    # 字符串字面量 token 是否含未转义 {（插值迹象）：含则路径必须动态化
    def _has_interpolation_mark(self, raw):
        if not (raw.startswith('"') and raw.endswith('"') and len(raw) >= 2):
            return False
        i = 1
        n = len(raw) - 1
        while i < n:
            ch = raw[i]
            if ch == '\\':
                i += 2
                continue
            if ch == '{':
                return True
            i += 1
        return False

    # 原样输出 import / -> 表达式语句（含分号），不静态解析依赖。
    # import（动态路径/列表）与 ->（动态路径/列表/= name 写法）
    # 都会走到这里；感知 () [] {} 嵌套深度，避免块内分号提前终止。
    def _emit_import_raw(self, i: int) -> int:
        start = i
        depth = 0
        while i < len(self._tokens):
            val = self._tokens[i][0]
            if val in ('{', '[', '('):
                depth += 1
            elif val in ('}', ']', ')'):
                depth -= 1
            elif val == ';' and depth == 0:
                break
            i += 1
        if i >= len(self._tokens):
            tok = self._tokens[start]
            raise self._make_error(
                'import 语句格式错误: 缺少结束的分号',
                tok[1], tok[2], tok[3],
            )
        # 消费分号
        i += 1
        for k in range(start, i):
            self._output_tokens.append(self._tokens[k])
        return i

    # 解析单条静态 import 语句（路径为字符串字面量）：解析路径并按需编译，
    # 保留 import 语句本身
    def _try_static_import(self, i: int, tok: tuple) -> int:
        path_tok = self._tokens[i + 1]
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
            # 支持 = *name; 语法（* 前缀：传地址引用绑定），
            # '*' 与名称一起保留，供 parser 识别引用绑定标记
            star_tok = None
            name_i = eq_i + 1
            semi_i = eq_i + 2
            if self._tokens[eq_i + 1][0] == '*':
                star_tok = self._tokens[eq_i + 1]
                name_i = eq_i + 2
                semi_i = eq_i + 3
            if semi_i >= len(self._tokens):
                last_tok = self._tokens[-1]
                raise self._make_error(
                    'import 语句格式错误: 缺少结束的分号',
                    last_tok[1], last_tok[2], last_tok[3],
                )
            name_tok = self._tokens[name_i]
            semi_tok = self._tokens[semi_i]
            if semi_tok[0] != ';':
                raise self._make_error(
                    'import 语句格式错误: 缺少结束的分号',
                    semi_tok[1], semi_tok[2], semi_tok[3],
                )
            self._emit_single_import(tok, path_tok, name_tok, semi_tok,
                star_tok = star_tok)
            return i + 6 if star_tok is not None else i + 5
        semi_tok = self._tokens[eq_i]
        if semi_tok[0] != ';':
            raise self._make_error(
                'import 语句格式错误: 缺少结束的分号',
                semi_tok[1], semi_tok[2], semi_tok[3],
            )
        self._emit_single_import(tok, path_tok, None, semi_tok)
        return i + 3

    # 解析单条静态 -> 语句（路径为字符串字面量）：解析路径并按需编译，
    # 保留 -> 语句本身（输出 resolved_path）
    def _try_static_include(self, i: int, tok: tuple) -> int:
        path_tok = self._tokens[i + 1]
        semi_tok = self._tokens[i + 2]
        if semi_tok[0] != ';':
            raise self._make_error(
                '-> 语句格式错误: 缺少结束的分号',
                semi_tok[1], semi_tok[2], semi_tok[3],
            )
        self._emit_single_include(tok, path_tok, semi_tok)
        return i + 3


    # 解析并输出一条 import 语句：解析路径、编译并输出，
    # 未改名时用默认名，改名时用给定名称；star_tok 非空时保留 * 前缀
    # （传地址引用绑定，供 parser 识别）
    def _emit_single_import(self, keyword_tok: tuple[str, int, int, str],
        path_tok: tuple[str, int, int, str],
        name_tok: tuple[str, int, int, str] | None,
        semi_tok: tuple[str, int, int, str],
        star_tok: tuple[str, int, int, str] | None = None) -> None:
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
            # 命名引入右值必须是地址引用（* 前缀）。自动生成的
            # 默认名同样补 *，与 parser 的"右值只能是地址引用"校验保持一致
            if star_tok is None:
                star_tok = ('*', path_tok[1], path_tok[2], path_tok[3])
        else:
            name_token = name_tok
        # 同一路径同一名称只导入一次；同一路径不同名称（如重复引入同一内容）
        # 也允许，重复的去重交给运行时处理
        import_key = (abs_path, name_token[0])
        if import_key in self._imported_paths:
            return
        self._imported_paths.add(import_key)
        # 输出: import "resolved_path" = 名称 ;
        # 运行时对字符串字面量做转义解码，路径中的反斜杠必须写成 \\ 才能还原
        resolved_val = '"' + resolved_path.replace('\\', '\\\\') + '"'
        self._output_tokens.append(
            ('import', keyword_tok[1], keyword_tok[2], keyword_tok[3]))
        self._output_tokens.append(
            (resolved_val, path_tok[1], path_tok[2], path_tok[3]))
        self._output_tokens.append(
            ('=', path_tok[1], path_tok[2], path_tok[3]))
        if star_tok is not None:
            self._output_tokens.append(star_tok)
        self._output_tokens.append(name_token)
        self._output_tokens.append(semi_tok)

    # 解析并输出一条 -> 语句：解析路径、编译并输出，
    # 输出保留 -> 前缀（不打包为 library，运行时展开顶层声明到当前作用域）
    def _emit_single_include(self, keyword_tok: tuple[str, int, int, str],
        path_tok: tuple[str, int, int, str],
        semi_tok: tuple[str, int, int, str]) -> None:
        raw_path = path_tok[0][1:-1]
        abs_path, import_type = self._resolve_import_path(
            raw_path, path_tok[1], path_tok[2], path_tok[3])
        if abs_path == self._file_path:
            warning([
                f'检测到循环引入: {raw_path}',
                f'文件 {abs_path} 不能引入自身，将跳过',
            ])
            return
        resolved_path = self._resolve_to_runtime_file(
            abs_path, import_type, path_tok)
        if resolved_path is None:
            warning([
                f'文件夹 "{raw_path}" 中没有主内容 (main.tsuc / main.tscc / main.tscl)',
                '将不引入任何内容，需要手动引入库中需要的文件',
            ])
            return
        # 输出: -> "resolved_path" ;
        # 运行时对字符串字面量做转义解码，路径中的反斜杠必须写成 \\ 才能还原
        resolved_val = '"' + resolved_path.replace('\\', '\\\\') + '"'
        self._output_tokens.append(
            ('->', keyword_tok[1], keyword_tok[2], keyword_tok[3]))
        self._output_tokens.append(
            (resolved_val, path_tok[1], path_tok[2], path_tok[3]))
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
        name = os.path.basename(abs_path)
        warning([
            f'已自动编译 {name} 为 {os.path.basename(tscc_path)}；'
            '注意：同名 .tsuc/.tscc 视为独立内容，'
            '下次裸名引入该库名可能因歧义报错，'
            '建议改用显式后缀（如 -> "xxx.tsuc";）引用。',
        ])

    # 构造预处理器错误
    def _make_error(self, message: str | list, line: int = 1, col: int = 1,
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

    # libary 库目录根路径（编译器安装目录下的 libary/）
    @staticmethod
    def _libary_root() -> str:
        return os.path.normpath(os.path.join(
            preprocessor._stdlib_root(), 'libary'))

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
        # 同名 .tsuc/.tscc 视为两个独立内容，可能因歧义报错
        if os.path.isfile(tscc_path):
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
            libary_candidates: list[tuple[str, str]] = []
        else:
            base = os.path.normpath(os.path.join(self._file_dir, clean_path))
            local_candidates = self._search_candidates(base)
            # 搜索 libary 库目录
            libary_base = os.path.normpath(os.path.join(
                self._libary_root(), clean_path))
            libary_candidates = self._search_candidates(libary_base)
        if wants_folder:
            local_candidates = [c for c in local_candidates if c[1] == 'folder']
            libary_candidates = [c for c in libary_candidates if c[1] == 'folder']
        # 合并候选并去重（本地与 libary 可能指向同一路径）
        seen: set[str] = set()
        all_candidates: list[tuple[str, str]] = []
        for path, typ in local_candidates + libary_candidates:
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
            raise self._make_error(
                [
                    f'导入 "{raw_path}" 存在多个可引用的内容，避免歧义:',
                    [f'{path} (类型: {typ})' for path, typ in all_candidates],
                    '可以加后缀避免歧义（文件夹加 /，文件加后缀名），也可以直接写绝对路径',
                ],
                error_line, error_col, error_file)
        if all_candidates:
            return all_candidates[0]
        raise self._make_error(
            f'无法找到导入目标: {raw_path}',
            error_line,
            error_col,
            error_file,
        )

    # 检查一个目录内是否有多个同名内容，有则报错，避免歧义。
    # 同名 .tsuc/.tscc 视为两个独立内容（编译产物关系也计入）。
    def _check_folder_no_ambiguous(self, dir_path: str,
        tok: tuple) -> None:
        try:
            entries = os.listdir(dir_path)
        except OSError:
            return
        by_base: dict[str, list[str]] = {}
        for entry in entries:
            full = os.path.join(dir_path, entry)
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
                candidates.append((p, typ))
        main_dir = os.path.join(dir_path, 'main')
        if os.path.isdir(main_dir):
            candidates.append((main_dir, 'folder'))
        if len(candidates) > 1:
            raise self._make_error(
                [
                    f'文件夹 "{dir_path}" 中存在多个主内容:',
                    [f'{path} (类型: {typ})' for path, typ in candidates],
                    '不能有多个主内容，请移除多余的 main',
                ],
                tok[1], tok[2], tok[3])
        if not candidates:
            return None
        path, typ = candidates[0]
        if typ == 'folder':
            # 递归查找最深层 main
            return self._find_main_in_folder(path, tok)
        return (path, typ)
