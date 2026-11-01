import pytest

from roofsans.harmonize import (
    apply_zone_map,
    dy_score,
    harmonize_outline,
    solve_dy,
    solve_masters,
    solve_w_prime,
    stroke_score,
)
from roofsans.selection import Zone


def test_apply_zone_map_is_piecewise_linear():
    m = ((0.0, 0.0), (100.0, 50.0), (200.0, 250.0))
    assert [apply_zone_map(m, y) for y in (0, 50, 100, 150, 200)] == [0, 25, 50, 150, 250]
    # Outside the pairs, a shift by the nearest pair's offset.
    assert apply_zone_map(m, -30) == -30
    assert apply_zone_map(m, 260) == 310


def test_w_prime(ps, ws):
    assert [round(solve_w_prime(ps, ws, w)) for w in (400, 700, 1000)] == pytest.approx([387, 672, 952], abs=3)


def test_stroke_score_scales_each_check_to_one():
    # A group median of 3% and a single stroke at 10% both score exactly 1.
    assert stroke_score([[0.03, 0.03, -0.01]]) == pytest.approx(1)
    assert stroke_score([[0.0, 0.0, 0.10], [0.0]]) == pytest.approx(1)
    assert stroke_score([[0.0, 0.01, -0.02], [0.015]]) == pytest.approx(0.5)


def test_dy(ps, ws):
    # Ruling R17: δy is solved against Acceptance 5's stroke checks (about 7 / 41 / 80).
    for w in (400, 700, 1000):
        w_prime = solve_w_prime(ps, ws, w)
        assert dy_score(ps, ws, w, w_prime, solve_dy(ps, ws, w, w_prime)) <= 1


def test_zone_map_hits_wanted_heights(ps, ws):
    # The input Wanted Sans stops at 400, so solve only the master this test reads.
    p = solve_masters(ps, ws, locs=(1.0,))[1.0]
    x = harmonize_outline(ps.outline("x", p.w_prime), Zone.LOWER, p)
    assert x.bounds()[3] == pytest.approx(1032, abs=1)
