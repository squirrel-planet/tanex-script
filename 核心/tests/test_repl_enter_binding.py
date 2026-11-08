import sys

sys.path.insert(0, '..')

from prompt_toolkit.buffer import Buffer
from runtime.repl import _batch_key_bindings

def _enter_handler():
    bindings = _batch_key_bindings()
    for binding in bindings.bindings:
        if getattr(binding.handler, '__name__', '') == '_on_enter':
            return binding.handler
    raise AssertionError('批量输入模式没有注册 Enter 绑定')

class _fake_event:

    def __init__(self, buffer):
        self.current_buffer = buffer

def test_enter_inserts_indented_newline():
    # 修复前：prompt_toolkit 3.x 的 Buffer 没有 text_before_cursor 属性，
    # 按 Enter 会抛 AttributeError；异常发生在事件循环里，
    # read_console_source 的 except 兜底接不到，只能看到 Unhandled exception
    buffer = Buffer()
    buffer.insert_text('  a = 1')

    _enter_handler()(_fake_event(buffer))

    assert buffer.text == '  a = 1\n  '
