"""H5: Pretendard symbols, aligned to Wanted Sans's axes by category."""

from __future__ import annotations

import unicodedata
import weakref
from dataclasses import dataclass
from typing import Literal

from roofsans.axis import H4_LOCS, roof_wght
from roofsans.measure import vertical_runs
from roofsans.newglyph import NewGlyph, simple_glyph
from roofsans.outline import Outline
from roofsans.rules import h4_letters
from roofsans.selection import Rule, SymbolCategory

SAMPLE_RANGE = (45.0, 1100.0)
SAMPLE_TOLERANCE = 0.05
ITERATIONS = 3
# Masters where no weight in SAMPLE_RANGE gives Wanted Sans's stroke, so the sampled
# weight stays at the range's end (R28): Pretendard's `→` head grows with weight, which
# lowers the height-ratio scale; at 1100 its scaled shaft is 301.5 against Wanted's 318.
CLAMPED_STROKES = frozenset({(SymbolCategory.ARROW, 1.0)})


@dataclass(frozen=True)
class Transform:
    """One master's move of a category: Pretendard sampled at ``sample_wght``, then
    y' = scale·y + shift_y, x scaled and re-centered, and the advance × advance_ratio."""

    scale: float
    shift_y: float
    advance_ratio: float
    sample_wght: float


@dataclass(frozen=True)
class _Reference:
    """A symbol both fonts draw, which sets a category's transform."""

    char: str
    size: Literal["height", "width"]
    # Whether the vertical run at 25% of the ink width (the shaft of `→`, the bar of `+`)
    # sets the sampled weight; otherwise Pretendard is sampled at H4's w′.
    stroke: bool
    # Whether the advance follows the reference's advances or the scale.
    own_advance: bool
    # Where the reference's ink center lands: the design's axis, or Wanted Sans's center.
    axis: float | None = None


_ARROW = _Reference("→", "height", stroke=True, own_advance=True, axis=725)
_MATH = _Reference("+", "width", stroke=True, own_advance=False, axis=540)
_CIRCLE = _Reference("●", "height", stroke=False, own_advance=False)
_SQUARE = _Reference("■", "height", stroke=False, own_advance=False)

_CATEGORY_REFERENCE = {SymbolCategory.ARROW: _ARROW, SymbolCategory.MATH: _MATH, SymbolCategory.GEOMETRIC: _SQUARE}

# Solved transforms per build context, keyed by id like h4_letters.params (ruling R12).
_CACHE: dict[int, tuple[weakref.ref, dict]] = {}


def _cache(ctx) -> dict:
    key = id(ctx)
    entry = _CACHE.get(key)
    if entry is None or entry[0]() is not ctx:
        entry = (weakref.ref(ctx, lambda _: _CACHE.pop(key, None)), {})
        _CACHE[key] = entry
    return entry[1]


def shaft(o: Outline) -> float:
    """The vertical run at 25% of the ink width: the shaft of `→`, the bar of `+`."""
    x0, _, x1, _ = o.bounds()
    runs = vertical_runs(o, x0 + 0.25 * (x1 - x0))
    if len(runs) != 1:
        raise ValueError(f"shaft: expected a single run, got {len(runs)}")
    a, b = runs[0]
    return b - a


def _size(o: Outline, size: str) -> float:
    x0, y0, x1, y1 = o.bounds()
    return y1 - y0 if size == "height" else x1 - x0


def _center_y(o: Outline) -> float:
    _, y0, _, y1 = o.bounds()
    return (y0 + y1) / 2


