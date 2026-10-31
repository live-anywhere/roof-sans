import pytest

from roofsans.measure import horizontal_runs, stroke, vertical_runs, zones_of
from roofsans.outline import Outline
from roofsans.sampling import WantedSampler

PHANTOMS = [(0, 0), (500, 0), (0, 0), (0, 0)]


def _ring() -> Outline:
    # A clockwise 0..300 square with a counter-clockwise 100..200 hole.
    outer = [(0, 0), (0, 300), (300, 300), (300, 0)]
    inner = [(100, 100), (200, 100), (200, 200), (100, 200)]
    return Outline(outer + inner + PHANTOMS, [3, 7], [1] * 8)


def test_runs_pair_under_nonzero():
    o = _ring()
    assert horizontal_runs(o, 150) == [(0, 100), (200, 300)]
    assert horizontal_runs(o, 50) == [(0, 300)]
    assert vertical_runs(o, 150) == [(0, 100), (200, 300)]
    assert horizontal_runs(o, 400) == []


def test_runs_follow_quadratic_curve():
    # One off-curve point at (100, 200): the curve's apex is y = 100 at x = 100.
    o = Outline([(0, 0), (100, 200), (200, 0)] + PHANTOMS, [2], [1, 0, 1])
    ((y0, y1),) = vertical_runs(o, 100)
    assert (y0, y1) == pytest.approx((0, 100), abs=0.1)


@pytest.mark.parametrize("w,l,o,e,h,n", [(400,168,160,160,164,156),(700,284,260,233,278,243),(1000,400,360,305,392,322)])
def test_wanted_strokes(wanted, w, l, o, e, h, n):
    ws = WantedSampler(wanted)
    got = [stroke(ws.outline(c, w), k) for c, k in (("l","l_stem"),("o","o_top"),("e","e_top"),("H","H_bar"),("n","n_arch"))]
    assert got == pytest.approx([l, o, e, h, n], abs=2)


def test_wanted_zones(wanted):
    z = zones_of(lambda c: WantedSampler(wanted).outline(c, 400))
    assert z.lower == pytest.approx((-460, -432, z.lower[2], 0, 1032, 1060, 1448), abs=1)
    assert z.capital[2] == pytest.approx(1448, abs=1)
