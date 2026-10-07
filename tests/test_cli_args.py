import sys

sys.path.insert(0, '..')

from cli_args import cli_parse_error, parse_argv

def test_parse_compile_short():
    cfg = parse_argv(['-c', '-f=a.tsuc'])
    assert cfg.compile is True
    assert cfg.file == 'a.tsuc'


def test_parse_compile_long():
    cfg = parse_argv(['--compile', '--file=a.tsuc'])
    assert cfg.compile is True
    assert cfg.file == 'a.tsuc'


def test_parse_run_boundary():
    cfg = parse_argv(['-f=a.tsuc', '-r', 'x', 'y'])
    assert cfg.run is True
    assert cfg.program_args == ['x', 'y']


def test_parse_run_long_boundary():
    cfg = parse_argv(['-f=a.tsuc', '--run', '-c'])
    assert cfg.run is True
    assert cfg.program_args == ['-c']


def test_parse_quiet():
    cfg = parse_argv(['-c', '-f=a.tsuc', '-q'])
    assert cfg.quiet is True


def test_parse_help_alone():
    cfg = parse_argv(['-h'])
    assert cfg.help is True


def test_parse_version_alone():
    cfg = parse_argv(['-v'])
    assert cfg.version is True


def test_help_conflicts():
    try:
        parse_argv(['-h', '-c'])
    except cli_parse_error as e:
        assert '-h 与 -c 冲突' in str(e)
    else:
        raise AssertionError('should raise cli_parse_error')


def test_version_conflicts():
    try:
        parse_argv(['-v', '-f=a.tsuc'])
    except cli_parse_error as e:
        assert '-v 与 -f 冲突' in str(e)
    else:
        raise AssertionError('should raise cli_parse_error')


def test_help_version_conflict():
    try:
        parse_argv(['-h', '-v'])
    except cli_parse_error as e:
        assert '-h 与 -v 冲突' in str(e)
    else:
        raise AssertionError('should raise cli_parse_error')


def test_compile_run_combined():
    # -c 与 -r 可组合：语义为先编译后运行（-r 后无参数时 program_args 为空）
    cfg = parse_argv(['-c', '-f=a.tsuc', '-r'])
    assert cfg.compile is True
    assert cfg.run is True
    assert cfg.program_args == []


def test_duplicate_simple_flag():
    try:
        parse_argv(['-c', '-c'])
    except cli_parse_error as e:
        assert '重复选项: -c' in str(e)
    else:
        raise AssertionError('should raise cli_parse_error')


def test_duplicate_short_and_long():
    try:
        parse_argv(['-c', '--compile'])
    except cli_parse_error as e:
        assert '重复选项: -c' in str(e)
    else:
        raise AssertionError('should raise cli_parse_error')


def test_duplicate_run_passthrough():
    # -r 是参数边界，之后的全部 argv 原样透传，不参与重复检测
    cfg = parse_argv(['-f=a.tsuc', '-r', 'a', '-r'])
    assert cfg.run is True
    assert cfg.program_args == ['a', '-r']


def test_no_input_file():
    try:
        parse_argv(['-c'])
    except cli_parse_error as e:
        assert '未提供输入文件' in str(e)
    else:
        raise AssertionError('should raise cli_parse_error')


def test_nothing_to_do():
    try:
        parse_argv(['-q'])
    except cli_parse_error as e:
        assert '未指定任何操作' in str(e)
    else:
        raise AssertionError('should raise cli_parse_error')


def test_empty_argv():
    try:
        parse_argv([])
    except cli_parse_error as e:
        assert '未指定任何操作' in str(e)
    else:
        raise AssertionError('should raise cli_parse_error')


def test_unknown_option():
    try:
        parse_argv(['-z'])
    except cli_parse_error as e:
        assert '未知选项: -z' in str(e)
    else:
        raise AssertionError('should raise cli_parse_error')


def test_positional_argument():
    try:
        parse_argv(['abc.tsuc'])
    except cli_parse_error as e:
        assert '意外的位置参数' in str(e)
    else:
        raise AssertionError('should raise cli_parse_error')


def test_output_mode_valid():
    cfg = parse_argv(['-c', '-f=a.tsuc', '-o=min'])
    assert cfg.output_mode == 'min'


def test_output_mode_invalid():
    try:
        parse_argv(['-c', '-f=a.tsuc', '-o=bad'])
    except cli_parse_error as e:
        assert '无效的输出模式' in str(e)
    else:
        raise AssertionError('should raise cli_parse_error')


def test_output_mode_twice():
    try:
        parse_argv(['-c', '-f=a.tsuc', '-o=min', '-o=tidy'])
    except cli_parse_error as e:
        assert '输出模式指定了两次' in str(e)
    else:
        raise AssertionError('should raise cli_parse_error')


def test_file_twice():
    try:
        parse_argv(['-c', '-f=a.tsuc', '-f=b.tsuc'])
    except cli_parse_error as e:
        assert '输入文件指定了两次' in str(e)
    else:
        raise AssertionError('should raise cli_parse_error')


def test_file_empty():
    try:
        parse_argv(['-f='])
    except cli_parse_error as e:
        assert '-f= 需要提供路径' in str(e)
    else:
        raise AssertionError('should raise cli_parse_error')


def test_debug_lines_collected():
    cfg = parse_argv(['-c', '-f=a.tsuc', '-d=3', '-d=5'])
    assert cfg.debug_lines == [3, 5]


def test_debug_line_invalid():
    try:
        parse_argv(['-c', '-f=a.tsuc', '-d=x'])
    except cli_parse_error as e:
        assert '无效的断点行号' in str(e)
    else:
        raise AssertionError('should raise cli_parse_error')


def test_args_expand(tmp_path):
    args_file = tmp_path / 'args.json'
    args_file.write_text('["-c", "-f=b.tsuc"]', encoding = 'utf-8')
    cfg = parse_argv(['-a=' + str(args_file)])
    assert cfg.compile is True
    assert cfg.file == 'b.tsuc'


def test_args_missing_path():
    try:
        parse_argv(['-a='])
    except cli_parse_error as e:
        assert '-a= 需要提供路径' in str(e)
    else:
        raise AssertionError('should raise cli_parse_error')


def test_args_expand_cycle(tmp_path, monkeypatch):
    import cli_args
    monkeypatch.setattr(cli_args, '_max_expand_rounds', 2)
    args_file = tmp_path / 'args.json'
    args_file.write_text('["-a=' + str(args_file).replace('\\', '/') + '"]',
        encoding = 'utf-8')
    try:
        parse_argv(['-a=' + str(args_file)])
    except cli_parse_error as e:
        assert '展开层数过多' in str(e)
    else:
        raise AssertionError('should raise cli_parse_error')


def test_input_mode_without_file():
    cfg = parse_argv(['-i'])
    assert cfg.input_mode is True


def test_shell_mode():
    cfg = parse_argv(['-s'])
    assert cfg.shell_mode is True
