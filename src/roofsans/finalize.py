"""Roof Sans names, head and OS/2 fields, and the combined OFL license text."""

from __future__ import annotations

import re
from pathlib import Path

from fontTools.misc.timeTools import timestampFromString
from fontTools.ttLib import TTFont

from roofsans.features.gsub import KOR_SET, kor_set_name
from roofsans.inputs import Inputs

OFL_BODY_START = "This Font Software is licensed"
RFN_PREFIX = "with Reserved Font Name"
TIMESTAMP = timestampFromString("Sat Oct 31 00:00:00 2026")
JIS_CODE_PAGE = 17
GB_CODE_PAGE = 18

MAC = (1, 0, 0)
WINDOWS = (3, 1, 0x409)
# Each name ID with the platforms Wanted Sans writes it on.
NAME_PLATFORMS = {**{i: (MAC, WINDOWS) for i in (0, 1, 2, 3, 4, 5, 6, 7, 13, 14)}, 25: (WINDOWS,)}
# Roof Sans 1.3.0: 1.200 without Wanted Sans's logo glyphs and `liga`, with the upstream
# trademark notices and LiveAnywhere's copyright line (build notes section 15).
VERSION = "1.300"
# LiveAnywhere's notice for its changes, after the upstream lines as the OFL header template
# places an added copyright holder. It adds no Reserved Font Name.
ROOF_COPYRIGHT = "Copyright 2026 LiveAnywhere Inc. (https://github.com/live-anywhere/roof-sans)"
# Name ID 7 separates notices with line breaks (Wanted Sans) or semicolons (Pretendard JP).
_NOTICE_SPLIT = re.compile(r"\n|; ")
_RFN_CLAUSE = re.compile(r",?\s*with\s+Reserved\s+Font\s+Name\s+'[^']*'\.?")
_COPYRIGHT_MARK = re.compile(r"Copyright|©|\(c\)")


def _split(path: Path) -> tuple[str, str]:
    """A license file's header (every line before the OFL body) and its OFL body."""
    text = path.read_text(encoding="utf-8")
    start = text.index(OFL_BODY_START)
    return text[:start], text[start:]


def font_notice(path: Path) -> str:
    """An input font's own copyright notice, its name ID 0."""
    return TTFont(path, lazy=True)["name"].getDebugName(0)


def wanted_notice(inputs: Inputs) -> str:
    """Wanted Sans's own copyright notice, its name ID 0."""
    return font_notice(inputs.wanted)


def _core(text: str) -> str:
    """A notice's years and holder: no "Copyright", "©", "(c)", Reserved Font Name clause, or line breaks."""
    text = _RFN_CLAUSE.sub("", text)
    text = _COPYRIGHT_MARK.sub(" ", text)
    return " ".join(text.split())


def states(header: str, notice: str) -> bool:
    """Whether a license header already gives ``notice``'s years and holder."""
    return _core(notice) in _core(header)


def _sources(inputs: Inputs, chinese: bool = True) -> list[tuple[Path, Path]]:
    """(font, license file) for each input whose glyphs ship, in license order."""
    sources = [(inputs.wanted, inputs.wanted_ofl), (inputs.pretendard, inputs.pretendard_license)]
    if chinese:
        sources.append((inputs.shs_cn, inputs.shs_license))
    return sources


def _notice_and_header(font: Path, license_file: Path) -> tuple[str | None, str]:
    """The font's own notice when its license header does not state it, and that header.

    Wanted Sans's name ID 0 names Wanted Lab, Inc., and Pretendard JP's has the year 2023,
    which their license files lack; Source Han Sans's matches its license file.
    """
    header = _split(license_file)[0]
    notice = font_notice(font)
    return (None if states(header, notice) else notice), header


def copyright_lines(inputs: Inputs, chinese: bool = True) -> list[str]:
    """Every upstream ``Copyright`` line and its reserved-font-name line, verbatim."""
    paths = (inputs.wanted_ofl, inputs.pretendard_license)
    if chinese:
        paths += (inputs.shs_license,)
    return [
        line
        for path in paths
        for line in _split(path)[0].splitlines()
        if line.startswith("Copyright") or line.startswith(RFN_PREFIX)
    ]


