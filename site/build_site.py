"""Build the Roof Sans specimen web page as one self-contained HTML file.

``specimen.html`` is the page source. This script embeds the built font as WOFF2, fills
in the language lists from ``languages.json``, and writes ``index.html``. Before writing,
it checks that the coverage numbers the page states still hold for the font; if the
font changed, it stops and names the numbers to update in ``specimen.html``.

Usage: ``uv run python site/build_site.py --out build/site``
"""

from __future__ import annotations

import argparse
import base64
import html
import io
import json
from pathlib import Path

from fontTools.ttLib import TTFont

SITE_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = SITE_DIR / "specimen.html"
LANGUAGES_PATH = SITE_DIR / "languages.json"
DEFAULT_ROOF = SITE_DIR.parent / "fonts" / "RoofSansVariable.ttf"

# Numbers the page states, as (covered, total). Keep them in sync with specimen.html.
PAGE_FACTS = {
    "code points": (21718, None),
    "glyphs": (22923, None),
    "Hangul syllables": (11172, 11172),
    "KS X 1001 hanja": (4888, 4888),
    "JIS X 0208 level 1 kanji": (2965, 2965),
    "JIS X 0208 level 2 kanji": (3390, 3390),
    "GB 2312 level 1 hanzi": (2420, 3755),
    "Big5 frequent hanzi": (4611, 5401),
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
        "GB 2312 level 1 hanzi": _double_byte_set("gb2312", range(0xB0, 0xD8), euc_trail),
        "Big5 frequent hanzi": _double_byte_set("big5", range(0xA4, 0xC7), big5_trail),
    }
    facts: dict[str, tuple[int, int | None]] = {
        "code points": (len(cmap), None),
        "glyphs": (len(font.getGlyphOrder()), None),
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


def woff2_base64(font_path: Path) -> str:
    font = TTFont(font_path)
    font.flavor = "woff2"
    buffer = io.BytesIO()
    font.save(buffer, reorderTables=False)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def build_site(roof: Path, out_dir: Path) -> Path:
    languages = json.loads(LANGUAGES_PATH.read_text(encoding="utf-8"))
    problems = stale_facts(TTFont(roof), languages)
    if problems:
        raise SystemExit(
            "specimen.html states numbers that no longer match the font. Update the page text and "
            "PAGE_FACTS in site/build_site.py (and regenerate languages.json with Hyperglot if the "
            "language counts changed):\n  " + "\n  ".join(problems)
        )
    page = TEMPLATE_PATH.read_text(encoding="utf-8")
    replacements = {
        "__FONT_DATA__": woff2_base64(roof),
        "__LATIN_LIST__": ", ".join(html.escape(n) for n in languages["scripts"]["Latin"]),
        "__CYRILLIC_LIST__": ", ".join(html.escape(n) for n in languages["scripts"]["Cyrillic"]),
    }
    for marker, value in replacements.items():
        if page.count(marker) != 1:
            raise SystemExit(f"specimen.html must contain {marker} exactly once")
        page = page.replace(marker, value)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "index.html"
    out.write_text(page, encoding="utf-8", newline="\n")
    return out


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build the self-contained Roof Sans specimen page.")
    parser.add_argument("--font", type=Path, default=DEFAULT_ROOF, help="built font to embed")
    parser.add_argument("--out", type=Path, default=Path("build/site"), help="output directory")
    args = parser.parse_args(argv)
    print(build_site(args.font, args.out))


if __name__ == "__main__":
    main()
