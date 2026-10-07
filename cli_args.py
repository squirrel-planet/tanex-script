# CLI 参数解析
#
# 参数规范：
#   - 带值选项只接受 `=` 形式（-f=<path> / --file=<path> / -o=<mode> ...）
#   - 不再有"位置参数即文件"
#   - -r / --run 是参数边界，之后的全部 argv 原样透传为 program_args
#   - 未知选项、空值、非法输出模式、冲突组合一律显式报错
# 旧选项保留并严格化：
#   - -i/--input、-s/--shell       无值标志
#   - -a=<path>/--args=<path>      只接受 = 形式，从 JSON 读取参数列表展开插入命令行
#   - -d=<n>/--debug=<n>           只接受 = 形式，可重复收集断点行号

import json
from dataclasses import dataclass, field
from errors import warning

class cli_parse_error(ValueError):
    pass

@dataclass
class config:
    compile: bool = False
    run: bool = False
    quiet: bool = False
    help: bool = False
    version: bool = False
    # min | standard | tidy
    output_mode: str = 'standard'
    file: str | None = None
    program_args: list[str] = field(default_factory = list)
    # 旧选项（保留并严格化）
    input_mode: bool = False
    shell_mode: bool = False
    debug_lines: list[int] = field(default_factory = list)
    # 用于冲突检测的"出现次数"记录（保持出现顺序）
    seen: dict[str, str] = field(default_factory = dict)
    # 记录 -o 已出现的取值，用于重复检测
    _output_seen: str | None = None

# -a / --args 展开的最深层数，防止 JSON 参数互相引用形成死循环
_max_expand_rounds = 8

