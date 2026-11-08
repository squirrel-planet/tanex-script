import os
import subprocess
import sys
import pytest

main_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'main.py')

def _run_main(args, cwd):
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    return subprocess.run(
        [sys.executable, main_path] + args,
        cwd = cwd,
        capture_output = True,
        text = True,
        encoding = 'utf-8',
        env = env,
        timeout = 60
    )

def _combined(result):
    return result.stdout + result.stderr

def test_temp_cli_runs_inline_code(tmp_path):
    result = _run_main(['-t=standard_output << 65;'], tmp_path)
    assert result.returncode == 0
    assert 'A' in _combined(result)

def test_temp_cli_does_not_write_output_file(tmp_path):
    result = _run_main(['-t=standard_output << 65;'], tmp_path)
    assert result.returncode == 0
    assert list(tmp_path.iterdir()) == []

def test_temp_cli_long_option(tmp_path):
    result = _run_main(['--temp=standard_output << 66;'], tmp_path)
    assert result.returncode == 0
    assert 'B' in _combined(result)

def test_temp_cli_multiline_code(tmp_path):
    code = 'standard_output << 65;\nstandard_output << 66;'
    result = _run_main([f'-t={code}'], tmp_path)
    assert result.returncode == 0
    assert 'AB' in _combined(result)

def test_temp_cli_quiet(tmp_path):
    result = _run_main(['-q', '-t=standard_output << 65;'], tmp_path)
    assert result.returncode == 0
    assert '开始运行' not in _combined(result)
    assert 'A' in _combined(result)

@pytest.mark.parametrize(
    'extra, flag',
    [
        ('-c', 'c'),
        ('-r', 'r'),
        ('-s', 's'),
        ('-i', 'i'),
        ('-f=x.tsuc', 'f'),
        ('-o=min', 'o')
    ]
)
def test_temp_cli_conflicts(tmp_path, extra, flag):
    result = _run_main(['-t=standard_output << 65;', extra], tmp_path)
    assert result.returncode == 1
    assert f'-t 与 -{flag} 冲突' in _combined(result)

def test_temp_cli_empty_code(tmp_path):
    result = _run_main(['-t='], tmp_path)
    assert result.returncode == 1
    assert '-t= 需要提供代码' in _combined(result)

def test_temp_cli_syntax_error_shows_source(tmp_path):
    result = _run_main(['-t=standard_output << ;'], tmp_path)
    assert result.returncode == 1
    output = _combined(result)
    assert '语法错误' in output
    assert '<temp>' in output
    assert 'standard_output << ;' in output

def test_temp_cli_runtime_error_shows_source(tmp_path):
    result = _run_main(['-t=standard_output << missing;'], tmp_path)
    assert result.returncode == 1
    output = _combined(result)
    assert '变量未定义: missing' in output
    assert '<temp>' in output
    assert 'standard_output << missing;' in output
