"""Small coordinate helpers shared by the unit tests."""

from __future__ import annotations

from collections.abc import Sequence

from fontTools.ttLib.tables._g_l_y_f import Glyph
from fontTools.ttLib.tables.TupleVariation import TupleVariation
from fontTools.varLib.iup import iup_delta
from fontTools.varLib.models import supportScalar

Point = tuple[float, float]


def _expanded(tv: TupleVariation, coords: Sequence[Point], end_pts: list[int] | None) -> list[Point]:
    if None not in tv.coordinates:
        return list(tv.coordinates)
    if end_pts is None:
        raise ValueError("IUP-omitted deltas need end_pts")
    return iup_delta(tv.coordinates, coords, end_pts)


def apply(
    coords: Sequence[Point], tvs: list[TupleVariation], norm: float, end_pts: list[int] | None = None
) -> list[Point]:
    """Return ``coords`` (outline plus 4 phantom points) moved by ``tvs`` at ``norm``."""
    out = [tuple(map(float, p)) for p in coords]
    for tv in tvs:
        s = supportScalar({"wght": norm}, tv.axes)
        if s == 0:
            continue
        for i, d in enumerate(_expanded(tv, coords, end_pts)):
            out[i] = (out[i][0] + d[0] * s, out[i][1] + d[1] * s)
    return out


def interpolated_coords(glyf, name: str, tvs: list[TupleVariation], norm: float) -> list[Point]:
    """Return the outline points of simple glyph ``name`` with ``tvs`` applied at ``norm``."""
    g = glyf[name]
    coords = [tuple(p) for p in g.coordinates] + [(0, 0)] * 4
    return apply(coords, tvs, norm, list(g.endPtsOfContours))[:-4]


def max_abs_diff(a: Sequence[Point] | Glyph, b: Sequence[Point] | Glyph) -> float:
    """Return the largest coordinate difference between two equally long point lists."""
    pa = list(a.coordinates) if isinstance(a, Glyph) else list(a)
    pb = list(b.coordinates) if isinstance(b, Glyph) else list(b)
    if len(pa) != len(pb):
        raise ValueError(f"point counts differ: {len(pa)} != {len(pb)}")
    return max((max(abs(p[0] - q[0]), abs(p[1] - q[1])) for p, q in zip(pa, pb)), default=0.0)
