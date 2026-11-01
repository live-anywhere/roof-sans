"""Roof Sans wght axis constants and normalization.

The axis runs 100–1000 with its default at 400. Normalized t is (wght − 400) / 600 at
and above the default, as on Wanted Sans's own 400–1000 axis, and (wght − 400) / 300
below it, so t = −1 is wght 100. Every tuple above 400 therefore reads the same as in
Wanted Sans.
"""

from __future__ import annotations

ROOF_MIN = 100
ROOF_DEFAULT = 400
ROOF_MAX = 1000
# Pretendard JP's 930 master on the Roof axis (530/600), stored as F2Dot14.
PJ_PEAK = 14473 / 16384
# Wanted Sans's 750 master, as stored in its gvar regions.
W_MID = 0.58331298828125
# The light masters: wght 100 and 250. H4 and H5 solve their parameters at both, because
# w′ and δy are not linear in weight. Composites take both too, since some (H2, unit
# squares) hold H4 parts; H3's enclosed figures and signs, built only from Wanted Sans
# parts, which vary linearly below 400, use 100 alone (``h3_enclosed.W_LOCS``).
H4_LOCS = (-1.0, -0.5, 0.0, 0.5, 0.75, 1.0)
COMPOSITE_LOCS = (-1.0, -0.5, 0.0, 0.5, W_MID, 1.0)


def roof_norm(wght: float) -> float:
    if wght < ROOF_DEFAULT:
        return (wght - ROOF_DEFAULT) / (ROOF_DEFAULT - ROOF_MIN)
    return (wght - ROOF_DEFAULT) / (ROOF_MAX - ROOF_DEFAULT)


def roof_wght(norm: float) -> float:
    if norm < 0:
        return ROOF_DEFAULT + norm * (ROOF_DEFAULT - ROOF_MIN)
    return ROOF_DEFAULT + norm * (ROOF_MAX - ROOF_DEFAULT)
