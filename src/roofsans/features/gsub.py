"""GSUB: Wanted Sans's layout plus Pretendard JP's CJK substitutions (design "OpenType features")."""

from __future__ import annotations

import copy
import unicodedata
from collections.abc import Mapping

from fontTools.otlLib.builder import buildCoverage, buildLookup, buildSingleSubstSubtable
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables

from roofsans.rules.c_hanzi import zhs_forms
from roofsans.rules.c_punct import ZHS_QUOTES, ZHS_SIGNS
from roofsans.selection import JAN_SHARED

# Pretendard JP lookups this build carries, verified by feature tag on the pinned input.
PJ_KOR = 34  # locl under hani/KOR: 537 Korean hanja forms
PJ_WIDTHS = {"fwid": 71, "pwid": 72}
PJ_JP = {"jp78": 73, "jp83": 74, "jp90": 75, "nlck": 76}
PJ_KANA = tuple(range(77, 86))  # rlig FeatureVariations kana weight alternates
# Pretendard's ss05 is the Korean set; Wanted Sans's ss05 already means a Latin alternate.
KOR_SET = "ss20"
PJ_KOR_SET = "ss05"
# Ruling R39: the UI name when Pretendard's ss05 has none.
KOR_SET_FALLBACK_NAME = "Korean hanja forms"
# Opt-in features every script's default LangSys gains.
CJK_FEATURES = ("ss20", "jp78", "jp83", "jp90", "nlck", "fwid", "pwid")
# Scripts Pretendard's Han and kana glyphs itemize as; Wanted Sans has neither.
CJK_SCRIPTS = ("hani", "kana")
# Rule H1: Japanese punctuation under JAN, also for brackets around Latin and digits.
JAN_SCRIPTS = ("DFLT", "hani", "kana", "latn")
ZHS_SCRIPTS = ("DFLT", "hani", "latn")
WIDENED_SCRIPTS = ("DFLT", "hang", "latn")
RLIG = "rlig"
_F2DOT14 = 1 << 14


def to_roof_t(s: float) -> float:
    """Pretendard JP normalized ``s`` → Roof normalized t, clamped to [0, 1], as F2Dot14."""
    wght = 400 + (530 if s >= 0 else 355) * s
    t = min(max((wght - 400) / 600, 0.0), 1.0)
    return round(t * _F2DOT14) / _F2DOT14


def merge_variations(
    wanted: list[tuple[float, list[int]]], pretendard: list[tuple[float, list[int]]]
) -> list[tuple[float, list[int]]]:
    """``rlig`` FeatureVariations records (minimum t, lookups) that apply both fonts' records.

    Each input lists (minimum t, lookups) in its record order, the first match winning. A
    merged record exists for each distinct threshold, in descending t, and turns on the
    lookups of the first matching record of each font at that t.
    """

    def active(records, t):
        return next((lookups for lo, lookups in records if lo <= t), [])

    out = []
    for t in sorted({lo for lo, _ in wanted + pretendard}, reverse=True):
        out.append((t, sorted({*active(wanted, t), *active(pretendard, t)})))
    return out


def width_mapping(
    lookup: Mapping[str, str], pcmap: Mapping[int, str], cmap: Mapping[int, str], glyphs: set[str]
) -> dict[str, str]:
    """``fwid``/``pwid`` entries re-mapped through code points: Pretendard source code point →
    Roof glyph, target code point → Roof glyph. Entries without a code point or a Roof glyph
    at either end drop."""
    cps: dict[str, list[int]] = {}
    for cp, g in sorted(pcmap.items()):
        cps.setdefault(g, []).append(cp)
    out: dict[str, str] = {}
    for src, dst in lookup.items():
        targets = {cmap.get(cp) for cp in cps.get(dst, ())} & glyphs
        if len(targets) > 1:
            raise ValueError(f"{dst} reaches several Roof glyphs: {sorted(targets)}")
        for cp in cps.get(src, ()):
            source = cmap.get(cp)
            if source not in glyphs or not targets:
                continue
            target = next(iter(targets))
            if out.get(source, target) != target:
                raise ValueError(f"{source} maps to both {out[source]} and {target}")
            if source != target:
                out[source] = target
    return out


def _single_mapping(gsub, index: int) -> dict[str, str]:
    lookup = gsub.LookupList.Lookup[index]
    if lookup.LookupType != 1 or lookup.LookupFlag:
        raise ValueError(f"Pretendard GSUB lookup {index} is not a plain single substitution")
    out: dict[str, str] = {}
    for st in lookup.SubTable:
        out.update(st.mapping)
    return out


