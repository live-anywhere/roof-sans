"""Acceptance 7: Wanted Sans's features behave as before; Pretendard JP's CJK features carry over."""

import unicodedata
from functools import cache

import pytest
import uharfbuzz as hb
from copies import pj_names  # noqa: F401 (fixture)
from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont
from fontTools.varLib.models import supportScalar

from roofsans.axis import roof_norm
from roofsans.features.gsub import PJ_JP, PJ_KANA, PJ_KOR
from roofsans.rules.h6_copy import format14_sequences
from roofsans.selection import JAN_SHARED, Rule

pytestmark = pytest.mark.acceptance

SAMPLE = "The quick brown fox 0123456789 ½ ffi (A) [B] ê ñ ș 한글 테스트 ㄱㄴ"
HANGUL_RUN = "한글 테스트 ㄱㄴ"
WANTED_FEATURES = [
    {},
    *({f"ss{i:02d}": True} for i in range(1, 17)),
    *({f"cv{i:02d}": True} for i in range(1, 23)),
    *({tag: True} for tag in ("frac", "sups", "subs", "tnum", "zero", "case")),
]
JAN_TEXT = "あ　〈〉《》「」『』【】〔〕あ"
KANA_WEIGHTS = (400, 500, 600, 700, 767, 800, 900, 930, 1000)


@cache
def _font(path: str, wght: float) -> hb.Font:
    font = hb.Font(hb.Face(hb.Blob.from_file_path(path)))
    font.set_variations({"wght": wght})
    return font


@cache
def _hiding(path: str, wght: float, hidden: frozenset[int]) -> hb.Font:
    """``_font`` with the code points ``hidden`` unmapped, so HarfBuzz keeps them decomposed."""
    parent = _font(path, wght)
    font = hb.Font(parent)
    funcs = hb.FontFuncs()
    funcs.set_nominal_glyph_func(lambda _f, cp, _d: 0 if cp in hidden else parent.get_nominal_glyph(cp) or 0, None)
    font.funcs = funcs
    return font


def shape(path, text, wght=400, features=None, language=None, script=None, hidden=frozenset()):
    """[(glyph name, x advance, y advance, x offset, y offset)] for ``text``."""
    font = _hiding(str(path), wght, hidden) if hidden else _font(str(path), wght)
    buf = hb.Buffer()
    buf.add_str(text)
    if language:
        buf.language = language
    if script:
        buf.script = script
    buf.guess_segment_properties()
    hb.shape(font, buf, features or {})
    return [
        (font.glyph_to_string(i.codepoint), p.x_advance, p.y_advance, p.x_offset, p.y_offset)
        for i, p in zip(buf.glyph_infos, buf.glyph_positions)
    ]


@cache
def wanted_cmap(inputs):
    return TTFont(inputs.wanted).getBestCmap()


def names(path, text, **kw):
    return [g[0] for g in shape(path, text, **kw)]


def _mapping(font, index):
    return font["GSUB"].table.LookupList.Lookup[index].SubTable[0].mapping


@pytest.fixture(scope="module")
def reach(pretendard):
    """Pretendard glyph → text that shapes to it by default: its code point or a variation sequence."""
    out = {}
    for vs, seqs in format14_sequences(pretendard).items():
        for base, g in seqs:
            if g is not None:
                out.setdefault(g, chr(base) + chr(vs))
    for cp, g in sorted(pretendard.getBestCmap().items(), reverse=True):
        out[g] = chr(cp)
    return out


def test_wanted_behavior_unchanged(inputs, roof_path):
    bad, compared = [], 0
    for wght in (400, 1000):
        for language in (None, "ko", "tr"):
            for features in WANTED_FEATURES:
                for text in (SAMPLE, HANGUL_RUN):
                    w = shape(inputs.wanted, text, wght, features, language)
                    r = shape(roof_path, text, wght, features, language)
                    if w != r or len(w) < len(text) // 2:
                        bad.append((wght, language, features, text[:8]))
                    compared += 1
    assert compared == 2 * 3 * len(WANTED_FEATURES) * 2
    assert not bad, bad[:10]


def test_kor_hanja(pretendard, pj_names, reach, roof_path):  # noqa: F811
    mapping = _mapping(pretendard, PJ_KOR)
    assert len(mapping) == 537
    sources = list(mapping)
    text = "".join(reach[g] for g in sources)
    assert all(len(reach[g]) == 1 for g in sources)
    kor = [pj_names[mapping[g]] for g in sources]
    assert names(roof_path, text, language="ko", script="Hani") == kor
    assert names(roof_path, text, features={"ss20": True}) == kor
    assert names(roof_path, text) == [pj_names[g] for g in sources]


