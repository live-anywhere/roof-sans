"""GPOS: Pretendard JP's kerning between copied glyphs and mark-to-base for the H4 marks and letters."""

from __future__ import annotations

import sys
import unicodedata

from fontTools.otlLib.builder import (
    buildAnchor,
    buildLookup,
    buildMarkBasePosSubtable,
    buildPairPosGlyphs,
    buildValue,
)
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables

from roofsans.axis import COMPOSITE_LOCS, PJ_PEAK
from roofsans.features import gdef
from roofsans.features.gsub import (
    CJK_SCRIPTS,
    JAN_SCRIPTS,
    add_lang_sys,
    add_scripts,
    lang_sys,
    new_script,
    scripts_by_tag,
)
from roofsans.rules import h2_compose
from roofsans.selection import Rule

# Pretendard JP's kern feature lookups (PairPos, the second inside an Extension).
PJ_KERN = (1, 2)
# Pretendard's (0, 1, 1) region ramps to the 930 master at PJ_PEAK and holds it to 1000.
_PJ_SUPPORTS = ({"wght": (0.0, PJ_PEAK, 1.0)}, {"wght": (PJ_PEAK, 1.0, 1.0)})
_X_ADVANCE = 0x0004
_X_ADVANCE_DEVICE = 0x0040
# Bases that take the horn (Wanted Sans letters), as in the H2 horn letters.
HORN_BASES = ("o", "u", "O", "U")


def _subtables(lookup):
    return [getattr(st, "ExtSubTable", st) for st in lookup.SubTable]


def effective_pairs(lookup, keep: set[str]) -> dict[tuple[str, str], otTables.ValueRecord]:
    """First-glyph value of each pair of ``keep`` glyphs, as a shaper applies one PairPos lookup.

    For a first glyph, subtables are tried in order: a glyph-pair subtable applies only to
    the pairs it lists, while a class subtable that covers the first glyph decides every
    pair starting with it, so no later subtable applies to that glyph. Second glyphs in class
    0 are left out; ``kern_pairs`` checks that class 0 carries no value.
    """
    out: dict[tuple[str, str], otTables.ValueRecord] = {}
    decided: set[str] = set()
    for st in _subtables(lookup):
        if st.Format == 1:
            for a, ps in zip(st.Coverage.glyphs, st.PairSet):
                if a in keep and a not in decided:
                    for r in ps.PairValueRecord:
                        if r.SecondGlyph in keep:
                            out.setdefault((a, r.SecondGlyph), r.Value1)
            continue
        c1, c2 = st.ClassDef1.classDefs, st.ClassDef2.classDefs
        for a in st.Coverage.glyphs:
            if a not in keep or a in decided:
                continue
            row = st.Class1Record[c1.get(a, 0)].Class2Record
            for b, k in c2.items():
                if k and b in keep:
                    out.setdefault((a, b), row[k].Value1)
            decided.add(a)
    return out


def _pretendard_delta(font: TTFont):
    """Device → its delta on Pretendard's (0, 1, 1) region; the region below 400 is dropped."""
    store = font["GDEF"].table.VarStore
    regions = [gdef.region_key(r) for r in store.VarRegionList.Region]

    def delta(dev) -> int:
        if dev is None or dev.StartSize == 0xFFFF:
            return 0
        if dev.DeltaFormat != 0x8000:
            raise ValueError(f"unexpected Pretendard device format {dev.DeltaFormat}")
        data = store.VarData[dev.StartSize]
        total = 0
        for col, ri in enumerate(data.VarRegionIndex):
            ((lo, peak, hi),) = regions[ri]
            if peak > 0:
                if (lo, peak, hi) != (0.0, 1.0, 1.0):
                    raise ValueError(f"unexpected Pretendard region {regions[ri]}")
                total += data.Item[dev.EndSize][col]
        return total

    return delta


def _value(v, delta) -> tuple[int, int]:
    if v is None:
        return (0, 0)
    return (getattr(v, "XAdvance", 0) or 0, delta(getattr(v, "XAdvDevice", None)))


