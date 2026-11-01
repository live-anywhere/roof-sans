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
    bad = differing_copies(static("pretendard", wght), static("roof", wght), pj_names.items(), tolerance)
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
