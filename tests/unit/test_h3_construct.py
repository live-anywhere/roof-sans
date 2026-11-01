import pytest
from fontTools.varLib.models import supportScalar

from roofsans.assemble import planned_cmap
from roofsans.axis import COMPOSITE_LOCS
from roofsans.context import make_context
from roofsans.rules.h3_construct import contribute, fraction_offsets, fraction_parts, sequence_parts
from roofsans.rules.h6_copy import copy_closure
from roofsans.selection import Rule


@pytest.fixture(scope="module")
def ctx(inputs):
    """A context with the planned cmap, as the build has it before the rules run."""
    c = make_context(inputs)
    copy_closure(c)
    c.cmap = planned_cmap(c)
    return c


def wanted_component_offsets(font, name, t):
    """(component, x) of Wanted Sans composite ``name`` at Roof normalized ``t``."""
    glyph = font["glyf"][name]
    xs = [float(c.x) for c in glyph.components]
    for tv in font["gvar"].variations.get(name, []):
        s = supportScalar({"wght": t}, tv.axes)
        for i, d in enumerate(tv.coordinates[: len(xs)]):
            if d is not None:
                xs[i] += d[0] * s
    return [(c.glyphName, x) for c, x in zip(glyph.components, xs)]


def test_fraction_rule_reproduces_wanted_onehalf(ctx):
    for t in COMPOSITE_LOCS:
        parts = fraction_offsets(ctx, ("one.numr", "fraction", "two.dnom"), t)
        assert parts == [(n, x, 0) for n, x in wanted_component_offsets(ctx.wanted, "onehalf", t)]


def test_sequence_unit_square_uses_wanted_k_g(ctx):
    assert sequence_parts(ctx, ord("㎏")) == ["k", "g"]
    # Ruling R15: Pretendard builds ㎕ from the micro sign, which Wanted Sans maps.
    assert sequence_parts(ctx, ord("㎕")) == ["uni00B5", "l"]
    assert sequence_parts(ctx, ord("Ⅳ")) == ["I", "V"]


def test_sequence_parts_follow_decomposition(ctx):
    assert sequence_parts(ctx, ord("ǅ")) == ["D", "zcaron"]
    assert sequence_parts(ctx, ord("℻")) == ["F", "A", "X"]
    assert sequence_parts(ctx, ord("№")) == ["N", "ordmasculine"]
    # Wanted Sans lacks Ω, so the component is the Roof cmap glyph (H4).
    assert sequence_parts(ctx, ord("㏀")) == ["k", "uni03A9"]


def test_fraction_parts(ctx):
    assert fraction_parts(ctx, ord("℀")) == ["a.numr", "fraction", "c.dnom"]
    assert fraction_parts(ctx, ord("⅚")) == ["five.numr", "fraction", "six.dnom"]
    assert fraction_parts(ctx, ord("⅟")) == ["one.numr", "fraction"]


def test_no_sequence_source_has_component_transform(ctx):
    # Ruling R5: there is no 2×2 transform to keep, so Part stays (name, dx, dy).
    glyf = ctx.pretendard["glyf"]
    pcmap = ctx.pretendard.getBestCmap()
    for cp in ctx.selection.codepoints(Rule.H3_SEQUENCE):
        glyph = glyf[pcmap[cp]]
        if glyph.isComposite():
            assert not any(hasattr(c, "transform") for c in glyph.components), hex(cp)


def test_sequence_source_transform_fails_loudly(ctx, monkeypatch):
    glyph = ctx.pretendard["glyf"][ctx.pretendard.getBestCmap()[ord("㎏")]]
    monkeypatch.setattr(glyph.components[1], "transform", ((-1, 0), (0, 1)), raising=False)
    with pytest.raises(ValueError, match="transform"):
        sequence_parts(ctx, ord("㎏"))


def test_contribute_places_parts_and_skips_missing(ctx, capsys):
    glyphs = {g.name: g for g in contribute(ctx)}
    # Nothing contributed the H4 Ω yet, so ㏀ and ㏁ are skipped (ruling R11).
    assert ctx.cmap[0x33C0] not in glyphs and ctx.cmap[0x33C1] not in glyphs
    assert "U+33C0" in capsys.readouterr().err
    assert len(glyphs) == 127 + 7 - 2
    g = glyphs[ctx.cmap[ord("㎏")]]
    assert g.rule is Rule.H3_SEQUENCE and g.unicodes == (ord("㎏"),)
    assert [c.glyphName for c in g.glyph.components] == ["k", "g"]
    assert [(c.x, c.y) for c in g.glyph.components] == [(0, 0), (round(ctx.advance("k", 0.0)), 0)]
    assert g.advance == round(ctx.advance("k", 0.0) + ctx.advance("g", 0.0))
    half = glyphs[ctx.cmap[ord("⅟")]]
    assert half.rule is Rule.H3_FRACTION
    assert [c.glyphName for c in half.glyph.components] == ["one.numr", "fraction"]
