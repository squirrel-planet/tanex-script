import sys
import os
from errors import error
from errors import warning
from errors import output_message
from compile.main import compile_source
from compile.main import compile_folder
from cli_args import parse_argv
from cli_args import cli_parse_error
from errors import tanex_script_error

# 打包成 exe 后标准输出默认走本地代码页，这里统一成 utf-8，与源码运行保持一致
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, 'reconfigure'):
        _stream.reconfigure(encoding = 'utf-8')

version = 'Beta-1.2.3'

def _compile_file(tsuc_path: str, tscc_path: str | None = None, output_mode: str = 'standard'):
    if not tsuc_path.endswith('.tsuc'):
        warning([f'{tsuc_path} 文件不是 .tsuc 文件'])
    try:
        with open(tsuc_path, 'r', encoding = 'utf-8') as f:
            source = f.read()
    except OSError:
        error([f'无法读取文件: {tsuc_path}'])
        raise
    result = compile_source(
        source,
        tsuc_path,
        output_mode = output_mode
    )
    if not tscc_path:
        tscc_path = tsuc_path.rsplit('.', 1)[0] + '.tscc'
    with open(tscc_path, 'w', encoding = 'utf-8') as f:
        f.write(result)
    output_message([f'已编译: {tscc_path}'], False)

def _compile_folder(folder_path: str, tscl_path: str | None = None, output_mode: str = 'standard'):
    result = compile_folder(folder_path, output_mode = output_mode)
    if not tscl_path:
        tscl_path = folder_path.rstrip('/\\') + '.tscl'
    with open(tscl_path, 'w', encoding = 'utf-8') as f:
        f.write(result)
    output_message([f'已编译库: {tscl_path}'], False)

def _has_invalid_path_char(path: str) -> bool:
    # Windows 文件名不允许 < > " | ? * 和控制字符。
    # 出现这些多半是把文档里的占位符 <path> 原样抄进命令行了
    return any((ord(c) < 32 or c in '<>"|?*' for c in path))

def _read_console_source() -> str:
    from runtime.repl import read_console_source

    return read_console_source()

def _compile_console_source(tscc_path: str):
    source = _read_console_source()
    result = compile_source(source, '<stdin>')
    with open(tscc_path, 'w', encoding = 'utf-8') as f:
        f.write(result)
    output_message([f'已编译: {tscc_path}'], False)

def _run_temp_source(source: str, debug_lines: list[int] | None = None):
    # 内联代码只编译到内存并直接运行，不生成 .tscc 文件
    from errors import register_virtual_source
    from runtime.main import run_compiled_entry
    source_path = '<temp>'
    register_virtual_source(source_path, source)
    result = compile_source(source, source_path)
    output_message([f'开始运行 {source_path}'], False)
    run_compiled_entry(
        result,
        source_path,
        debug_lines = debug_lines if debug_lines else None,
        program_args = [],
        program_dir = os.getcwd()
    )

def _print_help():
    output_message(
        [
            '欢迎使用 Tanex Script',
            f'版本: {version}',
            '用法: python main.py [选项]',
            '选项:',
            [
                '-c, --compile              编译 .tsuc 文件为 .tscc 文件（输出到输入同名 .tscc）',
                '-r, --run                  运行 .tscc 文件，此选项后的所有参数原样传给被运行的程序；与 -c 组合时表示先编译后运行',
                '-q, --quiet                抑制普通信息，仅保留错误和警告',
                '-f=<path>, --file=<path>   指定输入文件路径（只接受 = 形式）',
                '-t=<code>, --temp=<code>   直接编译并运行内联代码，不生成文件（与 -c/-r/-i/-s/-f/-o 冲突）',
                '-o=<mode>, --output=<mode> 指定编译输出模式：min（编译无pos信息） / standard（默认）/ tidy（JSON格式化）',
                '-i, --input                从控制台输入代码，Ctrl+D 结束输入',
                '-s, --shell                进入交互式环境，每条语句立即执行，Ctrl+D 进入菜单',
                '-d=<n>, --debug=<n>        以断点调试模式运行，可重复指定多个整数断点行号（只接受 = 形式）',
                '-a=<path>, --args=<path>   从 JSON 文件读取参数列表，插入到当前命令行（只接受 = 形式）',
                '-h, --help, -?             显示帮助并退出（须单独使用）',
                '-v, --version              获取版本信息（须单独使用）'
            ],
            '注: 带值选项只接受 = 形式；冲突组合会直接报错。'
        ],
        False,
        suppressible = False
    )

