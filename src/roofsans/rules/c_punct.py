"""C3: Wanted Sans punctuation at Chinese fullwidth ink positions."""

from __future__ import annotations

from roofsans.axis import COMPOSITE_LOCS, PJ_PEAK
from roofsans.newglyph import NewGlyph, composite_glyph
from roofsans.rules.c_hanzi import calibrate, ink_bounds
from roofsans.selection import Rule

ZHS_SIGNS = (0xFF01, 0xFF1A, 0xFF1B, 0xFF1F)
ZHS_QUOTES = (0x2018, 0x2019, 0x201C, 0x201D, 0x00B7)


def target_center(ctx, cp: int, t: float) -> float:
    c = calibrate(ctx)
    fraction = min(t / PJ_PEAK, 1)
    source = ctx.shs_cn.getBestCmap()[cp]
    a = ink_bounds(ctx.cs.outline(source, c.w400))
    b = ink_bounds(ctx.cs.outline(source, c.w930))
    left = c.scale * (a[0] + a[2]) / 2 + c.dx400
    right = c.scale * (b[0] + b[2]) / 2 + c.dx930
    return left + (right - left) * fraction


def contribute(ctx) -> list[NewGlyph]:
    out = []
    for cp in (*ZHS_SIGNS, *ZHS_QUOTES):
        if cp in ZHS_SIGNS:
            (component,) = ctx.contributed[ctx.cmap[cp]].glyph.components
            base = component.glyphName
        else:
            base = ctx.cmap[cp]
        parts = {}
        for t in COMPOSITE_LOCS:
            x0, _, x1, _ = ink_bounds(ctx.outline(base, t))
            parts[t] = [(base, target_center(ctx, cp, t) - (x0 + x1) / 2, 0)]
        out.append(composite_glyph(f'uni{cp:04X}.zhs', parts,
                                  {t: 1920 for t in COMPOSITE_LOCS}, (),
                                  Rule.C3_PUNCT, ctx.shs_cn.getBestCmap()[cp]))
    return out
