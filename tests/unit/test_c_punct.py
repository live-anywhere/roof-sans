import pytest

from roofsans.assemble import planned_cmap
from roofsans.axis import COMPOSITE_LOCS, PJ_PEAK
from roofsans.newglyph import newglyph_outline
from roofsans.rules import c_punct, h6_copy, r3_fullwidth
from roofsans.rules.c_hanzi import calibrate, ink_bounds
from roofsans.selection import Rule


@pytest.fixture(scope='module')
def punctuation(ctx):
    h6_copy.copy_closure(ctx)
    ctx.cmap = planned_cmap(ctx)
    for g in r3_fullwidth.contribute(ctx):
        ctx.contributed[g.name] = g
    return {g.name: g for g in c_punct.contribute(ctx)}


def test_c_punct_parts(ctx, punctuation):
    assert len(punctuation) == 9
    for cp in (*c_punct.ZHS_SIGNS, *c_punct.ZHS_QUOTES):
        g = punctuation[f'uni{cp:04X}.zhs']
        assert not g.unicodes and g.glyph.isComposite()
        assert g.rule is Rule.C3_PUNCT
        assert len(g.glyph.components) == 1
        component = g.glyph.components[0].glyphName
        expected = (ctx.contributed[ctx.cmap[cp]].glyph.components[0].glyphName
                    if cp in c_punct.ZHS_SIGNS else ctx.cmap[cp])
        assert component == expected
        for t in COMPOSITE_LOCS:
            assert newglyph_outline(g, t, ctx.outline).advance() == 1920


def test_c_punct_centers(ctx, punctuation):
    c = calibrate(ctx)
    for cp in (*c_punct.ZHS_SIGNS, *c_punct.ZHS_QUOTES):
        source = ink_bounds(ctx.cs.outline(ctx.shs_cn.getBestCmap()[cp], c.w400))
        target = c.scale * (source[0] + source[2]) / 2 + c.dx400
        actual = ink_bounds(newglyph_outline(punctuation[f'uni{cp:04X}.zhs'], 0, ctx.outline))
        assert (actual[0] + actual[2]) / 2 == pytest.approx(target, abs=1), chr(cp)


def test_c_punct_source_centers(ctx):
    c = calibrate(ctx)
    centers = {0xFF01: 250, 0xFF1A: 250, 0xFF1B: 243.4, 0xFF1F: 247.0,
               0x2018: 879.3, 0x2019: 120.7, 0x201C: 793.9, 0x201D: 206.1, 0x00B7: 500}
    for cp, expected in centers.items():
        bounds = ink_bounds(ctx.cs.outline(ctx.shs_cn.getBestCmap()[cp], c.w400))
        assert (bounds[0] + bounds[2]) / 2 == pytest.approx(expected, abs=1), chr(cp)


def test_c_punct_target_interpolation(ctx):
    c = calibrate(ctx)
    for cp in (*c_punct.ZHS_SIGNS, *c_punct.ZHS_QUOTES):
        source = ctx.shs_cn.getBestCmap()[cp]
        a = ink_bounds(ctx.cs.outline(source, c.w400))
        b = ink_bounds(ctx.cs.outline(source, c.w930))
        left = c.scale * (a[0] + a[2]) / 2 + c.dx400
        right = c.scale * (b[0] + b[2]) / 2 + c.dx930
        for t in (0, .25, .5, .75, PJ_PEAK, 1):
            expected = left + (right - left) * min(t / PJ_PEAK, 1)
            assert c_punct.target_center(ctx, cp, t) == pytest.approx(expected, abs=1e-9)