def trademark_notices(inputs: Inputs, chinese: bool = True) -> list[str]:
    """Every trademark notice in the input fonts' name ID 7, one sentence each, first use first.

    The OFL grants no trademark rights, and the OFL FAQ (3.7) asks derivatives to keep these.
    """
    paths = (inputs.wanted, inputs.pretendard) + ((inputs.shs_cn,) if chinese else ())
    notices: list[str] = []
    for path in paths:
        text = TTFont(path, lazy=True)["name"].getDebugName(7) or ""
        for part in _NOTICE_SPLIT.split(text):
            sentence = part.strip()
            if sentence and not sentence.endswith("."):
                sentence += "."
            if sentence and sentence not in notices:
                notices.append(sentence)
    return notices


def write_license(path: Path, inputs: Inputs, chinese: bool = True) -> None:
    """Write each source's license header verbatim, led by the font's own notice when the header
    lacks it, then LiveAnywhere's line, the trademark notices the headers lack, and Wanted's OFL 1.1 body."""
    body = _split(inputs.wanted_ofl)[1]
    parts = []
    for font, license_file in _sources(inputs, chinese=chinese):
        notice, header = _notice_and_header(font, license_file)
        parts.append(f"{notice}\n{header}" if notice else header)
    header = f"{''.join(parts)}{ROOF_COPYRIGHT}\n\n"
    missing = [t for t in trademark_notices(inputs, chinese=chinese) if t not in header]
    marks = "".join(f"{t}\n" for t in missing) + ("\n" if missing else "")
    path.write_text(f"{header}{marks}{body}", encoding="utf-8", newline="\n")


def copyright_notice(inputs: Inputs, chinese: bool = True) -> str:
    """Name ID 0: per source, the font's own notice if its header lacks it, then the header's
    ``Copyright`` lines without their Reserved Font Name clauses; LiveAnywhere's line last."""
    notices = []
    for font, license_file in _sources(inputs, chinese=chinese):
        notice, header = _notice_and_header(font, license_file)
        notices += [notice] if notice else []
        # Source Han Sans's RFN clause wraps onto the next line in its license header.
        notices += [
            line.split(", with Reserved Font", 1)[0].removesuffix(",")
            for line in header.splitlines() if line.startswith("Copyright")
        ]
    return " ".join([*notices, ROOF_COPYRIGHT])


def _names(inputs: Inputs, chinese: bool = True) -> dict[int, str]:
    return {
        0: copyright_notice(inputs, chinese=chinese),
        1: "Roof Sans",
        2: "Regular",
        3: f"{VERSION};ROOF;RoofSans-Regular",
        4: "Roof Sans Regular",
        5: f"Version {VERSION}",
        6: "RoofSans-Regular",
        7: " ".join(trademark_notices(inputs, chinese=chinese)),
        13: "This Font Software is licensed under the SIL Open Font License, Version 1.1.",
        14: "https://openfontlicense.org",
        25: "RoofSans",
    }


def _rename(font: TTFont, inputs: Inputs, chinese: bool = True) -> None:
    """Replace every name below 256 and rename Wanted Sans in the instance and STAT names."""
    name = font["name"]
    name.names = [rec for rec in name.names if rec.nameID >= 256]
    for rec in name.names:
        text = rec.toUnicode()
        renamed = text.replace("WantedSansVariable", "RoofSans").replace("Wanted Sans", "Roof Sans")
        if renamed != text:
            rec.string = renamed
    for name_id, text in _names(inputs, chinese=chinese).items():
        for platform in NAME_PLATFORMS[name_id]:
            name.setName(text, name_id, *platform)


def _name_kor_set(font: TTFont, pretendard: TTFont) -> None:
    """Write ``ss20``'s UI name on Windows, like Wanted Sans's ``ss01``–``ss16`` names."""
    (params,) = (
        fr.Feature.FeatureParams for fr in font["GSUB"].table.FeatureList.FeatureRecord if fr.FeatureTag == KOR_SET
    )
    params.UINameID = font["name"].addName(kor_set_name(pretendard), platforms=(WINDOWS,), minNameID=256)


def finalize(font: TTFont, ctx) -> None:
    _rename(font, ctx.inputs, chinese=ctx.chinese)
    _name_kor_set(font, ctx.pretendard)
    head = font["head"]
    head.fontRevision = float(VERSION)
    head.created = head.modified = TIMESTAMP
    os2 = font["OS/2"]
    os2.achVendID = "ROOF"
    os2.recalcUnicodeRanges(font)
    os2.recalcAvgCharWidth(font)
    code_pages = {JIS_CODE_PAGE}
    if ctx.chinese:
        code_pages.add(GB_CODE_PAGE)
    os2.setCodePageRanges(os2.getCodePageRanges() | code_pages)
