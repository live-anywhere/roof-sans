"""H4: match Pretendard letters to Wanted Sans in height and weight."""

from __future__ import annotations

import statistics
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from roofsans.axis import H4_LOCS, roof_norm, roof_wght
from roofsans.embolden import embolden_xy
from roofsans.measure import Stroke, Zones, stroke, zones_of
from roofsans.outline import Outline
from roofsans.sampling import PretendardSampler, WantedSampler
from roofsans.selection import Zone

ZoneMap = tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class StrokePair:
    """A Pretendard letter's stroke and the Wanted Sans stroke it should match."""

    char: str
    pretendard: str
    wanted: str
    stroke: Stroke
    zone: Zone


# Acceptance 5's horizontal strokes, in two groups that each keep their median within
# MEDIAN_TOLERANCE and every stroke within EACH_TOLERANCE (ruling R17).
REFERENCE_STROKES: tuple[StrokePair, ...] = (
    StrokePair("o", "o", "o", "o_top", Zone.LOWER),
    StrokePair("o", "o", "o", "o_bottom", Zone.LOWER),
    StrokePair("e", "e", "e", "e_top", Zone.LOWER),
    StrokePair("H", "H", "H", "H_bar", Zone.CAPITAL),
    StrokePair("n", "n", "n", "n_arch", Zone.LOWER),
)
LETTER_STROKES: tuple[StrokePair, ...] = (
    StrokePair("о", "uni043E", "o", "o_top", Zone.LOWER),
    StrokePair("о", "uni043E", "o", "o_bottom", Zone.LOWER),
    StrokePair("е", "uni0435", "e", "e_top", Zone.LOWER),
    StrokePair("п", "uni043F", "n", "n_arch", Zone.LOWER),
    StrokePair("Н", "uni041D", "H", "H_bar", Zone.CAPITAL),
    StrokePair("ο", "omicron", "o", "o_top", Zone.LOWER),
    StrokePair("ε", "epsilon", "e", "e_top", Zone.LOWER),
    StrokePair("π", "pi", "n", "n_arch", Zone.LOWER),
)
STROKE_GROUPS = (REFERENCE_STROKES, LETTER_STROKES)
MEDIAN_TOLERANCE = 0.03
EACH_TOLERANCE = 0.10

# The glyphs zones_of reads; the names are the same in both fonts.
_ZONE_GLYPHS = "gpoOxlH"

W_PRIME_RANGE = (45.0, 1100.0)
W_PRIME_TOLERANCE = 0.05
DY_RANGE = (0.0, 200.0)
DY_GRID = 0.25
DY_REFINE_STEPS = 24


@dataclass(frozen=True)
class MasterParams:
    norm: float
    wght: float
    w_prime: float
    dy: float
    lower_map: ZoneMap
    capital_map: ZoneMap


def apply_zone_map(m: ZoneMap, y: float) -> float:
    """Piecewise linear between the pairs; outside them, a shift by the nearest pair's offset."""
    if y <= m[0][0]:
        return y + m[0][1] - m[0][0]
    for (a, a2), (b, b2) in zip(m, m[1:]):
        if y <= b:
            return a2 + (y - a) * (b2 - a2) / (b - a)
    return y + m[-1][1] - m[-1][0]


def harmonize_outline(o: Outline, zone: Zone, p: MasterParams) -> Outline:
    """Embolden ``o`` in y by ``p.dy``, then remap y onto Wanted Sans's zones; x stays."""
    m = p.lower_map if zone is Zone.LOWER else p.capital_map
    return embolden_xy(o, 0, p.dy).transformed(lambda x, y: (x, apply_zone_map(m, y)))


def stroke_score(ratios: list[list[float]]) -> float:
    """Acceptance 5's weight check as one number: at most 1 when every group passes.

    ``ratios`` holds, per stroke group, (harmonized − Wanted Sans) / Wanted Sans.
    """
    worst_median = max(abs(statistics.median(g)) for g in ratios)
    worst = max(abs(r) for g in ratios for r in g)
    return max(worst_median / MEDIAN_TOLERANCE, worst / EACH_TOLERANCE)


