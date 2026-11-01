"""Acceptance 5, H4: Pretendard letters match Wanted Sans in height and weight."""

import statistics

import pytest

from roofsans.axis import roof_norm
from roofsans.harmonize import (
    EACH_TOLERANCE,
    LETTER_STROKES,
    MEDIAN_TOLERANCE,
    REFERENCE_STROKES,
    outline_masters,
    solve_w_prime,
)
from roofsans.measure import horizontal_runs, stroke
from roofsans.newglyph import newglyph_outline, simple_glyph
from roofsans.outline import Outline
from roofsans.rules import h4_letters
from roofsans.selection import Rule, Zone

pytestmark = pytest.mark.acceptance

WEIGHTS = (400, 550, 700, 850, 1000)

# (Roof letter, its edge, Wanted Sans glyph, its edge): bounds index 1 is the bottom, 3 the top.
HEIGHTS = (
    ("х", 3, "x", 3),
    ("ο", 3, "o", 3),
    ("ο", 1, "o", 1),
    ("р", 1, "p", 1),
    # Pretendard's у ends at its p/y depth, so it matches Wanted Sans's y, not g (R19).
    ("у", 1, "y", 1),
    ("Н", 3, "H", 3),
    ("О", 3, "O", 3),
    ("О", 1, "O", 1),
)


def roof_outline(font, char: str) -> Outline:
    glyf = font["glyf"]
    coords, ends, flags = glyf[font.getBestCmap()[ord(char)]].getCoordinates(glyf)
    return Outline([tuple(p) for p in coords] + [(0, 0)] * 4, list(ends), list(flags))


def low_stem(o: Outline) -> float:
    """The left vertical stem at 20% of the height, below the arch of `n` and the bar of `н`."""
    _, y0, _, y1 = o.bounds()
    a, b = horizontal_runs(o, y0 + 0.2 * (y1 - y0))[0]
    return b - a


def check_strokes(pairs, outline_of, ws, wght):
    ratios = {(q.char, q.stroke): stroke(outline_of(q), q.stroke) / stroke(ws.outline(q.wanted, wght), q.stroke) - 1 for q in pairs}
    median = statistics.median(ratios.values())
    assert abs(median) <= MEDIAN_TOLERANCE, f"median {median:+.2%} at {wght}: {ratios}"
    bad = {k: f"{r:+.2%}" for k, r in ratios.items() if abs(r) > EACH_TOLERANCE}
    assert not bad, f"strokes off by more than 10% at {wght}: {bad}"


@pytest.mark.parametrize("wght", WEIGHTS)
def test_heights(static, ws, wght):
    roof = static("roof", wght)
    bad = []
    for char, i, wanted, j in HEIGHTS:
        got, want = roof_outline(roof, char).bounds()[i], ws.outline(wanted, wght).bounds()[j]
        if abs(got - want) > 2:
            bad.append((char, "top" if i == 3 else "bottom", got, want))
    assert not bad, f"{wght}: {bad}"


@pytest.mark.parametrize("wght", WEIGHTS)
def test_letter_weights(static, ctx, ws, wght):
    roof = static("roof", wght)
    # Pretendard draws н and п with thinner stems than n; H4 keeps that ratio (R19).
    w_prime = solve_w_prime(ctx.ps, ws, wght)
    pcmap = ctx.pretendard.getBestCmap()
    pretendard_n = low_stem(ctx.ps.outline("n", w_prime))
    wanted_n = low_stem(ws.outline("n", wght))
    for char in "нп":
        want = low_stem(ctx.ps.outline(pcmap[ord(char)], w_prime)) / pretendard_n
        got = low_stem(roof_outline(roof, char)) / wanted_n
        assert got == pytest.approx(want, rel=0.03), f"{char} stem ratio to n at {wght}"
    check_strokes(LETTER_STROKES, lambda q: roof_outline(roof, q.char), ws, wght)


@pytest.fixture(scope="module")
def references(ctx):
    """Pretendard's ``l o e H n`` through the H4 masters and gvar tuples, as Roof glyphs."""
    params = h4_letters.params(ctx)
    zones = {"l": Zone.LOWER, "o": Zone.LOWER, "e": Zone.LOWER, "H": Zone.CAPITAL, "n": Zone.LOWER}
    out = {}
    for name, zone in zones.items():
        masters = outline_masters(lambda w: ctx.ps.outline(name, w), zone, params)
        out[name] = simple_glyph(name, masters, [], Rule.H4_LETTER, name)
    return out


@pytest.mark.parametrize("wght", WEIGHTS)
def test_reference_weights(references, ctx, ws, wght):
    def at(name):
        return newglyph_outline(references[name], roof_norm(wght), ctx.outline)

    assert stroke(at("l"), "l_stem") == pytest.approx(stroke(ws.outline("l", wght), "l_stem"), rel=0.03)
    check_strokes(REFERENCE_STROKES, lambda q: at(q.pretendard), ws, wght)
