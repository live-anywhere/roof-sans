"""Insert new glyphs into the Wanted Sans base and rebuild its cmap."""

from __future__ import annotations

from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable

from roofsans.newglyph import NewGlyph
from roofsans.rules.h6_copy import format14_sequences
from roofsans.selection import Rule, roof_glyph_name

# Wanted Sans maps ➀–➈ to ①–⑨'s glyphs; ➉ follows ⑩ the same way.
SHARED_GLYPH = {0x2789: 0x2469}

# (format, platformID, platEncID), in the spec's sort order.
_SUBTABLES = ((4, 0, 3), (12, 0, 4), (14, 0, 5), (4, 3, 1), (12, 3, 10))


def planned_cmap(ctx) -> dict[int, str]:
    """The Roof cmap: Wanted Sans's, then copies for H6, then a new name per other rule."""
    if not ctx.pj_names:
        raise ValueError("planned_cmap needs ctx.pj_names; run copy_closure first")
    cmap = dict(ctx.wanted.getBestCmap())
    pcmap = ctx.pretendard.getBestCmap()
    taken = set(ctx.wanted.getGlyphOrder()) | set(ctx.pj_names.values())
    for cp, rule in sorted(ctx.selection.rules.items()):
        if rule in (Rule.WANTED, Rule.EXCLUDED_PUA):
            continue
        if rule is Rule.H6_COPY:
            cmap[cp] = ctx.pj_names[pcmap[cp]]
        else:
            cmap[cp] = roof_glyph_name(cp, taken)
    for cp, target in SHARED_GLYPH.items():
        cmap[cp] = cmap[target]
    return cmap


def planned_uvs(ctx) -> dict[int, list[tuple[int, str | None]]]:
    """Pretendard JP's format-14 sequences, pointing at the copied glyphs."""
    return {
        vs: [(base, None if g is None else ctx.pj_names[g]) for base, g in seqs]
        for vs, seqs in format14_sequences(ctx.pretendard).items()
    }


def insert(font: TTFont, glyphs: list[NewGlyph]) -> None:
    """Append ``glyphs`` to the glyph order with their outlines, metrics, and tuples."""
    # These tables check the glyph count when decompiled, so load them first.
    glyf, gvar, hmtx = font["glyf"], font["gvar"].variations, font["hmtx"].metrics
    order = list(font.getGlyphOrder())
    existing = set(order)
    for g in glyphs:
        if g.name in existing:
            raise ValueError(f"glyph {g.name} already exists")
        existing.add(g.name)
    order.extend(g.name for g in glyphs)
    font.setGlyphOrder(order)
    glyf.setGlyphOrder(order)
    for g in glyphs:
        glyf.glyphs[g.name] = g.glyph
        gvar[g.name] = list(g.variations)
    # Bounds of a composite need its components in place, so they come last.
    for g in glyphs:
        g.glyph.recalcBounds(glyf)
        hmtx[g.name] = (g.advance, g.glyph.xMin if g.glyph.numberOfContours else 0)


def write_cmap(font: TTFont, cmap: dict[int, str], uvs: dict[int, list[tuple[int, str | None]]]) -> None:
    """Replace the cmap with formats 4 (3/1, 0/3), 12 (3/10, 0/4), and 14 (0/5)."""
    bmp = {cp: g for cp, g in cmap.items() if cp <= 0xFFFF}
    tables = []
    for fmt, platform, encoding in _SUBTABLES:
        table = CmapSubtable.newSubtable(fmt)
        table.platformID, table.platEncID = platform, encoding
        if fmt == 14:
            table.language = 0xFF
            table.cmap = {}
            table.uvsDict = {vs: sorted(seqs) for vs, seqs in uvs.items()}
        else:
            table.language = 0
            table.cmap = dict(sorted((bmp if fmt == 4 else cmap).items()))
        tables.append(table)
    font["cmap"].tables = tables