def solve_w_prime(ps: PretendardSampler, ws: WantedSampler, wght: float) -> float:
    """The Pretendard weight whose ``l`` stem equals Wanted Sans's at ``wght``."""
    target = stroke(ws.outline("l", wght), "l_stem")
    lo, hi = W_PRIME_RANGE
    while True:
        mid = (lo + hi) / 2
        err = stroke(ps.outline("l", mid), "l_stem") - target
        if abs(err) <= W_PRIME_TOLERANCE:
            return mid
        if hi - lo < 1e-9:
            raise ValueError(f"no Pretendard weight matches Wanted Sans's l stem at {wght}")
        lo, hi = (mid, hi) if err < 0 else (lo, mid)


class _Master:
    """Pretendard at one master's ``w′``, with Wanted Sans's zones and strokes at ``wght``."""

    def __init__(self, ps: PretendardSampler, ws: WantedSampler, wght: float, w_prime: float) -> None:
        self.norm, self.wght, self.w_prime = roof_norm(wght), wght, w_prime
        self._zone_src = {c: ps.outline(c, w_prime) for c in _ZONE_GLYPHS}
        self._zone_dst: Zones = zones_of(lambda c: ws.outline(c, wght))
        pairs = [p for g in STROKE_GROUPS for p in g]
        self._letters = {p.pretendard: ps.outline(p.pretendard, w_prime) for p in pairs}
        self._targets = [[stroke(ws.outline(p.wanted, wght), p.stroke) for p in g] for g in STROKE_GROUPS]

    def params(self, dy: float) -> MasterParams:
        # The zone maps start from the emboldened Pretendard zones.
        src = zones_of(lambda c: embolden_xy(self._zone_src[c], 0, dy))
        dst = self._zone_dst
        lower = tuple(sorted(zip(src.lower, dst.lower)))
        capital = tuple(sorted(zip(src.capital, dst.capital)))
        return MasterParams(self.norm, self.wght, self.w_prime, dy, lower, capital)

    def score(self, dy: float) -> float:
        p = self.params(dy)
        ratios = [
            [stroke(harmonize_outline(self._letters[q.pretendard], q.zone, p), q.stroke) / t - 1 for q, t in zip(g, ts)]
            for g, ts in zip(STROKE_GROUPS, self._targets)
        ]
        return stroke_score(ratios)


def dy_score(ps: PretendardSampler, ws: WantedSampler, wght: float, w_prime: float, dy: float) -> float:
    """``stroke_score`` of the harmonized strokes at master ``wght`` with ``dy``."""
    return _Master(ps, ws, wght, w_prime).score(dy)


def _minimize(f: Callable[[float], float]) -> float:
    """A 0.25-unit grid over DY_RANGE, then a ternary search around the best point.

    Ties go to the point nearest the center of the window where ``f`` ≤ 1.
    """
    lo, hi = DY_RANGE
    grid = [lo + i * DY_GRID for i in range(int((hi - lo) / DY_GRID) + 1)]
    scores = [f(d) for d in grid]
    best = min(scores)
    ties = [d for d, s in zip(grid, scores) if s <= best + 1e-9]
    window = [d for d, s in zip(grid, scores) if s <= 1] or ties
    center = (window[0] + window[-1]) / 2
    d0 = min(ties, key=lambda d: abs(d - center))
    if len(ties) > 1:
        return d0
    a, b = max(lo, d0 - DY_GRID), min(hi, d0 + DY_GRID)
    for _ in range(DY_REFINE_STEPS):
        m1, m2 = a + (b - a) / 3, b - (b - a) / 3
        a, b = (a, m2) if f(m1) <= f(m2) else (m1, b)
    return (a + b) / 2


def solve_dy(ps: PretendardSampler, ws: WantedSampler, wght: float, w_prime: float) -> float:
    """The y embolden strength that best meets Acceptance 5's stroke checks at ``wght`` (R17)."""
    return _minimize(_Master(ps, ws, wght, w_prime).score)


def solve_masters(
    ps: PretendardSampler, ws: WantedSampler, locs: tuple[float, ...] = H4_LOCS
) -> dict[float, MasterParams]:
    """H4 parameters at each Roof master location in ``locs``."""
    out = {}
    for norm in locs:
        wght = roof_wght(norm)
        master = _Master(ps, ws, wght, solve_w_prime(ps, ws, wght))
        out[norm] = master.params(_minimize(master.score))
    return out


def outline_masters(outline_of: Callable[[float], Outline], zone: Zone, params: Mapping[float, MasterParams]) -> dict[float, Outline]:
    """Harmonized masters of one glyph; ``outline_of(w′)`` samples it in Pretendard."""
    return {t: harmonize_outline(outline_of(p.w_prime), zone, p) for t, p in params.items()}
