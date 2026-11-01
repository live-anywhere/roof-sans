"""H3: unit squares, digraphs, Roman numerals, and fractions rebuilt from Wanted Sans glyphs."""

from __future__ import annotations

import sys
import unicodedata
from collections.abc import Sequence
from functools import cache

from roofsans.axis import COMPOSITE_LOCS
from roofsans.newglyph import NewGlyph, Part, composite_glyph
from roofsans.selection import Rule

# Pretendard composes these from letters; their parts follow its components in order.
_UNIT_SQUARES = (0x3300, 0x33FF)
# № decomposes to N o; H3 builds it from N and the raised º instead.
_NUMERO = {0x2116: (ord("N"), ord("º"))}
_FRACTION_SLASHES = (0x002F, 0x2044)


@cache
def _lowest_codepoints(font) -> dict[str, int]:
    """Glyph name → the lowest code point ``font`` maps to it."""
    out: dict[str, int] = {}
    for cp, name in sorted(font.getBestCmap().items()):
        out.setdefault(name, cp)
    return out


def _pretendard_codepoint(ctx, glyph_name: str) -> int:
    cp = _lowest_codepoints(ctx.pretendard).get(glyph_name)
    if cp is None:
        raise ValueError(f"Pretendard component {glyph_name} has no code point")
    return cp


def _sequence_codepoints(ctx, cp: int) -> list[int]:
    glyph = ctx.pretendard["glyf"][ctx.pretendard.getBestCmap()[cp]]
    # Ruling R5: no source composite has a 2×2 transform, so a part is (name, dx, dy).
    if glyph.isComposite() and any(hasattr(c, "transform") for c in glyph.components):
        raise ValueError(f"U+{cp:04X}: Pretendard composite has a component transform")
    if cp in _NUMERO:
        return list(_NUMERO[cp])
    if _UNIT_SQUARES[0] <= cp <= _UNIT_SQUARES[1]:
        return [_pretendard_codepoint(ctx, c.glyphName) for c in glyph.components]
    tag, *fields = unicodedata.decomposition(chr(cp)).split()
    if tag != "<compat>":
        raise ValueError(f"U+{cp:04X}: expected a compatibility decomposition, got {tag}")
    return [int(f, 16) for f in fields]


def sequence_parts(ctx, cp: int) -> list[str]:
    """Component names of ``cp`` in order: the Roof cmap glyph of each part."""
    return [ctx.cmap[c] for c in _sequence_codepoints(ctx, cp)]


def fraction_parts(ctx, cp: int) -> list[str]:
    """``[numr, "fraction", dnom]``, or ``[numr, "fraction"]`` for ``⅟``."""
    tag, *fields = unicodedata.decomposition(chr(cp)).split()
    first, slash, *last = (int(f, 16) for f in fields)
    if tag not in ("<compat>", "<fraction>") or slash not in _FRACTION_SLASHES or len(last) > 1:
        raise ValueError(f"U+{cp:04X}: unexpected fraction decomposition {tag} {fields}")
    wcmap = ctx.wanted.getBestCmap()
    parts = [f"{wcmap[first]}.numr", "fraction", *(f"{wcmap[c]}.dnom" for c in last)]
    missing = [p for p in parts if p not in ctx.wanted["glyf"].glyphs]
    if missing:
        raise ValueError(f"U+{cp:04X}: Wanted Sans has no {missing}")
    return parts


def fraction_offsets(ctx, parts: Sequence[str], t: float) -> list[Part]:
    """Place ``parts`` side by side at Roof normalized ``t``, each at the advances before it."""
    out, x = [], 0.0
    for name in parts:
        out.append((name, x, 0))
        x += ctx.advance(name, t)
    return out


def _available(ctx, name: str) -> bool:
    return name in ctx.contributed or name in ctx.wanted["glyf"].glyphs


def contribute(ctx) -> list[NewGlyph]:
    pcmap = ctx.pretendard.getBestCmap()
    out = []
    for rule, parts_of in ((Rule.H3_SEQUENCE, sequence_parts), (Rule.H3_FRACTION, fraction_parts)):
        skipped = []
        for cp in ctx.selection.codepoints(rule):
            parts = parts_of(ctx, cp)
            # Ruling R11: a part from a rule that has not landed yet skips the glyph.
            if not all(_available(ctx, p) for p in parts):
                skipped.append(cp)
                continue
            placed = {t: fraction_offsets(ctx, parts, t) for t in COMPOSITE_LOCS}
            advance = {t: sum(ctx.advance(p, t) for p in parts) for t in COMPOSITE_LOCS}
            out.append(composite_glyph(ctx.cmap[cp], placed, advance, (cp,), rule, pcmap[cp]))
        if skipped:
            listed = " ".join(f"U+{cp:04X}" for cp in skipped)
            print(f"h3_construct: skipped {rule} (components not built yet): {listed}", file=sys.stderr)
    return out
