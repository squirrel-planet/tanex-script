# -*- coding: utf-8 -*-
# Tanex Script 打包器。
# 流程：
#   1) PyInstaller --onedir 把 src/payload/tanex_app.py 打成 TanexScript.exe
#   2) 把 核心/ 下运行时需要的资源按原目录结构复制到 dist/TanexScript/
#   3) 压缩成 build/TanexScript.zip
#   4) PyInstaller --onefile --uac-admin 把 tools/installer.py 连 zip 打成 Setup.exe
#   5) 输出到 ../安装包/TanexScript_Setup.exe
# 用法：
#   python tools/packager.py
#   python tools/packager.py --skip-installer
#   python tools/packager.py --keep-temp

import os
import sys
import time
import shutil
import zipfile
import argparse
import datetime
import subprocess


here = os.path.dirname(os.path.abspath(__file__))
packager_root = os.path.dirname(here)
project_root = os.path.dirname(packager_root)
core_root = os.path.join(project_root, '核心')
docs_root = os.path.join(core_root, 'Tanex Script文档')
build_dir = os.path.join(packager_root, 'build')
dist_dir = os.path.join(packager_root, 'dist')
archive_dir = os.path.join(build_dir, '_archive')
output_dir = os.path.join(project_root, '安装包')
icon_path = os.path.join(packager_root, 'assets', 'tanex-script.ico')
payload_entry = os.path.join(packager_root, 'src', 'payload', 'tanex_app.py')
installer_entry = os.path.join(here, 'installer.py')
payload_zip = os.path.join(build_dir, 'TanexScript.zip')
payload_name = 'TanexScript'
setup_name = 'TanexScript_Setup'
version = 'Beta-1.2.3'

skip_suffixes = ('.pyc', '.bak')
skip_dirs = ('__pycache__', '.pytest_cache')
required_payload = (
    'TanexScript.exe',
    'runtime/bootstrap.tscc',
    'library/standard.tscl',
    'IDLE/tanex-script.ico',
    'IDLE/logo.png',
    'Tanex Script文档/index.md',
    'python_api/__init__.py',
    'standard_src/maths.tsuc',
)
smoke_cases = (
    ('版本号', ['-v'], 'Beta-1.2.3'),
    (
        '标准库快速幂',
        ['-t=import "library/standard"; standard.output(standard.maths.power_integer(2, 10), false);'],
        '1024'
    ),
    (
        '标准库位取反',
        ['-t=import "library/standard"; standard.output(standard.bit.bit_not(5), false);'],
        '2'
    ),
    (
        '重声明规则',
        ['-t=*a = 1; ***a = 2;'],
        '需先 delete 再声明'
    ),
    (
        '网络运算符已删除',
        ['-t=*a = 1 === 1;'],
        '语法错误'
    ),
)


def log(message):
    print('[packager] ' + message, flush = True)


def ensure_dir(path):
    os.makedirs(path, exist_ok = True)


# 用重命名把旧产物移进 _archive，避免直接删除触发批量删除保护。
def archive_old(path):
    if not os.path.exists(path):
        return
    ensure_dir(archive_dir)
    stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    target = os.path.join(archive_dir, os.path.basename(path) + '_old_' + stamp)
    if os.path.exists(target):
        target = target + '_' + str(os.getpid())
    os.rename(path, target)
    log('旧产物已归档: ' + target)


def run_pyinstaller(args):
    cmd = [sys.executable, '-m', 'PyInstaller', '--noconfirm'] + args
    log('执行: ' + ' '.join(cmd))
    result = subprocess.run(cmd, cwd = packager_root)
    if result.returncode != 0:
        raise RuntimeError('PyInstaller 失败，退出码 ' + str(result.returncode))


def copy_tree(src, dst, suffixes = None):
    if not os.path.isdir(src):
        raise RuntimeError('缺少资源目录: ' + src)
    for current, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        rel = os.path.relpath(current, src)
        target_dir = dst if rel == '.' else os.path.join(dst, rel)
        ensure_dir(target_dir)
        for name in files:
            if name.endswith(skip_suffixes):
                continue
            if suffixes and not name.endswith(suffixes):
                continue
            shutil.copy2(os.path.join(current, name), os.path.join(target_dir, name))