def _feature_index(gsub, tag: str, lookups: list[int]) -> int:
    for i, fr in enumerate(gsub.FeatureList.FeatureRecord):
        if fr.FeatureTag == tag and list(fr.Feature.LookupListIndex) == lookups:
            return i
    raise ValueError(f"no {tag} feature with lookups {lookups}")


def _check_pretendard(gsub) -> int:
    """Check the carried lookups' tags on Pretendard JP; return its ``rlig`` feature index."""
    kor = _feature_index(gsub, "locl", [PJ_KOR])
    hani = next(sr.Script for sr in gsub.ScriptList.ScriptRecord if sr.ScriptTag == "hani")
    langs = {lr.LangSysTag: lr.LangSys for lr in hani.LangSysRecord}
    if kor not in langs["KOR "].FeatureIndex:
        raise ValueError("Pretendard's hani/KOR LangSys lacks the locl KOR feature")
    for tag, index in (*PJ_WIDTHS.items(), *PJ_JP.items()):
        _feature_index(gsub, tag, [index])
    return _feature_index(gsub, RLIG, [])


def _variation_records(gsub, feature: int) -> list[tuple[float, list[int]]]:
    """(minimum normalized value, lookups) of each FeatureVariations record, which may only
    substitute ``feature`` and only condition the single axis up to its maximum."""
    out = []
    for rec in gsub.FeatureVariations.FeatureVariationRecord:
        (cond,) = rec.ConditionSet.ConditionTable
        (sub,) = rec.FeatureTableSubstitution.SubstitutionRecord
        if cond.AxisIndex != 0 or cond.FilterRangeMaxValue != 1.0 or sub.FeatureIndex != feature:
            raise ValueError("unexpected FeatureVariations record")
        out.append((cond.FilterRangeMinValue, list(sub.Feature.LookupListIndex)))
    return out


def _feature(tag: str, lookups: list[int]) -> otTables.FeatureRecord:
    fr = otTables.FeatureRecord()
    fr.FeatureTag = tag
    fr.Feature = otTables.Feature()
    fr.Feature.FeatureParams = None
    fr.Feature.LookupListIndex = list(lookups)
    fr.Feature.LookupCount = len(lookups)
    return fr


def kor_set_name(pretendard: TTFont) -> str:
    """The UI name ``ss20`` takes: Pretendard's ``ss05`` name, else the R39 fallback."""
    for fr in pretendard["GSUB"].table.FeatureList.FeatureRecord:
        params = fr.Feature.FeatureParams
        if fr.FeatureTag == PJ_KOR_SET and params is not None:
            name = pretendard["name"].getDebugName(params.UINameID)
            if name:
                return name
    return KOR_SET_FALLBACK_NAME


def _stylistic_set_params() -> otTables.FeatureParamsStylisticSet:
    """Stylistic-set FeatureParams; ``finalize`` writes the name record and sets UINameID."""
    params = otTables.FeatureParamsStylisticSet()
    params.Version = 0
    params.UINameID = 0
    return params


def sort_features(table) -> None:
    """Sort ``table``'s FeatureList by tag, as the OpenType spec requires, and remap every
    feature index to match. Records with the same tag keep their relative order."""
    records = table.FeatureList.FeatureRecord
    order = sorted(range(len(records)), key=lambda i: records[i].FeatureTag)
    index = {old: new for new, old in enumerate(order)}
    table.FeatureList.FeatureRecord = [records[i] for i in order]
    seen: set[int] = set()
    for sr in table.ScriptList.ScriptRecord:
        for ls in (sr.Script.DefaultLangSys, *(lr.LangSys for lr in sr.Script.LangSysRecord)):
            if ls is None or id(ls) in seen:
                continue
            seen.add(id(ls))
            ls.FeatureIndex = sorted(index[i] for i in ls.FeatureIndex)
            if ls.ReqFeatureIndex != 0xFFFF:
                ls.ReqFeatureIndex = index[ls.ReqFeatureIndex]
    variations = getattr(table, "FeatureVariations", None)
    for rec in variations.FeatureVariationRecord if variations else ():
        subs = rec.FeatureTableSubstitution.SubstitutionRecord
        for sub in subs:
            sub.FeatureIndex = index[sub.FeatureIndex]
        subs.sort(key=lambda sub: sub.FeatureIndex)


def lang_sys(features: list[int]) -> otTables.LangSys:
    ls = otTables.LangSys()
    ls.LookupOrder = None
    ls.ReqFeatureIndex = 0xFFFF
    ls.FeatureIndex = sorted(set(features))
    ls.FeatureCount = len(ls.FeatureIndex)
    return ls


def new_script(default: otTables.LangSys) -> otTables.Script:
    s = otTables.Script()
    s.DefaultLangSys = default
    s.LangSysRecord = []
    s.LangSysCount = 0
    return s