def kern_pairs(ctx) -> tuple[dict[tuple[str, str], tuple[int, int]], int]:
    """(Roof first, second) → (x advance at 400, its delta at 930), summed over Pretendard's kern
    lookups, for pairs whose glyphs are both copied; and the lookups' flag."""
    gpos = ctx.pretendard["GPOS"].table
    kern = [fr.Feature.LookupListIndex for fr in gpos.FeatureList.FeatureRecord if fr.FeatureTag == "kern"]
    if any(list(k) != list(PJ_KERN) for k in kern) or not kern:
        raise ValueError(f"Pretendard kern lookups are {kern}, expected {list(PJ_KERN)}")
    delta = _pretendard_delta(ctx.pretendard)
    keep = set(ctx.pj_names)
    flags = set()
    total: dict[tuple[str, str], tuple[int, int]] = {}
    for index in PJ_KERN:
        lookup = gpos.LookupList.Lookup[index]
        flags.add(lookup.LookupFlag)
        for st in _subtables(lookup):
            if st.LookupType != 2 or st.ValueFormat1 & ~(_X_ADVANCE | _X_ADVANCE_DEVICE) or st.ValueFormat2:
                raise ValueError(f"Pretendard GPOS lookup {index} is not x-advance PairPos")
            if st.Format == 2 and any(_value(r.Class2Record[0].Value1, delta) != (0, 0) for r in st.Class1Record):
                raise ValueError(f"Pretendard GPOS lookup {index} kerns class 0")
        for pair, v in effective_pairs(lookup, keep).items():
            (x, d), (vx, vd) = total.get(pair, (0, 0)), _value(v, delta)
            total[pair] = (x + vx, d + vd)
    if len(flags) != 1:
        raise ValueError(f"Pretendard kern lookups differ in flags: {flags}")
    names = ctx.pj_names
    return {(names[a], names[b]): xd for (a, b), xd in total.items() if any(xd)}, flags.pop()


def _anchor(store: gdef.VarStoreAppender, masters: dict[float, tuple[float, float]]) -> otTables.Anchor:
    """An anchor at ``masters`` (Roof normalized location → x, y), varying through ``store``."""
    x, dx = store.masters({t: p[0] for t, p in masters.items()})
    y, dy = store.masters({t: p[1] for t, p in masters.items()})
    return buildAnchor(x, y, deviceX=dx, deviceY=dy) if dx or dy else buildAnchor(x, y)


def _varying(store: gdef.VarStoreAppender, anchor_at) -> otTables.Anchor:
    """An anchor whose position at each ``COMPOSITE_LOCS`` location is ``anchor_at(t)``."""
    return _anchor(store, {t: anchor_at(t) for t in COMPOSITE_LOCS})


def h4_bases(ctx) -> list[str]:
    """Roof names of the H4 letters that take marks (every H4 code point that is not a mark)."""
    cps = ctx.selection.codepoints(Rule.H4_LETTER)
    return [ctx.cmap[cp] for cp in cps if not unicodedata.category(chr(cp)).startswith("M")]


