"""Prepare the Wanted Sans base, insert new glyphs into it, and rebuild its cmap."""

from __future__ import annotations

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable

from roofsans.newglyph import NewGlyph
from roofsans.rules.h6_copy import format14_sequences
from roofsans.selection import WANTED_LOGO, Rule, roof_glyph_name

# Wanted Sans maps ➀–➈ to ①–⑨'s glyphs; ➉ follows ⑩ the same way.
SHARED_GLYPH = {0x2789: 0x2469}

# (format, platformID, platEncID), in the spec's sort order.
_SUBTABLES = ((4, 0, 3), (12, 0, 4), (14, 0, 5), (4, 3, 1), (12, 3, 10))

# Wanted Sans's `liga` holds only the logo: `wanted_logo` → U+F0000, then " × " or " | "
# after the logo → the U+F0003 divider. No other feature reaches the logo glyphs.
LOGO_FEATURE = "liga"


def _keep_all_options(features: set[str]) -> subset.Options:
    """Subsetter options that keep every table, name, glyph name, and hint, and ``features``."""
    options = subset.Options()
    options.layout_features = sorted(features)
    options.layout_scripts = ["*"]
    options.name_IDs = ["*"]
    options.name_languages = ["*"]
    options.name_legacy = True
    options.glyph_names = True
    options.legacy_cmap = True
    options.symbol_cmap = True
    options.notdef_outline = True
    options.prune_unicode_ranges = False
    options.prune_codepage_ranges = False
    options.drop_tables = []
    options.passthrough_tables = True
    return options


def drop_wanted_logo(font: TTFont) -> None:
    """Remove Wanted Sans's logo glyphs and the `liga` feature that forms them from ``font``.

    The logo is Wanted Lab's trademark; the OFL licenses the font, not the mark. Every other
    glyph, lookup, and value stays: the subsetter keeps all glyphs but the logo's, every
    other feature, and every table, and drops only lookups no remaining feature reaches.
    """
    cmap = font.getBestCmap()
    logo = {cmap[cp] for cp in WANTED_LOGO}
    features = {
        record.FeatureTag
        for tag in ("GSUB", "GPOS")
        for record in font[tag].table.FeatureList.FeatureRecord
    }
    subsetter = subset.Subsetter(_keep_all_options(features - {LOGO_FEATURE}))
    subsetter.populate(
        glyphs=[g for g in font.getGlyphOrder() if g not in logo],
        unicodes=[cp for cp in cmap if cp not in WANTED_LOGO],
    )
    subsetter.subset(font)
    left = logo & set(font.getGlyphOrder())
    if left:
        raise ValueError(f"logo glyphs survived the subset: {sorted(left)}")


def planned_cmap(ctx) -> dict[int, str]:
    """The Roof cmap: Wanted Sans's, then copies for H6, then a new name per other rule."""
    if not ctx.pj_names:
        raise ValueError("planned_cmap needs ctx.pj_names; run copy_closure first")
    cmap = {cp: g for cp, g in ctx.wanted.getBestCmap().items() if ctx.selection.rules[cp] is Rule.WANTED}
    pcmap = ctx.pretendard.getBestCmap()
    taken = set(ctx.wanted.getGlyphOrder()) | set(ctx.pj_names.values())
    for cp, rule in sorted(ctx.selection.rules.items()):
        if rule in (Rule.WANTED, Rule.EXCLUDED_PUA, Rule.EXCLUDED_LOGO):
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
