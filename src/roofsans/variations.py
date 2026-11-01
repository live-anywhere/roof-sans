"""gvar tuple builders on the Roof Sans axis."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from functools import partial

from fontTools.misc.roundTools import otRound
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates
from fontTools.ttLib.tables.TupleVariation import TupleVariation
from fontTools.varLib.iup import iup_delta_optimize
from fontTools.varLib.models import VariationModel

from roofsans.axis import PJ_PEAK

# The (0, 1, 1) tuple ramps to the 930 master at PJ_PEAK, then holds it to 1000.
_PJ_REGIONS = ((0.0, PJ_PEAK, 1.0), (PJ_PEAK, 1.0, 1.0))


def remap_pretendard_tuples(tvs: list[TupleVariation]) -> list[TupleVariation]:
    out = []
    for tv in tvs:
        region = tv.axes.get("wght")
        if len(tv.axes) != 1 or region is None:
            raise ValueError(f"unexpected Pretendard region {tv.axes}")
        if region[1] < 0:
            continue
        if region != (0.0, 1.0, 1.0):
            raise ValueError(f"unexpected Pretendard region {tv.axes}")
        for r in _PJ_REGIONS:
            out.append(TupleVariation({"wght": r}, list(tv.coordinates)))
    return out


def tuples_from_masters(
    masters: Mapping[float, Sequence[tuple[float, float]]], end_pts: list[int] | None
) -> list[TupleVariation]:
    """Build tuples that reproduce ``masters`` (Roof normalized location → coords)."""
    if 0.0 not in masters:
        raise ValueError("masters must include the default location 0.0")
    locs = sorted(masters)
    model = VariationModel([{"wght": t} if t else {} for t in locs], axisOrder=["wght"])
    values = [GlyphCoordinates(masters[t]) for t in locs]
    deltas, supports = model.getDeltasAndSupports(
        values, round=partial(GlyphCoordinates.__round__, round=otRound)
    )
    base = list(masters[0.0])
    out = []
    for delta, support in zip(deltas[1:], supports[1:]):
        d = [tuple(p) for p in delta]
        if not any(x or y for x, y in d):
            continue
        if end_pts is not None:
            d = iup_delta_optimize(d, base, end_pts, tolerance=0.5)
        out.append(TupleVariation(dict(support), list(d)))
    return out
