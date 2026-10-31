"""Floating-point glyph outlines with phantom points."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from fontTools.misc.roundTools import otRound
from fontTools.ttLib.tables import ttProgram
from fontTools.ttLib.tables._g_l_y_f import Glyph, GlyphCoordinates, flagOverlapSimple

Point = tuple[float, float]


@dataclass
class Outline:
    """Outline points followed by the 4 phantom points (left, right, top, bottom)."""

    coords: list[Point]
    end_pts: list[int]
    flags: list[int]

    @property
    def points(self) -> list[Point]:
        return self.coords[:-4]

    def advance(self) -> float:
        return self.coords[-3][0] - self.coords[-4][0]

    def bounds(self) -> tuple[float, float, float, float]:
        pts = self.points
        if not pts:
            return (0.0, 0.0, 0.0, 0.0)
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        return (min(xs), min(ys), max(xs), max(ys))

    def contours(self) -> list[list[Point]]:
        pts = self.points
        out, start = [], 0
        for end in self.end_pts:
            out.append(pts[start : end + 1])
            start = end + 1
        return out

    def transformed(self, fn: Callable[[float, float], Point]) -> Outline:
        """Return a copy with ``fn`` applied to the outline points; phantom points stay."""
        moved = [tuple(fn(x, y)) for x, y in self.points]
        return Outline(moved + list(self.coords[-4:]), list(self.end_pts), list(self.flags))

    def to_glyph(self) -> Glyph:
        g = Glyph()
        if not self.end_pts:
            g.numberOfContours = 0
            return g
        g.numberOfContours = len(self.end_pts)
        g.coordinates = GlyphCoordinates([(otRound(x), otRound(y)) for x, y in self.points])
        g.endPtsOfContours = list(self.end_pts)
        g.flags = bytearray(self.flags)
        g.program = ttProgram.Program()
        g.program.fromBytecode(b"")
        g.recalcBounds(None)
        return g


def combine(parts: Sequence[Outline], phantoms: Sequence[Point], overlap: bool = False) -> Outline:
    """Concatenate the outline points of ``parts`` and attach ``phantoms``.

    The result carries ``OVERLAP_SIMPLE`` on its first point when ``overlap`` is set
    or any part had it, which is how a decomposed ``OVERLAP_COMPOUND`` is kept.
    """
    coords: list[Point] = []
    end_pts: list[int] = []
    flags: list[int] = []
    for part in parts:
        base = len(coords)
        coords.extend(part.points)
        end_pts.extend(base + e for e in part.end_pts)
        overlap = overlap or bool(part.flags and part.flags[0] & flagOverlapSimple)
        flags.extend(f & ~flagOverlapSimple for f in part.flags)
    if flags and overlap:
        flags[0] |= flagOverlapSimple
    return Outline(coords + [tuple(p) for p in phantoms], end_pts, flags)
