"""Build the Roof Sans specimen web page, the site GitHub Pages serves.

``specimen.html`` is the page source. This script writes the built font as
``RoofSansVariable.woff2`` next to the page, fills in the language lists from
``languages.json`` and the version, release, and file-size markers, and writes
``index.html``. Before writing, it checks that the coverage numbers the page states still
hold for the font; if the font changed, it stops and names the numbers to update in
``specimen.html``.

The page loads the font file by a relative URL, so open it through a web server:

    uv run python site/build_site.py --out build/site
    uv run python -m http.server -d build/site 8000
"""

from __future__ import annotations

import argparse
import html
import json
import re
import tomllib
from pathlib import Path

from fontTools.ttLib import TTFont

from roofsans.chinese import gb2312_levels

SITE_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = SITE_DIR / "specimen.html"
LANGUAGES_PATH = SITE_DIR / "languages.json"
DEFAULT_ROOF = SITE_DIR.parent / "fonts" / "RoofSansVariable.ttf"
PYPROJECT_PATH = SITE_DIR.parent / "pyproject.toml"
# The page's @font-face and preload link use this file name.
WOFF2_NAME = "RoofSansVariable.woff2"

# Numbers the page states, as (covered, total). Keep them in sync with specimen.html.
PAGE_FACTS = {
    "code points": (24978, None),
    "glyphs": (28404, None),
    # The page's axis range, sliders, weights tab counter, and "이름 있는 굵기 7개" (Regular 400 … ExtraBlack 1000).
    "wght minimum": (400, None),
    "wght maximum": (1000, None),
    "named weights": (7, None),
    "Hangul syllables": (11172, 11172),
    "KS X 1001 hanja": (4888, 4888),
    "JIS X 0208 level 1 kanji": (2965, 2965),
    "JIS X 0208 level 2 kanji": (3390, 3390),
    "GB 2312 level 1 hanzi": (3755, 3755),
    "GB 2312 level 2 hanzi": (3008, 3008),
    "Big5 frequent hanzi": (5034, 5401),
}
# Language counts the page states, per Hyperglot script name.
PAGE_LANGUAGE_COUNTS = {"Latin": 483, "Cyrillic": 77}


def _is_han(cp: int) -> bool:
    return 0x3400 <= cp <= 0x9FFF or 0xF900 <= cp <= 0xFAFF or 0x20000 <= cp <= 0x2FFFF


def _double_byte_set(codec: str, lead_bytes: range, trail_bytes) -> set[int]:
    """Code points of the single characters a double-byte codec encodes in these rows."""
    chars = set()
    for lead in lead_bytes:
        for trail in trail_bytes:
            try:
                text = bytes([lead, trail]).decode(codec)
            except UnicodeDecodeError:
                continue
            if len(text) == 1:
                chars.add(ord(text))
    return chars


def measure_facts(font: TTFont) -> dict[str, tuple[int, int | None]]:
    cmap = set(font.getBestCmap())
    euc_trail = range(0xA1, 0xFF)
    big5_trail = list(range(0x40, 0x7F)) + list(range(0xA1, 0xFF))
    sets = {
        "Hangul syllables": set(range(0xAC00, 0xD7A4)),
        "KS X 1001 hanja": _double_byte_set("euc_kr", range(0xCA, 0xFE), euc_trail),
        "JIS X 0208 level 1 kanji": _double_byte_set("euc_jp", range(0xB0, 0xD0), euc_trail),
        "JIS X 0208 level 2 kanji": _double_byte_set("euc_jp", range(0xD0, 0xF5), euc_trail),
        "GB 2312 level 1 hanzi": set(gb2312_levels()[0]),
        "GB 2312 level 2 hanzi": set(gb2312_levels()[1]),
        "Big5 frequent hanzi": _double_byte_set("big5", range(0xA4, 0xC7), big5_trail),
    }
    (axis,) = (a for a in font["fvar"].axes if a.axisTag == "wght")
    facts: dict[str, tuple[int, int | None]] = {
        "code points": (len(cmap), None),
        "glyphs": (len(font.getGlyphOrder()), None),
        "wght minimum": (round(axis.minValue), None),
        "wght maximum": (round(axis.maxValue), None),
        "named weights": (len(font["fvar"].instances), None),
    }
    for name, chars in sets.items():
        han = {cp for cp in chars if name == "Hangul syllables" or _is_han(cp)}
        facts[name] = (len(han & cmap), len(han))
    return facts


