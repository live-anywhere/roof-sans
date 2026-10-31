"""Acceptance 5, H2/H3 part for H3: sequences and fractions reference Wanted Sans glyphs."""

import unicodedata

import pytest

from roofsans.selection import Rule

pytestmark = pytest.mark.acceptance

UNIT_SQUARES = (0x3300, 0x33FF)


def source_codepoints(pretendard, cp):
    """The code points a sequence is built from: Pretendard's square, or the decomposition."""
    if cp == 0x2116:
        return [ord("N"), ord("º")]
    if UNIT_SQUARES[0] <= cp <= UNIT_SQUARES[1]:
        reverse = {}
        for c, g in sorted(pretendard.getBestCmap().items()):
            reverse.setdefault(g, c)
        glyph = pretendard["glyf"][pretendard.getBestCmap()[cp]]
        return [reverse[c.glyphName] for c in glyph.components]
    return [int(h, 16) for h in unicodedata.decomposition(chr(cp)).split()[1:]]


def test_a05_h3_components(ctx, wanted, roof):
    wcmap, rcmap = wanted.getBestCmap(), roof.getBestCmap()
    wanted_names = set(wanted.getGlyphOrder())
    glyf = roof["glyf"]
    names = set(roof.getGlyphOrder())
    bad = []
    for cp in ctx.selection.codepoints(Rule.H3_SEQUENCE) + ctx.selection.codepoints(Rule.H3_FRACTION):
        if cp not in rcmap:
            bad.append((hex(cp), "missing"))
            continue
        glyph = glyf[rcmap[cp]]
        if not glyph.isComposite():
            bad.append((hex(cp), "not a composite"))
            continue
        components = [c.glyphName for c in glyph.components]
        if absent := [c for c in components if c not in names]:
            bad.append((hex(cp), "absent", absent))
        if ctx.selection.rules[cp] is Rule.H3_FRACTION:
            # numr/dnom figures and letters have no code point; all are Wanted Sans glyphs.
            first, _, *last = source_codepoints(ctx.pretendard, cp)
            expected = [f"{wcmap[first]}.numr", "fraction", *(f"{wcmap[c]}.dnom" for c in last)]
            if components != expected or not set(components) <= wanted_names:
                bad.append((hex(cp), components, expected))
            continue
        expected = [wcmap.get(c) or rcmap.get(c) for c in source_codepoints(ctx.pretendard, cp)]
        if components != expected:
            bad.append((hex(cp), components, expected))
    assert not bad, f"{len(bad)} H3 glyphs differ: {bad[:10]}"
