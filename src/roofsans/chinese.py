"""The two GB 2312 hanzi levels, decoded with Python's pinned Unicode codec."""

from functools import cache


@cache
def gb2312_levels() -> tuple[tuple[int, ...], tuple[int, ...]]:
    levels = []
    for leads in (range(0xB0, 0xD8), range(0xD8, 0xF8)):
        points = set()
        for lead in leads:
            for trail in range(0xA1, 0xFF):
                try:
                    text = bytes((lead, trail)).decode('gb2312')
                except UnicodeDecodeError:
                    continue
                if len(text) == 1 and 0x4E00 <= ord(text) <= 0x9FFF:
                    points.add(ord(text))
        levels.append(tuple(sorted(points)))
    return levels[0], levels[1]


@cache
def gb2312_hanzi() -> tuple[int, ...]:
    return tuple(sorted(cp for level in gb2312_levels() for cp in level))
