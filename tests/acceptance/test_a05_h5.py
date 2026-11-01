"""Acceptance 5, H5: Pretendard arrows and math symbols sit on Wanted Sans's axes."""

import pytest
from sectors import interpolate

from roofsans.axis import H4_LOCS, roof_norm
from roofsans.outline import Outline
from roofsans.rules.h5_symbols import category_transform
from roofsans.selection import SymbolCategory

pytestmark = pytest.mark.acceptance

WEIGHTS = (400, 550, 700, 850, 1000)

# The design's axes and the reference each category is moved by.
AXIS = {SymbolCategory.ARROW: 725, SymbolCategory.MATH: 540}
REFERENCE = {SymbolCategory.ARROW: "→", SymbolCategory.MATH: "+"}
# Glyphs whose ink center sits on the axis. `← → ↔ + − = × < >` are Wanted Sans's own.
ON_AXIS = {
    SymbolCategory.ARROW: "← → ↔ ⟵ ⟶ ⟷ ⇐ ⇒ ⇔ ⟸ ⟹ ⟺ 🡐 🡒",
    SymbolCategory.MATH: "≪ ≫ + − = × < >",
}
# Pretendard draws these off its own axis (the hook of `↩` rises above the head; `⋯` sits
# 156 units above `+`). H5 moves a whole category alike, so each keeps Pretendard's
# offset from the axis, scaled (R29).
OFF_AXIS = {
    SymbolCategory.ARROW: "↩ ↪",
    SymbolCategory.MATH: "≤ ≥ ∞ ⋯",
}


def roof_outline(font, char: str) -> Outline:
    glyf = font["glyf"]
    coords, ends, flags = glyf[font.getBestCmap()[ord(char)]].getCoordinates(glyf)
    return Outline([tuple(p) for p in coords] + [(0, 0)] * 4, list(ends), list(flags))


def center_y(o: Outline) -> float:
    _, y0, _, y1 = o.bounds()
    return (y0 + y1) / 2


def expected_center(ctx, cat: SymbolCategory, char: str, norm: float) -> float:
    """The axis plus Pretendard's own offset of ``char`` from the reference, scaled."""
    pcmap = ctx.pretendard.getBestCmap()

    def at(t: float) -> float:
        tr = category_transform(ctx, cat, t)
        offset = center_y(ctx.ps.outline(pcmap[ord(char)], tr.sample_wght)) - center_y(
            ctx.ps.outline(pcmap[ord(REFERENCE[cat])], tr.sample_wght)
        )
        return AXIS[cat] + tr.scale * offset

    return interpolate({t: at(t) for t in H4_LOCS}, norm)


@pytest.mark.parametrize("wght", WEIGHTS)
def test_symbols_on_wanted_axes(static, wght):
    roof = static("roof", wght)
    got = {(cat, c): center_y(roof_outline(roof, c)) for cat, chars in ON_AXIS.items() for c in chars.split()}
    print(f"{wght}: " + " ".join(f"{c} {y:.1f}" for (_, c), y in got.items()))
    bad = {c: round(y, 1) for (cat, c), y in got.items() if abs(y - AXIS[cat]) > 5}
    assert not bad, f"ink centers off the axis at {wght}: {bad}"


@pytest.mark.parametrize("wght", WEIGHTS)
def test_off_axis_symbols_keep_pretendard_offset(static, ctx, wght):
    roof = static("roof", wght)
    rows = []
    for cat, chars in OFF_AXIS.items():
        for c in chars.split():
            got = center_y(roof_outline(roof, c))
            rows.append((c, round(got, 1), round(expected_center(ctx, cat, c, roof_norm(wght)), 1)))
    print(f"{wght} (char, center, expected): {rows}")
    bad = [r for r in rows if abs(r[1] - r[2]) > 5]
    assert not bad, f"offsets from the axis differ from Pretendard's at {wght}: {bad}"
