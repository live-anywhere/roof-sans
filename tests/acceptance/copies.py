"""The Acceptance 2 comparison of copied glyphs, shared by test_a02 and test_a04."""

from collections.abc import Iterable

import pytest

from roofsans.rules.h6_copy import copy_closure

# (wght, outline tolerance): light delta scaling rounds; old master limits stay exact.
COPY_WEIGHTS = [(100, 1), (250, 1), (400, 0), (700, 1), (930, 0)]


@pytest.fixture(scope="module")
def pj_names(ctx):
    return copy_closure(ctx)


def outline(font, name):
    """Decomposed coordinates, end points, and advance of ``name`` in a static instance."""
    glyf = font["glyf"]
    coords, end_pts, _ = glyf[name].getCoordinates(glyf)
    return list(coords), list(end_pts), font["hmtx"][name][0]


def max_abs_diff(a, b):
    return max((max(abs(p[0] - q[0]), abs(p[1] - q[1])) for p, q in zip(a, b)), default=0)


def differing_copies(p, r, pairs: Iterable[tuple[str, str]], tolerance: float, advance_tolerance: float = 0,
                     composite_tolerance: float | None = None) -> list[str]:
    """Pretendard names whose Roof copy differs from Pretendard instance ``p`` in ``r``.

    ``pairs`` holds (Pretendard name, Roof name); ``p`` and ``r`` are static instances
    at the same weight. Advances stay exact unless the caller explicitly allows the
    light-weight rounding tolerance through ``advance_tolerance``. Decomposed light
    composites may accumulate component and parent-offset rounding, accounted for
    only when ``composite_tolerance`` is explicitly supplied.
    """
    bad = []
    for source, name in pairs:
        pc, pend, padv = outline(p, source)
        rc, rend, radv = outline(r, name)
        limit = composite_tolerance if composite_tolerance is not None and p["glyf"][source].isComposite() else tolerance
        if pend != rend or len(pc) != len(rc) or max_abs_diff(pc, rc) > limit or abs(padv - radv) > advance_tolerance:
            bad.append(source)
    return bad
