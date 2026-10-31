"""R24's test for self-intersections in harmonized glyphs, shared by test_a05_h3 and test_a06.

At each new crossing of a contour with itself, the winding numbers of the four sectors
around it decide (R24 and its clarification). The crossing fails when the contour's own
sectors form a twist (its opposite equal pair is 0, as in (0, −1, 0, 1)), even if other
contours' ink shifts the total, or when the total sectors carry opposite signs (ink in a
hole, or a hole in ink). A same-sign overlap passes. The only twist that passes is the
open-counter allowance: the region where a counter's own winding runs against its
orientation covers at most ``FOLD_ALLOWANCE`` units² and the counter keeps a positive area.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from roofsans.measure import FLATTEN_STEPS, flattened_contours
from roofsans.outline import Outline, Point
from roofsans.sanity import check_outline

# Largest reversed area (units²) a counter may fold into and still pass (R24, `д` at 1000).
FOLD_ALLOWANCE = 1.0
# A candidate crossing is the source's own when it joins the same pair of flattened edges
# give or take one flattened quadratic segment, or, if the contour's vertex count differs
# from the source's, when it lies within SOURCE_MATCH units of a source crossing (R24).
EDGE_MATCH = FLATTEN_STEPS
SOURCE_MATCH = 4.0
EPS = 0.01


@dataclass(frozen=True)
class Crossing:
    """Where edges ``i`` and ``j`` (i < j) of one polygon cross, with their directions."""

    i: int
    j: int
    point: Point
    u: Point
    v: Point


@dataclass
class Verdict:
    """The judged crossings of one glyph: failures, same-sign overlaps, allowed folds, and
    crossings the source already has."""

    failures: list[str] = field(default_factory=list)
    accepted: int = 0
    matched: int = 0
    allowed: list[str] = field(default_factory=list)


def winding(polys, x, y):
    w = 0
    for poly in polys:
        for (ax, ay), (bx, by) in zip(poly, poly[1:] + poly[:1]):
            side = (bx - ax) * (y - ay) - (x - ax) * (by - ay)
            if ay <= y < by and side > 0:
                w += 1
            elif by <= y < ay and side < 0:
                w -= 1
    return w


def area(poly: Sequence[Point]) -> float:
    """Signed area; negative is clockwise (a TrueType outer contour)."""
    return sum(poly[k - 1][0] * poly[k][1] - poly[k][0] * poly[k - 1][1] for k in range(len(poly))) / 2


def _unit(a: Point, b: Point) -> Point:
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = (dx * dx + dy * dy) ** 0.5
    return dx / length, dy / length


def self_crossings(poly: Sequence[Point]) -> list[Crossing]:
    """Every proper crossing of two non-adjacent edges of the closed polygon ``poly``.

    Edges are swept in x order, as `check_outline` does, so long contours stay fast.
    """
    n = len(poly)
    edges = sorted(
        (min(a[0], b[0]), max(a[0], b[0]), k, a, b) for k, (a, b) in enumerate(zip(poly, list(poly[1:]) + [poly[0]]))
    )
    out = []
    for e, (_, hi, k, a, b) in enumerate(edges):
        for lo2, _, k2, c, d in edges[e + 1 :]:
            if lo2 > hi:
                break
            if abs(k - k2) in (1, n - 1):
                continue
            r = (b[0] - a[0], b[1] - a[1])
            q = (d[0] - c[0], d[1] - c[1])
            den = r[0] * q[1] - r[1] * q[0]
            if den == 0:
                continue
            t = ((c[0] - a[0]) * q[1] - (c[1] - a[1]) * q[0]) / den
            u = ((c[0] - a[0]) * r[1] - (c[1] - a[1]) * r[0]) / den
            if not (0 < t < 1 and 0 < u < 1):
                continue
            point = (a[0] + t * r[0], a[1] + t * r[1])
            (i, ab), (j, cd) = sorted(((k, (a, b)), (k2, (c, d))))
            out.append(Crossing(i, j, point, _unit(*ab), _unit(*cd)))
    return sorted(out, key=lambda c: (c.i, c.j))


def sectors(polys, c: Crossing) -> list[int]:
    """The windings of ``polys`` in the four sectors around crossing ``c``, in turn."""
    px, py = c.point
    return [
        winding(polys, px + EPS * (s * c.u[0] + t * c.v[0]), py + EPS * (s * c.u[1] + t * c.v[1]))
        for s, t in ((1, 1), (1, -1), (-1, -1), (-1, 1))
    ]


def is_twist(own: list[int]) -> bool:
    """A contour's own sectors are (k−1, k, k+1, k); k = 0 means the contour twists there."""
    a, b, c, d = own
    return (a == c == 0) or (b == d == 0)


def opposite_signs(total: list[int]) -> bool:
    return min(total) < 0 < max(total)