def main():
    print('\x1b[0m')
    args = sys.argv[1:]
    try:
        cfg = parse_argv(args)
    except cli_parse_error as e:
        error([str(e)])
        raise SystemExit(1)
    if cfg.help:
        _print_help()
        sys.exit(0)
    if cfg.version:
        output_message(
            [
                'Tanex Script',
                f'版本: {version}'
            ],
            False,
            suppressible = False
        )
        sys.exit(0)
    if cfg.quiet:
        import errors

        errors.clear_mode = True

    # -o 输出模式仅编译生效；运行模式警告并忽略
    if cfg.run and (not cfg.compile) and ('o' in cfg.seen):
        error([f'-o={cfg.output_mode} 仅在编译模式下生效'])
    if cfg.shell_mode:
        from runtime.repl import repl_entry

        rc = None
        try:
            rc = repl_entry()
        except KeyboardInterrupt:
            output_message(['已中断，正在退出'], False)
            sys.exit(0)
        except Exception as e:
            error(e)
        if rc is not None:
            sys.exit(rc)
        return
    try:
        if cfg.temp_source is not None:
            _run_temp_source(cfg.temp_source, cfg.debug_lines)
            return
        run_target = None
        if cfg.input_mode:
            # 输入模式：编译控制台输入，产物路径取 -f=<path> 或 --file=<path>
            if not cfg.file:
                error(['输入模式必须指定产物文件路径（-f=<path> 或 --file=<path>）'])
                raise SystemExit(1)
            if _has_invalid_path_char(cfg.file):
                # 先校验再让用户输入，避免辛苦敲完代码才发现路径写不进去
                error(
                    [
                        f'产物路径不合法: {cfg.file}',
                        '文件名不能包含 < > " | ? * 等字符，-f= 后面直接写路径，不要带尖括号'
                    ]
                )
                raise SystemExit(1)
            _compile_console_source(cfg.file)
            run_target = cfg.file
        elif cfg.compile:
            assert cfg.file is not None
            if os.path.isdir(cfg.file):
                _compile_folder(cfg.file, output_mode = cfg.output_mode)
            else:
                _compile_file(cfg.file, output_mode = cfg.output_mode)
                run_target = cfg.file.rsplit('.', 1)[0] + '.tscc'
        else:
            run_target = cfg.file
        if cfg.run:
            if run_target is None:
                error(['编译目录没有生成可运行的程序产物（.tscc），无法继续运行'])
                raise SystemExit(1)
            if not (run_target.endswith('.tscc') or run_target.endswith('.tscl')):
                error(
                    [
                        f'{run_target} 不是编译产物文件（.tscc / .tscl），无法直接运行',
                        '请先编译得到 .tscc 后再运行'
                    ]
                )
            if run_target.endswith('.tscl'):
                warning([f'{run_target} 是库文件，正在尝试运行库'])
            output_message([f'开始运行 {run_target}'], False)

            from runtime.main import run_entry

            run_entry(
                run_target,
                debug_lines = cfg.debug_lines if cfg.debug_lines else None,
                program_args = cfg.program_args
            )
    except KeyboardInterrupt:
        output_message(['已中断，正在退出'], False)
        sys.exit(0)
    except RecursionError:
        error(['递归超限'])
    except tanex_script_error as err:
        error(err)
    except OSError as e:
        # 文件名非法 / 路径不存在 / 没权限都落这里，单独给个看得懂的提示
        error(['文件读写失败', str(e), '检查路径是否合法、目录是否存在'])
    except Exception as e:
        error(['解释器底层错误', str(e)])

if __name__ == '__main__':
    main()
