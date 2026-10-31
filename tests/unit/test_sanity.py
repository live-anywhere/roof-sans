from roofsans.embolden import embolden_xy
from roofsans.outline import Outline
from roofsans.sampling import PretendardSampler
from roofsans.sanity import check_outline

PHANTOMS = [(0, 0), (500, 0), (0, 0), (0, 0)]
SQUARE = [(0, 0), (0, 300), (300, 300), (300, 0)]


def _outline(*contours) -> Outline:
    coords, end_pts = [], []
    for c in contours:
        coords.extend(c)
        end_pts.append(len(coords) - 1)
    return Outline(coords + PHANTOMS, end_pts, [1] * len(coords))


def test_sanity_flags_collapse(pretendard):
    o = PretendardSampler(pretendard).outline("o", 400)
    assert check_outline(o, o) == []
    assert any("collapsed" in m for m in check_outline(embolden_xy(o, 0, 900), o))


def test_sanity_flags_contour_count():
    assert check_outline(_outline(SQUARE), _outline(SQUARE, SQUARE)) != []


def test_sanity_outer_reversal_is_not_collapse():
    got = check_outline(_outline(SQUARE[::-1]), _outline(SQUARE))
    assert len(got) == 1 and "collapsed" not in got[0]


def test_sanity_flags_tiny_counter():
    hole = [(100, 100), (100.5, 100), (100.5, 101), (100, 101)]
    ref_hole = [(100, 100), (200, 100), (200, 200), (100, 200)]
    got = check_outline(_outline(SQUARE, hole), _outline(SQUARE, ref_hole))
    assert len(got) == 1 and "collapsed" in got[0]


def test_sanity_flags_new_self_intersection():
    bowtie = [(0, 0), (0, 300), (300, 0), (300, 300)]
    assert any("self-intersect" in m for m in check_outline(_outline(bowtie), _outline(SQUARE)))
    assert check_outline(_outline(bowtie), _outline(bowtie)) == []
