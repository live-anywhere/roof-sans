import pytest

from roofsans.embolden import embolden_xy
from roofsans.measure import stroke
from roofsans.sampling import PretendardSampler


def test_embolden_y_only_keeps_x(pretendard):
    o = PretendardSampler(pretendard).outline("o", 400)
    e = embolden_xy(o, 0, 20)
    assert [p[0] for p in e.coords] == [p[0] for p in o.coords]
    assert stroke(e, "o_top") == pytest.approx(stroke(o, "o_top") + 20, abs=1)


def test_embolden_keeps_structure(ps):
    # A mirrored composite: its contours run the other way (R4).
    for name in ("o", "arrowdown"):
        o = ps.outline(name, 400)
        e = embolden_xy(o, 16, 24)
        assert len(e.coords) == len(o.coords)
        assert (e.end_pts, e.flags) == (o.end_pts, o.flags)
        assert e.coords[-4:] == o.coords[-4:]
        assert e.coords[:-4] != o.coords[:-4]


def test_embolden_x_widens_stem(ps):
    o = ps.outline("l", 400)
    e = embolden_xy(o, 20, 0)
    assert [p[1] for p in e.coords] == [p[1] for p in o.coords]
    assert stroke(e, "l_stem") == pytest.approx(stroke(o, "l_stem") + 20, abs=1)
