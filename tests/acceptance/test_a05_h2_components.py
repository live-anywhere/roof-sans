"""Acceptance 5, H2/H3 part for H2: decomposable letters are composites of Wanted Sans parts."""

import unicodedata

import pytest

from roofsans.selection import Rule

pytestmark = pytest.mark.acceptance

# Under a mark above, i and j lose their dot (Wanted Sans builds í and ĵ the same way).
DOTLESS = {"i": "dotlessi", "j": "uni0237"}


def test_a05_h2_components(ctx, wanted, roof):
    wcmap, rcmap = wanted.getBestCmap(), roof.getBestCmap()
    glyf = roof["glyf"]
    bad = []
    for cp in ctx.selection.codepoints(Rule.H2_COMPOSE):
        if cp not in rcmap:
            bad.append((f"U+{cp:04X}", "missing"))
            continue
        glyph = glyf[rcmap[cp]]
        if not glyph.isComposite():
            bad.append((f"U+{cp:04X}", "not a composite"))
            continue
        chars = unicodedata.normalize("NFD", chr(cp))
        names = [c.glyphName for c in glyph.components]
        if len(names) != len(chars):
            bad.append((f"U+{cp:04X}", names))
            continue
        for i, (ch, name) in enumerate(zip(chars, names)):
            c = ord(ch)
            if c in wcmap:
                allowed = {wcmap[c]} | ({DOTLESS[ch]} if i == 0 and ch in DOTLESS else set())
            elif ctx.selection.rules[c] is Rule.H4_LETTER:
                # A mark (or, ruling R10, one of Ʒ ʒ ſ) Wanted Sans lacks: the H4 glyph.
                allowed = {rcmap[c]}
            else:
                allowed = set()
            if name not in allowed:
                bad.append((f"U+{cp:04X}", ch, name, sorted(allowed)))
    assert not bad, bad[:20]


def test_a05_h2_non_wanted_parts_are_h4(ctx, wanted, roof):
    wanted_glyphs = set(wanted.getGlyphOrder())
    h4 = {roof.getBestCmap()[cp] for cp in ctx.selection.codepoints(Rule.H4_LETTER)}
    glyf = roof["glyf"]
    used = {
        c.glyphName
        for cp in ctx.selection.codepoints(Rule.H2_COMPOSE)
        for c in glyf[roof.getBestCmap()[cp]].components
    }
    assert sorted(used - wanted_glyphs - h4) == []
    assert {"uni0309", "uni031B"} <= used - wanted_glyphs