def test_jan_punctuation(wanted, pretendard, pj_names, roof, roof_path):  # noqa: F811
    pcmap, wcmap = pretendard.getBestCmap(), wanted.getBestCmap()
    middle = slice(1, -1)
    ja = shape(roof_path, JAN_TEXT, language="ja")[middle]
    cps = [ord(c) for c in JAN_TEXT[middle]]
    assert sorted(cps) == sorted(JAN_SHARED)
    # Ruling R13: each .pj glyph keeps Pretendard JP's own advance (698 for 〈〉, else 1920).
    assert [(g[0], g[1]) for g in ja] == [(pj_names[pcmap[cp]], pretendard["hmtx"][pcmap[cp]][0]) for cp in cps]
    assert all(g[0].endswith(".pj") for g in ja)
    assert sorted({g[1] for g in ja}) == [698, 1920]
    for language in ("ko", None):
        assert names(roof_path, JAN_TEXT, language=language)[middle] == [wcmap[cp] for cp in cps]


def test_jan_brackets_after_latin(roof_path):
    for text in ("ID「abc」", "2026「新」"):
        out = names(roof_path, text, language="ja")
        assert "uni300C.pj" in out and "uni300D.pj" in out, (text, out)
        assert "uni300C" not in out and "uni300D" not in out, (text, out)


def _variant_inputs(pretendard, pj_names, reach):  # noqa: F811
    """(lookup, source, text, features) for every carried jp78/jp83/jp90/nlck mapping, and the
    sources Roof does not copy. A source with no code point or variation sequence is reached
    through an earlier variant lookup."""
    tags = {index: tag for tag, index in PJ_JP.items()}
    out, unreached, dropped = [], [], []
    for index, tag in tags.items():
        for src in _mapping(pretendard, index):
            if src not in pj_names:
                dropped.append(src)
            elif src in reach:
                out.append((index, src, reach[src], {tag: True}))
            else:
                via = [
                    (reach[g], {tags[e]: True, tag: True})
                    for e in tags
                    if e < index
                    for g, dst in _mapping(pretendard, e).items()
                    if dst == src and g in reach
                ]
                if via:
                    out.append((index, src, *via[0]))
                else:
                    unreached.append((tag, src))
    return out, unreached, dropped


def test_jp_variants(pretendard, pj_names, reach, roof_path):  # noqa: F811
    cases, unreached, dropped = _variant_inputs(pretendard, pj_names, reach)
    assert not unreached, unreached
    # nlck's uni5349.001 → uni5349 has a source Roof does not copy; the entry is dropped.
    assert dropped == ["uni5349.001"]
    bad = []
    for index, src, text, features in cases:
        want = pj_names[_mapping(pretendard, index)[src]]
        got = names(roof_path, text, features=features)
        if got != [want]:
            bad.append((index, src, features, got, want))
    assert not bad, bad[:10]


def test_kana_weight_alternates(pretendard, pj_names, reach, inputs, roof_path):  # noqa: F811
    inputs_77_85 = {g for index in PJ_KANA for g in _mapping(pretendard, index)}
    # A source with no code point is the output of an earlier alternate lookup.
    produced = {dst: src for index in PJ_KANA for src, dst in _mapping(pretendard, index).items()}
    texts = {}
    for g in inputs_77_85:
        src = g
        while src not in reach:
            src = produced[src]
        texts[g] = reach[src]
    # 42 mappings; one glyph is the input of two lookups.
    assert sum(len(_mapping(pretendard, index)) for index in PJ_KANA) == 42
    bad = []
    for wght in KANA_WEIGHTS:
        for g, text in sorted(texts.items()):
            want = [pj_names[n] for n in names(inputs.pretendard, text, wght=min(wght, 930))]
            got = names(roof_path, text, wght=wght)
            if got != want:
                bad.append((wght, g, got, want))
    assert not bad, bad[:10]


def test_nfd_kana_composes(roof_path):
    assert names(roof_path, "が") == names(roof_path, "が")
    assert names(roof_path, "パ") == names(roof_path, "パ")
    assert len(names(roof_path, "が")) == 1 and len(names(roof_path, "パ")) == 1


