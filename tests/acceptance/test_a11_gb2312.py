"""Acceptance 11: add exactly C1 while preserving every previous cmap entry."""

import pytest
from fontTools.ttLib import TTFont

from roofsans.chinese import gb2312_hanzi
from roofsans.selection import Rule

pytestmark = pytest.mark.acceptance


def test_a11_gb2312(ctx, roof, baseline_path):
    old = TTFont(baseline_path).getBestCmap()
    new = roof.getBestCmap()
    c1 = set(ctx.selection.codepoints(Rule.C1_HANZI))
    assert len(c1) == 3260
    assert set(gb2312_hanzi()) <= new.keys()
    assert new.keys() - old.keys() == c1
    assert all(new[cp] == name for cp, name in old.items())
    assert len(new) == 24974
    assert len(roof.getGlyphOrder()) == 28400
