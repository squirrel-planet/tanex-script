#!/usr/bin/env python
# Tanex Script 回归测试运行器
#
# 用法（务必在 核心/ 目录下执行）：
#   python tests/regression/run.py                 跑全部用例
#   python tests/regression/run.py test_pyapi      只跑指定用例（可写多个名字）
#   python tests/regression/run.py --update        重新采集期望输出并覆盖 expected.json
#
# 每个用例的流程：
#   cases/<name>.tsuc -> .build/<name>.tsuc -> main.py -c 编译
#   -> main.py -r 运行 -> 去掉解释器装饰行后与 expected.json 逐字比对。
# 编译失败、运行失败、输出不符、出现 *_FAIL 标记，都判为失败；退出码非 0。
# 编译产物只落在 .build/ 中，不会污染 cases/ 和核心根目录。

import glob
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CORE = os.path.normpath(os.path.join(HERE, '..', '..'))
CASES = os.path.join(HERE, 'cases')
BUILD = os.path.join(HERE, '.build')
EXPECTED = os.path.join(HERE, 'expected.json')


def clean_output(text):
    # 解释器会输出 "·开始运行 ..." / "·已编译 ..." 之类的装饰行，剔除后
    # 剩下的就是测试脚本自己 standard.output 出来的结果串。
    return ''.join(
        line.strip() for line in text.splitlines()
        if line.strip() and not line.strip().startswith('·')
    )


def run_case(name):
    src = os.path.join(CASES, name + '.tsuc')
    tmp_tsuc = os.path.join(BUILD, name + '.tsuc')
    tmp_tscc = os.path.join(BUILD, name + '.tscc')
    shutil.copyfile(src, tmp_tsuc)

    compiled = subprocess.run(
        [sys.executable, 'main.py', '-f=' + tmp_tsuc, '-c'],
        cwd=CORE, capture_output=True, text=True, timeout=120
    )
    if compiled.returncode != 0:
        return 'COMPILE_FAIL', clean_output(compiled.stdout + compiled.stderr), ''

    result = subprocess.run(
        [sys.executable, 'main.py', '-f=' + tmp_tscc, '-r'],
        cwd=CORE, capture_output=True, text=True, timeout=120
    )
    actual = clean_output(result.stdout)
    if result.returncode != 0:
        return 'RUN_FAIL', actual, ''
    return 'OK', actual, actual


def main(argv):
    update = '--update' in argv
    filters = [a for a in argv if not a.startswith('-')]
    names = sorted(
        os.path.splitext(os.path.basename(p))[0]
        for p in glob.glob(os.path.join(CASES, '*.tsuc'))
    )
    if filters:
        names = [n for n in names if n in filters]
    if not names:
        print('没有匹配的回归用例')
        return 1
    if not os.path.isfile(EXPECTED) and not update:
        print('缺少 expected.json，请先运行：python tests/regression/run.py --update')
        return 1

    os.makedirs(BUILD, exist_ok=True)
    expected = {}
    if os.path.isfile(EXPECTED):
        with open(EXPECTED, 'r', encoding='utf-8') as f:
            expected = json.load(f)

    collected, failed = {}, []
    for name in names:
        status, actual, _ = run_case(name)
        if status != 'OK':
            failed.append((name, status, actual))
            print('  FAIL  %-20s %s %s' % (name, status, actual[:120]))
            continue
        if update:
            collected[name] = actual
            print('  BASE  %-20s %s' % (name, actual[:100]))
        elif name not in expected:
            failed.append((name, 'NO_EXPECTED', actual))
            print('  FAIL  %-20s expected.json 中没有该用例' % name)
        elif actual != expected[name]:
            failed.append((name, 'MISMATCH', actual))
            print('  FAIL  %-20s 输出不符' % name)
            print('         期望: ' + expected[name][:200])
            print('         实际: ' + actual[:200])
        elif '_FAIL|' in actual or '_FAIL:' in actual:
            failed.append((name, 'FAIL_MARKER', actual))
            print('  FAIL  %-20s 输出中出现 *_FAIL 标记' % name)
        else:
            print('  PASS  %-20s %d 项断言' % (name, actual.count('_OK|') + actual.count('_OK:')))

    if update and not failed:
        merged = dict(expected)
        merged.update(collected)
        with open(EXPECTED, 'w', encoding='utf-8') as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
        print('已更新 expected.json（用例数 %d）' % len(merged))

    # 清理本轮编译产物，保持 .build/ 为空
    for p in glob.glob(os.path.join(BUILD, '*')):
        try:
            os.remove(p)
        except OSError:
            pass

    print('-' * 60)
    print('回归测试：%d 个用例，%d 通过，%d 失败' % (len(names), len(names) - len(failed), len(failed)))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
