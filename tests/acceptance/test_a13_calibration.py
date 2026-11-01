"""Acceptance 13: one transform matches the existing Japanese-form Han glyphs."""

import json
import math
from statistics import median

import pytest

from roofsans.outline import Outline
from roofsans.rules.c_hanzi import calibrate, calibration_set, ink_area, ink_bounds, transform

pytestmark = pytest.mark.acceptance


@pytest.mark.parametrize('w', [400, 700, 930])
def test_a13_calibration_match(ctx, w):
    c = calibrate(ctx)
    t = (w - 400) / 530
    pcmap, jcmap = ctx.pretendard.getBestCmap(), ctx.shs_jp.getBestCmap()
    limit, maximum = (3, 20) if w == 400 else (5, 8)
    errors, ratios, outliers = [], [], []
    for cp in calibration_set(ctx):
        target = ctx.ps.outline(pcmap[cp], w)
        # Ship the linear interpolation of the transformed masters, as Pretendard does.
        a = transform(ctx.js.outline(jcmap[cp], c.w400), c.scale, c.dx400, c.dy400)
        b = transform(ctx.js.outline(jcmap[cp], c.w930), c.scale, c.dx930, c.dy930)
        source = Outline([(x + (u - x) * t, y + (v - y) * t)
                          for (x, y), (u, v) in zip(a.coords, b.coords)], a.end_pts, a.flags)
        error = max(abs(a - b) for a, b in zip(ink_bounds(target), ink_bounds(source)))
        errors.append(error)
        ratios.append(ink_area(target) / ink_area(source))
        if error > limit:
            outliers.append((f'U+{cp:04X}', chr(cp), round(error, 6)))
    stats = dict(wght=w, method="two-master interpolation", count=len(errors),
                 edges_median=median(errors), edges_p99=sorted(errors)[math.ceil(.99 * len(errors)) - 1],
                 edges_max=max(errors), within_limit=sum(e <= limit for e in errors),
                 area_median=median(ratios), area_min=min(ratios), area_max=max(ratios), outliers=outliers)
    print('CALIBRATION_DISTRIBUTION ' + json.dumps(stats, ensure_ascii=False))
    assert sum(e <= limit for e in errors) / len(errors) >= .99, stats
    assert max(errors) <= maximum, stats
    assert abs(median(ratios) - 1) <= .01, stats
    assert all(abs(r - 1) <= .03 for r in ratios), stats