def _read_json_args(file_path: str) -> list:
    # 读取 JSON 文件，解析为 list，作为命令行参数使用。
    # 若后缀不是 .json 则警告；若格式错误或内容不是 list 则报错。
    if not file_path.lower().endswith('.json'):
        warning([f'文件 "{file_path}" 不是 .json 后缀，尝试读取'])
    try:
        with open(file_path, 'r', encoding = 'utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        raise cli_parse_error(f'文件不存在: {file_path}')
    except json.JSONDecodeError as e:
        raise cli_parse_error(f'JSON 格式错误: {e}')
    except OSError as e:
        raise cli_parse_error(f'无法读取文件: {file_path} - {e}')
    if isinstance(data, dict):
        raise cli_parse_error('期望 JSON 数组，但得到 JSON 对象')
    if not isinstance(data, list):
        raise cli_parse_error('期望 JSON 数组，但得到未知内容')
    return data

def _mark(cfg: config, name: str) -> None:
    # 记录简单标志出现，重复即报错
    if name in cfg.seen:
        raise cli_parse_error(f'重复选项: -{name}')
    cfg.seen[name] = ''

def _set_file(cfg: config, path: str) -> None:
    if cfg.file is not None:
        raise cli_parse_error(
            f'输入文件指定了两次: {cfg.file!r} 和 {path!r}')
    cfg.file = path
    cfg.seen.setdefault('f', path)

def _set_output(cfg: config, mode: str) -> None:
    if mode not in ('min', 'standard', 'tidy'):
        raise cli_parse_error(f'无效的输出模式: {mode!r}')
    if cfg._output_seen is not None:
        raise cli_parse_error(
            f'输出模式指定了两次: {cfg._output_seen!r} 和 {mode!r}')
    cfg.output_mode = mode
    cfg._output_seen = mode
    cfg.seen.setdefault('o', mode)

def _validate(cfg: config) -> None:
    # -h / -v 与任何其它选项冲突
    if cfg.help or cfg.version:
        others = [k for k in cfg.seen if k not in ('h', 'v')]
        if others:
            flag = '-h' if cfg.help else '-v'
            raise cli_parse_error(f'{flag} 与 -{others[0]} 冲突')
        if cfg.help and cfg.version:
            raise cli_parse_error('-h 与 -v 冲突')
        # -h / -v 单独出现，直接放行
        return
    # -c 与 -r 可组合：语义为"先编译后运行"（-r 是参数边界，须在 -c 之后，
    # 之后的 argv 原样透传为 program_args；若 -r 在 -c 前，-c 会被当作
    # program_args 透传，不会被解析为编译选项，故不存在"先运行再编译"）。
    # main.py 按固定顺序执行：先编译出 .tscc 产物，再运行该产物。
    # 编译/运行必须有文件（-i 输入模式例外：源码来自控制台，-f 可作产物路径）
    if (cfg.compile or cfg.run) and cfg.file is None and not cfg.input_mode:
        raise cli_parse_error('未提供输入文件; 请使用 -f=<path> 指定')
    # 什么都没做（-i / -s 是实质操作，不算空命令）
    if not (cfg.compile or cfg.run or cfg.help or cfg.version
            or cfg.input_mode or cfg.shell_mode):
        raise cli_parse_error('未指定任何操作; 请使用 -c、-r、-h 或 -v')

def parse_argv(argv: list[str]) -> config:
    cfg = config()
    i = 0
    expand_rounds = 0
    while i < len(argv):
        a = argv[i]
        # -a / --args：展开 JSON 参数列表（= 形式），原地插入继续解析
        if a.startswith('-a=') or a.startswith('--args='):
            path = a.split('=', 1)[1]
            if not path:
                raise cli_parse_error(
                    '-a= 需要提供路径' if a.startswith('-a=')
                    else '--args= 需要提供路径')
            expand_rounds += 1
            if expand_rounds > _max_expand_rounds:
                raise cli_parse_error('-a --args 展开层数过多，可能存在循环引用')
            extra = _read_json_args(path)
            argv = argv[:i] + extra + argv[i + 1:]
            continue
        # 边界：-r / --run
        if a in ('-r', '--run'):
            if 'r' in cfg.seen:
                raise cli_parse_error('重复选项: -r')
            cfg.seen['r'] = ''
            cfg.run = True
            cfg.program_args = argv[i + 1:]
            break
        # 简单标志
        if   a in ('-c', '--compile'): _mark(cfg, 'c'); cfg.compile = True
        elif a in ('-q', '--quiet'):   _mark(cfg, 'q'); cfg.quiet   = True
        elif a in ('-h', '--help'):    _mark(cfg, 'h'); cfg.help    = True
        elif a in ('-v', '--version'): _mark(cfg, 'v'); cfg.version = True
        # 旧选项：无值标志
        elif a in ('-i', '--input'):   _mark(cfg, 'i'); cfg.input_mode = True
        elif a in ('-s', '--shell'):   _mark(cfg, 's'); cfg.shell_mode = True
        # 文件
        elif a.startswith('-f='):
            val = a[3:]
            if not val:
                raise cli_parse_error('-f= 需要提供路径')
            _set_file(cfg, val)
        elif a.startswith('--file='):
            val = a[len('--file='):]
            if not val:
                raise cli_parse_error('--file= 需要提供路径')
            _set_file(cfg, val)
        # 输出模式
        elif a.startswith('-o=') or a.startswith('--output='):
            val = a.split('=', 1)[1]
            if not val:
                raise cli_parse_error('输出模式需要提供值')
            _set_output(cfg, val)
        # 断点行号（可重复）
        elif a.startswith('-d=') or a.startswith('--debug='):
            val = a.split('=', 1)[1]
            if not val:
                raise cli_parse_error(
                    '-d= 需要提供值' if a.startswith('-d=')
                    else '--debug= 需要提供值')
            try:
                n = int(val)
            except ValueError:
                raise cli_parse_error(f'无效的断点行号: {val!r}')
            cfg.debug_lines.append(n)
            cfg.seen.setdefault('d', val)
        # 未知选项 / 位置参数
        elif a.startswith('-'):
            raise cli_parse_error(f'未知选项: {a}')
        else:
            raise cli_parse_error(
                f'意外的位置参数 {a!r}; '
                '请使用 -f=<path> 指定输入文件')
        i += 1
    _validate(cfg)
    return cfg
