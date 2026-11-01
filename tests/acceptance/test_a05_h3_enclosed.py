"""Acceptance 5, H3: enclosed numbers share Wanted Sans's ring; sanity of the H3 parts."""

import pytest
import skia
from sectors import judge

from roofsans.axis import roof_norm
from roofsans.measure import flattened_contours
from roofsans.outline import Outline, combine
from roofsans.rules.h3_enclosed import (
    DISC,
    ENCLOSED,
    FIGURES,
    RING,
    SUPSUB,
    pair_limit,
    reach,
)
from roofsans.sanity import check_outline

pytestmark = pytest.mark.acceptance

WEIGHTS = (100, 175, 250, 300, 400, 550, 700, 850, 1000)
PAIR_PREFIXES = ("roof.pair.", "roof.knockpair.")


def instance_outline(font, name):
    """Decomposed outline of ``name`` in a static instance (phantom points zeroed)."""
    glyf = font["glyf"]
    coords, end_pts, flags = glyf[name].getCoordinates(glyf)
    return Outline([tuple(p) for p in coords] + [(0, 0)] * 4, list(end_pts), list(flags))


def figure(font, helper, digit):
    """Figure ``digit`` of Wanted Sans's enclosed digit in ``helper``, from the Roof instance."""
    o = instance_outline(font, font.getBestCmap()[FIGURES[helper][digit]])
    contours = o.contours()
    if helper == RING:
        keep = range(2, len(contours))
    else:
        disc = max(range(len(contours)), key=lambda n: bbox_area(contours[n]))
        keep = [n for n in range(len(contours)) if n != disc]
    return combine([part(o, n) for n in keep], [(0, 0)] * 4)


def part(o, n):
    """Contour ``n`` of ``o`` as an outline of its own."""
    start = o.end_pts[n - 1] + 1 if n else 0
    pts = o.coords[start : o.end_pts[n] + 1]
    return Outline(pts + [(0, 0)] * 4, [len(pts) - 1], o.flags[start : o.end_pts[n] + 1])


def bbox_area(pts):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return (max(xs) - min(xs)) * (max(ys) - min(ys))


def source_outline(font, name):
    """What ``name`` is built from, at the instance's weight: a pair helper's enclosed
    figures (R27), or a composite's components (judged the same way)."""
    if name.startswith(PAIR_PREFIXES):
        helper = RING if name.startswith("roof.pair.") else DISC
        digits = [int(c) for c in name.rsplit(".", 1)[1]]
        return combine([figure(font, helper, d) for d in digits], [(0, 0)] * 4)
    glyph = font["glyf"][name]
    if glyph.isComposite():
        return combine([source_outline(font, c.glyphName) for c in glyph.components], [(0, 0)] * 4)
    return instance_outline(font, name)




@pytest.mark.parametrize("wght", WEIGHTS)
def test_ring_matches_wanted_circled_one(static, roof, wght):
    font, cmap = static("roof", wght), roof.getBestCmap()
    ring = instance_outline(font, cmap[0x2460]).contours()[:2]
    bad = []
    for cp in range(0x2469, 0x2474):
        # roof.ring carries uni2460's own deltas (R18), so the instances are equal.
        if instance_outline(font, cmap[cp]).contours()[:2] != ring:
            bad.append(f"U+{cp:04X}")
    assert not bad, f"ring differs from U+2460 at {wght}: {bad}"


def test_u2789_shares_u2469(roof):
    cmap = roof.getBestCmap()
    assert cmap[0x2789] == cmap[0x2469]


@pytest.mark.parametrize("wght", WEIGHTS)
def test_pairs_keep_wanted_clearance(ctx, static, roof, wght):
    # R22: no figure pair reaches closer to the ring (disc edge) than Wanted's own ①–⑨ do.
    font, cmap = static("roof", wght), roof.getBestCmap()
    bad = []
    for cp, (_, helper) in sorted(ENCLOSED.items()):
        ring = instance_outline(font, helper)
        x0, y0, x1, y1 = ring.bounds()
        limit = pair_limit(ctx, helper, ring, roof_norm(wght))
        o = instance_outline(font, cmap[cp])
        n = len(ring.points)
        pair = Outline(o.coords[n:], [e - n for e in o.end_pts[len(ring.end_pts) :]], o.flags[n:])
        got = reach(pair, (x0 + x1) / 2, (y0 + y1) / 2)
        if got > limit + 2:
            bad.append((f"U+{cp:04X}", round(got, 1), round(limit, 1)))
    assert not bad, bad