def stage_runtime_data(target):
    log('复制运行时资源到 ' + target)
    internal = os.path.join(target, '_internal')
    roots = [target]
    # PyInstaller 6 把 sys._MEIPASS 指向 _internal，冻结模块的 __file__
    # 也基于它，所以解释器要找的资源必须在 _internal 下再放一份。
    if os.path.isdir(internal):
        roots.append(internal)
    for base in roots:
        copy_tree(os.path.join(core_root, 'library'), os.path.join(base, 'library'))
        copy_tree(
            os.path.join(core_root, 'runtime'),
            os.path.join(base, 'runtime'),
            ('.tscc', '.tsuc')
        )
        copy_tree(
            os.path.join(core_root, 'standard_src'),
            os.path.join(base, 'standard_src'),
            ('.tsuc', '.tscc')
        )
        copy_tree(
            os.path.join(core_root, 'python_api'),
            os.path.join(base, 'python_api'),
            ('.py',)
        )
        copy_tree(
            docs_root,
            os.path.join(base, 'Tanex Script文档'),
            ('.md',)
        )
    idle_res = os.path.join(target, 'IDLE')
    ensure_dir(idle_res)
    for name in ('tanex-script.ico', 'logo.png'):
        src = os.path.join(core_root, 'IDLE', name)
        if not os.path.isfile(src):
            raise RuntimeError('缺少 IDLE 资源: ' + src)
        shutil.copy2(src, os.path.join(idle_res, name))
    stamp = datetime.datetime.now().isoformat(timespec = 'seconds')
    with open(os.path.join(target, 'VERSION.txt'), 'w', encoding = 'utf-8') as f:
        f.write('Tanex Script ' + version + '\n')
        f.write('构建时间: ' + stamp + '\n')
        f.write('入口: TanexScript.exe（无参数启动 IDLE，带参数作为命令行主程序）\n')


def verify_payload(target):
    for rel in required_payload:
        path = os.path.join(target, *rel.split('/'))
        if not os.path.isfile(path):
            raise RuntimeError('payload 缺少文件: ' + rel)
    internal = os.path.join(target, '_internal')
    if os.path.isdir(internal):
        for rel in (
            'runtime/bootstrap.tscc',
            'library/standard.tscl',
            'python_api/__init__.py',
            'standard_src/maths.tsuc',
        ):
            path = os.path.join(internal, *rel.split('/'))
            if not os.path.isfile(path):
                raise RuntimeError('payload 的 _internal 缺少文件: ' + rel)
    log('payload 关键文件校验通过')


def build_payload(stamp):
    payload_dist = os.path.join(build_dir, 'payload_' + stamp)
    work = os.path.join(build_dir, 'work_payload_' + stamp)
    ensure_dir(payload_dist)
    args = [
        '--onedir',
        '--console',
        '--name', payload_name,
        '--icon', icon_path,
        '--paths', core_root,
        '--paths', os.path.join(core_root, 'IDLE'),
        '--collect-all', 'tkinter',
        '--collect-all', 'prompt_toolkit',
        '--distpath', payload_dist,
        '--workpath', work,
        '--specpath', build_dir,
        payload_entry,
    ]
    run_pyinstaller(args)
    target = os.path.join(payload_dist, payload_name)
    exe = os.path.join(target, payload_name + '.exe')
    if not os.path.isfile(exe):
        raise RuntimeError('未找到 ' + exe + '，payload 打包失败')
    stage_runtime_data(target)
    verify_payload(target)
    return target


# 冻结环境下模块的 __file__ 是 PyInstaller 的虚拟路径，
# 这里打印出来，确认 bootstrap 与标准库能被现有路径解析找到。
def self_check(target):
    exe = os.path.join(target, payload_name + '.exe')
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    env['PYTHONUTF8'] = '1'
    common = {
        'cwd': target,
        'capture_output': True,
        'text': True,
        'encoding': 'utf-8',
        'errors': 'replace',
        'env': env,
        'timeout': 90
    }
    result = subprocess.run([exe, '--dump-paths'], **common)
    output = result.stdout or ''
    log('--- 冻结环境路径自检 ---')
    for line in output.splitlines():
        log(line)
    if result.returncode != 0:
        log('路径自检退出码 ' + str(result.returncode) + '，stderr: ' + (result.stderr or '')[-600:])
    imports = subprocess.run([exe, '--check-imports'], **common)
    log('--- 冻结环境导入自检 ---')
    for line in (imports.stdout or '').splitlines():
        log(line)
    if imports.returncode != 0 or 'imports_ok: True' not in (imports.stdout or ''):
        log('导入自检 stderr: ' + (imports.stderr or '')[-1200:])
        raise RuntimeError('冻结环境模块导入自检未通过')
    return output


# 在冻结产物上直接跑真实例句，确认引导库、标准库与本轮修复都进了安装包。
def run_smoke(target):
    exe = os.path.join(target, payload_name + '.exe')
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    env['PYTHONUTF8'] = '1'
    common = {
        'cwd': target,
        'capture_output': True,
        'text': True,
        'encoding': 'utf-8',
        'errors': 'replace',
        'env': env,
        'timeout': 90
    }
    log('--- 冻结环境行为冒烟 ---')
    for label, args, expected in smoke_cases:
        result = subprocess.run([exe] + args, **common)
        text = (result.stdout or '') + (result.stderr or '')
        if expected not in text:
            log(label + ' 输出: ' + text[-700:])
            raise RuntimeError('冒烟未通过: ' + label + '，期望包含 ' + expected)
        log('通过: ' + label)


