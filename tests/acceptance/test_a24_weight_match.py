"""Acceptance 24: light Hangul ink and Latin stem match Pretendard JP."""

from statistics import median

import pytest

from roofsans.light import ks_hangul
from roofsans.measure import ink_area, stroke
from roofsans.sampling import WantedSampler

pytestmark = pytest.mark.acceptance


@pytest.mark.parametrize("wght", (100, 200, 300))
def test_light_weight_match(roof, pretendard, ps, wght):
    sampler = WantedSampler(roof)
    rcmap, pcmap = roof.getBestCmap(), pretendard.getBestCmap()
    ratios = [ink_area(sampler.outline(rcmap[cp], wght)) / ink_area(ps.outline(pcmap[cp], wght))
              for cp in ks_hangul()]
    ink_ratio = median(ratios)
    stem_ratio = stroke(sampler.outline(rcmap[ord("l")], wght), "l_stem") / stroke(ps.outline("l", wght), "l_stem")
    print(f"WEIGHT_MATCH wght={wght} count={len(ratios)} ink_ratio={ink_ratio:.9f} l_ratio={stem_ratio:.9f}")
    assert ink_ratio == pytest.approx(1, abs=0.01)
    assert stem_ratio == pytest.approx(1, abs=0.05)
