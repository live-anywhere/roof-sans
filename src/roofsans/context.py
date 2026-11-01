"""Shared state for one Roof Sans build."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from fontTools.ttLib import TTFont

from roofsans.axis import PJ_PEAK, roof_wght
from roofsans import light as light_mod
from roofsans.inputs import Inputs
from roofsans.newglyph import NewGlyph, newglyph_outline
from roofsans.outline import Outline
from roofsans.sampling import PretendardSampler, ShsSampler, WantedSampler
from roofsans.selection import Selection, select

if TYPE_CHECKING:
    from roofsans.rules.c_hanzi import Calibration


def pretendard_wght(norm: float) -> float:
    """The Pretendard weight a copied glyph shows at Roof ``norm``: the same weight up to
    930, then the 930 plateau."""
    if norm < 0:
        return roof_wght(norm)
    return 400 + 530 * min(norm / PJ_PEAK, 1.0)


@dataclass
class BuildContext:
    inputs: Inputs
    wanted: TTFont
    pretendard: TTFont
    shs_cn: TTFont
    shs_jp: TTFont
    cs: ShsSampler
    js: ShsSampler
    selection: Selection
    ws: WantedSampler
    ps: PretendardSampler
    # None when the build leaves out the light weights (``--without-light``).
    light: light_mod.LightData | None
    chinese: bool = True
    cmap: dict[int, str] = field(default_factory=dict)
    pj_names: dict[str, str] = field(default_factory=dict)
    contributed: dict[str, NewGlyph] = field(default_factory=dict)
    calibration: Calibration | None = field(default=None, init=False, repr=False)
    chinese_sets: tuple[tuple[int, ...], tuple[int, ...]] | None = field(default=None, init=False, repr=False)
    _pj_sources: dict[str, str] = field(default_factory=dict, init=False, repr=False)

    def _pj_source(self, name: str) -> str | None:
        """The Pretendard glyph a copied Roof glyph comes from, if ``name`` is a copy."""
        if len(self._pj_sources) != len(self.pj_names):
            self._pj_sources = {roof: pj for pj, roof in self.pj_names.items()}
        return self._pj_sources.get(name)

    def locs(self, locs: tuple[float, ...]) -> tuple[float, ...]:
        """Master locations ``locs``, without the light ones (t < 0) when the build has none."""
        return locs if self.light is not None else tuple(t for t in locs if t >= 0)

    def outline(self, name: str, norm: float) -> Outline:
        """Roof glyph ``name`` at Roof normalized ``norm``, decomposed."""
        source = self._pj_source(name)
        if source is not None:
            # The sampler applies component transforms; newglyph_outline does not.
            return self.ps.outline(source, pretendard_wght(norm))
        if name in self.contributed:
            return newglyph_outline(self.contributed[name], norm, self.outline)
        return self.ws.outline(name, roof_wght(norm))

    def advance(self, name: str, norm: float) -> float:
        source = self._pj_source(name)
        if source is not None:
            return self.ps.advance(source, pretendard_wght(norm))
        if name in self.contributed:
            return self.outline(name, norm).advance()
        return self.ws.advance(name, roof_wght(norm))


def make_context(inputs: Inputs, chinese: bool = True, light: bool = True) -> BuildContext:
    """The build state. With ``light``, ``wanted`` is Wanted Sans with the light tuples added
    in memory, so every rule reads its glyphs, offsets, and anchors down to 100. Without it,
    the build is the 400–1000 font from before the light weights."""
    wanted = TTFont(inputs.wanted)
    pretendard = TTFont(inputs.pretendard)
    light_data = light_mod.solve(wanted, pretendard) if light else None
    if light_data is not None:
        light_mod.extend_wanted(wanted, light_data)
    shs_cn = TTFont(inputs.shs_cn)
    shs_jp = TTFont(inputs.shs_jp)
    return BuildContext(
        inputs=inputs,
        wanted=wanted,
        pretendard=pretendard,
        shs_cn=shs_cn,
        shs_jp=shs_jp,
        cs=ShsSampler(shs_cn),
        js=ShsSampler(shs_jp),
        selection=select(wanted, pretendard, shs_cn, chinese=chinese),
        ws=WantedSampler(wanted),
        ps=PretendardSampler(pretendard),
        light=light_data,
        chinese=chinese,
    )