def _solve_sample_wght(ps_outline, scale: float, target: float) -> float:
    """The Pretendard weight whose shaft, scaled by ``scale``, equals ``target``.

    When no weight in ``SAMPLE_RANGE`` reaches it, the nearest end of the range (R28).
    """
    lo, hi = SAMPLE_RANGE
    if shaft(ps_outline(hi)) * scale < target:
        return hi
    if shaft(ps_outline(lo)) * scale > target:
        return lo
    while True:
        mid = (lo + hi) / 2
        err = shaft(ps_outline(mid)) * scale - target
        if abs(err) <= SAMPLE_TOLERANCE:
            return mid
        if hi - lo < 1e-9:
            raise ValueError(f"no Pretendard weight gives a shaft of {target}")
        lo, hi = (mid, hi) if err < 0 else (lo, mid)


def _solve(ctx, ref: _Reference, t: float) -> Transform:
    pname = ctx.pretendard.getBestCmap()[ord(ref.char)]
    wname = ctx.wanted.getBestCmap()[ord(ref.char)]
    wanted = ctx.ws.outline(wname, roof_wght(t))
    w = h4_letters.params(ctx)[t].w_prime

    def ps_outline(wght: float) -> Outline:
        return ctx.ps.outline(pname, wght)

    scale = _size(wanted, ref.size) / _size(ps_outline(w), ref.size)
    if ref.stroke:
        target = shaft(wanted)
        for _ in range(ITERATIONS):
            w = _solve_sample_wght(ps_outline, scale, target)
            scale = _size(wanted, ref.size) / _size(ps_outline(w), ref.size)
    source = ps_outline(w)
    axis = _center_y(wanted) if ref.axis is None else ref.axis
    shift_y = axis - scale * _center_y(source)
    advance_ratio = wanted.advance() / source.advance() if ref.own_advance else scale
    return Transform(scale, shift_y, advance_ratio, w)


def _transform(ctx, ref: _Reference | None, t: float) -> Transform:
    if ref is None:
        return Transform(1.0, 0.0, 1.0, h4_letters.params(ctx)[t].w_prime)
    cache = _cache(ctx)
    if (ref, t) not in cache:
        cache[(ref, t)] = _solve(ctx, ref, t)
    return cache[(ref, t)]


def category_transform(ctx, cat: SymbolCategory, t: float) -> Transform:
    """The transform of category ``cat`` at master ``t`` in ``H4_LOCS`` (`■` for GEOMETRIC)."""
    return _transform(ctx, _CATEGORY_REFERENCE.get(cat), t)


def symbol_transform(ctx, cp: int, t: float) -> Transform:
    """The transform of H5 symbol ``cp`` at master ``t``: its category's, with `●` for circles."""
    cat = ctx.selection.symbol_category[cp]
    if cat is SymbolCategory.GEOMETRIC and "CIRCLE" in unicodedata.name(chr(cp), ""):
        return _transform(ctx, _CIRCLE, t)
    return category_transform(ctx, cat, t)


def symbol_outline(source: Outline, tr: Transform) -> Outline:
    """``source`` moved by ``tr``: x scaled about the origin and re-centered so the ink
    center keeps its share of the advance, y scaled and shifted."""
    advance = source.advance() * tr.advance_ratio
    dx = 0.0
    if source.points and source.advance():
        x0, _, x1, _ = source.bounds()
        cx = (x0 + x1) / 2
        dx = cx / source.advance() * advance - tr.scale * cx
    moved = source.transformed(lambda x, y: (tr.scale * x + dx, tr.scale * y + tr.shift_y))
    return Outline(moved.points + [(0.0, 0.0), (advance, 0.0), *source.coords[-2:]], moved.end_pts, moved.flags)


def contribute(ctx) -> list[NewGlyph]:
    pcmap = ctx.pretendard.getBestCmap()
    out = []
    for cp in ctx.selection.codepoints(Rule.H5_SYMBOL):
        source = pcmap[cp]
        masters = {}
        for t in ctx.locs(H4_LOCS):
            tr = symbol_transform(ctx, cp, t)
            masters[t] = symbol_outline(ctx.ps.outline(source, tr.sample_wght), tr)
        out.append(simple_glyph(ctx.cmap[cp], masters, [cp], Rule.H5_SYMBOL, source))
    return out