def _component_offset(roof, glyph, mark, wght):
    """Offset of component ``mark`` in Roof composite ``glyph`` at ``wght``, from its gvar."""
    comps = roof["glyf"][glyph].components
    i = [c.glyphName for c in comps].index(mark)
    x, y = float(comps[i].x), float(comps[i].y)
    for tv in roof["gvar"].variations.get(glyph, []):
        s = supportScalar({"wght": roof_norm(wght)}, tv.axes)
        d = tv.coordinates[i]
        if s and d is not None:
            x, y = x + s * d[0], y + s * d[1]
    return x, y


# H2 keeps Wanted's base anchors (R25). Wanted's own a, E, R, r anchors (and Pretendard's on ư)
# sit differently from the other font's relative to the ink, so these letters differ from
# Pretendard's precomposed letter by up to 18 units; the others stay within 4.
ANCHOR_DESIGN_DIFFERS = "ảȃȓȒȆẺử"
# Wanted's mark lookup has no anchor on `ae` (H2 derives one), so Wanted cannot be compared.
# ẛ's dot follows ruling R31 (Pretendard's dot x over the Roof ſ, which is Pretendard's ſ, not
# the differently drawn body of Pretendard's ẛ); `test_long_s_dot_clears_long_s` covers it.
NO_SOURCE_MATCH = "ǣǽẛ"
# Decomposed input that shapes differently from the H2 glyph, which HarfBuzz composes anyway:
# i/j + an H4 mark above keep the dot (Wanted's ccmp only knows its own marks), Wanted's ccmp
# turns the ogonek after a capital into `uni0328.case`, and `ae` has no Wanted anchor.
NO_DECOMPOSED_MATCH = "ȋỉǰǪǣǽǢǼ"
HORN = 0x031B


def _w_prime(ctx, wght):
    """The Pretendard weight the H4 glyphs are drawn from at Roof ``wght``."""
    from roofsans.axis import H4_LOCS
    from roofsans.rules import h4_letters

    p, t = h4_letters.params(ctx), roof_norm(wght)
    i = max(j for j, loc in enumerate(H4_LOCS[:-1]) if loc <= t)
    a, b = H4_LOCS[i], H4_LOCS[i + 1]
    return p[a].w_prime + (t - a) * (p[b].w_prime - p[a].w_prime) / (b - a)


def _center_x(contours):
    xs = [x for c in contours for x, _ in c]
    return (min(xs) + max(xs)) / 2


def _pretendard_mark_offset(ctx, ch, mark_cp, w):
    """Ink center x of mark ``mark_cp`` minus the base's in Pretendard's precomposed ``ch`` at ``w``:
    the mark is what ``ch`` draws beyond the letter without that mark."""
    pcmap = ctx.pretendard.getBestCmap()
    chars = unicodedata.normalize("NFD", ch)
    without = unicodedata.normalize("NFC", chars.replace(chr(mark_cp), ""))
    own = {tuple(map(tuple, c)) for c in ctx.ps.outline(pcmap[ord(without)], w).contours()}
    mark = [c for c in ctx.ps.outline(pcmap[ord(ch)], w).contours() if tuple(map(tuple, c)) not in own]
    return _center_x(mark) - _center_x(ctx.ps.outline(pcmap[ord(chars[0])], w).contours())


def _roof_parts(roof, glyph, wght):
    """[(component, x offset, y offset, ink center x)] of Roof composite ``glyph`` at ``wght``."""
    out = []
    glyph_set = roof.getGlyphSet(location={"wght": wght})
    for c in roof["glyf"][glyph].components:
        x, y = _component_offset(roof, glyph, c.glyphName, wght)
        pen = BoundsPen(glyph_set)
        glyph_set[c.glyphName].draw(pen)
        out.append((c.glyphName, x, y, x + (pen.bounds[0] + pen.bounds[2]) / 2))
    return out


