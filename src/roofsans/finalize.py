"""Roof Sans names, head and OS/2 fields, and the combined OFL license text."""

from __future__ import annotations

from pathlib import Path

from fontTools.misc.timeTools import timestampFromString
from fontTools.ttLib import TTFont

from roofsans.features.gsub import KOR_SET, kor_set_name
from roofsans.inputs import Inputs

OFL_BODY_START = "This Font Software is licensed"
RFN_PREFIX = "with Reserved Font Name"
TIMESTAMP = timestampFromString("Sat Oct 31 00:00:00 2026")
JIS_CODE_PAGE = 17

MAC = (1, 0, 0)
WINDOWS = (3, 1, 0x409)
# Each name ID with the platforms Wanted Sans writes it on.
NAME_PLATFORMS = {**{i: (MAC, WINDOWS) for i in (0, 1, 2, 3, 4, 5, 6, 13, 14)}, 25: (WINDOWS,)}


def _split(path: Path) -> tuple[str, str]:
    """A license file's header (every line before the OFL body) and its OFL body."""
    text = path.read_text(encoding="utf-8")
    start = text.index(OFL_BODY_START)
    return text[:start], text[start:]


def wanted_notice(inputs: Inputs) -> str:
    """Wanted Sans's own copyright notice, its name ID 0."""
    return TTFont(inputs.wanted, lazy=True)["name"].getDebugName(0)


def copyright_lines(inputs: Inputs) -> list[str]:
    """Every upstream ``Copyright`` line and its reserved-font-name line, verbatim."""
    return [
        line
        for path in (inputs.wanted_ofl, inputs.pretendard_license)
        for line in _split(path)[0].splitlines()
        if line.startswith("Copyright") or line.startswith(RFN_PREFIX)
    ]


def write_license(path: Path, inputs: Inputs) -> None:
    """Write Wanted's binary notice, both sources' license headers verbatim, then Wanted's OFL 1.1 body."""
    wanted_header, body = _split(inputs.wanted_ofl)
    pretendard_header, _ = _split(inputs.pretendard_license)
    notice = wanted_notice(inputs)
    lead = "" if notice in wanted_header else f"{notice}\n"
    path.write_text(f"{lead}{wanted_header}{pretendard_header}{body}", encoding="utf-8", newline="\n")


def _names(inputs: Inputs) -> dict[int, str]:
    holders = [line.removesuffix(",") for line in copyright_lines(inputs) if not line.startswith(RFN_PREFIX)]
    return {
        0: " ".join([wanted_notice(inputs), *holders]),
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


def _rename(font: TTFont, inputs: Inputs) -> None:
    """Replace every name below 256 and rename Wanted Sans in the instance and STAT names."""
    name = font["name"]
    name.names = [rec for rec in name.names if rec.nameID >= 256]
    for rec in name.names:
        text = rec.toUnicode()
        renamed = text.replace("WantedSansVariable", "RoofSans").replace("Wanted Sans", "Roof Sans")
        if renamed != text:
            rec.string = renamed
    for name_id, text in _names(inputs).items():
        for platform in NAME_PLATFORMS[name_id]:
            name.setName(text, name_id, *platform)


def _name_kor_set(font: TTFont, pretendard: TTFont) -> None:
    """Write ``ss20``'s UI name on Windows, like Wanted Sans's ``ss01``–``ss16`` names."""
    (params,) = (
        fr.Feature.FeatureParams for fr in font["GSUB"].table.FeatureList.FeatureRecord if fr.FeatureTag == KOR_SET
    )
    params.UINameID = font["name"].addName(kor_set_name(pretendard), platforms=(WINDOWS,), minNameID=256)


def finalize(font: TTFont, ctx) -> None:
    _rename(font, ctx.inputs)
    _name_kor_set(font, ctx.pretendard)
    head = font["head"]
    head.fontRevision = 1.0
    head.created = head.modified = TIMESTAMP
    os2 = font["OS/2"]
    os2.achVendID = "ROOF"
    os2.recalcUnicodeRanges(font)
    os2.recalcAvgCharWidth(font)
    os2.setCodePageRanges(os2.getCodePageRanges() | {JIS_CODE_PAGE})
