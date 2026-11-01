"""Acceptance 15: Chinese punctuation shifts Wanted's own drawing in x only."""

import pytest
from fontTools.pens.boundsPen import BoundsPen

from roofsans.axis import PJ_PEAK, roof_norm
from roofsans.rules.c_hanzi import calibrate, ink_bounds
from roofsans.rules.c_punct import ZHS_QUOTES, ZHS_SIGNS

pytestmark = pytest.mark.acceptance


@pytest.mark.parametrize('w', [400, 750, 1000])
def test_a15_c_punct_placement(ctx, static, w):
    calibration = calibrate(ctx)
    font = static('roof', w)
    glyf = font['glyf']
    for cp in (*ZHS_SIGNS, *ZHS_QUOTES):
        name = f'uni{cp:04X}.zhs'
        glyph = glyf[name]
        (component,) = glyph.components
        assert component.y == 0
        points, ends, flags = glyph.getCoordinates(glyf)
        wanted = ctx.ws.outline(component.glyphName, w)
        assert list(ends) == wanted.end_pts
        assert len(points) == len(wanted.points)
        assert max(abs(actual[i] - expected[i] - (component.x if i == 0 else 0))
                   for actual, expected in zip(points, wanted.points) for i in (0, 1)) <= 1
        pen = BoundsPen(font.getGlyphSet())
        font.getGlyphSet()[name].draw(pen)
        source = ctx.shs_cn.getBestCmap()[cp]
        a = ink_bounds(ctx.cs.outline(source, calibration.w400))
        b = ink_bounds(ctx.cs.outline(source, calibration.w930))
        left = calibration.scale * (a[0] + a[2]) / 2 + calibration.dx400
        right = calibration.scale * (b[0] + b[2]) / 2 + calibration.dx930
        expected = left + (right - left) * min(roof_norm(w) / PJ_PEAK, 1)
        assert (pen.bounds[0] + pen.bounds[2]) / 2 == pytest.approx(expected, abs=1)
        assert font['hmtx'][name][0] == 1920
