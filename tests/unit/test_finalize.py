import re

import pytest
from fontTools.misc.timeTools import timestampFromString

from roofsans.finalize import copyright_lines, wanted_notice, write_license

WANTED_NOTICE = "Copyright \u00a9 2024 Wanted Lab, Inc."

COPYRIGHT_HOLDERS = [
    "The Wanted Sans Project Authors",
    "Kil Hyung-jin",
    "Adobe",
    "The Inter Project Authors",
    "The M+ FONTS Project Authors",
    "Adobe",
]


def test_copyright_lines(inputs):
    lines = copyright_lines(inputs)
    holders = [line for line in lines if line.startswith("Copyright")]
    assert [next(h for h in COPYRIGHT_HOLDERS if h in line) for line in holders] == COPYRIGHT_HOLDERS
    rfn = [line for line in lines if line.startswith("with Reserved Font Name")]
    assert rfn == [
        "with Reserved Font Name 'Pretendard'.",
        "with Reserved Font Name 'Source'.",
        "with Reserved Font Name 'Inter'.",
        "with Reserved Font Name 'M PLUS 1'.",
    ]
    sources = inputs.wanted_ofl.read_text() + inputs.pretendard_license.read_text() + inputs.shs_license.read_text()
    assert len(lines) == 10 and all(line in sources.splitlines() for line in lines)


def test_wanted_notice(inputs):
    assert wanted_notice(inputs) == WANTED_NOTICE


def test_write_license(tmp_path, inputs):
    path = tmp_path / "OFL.txt"
    write_license(path, inputs)
    text = path.read_bytes().decode("utf-8")
    assert "\r" not in text
    sources = [p.read_text(encoding="utf-8") for p in (inputs.wanted_ofl, inputs.pretendard_license, inputs.shs_license)]
    headers = [t[: t.index("This Font Software is licensed")] for t in sources]
    assert WANTED_NOTICE not in headers[0]
    body = sources[0][len(headers[0]) :]
    assert text == f"{WANTED_NOTICE}\n{headers[0]}{headers[1]}{headers[2]}{body}"
    assert "Source is a trademark of Adobe in the United States and/or other countries." in text
    assert text.count("SIL OPEN FONT LICENSE Version 1.1") == 1


def test_write_license_without_chinese(tmp_path, inputs):
    path = tmp_path / "OFL.txt"
    write_license(path, inputs, chinese=False)
    sources = [p.read_text(encoding="utf-8") for p in (inputs.wanted_ofl, inputs.pretendard_license)]
    headers = [text[:text.index("This Font Software is licensed")] for text in sources]
    body = sources[0][len(headers[0]):]
    assert path.read_bytes().decode("utf-8") == f"{WANTED_NOTICE}\n{headers[0]}{headers[1]}{body}"
    assert not any("2014-2025" in line for line in copyright_lines(inputs, chinese=False))


@pytest.mark.acceptance
def test_names(roof):
    n = roof["name"]
    assert n.getDebugName(1) == "Roof Sans" and n.getDebugName(5) == "Version 1.000"
    for rec in n.names:
        if rec.nameID not in (0, 13, 14):
            assert not re.search(r"Pretendard|Source|Inter|M PLUS 1|Wanted Sans", rec.toUnicode())
    assert "Copyright 2014-2025 Adobe (http://www.adobe.com/)" in n.getDebugName(0)
    assert "Reserved Font" not in n.getDebugName(0)
    assert "Copyright 2014-2021 Adobe" in n.getDebugName(0)
    assert "Kil Hyung-jin" in n.getDebugName(0) and "M+ FONTS" in n.getDebugName(0) and "Inter Project" in n.getDebugName(0)