def add_lang_sys(script: otTables.Script, tag: str, features: list[int]) -> None:
    """Add LangSys ``tag`` (4 characters) to ``script``, keeping the records sorted."""
    if any(lr.LangSysTag == tag for lr in script.LangSysRecord):
        raise ValueError(f"LangSys {tag!r} exists")
    lr = otTables.LangSysRecord()
    lr.LangSysTag = tag
    lr.LangSys = lang_sys(features)
    script.LangSysRecord = sorted([*script.LangSysRecord, lr], key=lambda r: r.LangSysTag)
    script.LangSysCount = len(script.LangSysRecord)


def add_scripts(table, scripts: dict[str, otTables.Script]) -> None:
    """Add ``scripts`` to ``table``'s ScriptList; tags stay sorted, as shapers binary-search them."""
    records = list(table.ScriptList.ScriptRecord)
    for tag, script in scripts.items():
        if any(sr.ScriptTag == tag for sr in records):
            raise ValueError(f"script {tag} exists")
        sr = otTables.ScriptRecord()
        sr.ScriptTag, sr.Script = tag, script
        records.append(sr)
    table.ScriptList.ScriptRecord = sorted(records, key=lambda r: r.ScriptTag)
    table.ScriptList.ScriptCount = len(records)


def scripts_by_tag(table) -> dict[str, otTables.Script]:
    return {sr.ScriptTag: sr.Script for sr in table.ScriptList.ScriptRecord}


def _renamed(mapping: Mapping[str, str], names: Mapping[str, str], glyphs: set[str]) -> dict[str, str]:
    """``mapping`` with Pretendard names replaced by Roof copies; entries with a glyph absent drop."""
    out = {}
    for src, dst in mapping.items():
        a, b = names.get(src), names.get(dst)
        if a in glyphs and b in glyphs:
            out[a] = b
    return out


def _zhs_quotes(cmap: Mapping[int, str], glyph_map: Mapping[str, int], target: int) -> otTables.Lookup:
    """Keep apostrophes and middle dots inside alphanumeric words proportional."""
    alnum = {
        g for cp, g in cmap.items()
        if cp < 0x3000 and (unicodedata.category(chr(cp)).startswith("L")
                            or unicodedata.category(chr(cp)) == "Nd")
    }
    exception = otTables.ChainContextSubst()
    exception.Format = 3
    exception.BacktrackCoverage = [buildCoverage(alnum, glyph_map)]
    exception.InputCoverage = [buildCoverage({cmap[0x2019], cmap[0x00B7]}, glyph_map)]
    exception.LookAheadCoverage = [buildCoverage(alnum, glyph_map)]
    exception.BacktrackGlyphCount = exception.LookAheadGlyphCount = 1
    exception.InputGlyphCount = 1
    exception.SubstCount = 0
    exception.SubstLookupRecord = []

    substitution = otTables.ChainContextSubst()
    substitution.Format = 3
    substitution.BacktrackCoverage = substitution.LookAheadCoverage = []
    substitution.BacktrackGlyphCount = substitution.LookAheadGlyphCount = 0
    substitution.InputCoverage = [buildCoverage({cmap[cp] for cp in ZHS_QUOTES}, glyph_map)]
    substitution.InputGlyphCount = 1
    record = otTables.SubstLookupRecord()
    record.SequenceIndex, record.LookupListIndex = 0, target
    substitution.SubstCount = 1
    substitution.SubstLookupRecord = [record]
    return buildLookup([exception, substitution], table="GSUB")


