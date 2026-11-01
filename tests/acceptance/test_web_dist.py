"""The web build: the dynamic subset must cover the font and shape like it.

A browser shapes each run of characters with the subset file that holds them. The
shaping tests split each sample the same way and compare the glyphs and positions
with the full font. The samples avoid the known cross-file limits listed in
docs/ROOF_SANS_WEB_DISTRIBUTION.md.
"""

import hashlib
import io
import os
import re
from functools import cache
from pathlib import Path

import pytest
import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.unicodedata import mirrored

from roofsans import web
from roofsans.inputs import ensure_files

COMMITTED_FONT = Path("fonts/RoofSansVariable.ttf")
COMMITTED_WEB = Path("dist/web")
FACE_RE = re.compile(r"src: url\('\./([^']+)'\) format\('woff2'\);\n  unicode-range: ([^;]+);")


@pytest.fixture(scope="session")
def web_dir(roof_path):
    """A web build of the font under test, or ``$ROOF_WEB`` when set."""
    if os.environ.get("ROOF_WEB"):
        return Path(os.environ["ROOF_WEB"])
    slicings = web.load_slicings(ensure_files(set(web.SLICING_ORDER)))
    return web.build_web(roof_path, slicings, Path("build/test-web")).out_dir


@pytest.fixture(scope="session")
def faces(web_dir):
    """(file, code points) for each @font-face of the dynamic subset CSS."""
    css = (web_dir / web.SUBSET_CSS).read_text(encoding="utf-8")
    return [(web_dir / url, web.parse_unicode_range(rng)) for url, rng in FACE_RE.findall(css)]


@pytest.fixture(scope="session")
def chunk_of(faces):
    return {cp: path for path, cps in faces for cp in cps}


@cache
def sfnt(path: Path) -> bytes:
    font = TTFont(path)
    font.flavor = None
    out = io.BytesIO()
    font.save(out)
    return out.getvalue()


def shape(data: bytes, cps: list[int], start: int, end: int, script: str, lang: str, wght: float):
    font = hb.Font(hb.Face(data))
    font.set_variations({"wght": wght})
    buf = hb.Buffer()
    buf.add_codepoints(cps, start, end - start)
    buf.direction, buf.script, buf.language = "ltr", script, lang
    hb.shape(font, buf)
    return [
        (font.glyph_to_string(i.codepoint), i.cluster, p.x_advance, p.x_offset, p.y_offset)
        for i, p in zip(buf.glyph_infos, buf.glyph_positions)
    ]


def is_variation_selector(cp: int) -> bool:
    return 0xFE00 <= cp <= 0xFE0F or 0xE0100 <= cp <= 0xE01EF


def shape_split(chunk_of, text: str, script: str, lang: str, wght: float):
    """Shape ``text`` as a browser would with the dynamic subset: one run per file.

    A variation selector stays in the run of the character before it.
    """
    cps = [ord(c) for c in text]
    files = []
    for cp in cps:
        files.append(files[-1] if is_variation_selector(cp) and files else chunk_of[cp])
    out, start = [], 0
    for end in range(1, len(cps) + 1):
        if end == len(cps) or files[end] != files[start]:
            out += shape(sfnt(files[start]), cps, start, end, script, lang, wght)
            start = end
    return out


def uvs_entries(font: TTFont) -> list[tuple[int, int, str | None]]:
    """(selector, base, glyph name or None for the default glyph) for every variation sequence."""
    return sorted(
        (selector, base, glyph)
        for table in font["cmap"].tables if table.format == 14
        for selector, entries in table.uvsDict.items()
        for base, glyph in entries
    )


def test_subset_files_partition_the_font(roof, faces, web_dir):
    cmap = roof.getBestCmap()
    claimed = [cp for _, cps in faces for cp in cps]
    assert len(claimed) == len(set(claimed)), "a code point is in two @font-face rules"
    assert set(claimed) == set(cmap)
    files = sorted((web_dir / web.SUBSET_DIR).glob("*.woff2"))
    assert sorted(path for path, _ in faces) == files


def test_each_subset_file_holds_exactly_its_range(roof, faces):
    """Each file maps its range, plus the bidi mirror of a bracket in it (fontTools' bidi closure)."""
    axis = roof["fvar"].axes[0]
    full = set(roof.getBestCmap())
    for path, cps in faces:
        font = TTFont(path)
        mirrors = {m for cp in cps if (m := mirrored(cp)) is not None} & full
        assert set(font.getBestCmap()) == cps | mirrors, path.name
        assert {"fvar", "gvar", "STAT"} <= set(font.keys()), path.name
        (a,) = font["fvar"].axes
        assert (a.axisTag, a.minValue, a.defaultValue, a.maxValue) == (
            axis.axisTag, axis.minValue, axis.defaultValue, axis.maxValue
        )
        assert font["name"].getDebugName(1) == "Roof Sans"


def test_variation_sequences_stay_with_their_base(roof, faces, chunk_of):
    """Each variation sequence of the font is in the file that holds its base character."""
    source = uvs_entries(roof)
    assert len(source) == 524
    found = {path: set(uvs_entries(TTFont(path))) for path, _ in faces}
    for entry in source:
        assert entry in found[chunk_of[entry[1]]], [hex(v) if isinstance(v, int) else v for v in entry]
    assert sum(len(v) for v in found.values()) == len(source)