def reversed_area(poly: Sequence[Point]) -> float:
    """Area where ``poly``'s own winding runs against its orientation (its reversed region).

    The y values of the vertices and of the self-crossings cut the plane into slabs in
    which no two edges cross, so the reversed width is linear in y within a slab and its
    value at the slab's middle times the slab's height is exact.
    """
    orientation = 1 if area(poly) > 0 else -1
    edges = list(zip(poly, list(poly[1:]) + [poly[0]]))
    cuts = sorted({p[1] for p in poly} | {c.point[1] for c in self_crossings(poly)})
    total = 0.0
    for y0, y1 in zip(cuts, cuts[1:]):
        y = (y0 + y1) / 2
        hits = sorted(
            (a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1]), 1 if b[1] > a[1] else -1)
            for a, b in edges
            if (a[1] < y < b[1]) or (b[1] < y < a[1])
        )
        # Crossing edges left to right; the winding to the right of an upward edge drops by 1,
        # as in ``winding``, which counts upward edges to the right of the point.
        w = sum(d for _, d in hits)
        for (x, d), (x2, _) in zip(hits, hits[1:]):
            w -= d
            if w * orientation < 0:
                total += (x2 - x) * (y1 - y0)
    return total


def _distance(c: Crossing, x: Crossing, by_index: bool) -> float | None:
    """How far apart two crossings are, or None when they cannot be the same crossing."""
    if by_index:
        d = max(abs(c.i - x.i), abs(c.j - x.j))
        return d if d <= EDGE_MATCH else None
    d = max(abs(c.point[0] - x.point[0]), abs(c.point[1] - x.point[1]))
    return d if d <= SOURCE_MATCH else None


def _source_crossings(found: list[Crossing], sources: list[tuple[bool, list[Crossing]]]) -> set[int]:
    """Indices of the crossings in ``found`` that a source already has.

    Within each source a crossing excuses at most one candidate crossing, nearest first.
    """
    excused: set[int] = set()
    for by_index, known in sources:
        pairs = sorted(
            (d, a, b)
            for a, c in enumerate(found)
            for b, x in enumerate(known)
            if (d := _distance(c, x, by_index)) is not None
        )
        taken_a, taken_b = set(), set()
        for _, a, b in pairs:
            if a not in taken_a and b not in taken_b:
                taken_a.add(a)
                taken_b.add(b)
        excused |= taken_a
    return excused


def judge_crossings(candidate: Outline, sources: Iterable[Outline] = ()) -> Verdict:
    """R24 verdict on every self-crossing of ``candidate``'s contours.

    A crossing the same contour of any of ``sources`` already has is not judged. Crossings
    are matched by flattened edge indices: the build's embolden, zone maps, and affine
    moves keep every point and flag, so a candidate contour and its source flatten to the
    same vertices in the same order, while the points themselves move by tens of units
    (H4's δy and zone map). Contours whose vertex counts differ fall back to location.
    """
    polys = flattened_contours(candidate)
    source_polys = [flattened_contours(s) for s in sources]
    total_area = sum(area(p) for p in polys)
    verdict = Verdict()
    for n, poly in enumerate(polys):
        found = self_crossings(poly)
        if not found:
            continue
        known = [(len(s[n]) == len(poly), self_crossings(s[n])) for s in source_polys if n < len(s)]
        excused = _source_crossings(found, known)
        verdict.matched += len(excused)
        reversed_ = None
        for k, c in enumerate(found):
            if k in excused:
                continue
            total, own = sectors(polys, c), sectors([poly], c)
            where = f"contour {n} at ({c.point[0]:.1f}, {c.point[1]:.1f})"
            if opposite_signs(total):
                verdict.failures.append(f"{where}: ink and hole meet, sectors {total}")
                continue
            if not is_twist(own):
                verdict.accepted += 1
                continue
            if reversed_ is None:
                reversed_ = reversed_area(poly)
            counter = area(poly) * total_area < 0 and abs(area(poly)) > 1
            # A twist always reverses some area; finding none means the measurement failed.
            if counter and 0 < reversed_ <= FOLD_ALLOWANCE:
                verdict.allowed.append(f"{where}: counter fold {reversed_:.2f} unit²")
            else:
                verdict.failures.append(f"{where}: twist, own sectors {own}, reversed area {reversed_:.2f} unit²")
    return verdict


def judge(candidate, reference):
    """``check_outline`` failures, with self-intersections judged by the R24 sector test.

    Returns (failures, number of accepted same-sign crossings). Allowed counter folds are
    printed, so the caller's output lists them (R24).
    """
    failures = [m for m in check_outline(candidate, reference) if "self-intersects" not in m]
    verdict = judge_crossings(candidate, [reference])
    for fold in verdict.allowed:
        print(f"R24 open-counter allowance: {fold}")
    return failures + verdict.failures, verdict.accepted


def interpolate(values: dict[float, float], norm: float) -> float:
    """``values`` (at the masters) at ``norm``, piecewise linear like the gvar tuples."""
    locs = sorted(values)
    for a, b in zip(locs, locs[1:]):
        if norm <= b:
            return values[a] + (norm - a) / (b - a) * (values[b] - values[a])
    return values[locs[-1]]
