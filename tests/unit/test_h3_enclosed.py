import pytest
from fontTools.misc.roundTools import otRound

from roofsans.assemble import planned_cmap
from roofsans.axis import W_MID
from roofsans.context import make_context
from roofsans.newglyph import newglyph_outline
from roofsans.outline import Outline
from roofsans.rules.h3_enclosed import (
    DISC,
    ENCLOSED,
    RING,
    SUPSUB,
    contribute,
    figure_outline,
    figure_stem,
    pair_limit,
    reach,
    sign_stroke,
)
from roofsans.rules.h6_copy import copy_closure


@pytest.fixture(scope="module")
def ctx(inputs):
    """A context with the planned cmap, as the build has it before the rules run."""
    c = make_context(inputs)
    copy_closure(c)
    c.cmap = planned_cmap(c)
    return c


@pytest.fixture(scope="module")
def glyphs(ctx):
    """The contributed glyphs, also added to ``ctx`` so composites resolve their components."""
    out = {g.name: g for g in contribute(ctx)}
    ctx.contributed.update(out)
    return out


def rounded(contours):
    """Contours as an instance stores them. Wanted's own ①–⑨ differ by less than 0.5 at
    1000 (IUP-inferred deltas), so their rings agree only after rounding."""
    return [[(otRound(x), otRound(y)) for x, y in c] for c in contours]


def wanted_contours(ctx, u, t):
    return rounded(ctx.outline(ctx.wanted.getBestCmap()[u], t).contours())


def ring_contours(ctx, t):
    return rounded(ctx.outline(RING, t).contours())


def test_ring_is_shared_by_wanted_circled_digits(ctx, glyphs):
    for u in range(0x2460, 0x2469):
        for t in (0.0, 1.0):
            assert wanted_contours(ctx, u, t)[:2] == ring_contours(ctx, t)


def test_ring_takes_wanted_deltas_exactly(ctx, glyphs):
    # R18: no interpolation drift, even before rounding.
    for t in (0.0, 0.25, W_MID, 0.75, 1.0):
        assert ctx.outline(RING, t).contours() == ctx.outline("uni2460", t).contours()[:2]
        assert ctx.outline(RING, t).advance() == ctx.advance("uni2460", t)


def test_supsub_stroke_matches_superior_figures(ctx, glyphs):
    # R16, R18: each sign keeps Wanted Sans's own sign-to-figure stroke ratio.
    for cp, (source, _) in SUPSUB.items():
        g = glyphs[ctx.cmap[cp]]
        for t in (0.0, W_MID, 1.0):
            o = newglyph_outline(g, t, ctx.outline)
            got = sign_stroke(o, source) / figure_stem(ctx.outline("one.dnom", t))
            want = sign_stroke(ctx.outline(source, t), source) / figure_stem(ctx.outline("one", t))
            assert got == pytest.approx(want, rel=0.02), (source, t)


def test_enclosed_glyphs_cover_the_rule(ctx, glyphs):
    names = {ctx.cmap[cp] for cp in (*range(0x2469, 0x2474), *range(0x24EB, 0x24F5), 0x277F)}
    assert len(names) == 22 and names <= set(glyphs)
    assert ctx.cmap[0x2789] == ctx.cmap[0x2469]
    # R22, R27: every number takes a helper of Wanted's own enclosed figures, fitted.
    assert [c.glyphName for c in glyphs[ctx.cmap[0x2469]].glyph.components] == [RING, "roof.pair.10"]
    assert [c.glyphName for c in glyphs[ctx.cmap[0x24F4]].glyph.components] == [DISC, "roof.knockpair.20"]


def test_pairs_fill_wanted_clearance(ctx, glyphs):
    # R22: each pair reaches as far from the center as Wanted's tightest `①`–`⑨` figure allows.
    for cp, (_, helper) in ENCLOSED.items():
        for t in (0.0, W_MID, 1.0):
            o, ring = ctx.outline(ctx.cmap[cp], t), ctx.outline(helper, t)
            x0, y0, x1, y1 = ring.bounds()
            n = len(ring.points)
            pair = Outline(o.coords[n:], [e - n for e in o.end_pts[len(ring.end_pts) :]], o.flags[n:])
            got = reach(pair, (x0 + x1) / 2, (y0 + y1) / 2)
            # The pair helper's masters are rounded and IUP-optimized, hence R22's 2-unit slack.
            assert got == pytest.approx(pair_limit(ctx, helper, ring, t), abs=2), (hex(cp), t)


def test_fitted_pair_stems_scale_with_the_pair(ctx, glyphs):
    # R27: figures are only scaled, so each stem is s times its enclosed `1`'s stem.
    for name, helper in (("roof.pair.11", RING), ("roof.knockpair.11", DISC)):
        for t in (0.0, W_MID, 1.0):
            pair, source = ctx.outline(name, t), figure_outline(ctx, helper, 1, t)
            s = (pair.bounds()[3] - pair.bounds()[1]) / (source.bounds()[3] - source.bounds()[1])
            assert s < 1
            assert figure_stem(pair) == pytest.approx(s * figure_stem(source), abs=1)


def test_enclosed_pair_is_centered_in_ring(ctx, glyphs):
    for cp in (0x2469, 0x2473, 0x24EB, 0x277F):
        g = glyphs[ctx.cmap[cp]]
        for t in (0.0, W_MID, 1.0):
            o = ctx.outline(g.name, t)
            helper = ctx.outline(g.glyph.components[0].glyphName, t)
            n = len(helper.end_pts)
            pair = [p for c in o.contours()[n:] for p in c]
            hx0, hy0, hx1, hy1 = helper.bounds()
            px = [p[0] for p in pair]
            py = [p[1] for p in pair]
            assert (min(px) + max(px)) / 2 == pytest.approx((hx0 + hx1) / 2, abs=1)
            assert (min(py) + max(py)) / 2 == pytest.approx((hy0 + hy1) / 2, abs=1)
            assert o.advance() == pytest.approx(ctx.advance("uni2460", t), abs=1)


def test_supsub_ink_is_centered_and_shifted(ctx, glyphs):
    # k = height(zero.dnom) / height(zero) = 752 / 1504 in Wanted Sans.
    for cp, dy in ((0x207B, 936), (0x208B, -208)):
        g = glyphs[ctx.cmap[cp]]
        assert g.source == "minus"
        for t in (0.0, W_MID, 1.0):
            o = newglyph_outline(g, t, ctx.outline)
            x0, y0, x1, y1 = o.bounds()
            assert o.advance() == pytest.approx(0.5 * ctx.advance("minus", t), abs=1)
            assert (x0 + x1) / 2 == pytest.approx(o.advance() / 2, abs=1)
            # R23: the ink center stays where the scaled source's center was, plus dy.
            _, sy0, _, sy1 = ctx.outline("minus", t).bounds()
            assert (y0 + y1) / 2 == pytest.approx(0.5 * (sy0 + sy1) / 2 + dy, abs=1)
