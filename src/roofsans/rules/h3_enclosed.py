"""H3: enclosed numbers and superscript/subscript signs built from Wanted Sans parts."""

from __future__ import annotations

import math

from fontTools.misc.roundTools import otRound
from fontTools.ttLib.tables._g_l_y_f import flagOverlapSimple
from fontTools.ttLib.tables.TupleVariation import TupleVariation

from roofsans.axis import W_MID
from roofsans.embolden import embolden_xy
from roofsans.measure import flattened_contours, horizontal_runs, stroke, vertical_runs
from roofsans.newglyph import NewGlyph, Part, composite_glyph, newglyph_outline, simple_glyph
from roofsans.outline import Outline, combine
from roofsans.selection import Rule

# Wanted Sans's masters (400, 750, 1000) and its light end (100); every part here is a
# Wanted Sans glyph, and those vary linearly below 400.
W_LOCS = (-1.0, 0.0, W_MID, 1.0)

RING = "roof.ring"
DISC = "roof.disc"
RING_SOURCE = "uni2460"  # ①
DISC_SOURCE = "uni2776"  # ❶
DIGITS = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine")
# Wanted Sans's own enclosed figures 0–9: ⓪①–⑨ and ⓿❶–❾. Their knocked-out figures are
# drawn without overlaps, which reversed `.numr` contours are not (R27).
FIGURES = {
    RING: (0x24EA, *range(0x2460, 0x2469)),
    DISC: (0x24FF, *range(0x2776, 0x277F)),
}

# Enclosed code point → (number, helper).
ENCLOSED = {
    **{0x2469 + i: (10 + i, RING) for i in range(11)},  # ⑩–⑳
    **{0x24EB + i: (11 + i, DISC) for i in range(10)},  # ⓫–⓴
    0x277F: (10, DISC),  # ❿
}
# ⑩'s glyph also serves U+2789 ➉ through the cmap (R14).
ALSO_MAPPED = {0x2469: 0x2789}

# The y offsets Wanted Sans uses for `²` (two.dnom +936) and `₂` (two.dnom −208).
SUP_DY = 936
SUB_DY = -208
SIGN_SOURCES = ("plus", "minus", "equal", "parenleft", "parenright")
SUPSUB = {
    **{0x207A + i: (s, SUP_DY) for i, s in enumerate(SIGN_SOURCES)},  # ⁺⁻⁼⁽⁾
    **{0x208A + i: (s, SUB_DY) for i, s in enumerate(SIGN_SOURCES)},  # ₊₋₌₍₎
}


def figure_stem(o: Outline) -> float:
    """Stem of the figure `one`: the first horizontal run at 25% of its height (R16).

    Higher rays cross the flag of Wanted Sans's `one` (at 75%) or catch a 4-unit sliver
    of `one.dnom` at wght 1000 (at 50%).
    """
    _, y0, _, y1 = o.bounds()
    a, b = horizontal_runs(o, y0 + 0.25 * (y1 - y0))[0]
    return b - a


def sign_stroke(o: Outline, source: str) -> float:
    """Stroke of a sign, measured where the ray crosses a single stroke of ``source``."""
    x0, y0, x1, y1 = o.bounds()
    if source == "plus":
        # The run at 75% height crosses only the vertical bar.
        return stroke(o, "l_stem")
    if source in ("minus", "equal"):
        a, b = vertical_runs(o, (x0 + x1) / 2)[0]
    elif source in ("parenleft", "parenright"):
        a, b = horizontal_runs(o, y0 + 0.5 * (y1 - y0))[0]
    else:
        raise ValueError(f"no stroke measurement for {source}")
    return b - a


def _overlap(o: Outline) -> bool:
    return bool(o.flags and o.flags[0] & flagOverlapSimple)


def _keep_contours(o: Outline, keep: set[int]) -> Outline:
    """Contours ``keep`` of ``o``, with its phantom points and overlap flag."""
    parts, start = [], 0
    for n, end in enumerate(o.end_pts):
        if n in keep:
            pts = o.coords[start : end + 1]
            parts.append(Outline(pts + o.coords[-4:], [len(pts) - 1], o.flags[start : end + 1]))
        start = end + 1
    return combine(parts, o.coords[-4:], _overlap(o))