def mark_lookups(ctx, glyph_map, store: gdef.VarStoreAppender) -> tuple[list[otTables.Lookup], list[str]]:
    """MarkBasePos lookups and the H4 marks left out because ``mark_anchor`` has no anchor for them.

    The lookups are: the H4 combining marks on Wanted Sans letters (top, bottom), the horn on
    ``o u O U``, and (ruling R36) Wanted's letter marks and the H4 marks on the H4 letters.
    Every anchor takes H2's anchor at each ``COMPOSITE_LOCS`` location (ruling R35), so a
    decomposed sequence shapes like the H2 composite.
    """
    served: dict[str, str] = {}
    skipped = []
    for mark in gdef.h4_marks(ctx):
        try:
            served[mark] = h2_compose.mark_anchor(ctx, mark)[0]
        except ValueError:
            skipped.append(mark)
    marks = {m: _varying(store, lambda t, m=m: h2_compose.mark_anchor(ctx, m, t)[1:]) for m in served}

    def base_anchors(base: str, classes: tuple[str, ...]) -> dict[int, otTables.Anchor]:
        out = {}
        for c, cls in enumerate(classes):
            if h2_compose.base_anchor(ctx, base, cls) is not None:
                out[c] = _varying(store, lambda t: h2_compose.base_anchor(ctx, base, cls, t))
        return out

    lookups = []
    for cls in ("top", "bottom"):
        bases = {b: a for b in h2_compose.wanted_letter_bases(ctx) if (a := base_anchors(b, (cls,)))}
        lookups.append(_mark_lookup({m: (0, marks[m]) for m, c in served.items() if c == cls}, bases, glyph_map))
    horn = {b: base_anchors(b, ("horn",)) for b in HORN_BASES}
    lookups.append(_mark_lookup({m: (0, marks[m]) for m, c in served.items() if c == "horn"}, horn, glyph_map))

    classes = ("top", "bottom")
    wanted_marks = {}
    for m in h2_compose.wanted_letter_marks(ctx):
        cls, *_ = h2_compose.mark_anchor(ctx, m)
        wanted_marks[m] = (classes.index(cls), _varying(store, lambda t, m=m: h2_compose.mark_anchor(ctx, m, t)[1:]))
    h4_marks = {m: (classes.index(c), marks[m]) for m, c in served.items() if c in classes}
    bases = {b: a for b in h4_bases(ctx) if (a := base_anchors(b, classes))}
    lookups.append(_mark_lookup({**wanted_marks, **h4_marks}, bases, glyph_map))
    return lookups, skipped


def _mark_lookup(marks, bases, glyph_map) -> otTables.Lookup:
    if not marks or not bases:
        raise ValueError("an added mark lookup has no marks or no bases")
    return buildLookup([buildMarkBasePosSubtable(marks, bases, glyph_map)], table="GPOS")


def carry(font: TTFont, ctx) -> None:
    """Append the kern and mark lookups to Wanted Sans's kern and mark features (so every
    LangSys has them) and add the CJK scripts and JAN/KOR LangSys GSUB has."""
    gpos = font["GPOS"].table
    glyph_map = font.getReverseGlyphMap()
    store = gdef.VarStoreAppender()
    new: dict[str, list[int]] = {"kern": [], "mark": []}
    lookups = gpos.LookupList.Lookup

    pairs, flag = kern_pairs(ctx)
    if pairs:
        values = {}
        for pair, (x, d) in pairs.items():
            dev = store.deltas(_PJ_SUPPORTS, [d, d])
            values[pair] = (buildValue({"XAdvance": x, **({"XAdvDevice": dev} if dev else {})}), None)
        new["kern"].append(len(lookups))
        lookups.append(buildLookup(buildPairPosGlyphs(values, glyph_map), flags=flag, table="GPOS"))
    else:
        print("features: no Pretendard kern pair has both glyphs copied; no kern lookup added", file=sys.stderr)

    marks, skipped = mark_lookups(ctx, glyph_map, store)
    for lookup in marks:
        new["mark"].append(len(lookups))
        lookups.append(lookup)
    gpos.LookupList.LookupCount = len(lookups)
    if skipped:
        listed = " ".join(skipped)
        print(f"features: {len(skipped)} H4 marks have no anchor and no mark-to-base: {listed}", file=sys.stderr)

    for fr in gpos.FeatureList.FeatureRecord:
        if fr.FeatureTag in new:
            fr.Feature.LookupListIndex = [*fr.Feature.LookupListIndex, *new[fr.FeatureTag]]
            fr.Feature.LookupCount = len(fr.Feature.LookupListIndex)

    scripts = scripts_by_tag(gpos)
    default = list(scripts["DFLT"].DefaultLangSys.FeatureIndex)
    add_scripts(gpos, {tag: new_script(lang_sys(default)) for tag in CJK_SCRIPTS})
    scripts = scripts_by_tag(gpos)
    add_lang_sys(scripts["hani"], "KOR ", list(scripts["hani"].DefaultLangSys.FeatureIndex))
    for tag in JAN_SCRIPTS:
        add_lang_sys(scripts[tag], "JAN ", list(scripts[tag].DefaultLangSys.FeatureIndex))

    gdef.append_store(font["GDEF"].table.VarStore, store)
