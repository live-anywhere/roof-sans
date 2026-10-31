from roofsans.axis import PJ_PEAK, W_MID, roof_norm, roof_wght
from roofsans.sampling import WantedSampler
from roofsans.variations import remap_pretendard_tuples, tuples_from_masters

from helpers import apply, interpolated_coords, max_abs_diff


def test_remap_plateau(pretendard, static):
    name = pretendard.getBestCmap()[ord("漢")]
    tvs = remap_pretendard_tuples(pretendard["gvar"].variations[name])
    at = lambda t: interpolated_coords(pretendard["glyf"], name, tvs, t)   # test helper
    assert at(1.0) == at(PJ_PEAK)
    assert max_abs_diff(at(roof_norm(700)), static("pretendard", 700)["glyf"][name]) <= 1


def test_masters_roundtrip(wanted):
    ws = WantedSampler(wanted)
    m = {t: ws.outline("A", roof_wght(t)).coords for t in (0.0, W_MID, 1.0)}
    end_pts = ws.outline("A", 400).end_pts
    tvs = tuples_from_masters(m, end_pts)
    for w in (400, 550, 750, 900, 1000):
        assert max_abs_diff(apply(m[0.0], tvs, roof_norm(w), end_pts), ws.outline("A", w).coords) <= 0.5