def _sliced_glyph(ctx, name: str, source: str, keep: set[int]) -> NewGlyph:
    """Contours ``keep`` of Wanted glyph ``source`` with its own gvar deltas (R18).

    IUP interpolates within each contour, so whole contours keep their omitted deltas
    and every instance equals ``source``'s contours exactly.
    """
    default = ctx.outline(source, 0.0)
    points, start = [], 0
    for n, end in enumerate(default.end_pts):
        if n in keep:
            points.extend(range(start, end + 1))
        start = end + 1
    total = len(default.coords)
    points.extend(range(total - 4, total))
    variations = [
        TupleVariation(dict(tv.axes), [tv.coordinates[i] for i in points])
        for tv in ctx.wanted["gvar"].variations.get(source, [])
    ]
    outline = _keep_contours(default, keep)
    return NewGlyph(name, outline.to_glyph(), otRound(outline.advance()), variations, (), Rule.H3_ENCLOSED, source)


def _bbox_area(pts) -> float:
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return (max(xs) - min(xs)) * (max(ys) - min(ys))


def _largest_contour(o: Outline) -> int:
    contours = o.contours()
    return max(range(len(contours)), key=lambda n: _bbox_area(contours[n]))


def _enclosure(o: Outline, helper: str) -> set[int]:
    """The contours of a Wanted circled figure that form its ring or disc."""
    return {0, 1} if helper == RING else {_largest_contour(o)}


def _center_and_radius(o: Outline, helper: str) -> tuple[float, float, float]:
    """The ink center of a ring or disc and the radius of its inner edge (the disc's edge)."""
    x0, y0, x1, y1 = o.bounds()
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    edge = flattened_contours(o)[1 if helper == RING else 0]
    return cx, cy, min(math.hypot(x - cx, y - cy) for x, y in edge)


def reach(o: Outline, cx: float, cy: float) -> float:
    """How far the ink of ``o`` reaches from (``cx``, ``cy``)."""
    return max(math.hypot(x - cx, y - cy) for poly in flattened_contours(o) for x, y in poly)


def figure_outline(ctx, helper: str, digit: int, t: float) -> Outline:
    """Figure ``digit`` of Wanted Sans's enclosed digit in ``helper``: its contours other than
    the ring or disc, where Wanted places them (R27)."""
    o = ctx.outline(ctx.wanted.getBestCmap()[FIGURES[helper][digit]], t)
    return _keep_contours(o, set(range(len(o.end_pts))) - _enclosure(o, helper))


def pair_limit(ctx, helper: str, outline: Outline, t: float) -> float:
    """How far a figure pair may reach from the center of ``helper`` (``outline`` at ``t``):
    its inner radius less Wanted Sans's tightest clearance among `①`–`⑨` (`❶`–`❾`) (R22)."""
    cmap = ctx.wanted.getBestCmap()
    clearances = []
    for u in FIGURES[helper][1:]:
        o = ctx.outline(cmap[u], t)
        keep = _enclosure(o, helper)
        cx, cy, r = _center_and_radius(_keep_contours(o, keep), helper)
        figure = _keep_contours(o, set(range(len(o.end_pts))) - keep)
        clearances.append(r - reach(figure, cx, cy))
    return _center_and_radius(outline, helper)[2] - min(clearances)


def _pair(ctx, helper: str, number: int, t: float) -> Outline:
    """The number's enclosed figures side by side, at the `.numr` figures' ink gap scaled
    to the enclosed figures' height; each keeps Wanted's vertical position (R27)."""
    digits = [int(c) for c in str(number)]
    numr = [ctx.outline(f"{DIGITS[d]}.numr", t) for d in digits]
    one_numr, one = ctx.outline("one.numr", t).bounds(), figure_outline(ctx, helper, 1, t).bounds()
    scale = (one[3] - one[1]) / (one_numr[3] - one_numr[1])
    parts, right = [], None
    for d, prev, cur in zip(digits, [None, *numr], numr):
        figure = figure_outline(ctx, helper, d, t)
        if right is not None:
            gap = scale * (prev.advance() + cur.bounds()[0] - prev.bounds()[2])
            dx = right + gap - figure.bounds()[0]
            figure = figure.transformed(lambda x, y, dx=dx: (x + dx, y))
        parts.append(figure)
        right = figure.bounds()[2]
    return combine(parts, [(0.0, 0.0)] * 4)


