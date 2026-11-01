"""C1/C2: calibrated Source Han Sans CN masters and Simplified Chinese forms."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from statistics import median

from fontTools.misc.roundTools import otRound
from fontTools.pens.areaPen import AreaPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates
from fontTools.ttLib.tables.TupleVariation import TupleVariation
from fontTools.varLib.iup import iup_delta_optimize

from roofsans.chinese import gb2312_hanzi
from roofsans.newglyph import NewGlyph
from roofsans.outline import Outline
from roofsans.selection import Rule
from roofsans.variations import remap_pretendard_tuples


@dataclass(frozen=True)
class Calibration:
    w400: float
    w930: float
    scale: float
    dx400: float
    dy400: float
    dx930: float
    dy930: float


def _form_sets(ctx) -> tuple[tuple[int, ...], tuple[int, ...]]:
    if ctx.chinese_sets is None:
        cn, jp = ctx.shs_cn.getBestCmap(), ctx.shs_jp.getBestCmap()
        cgs, jgs = ctx.shs_cn.getGlyphSet(), ctx.shs_jp.getGlyphSet()
        same, different = [], []
        for cp in gb2312_hanzi():
            if ctx.selection.rules[cp] is Rule.C1_HANZI:
                continue
            if cp not in jp:
                different.append(cp)
                continue
            a, b = DecomposingRecordingPen(cgs), DecomposingRecordingPen(jgs)
            cgs[cn[cp]].draw(a)
            jgs[jp[cp]].draw(b)
            equal = a.value == b.value and cgs[cn[cp]].width == jgs[jp[cp]].width
            (same if equal else different).append(cp)
        ctx.chinese_sets = (tuple(same), tuple(different))
    return ctx.chinese_sets


def calibration_set(ctx) -> tuple[int, ...]:
    return _form_sets(ctx)[0]


def zhs_forms(ctx) -> tuple[int, ...]:
    return _form_sets(ctx)[1]


def ink_bounds(outline: Outline) -> tuple[float, float, float, float]:
    """True curve ink bounds; the global Outline.bounds includes control points."""
    glyph = outline.to_glyph()
    glyph.coordinates = GlyphCoordinates(outline.points)
    pen = BoundsPen(None)
    glyph.draw(pen, None)
    return pen.bounds or (0.0, 0.0, 0.0, 0.0)


def ink_area(outline: Outline) -> float:
    """Absolute signed curve area, without rounding the sampled outline."""
    glyph = outline.to_glyph()
    glyph.coordinates = GlyphCoordinates(outline.points)
    pen = AreaPen(None)
    glyph.draw(pen, None)
    return abs(pen.value)


def transform(outline: Outline, scale: float, dx: float, dy: float) -> Outline:
    moved = outline.transformed(lambda x, y: (scale * x + dx, scale * y + dy))
    moved.coords[-4:] = [(0, 0), (1920, 0), (0, 0), (0, 0)]
    return moved


def calibrate(ctx) -> Calibration:
    if ctx.calibration is not None:
        return ctx.calibration
    points = calibration_set(ctx)
    pcmap, jcmap = ctx.pretendard.getBestCmap(), ctx.shs_jp.getBestCmap()
    scale = 1.92
    values = []
    for master, lower, upper in ((400, 350.0, 420.0), (930, 850.0, 900.0)):
        lo, hi = lower, upper
        targets = [ctx.ps.outline(pcmap[cp], master) for cp in points]
        areas = [ink_area(o) for o in targets]

        def ratio(w):
            return median(a / (ink_area(ctx.js.outline(jcmap[cp], w)) * scale**2)
                          for cp, a in zip(points, areas))

        if ratio(hi) >= 1:
            weight = hi
        elif ratio(lo) <= 1:
            weight = lo
        else:
            while hi - lo > 0.01:
                mid = (lo + hi) / 2
                if ratio(mid) > 1:
                    lo = mid
                else:
                    hi = mid
            weight = round((lo + hi) / 2 * 4) / 4
        if (master == 400 and weight in (lower, upper)) or (master == 930 and weight == lower):
            raise ValueError(
                f'Han calibration w{master} reached search bound {weight:g} in [{lower:g}, {upper:g}]'
            )
        xs, ys = [], []
        for cp, target in zip(points, targets):
            a = ink_bounds(target)
            b = ink_bounds(ctx.js.outline(jcmap[cp], weight))
            xs.extend(a[i] - scale * b[i] for i in (0, 2))
            ys.extend(a[i] - scale * b[i] for i in (1, 3))
        values.append((weight, median(xs), median(ys)))
    (w400, dx400, dy400), (w930, dx930, dy930) = values
    ctx.calibration = Calibration(w400, w930, scale, dx400, dy400, dx930, dy930)
    print(f'C hanzi calibration: {ctx.calibration}', file=sys.stderr)
    return ctx.calibration


def hanzi_master(ctx, cp: int, master: int) -> Outline:
    c = calibrate(ctx)
    if master == 400:
        weight, dx, dy = c.w400, c.dx400, c.dy400
    elif master == 930:
        weight, dx, dy = c.w930, c.dx930, c.dy930
    else:
        raise ValueError(f'unsupported hanzi master {master}')
    return transform(ctx.cs.outline(ctx.shs_cn.getBestCmap()[cp], weight), c.scale, dx, dy)


def contribute(ctx) -> list[NewGlyph]:
    c1 = ctx.selection.codepoints(Rule.C1_HANZI)
    cn = ctx.shs_cn.getBestCmap()
    out = []
    for cp, alternate in [(cp, False) for cp in c1] + [(cp, True) for cp in zhs_forms(ctx)]:
        a, b = hanzi_master(ctx, cp, 400), hanzi_master(ctx, cp, 930)
        if a.end_pts != b.end_pts or a.flags != b.flags:
            raise ValueError(f'U+{cp:04X}: incompatible Source Han Sans masters')
        coords = [[(otRound(x), otRound(y)) for x, y in o.coords] for o in (a, b)]
        deltas = [(q[0] - p[0], q[1] - p[1]) for p, q in zip(*coords)]
        deltas = iup_delta_optimize(deltas, coords[0], a.end_pts, tolerance=0.5)
        variations = remap_pretendard_tuples([TupleVariation({'wght': (0.0, 1.0, 1.0)}, deltas)])
        name = f'uni{cp:04X}.zhs' if alternate else ctx.cmap.get(cp, f'uni{cp:04X}')
        out.append(NewGlyph(name, a.to_glyph(), 1920, variations,
                            () if alternate else (cp,),
                            Rule.C2_FORM if alternate else Rule.C1_HANZI, cn[cp]))
    return out
