"""Acceptance 1: every code point Wanted Sans maps keeps Wanted Sans's glyph."""

import pytest

pytestmark = pytest.mark.acceptance

WEIGHTS = (400, 750, 1000)


def structure(glyph):
    """Everything a glyf entry stores except bounds, which are recomputed on save."""
    if glyph.isComposite():
        return [(c.glyphName, c.x, c.y, c.flags, getattr(c, "transform", None)) for c in glyph.components]
    if glyph.numberOfContours == 0:
        return ()
    program = glyph.program.getBytecode() if hasattr(glyph, "program") else b""
    return (list(glyph.coordinates), list(glyph.endPtsOfContours), bytes(glyph.flags), program)


@pytest.mark.parametrize("wght", WEIGHTS)
def test_static_outlines_and_advances(static, wanted, wght):
    w, r = static("wanted", wght), static("roof", wght)
    wglyf, rglyf = w["glyf"], r["glyf"]
    rcmap = r.getBestCmap()
    bad = []
    for cp, name in sorted(wanted.getBestCmap().items()):
        if rcmap.get(cp) != name:
            bad.append((hex(cp), "cmap", rcmap.get(cp)))
            continue
        wc, wend, _ = wglyf[name].getCoordinates(wglyf)
        rc, rend, _ = rglyf[name].getCoordinates(rglyf)
        if list(wc) != list(rc) or list(wend) != list(rend):
            bad.append((hex(cp), name, "outline"))
        if w["hmtx"][name][0] != r["hmtx"][name][0]:
            bad.append((hex(cp), name, "advance", w["hmtx"][name][0], r["hmtx"][name][0]))
    assert not bad, f"{len(bad)} differ at {wght}: {bad[:10]}"


def test_variable_glyf_and_gvar_unchanged(wanted, roof):
    names = sorted(set(wanted.getBestCmap().values()))
    wglyf, rglyf = wanted["glyf"], roof["glyf"]
    wgvar, rgvar = wanted["gvar"].variations, roof["gvar"].variations
    bad = [n for n in names if structure(wglyf[n]) != structure(rglyf[n])]
    assert not bad, f"glyf differs for {len(bad)} glyphs: {bad[:10]}"
    # The new negative tuple must not change any of Wanted's positive-region tuples.
    bad = [n for n in names if wgvar.get(n, []) != [tv for tv in rgvar.get(n, []) if tv.axes["wght"][1] >= 0]]
    assert all(tv.axes == {"wght": (-1, -1, 0)}
               for n in names for tv in rgvar.get(n, []) if tv.axes["wght"][1] < 0)
    assert not bad, f"gvar differs for {len(bad)} glyphs: {bad[:10]}"
