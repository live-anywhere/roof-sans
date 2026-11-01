import pytest
from fontTools.otlLib.builder import buildPairPosClassesSubtable, buildPairPosGlyphsSubtable, buildValue
from fontTools.ttLib.tables import otTables
from fontTools.varLib.builder import buildVarData, buildVarRegionList, buildVarStore
from fontTools.varLib.models import supportScalar

from roofsans.axis import PJ_PEAK, W_MID
from roofsans.features.gdef import VarStoreAppender, append_store, region_key
from roofsans.features.gpos import effective_pairs
from roofsans.features.gsub import (
    _feature,
    add_lang_sys,
    add_scripts,
    lang_sys,
    merge_variations,
    new_script,
    sort_features,
    to_roof_t,
    width_mapping,
)

# Pretendard JP's rlig thresholds (record order) and the Roof lookups each record turns on.
PJ_RECORDS = [
    (0.69244384765625, list(range(89, 98))),
    (0.6905517578125, list(range(89, 97))),
    (0.43963623046875, list(range(89, 96))),
    (0.437744140625, list(range(89, 95))),
    (0.18865966796875, list(range(89, 94))),
    (0.186767578125, list(range(89, 93))),
    (-0.09295654296875, list(range(89, 92))),
    (-0.09576416015625, list(range(89, 91))),
    (-0.47607421875, [89]),
]


def test_fv_conditions_remap():
    assert to_roof_t(0.69244384765625) == pytest.approx((400 + 0.69244384765625 * 530 - 400) / 600, abs=1e-4)
    assert to_roof_t(-0.47607421875) == 0.0
    # Pretendard's 930 master lands on PJ_PEAK; conditions keep their maximum of 1.0.
    assert to_roof_t(1.0) == PJ_PEAK
    assert to_roof_t(0.18865966796875) * 16384 == round(to_roof_t(0.18865966796875) * 16384)


def test_merge_variations_descends_and_adds_wanted_above_its_threshold():
    pj = [(to_roof_t(s), lookups) for s, lookups in PJ_RECORDS]
    merged = merge_variations([(0.41668701171875, [35, 74])], pj)
    ts = [t for t, _ in merged]
    assert ts == sorted(set(ts), reverse=True)
    assert ts[0] == to_roof_t(0.69244384765625) and ts[-1] == 0.0
    by_t = dict(merged)
    assert by_t[ts[0]] == [35, 74, *range(89, 98)]
    assert by_t[0.41668701171875] == [35, 74, *range(89, 96)]
    assert by_t[to_roof_t(0.43963623046875)] == list(range(89, 96))
    # The three negative thresholds clamp to 0; the first of them (77–79) wins.
    assert by_t[0.0] == [89, 90, 91]
    assert len(merged) == 8


def test_width_mapping_goes_through_code_points():
    lookup = {"A": "uniFF21", "Aalt": "uniFF21", "space": "uni3000", "B": "uniFF22"}
    pcmap = {0x41: "A", 0xFF21: "uniFF21", 0x20: "space", 0x3000: "uni3000", 0x42: "B"}
    cmap = {0x41: "A", 0xFF21: "uniFF21.r3", 0x20: "space", 0x3000: "uni3000", 0x42: "B"}
    glyphs = {"A", "uniFF21.r3", "space", "uni3000", "B"}
    # Aalt has no code point and U+FF22 has no Roof glyph, so both entries drop.
    assert width_mapping(lookup, pcmap, cmap, glyphs) == {"A": "uniFF21.r3", "space": "uni3000"}


