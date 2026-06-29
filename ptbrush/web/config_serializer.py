"""
配置序列化器：在 pydantic 的 int 形态与"人类可读"形态之间双向转换。

pydantic 的 field_validator 会把 "1024GiB" 立刻 parse 成 int，
但 UI 和 toml 都需要保留单位字符串形式，所以这里要做反向格式化。
"""
from typing import Dict, List, Tuple

from config.config import parse_time_ranges

MASKED_SENTINEL = "***"

_SIZE_UNITS: List[Tuple[str, int]] = [
    ("TiB", 1024 ** 4),
    ("GiB", 1024 ** 3),
    ("MiB", 1024 ** 2),
    ("KiB", 1024),
    ("B", 1),
]

_SPEED_UNITS: List[Tuple[str, int]] = [
    ("GiB/s", 1024 ** 3),
    ("MiB/s", 1024 ** 2),
    ("KiB/s", 1024),
    ("B/s", 1),
]


def _humanize(n: int, units: List[Tuple[str, int]], default_unit: str) -> Dict[str, object]:
    if n <= 0:
        return {"value": 0, "unit": default_unit}
    for unit, factor in units:
        if n >= factor:
            value = n / factor
            if value == int(value):
                return {"value": int(value), "unit": unit}
            return {"value": round(value, 3), "unit": unit}
    return {"value": int(n), "unit": units[-1][0]}


def humanize_size(n: int) -> Dict[str, object]:
    """1099511627776 -> {value: 1024, unit: 'GiB'}; 优先整除单位、整数 value。"""
    return _humanize(int(n), _SIZE_UNITS, "GiB")


def humanize_speed(n: int) -> Dict[str, object]:
    """1966080 -> {value: 1.875, unit: 'MiB/s'}。"""
    return _humanize(int(n), _SPEED_UNITS, "MiB/s")


def to_unit_string(value: float, unit: str) -> str:
    """{value:1024, unit:'GiB'} -> '1024GiB'；整数值不带小数。"""
    if isinstance(value, float) and value == int(value):
        return f"{int(value)}{unit}"
    return f"{value}{unit}"


def expand_work_time(s: str) -> List[int]:
    """'22-23,0-2' -> [22, 23, 0, 1, 2]；空串返回空列表。"""
    if not s:
        return []
    hours: List[int] = []
    for start, end in parse_time_ranges(s):
        for h in range(start.hour, end.hour + 1):
            if h not in hours:
                hours.append(h)
    return hours


def compress_work_time(hours: List[int]) -> str:
    """
    [22,23,0,1,2] -> '0-2,22-23'；
    强制按 0-23 边界分段，不输出跨午夜的单段（与 parse_time_ranges 语义一致）。
    """
    if not hours:
        return ""
    sorted_hours = sorted(set(h for h in hours if 0 <= h <= 23))
    if not sorted_hours:
        return ""
    ranges: List[str] = []
    start = prev = sorted_hours[0]
    for h in sorted_hours[1:]:
        if h == prev + 1:
            prev = h
        else:
            ranges.append(f"{start}-{prev}")
            start = prev = h
    ranges.append(f"{start}-{prev}")
    return ",".join(ranges)


def mask(value: str) -> str:
    """非空字符串脱敏为 ***；空字符串保留为空（避免误导前端"已设置"）。"""
    return MASKED_SENTINEL if value else ""


def is_masked(value: str) -> bool:
    """前端回传时识别 mask 哨兵或空串，两种都视作"保留旧值"。"""
    return value == "" or value == MASKED_SENTINEL
