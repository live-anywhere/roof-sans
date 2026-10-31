"""Glyphs the build adds, with their gvar tuples."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass

from fontTools.misc.roundTools import otRound
from fontTools.ttLib.tables._g_l_y_f import OVERLAP_COMPOUND, Glyph, GlyphComponent
from fontTools.ttLib.tables.TupleVariation import TupleVariation
from fontTools.varLib.iup import iup_delta
from fontTools.varLib.models import supportScalar

from roofsans.outline import Outline, Point, combine
from roofsans.selection import Rule
from roofsans.variations import tuples_from_masters

Part = tuple[str, float, float]


@dataclass
class NewGlyph:
    name: str
    glyph: Glyph
    advance: int
    variations: list[TupleVariation]
    unicodes: tuple[int, ...]
    rule: Rule
    source: str


def _rounded(coords: Iterable[Point]) -> list[Point]:
    return [(otRound(x), otRound(y)) for x, y in coords]


def simple_glyph(
    name: str, masters: Mapping[float, Outline], unicodes: Iterable[int], rule: Rule, source: str
) -> NewGlyph:
    default = masters[0.0]
    # Round the masters first so the deltas are measured from the stored default glyph.
    coords = {t: _rounded(o.coords) for t, o in masters.items()}
    return NewGlyph(
        name=name,
        glyph=default.to_glyph(),
        advance=coords[0.0][-3][0] - coords[0.0][-4][0],
        variations=tuples_from_masters(coords, default.end_pts),
        unicodes=tuple(unicodes),
        rule=rule,
        source=source,
    )


def composite_glyph(
    name: str,
    parts: Mapping[float, list[Part]],
    advance: Mapping[float, float],
    unicodes: Iterable[int],
    rule: Rule,
    source: str,
) -> NewGlyph:
    names = [p[0] for p in parts[0.0]]
    if set(advance) != set(parts):
        raise ValueError(f"{name}: parts and advance list different locations")
    for t, ps in parts.items():
        if [p[0] for p in ps] != names:
            raise ValueError(f"{name}: components at {t} differ from the default")
    # Component offsets and the advance (right phantom point) become point deltas. The
    # deltas come from the unrounded masters and are rounded in turn, so each master
    # lands within 0.5 even where its offset is fractional (ruling R20).
    masters = {
        t: [(dx, dy) for _, dx, dy in ps] + [(0, 0), (advance[t], 0), (0, 0), (0, 0)]
        for t, ps in parts.items()
    }
    default = _rounded(masters[0.0])
    glyph = Glyph()
    glyph.numberOfContours = -1
    glyph.components = []
    for i, (comp_name, (dx, dy)) in enumerate(zip(names, default)):
        c = GlyphComponent()
        c.glyphName = comp_name
        c.x, c.y = dx, dy
        # Both inputs flag the first component of every composite (ruling R21).
        c.flags = OVERLAP_COMPOUND if i == 0 else 0
        glyph.components.append(c)
    return NewGlyph(
        name=name,
        glyph=glyph,
        advance=default[-3][0],
        variations=tuples_from_masters(masters, None),
        unicodes=tuple(unicodes),
        rule=rule,
        source=source,
    )


def newglyph_outline(g: NewGlyph, norm: float, resolve: Callable[[str, float], Outline]) -> Outline:
    """Return ``g`` at Roof normalized ``norm``; ``resolve`` gives a component's outline."""
    composite = g.glyph.isComposite()
    if composite:
        base = [(c.x, c.y) for c in g.glyph.components]
        end_pts = None
    elif g.glyph.numberOfContours > 0:
        base = [tuple(p) for p in g.glyph.coordinates]
        end_pts = list(g.glyph.endPtsOfContours)
    else:
        base, end_pts = [], []
    coords = base + [(0, 0), (g.advance, 0), (0, 0), (0, 0)]
    out = [tuple(map(float, p)) for p in coords]
    for tv in g.variations:
        s = supportScalar({"wght": norm}, tv.axes)
        if s == 0:
            continue
        deltas = tv.coordinates
        if None in deltas:
            deltas = [d or (0, 0) for d in deltas] if composite else iup_delta(deltas, coords, end_pts)
        out = [(p[0] + d[0] * s, p[1] + d[1] * s) for p, d in zip(out, deltas)]
    if not composite:
        return Outline(out, end_pts, list(g.glyph.flags) if end_pts else [])
    parts = []
    for i, c in enumerate(g.glyph.components):
        dx, dy = out[i]
        parts.append(resolve(c.glyphName, norm).transformed(lambda x, y: (x + dx, y + dy)))
    return combine(parts, out[-4:])