def test_sort_features_remaps_every_feature_index():
    table = otTables.GSUB()
    table.FeatureList = otTables.FeatureList()
    tags = ["rlig", "locl", "aalt", "locl", "fwid"]
    table.FeatureList.FeatureRecord = [_feature(tag, [i]) for i, tag in enumerate(tags)]
    table.ScriptList = otTables.ScriptList()
    table.ScriptList.ScriptRecord = []
    add_scripts(table, {"DFLT": new_script(lang_sys([0, 2, 4])), "latn": new_script(lang_sys([0, 1]))})
    add_lang_sys(table.ScriptList.ScriptRecord[1].Script, "JAN ", [0, 3])
    table.ScriptList.ScriptRecord[1].Script.DefaultLangSys.ReqFeatureIndex = 1
    table.FeatureVariations = otTables.FeatureVariations()
    rec = otTables.FeatureVariationRecord()
    rec.FeatureTableSubstitution = otTables.FeatureTableSubstitution()
    sub = otTables.FeatureTableSubstitutionRecord()
    sub.FeatureIndex, sub.Feature = 0, _feature("rlig", [9]).Feature
    rec.FeatureTableSubstitution.SubstitutionRecord = [sub]
    table.FeatureVariations.FeatureVariationRecord = [rec]

    sort_features(table)

    records = table.FeatureList.FeatureRecord
    # Same-tag records keep their order: locl (lookup 1) before locl (lookup 3).
    assert [(fr.FeatureTag, fr.Feature.LookupListIndex) for fr in records] == [
        ("aalt", [2]), ("fwid", [4]), ("locl", [1]), ("locl", [3]), ("rlig", [0]),
    ]
    scripts = {sr.ScriptTag: sr.Script for sr in table.ScriptList.ScriptRecord}

    def tags_of(ls):
        return [(records[i].FeatureTag, records[i].Feature.LookupListIndex) for i in ls.FeatureIndex]

    assert tags_of(scripts["DFLT"].DefaultLangSys) == [("aalt", [2]), ("fwid", [4]), ("rlig", [0])]
    assert tags_of(scripts["latn"].DefaultLangSys) == [("locl", [1]), ("rlig", [0])]
    assert tags_of(scripts["latn"].LangSysRecord[0].LangSys) == [("locl", [3]), ("rlig", [0])]
    assert records[scripts["latn"].DefaultLangSys.ReqFeatureIndex].Feature.LookupListIndex == [1]
    assert scripts["DFLT"].DefaultLangSys.ReqFeatureIndex == 0xFFFF
    assert records[sub.FeatureIndex].FeatureTag == "rlig"


def _lookup(*subtables):
    lk = otTables.Lookup()
    lk.LookupType, lk.LookupFlag, lk.SubTable = 2, 0, list(subtables)
    return lk


def test_effective_pairs_follow_subtable_order():
    glyph_map = {g: i for i, g in enumerate(".notdef a b c d".split())}
    first = buildPairPosGlyphsSubtable({("a", "b"): (buildValue({"XAdvance": -10}), None)}, glyph_map)
    classes = buildPairPosClassesSubtable(
        {
            (("a", "c"), ("b",)): (buildValue({"XAdvance": -20}), None),
            (("a", "c"), ("d",)): (buildValue({"XAdvance": -30}), None),
        },
        glyph_map,
    )
    # A later glyph-pair subtable never applies to a first glyph a class subtable covers.
    late = buildPairPosGlyphsSubtable({("c", "a"): (buildValue({"XAdvance": -40}), None)}, glyph_map)
    pairs = effective_pairs(_lookup(first, classes, late), {"a", "b", "c", "d"})
    x = {k: v.XAdvance for k, v in pairs.items()}
    assert x == {("a", "b"): -10, ("a", "d"): -30, ("c", "b"): -20, ("c", "d"): -30}
    # Pairs with a glyph outside ``keep`` are left out.
    assert set(effective_pairs(_lookup(first, classes, late), {"a", "c", "d"})) == {("a", "d"), ("c", "d")}


def test_append_store_keeps_existing_rows_and_shares_regions():
    regions = buildVarRegionList([{"wght": (0.0, W_MID, 1.0)}], ["wght"])
    store = buildVarStore(regions, [buildVarData([0], [[5], [7]])])
    new = VarStoreAppender()
    masters = {0.0: 100, W_MID: 130, 1.0: 160}
    default, dev = new.masters(masters)
    assert default == 100 and dev is not None
    assert new.masters({0.0: 100, W_MID: 100, 1.0: 100}) == (100, None)
    append_store(store, new)
    assert [list(r) for r in store.VarData[0].Item] == [[5], [7]]
    keys = [region_key(r) for r in store.VarRegionList.Region]
    # The existing (0, W_MID, 1) region is reused; only (W_MID, 1, 1) is added.
    assert keys == [((0.0, W_MID, 1.0),), ((W_MID, 1.0, 1.0),)]
    assert store.VarRegionList.RegionCount == 2 and store.VarDataCount == 2
    assert dev.StartSize == 1
    data = store.VarData[dev.StartSize]
    row = data.Item[dev.EndSize]
    for t, value in masters.items():
        scalars = [supportScalar({"wght": t}, {"wght": keys[i][0]}) for i in data.VarRegionIndex]
        assert default + sum(s * d for s, d in zip(scalars, row)) == pytest.approx(value)


