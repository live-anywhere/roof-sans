import unicodedata

import pytest
import uharfbuzz as hb
from fontTools.pens.boundsPen import BoundsPen
from fontTools.varLib.models import supportScalar
from fontTools.varLib.varStore import VarStoreInstancer

from helpers import apply
from roofsans.assemble import planned_cmap
from roofsans.axis import COMPOSITE_LOCS, H4_LOCS, roof_norm
from roofsans.context import make_context
from roofsans.rules import h4_letters
from roofsans.rules.h2_compose import base_anchor, components, contribute, mark_anchor, placed_parts
from roofsans.rules.h6_copy import copy_closure
from roofsans.selection import Rule


@pytest.fixture(scope="module")
def ctx(inputs):
    """A context with the planned cmap and the H4 glyphs, as h2_compose sees it in the build."""
    c = make_context(inputs)
    copy_closure(c)
    c.cmap = planned_cmap(c)
    c.contributed.update((g.name, g) for g in h4_letters.contribute(c))
    return c


@pytest.fixture(scope="module")
def glyphs(ctx):
    return {g.name: g for g in contribute(ctx)}


def _codepoint(font, name):
    return min(cp for cp, g in font.getBestCmap().items() if g == name)


def wanted_component_offsets(font, name, t):
    """(dx, dy) of each component of Wanted Sans composite ``name`` at Roof normalized ``t``."""
    glyph = font["glyf"][name]
    out = [[float(c.x), float(c.y)] for c in glyph.components]
    for tv in font["gvar"].variations.get(name, []):
        s = supportScalar({"wght": t}, tv.axes)
        for i, d in enumerate(tv.coordinates[: len(out)]):
            if d is not None:
                out[i][0] += d[0] * s
                out[i][1] += d[1] * s
    return [tuple(p) for p in out]


def rebuilt_offsets(ctx, name, t):
    """(dx, dy) of each part the H2 rule places for Wanted Sans glyph ``name``'s code point."""
    return [(dx, dy) for _, dx, dy in placed_parts(ctx, _codepoint(ctx.wanted, name), t)]


def component_names(g):
    return [c.glyphName for c in g.glyph.components]


def stored_coords(g, t):
    """Component offsets and phantom points of contributed glyph ``g`` at ``t``, from its tuples."""
    coords = [(c.x, c.y) for c in g.glyph.components] + [(0, 0), (g.advance, 0), (0, 0), (0, 0)]
    return apply(coords, g.variations, t)


def component_offsets(g, t):
    return stored_coords(g, t)[: len(g.glyph.components)]


def horn_ink_xmin(ctx, glyphs, base, t):
    glyph = glyphs[ctx.cmap[{"o": 0x01A1, "u": 0x01B0, "O": 0x01A0, "U": 0x01AF}[base]]]
    names = component_names(glyph)
    i = names.index(ctx.cmap[0x031B])
    return component_offsets(glyph, t)[i][0] + ctx.outline(names[i], t).bounds()[0]


def h2_codepoints(ctx):
    return ctx.selection.codepoints(Rule.H2_COMPOSE)


def shape(path, text):
    font = hb.Font(hb.Face(hb.Blob.from_file_path(str(path))))
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf, {})
    return [font.glyph_to_string(i.codepoint) for i in buf.glyph_infos]


def mark_center_x(static, glyph, mark, w):
    """Ink center x of component ``mark`` inside composite ``glyph`` of Roof at ``w``."""
    font = static("roof", w)
    comp = next(c for c in font["glyf"][glyph].components if c.glyphName == mark)
    pen = BoundsPen(font.getGlyphSet())
    font.getGlyphSet()[mark].draw(pen)
    x_min, _, x_max, _ = pen.bounds
    return comp.x + (x_min + x_max) / 2


def wanted_composites(ctx):
    """Wanted Sans's composite letters whose components are the parts the H2 rule would use."""
    out = []
    for cp, name in sorted(ctx.wanted.getBestCmap().items()):
        glyph = ctx.wanted["glyf"][name]
        chars = unicodedata.normalize("NFD", chr(cp))
        if not glyph.isComposite() or len(chars) < 2 or not all(ord(c) in ctx.cmap for c in chars):
            continue
        if components(ctx, cp) == component_names_of(glyph):
            out.append(name)
    return out


