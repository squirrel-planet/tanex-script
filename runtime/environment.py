# 地址空间与作用域

from typing import Any

_addr_chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_'

class storage_cell:
    def __init__(self, address: str, value: Any = None):
        self.address = address
        self.value: Any = value
        self.is_const = False
        self.initialized = False

class address_space:
    def __init__(self):
        self.cells: dict[str, storage_cell] = {}
        self._count = 0

    def _alloc_address(self) -> str:
        n = self._count
        self._count += 1
        chars = []
        while True:
            chars.append(_addr_chars[n % 63])
            n = n // 63
            if n == 0:
                break
        return ''.join(reversed(chars))

    def allocate(self, value = None) -> storage_cell:
        addr = self._alloc_address()
        cell = storage_cell(addr, value)
        self.cells[addr] = cell
        return cell

    def get(self, addr: str):
        return self.cells.get(addr)

    def write(self, cell: storage_cell, value):
        if cell.is_const and cell.initialized:
            raise RuntimeError('常量不可修改: ' + cell.address)
        cell.value = value
        if cell.is_const:
            cell.initialized = True
        return value

    def mark_const(self, cell: storage_cell) -> None:
        cell.is_const = True

    def exists(self, addr: str) -> bool:
        return addr in self.cells

class scope:
    def __init__(self, parent = None):
        self.parent = parent
        self.is_function = False
        self.is_module = False
        self.names: dict[str, storage_cell] = {}

    def declare(self, name: str, cell: storage_cell) -> None:
        self.names[name] = cell

    def find(self, name: str):
        s = self
        while s is not None:
            if name in s.names:
                return s.names[name]
            s = s.parent
        return None

    def resolve(self, name: str) -> storage_cell:
        cell = self.find(name)
        if cell is None:
            raise RuntimeError('变量未定义: ' + name)
        return cell

    def find_local(self, name: str):
        return self.names.get(name)
