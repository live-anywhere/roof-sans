"""GDEF: glyph classes for the added glyphs and the variation rows their GPOS values use."""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping, Sequence

from fontTools.misc.roundTools import otRound
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables
from fontTools.varLib.models import VariationModel
from fontTools.varLib.varStore import OnlineVarStoreBuilder

from roofsans.selection import Rule

BASE, MARK = 1, 3

Support = Mapping[str, tuple[float, float, float]]


def h4_marks(ctx) -> list[str]:
    """Roof names of the H4 combining marks (general category Mn)."""
    cps = ctx.selection.codepoints(Rule.H4_LETTER)
    return [ctx.cmap[cp] for cp in cps if unicodedata.category(chr(cp)) == "Mn"]


def classify(font: TTFont, ctx) -> None:
    """Class 3 (mark) for H4 combining marks, class 1 (base) for every other added glyph."""
    classes = font["GDEF"].table.GlyphClassDef.classDefs
    wanted = set(ctx.wanted.getGlyphOrder())
    marks = set(h4_marks(ctx))
    for name in font.getGlyphOrder():
        if name not in wanted:
            classes[name] = MARK if name in marks else BASE


class VarStoreAppender:
    """Variation rows for new GPOS values, appended to the font's GDEF store by ``append_store``.

    Each Device it hands out holds an index into its own rows until ``append_store`` moves
    the rows behind the existing ones and shifts the Device's outer index to match.
    """

    def __init__(self) -> None:
        self._builder = OnlineVarStoreBuilder(["wght"])
        self._models: dict[tuple[float, ...], VariationModel] = {}
        self.devices: list[otTables.Device] = []

    def _device(self, var_idx: int) -> otTables.Device:
        dev = otTables.Device()
        dev.DeltaFormat = 0x8000
        dev.StartSize, dev.EndSize = var_idx >> 16, var_idx & 0xFFFF
        self.devices.append(dev)
        return dev

    def masters(self, values: Mapping[float, float]) -> tuple[int, otTables.Device | None]:
        """The rounded default of ``values`` (Roof normalized location → value) and a Device
        reproducing the others, or None when the value does not vary."""
        locs = tuple(sorted(values))
        model = self._models.get(locs)
        if model is None:
            model = self._models[locs] = VariationModel([{"wght": t} if t else {} for t in locs], ["wght"])
        deltas = model.getDeltas([values[t] for t in locs], round=otRound)
        if not any(deltas[1:]):
            return deltas[0], None
        self._builder.setSupports(model.supports)
        return deltas[0], self._device(self._builder.storeDeltas(deltas[1:]))

    def deltas(self, supports: Sequence[Support], deltas: Sequence[int]) -> otTables.Device | None:
        """A Device for ``deltas`` over ``supports``, or None when all are zero."""
        if not any(deltas):
            return None
        self._builder.setSupports([dict(s) for s in supports])
        return self._device(self._builder.storeDeltas([otRound(d) for d in deltas]))

    def finish(self) -> otTables.VarStore:
        return self._builder.finish()


def region_key(region) -> tuple[tuple[float, float, float], ...]:
    return tuple((a.StartCoord, a.PeakCoord, a.EndCoord) for a in region.VarRegionAxis)


def append_store(store: otTables.VarStore, new: VarStoreAppender) -> None:
    """Append ``new``'s rows to ``store``, reusing equal regions; existing indices stay valid."""
    added = new.finish()
    regions = store.VarRegionList.Region
    index = {}
    for i, r in enumerate(regions):
        index.setdefault(region_key(r), i)
    remap = []
    for r in added.VarRegionList.Region:
        key = region_key(r)
        if key not in index:
            index[key] = len(regions)
            regions.append(r)
        remap.append(index[key])
    store.VarRegionList.RegionCount = len(regions)
    offset = len(store.VarData)
    for data in added.VarData:
        data.VarRegionIndex = [remap[i] for i in data.VarRegionIndex]
        data.VarRegionCount = len(data.VarRegionIndex)
        store.VarData.append(data)
    store.VarDataCount = len(store.VarData)
    for dev in new.devices:
        dev.StartSize += offset
