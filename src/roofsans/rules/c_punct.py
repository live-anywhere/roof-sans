"""C3: Wanted Sans punctuation at Chinese fullwidth ink positions."""

from __future__ import annotations

from roofsans.axis import COMPOSITE_LOCS, PJ_PEAK
from roofsans.newglyph import NewGlyph, composite_glyph
from roofsans.rules.c_hanzi import calibrate, ink_bounds
from roofsans.selection import Rule

ZHS_SIGNS = (0xFF01, 0xFF1A, 0xFF1B, 0xFF1F)
ZHS_QUOTES = (0x2018, 0x2019, 0x201C, 0x201D, 0x00B7)


def target_center(ctx, cp: int, t: float) -> float:
    """The ink center x of the calibrated Source Han Sans sign at Roof ``t``: linear from the
    100 master to the 400 master to the 930 master, then held, like the C1 hanzi."""
    c = calibrate(ctx)
    source = ctx.shs_cn.getBestCmap()[cp]

    def center(weight: float, dx: float) -> float:
        x0, _, x1, _ = ink_bounds(ctx.cs.outline(source, weight))
        return c.scale * (x0 + x1) / 2 + dx

    regular = center(c.w400, c.dx400)
    if t < 0:
        return regular + (center(c.w100, c.dx100) - regular) * -t
    return regular + (center(c.w930, c.dx930) - regular) * min(t / PJ_PEAK, 1)


def contribute(ctx) -> list[NewGlyph]:
    out = []
    for cp in (*ZHS_SIGNS, *ZHS_QUOTES):
        if cp in ZHS_SIGNS:
            (component,) = ctx.contributed[ctx.cmap[cp]].glyph.components
            base = component.glyphName
        else:
            base = ctx.cmap[cp]
        parts = {}
        locs = ctx.locs(COMPOSITE_LOCS)
        for t in locs:
            x0, _, x1, _ = ink_bounds(ctx.outline(base, t))
            parts[t] = [(base, target_center(ctx, cp, t) - (x0 + x1) / 2, 0)]
        out.append(composite_glyph(f'uni{cp:04X}.zhs', parts,
                                  {t: 1920 for t in locs}, (),
                                  Rule.C3_PUNCT, ctx.shs_cn.getBestCmap()[cp]))
    return out
