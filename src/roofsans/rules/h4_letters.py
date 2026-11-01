"""H4: Pretendard letters, matched to Wanted Sans in height and weight."""

from __future__ import annotations

import weakref

from roofsans.axis import H4_LOCS
from roofsans.harmonize import MasterParams, outline_masters, solve_masters
from roofsans.newglyph import NewGlyph, simple_glyph
from roofsans.selection import Rule

# solve_masters per build context (ruling R12); BuildContext is unhashable, so key by id.
_PARAMS: dict[int, tuple[weakref.ref, dict[float, MasterParams]]] = {}


def params(ctx) -> dict[float, MasterParams]:
    """H4 master parameters for ``ctx``, solved once per context."""
    key = id(ctx)
    entry = _PARAMS.get(key)
    if entry is None or entry[0]() is not ctx:
        entry = (weakref.ref(ctx, lambda _: _PARAMS.pop(key, None)), solve_masters(ctx.ps, ctx.ws, ctx.locs(H4_LOCS)))
        _PARAMS[key] = entry
    return entry[1]


def contribute(ctx) -> list[NewGlyph]:
    p = params(ctx)
    pcmap = ctx.pretendard.getBestCmap()
    out = []
    for cp in ctx.selection.codepoints(Rule.H4_LETTER):
        source = pcmap[cp]
        masters = outline_masters(lambda w: ctx.ps.outline(source, w), ctx.selection.zone[cp], p)
        out.append(simple_glyph(ctx.cmap[cp], masters, [cp], Rule.H4_LETTER, source))
    return out
