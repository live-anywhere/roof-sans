import pytest

from roofsans.assemble import planned_cmap
from roofsans.axis import H4_LOCS, roof_wght
from roofsans.context import make_context
from roofsans.measure import vertical_runs
from roofsans.newglyph import newglyph_outline
from roofsans.rules.h5_symbols import CLAMPED_STROKES, SAMPLE_RANGE, category_transform, contribute
from roofsans.rules.h6_copy import copy_closure
from roofsans.selection import SymbolCategory


@pytest.fixture(scope="module")
def ctx(inputs):
    """A context with the planned cmap, as the build has it before the rules run."""
    c = make_context(inputs)
    copy_closure(c)
    c.cmap = planned_cmap(c)
    return c


def shaft(o):
    """The vertical run at 25% of the ink width: the shaft of `→`, the bar of `+`."""
    x0, _, x1, _ = o.bounds()
    (a, b), = vertical_runs(o, x0 + 0.25 * (x1 - x0))
    return b - a


def test_arrow_transform_lands_on_725(ctx):
    for t in H4_LOCS:
        tr = category_transform(ctx, SymbolCategory.ARROW, t)
        assert 634 * tr.scale + tr.shift_y == pytest.approx(725, abs=2)


def test_math_axis(ctx):
    tr = category_transform(ctx, SymbolCategory.MATH, 0.0)
    assert 566 * tr.scale + tr.shift_y == pytest.approx(540, abs=2)


@pytest.mark.parametrize(("cat", "name"), [(SymbolCategory.ARROW, "arrowright"), (SymbolCategory.MATH, "plus")])
def test_scaled_stroke_matches_wanted(ctx, cat, name):
    # The compensating weight keeps the reference's shaft (bar) as thick as Wanted Sans's.
    for t in H4_LOCS:
        tr = category_transform(ctx, cat, t)
        got = shaft(ctx.ps.outline(name, tr.sample_wght)) * tr.scale
        want = shaft(ctx.ws.outline(name, roof_wght(t)))
        if (cat, t) in CLAMPED_STROKES:
            # No weight reaches Wanted's stroke; the closest one is the sampler's maximum (R28).
            assert tr.sample_wght == SAMPLE_RANGE[1]
            assert got < want
        else:
            assert got == pytest.approx(want, rel=0.01)


def test_identity_categories(ctx):
    tr = category_transform(ctx, SymbolCategory.CURRENCY, 1.0)
    assert (tr.scale, tr.shift_y, tr.advance_ratio) == (1.0, 0.0, 1.0)


def test_symbols_keep_their_place_in_the_advance(ctx):
    # x is scaled about the origin, then re-centered on Pretendard's ink-center/advance ratio.
    glyphs = {g.unicodes[0]: g for g in contribute(ctx)}
    g = glyphs[ord("⇒")]
    for t in H4_LOCS:
        tr = category_transform(ctx, SymbolCategory.ARROW, t)
        src = ctx.ps.outline("arrowdblright", tr.sample_wght)
        out = newglyph_outline(g, t, ctx.outline)
        assert out.advance() == pytest.approx(src.advance() * tr.advance_ratio, abs=1)
        sx0, _, sx1, _ = src.bounds()
        x0, y0, x1, y1 = out.bounds()
        assert (x0 + x1) / 2 / out.advance() == pytest.approx((sx0 + sx1) / 2 / src.advance(), abs=1e-3)
        assert x1 - x0 == pytest.approx((sx1 - sx0) * tr.scale, abs=1)
