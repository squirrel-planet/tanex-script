import sys
import json
import os
from errors import error
from errors import warning
from errors import output_message
from compile.main import compile_source
from compile.main import compile_folder

def _read_json_args(file_path: str):
    # 读取 JSON 文件，解析为 list，作为命令行参数使用。
    # 若后缀不是 .json 则警告；若格式错误或内容不是 list 则报错退出。
    if not file_path.lower().endswith('.json'):
        warning([f'文件 "{file_path}" 不是 .json 后缀，尝试读取'])
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        error([f'文件不存在: {file_path}'])
        raise ValueError(f"File not found: {file_path}")
    except json.JSONDecodeError as e:
        error([f'JSON 格式错误: {e}'])
        raise ValueError(f"Invalid JSON: {e}")
    except OSError as e:
        error([f'无法读取文件: {file_path} - {e}'])
        raise
    if isinstance(data, dict):
        error(['期望 JSON 数组 (list)，但得到 JSON 对象 (dict)'])
        raise TypeError("Expected list, got dict")
    elif isinstance(data, list):
        return data
    else:
        error([f'期望 JSON 数组 (list)，但得到 {type(data).__name__}'])
        raise TypeError(f"Expected list, got {type(data).__name__}")

def _compile_file(tsuc_path: str, tscc_path: str | None = None):
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
    )
    if not tscc_path:
        tscc_path = tsuc_path.rsplit('.', 1)[0] + '.tscc'
    with open(tscc_path, 'w', encoding = 'utf-8') as f:
        f.write(result)
    output_message([f'已编译: {tscc_path}'], False)

def _compile_folder(folder_path: str, tscl_path: str | None = None):
    result = compile_folder(folder_path)
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
        '用法: python main.py [选项] <文件或文件夹>',
        '选项:',
        [
            '-c, --compile 编译 .tsuc 为 .tscc，后跟输出名可指定输出文件',
            '-r, --run     运行 .tscc 文件',
            '-i, --input   从控制台输入代码，Ctrl+D 结束输入',
            '-s, --shell   进入交互式环境，每条语句立即执行，Ctrl+D 退出',
            '-a, --args    从 JSON 文件中读取参数列表，插入到当前命令行',
            '--clear       清除所有普通的输出信息，仅保留错误和警告'
        ],
        '无选项或两个选项都选表示编译并运行'
    ], False)

def main():
    print('\033[0m')
    args = sys.argv[1:]
    new_args = []
    i = 0
    while i < len(args):
        if args[i] in ('-a', '--args'):
            if i + 1 >= len(args):
                error(['缺少 --args 参数的文件路径'])
                raise ValueError("Missing argument for --args")
            file_path = args[i + 1]
            extra_args = _read_json_args(file_path)
            new_args.extend(extra_args)
            i += 2
        else:
            new_args.append(args[i])
            i += 1
    args = new_args
    if not args or args[0] in ('-h', '--help', '?', '-?'):
        _print_help()
        sys.exit(1)
    file_path = None
    output_path = None
    compile_mode = False
    run_mode = False
    input_mode = False
    shell_mode = False
    clear_output = False
    i = 0
    while i < len(args):
        if args[i] in ('-c', '--compile'):
            compile_mode = True
            if i + 1 < len(args) and not args[i + 1].startswith('-'):
                output_path = args[i + 1]
                i += 1
        elif args[i] in ('-r', '--run'):
            run_mode = True
        elif args[i] in ('-i', '--input'):
            input_mode = True
        elif args[i] in ('-s', '--shell'):
            shell_mode = True
        elif args[i] == '--clear':
            clear_output = True
        else:
            file_path = args[i]
        i += 1
    if clear_output:
        import errors
        errors.clear_mode = True
    if output_path and not (output_path.endswith('.tscc') or output_path.endswith('.tscl')):
        warning([f'{output_path} 不是有效的输出文件名，输出文件名与输入文件同名'])
        output_path = None
    if shell_mode:
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
    if input_mode:
        if not compile_mode:
            compile_mode = True
        if not output_path:
            error(['输入模式必须在 -c --compile 参数后添加输出名'])
    if not input_mode and not file_path:
        _print_help()
        sys.exit(1)
    if not compile_mode:
        if not run_mode:
            compile_mode, run_mode = True, True
    try:
        run_target = file_path
        if input_mode:
            assert output_path is not None
            _compile_console_source(output_path)
            run_target = output_path
        elif compile_mode:
            assert file_path is not None
            if os.path.isdir(file_path):
                _compile_folder(file_path, output_path)
                if run_mode:
                    warning([f'{file_path} 是文件夹，编译为库文件后无法直接运行'])
                    run_mode = False
            else:
                _compile_file(file_path, output_path)
                if run_mode and not file_path.endswith('.tscc'):
                    run_target = output_path if output_path else file_path.rsplit('.', 1)[0] + '.tscc'
        if run_mode:
            assert run_target is not None
            if not (run_target.endswith('.tscc') or run_target.endswith('.tscl')):
                error([
                    f'{run_target} 不是编译产物文件（.tscc / .tscl），无法直接运行',
                    '请直接运行 .tsuc 源文件（会自动编译并运行），或先编译得到 .tscc 后再运行'
                ])
            if run_target.endswith('.tscl'):
                warning([f'{run_target} 是库文件，正在尝试运行库'])
            output_message([f'开始运行 {run_target}'], False)
            from runtime import run_entry
            run_entry(run_target)
    except KeyboardInterrupt:
        output_message(['已中断，正在退出'], False)
        sys.exit(0)
    except Exception as e:
        error(e)

if __name__ == '__main__':
    main()