def component_names_of(glyph):
    return [c.glyphName for c in glyph.components]


def test_rule_reproduces_wanted_composites(ctx):
    # Ruling R35: anchors at each location alone place the marks where Wanted's composites do.
    names = wanted_composites(ctx)
    assert {"ecircumflex", "abreve", "Ecircumflex", "uni1EC7", "uni1EAD"} <= set(names)
    assert len(names) == 252
    for name in names:
        for t in COMPOSITE_LOCS:
            rebuilt = [v for p in rebuilt_offsets(ctx, name, t) for v in p]
            want = [v for p in wanted_component_offsets(ctx.wanted, name, t) for v in p]
            assert rebuilt == pytest.approx(want, abs=2), (name, t)


def wanted_gpos_offset(ctx, base, mark, t):
    """Wanted Sans's mark-to-base offset of ``mark`` on ``base`` at ``t``, from its GPOS and the
    device deltas of its GDEF store (fontTools's own instancer, independent of the rule)."""
    gpos = ctx.wanted["GPOS"].table
    instancer = VarStoreInstancer(ctx.wanted["GDEF"].table.VarStore, ctx.wanted["fvar"].axes, {"wght": t})

    def delta(dev):
        return instancer[(dev.StartSize << 16) + dev.EndSize] if dev is not None else 0

    def at(a):
        if a.Format != 3:
            return a.XCoordinate, a.YCoordinate
        return a.XCoordinate + delta(a.XDeviceTable), a.YCoordinate + delta(a.YDeviceTable)

    for index in next(f.Feature.LookupListIndex for f in gpos.FeatureList.FeatureRecord if f.FeatureTag == "mark"):
        for st in gpos.LookupList.Lookup[index].SubTable:
            if not hasattr(st, "BaseCoverage"):
                continue
            if base not in st.BaseCoverage.glyphs or mark not in st.MarkCoverage.glyphs:
                continue
            record = st.MarkArray.MarkRecord[st.MarkCoverage.glyphs.index(mark)]
            anchor = st.BaseArray.BaseRecord[st.BaseCoverage.glyphs.index(base)].BaseAnchor[record.Class]
            if anchor is not None:
                (bx, by), (mx, my) = at(anchor), at(record.MarkAnchor)
                return bx - mx, by - my
    return None


def test_wanted_marks_follow_wanted_gpos(ctx):
    # Ruling R35 (final review I1): a Wanted mark on a Wanted letter lands where Wanted's own
    # GPOS puts it at every location, also for letters without a same-base Wanted composite.
    checked = 0
    for cp in h2_codepoints(ctx):
        base, *marks = components(ctx, cp)
        seen = set()
        for mark in marks:
            cls = mark_anchor(ctx, mark)[0]
            if cls in seen:  # stacked: centered on the lower mark (decision 13)
                continue
            seen.add(cls)
            for t in (0.0, 0.5, 1.0):
                want = wanted_gpos_offset(ctx, base, mark, t)
                if want is None:
                    continue
                _, dx, dy = next(p for p in placed_parts(ctx, cp, t) if p[0] == mark)
                assert (dx, dy) == pytest.approx(want, abs=1), (chr(cp), mark, t)
                checked += 1
    assert checked > 3 * 150


def test_vietnamese_uses_wanted_marks(glyphs):
    assert component_names(glyphs["uni1EA7"]) == ["a", "uni0302", "gravecomb"]
    assert component_names(glyphs["uni1EF1"]) == ["u", "uni031B", "dotbelowcomb"]


def test_contributes_every_h2_letter(ctx, glyphs):
    assert sorted(ctx.cmap[cp] for cp in h2_codepoints(ctx)) == sorted(glyphs)
    assert len(glyphs) == 228


def test_dotless_base_under_top_mark(glyphs):
    assert component_names(glyphs["uni020B"])[0] == "dotlessi"  # ȋ: i + inverted breve
    assert component_names(glyphs["uni01F0"])[0] == "uni0237"  # ǰ: j + caron


def test_horn_touches_base(ctx, glyphs):
    for base in ("o", "u", "O", "U"):
        for t in COMPOSITE_LOCS:
            assert horn_ink_xmin(ctx, glyphs, base, t) <= ctx.outline(base, t).bounds()[2] + 2


