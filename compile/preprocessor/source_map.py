class source_map(object):
    def __init__(self):
        self._map: dict[int, tuple[str, int]] = {}

    def set_line(self, resolved_line: int, file: str, original_line: int):
        self._map[resolved_line] = (file, original_line)

    def lookup(self, resolved_line: int) -> tuple[str, int] | None:
        return self._map.get(resolved_line)

    def merge(self, other: 'source_map', line_offset: int):
        for resolved_line, (file, original_line) in other._map.items():
            self._map[resolved_line + line_offset] = (file, original_line)
