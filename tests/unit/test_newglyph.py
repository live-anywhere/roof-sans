import pytest

from roofsans.axis import COMPOSITE_LOCS, roof_wght
from roofsans.newglyph import composite_glyph, newglyph_outline
from roofsans.sampling import WantedSampler
from roofsans.selection import Rule


def test_composite_offsets_vary(wanted):
    ws = WantedSampler(wanted)
    adv = {t: ws.advance("zero", roof_wght(t)) for t in COMPOSITE_LOCS}
    g = composite_glyph("t", {t: [("zero", (1920 - adv[t]) / 2, 0)] for t in COMPOSITE_LOCS},
                        {t: 1920 for t in COMPOSITE_LOCS}, (), Rule.R3_FULLWIDTH, "test")
    o = newglyph_outline(g, 1.0, lambda n, t: ws.outline(n, roof_wght(t)))
    assert o.advance() == 1920 and o.bounds()[0] == pytest.approx(ws.outline("zero", 1000).bounds()[0] + 240, abs=0.5)


def test_composite_offsets_land_within_half_unit(wanted):
    # Ruling R20: deltas come from the unrounded masters, so 750's fractional offset holds.
    ws = WantedSampler(wanted)
    dx = {t: (1920 - ws.advance("zero", roof_wght(t))) / 2 for t in COMPOSITE_LOCS}
    g = composite_glyph("t", {t: [("zero", dx[t], 0)] for t in COMPOSITE_LOCS},
                        {t: 1920 for t in COMPOSITE_LOCS}, (), Rule.R3_FULLWIDTH, "test")
    for t in COMPOSITE_LOCS:
        o = newglyph_outline(g, t, lambda n, u: ws.outline(n, roof_wght(u)))
        assert o.bounds()[0] == pytest.approx(ws.outline("zero", roof_wght(t)).bounds()[0] + dx[t], abs=0.5)
        assert o.advance() == pytest.approx(1920, abs=0.5)


def test_composite_flags_match_wanted_onehalf(wanted):
    # Ruling R21: every input composite sets OVERLAP_COMPOUND on its first component.
    ws = WantedSampler(wanted)
    source = wanted["glyf"]["onehalf"]
    parts = [(c.glyphName, c.x, c.y) for c in source.components]
    g = composite_glyph("t", {0.0: parts}, {0.0: ws.advance("onehalf", 400)}, (), Rule.H3_FRACTION, "test")
    assert [c.flags for c in g.glyph.components] == [c.flags for c in source.components]