def fitted_pair(pair: Outline, limit: float) -> tuple[Outline, float]:
    """``pair`` scaled about its ink center by the largest s ≤ 1 whose ink reaches at most
    ``limit`` from that center (R22, R27). Reach scales with s, so s = limit / reach."""
    x0, y0, x1, y1 = pair.bounds()
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    s = min(1.0, limit / reach(pair, cx, cy))
    return pair.transformed(lambda x, y: (cx + s * (x - cx), cy + s * (y - cy))), s


def _helpers(ctx) -> tuple[list[NewGlyph], dict[str, dict[float, Outline]]]:
    """The ring and the disc, with their outlines per location."""
    glyphs = [
        _sliced_glyph(ctx, RING, RING_SOURCE, {0, 1}),
        _sliced_glyph(ctx, DISC, DISC_SOURCE, _enclosure(ctx.outline(DISC_SOURCE, 0.0), DISC)),
    ]
    return glyphs, {g.name: {t: newglyph_outline(g, t, ctx.outline) for t in ctx.locs(W_LOCS)} for g in glyphs}


def _centered(outline: Outline, pair: Outline) -> tuple[float, float]:
    """The offset that centers ``pair``'s ink on ``outline``'s ink."""
    hx0, hy0, hx1, hy1 = outline.bounds()
    px0, py0, px1, py1 = pair.bounds()
    return (hx0 + hx1 - px0 - px1) / 2, (hy0 + hy1 - py0 - py1) / 2


def _enclosed(ctx, cp: int, number: int, helper: str, outlines: dict[float, Outline]) -> list[NewGlyph]:
    """The enclosed glyph for ``number``: ``helper`` plus a helper glyph of fitted figures."""
    name = f"roof.pair.{number}" if helper == RING else f"roof.knockpair.{number}"
    masters, parts = {}, {}
    for t in outlines:
        # Figures are only scaled: restored strokes clog small ring figures, and emboldening
        # folds that show as ink inside a disc's white figures (R27).
        fitted, _ = fitted_pair(_pair(ctx, helper, number, t), pair_limit(ctx, helper, outlines[t], t))
        masters[t] = fitted
        parts[t] = [(helper, 0, 0), (name, *_centered(outlines[t], fitted))]
    cmap = ctx.wanted.getBestCmap()
    figures = "+".join(cmap[FIGURES[helper][int(c)]] for c in str(number))
    advance = {t: o.advance() for t, o in outlines.items()}
    unicodes = (cp, ALSO_MAPPED[cp]) if cp in ALSO_MAPPED else (cp,)
    source = RING_SOURCE if helper == RING else DISC_SOURCE
    return [
        simple_glyph(name, masters, (), Rule.H3_ENCLOSED, figures),
        composite_glyph(ctx.cmap[cp], parts, advance, unicodes, Rule.H3_ENCLOSED, source),
    ]


def _supsub(ctx, name: str, cp: int, source: str, dy: float) -> NewGlyph:
    zero_dnom, zero = ctx.outline("zero.dnom", 0.0).bounds(), ctx.outline("zero", 0.0).bounds()
    k = (zero_dnom[3] - zero_dnom[1]) / (zero[3] - zero[1])
    masters = {}
    for t in ctx.locs(W_LOCS):
        src = ctx.outline(source, t)
        k_s = figure_stem(ctx.outline("one.dnom", t)) / figure_stem(ctx.outline("one", t))
        strength = (k_s - k) * sign_stroke(src, source)
        o = embolden_xy(src.transformed(lambda x, y: (k * x, k * y)), strength, strength)
        advance = k * src.advance()
        x0, _, x1, _ = o.bounds()
        dx = advance / 2 - (x0 + x1) / 2
        # Emboldening raises the ink by strength/2; take that back before the shift (R23).
        moved = [(x + dx, y - strength / 2 + dy) for x, y in o.points]
        masters[t] = Outline(moved + [(0.0, 0.0), (advance, 0.0), *src.coords[-2:]], o.end_pts, o.flags)
    return simple_glyph(name, masters, (cp,), Rule.H3_SUPSUB, source)


def contribute(ctx) -> list[NewGlyph]:
    out, outlines = _helpers(ctx)
    for cp, (number, helper) in sorted(ENCLOSED.items()):
        out.extend(_enclosed(ctx, cp, number, helper, outlines[helper]))
    for cp, (source, dy) in sorted(SUPSUB.items()):
        out.append(_supsub(ctx, ctx.cmap[cp], cp, source, dy))
    return out