def test_horn_stays_within_advance(ctx, glyphs):
    # Ruling R30: the horn ends no further past the advance than Pretendard's own horn does.
    letters = {"o": "ohorn", "u": "uhorn", "O": "Ohorn", "U": "Uhorn"}
    p = h4_letters.params(ctx)
    horned = [g for g in glyphs.values() if ctx.cmap[0x031B] in component_names(g)]
    assert len(horned) == 24
    for g in horned:
        names = component_names(g)
        letter = letters[names[0]]
        for t in COMPOSITE_LOCS:
            i = max(j for j, loc in enumerate(H4_LOCS) if loc <= t and j < len(H4_LOCS) - 1)
            a, b = H4_LOCS[i], H4_LOCS[i + 1]
            w = p[a].w_prime + (t - a) * (p[b].w_prime - p[a].w_prime) / (b - a)
            overhang = ctx.ps.outline(letter, w).bounds()[2] - ctx.ps.advance(letter, w)
            coords = stored_coords(g, t)
            horn = names.index(ctx.cmap[0x031B])
            horn_right = coords[horn][0] + ctx.outline(names[horn], t).bounds()[2]
            assert horn_right <= coords[-3][0] - coords[-4][0] + overhang + 1, (g.name, t)


def test_stacked_mark_gap_matches_ecircumflex(ctx, glyphs):
    # ầ: grave sits above the circumflex with the gap between e and its circumflex in ê.
    for t in COMPOSITE_LOCS:
        e_top = ctx.outline("e", t).bounds()[3]
        dy = wanted_component_offsets(ctx.wanted, "ecircumflex", t)[1][1]
        gap = dy + ctx.outline("uni0302", t).bounds()[1] - e_top
        _, (_, c_dy), (_, g_dy) = component_offsets(glyphs["uni1EA7"], t)
        circumflex_top = c_dy + ctx.outline("uni0302", t).bounds()[3]
        grave_bottom = g_dy + ctx.outline("gravecomb", t).bounds()[1]
        assert grave_bottom - circumflex_top == pytest.approx(gap, abs=1)


def test_served_mark_anchors_clear_o(ctx):
    # Ruling R31: a served anchor puts a mark above o's top, or below o's bottom.
    o = ctx.outline("o", 0.0).bounds()
    served = []
    for cp in ctx.selection.codepoints(Rule.H4_LETTER):
        if unicodedata.category(chr(cp)) != "Mn":
            continue
        try:
            cls, mx, my = mark_anchor(ctx, ctx.cmap[cp])
        except ValueError:
            continue
        if cls == "horn":
            continue
        dy = base_anchor(ctx, "o", cls)[1] - my
        ink = ctx.outline(ctx.cmap[cp], 0.0).bounds()
        served.append(ctx.cmap[cp])
        if cls == "top":
            assert ink[1] + dy > o[3], ctx.cmap[cp]
        else:
            assert ink[3] + dy < o[1], ctx.cmap[cp]
    assert {"uni0309", "uni0311"} <= set(served)


@pytest.mark.acceptance
def test_long_s_dot_clears_long_s(static):
    # Ruling R31: ẛ's dot lands on Pretendard's harmonized dot at each master, so it stays
    # above the long s at every weight.
    for w in (400, 550, 700, 850, 1000):
        font = static("roof", w)
        glyph_set = font.getGlyphSet()
        ink = {}
        for c in font["glyf"]["uni1E9B"].components:
            pen = BoundsPen(glyph_set)
            glyph_set[c.glyphName].draw(pen)
            x_min, y_min, x_max, y_max = pen.bounds
            ink[c.glyphName] = (x_min + c.x, y_min + c.y, x_max + c.x, y_max + c.y)
        assert ink["uni0307"][1] > ink["uni017F"][3], w


@pytest.mark.acceptance
def test_nfd_latin_composes(ctx, roof_path):  # Review Focus 1
    cmap = ctx.cmap
    wrong = [
        (f"U+{cp:04X}", got)
        for cp in h2_codepoints(ctx)
        if (got := shape(roof_path, unicodedata.normalize("NFD", chr(cp)))) != [cmap[cp]]
    ]
    assert not wrong


