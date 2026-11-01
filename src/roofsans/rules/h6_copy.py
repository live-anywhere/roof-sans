"""H6: Han, kana, and Japanese punctuation glyphs copied unchanged from Pretendard JP."""

from __future__ import annotations

import copy

from roofsans.newglyph import NewGlyph
from roofsans.selection import JAN_SHARED, Rule
from roofsans.variations import remap_pretendard_tuples

# Pretendard JP GSUB lookups whose outputs are copied: `locl` KOR (34); `jp78`,
# `jp83`, `jp90`, `nlck` (73–76); the `rlig` FeatureVariations kana alternates (77–85).
CARRIED_LOOKUPS = (34, *range(73, 86))

PJ_SUFFIX = ".pj"


def format14_sequences(font) -> dict[int, list[tuple[int, str | None]]]:
    """The font's format-14 ``uvsDict``: selector → [(base, glyph or None)]."""
    for table in font["cmap"].tables:
        if table.format == 14:
            return table.uvsDict
    return {}


def _lookup_outputs(font, indices) -> set[str]:
    lookups = font["GSUB"].table.LookupList.Lookup
    out: set[str] = set()
    for i in indices:
        lookup = lookups[i]
        for sub in lookup.SubTable:
            if lookup.LookupType == 7:
                sub = sub.ExtSubTable
            if sub.LookupType != 1:
                raise ValueError(f"Pretendard GSUB lookup {i} is type {sub.LookupType}, expected 1")
            out.update(sub.mapping.values())
    return out


def copy_closure(ctx) -> dict[str, str]:
    """Map every Pretendard glyph the build copies to its Roof name; fills ``ctx.pj_names``."""
    pretendard = ctx.pretendard
    pcmap = pretendard.getBestCmap()
    seeds = {pcmap[cp] for cp in ctx.selection.codepoints(Rule.H6_COPY)}
    seeds.update(pcmap[cp] for cp in JAN_SHARED)
    seeds.update(g for seqs in format14_sequences(pretendard).values() for _, g in seqs if g is not None)
    seeds.update(_lookup_outputs(pretendard, CARRIED_LOOKUPS))

    glyf = pretendard["glyf"]
    closure: set[str] = set()
    stack = list(seeds)
    while stack:
        name = stack.pop()
        if name in closure:
            continue
        closure.add(name)
        glyph = glyf[name]
        if glyph.isComposite():
            stack.extend(c.glyphName for c in glyph.components)

    wanted_names = set(ctx.wanted.getGlyphOrder())
    names: dict[str, str] = {}
    for name in sorted(closure, key=pretendard.getGlyphID):
        roof = name + PJ_SUFFIX if name in wanted_names else name
        if roof in wanted_names:
            raise ValueError(f"copied glyph name {roof} collides with Wanted Sans")
        names[name] = roof
    ctx.pj_names = names
    return names


def contribute(ctx) -> list[NewGlyph]:
    names = ctx.pj_names or copy_closure(ctx)
    pretendard = ctx.pretendard
    glyf = pretendard["glyf"]
    hmtx = pretendard["hmtx"].metrics
    gvar = pretendard["gvar"].variations

    unicodes: dict[str, list[int]] = {}
    pcmap = pretendard.getBestCmap()
    for cp in ctx.selection.codepoints(Rule.H6_COPY):
        unicodes.setdefault(pcmap[cp], []).append(cp)

    out = []
    for source, name in names.items():
        glyph = copy.deepcopy(glyf[source])
        if glyph.isComposite():
            for c in glyph.components:
                c.glyphName = names[c.glyphName]
        out.append(
            NewGlyph(
                name=name,
                glyph=glyph,
                advance=hmtx[source][0],
                variations=remap_pretendard_tuples(gvar.get(source, []), light=ctx.light is not None),
                unicodes=tuple(unicodes.get(source, ())),
                rule=Rule.H6_COPY,
                source=source,
            )
        )
    return out