def carry(font: TTFont, ctx) -> None:
    """Append Pretendard JP's CJK lookups and features; Wanted Sans's keep their indices."""
    gsub = font["GSUB"].table
    pgsub = ctx.pretendard["GSUB"].table
    p_rlig = _check_pretendard(pgsub)
    glyphs = set(font.getGlyphOrder())
    names = ctx.pj_names
    pcmap = ctx.pretendard.getBestCmap()

    # Pretendard's relative lookup order, then JAN.
    mappings: dict[str, dict[str, str]] = {"kor": _renamed(_single_mapping(pgsub, PJ_KOR), names, glyphs)}
    for tag, index in PJ_WIDTHS.items():
        mappings[tag] = width_mapping(_single_mapping(pgsub, index), pcmap, ctx.cmap, glyphs)
    for tag, index in PJ_JP.items():
        mappings[tag] = _renamed(_single_mapping(pgsub, index), names, glyphs)
    for index in PJ_KANA:
        mappings[f"kana{index}"] = _renamed(_single_mapping(pgsub, index), names, glyphs)
    mappings["jan"] = {ctx.cmap[cp]: names[pcmap[cp]] for cp in JAN_SHARED}
    if ctx.chinese:
        mappings["zhs_hanzi"] = {ctx.cmap[cp]: f"uni{cp:04X}.zhs" for cp in zhs_forms(ctx)}
        mappings["zhs_punct"] = {
            **mappings["jan"], **{ctx.cmap[cp]: f"uni{cp:04X}.zhs" for cp in ZHS_SIGNS},
        }
    lookups = gsub.LookupList.Lookup
    new: dict[str, int] = {}
    for key, mapping in mappings.items():
        if not mapping:
            raise ValueError(f"carried GSUB lookup {key} is empty")
        new[key] = len(lookups)
        lookups.append(buildLookup([buildSingleSubstSubtable(mapping)], table="GSUB"))
    if ctx.chinese:
        new["zhs_quotes"] = len(lookups)
        lookups.append(_zhs_quotes(ctx.cmap, font.getReverseGlyphMap(), len(lookups) + 1))
        # Only the context lookup references this single substitution; no feature lists it.
        quote_mapping = {ctx.cmap[cp]: f"uni{cp:04X}.zhs" for cp in ZHS_QUOTES}
        lookups.append(buildLookup([buildSingleSubstSubtable(quote_mapping)], table="GSUB"))
    gsub.LookupList.LookupCount = len(lookups)

    records = gsub.FeatureList.FeatureRecord
    feature: dict[str, int] = {}
    for tag, key in (
        ("fwid", "fwid"), ("jp78", "jp78"), ("jp83", "jp83"), ("jp90", "jp90"), ("locl KOR", "kor"),
        ("locl JAN", "jan"), ("nlck", "nlck"), ("pwid", "pwid"), (KOR_SET, "kor"),
    ):
        feature[tag] = len(records)
        records.append(_feature(tag[:4], [new[key]]))
    records[feature[KOR_SET]].Feature.FeatureParams = _stylistic_set_params()
    if ctx.chinese:
        for key, keys in (
            ("locl ZHS hani", ("zhs_hanzi", "zhs_punct", "zhs_quotes")),
            ("locl ZHS common", ("zhs_punct", "zhs_quotes")),
        ):
            feature[key] = len(records)
            records.append(_feature("locl", [new[k] for k in keys]))
    gsub.FeatureList.FeatureCount = len(records)

    scripts = scripts_by_tag(gsub)
    cjk = [feature[tag] for tag in CJK_FEATURES]
    default = list(scripts["DFLT"].DefaultLangSys.FeatureIndex)
    for tag in WIDENED_SCRIPTS:
        ls = scripts[tag].DefaultLangSys
        ls.FeatureIndex = sorted({*ls.FeatureIndex, *cjk})
        ls.FeatureCount = len(ls.FeatureIndex)
    add_scripts(gsub, {tag: new_script(lang_sys(default + cjk)) for tag in CJK_SCRIPTS})
    scripts = scripts_by_tag(gsub)
    add_lang_sys(scripts["hani"], "KOR ", [*scripts["hani"].DefaultLangSys.FeatureIndex, feature["locl KOR"]])
    for tag in JAN_SCRIPTS:
        add_lang_sys(scripts[tag], "JAN ", [*scripts[tag].DefaultLangSys.FeatureIndex, feature["locl JAN"]])

    if ctx.chinese:
        for tag in ZHS_SCRIPTS:
            key = "locl ZHS hani" if tag == "hani" else "locl ZHS common"
            add_lang_sys(scripts[tag], "ZHS ", [*scripts[tag].DefaultLangSys.FeatureIndex, feature[key]])

    rlig = next(i for i, fr in enumerate(records) if fr.FeatureTag == RLIG)
    kana = {p: new[f"kana{p}"] for p in PJ_KANA}
    pj = [(to_roof_t(s), [kana[i] for i in ls]) for s, ls in _variation_records(pgsub, p_rlig)]
    _write_variations(gsub, rlig, merge_variations(_variation_records(gsub, rlig), pj))
    sort_features(gsub)


def _write_variations(gsub, feature: int, merged: list[tuple[float, list[int]]]) -> None:
    template = gsub.FeatureVariations.FeatureVariationRecord[0]
    out = []
    for t, lookups in merged:
        rec = copy.deepcopy(template)
        (cond,) = rec.ConditionSet.ConditionTable
        cond.FilterRangeMinValue, cond.FilterRangeMaxValue = t, 1.0
        (sub,) = rec.FeatureTableSubstitution.SubstitutionRecord
        sub.FeatureIndex = feature
        sub.Feature.LookupListIndex = lookups
        sub.Feature.LookupCount = len(lookups)
        out.append(rec)
    gsub.FeatureVariations.FeatureVariationRecord = out
    gsub.FeatureVariations.FeatureVariationCount = len(out)