@pytest.mark.parametrize("wght", [400, 700, 1000])
def test_decomposed_marks(ctx, inputs, roof, roof_path, wght):
    """Ruling R35: every H2 mark sits where its source font puts it, and GPOS agrees.

    A Wanted mark on a Wanted letter matches Wanted Sans's own GPOS placement; a mark with an
    H4 glyph (or on an H4 letter) matches Pretendard's precomposed letter in ink center x.
    Stacked marks follow decision 13 and the horn its own rule (both tested in
    test_h2_compose). Decomposed single-mark input shapes like the precomposed H2 glyph.
    """
    cmap, wcmap = roof.getBestCmap(), wanted_cmap(inputs)
    bad, counts = [], {"wanted": 0, "pretendard": 0, "decomposed": 0}
    for cp in ctx.selection.codepoints(Rule.H2_COMPOSE):
        ch = chr(cp)
        chars = unicodedata.normalize("NFD", ch)
        parts = _roof_parts(roof, cmap[cp], wght)
        base_center = parts[0][3]
        seen = set()
        for mark_char, (mark, x, y, center) in zip(chars[1:], parts[1:]):
            above = unicodedata.combining(mark_char) == 230
            if ord(mark_char) == HORN or above in seen:
                continue
            seen.add(above)
            if ch in NO_SOURCE_MATCH:
                continue
            if ord(chars[0]) in wcmap and ord(mark_char) in wcmap:
                pair = chars[0] + mark_char
                composed = unicodedata.normalize("NFC", pair)
                hidden = frozenset({ord(composed)}) if len(composed) == 1 else frozenset()
                out = shape(inputs.wanted, pair, wght, hidden=hidden)
                if len(out) == 2 and out[1][0] == mark:
                    counts["wanted"] += 1
                    want = (out[0][1] + out[1][3], out[1][4])
                    if abs(x - want[0]) > 2 or abs(y - want[1]) > 2:
                        bad.append(("wanted", wght, ch, (x, y), want))
                continue
            counts["pretendard"] += 1
            want = _pretendard_mark_offset(ctx, ch, ord(mark_char), _w_prime(ctx, wght))
            tolerance = 18 if ch in ANCHOR_DESIGN_DIFFERS else 4
            if abs(center - base_center - want) > tolerance:
                bad.append(("pretendard", wght, ch, round(center - base_center), round(want)))
        if len(chars) != 2 or ch in NO_DECOMPOSED_MATCH:
            continue
        out = shape(roof_path, chars, wght, hidden=frozenset({cp}))
        counts["decomposed"] += 1
        got = (out[0][1] + out[1][3], out[1][4])
        moved = max(abs(got[0] - parts[1][1]), abs(got[1] - parts[1][2]))
        if [g[0] for g in out] != [p[0] for p in parts] or moved > 2:
            bad.append(("decomposed", wght, ch, [g[0] for g in out], got, parts[1][1:3]))
    assert not bad, bad[:10]
    assert counts["wanted"] >= 190 and counts["pretendard"] >= 30 and counts["decomposed"] >= 110, counts


# Ruling R36: marks attach to H4 letters. Pretendard anchors these four; the others have
# anchors derived from their ink (R36 amendment).
H4_ANCHORED = "аоыŋ"
H4_DERIVED = "ʃбдфюβλ"


def _shaped_marks(path, wght, text):
    """(mark ink center x − base ink center x, clearance between mark and base ink) for base + mark."""
    font = TTFont(path)
    glyph_set = font.getGlyphSet(location={"wght": wght})
    composed = unicodedata.normalize("NFC", text)
    hidden = frozenset({ord(composed)} if len(composed) == 1 else ())
    out = shape(path, text, wght, features={"ccmp": False}, hidden=hidden)
    boxes, x = [], 0
    for name, advance, _, dx, dy in out:
        pen = BoundsPen(glyph_set)
        glyph_set[name].draw(pen)
        x0, y0, x1, y1 = pen.bounds
        boxes.append((x + dx + (x0 + x1) / 2, dy + y0, dy + y1))
        x += advance
    assert len(boxes) == 2, (text, out)
    (base, b0, b1), (mark, m0, m1) = boxes
    return mark - base, (m0 - b1) if unicodedata.combining(text[1]) == 230 else (b0 - m1)


@pytest.mark.parametrize("wght", [400, 700, 1000])
def test_marks_on_h4_bases(inputs, roof_path, wght):
    """A mark on an H4 letter sits as on ``o``, measured from the ink, the way Pretendard JP's
    letters relate to its ``o``; on letters Pretendard leaves without anchors, as on ``o``."""
    bad = []
    p_wght = min(wght, 930)
    for mark in ("\u0301", "\u0303"):
        r_o = _shaped_marks(roof_path, wght, "o" + mark)
        p_o = _shaped_marks(inputs.pretendard, p_wght, "o" + mark)
        for base in H4_ANCHORED + H4_DERIVED:
            r = _shaped_marks(roof_path, wght, base + mark)
            want = r_o[0]
            if base in H4_ANCHORED:
                want += _shaped_marks(inputs.pretendard, p_wght, base + mark)[0] - p_o[0]
            if abs(r[0] - want) > 3 or r[1] <= 0:
                bad.append((wght, base + mark, r, want))
    assert not bad, bad