def test_enclosed_and_helpers_keep_their_contours(static, roof):
    # Ring and disc against their 400 outline; pair helpers and enclosed glyphs
    # against their figures at the same weight, with self-intersections judged per R24.
    cmap = roof.getBestCmap()
    order = roof.getGlyphOrder()
    pairs = [n for n in order if n.startswith(PAIR_PREFIXES)]
    built = [*pairs, *sorted({cmap[cp] for cp in ENCLOSED})]
    bad, accepted = [], {}
    for wght in WEIGHTS:
        font = static("roof", wght)
        for n in (RING, DISC):
            if msgs := check_outline(instance_outline(font, n), instance_outline(static("roof", 400), n)):
                bad.append((n, wght, msgs))
        for n in built:
            failures, ok = judge(instance_outline(font, n), source_outline(font, n))
            if failures:
                bad.append((n, wght, failures))
            if ok:
                accepted[(n, wght)] = ok
    print(f"same-sign crossings accepted (R24): {sum(accepted.values())} in {len(accepted)} glyph-weights")
    for (n, wght), count in sorted(accepted.items()):
        print(f"  {n} at {wght}: {count}")
    assert not bad, bad


def skia_path(o):
    path = skia.Path()
    path.setFillType(skia.PathFillType.kWinding)
    for poly in flattened_contours(o):
        path.moveTo(*poly[0])
        for p in poly[1:]:
            path.lineTo(*p)
        path.close()
    return path


def ink_area(path, scale=4):
    """Area of ``path``'s fill in units², rasterized at ``scale`` pixels per unit."""
    b = path.computeTightBounds()
    if path.isEmpty() or b.isEmpty():
        return 0.0
    w, h = int(b.width() * scale) + 4, int(b.height() * scale) + 4
    surface = skia.Surface(w, h)
    canvas = surface.getCanvas()
    canvas.clear(skia.ColorTRANSPARENT)
    canvas.scale(scale, scale)
    canvas.translate(-b.left() + 1 / scale, -b.top() + 1 / scale)
    canvas.drawPath(path, skia.Paint(Color=skia.ColorBLACK))
    alpha = surface.makeImageSnapshot().toarray()[..., 3]
    return float(alpha.sum()) / 255 / scale**2


@pytest.mark.parametrize("wght", WEIGHTS)
def test_disc_figures_have_no_ink_inside(static, roof, wght):
    # R27: check_outline sees one contour at a time, so measure the filled glyph: no ink may
    # fall inside a knocked-out figure.
    font, cmap = static("roof", wght), roof.getBestCmap()
    disc = len(instance_outline(font, DISC).end_pts)
    bad = []
    for cp, (_, helper) in sorted(ENCLOSED.items()):
        if helper != DISC:
            continue
        o = instance_outline(font, cmap[cp])
        figures = combine([part(o, n) for n in range(disc, len(o.end_pts))], [(0, 0)] * 4)
        inside = skia.Op(skia_path(o), skia_path(figures), skia.PathOp.kIntersect_PathOp)
        if (area := ink_area(inside)) > 1:
            bad.append((f"U+{cp:04X}", round(area, 1)))
    assert not bad, f"ink inside knocked-out figures at {wght} (units²): {bad}"


def test_supsub_signs_keep_their_contours(static, roof, ws):
    # Each sign is checked against its Wanted Sans source at 400, as Acceptance 6 does.
    cmap = roof.getBestCmap()
    bad = [
        (f"U+{cp:04X}", wght, msgs)
        for wght in WEIGHTS
        for cp, (source, _) in sorted(SUPSUB.items())
        if (msgs := check_outline(instance_outline(static("roof", wght), cmap[cp]), ws.outline(source, 400)))
    ]
    assert not bad, bad