@pytest.mark.acceptance
def test_name_records(roof, inputs):
    n = roof["name"]
    expected = {
        0: " ".join(
            [WANTED_NOTICE, *(line.split(", with Reserved Font", 1)[0].removesuffix(",") for line in copyright_lines(inputs) if not line.startswith("with "))]
        ),
        1: "Roof Sans",
        2: "Regular",
        3: "1.000;ROOF;RoofSans-Regular",
        4: "Roof Sans Regular",
        5: "Version 1.000",
        6: "RoofSans-Regular",
        13: "This Font Software is licensed under the SIL Open Font License, Version 1.1.",
        14: "https://openfontlicense.org",
        25: "RoofSans",
    }
    low = {rec.nameID for rec in n.names if rec.nameID < 256}
    assert low == set(expected)
    for name_id, value in expected.items():
        assert {rec.toUnicode() for rec in n.names if rec.nameID == name_id} == {value}, name_id
    fvar = roof["fvar"]
    assert [n.getDebugName(i.postscriptNameID) for i in fvar.instances] == [
        f"RoofSans-{style}" for style in ("Regular", "Medium", "SemiBold", "Bold", "ExtraBold", "Black", "ExtraBlack")
    ]
    assert not [rec for rec in n.names if rec.nameID != 0 and "Wanted" in rec.toUnicode()]


@pytest.mark.acceptance
def test_head(roof):
    head = roof["head"]
    stamp = timestampFromString("Sat Oct 31 00:00:00 2026")
    assert head.fontRevision == 1.0 and head.created == head.modified == stamp


@pytest.mark.acceptance
def test_os2(roof, wanted):
    o, w = roof["OS/2"], wanted["OS/2"]
    assert o.achVendID == "ROOF"
    assert o.getCodePageRanges() == w.getCodePageRanges() | {17, 18}
    # Hiragana (49), CJK Unified Ideographs (59), Enclosed Alphanumerics (42): Roof adds kana and Han.
    assert {42, 49, 59} <= o.getUnicodeRanges()
    widths = [width for width, _ in roof["hmtx"].metrics.values() if width > 0]
    assert o.xAvgCharWidth == round(sum(widths) / len(widths)) != w.xAvgCharWidth


@pytest.mark.acceptance
def test_kor_set_ui_name(roof, pretendard):
    def ui_names(font):
        gsub, name = font["GSUB"].table, font["name"]
        out = {}
        for fr in gsub.FeatureList.FeatureRecord:
            if fr.FeatureTag.startswith("ss") and fr.Feature.FeatureParams is not None:
                params = fr.Feature.FeatureParams
                out[fr.FeatureTag] = (params.Version, {rec.toUnicode() for rec in name.names if rec.nameID == params.UINameID})
        return out

    roof_names = ui_names(roof)
    # Pretendard's ss05 is the set Roof carries as ss20; its UI name comes along.
    assert roof_names["ss20"] == (0, {"Korean localization"}) == ui_names(pretendard)["ss05"]
    assert len(roof_names) == 17
    ids = [fr.Feature.FeatureParams.UINameID for fr in roof["GSUB"].table.FeatureList.FeatureRecord if fr.FeatureTag.startswith("ss")]
    assert len(set(ids)) == len(ids)


@pytest.mark.acceptance
def test_metrics(roof):
    h, o = roof["hhea"], roof["OS/2"]
    assert (h.ascent, h.descent, h.lineGap) == (1950, -494, 0)
    assert (o.sTypoAscender, o.sTypoDescender, o.sTypoLineGap, o.usWinAscent, o.usWinDescent) == (1752, -296, 0, 1950, 494)
    assert not o.fsSelection & (1 << 7) and (o.sxHeight, o.sCapHeight) == (1032, 1448)
    a = roof["fvar"].axes[0]
    assert (a.axisTag, a.minValue, a.defaultValue, a.maxValue) == ("wght", 400, 400, 1000)


def test_build_fails_on_missing_planned_glyph(monkeypatch, tmp_path, inputs):
    from roofsans import build
    from roofsans.rules import h6_copy

    monkeypatch.setattr(build, "CONTRIBUTORS", (h6_copy,))
    with pytest.raises(ValueError, match=r"no glyph for \d+ planned code points \(.*H4_LETTER: \d+"):
        build.build(tmp_path / "RoofSansVariable.ttf", inputs)
    assert not (tmp_path / "RoofSansVariable.ttf").exists()