def stale_facts(font: TTFont, languages: dict) -> list[str]:
    """Describe every number on the page that no longer matches the font or language data."""
    problems = []
    for name, measured in measure_facts(font).items():
        if measured != PAGE_FACTS[name]:
            problems.append(f"{name}: page says {PAGE_FACTS[name]}, font has {measured}")
    for script, count in PAGE_LANGUAGE_COUNTS.items():
        listed = len(languages["scripts"][script])
        if listed != count:
            problems.append(f"{script} languages: page says {count}, languages.json lists {listed}")
    return problems


def package_version() -> str:
    """The package version, which names the release tag (``v`` + version)."""
    return tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))["project"]["version"]


def font_version(font: TTFont) -> str:
    """The version in the font's name table, such as ``1.200`` from ``Version 1.200``."""
    return font["name"].getDebugName(5).removeprefix("Version ").split(";")[0].strip()


def megabytes(size: int) -> str:
    """Three significant figures in decimal megabytes, as the README states file sizes."""
    mb = size / 1_000_000
    return f"{mb:.1f} MB" if mb >= 10 else f"{mb:.2f} MB"


def write_woff2(font_path: Path, out: Path) -> None:
    """Write the font as WOFF2 the way ``roofsans-web`` writes its single file, so the page's
    file is byte-identical to ``dist/web/woff2/RoofSansVariable.woff2`` and the release asset."""
    font = TTFont(font_path, recalcTimestamp=False)
    font.flavor = "woff2"
    font.save(out)


def build_site(roof: Path, out_dir: Path) -> Path:
    languages = json.loads(LANGUAGES_PATH.read_text(encoding="utf-8"))
    font = TTFont(roof)
    problems = stale_facts(font, languages)
    if problems:
        raise SystemExit(
            "specimen.html states numbers that no longer match the font. Update the page text and "
            "PAGE_FACTS in site/build_site.py (and regenerate languages.json with Hyperglot if the "
            "language counts changed):\n  " + "\n  ".join(problems)
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    woff2 = out_dir / WOFF2_NAME
    write_woff2(roof, woff2)
    page = TEMPLATE_PATH.read_text(encoding="utf-8")
    replacements = {
        "__LATIN_LIST__": ", ".join(html.escape(n) for n in languages["scripts"]["Latin"]),
        "__CYRILLIC_LIST__": ", ".join(html.escape(n) for n in languages["scripts"]["Cyrillic"]),
        "__RELEASE_TAG__": f"v{package_version()}",
        "__FONT_VERSION__": font_version(font),
        "__TTF_SIZE__": megabytes(roof.stat().st_size),
        "__WOFF2_SIZE__": megabytes(woff2.stat().st_size),
    }
    for marker, value in replacements.items():
        if marker not in page:
            raise SystemExit(f"specimen.html must contain {marker}")
        page = page.replace(marker, value)
    leftover = sorted(set(re.findall(r"__[A-Z0-9_]+__", page)))
    if leftover:
        raise SystemExit(f"specimen.html has markers build_site.py does not fill: {', '.join(leftover)}")
    out = out_dir / "index.html"
    out.write_text(page, encoding="utf-8", newline="\n")
    return out


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build the Roof Sans specimen page and its font file.")
    parser.add_argument("--font", type=Path, default=DEFAULT_ROOF, help="built font to publish with the page")
    parser.add_argument("--out", type=Path, default=Path("build/site"), help="output directory")
    args = parser.parse_args(argv)
    print(build_site(args.font, args.out))


if __name__ == "__main__":
    main()