# 若自检发现资源落在别的目录，按自检结果补一份，保证安装后能直接跑。
def adapt_paths(target, dump_output):
    values = {}
    for line in dump_output.splitlines():
        if ': ' in line:
            key, value = line.split(': ', 1)
            values[key] = value
    interpreter_dir = values.get('interpreter_dir', '')
    library_root = values.get('library_root', '')
    if interpreter_dir and os.path.isdir(interpreter_dir):
        dest = os.path.join(interpreter_dir, 'bootstrap.tscc')
        if not os.path.isfile(dest):
            shutil.copy2(os.path.join(target, 'runtime', 'bootstrap.tscc'), dest)
            log('已补充 bootstrap.tscc 到 ' + interpreter_dir)
    if library_root and os.path.isdir(library_root):
        dest = os.path.join(library_root, 'standard.tscl')
        if not os.path.isfile(dest):
            shutil.copy2(os.path.join(target, 'library', 'standard.tscl'), dest)
            log('已补充 standard.tscl 到 ' + library_root)
    if values.get('bootstrap_exists') != 'True' or values.get('standard_exists') != 'True':
        log('注意：自检报告资源未在预期位置，已按实际路径补齐，请复测安装包')


def make_zip(source):
    archive_old(payload_zip)
    count = 0
    with zipfile.ZipFile(payload_zip, 'w', zipfile.ZIP_DEFLATED, compresslevel = 6) as z:
        for current, dirs, files in os.walk(source):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for name in files:
                path = os.path.join(current, name)
                z.write(path, os.path.relpath(path, source).replace('\\', '/'))
                count += 1
    log('已生成 ' + payload_zip + '，' + str(count) + ' 个文件')


def build_installer(stamp):
    archive_old(os.path.join(dist_dir, setup_name + '.exe'))
    work = os.path.join(build_dir, 'work_installer_' + stamp)
    args = [
        '--onefile',
        '--windowed',
        '--uac-admin',
        '--name', setup_name,
        '--icon', icon_path,
        '--add-data', payload_zip + ';payload',
        '--collect-all', 'tkinter',
        '--collect-all', 'PIL',
        '--distpath', dist_dir,
        '--workpath', work,
        '--specpath', build_dir,
        installer_entry,
    ]
    run_pyinstaller(args)
    exe = os.path.join(dist_dir, setup_name + '.exe')
    if not os.path.isfile(exe):
        raise RuntimeError('未找到 ' + exe + '，安装包打包失败')
    return exe


def publish(setup_exe):
    ensure_dir(output_dir)
    final = os.path.join(output_dir, setup_name + '.exe')
    archive_old(final)
    shutil.move(setup_exe, final)
    log('已输出安装包: ' + final)
    return final


def cleanup(stamp):
    for path in (
        os.path.join(build_dir, 'payload_' + stamp),
        os.path.join(build_dir, 'work_payload_' + stamp),
        os.path.join(build_dir, 'work_installer_' + stamp),
    ):
        if os.path.isdir(path):
            try:
                shutil.rmtree(path)
                log('已删除临时目录: ' + path)
            except OSError as e:
                log('临时目录清理失败（可手动删除）: ' + path + ' ' + str(e))


def main():
    parser = argparse.ArgumentParser(description = 'Tanex Script 打包器')
    parser.add_argument(
        '--skip-installer',
        action = 'store_true',
        help = '只重新打 payload zip，不重新打安装包'
    )
    parser.add_argument(
        '--keep-temp',
        action = 'store_true',
        help = '保留构建临时目录'
    )
    args = parser.parse_args()

    try:
        import PyInstaller
    except ImportError:
        raise RuntimeError('当前解释器未安装 PyInstaller，请用 D:/python/python.exe 运行本脚本')
    if not os.path.isfile(icon_path):
        raise RuntimeError('缺少图标: ' + icon_path)
    if not os.path.isfile(os.path.join(core_root, 'main.py')):
        raise RuntimeError('缺少核心源码: ' + core_root)

    ensure_dir(build_dir)
    ensure_dir(dist_dir)
    ensure_dir(archive_dir)

    stamp = str(int(time.time()))
    log('使用解释器: ' + sys.executable)
    log('PyInstaller: ' + PyInstaller.__version__)
    target = build_payload(stamp)
    dump = self_check(target)
    run_smoke(target)
    adapt_paths(target, dump)
    make_zip(target)
    if args.skip_installer:
        log('仅重新生成了 payload zip，已保留在 build/ 下')
        return
    setup_exe = build_installer(stamp)
    final = publish(setup_exe)
    log('打包完成，安装包已输出到 ' + final)
    if not args.keep_temp:
        cleanup(stamp)


if __name__ == '__main__':
    main()
