"""Acceptance 2: glyphs copied from Pretendard JP keep its outlines and advances."""

import pytest
from copies import COPY_WEIGHTS, differing_copies, outline, pj_names  # noqa: F401 (fixture)

pytestmark = pytest.mark.acceptance

# Design selection rule 2: the Han and Japanese blocks (Han, kana, and Japanese punctuation).
HAN_JP_BLOCKS = (
    (0x2E80, 0x2FDF), (0x3000, 0x30FF), (0x31F0, 0x31FF), (0x3200, 0x33FF),
    (0x3400, 0x4DBF), (0x4E00, 0x9FFF), (0xF900, 0xFAFF), (0xFF00, 0xFFEF),
    (0x20000, 0x2FFFF),
)


@pytest.mark.parametrize("wght, tolerance", COPY_WEIGHTS)
def test_copies_match_pretendard(static, pj_names, wght, tolerance):
    bad = differing_copies(static("pretendard", wght), static("roof", wght), pj_names.items(), tolerance, advance_tolerance=tolerance if wght < 400 else 0,
                           composite_tolerance=1.5 if wght < 400 else None)
    assert not bad, f"{len(bad)} copies differ at {wght}: {bad[:10]}"


def test_han_and_kana_hold_930_shape(static, roof, pj_names):
    encoded: dict[str, list[int]] = {}
    for cp, name in roof.getBestCmap().items():
        encoded.setdefault(name, []).append(cp)
    held = [
        name for name in pj_names.values()
        if all(any(lo <= cp <= hi for lo, hi in HAN_JP_BLOCKS) for cp in encoded.get(name, ()))
    ]
    assert len(held) == len(pj_names)
    a, b = static("roof", 930), static("roof", 1000)
    bad = [name for name in held if outline(a, name) != outline(b, name)]
    assert not bad, f"{len(bad)} copies move past 930: {bad[:10]}"


@pytest.mark.parametrize("wght", [100, 250, 400, 700, 930])
def test_carried_kerning_matches_pretendard(roof, pretendard, inputs, pj_names, wght):  # noqa: F811
    """The Pretendard kerning carried between copies equals Pretendard's own at the same weight,
    below 400 too (its light deltas are scaled onto Roof's light region)."""
    import uharfbuzz as hb
    from fontTools.varLib.varStore import VarStoreInstancer

    from roofsans.axis import roof_norm

    copies = set(pj_names.values())
    store = VarStoreInstancer(roof["GDEF"].table.VarStore, roof["fvar"].axes, {"wght": roof_norm(wght)})
    first_cp: dict[str, int] = {}
    for cp, name in sorted(pretendard.getBestCmap().items()):
        first_cp.setdefault(name, cp)
    source = {roof_name: pj for pj, roof_name in pj_names.items()}
    font = hb.Font(hb.Face(hb.Blob.from_file_path(str(inputs.pretendard))))
    font.set_variations({"wght": wght})

    def advance(text: str) -> int:
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(font, buf, {"kern": True})
        return buf.glyph_positions[0].x_advance

    pairs, bad = 0, []
    for lookup in roof["GPOS"].table.LookupList.Lookup:
        for st in lookup.SubTable:
            st = getattr(st, "ExtSubTable", st)
            if st.LookupType != 2 or st.Format != 1 or not set(st.Coverage.glyphs) <= copies:
                continue
            for first, pair_set in zip(st.Coverage.glyphs, st.PairSet):
                for record in pair_set.PairValueRecord:
                    a, b = first_cp.get(source[first]), first_cp.get(source[record.SecondGlyph])
                    if a is None or b is None:
                        continue
                    value = record.Value1
                    got = (value.XAdvance or 0) + (
                        store[(value.XAdvDevice.StartSize << 16) | value.XAdvDevice.EndSize]
                        if getattr(value, "XAdvDevice", None) is not None else 0
                    )
                    want = advance(chr(a) + chr(b)) - advance(chr(a))
                    pairs += 1
                    if abs(got - want) > 1:
                        bad.append((first, record.SecondGlyph, got, want))
    assert pairs >= 5
    assert not bad, bad