@pytest.mark.parametrize("wght", [400, 1000])
def test_variation_sequences_shape_like_the_font(roof, roof_path, chunk_of, wght):
    by_selector: dict[int, list[int]] = {}
    for selector, base, _ in uvs_entries(roof):
        by_selector.setdefault(selector, []).append(base)
    text = "".join(chr(b) + chr(s) for s, bases in by_selector.items() for b in bases[:4])
    cps = [ord(c) for c in text]
    whole = shape(roof_path.read_bytes(), cps, 0, len(cps), "Hani", "ja", wght)
    assert any(".uv" in g[0] for g in whole)  # the sample selects variant glyphs
    assert shape_split(chunk_of, text, "Hani", "ja", wght) == whole


def test_css_declares_the_weight_range(web_dir):
    for name in (web.FULL_CSS, web.SUBSET_CSS):
        css = (web_dir / name).read_text(encoding="utf-8")
        assert css.count("font-weight: 100 1000;") == css.count("@font-face"), name
        assert "font-family: 'Roof Sans';" in css


def test_full_woff2_is_the_font(roof, roof_path, web_dir):
    woff2 = TTFont(web_dir / web.FULL_WOFF2)
    assert woff2.flavor == "woff2"
    assert sorted(woff2.keys()) == sorted(roof.keys())
    assert woff2.getGlyphOrder() == roof.getGlyphOrder()
    assert woff2.getBestCmap() == roof.getBestCmap()


# (text, OpenType script, BCP 47 language). Each must shape the same split and whole.
SAMPLES = [
    ("Roof Sans: A-B, a:b, 12:30 — “quoted” (it’s) fine… @home #1", "Latn", "en"),
    ("e\u0301 a\u0308 n\u0303 o\u0302 A\u030a", "Latn", "vi"),
    ("It’s l·l “ok” ‘ok’ 2’3", "Latn", "zh-Hans"),
    ("「東京」へ行きます。（テスト）『確認』【注意】〈山〉《本》　終わり",
     "Hani", "ja"),
    ("直骨安！：；？「中文」测试“引号”。", "Hani", "zh-Hans"),
    ("大韓民國 漢字 新聞 社會 經濟 文化 神 骨", "Hani", "ko"),
    ("다람쥐 헌 쳇바퀴에 타고파 키스의 고유조건은 입술끼리 만나야 하고", "Hang", "ko"),
    ("Ελληνικά", "Grek", "el"),
    ("Русский язык", "Cyrl", "ru"),
]


@pytest.mark.parametrize("wght", [400, 700, 1000])
@pytest.mark.parametrize("text,script,lang", SAMPLES, ids=[s[2] + "-" + s[1] for s in SAMPLES])
def test_split_shaping_matches_the_font(roof_path, chunk_of, text, script, lang, wght):
    cps = [ord(c) for c in text]
    whole = shape(roof_path.read_bytes(), cps, 0, len(cps), script, lang, wght)
    assert shape_split(chunk_of, text, script, lang, wght) == whole


def test_decomposed_letter_outside_latin_keeps_its_mark(roof_path, chunk_of):
    """Known limit: i + U+0323 composes to U+1ECB in the full font, which is in latin-ext.

    Split, the latin file has no U+1ECB, so the base and the mark stay separate and the
    mark attaches by GPOS instead.
    """
    text = "i\u0323"
    whole = shape(roof_path.read_bytes(), [ord(c) for c in text], 0, len(text), "Latn", "vi", 400)
    split = shape_split(chunk_of, text, "Latn", "vi", 400)
    assert [g[0] for g in whole] == ["uni1ECB"]
    assert [g[0] for g in split] == ["i", "dotbelowcomb"]
    assert split[1][3] != 0 and split[1][2] == 0  # positioned on the base, zero advance


def test_language_forms_survive_the_split(roof_path, chunk_of):
    """The samples exercise locl: the ko, zh-Hans, and ja forms differ in the full font."""
    def names(text, script, lang):
        cps = [ord(c) for c in text]
        return [g[0] for g in shape(roof_path.read_bytes(), cps, 0, len(cps), script, lang, 400)]

    ko_text, zh_text, ja_text = SAMPLES[5][0], SAMPLES[4][0], SAMPLES[3][0]
    assert names(ko_text, "Hani", "ko") != names(ko_text, "Hani", "ja")
    assert names(zh_text, "Hani", "zh-Hans") != names(zh_text, "Hani", "ja")
    assert names(ja_text, "Hani", "ja") != names(ja_text, "Hani", "ko")
    zh_latin = SAMPLES[2][0]
    assert names(zh_latin, "Latn", "zh-Hans") != names(zh_latin, "Latn", "en")


def test_committed_dist_matches_a_fresh_build(roof_path, web_dir):
    """dist/web is the web build of the committed font, byte for byte."""
    if roof_path.resolve() != COMMITTED_FONT.resolve() and (
        hashlib.sha256(roof_path.read_bytes()).digest() != hashlib.sha256(COMMITTED_FONT.read_bytes()).digest()
    ):
        pytest.skip("the font under test is not the committed font")
    if web_dir.resolve() == COMMITTED_WEB.resolve():
        pytest.skip("ROOF_WEB points at dist/web itself")
    fresh = sorted(p.relative_to(web_dir) for p in web_dir.rglob("*") if p.is_file())
    committed = sorted(p.relative_to(COMMITTED_WEB) for p in COMMITTED_WEB.rglob("*") if p.is_file())
    assert fresh == committed
    for rel in fresh:
        assert (web_dir / rel).read_bytes() == (COMMITTED_WEB / rel).read_bytes(), rel
