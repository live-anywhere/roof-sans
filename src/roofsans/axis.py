"""Roof Sans wght axis constants and normalization."""

from __future__ import annotations

ROOF_MIN = 400
ROOF_MAX = 1000
# Pretendard JP's 930 master on the Roof axis (530/600), stored as F2Dot14.
PJ_PEAK = 14473 / 16384
# Wanted Sans's 750 master, as stored in its gvar regions.
W_MID = 0.58331298828125
H4_LOCS = (0.0, 0.5, 0.75, 1.0)
COMPOSITE_LOCS = (0.0, 0.5, W_MID, 1.0)


def roof_norm(wght: float) -> float:
    return (wght - ROOF_MIN) / (ROOF_MAX - ROOF_MIN)


def roof_wght(norm: float) -> float:
    return ROOF_MIN + norm * (ROOF_MAX - ROOF_MIN)
