"""Wanted Sans below 400: light tuples extrapolated from its own 400 → 550 movement.

Wanted Sans has masters only at 400 and 1000 (and 750 for 70 glyphs). Between 400 and
750 every point moves on a straight line, so continuing that line below 400 gives a
lighter outline with the same structure. The build adds one tuple per varying glyph on
the region (−1, −1, 0), which reaches its full delta at wght 100.

How far the line goes is set by Pretendard JP, the source of the Han and kana glyphs
that sit next to Wanted Sans's Hangul: at wght 100 the median ink area of the 2,350
KS X 1001 Hangul syllables equals Pretendard's. That extrapolation weight (``LightData.wght``,
126.0 on the pinned inputs) is what Roof Sans shows as 100; both fonts are linear below 400, so they keep
matching between 100 and 400.

A glyph whose extrapolated outline breaks its own contour structure (a fold, a reversed
or collapsed contour, against the 550 outline) stops at the lightest whole weight that
keeps it intact. Wanted Sans's GDEF variation rows (kerning and anchors) are extended
the same way.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from statistics import median

import fontTools.varLib.builder  # noqa: F401 (registers VarData.optimize)
from fontTools.misc.roundTools import otRound
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables
from fontTools.ttLib.tables.TupleVariation import TupleVariation
from fontTools.varLib.iup import iup_delta, iup_delta_optimize
from fontTools.varLib.models import supportScalar

from roofsans.axis import ROOF_DEFAULT, ROOF_MIN, W_MID
from roofsans.measure import ink_area
from roofsans.outline import Outline, Point
from roofsans.sampling import PretendardSampler, WantedSampler
from roofsans.sanity import check_outline
from roofsans.variations import LIGHT_REGION

# The in-range sample that sets each point's direction: wght 550, inside 400–750.
SLOPE_NORM = 0.25
SLOPE_WGHT = 550
# Wanted Sans's own regions; all of them are linear from 0 to SLOPE_NORM.
_WANTED_REGIONS = {(0.0, 1.0, 1.0), (0.0, W_MID, 1.0), (W_MID, 1.0, 1.0)}
# The extrapolation weight is solved in [SEARCH_MIN, ROOF_DEFAULT] and rounded to a quarter.
SEARCH_MIN = 50.0
WGHT_STEP = 0.25


def ks_hangul() -> tuple[int, ...]:
    """The 2,350 Hangul syllables of KS X 1001 (EUC-KR rows 0xB0–0xC8)."""
    return tuple(ord(bytes((hi, lo)).decode("euc_kr")) for hi in range(0xB0, 0xC9) for lo in range(0xA1, 0xFF))


@dataclass
class LightData:
    """The light tuples and GDEF rows for Wanted Sans, solved once per build."""

    wght: float
    tuples: dict[str, TupleVariation] = field(default_factory=dict)
    clamped: dict[str, float] = field(default_factory=dict)
    # (VarData index, item index) → delta on LIGHT_REGION.
    rows: dict[tuple[int, int], int] = field(default_factory=dict)


def _check_regions(font: TTFont) -> None:
    for name, tvs in font["gvar"].variations.items():
        for tv in tvs:
            if len(tv.axes) != 1 or tuple(tv.axes["wght"]) not in _WANTED_REGIONS:
                raise ValueError(f"{name}: unexpected Wanted Sans region {tv.axes}")
    store = font["GDEF"].table.VarStore
    for r in store.VarRegionList.Region:
        (axis,) = r.VarRegionAxis
        if (axis.StartCoord, axis.PeakCoord, axis.EndCoord) not in _WANTED_REGIONS:
            raise ValueError(f"unexpected Wanted Sans GDEF region {axis.StartCoord, axis.PeakCoord, axis.EndCoord}")


def _extrapolated(a: Outline, b: Outline, wght: float) -> Outline:
    """The line through ``a`` (400) and ``b`` (550), at ``wght``."""
    k = (wght - ROOF_DEFAULT) / (SLOPE_WGHT - ROOF_DEFAULT)
    coords = [(x0 + (x1 - x0) * k, y0 + (y1 - y0) * k) for (x0, y0), (x1, y1) in zip(a.coords, b.coords)]
    return Outline(coords, list(a.end_pts), list(a.flags))


def solve_wght(ws: WantedSampler, ps: PretendardSampler, wanted: TTFont, pretendard: TTFont) -> float:
    """The extrapolation weight at which Wanted Sans's median Hangul ink equals Pretendard's at 100.

    An outline's area is a quadratic function of the extrapolation weight (it is bilinear
    in the points, which move linearly), so three samples give it exactly.
    """
    wcmap, pcmap = wanted.getBestCmap(), pretendard.getBestCmap()
    fits, targets = [], []
    for cp in ks_hangul():
        a, b = ws.outline(wcmap[cp], ROOF_DEFAULT), ws.outline(wcmap[cp], SLOPE_WGHT)
        k0, k1, km = ink_area(a), ink_area(b), ink_area(_extrapolated(a, b, 2 * ROOF_DEFAULT - SLOPE_WGHT))
        # A(k) = k0 + c1·k + c2·k² with k = (w − 400) / 150.
        fits.append((k0, (k1 - km) / 2, (k1 + km) / 2 - k0))
        targets.append(ink_area(ps.outline(pcmap[cp], ROOF_MIN)))

    def ratio(w: float) -> float:
        k = (w - ROOF_DEFAULT) / (SLOPE_WGHT - ROOF_DEFAULT)
        return median(abs(c0 + c1 * k + c2 * k * k) / t for (c0, c1, c2), t in zip(fits, targets))

    lo, hi = SEARCH_MIN, float(ROOF_DEFAULT)
    if not ratio(lo) < 1 < ratio(hi):
        raise ValueError(f"light weight: no extrapolation in [{lo:g}, {hi:g}] matches Pretendard at {ROOF_MIN}")
    while hi - lo > WGHT_STEP / 8:
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if ratio(mid) < 1 else (lo, mid)
    return round((lo + hi) / 2 / WGHT_STEP) * WGHT_STEP


def _light_tuple(base: list[Point], slope: list[Point], wght: float, end_pts: list[int] | None) -> TupleVariation | None:
    """The LIGHT_REGION tuple that moves ``base`` along ``slope`` (the 400 → 550 movement) to ``wght``."""
    k = (wght - ROOF_DEFAULT) / (SLOPE_WGHT - ROOF_DEFAULT)
    deltas = [(otRound(dx * k), otRound(dy * k)) for dx, dy in slope]
    if not any(x or y for x, y in deltas):
        return None
    if end_pts is not None:
        deltas = iup_delta_optimize(deltas, base, end_pts, tolerance=0.5)
    return TupleVariation({"wght": LIGHT_REGION}, list(deltas))


def _stored(o: Outline, tv: TupleVariation | None) -> Outline:
    """``o`` (the 400 outline, with phantoms) moved by the full delta of ``tv``."""
    if tv is None:
        return o
    deltas = tv.coordinates
    if None in deltas:
        deltas = iup_delta(deltas, [tuple(p) for p in o.coords], o.end_pts)
    return Outline([(x + d[0], y + d[1]) for (x, y), d in zip(o.coords, deltas)], list(o.end_pts), list(o.flags))


def solve(wanted: TTFont, pretendard: TTFont) -> LightData:
    """Light tuples for every varying Wanted Sans glyph and its GDEF rows (see the module docstring)."""
    _check_regions(wanted)
    ws, ps = WantedSampler(wanted), PretendardSampler(pretendard)
    light = LightData(solve_wght(ws, ps, wanted, pretendard))
    for name in wanted.getGlyphOrder():
        if not wanted["gvar"].variations.get(name):
            continue
        base, controls = ws._varied(name, 0.0)
        moved, _ = ws._varied(name, SLOPE_NORM)
        slope = [(x1 - x0, y1 - y0) for (x0, y0), (x1, y1) in zip(base, moved)]
        simple = controls.numberOfContours > 0
        end_pts = list(controls.endPts) if simple else None
        wght = light.wght
        tv = _light_tuple(base, slope, wght, end_pts)
        if simple:
            a = ws.outline(name, ROOF_DEFAULT)
            reference = ws.outline(name, SLOPE_WGHT)
            # Integer weights from the solved one up to 400, until the stored outline is intact.
            while check_outline(_stored(a, tv), reference):
                wght = float(int(wght) + 1)
                if wght >= ROOF_DEFAULT:
                    raise ValueError(f"{name}: no light extrapolation keeps the outline intact")
                tv = _light_tuple(base, slope, wght, end_pts)
            if wght != light.wght:
                light.clamped[name] = wght
        if tv is not None:
            light.tuples[name] = tv
    if light.clamped:
        listed = " ".join(f"{n}@{w:g}" for n, w in light.clamped.items())
        print(f"light: {len(light.clamped)} Wanted Sans glyphs stop above {light.wght:g}: {listed}", file=sys.stderr)

    store = wanted["GDEF"].table.VarStore
    regions = [r.VarRegionAxis[0] for r in store.VarRegionList.Region]
    scalars = [supportScalar({"wght": SLOPE_NORM}, {"wght": (a.StartCoord, a.PeakCoord, a.EndCoord)}) for a in regions]
    k = (light.wght - ROOF_DEFAULT) / (SLOPE_WGHT - ROOF_DEFAULT)
    for outer, data in enumerate(store.VarData):
        for inner, item in enumerate(data.Item):
            moved = sum(d * scalars[ri] for d, ri in zip(item, data.VarRegionIndex))
            delta = otRound(moved * k)
            if delta:
                light.rows[(outer, inner)] = delta
    return light


def extend_wanted(font: TTFont, light: LightData) -> None:
    """Add ``light``'s tuples and GDEF rows to Wanted Sans ``font`` and lower its axis to ROOF_MIN.

    Every value at and above 400 stays as it was: the new region is zero there.
    """
    gvar = font["gvar"].variations
    for name, tv in light.tuples.items():
        gvar[name] = [*gvar[name], TupleVariation(dict(tv.axes), list(tv.coordinates))]

    store = font["GDEF"].table.VarStore
    region = otTables.VarRegion()
    axis = otTables.VarRegionAxis()
    axis.StartCoord, axis.PeakCoord, axis.EndCoord = LIGHT_REGION
    region.VarRegionAxis = [axis]
    region.VarRegionAxisCount = 1
    index = len(store.VarRegionList.Region)
    store.VarRegionList.Region.append(region)
    store.VarRegionList.RegionCount = index + 1
    outers = {o for o, _ in light.rows}
    for outer, data in enumerate(store.VarData):
        if outer not in outers:
            continue
        data.VarRegionIndex = [*data.VarRegionIndex, index]
        data.VarRegionCount = len(data.VarRegionIndex)
        data.Item = [[*item, light.rows.get((outer, inner), 0)] for inner, item in enumerate(data.Item)]
        data.optimize()

    (wght,) = (a for a in font["fvar"].axes if a.axisTag == "wght")
    wght.minValue = ROOF_MIN
