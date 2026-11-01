"""gvar tuple builders on the Roof Sans axis."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from functools import partial

from fontTools.misc.roundTools import otRound
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates
from fontTools.ttLib.tables.TupleVariation import TupleVariation
from fontTools.varLib.iup import iup_delta_optimize
from fontTools.varLib.models import VariationModel

from roofsans.axis import PJ_PEAK, ROOF_DEFAULT, ROOF_MIN

# The (0, 1, 1) tuple ramps to the 930 master at PJ_PEAK, then holds it to 1000.
_PJ_REGIONS = ((0.0, PJ_PEAK, 1.0), (PJ_PEAK, 1.0, 1.0))
# Pretendard's (−1, −1, 0) tuple is its 45 master. Roof's −1 is wght 100, where Pretendard
# has moved (400 − 100) / (400 − 45) of the way, so the tuple's deltas scale by that.
PJ_LIGHT = 45
PJ_LIGHT_SCALE = (ROOF_DEFAULT - ROOF_MIN) / (ROOF_DEFAULT - PJ_LIGHT)
LIGHT_REGION = (-1.0, -1.0, 0.0)


def scaled_tuple(tv: TupleVariation, scale: float, region: tuple[float, float, float]) -> TupleVariation:
    """``tv`` with each explicit delta scaled and rounded; IUP-omitted points stay omitted."""
    coords = [None if d is None else (otRound(d[0] * scale), otRound(d[1] * scale)) for d in tv.coordinates]
    return TupleVariation({"wght": region}, coords)


def remap_pretendard_tuples(tvs: list[TupleVariation], light: bool = True) -> list[TupleVariation]:
    """Pretendard JP's tuples on the Roof axis: the same weight shows the same outline from
    100 to 930, and the 930 outline holds to 1000. Without ``light`` the tuple below 400
    is dropped."""
    out = []
    for tv in tvs:
        region = tv.axes.get("wght")
        if len(tv.axes) != 1 or region is None:
            raise ValueError(f"unexpected Pretendard region {tv.axes}")
        if region == LIGHT_REGION:
            if light:
                out.append(scaled_tuple(tv, PJ_LIGHT_SCALE, LIGHT_REGION))
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
