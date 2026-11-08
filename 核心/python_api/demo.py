# python_api 示例模块：演示函数、常量、类与对象投影

__all__ = [
    'add', 'greet', 'echo', 'sum_list', 'describe', 'is_point', 'coord_x',
    'make_point', 'make_slot_point', 'point', 'slot_point', 'VERSION',
    'ITEMS', 'CONFIG', 'mutate_list', 'mutate_dict', 'bump_version',
    'bump_point', 'guarded_point', 'make_guarded_point', 'locked_value',
    'list_size', 'list_first', 'dict_a', 'dict_c',
    'clamped_point', 'make_clamped_point', 'clamped_value',
    'make_counter', 'raw_bytes', 'iter_map'
]

VERSION = '1.0'
ITEMS = [10, 20]
CONFIG = {'a': 1}


def mutate_list():
    # 投影生成之后就地修改 Python 侧容器，验证 TanexScript 读时同步
    ITEMS[0] = 99
    ITEMS.append(30)
    return len(ITEMS)


def mutate_dict():
    CONFIG['a'] = 7
    CONFIG['b'] = 2
    return len(CONFIG)


def bump_version():
    global VERSION
    VERSION = '2.0'
    return VERSION


def bump_point(value, dx):
    # 不返回对象，只改属性：TanexScript 侧必须靠下次成员读取看到新值
    value.x = value.x + dx
    return value.x


def list_size():
    return len(ITEMS)


def list_first():
    return ITEMS[0]


def dict_a():
    return CONFIG.get('a', -1)


def dict_c():
    return CONFIG.get('c', -1)


def add(a, b):
    return a + b


def greet(name):
    return 'hello ' + name


def echo(value):
    # 验证 ts_to_py → Python → py_to_ts 的往返
    return value


def sum_list(items):
    total = 0
    for v in items:
        total = total + v
    return total


def describe(value):
    # 用于验证 TanexScript 值 → Python 值的还原结果
    return 'VAL=' + repr(value)


def is_point(value):
    # 验证 object 投影包装器能还原成原始 Python 对象
    return 'POINT_OK|' if isinstance(value, point) else 'POINT_FAIL|'


def coord_x(value):
    # 从原始 Python 对象读属性，用于验证 TanexScript 侧赋值是否回写成功
    return value.x


class slot_point:
    __slots__ = ('px', 'py')

    def __init__(self, px, py):
        self.px = px
        self.py = py

    def shift(self, dx):
        self.px = self.px + dx
        return self.px


def make_slot_point(px, py):
    return slot_point(px, py)


class point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def move(self, dx, dy):
        self.x = self.x + dx
        self.y = self.y + dy
        return self


def make_point(x, y):
    return point(x, y)


class guarded_point:
    # 只读 property：TanexScript 侧赋值会因 setattr 失败而触发写回回滚
    __slots__ = ('_v',)

    def __init__(self, v):
        self._v = v

    @property
    def locked(self):
        return self._v


def make_guarded_point(v):
    return guarded_point(v)


def locked_value(value):
    return value.locked


class clamped_point:
    # setter 会把写入值归一化到 0..100，用于验证写回后的读回校正
    def __init__(self, v):
        self.v = v

    @property
    def value(self):
        return self.v

    @value.setter
    def value(self, x):
        self.v = max(0, min(100, x))


def make_clamped_point(v):
    return clamped_point(v)


def clamped_value(value):
    return value.value


def make_counter(n):
    # 返回生成器：桥接层应物化为 list，而不是投影 gi_frame / gi_code
    return (x * x for x in range(n))


def raw_bytes():
    return b'AB'


def iter_map(values):
    # map 也是迭代器，验证通用 Iterator 物化
    return map(lambda v: v + 1, values)
