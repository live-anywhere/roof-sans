"""Acceptance 12: every C1/C2 master preserves its transformed CN source."""

import pytest

from roofsans.rules.c_hanzi import calibrate, zhs_forms
from roofsans.selection import Rule

pytestmark = pytest.mark.acceptance


def _points(font, name):
    return font['glyf'][name].getCoordinates(font['glyf'])[0]


def test_a12_source_fidelity(ctx, static):
    calibration = calibrate(ctx)
    source_cmap = ctx.shs_cn.getBestCmap()
    glyphs = [(cp, f'uni{cp:04X}') for cp in ctx.selection.codepoints(Rule.C1_HANZI)]
    glyphs += [(cp, f'uni{cp:04X}.zhs') for cp in zhs_forms(ctx)]
    bad = []
    for w, master in ((400, 400), (930, 930), (1000, 930)):
        font = static('roof', w)
        for cp, name in glyphs:
            weight, dx, dy = (
                (calibration.w400, calibration.dx400, calibration.dy400) if master == 400
                else (calibration.w930, calibration.dx930, calibration.dy930)
            )
            source = ctx.cs.outline(source_cmap[cp], weight)
            expected = [(calibration.scale * x + dx, calibration.scale * y + dy)
                        for x, y in source.points]
            actual = _points(font, name)
            if len(actual) != len(expected):
                bad.append((w, name, 'point count'))
                continue
            error = max(abs(a[i] - b[i]) for a, b in zip(actual, expected) for i in (0, 1))
            if error > 1:
                bad.append((w, name, error))
            assert list(font['glyf'][name].endPtsOfContours) == source.end_pts
    for w in (400, 750, 1000):
        font = static('roof', w)
        assert all(font['hmtx'][name][0] == 1920 for _, name in glyphs)
    assert not bad, bad[:20]


def test_a12_c2_differs_from_default(ctx, static):
    font = static('roof', 400)
    cmap = font.getBestCmap()
    identical = []
    for cp in zhs_forms(ctx):
        alternate, default = f'uni{cp:04X}.zhs', cmap[cp]
        a, ae, _ = font['glyf'][alternate].getCoordinates(font['glyf'])
        b, be, _ = font['glyf'][default].getCoordinates(font['glyf'])
        if list(a) == list(b) and list(ae) == list(be):
            identical.append(f'U+{cp:04X}')
    assert not identical, identical