# Final review I1: letters whose Wanted mark drifted from Wanted's own GPOS placement, and
# the hook-above letters, whose H4 mark drifted from Pretendard's placement.
I1_LETTERS = "ẋẍṽṿẊẌẉṼṾṔṖḂḃḋṕṗḟǢǼ"
HOOK_LETTERS = "ảẻỉỏủỷẢẺỈỎỦỶởửỞỬ"
# H2 keeps Wanted's base anchors (R25). Wanted's own a, E, R, r anchors (and Pretendard's on ư)
# sit differently from the other font's relative to the ink, so these letters differ from
# Pretendard's precomposed letter by up to 18 units; the others stay within 4.
ANCHOR_DESIGN_DIFFERS = "ảȃȓȒȆẺử"


def h4_mark_tolerance(ch):
    return 18 if ch in ANCHOR_DESIGN_DIFFERS else 4


def w_prime(ctx, t):
    """The Pretendard weight the H4 glyphs are drawn from at Roof normalized ``t``."""
    p = h4_letters.params(ctx)
    i = max(j for j, loc in enumerate(H4_LOCS[:-1]) if loc <= t)
    a, b = H4_LOCS[i], H4_LOCS[i + 1]
    return p[a].w_prime + (t - a) * (p[b].w_prime - p[a].w_prime) / (b - a)


def wanted_shaped_offset(path, w, text):
    """Wanted Sans's GPOS offset of the second glyph of ``text`` (base + one mark) at ``w``."""
    font = hb.Font(hb.Face(hb.Blob.from_file_path(str(path))))
    font.set_variations({"wght": w})
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf, {})
    first, second = buf.glyph_positions
    return first.x_advance + second.x_offset, second.y_offset


def roof_mark_offset(static, glyph, mark, w):
    comp = next(c for c in static("roof", w)["glyf"][glyph].components if c.glyphName == mark)
    return comp.x, comp.y


def ink_center_x(contours):
    xs = [x for c in contours for x, _ in c]
    return (min(xs) + max(xs)) / 2


def pretendard_hook_offset(ctx, ch, w):
    """Hook ink center x minus base ink center x in Pretendard's precomposed ``ch`` at ``w``."""
    pcmap = ctx.pretendard.getBestCmap()
    chars = unicodedata.normalize("NFD", ch)
    without = unicodedata.normalize("NFC", chars.replace("\u0309", ""))
    own = {tuple(map(tuple, c)) for c in ctx.ps.outline(pcmap[ord(without)], w).contours()}
    hook = [c for c in ctx.ps.outline(pcmap[ord(ch)], w).contours() if tuple(map(tuple, c)) not in own]
    return ink_center_x(hook) - ink_center_x(ctx.ps.outline(pcmap[ord(chars[0])], w).contours())


def roof_hook_offset(static, ctx, ch, w):
    font = static("roof", w)
    glyph = font["glyf"][ctx.cmap[ord(ch)]]
    centers = {}
    for c in glyph.components:
        pen = BoundsPen(font.getGlyphSet())
        font.getGlyphSet()[c.glyphName].draw(pen)
        centers[c.glyphName] = c.x + (pen.bounds[0] + pen.bounds[2]) / 2
    return centers["uni0309"] - centers[glyph.components[0].glyphName]


@pytest.mark.acceptance
def test_mark_alignment_between_masters(ctx, inputs, static):  # Review Focus 5
    for w in (550, 850):
        assert mark_center_x(static, "uni1EA7", "uni0302", w) == pytest.approx(
            mark_center_x(static, "acircumflex", "uni0302", w), abs=1)
        for ch in I1_LETTERS:
            base, mark = components(ctx, ord(ch))
            want = wanted_shaped_offset(inputs.wanted, w, unicodedata.normalize("NFD", ch))
            assert roof_mark_offset(static, ctx.cmap[ord(ch)], mark, w) == pytest.approx(want, abs=2), (ch, w)
        for ch in HOOK_LETTERS:
            want = pretendard_hook_offset(ctx, ch, w_prime(ctx, roof_norm(w)))
            assert roof_hook_offset(static, ctx, ch, w) == pytest.approx(want, abs=h4_mark_tolerance(ch)), (ch, w)