@pytest.fixture(scope='module')
def chinese_gsub(ctx, inputs):
    from fontTools.ttLib import TTFont
    from roofsans.assemble import planned_cmap
    from roofsans.features.gsub import carry
    from roofsans.rules import c_hanzi, c_punct, h6_copy

    h6_copy.copy_closure(ctx)
    ctx.cmap = planned_cmap(ctx)
    font = TTFont(inputs.wanted)
    names = set(font.getGlyphOrder()) | set(ctx.pj_names.values()) | set(ctx.cmap.values())
    names.update(f'uni{cp:04X}.zhs' for cp in (*c_hanzi.zhs_forms(ctx), *c_punct.ZHS_SIGNS, *c_punct.ZHS_QUOTES))
    order = font.getGlyphOrder()
    font.setGlyphOrder(order + sorted(names - set(order)))
    carry(font, ctx)
    return font['GSUB'].table


def test_zhs_lookup_order(chinese_gsub):
    lookups = chinese_gsub.LookupList.Lookup
    assert len(lookups) == 103
    mappings = [lookups[i].SubTable[0].mapping for i in (99, 100, 102)]
    assert [len(m) for m in mappings] == [2212, 17, 5]
    assert mappings[0]['uni76F4'] == 'uni76F4.zhs'
    assert mappings[1]['uniFF01'] == 'uniFF01.zhs'
    assert mappings[2]['quotedblleft'] == 'uni201C.zhs'


def test_zhs_quote_context(chinese_gsub, ctx):
    import unicodedata

    lookup = chinese_gsub.LookupList.Lookup[101]
    assert lookup.LookupType == 6 and lookup.LookupFlag == 0
    exception, substitution = lookup.SubTable
    assert exception.Format == substitution.Format == 3
    alnum = {g for cp, g in ctx.cmap.items()
             if cp < 0x3000 and (unicodedata.category(chr(cp)).startswith('L')
                                 or unicodedata.category(chr(cp)) == 'Nd')}
    assert set(exception.BacktrackCoverage[0].glyphs) == alnum
    assert set(exception.LookAheadCoverage[0].glyphs) == alnum
    assert set(exception.InputCoverage[0].glyphs) == {ctx.cmap[0x2019], ctx.cmap[0x00B7]}
    assert exception.SubstCount == 0 and exception.SubstLookupRecord == []
    assert substitution.BacktrackGlyphCount == substitution.LookAheadGlyphCount == 0
    assert set(substitution.InputCoverage[0].glyphs) == {
        ctx.cmap[cp] for cp in (0x2018, 0x2019, 0x201C, 0x201D, 0x00B7)}
    (record,) = substitution.SubstLookupRecord
    assert (record.SequenceIndex, record.LookupListIndex) == (0, 102)
    assert all(102 not in fr.Feature.LookupListIndex for fr in chinese_gsub.FeatureList.FeatureRecord)


def test_zhs_language_systems(chinese_gsub, wanted):
    records = chinese_gsub.FeatureList.FeatureRecord
    assert [fr.FeatureTag for fr in records] == sorted(fr.FeatureTag for fr in records)
    scripts = {sr.ScriptTag: sr.Script for sr in chinese_gsub.ScriptList.ScriptRecord}
    zhs = {tag: next((lr.LangSys for lr in s.LangSysRecord if lr.LangSysTag == 'ZHS '), None)
           for tag, s in scripts.items()}
    assert {tag for tag, ls in zhs.items() if ls is not None} == {'DFLT', 'hani', 'latn'}
    for tag in ('DFLT', 'hani', 'latn'):
        ls = zhs[tag]
        added = set(ls.FeatureIndex) - set(scripts[tag].DefaultLangSys.FeatureIndex)
        assert len(added) == 1
        (index,) = added
        assert records[index].FeatureTag == 'locl'
        assert records[index].Feature.LookupListIndex == ([99, 100, 101] if tag == 'hani' else [100, 101])
    original = wanted['GSUB'].table
    for sr in original.ScriptList.ScriptRecord:
        for lr in sr.Script.LangSysRecord:
            current = next(r.LangSys for r in scripts[sr.ScriptTag].LangSysRecord if r.LangSysTag == lr.LangSysTag)
            assert [records[i].FeatureTag for i in current.FeatureIndex] == [
                original.FeatureList.FeatureRecord[i].FeatureTag for i in lr.LangSys.FeatureIndex]
