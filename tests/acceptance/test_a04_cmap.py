"""Acceptance 4: the cmap follows the selection rule, with Pretendard's 524 sequences."""

from collections import Counter

import pytest
import uharfbuzz as hb
from copies import COPY_WEIGHTS, differing_copies, pj_names  # noqa: F401 (fixture)

from roofsans.assemble import planned_cmap
from roofsans.rules.h6_copy import format14_sequences

pytestmark = pytest.mark.acceptance


@pytest.fixture(scope="module")
def plan(ctx, pj_names):
    return planned_cmap(ctx)


def shape(path, text):
    font = hb.Font(hb.Face(hb.Blob.from_file_path(str(path))))
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf, {})
    return [(i.codepoint, p.x_advance) for i, p in zip(buf.glyph_infos, buf.glyph_positions)]


def test_cmap_equals_plan(ctx, roof, plan):
    cmap = roof.getBestCmap()
    missing = Counter(str(ctx.selection.rules[cp]) for cp in plan if cp not in cmap)
    wrong = [hex(cp) for cp, g in plan.items() if cp in cmap and cmap[cp] != g]
    extra = [hex(cp) for cp in cmap if cp not in plan]
    assert not (missing or wrong or extra), f"missing {dict(missing)}, wrong {wrong[:10]}, extra {extra[:10]}"


def test_no_private_use(roof, plan):
    assert not [cp for cp in roof.getBestCmap() if 0xE000 <= cp <= 0xF8FF]
    assert not [cp for cp in plan if 0xE000 <= cp <= 0xF8FF]


def test_format4_size_limit(roof):
    sizes = [len(table.compile(roof)) for table in roof['cmap'].tables if table.format == 4]
    print('CMAP_FORMAT4_BYTES', sizes)
    assert sizes and all(size < 65535 for size in sizes)


def test_variation_sequences(roof, pretendard, pj_names):
    expected = {
        (vs, base, pj_names[g]) for vs, seqs in format14_sequences(pretendard).items() for base, g in seqs
    }
    cmap = roof.getBestCmap()
    actual = {
        (vs, base, g if g is not None else cmap[base])
        for vs, seqs in format14_sequences(roof).items()
        for base, g in seqs
    }
    assert len(expected) == 524 and actual == expected


@pytest.mark.parametrize("wght, tolerance", COPY_WEIGHTS)
def test_sequence_targets_match_pretendard(static, pretendard, pj_names, wght, tolerance):
    targets = {g for seqs in format14_sequences(pretendard).values() for _, g in seqs}
    pairs = [(source, pj_names[source]) for source in sorted(targets)]
    bad = differing_copies(static("pretendard", wght), static("roof", wght), pairs, tolerance)
    assert len(targets) == 524 and not bad, bad[:10]


@pytest.mark.parametrize("text", ["漢\U000E0108", "A︀"])
def test_unknown_variation_selector_falls_back(roof, roof_path, text):
    base = roof.getGlyphID(roof.getBestCmap()[ord(text[0])])
    glyphs = shape(roof_path, text)
    assert len(glyphs) == 2 and glyphs[0][0] == base
    assert glyphs[1][1] == 0 and 0 not in [g for g, _ in glyphs]
