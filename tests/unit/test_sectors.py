"""R24's sector test (tests/acceptance/sectors.py) on synthetic outlines."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "acceptance"))

from sectors import FOLD_ALLOWANCE, judge_crossings, reversed_area  # noqa: E402

from roofsans.outline import Outline  # noqa: E402

OUTER = [(0, 0), (0, 100), (100, 100), (100, 0)]  # clockwise: a TrueType outer contour
NOTCH = [(0, 0), (0, 100), (40, 100), (60, 40), (60, 100), (100, 100), (100, 0)]


def outline(*contours) -> Outline:
    pts, ends = [], []
    for c in contours:
        pts += [tuple(map(float, p)) for p in c]
        ends.append(len(pts) - 1)
    return Outline(pts + [(0.0, 0.0)] * 4, ends, [1] * len(pts))


def shifted(contour, dx):
    return [(x + dx, y) for x, y in contour]


def test_bow_tie_fails():
    v = judge_crossings(outline([(0, 0), (0, 100), (100, 0), (100, 100)]))
    assert len(v.failures) == 1 and v.accepted == 0


def test_crossed_notch_is_a_same_sign_overlap():
    # The edge below the notch rose past the edge above it: the strokes overlap, no hole.
    crossed = [(0, 0), (0, 100), (45, 100), (60, 60), (40, 60), (55, 100), (100, 100), (100, 0)]
    v = judge_crossings(outline(crossed), [outline(NOTCH)])
    assert (v.failures, v.accepted, v.allowed) == ([], 1, [])


def test_twisted_counter_inside_an_outer_fails():
    # The total sectors are (−1, −2, −1, 0), with no opposite signs; the counter's own
    # sectors (0, −1, 0, 1) show the twist.
    bow = [(20, 20), (80, 80), (80, 20), (20, 80)]
    v = judge_crossings(outline(OUTER, bow))
    assert len(v.failures) == 1 and "twist" in v.failures[0]
    assert v.accepted == 0 and v.allowed == []


def test_tiny_counter_fold_is_allowed_and_listed():
    # A counter (counterclockwise) whose bottom edge folds into a reversed 1 × 1 loop.
    counter = [(20, 20), (51, 20), (51, 19), (50, 19), (50, 20.5), (80, 20.5), (80, 80), (20, 80)]
    v = judge_crossings(outline(OUTER, counter))
    assert v.failures == [] and v.accepted == 0
    assert len(v.allowed) == 1 and "counter fold 1.00" in v.allowed[0]
    assert FOLD_ALLOWANCE == 1.0


def test_large_counter_fold_fails():
    counter = [(20, 20), (60, 20), (60, 10), (50, 10), (50, 25), (80, 25), (80, 80), (20, 80)]
    v = judge_crossings(outline(OUTER, counter))
    assert len(v.failures) == 1 and "twist" in v.failures[0] and v.allowed == []


def test_pinched_counter_fails():
    # Both sides of a counter cross twice, so its middle runs reversed (2,250 unit², filled
    # with ink) between two larger forward end lobes. Cut at either crossing, both loops
    # have forward net areas, which once read as a 0 unit² fold.
    outer = [(0, 0), (0, 200), (100, 200), (100, 0)]
    counter = [
        (20, 10), (80, 10), (80, 70), (20, 85), (20, 115), (80, 130), (80, 190),
        (20, 190), (20, 130), (80, 115), (80, 85), (20, 70),
    ]
    assert reversed_area(counter) == pytest.approx(2250)
    v = judge_crossings(outline(outer, counter))
    assert len(v.failures) == 2 and all("twist" in f for f in v.failures)
    assert v.allowed == []


def test_reversed_area_of_a_simple_counter_is_zero():
    assert reversed_area([(20, 20), (80, 20), (80, 80), (20, 80)]) == 0


def dense(contour, k=10):
    """``contour`` with each edge split into ``k`` pieces, so edge indices run far apart."""
    out = []
    for (ax, ay), (bx, by) in zip(contour, contour[1:] + contour[:1]):
        out += [(ax + (bx - ax) * m / k, ay + (by - ay) * m / k) for m in range(k)]
    return out


def two_notches(left_crossed, right_crossed):
    """An outer contour with two notches in its top edge; a crossed notch overlaps itself."""
    crossed, open_ = [(60, 60), (40, 60)], [(50, 40), (50, 41)]
    left = [(45, 100), *(crossed if left_crossed else open_), (55, 100)]
    right = [(145, 100), *([(160, 60), (140, 60)] if right_crossed else [(150, 40), (150, 41)]), (155, 100)]
    return dense([(0, 0), (0, 100), *left, *right, (200, 100), (200, 0)])


def test_source_crossings_are_excused_per_crossing():
    # The source already crosses in the left notch only; the right notch's crossing is new.
    v = judge_crossings(outline(two_notches(True, True)), [outline(two_notches(True, False))])
    assert (v.matched, v.accepted, v.failures) == (1, 1, [])


def test_source_crossings_match_by_edge_index_after_a_move():
    # Embolden and zone maps move points by tens of units but keep them in order.
    bow = [(0, 0), (0, 100), (100, 0), (100, 100)]
    v = judge_crossings(outline(bow), [outline(shifted(bow, 30))])
    assert (v.matched, v.failures) == (1, [])
    assert len(judge_crossings(outline(bow), [outline(OUTER)]).failures) == 1


def test_location_fallback_when_vertex_counts_differ():
    bow = [(0, 0), (0, 100), (100, 0), (100, 100)]
    split = [(0, 0), (0, 50), (0, 100), (100, 0), (100, 100)]
    assert judge_crossings(outline(bow), [outline(shifted(split, 2))]).matched == 1
    assert len(judge_crossings(outline(bow), [outline(shifted(split, 20))]).failures) == 1


def test_one_source_crossing_excuses_one_candidate_crossing():
    # The source crosses once, in the left notch. The candidate adds a second notch that
    # crosses itself and the first: three crossings, all within ±32 edges of the source's.
    # One is excused; the other two are judged (as same-sign overlaps).
    notch = [(45, 100), (60, 60), (40, 60), (55, 100)]
    near = [(57, 100), (70, 60), (52, 60), (66, 100)]
    source = dense([(0, 0), (0, 100), *notch, (56, 100), (60, 99), (64, 99), (66, 100), (200, 100), (200, 0)], k=2)
    candidate = dense([(0, 0), (0, 100), *notch, *near, (200, 100), (200, 0)], k=2)
    v = judge_crossings(outline(candidate), [outline(source)])
    assert (v.matched, v.accepted, v.failures) == (1, 2, [])
