"""Acceptance 3 and design decision 11: fullwidth letters, digits, and signs."""

import pytest

from roofsans.axis import roof_norm, roof_wght
from roofsans.selection import Rule

pytestmark = pytest.mark.acceptance

WEIGHTS = (400, 750, 1000)
FULLWIDTH_ADVANCE = 1920
FLOAT_SLACK = 1e-3


def outline(font, name):
    """Decomposed coordinates, end points, and advance of ``name`` in a static instance."""
    glyf = font["glyf"]
    coords, end_pts, _ = glyf[name].getCoordinates(glyf)
    return list(coords), list(end_pts), font["hmtx"][name][0]


def shift_of(roof_pts, roof_end, wanted_pts, wanted_end):
    """The x shift that maps the Wanted Sans outline onto the Roof one, or None.

    Unrounded instances carry float noise, so points match within ``FLOAT_SLACK``.
    """
    if roof_end != wanted_end or len(roof_pts) != len(wanted_pts) or not roof_pts:
        return None
    dx = roof_pts[0][0] - wanted_pts[0][0]
    if any(
        abs(r[0] - w[0] - dx) > FLOAT_SLACK or abs(r[1] - w[1]) > FLOAT_SLACK
        for r, w in zip(roof_pts, wanted_pts)
    ):
        return None
    return dx


def instance_wght(wght):
    """The weight an instance shows: its normalized location is stored as F2Dot14."""
    return roof_wght(round(roof_norm(wght) * 16384) / 16384)


def ink_center_x(pts):
    xs = [p[0] for p in pts]
    return (min(xs) + max(xs)) / 2


@pytest.mark.parametrize("wght", WEIGHTS)
def test_a03_fullwidth(static, ctx, ws, wght):
    w, r = static("wanted", wght), static("roof", wght)
    wcmap, rcmap = w.getBestCmap(), r.getBestCmap()
    codepoints = ctx.selection.codepoints(Rule.R3_FULLWIDTH)
    assert len(codepoints) == 62
    bad = []
    for cp in codepoints:
        if cp not in rcmap:
            bad.append((hex(cp), "missing"))
            continue
        base = wcmap[cp - 0xFEE0]
        rc, rend, radv = outline(r, rcmap[cp])
        wc, wend, _ = outline(w, base)
        # The instance's hmtx rounds Wanted Sans's advance, so take it unrounded.
        wadv = ws.advance(base, instance_wght(wght))
        dx = shift_of(rc, rend, wc, wend)
        if dx is None:
            bad.append((hex(cp), "outline"))
        elif abs(dx - (FULLWIDTH_ADVANCE - wadv - dx)) > 1:
            bad.append((hex(cp), "gaps", dx, FULLWIDTH_ADVANCE - wadv - dx))
        if radv != FULLWIDTH_ADVANCE:
            bad.append((hex(cp), "advance", radv))
    assert not bad, f"{len(bad)} differ at {wght}: {bad[:10]}"


@pytest.mark.parametrize("wght", WEIGHTS)
def test_a03_fullwidth_signs(static, ctx, wght):
    w, r, p = static("wanted", wght), static("roof", wght), static("pretendard", min(wght, 930))
    pcmap, rcmap = ctx.pretendard.getBestCmap(), r.getBestCmap()
    pglyf = ctx.pretendard["glyf"]
    codepoints = ctx.selection.codepoints(Rule.R3_SIGN)
    assert len(codepoints) == 23
    bad = []
    for cp in codepoints:
        if cp not in rcmap:
            bad.append((hex(cp), "missing"))
            continue
        (component,) = pglyf[pcmap[cp]].components
        rc, rend, radv = outline(r, rcmap[cp])
        wc, wend, _ = outline(w, component.glyphName)
        pc, _, _ = outline(p, pcmap[cp])
        if shift_of(rc, rend, wc, wend) is None:
            bad.append((hex(cp), "outline"))
        elif abs(ink_center_x(rc) - ink_center_x(pc)) > 1:
            bad.append((hex(cp), "center", ink_center_x(rc), ink_center_x(pc)))
        if radv != FULLWIDTH_ADVANCE:
            bad.append((hex(cp), "advance", radv))
    assert not bad, f"{len(bad)} differ at {wght}: {bad[:10]}"
