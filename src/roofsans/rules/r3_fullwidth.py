"""Rule 3: fullwidth letters, digits, and signs rebuilt from one Wanted Sans glyph."""

from __future__ import annotations

from roofsans.axis import COMPOSITE_LOCS, roof_wght
from roofsans.newglyph import NewGlyph, composite_glyph
from roofsans.selection import Rule

FULLWIDTH_ADVANCE = 1920
# U+FF01–FF5E map to U+0021–007E.
_FULLWIDTH_OFFSET = 0xFEE0
# Pretendard's placement of a sign is sampled no heavier than its 930 master.
_PRETENDARD_MAX = 930


def _center_x(outline) -> float:
    x_min, _, x_max, _ = outline.bounds()
    return (x_min + x_max) / 2


def _composite(ctx, cp: int, base: str, dx: dict[float, float], rule: Rule, source: str) -> NewGlyph:
    return composite_glyph(
        ctx.cmap[cp],
        {t: [(base, dx[t], 0)] for t in COMPOSITE_LOCS},
        {t: FULLWIDTH_ADVANCE for t in COMPOSITE_LOCS},
        (cp,),
        rule,
        source,
    )


def contribute(ctx) -> list[NewGlyph]:
    wcmap = ctx.wanted.getBestCmap()
    pcmap = ctx.pretendard.getBestCmap()
    out = []
    for cp in ctx.selection.codepoints(Rule.R3_FULLWIDTH):
        base = wcmap[cp - _FULLWIDTH_OFFSET]
        dx = {t: (FULLWIDTH_ADVANCE - ctx.advance(base, t)) / 2 for t in COMPOSITE_LOCS}
        out.append(_composite(ctx, cp, base, dx, Rule.R3_FULLWIDTH, pcmap[cp]))
    # Design decision 11: the Wanted Sans glyph goes where Pretendard puts its own.
    for cp in ctx.selection.codepoints(Rule.R3_SIGN):
        source = pcmap[cp]
        (component,) = ctx.pretendard["glyf"][source].components
        base = component.glyphName
        dx = {
            t: _center_x(ctx.ps.outline(source, min(roof_wght(t), _PRETENDARD_MAX)))
            - _center_x(ctx.outline(base, t))
            for t in COMPOSITE_LOCS
        }
        out.append(_composite(ctx, cp, base, dx, Rule.R3_SIGN, source))
    return out
