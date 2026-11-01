"""Side bearings of the rebuilt glyphs: no new overhang past the advance (final review M4)."""

import unicodedata

import pytest
from fontTools.pens.boundsPen import BoundsPen

from roofsans.selection import Rule

pytestmark = pytest.mark.acceptance

# Glyphs Roof Sans builds itself; Wanted Sans glyphs and Pretendard copies keep their source's.
REBUILT = {rule for rule in Rule if rule not in (Rule.WANTED, Rule.H6_COPY, Rule.EXCLUDED_PUA)}
WORSE_BY = 40
ALLOWED = {
    # Ruling R37: ⅟'s slash reaches where ½ puts its .dnom, as in Pretendard JP's own ⅟.
    0x215F: "fraction numerator one: overhang kept for the denominator",
    # Wanted's own GPOS places the ogonek on o at the right edge (lookup 9); owner's visual call.
    0x01EB: "ǫ ogonek", 0x01ED: "ǭ ogonek", 0x01EA: "Ǫ ogonek", 0x01EC: "Ǭ ogonek",
    # Wanted marks wider than a narrow base, placed exactly as Wanted's own GPOS places the
    # decomposed sequence (test_decomposed_marks); Pretendard's narrower marks overhang less.
    0x0204: "Ȅ double grave", 0x0205: "ȅ double grave", 0x020D: "ȍ double grave",
    0x0208: "Ȉ double grave", 0x0209: "ȉ double grave", 0x0211: "ȑ double grave",
    0x1E2C: "Ḭ tilde below", 0x1E2D: "ḭ tilde below", 0x1E2E: "Ḯ diaeresis acute", 0x1E2F: "ḯ diaeresis acute",
    # R3 centers Wanted's W and % in the fullwidth cell unscaled; Pretendard's Ｗ overhangs too
    # (−94 at 930). Reported for a decision outside this test.
    0xFF37: "fullwidth W", 0xFF05: "fullwidth percent",
    # Below 400 Wanted's marks narrow more slowly than its stems, so on narrow bases they reach
    # past the advance, as `Ȉ ȉ` do at every weight; the placement is Wanted's own GPOS
    # (test_decomposed_marks). `Ĭ` −40 a side at 100 (Pretendard 51) and −42/−44 at 250 (3/1);
    # at 100 only: `ĭ` −50 a side (Pretendard 23), `ǰ` left −120 (−71), `ḧ` left −65 (−6).
    0x012C: "Ĭ breve (light weights)", 0x012D: "ĭ breve (light weights)",
    0x01F0: "ǰ caron (light weights)", 0x1E27: "ḧ diaeresis (light weights)",
}


def bearings(font, glyph_set, name):
    pen = BoundsPen(glyph_set)
    glyph_set[name].draw(pen)
    if pen.bounds is None:
        return None
    return pen.bounds[0], font["hmtx"][name][0] - pen.bounds[2]


@pytest.mark.parametrize("wght", [100, 250, 400, 1000])
def test_a09_side_bearings(ctx, roof, static, wght):
    roof_static, pretendard = static("roof", wght), static("pretendard", min(wght, 930))
    rcmap, pcmap = roof.getBestCmap(), pretendard.getBestCmap()
    roof_set, pretendard_set = roof_static.getGlyphSet(), pretendard.getGlyphSet()
    flagged, checked = [], 0
    for cp, rule in sorted(ctx.selection.rules.items()):
        if rule not in REBUILT or cp not in rcmap or cp not in pcmap:
            continue
        if unicodedata.category(chr(cp)) in ("Mn", "Me", "Cf", "Zs"):
            continue
        ours = bearings(roof_static, roof_set, rcmap[cp])
        theirs = bearings(pretendard, pretendard_set, pcmap[cp])
        if ours is None or theirs is None:
            continue
        checked += 1
        for side, mine, source in zip(("left", "right"), ours, theirs):
            if mine < 0 and mine < source - WORSE_BY:
                flagged.append((cp, f"U+{cp:04X} {chr(cp)}", side, round(mine), round(source)))
    unexpected = [f[1:] for f in flagged if f[0] not in ALLOWED]
    print(f"\n{wght}: {checked} glyphs checked; allowed: {[f[1:] for f in flagged if f[0] in ALLOWED]}")
    assert checked > 1000
    assert not unexpected, " ".join(map(str, unexpected))
