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

version = 'Beta-1.2.3'

def _compile_file(tsuc_path: str, tscc_path: str | None = None,
    output_mode: str = 'standard'):
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
        output_mode = output_mode,
    )
    if not tscc_path:
        tscc_path = tsuc_path.rsplit('.', 1)[0] + '.tscc'
    with open(tscc_path, 'w', encoding = 'utf-8') as f:
        f.write(result)
    output_message([f'已编译: {tscc_path}'], False)

def _compile_folder(folder_path: str, tscl_path: str | None = None,
    output_mode: str = 'standard'):
    result = compile_folder(folder_path, output_mode = output_mode)
    if not tscl_path:
        tscl_path = folder_path.rstrip('/\\') + '.tscl'
    with open(tscl_path, 'w', encoding = 'utf-8') as f:
        f.write(result)
    output_message([f'已编译库: {tscl_path}'], False)

def _read_console_source() -> str:
    from runtime.repl import read_console_source
    return read_console_source()

def _compile_console_source(tscc_path: str):
    source = _read_console_source()
    result = compile_source(source, '<stdin>')
    with open(tscc_path, 'w', encoding = 'utf-8') as f:
        f.write(result)
    output_message([f'已编译: {tscc_path}'], False)

def _print_help():
    output_message([
        '欢迎使用 Tanex Script',
        f'版本: {version}',
        '用法: python main.py [选项]',
        '选项:',
        [
            '-c, --compile              编译 .tsuc 文件为 .tscc 文件（输出到输入同名 .tscc）',
            '-r, --run                  运行 .tscc 文件，此选项后的所有参数原样传给被运行的程序；与 -c 组合时表示先编译后运行',
            '-q, --quiet                抑制普通信息，仅保留错误和警告',
            '-f=<path>, --file=<path>   指定输入文件路径（只接受 = 形式）',
            '-o=<mode>, --output=<mode> 指定编译输出模式：min（编译无pos信息） / standard（默认）/ tidy（JSON格式化）',
            '-i, --input                从控制台输入代码，Ctrl+D 结束输入',
            '-s, --shell                进入交互式环境，每条语句立即执行，Ctrl+D 进入菜单',
            '-d=<n>, --debug=<n>        以断点调试模式运行，可重复指定多个整数断点行号（只接受 = 形式）',
            '-a=<path>, --args=<path>   从 JSON 文件读取参数列表，插入到当前命令行（只接受 = 形式）',
            '-h, --help, -?             显示帮助并退出（须单独使用）',
            '-v, --version              获取版本信息（须单独使用）'
        ],
        '注: 带值选项只接受 = 形式；冲突组合会直接报错。'
    ], False, suppressible = False)

def main():
    print('\033[0m')
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
        output_message([
            'Tanex Script',
            f'版本: {version}'
        ], suppressible = False)
        sys.exit(0)
    if cfg.quiet:
        import errors
        errors.clear_mode = True
    # -o 输出模式仅编译生效；运行模式警告并忽略
    if cfg.run and not cfg.compile and 'o' in cfg.seen:
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
        run_target = None
        if cfg.input_mode:
            # 输入模式：编译控制台输入，产物路径取 -f=<path> 或 --file=<path>
            if not cfg.file:
                error(['输入模式必须指定产物文件路径（-f=<path> 或 --file=<path>）'])
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
                error([
                    f'{run_target} 不是编译产物文件（.tscc / .tscl），无法直接运行',
                    '请先编译得到 .tscc 后再运行'
                ])
            if run_target.endswith('.tscl'):
                warning([f'{run_target} 是库文件，正在尝试运行库'])
            output_message([f'开始运行 {run_target}'], False)
            from runtime.main import run_entry
            run_entry(run_target,
                debug_lines = cfg.debug_lines if cfg.debug_lines else None,
                program_args = cfg.program_args)
    except KeyboardInterrupt:
        output_message(['已中断，正在退出'], False)
        sys.exit(0)
    except RecursionError:
        error(['递归超限'])
    except tanex_script_error as err:
        error(err)
    except Exception as e:
        error(['解释器底层错误', str(e)])

if __name__ == '__main__':
    main()
