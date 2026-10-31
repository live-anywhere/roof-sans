"""Ray-cast stroke measurement and vertical zones of outlines."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from itertools import groupby
from typing import Literal

from roofsans.outline import Outline, Point

Stroke = Literal["l_stem", "o_top", "o_bottom", "e_top", "H_bar", "n_arch"]

FLATTEN_STEPS = 32


def _quad(p0: Point, c: Point, p1: Point) -> list[Point]:
    """Points of a quadratic segment after ``p0``, as ``FLATTEN_STEPS`` lines."""
    out = []
    for i in range(1, FLATTEN_STEPS + 1):
        t = i / FLATTEN_STEPS
        a, b, d = (1 - t) ** 2, 2 * t * (1 - t), t * t
        out.append((a * p0[0] + b * c[0] + d * p1[0], a * p0[1] + b * c[1] + d * p1[1]))
    return out


def _mid(a: Point, b: Point) -> Point:
    return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)


def _flatten(pts: list[Point], on: list[bool]) -> list[Point]:
    if not any(on):
        # An all-off-curve contour starts at the implied point before its first point.
        pts, on = [_mid(pts[-1], pts[0])] + pts, [True] + on
    k = on.index(True)
    pts, on = pts[k:] + pts[:k], on[k:] + on[:k]
    poly, cur, ctrl = [pts[0]], pts[0], None
    for p, is_on in zip(pts[1:] + pts[:1], on[1:] + [True]):
        if is_on:
            poly.extend([p] if ctrl is None else _quad(cur, ctrl, p))
            cur, ctrl = p, None
        elif ctrl is None:
            ctrl = p
        else:
            m = _mid(ctrl, p)
            poly.extend(_quad(cur, ctrl, m))
            cur, ctrl = m, p
    return poly[:-1]


def flattened_contours(o: Outline) -> list[list[Point]]:
    """Each contour as a closed polygon, every quadratic segment flattened into 32 lines."""
    out, start = [], 0
    for end in o.end_pts:
        pts = [tuple(map(float, p)) for p in o.coords[start : end + 1]]
        out.append(_flatten(pts, [bool(f & 1) for f in o.flags[start : end + 1]]))
        start = end + 1
    return out


def _runs(o: Outline, axis: int, at: float) -> list[tuple[float, float]]:
    """Inside intervals along a ray where coordinate ``axis`` equals ``at`` (nonzero rule)."""
    other = 1 - axis
    hits = []
    for poly in flattened_contours(o):
        for a, b in zip(poly, poly[1:] + poly[:1]):
            if a[axis] <= at < b[axis] or b[axis] <= at < a[axis]:
                t = (at - a[axis]) / (b[axis] - a[axis])
                hits.append((a[other] + t * (b[other] - a[other]), 1 if b[axis] > a[axis] else -1))
    hits.sort()
    runs, winding, start = [], 0, 0.0
    for u, group in groupby(hits, key=lambda h: h[0]):
        before = winding
        winding += sum(d for _, d in group)
        if before == 0 and winding != 0:
            start = u
        elif before != 0 and winding == 0 and u > start:
            runs.append((start, u))
    return runs


def horizontal_runs(o: Outline, y: float) -> list[tuple[float, float]]:
    return _runs(o, 1, y)


def vertical_runs(o: Outline, x: float) -> list[tuple[float, float]]:
    return _runs(o, 0, x)


def stroke(o: Outline, kind: Stroke) -> float:
    """Thickness of a named reference stroke, measured across one ray."""
    x0, y0, x1, y1 = o.bounds()
    if kind == "l_stem":
        runs = horizontal_runs(o, y0 + 0.75 * (y1 - y0))
    else:
        runs = vertical_runs(o, (x0 + x1) / 2)
    if not runs:
        raise ValueError(f"{kind}: the ray misses the outline")
    if kind == "H_bar" and len(runs) != 1:
        raise ValueError(f"H_bar: expected a single run, got {len(runs)}")
    a, b = runs[0] if kind in ("l_stem", "o_bottom") else runs[-1]
    return b - a


@dataclass(frozen=True)
class Zones:
    lower: tuple[float, ...]
    capital: tuple[float, ...]


def zones_of(outline_of: Callable[[str], Outline]) -> Zones:
    """Zone heights of a font, from ``outline_of(glyph name)``."""
    y_min = {c: outline_of(c).bounds()[1] for c in "gpoO"}
    y_max = {c: outline_of(c).bounds()[3] for c in "xolHO"}
    return Zones(
        lower=(y_min["g"], y_min["p"], y_min["o"], 0.0, y_max["x"], y_max["o"], y_max["l"]),
        capital=(y_min["O"], 0.0, y_max["H"], y_max["O"]),
    )
