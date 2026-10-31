"""Outline sanity check for glyphs sampled past a master or emboldened."""

from __future__ import annotations

from roofsans.measure import flattened_contours
from roofsans.outline import Outline, Point


def _area(poly: list[Point]) -> float:
    """Signed area; negative is clockwise (a TrueType outer contour)."""
    return sum(poly[i - 1][0] * poly[i][1] - poly[i][0] * poly[i - 1][1] for i in range(len(poly))) / 2


def _sign(v: float) -> int:
    return (v > 0) - (v < 0)


def _cross(o: Point, a: Point, b: Point) -> float:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _self_intersects(poly: list[Point]) -> bool:
    """Whether two non-adjacent edges of the closed polygon cross (O(n²) with an x-range cut)."""
    n = len(poly)
    edges = sorted(
        (min(a[0], b[0]), max(a[0], b[0]), i, a, b)
        for i, (a, b) in enumerate(zip(poly, poly[1:] + poly[:1]))
    )
    for e, (_, hi, i, a, b) in enumerate(edges):
        for lo2, _, i2, c, d in edges[e + 1 :]:
            if lo2 > hi:
                break
            if abs(i - i2) in (1, n - 1):
                continue
            if max(a[1], b[1]) < min(c[1], d[1]) or max(c[1], d[1]) < min(a[1], b[1]):
                continue
            if (
                _sign(_cross(a, b, c)) * _sign(_cross(a, b, d)) < 0
                and _sign(_cross(c, d, a)) * _sign(_cross(c, d, b)) < 0
            ):
                return True
    return False


def check_outline(candidate: Outline, reference: Outline) -> list[str]:
    """Return the ways ``candidate`` breaks ``reference``'s contour structure; empty if none.

    An inner contour (a counter) runs against the outline's total orientation in the
    reference, so a mirrored glyph is judged the same way as its source (R4).
    """
    if len(candidate.end_pts) != len(reference.end_pts):
        return [f"contour count {len(candidate.end_pts)} != reference {len(reference.end_pts)}"]
    cand, ref = flattened_contours(candidate), flattened_contours(reference)
    ref_areas = [_area(p) for p in ref]
    total = _sign(sum(ref_areas))
    problems = []
    for n, (c, r, r_area) in enumerate(zip(cand, ref, ref_areas)):
        c_area = _area(c)
        inner = total != 0 and _sign(r_area) == -total
        # A closing counter shows as a tiny area, a reversed sign, or a fold (R7).
        collapsed = " collapsed:" if inner else ""
        if inner and abs(c_area) <= 1:
            problems.append(f"contour {n} collapsed: area {c_area:.2f}")
        elif _sign(c_area) != _sign(r_area):
            problems.append(f"contour {n}{collapsed} orientation reversed")
        if _self_intersects(c) and not _self_intersects(r):
            problems.append(f"contour {n}{collapsed} self-intersects")
    return problems
