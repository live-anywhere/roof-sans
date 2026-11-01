import pytest

from helpers import max_abs_diff
from roofsans.axis import PJ_PEAK
from roofsans.chinese import gb2312_hanzi
from roofsans.newglyph import newglyph_outline
from roofsans.rules.c_hanzi import calibrate, calibration_set, contribute, hanzi_master, zhs_forms
from roofsans.selection import Rule


def test_calibration_set(ctx):
    points = calibration_set(ctx)
    assert len(points) == 1291
    assert set(map(ord, '田熙')) <= set(points)
    assert not set(map(ord, '唾毁')) & set(points)


def test_zhs_forms(ctx):
    points = zhs_forms(ctx)
    assert len(points) == 2212
    assert set(map(ord, '唾毁埃安')) <= set(points)
    assert not set(map(ord, '田熙')) & set(points)
    assert set(points) <= ctx.selection.rules.keys() & set(gb2312_hanzi())


def test_calibration_values(ctx):
    c = calibrate(ctx)
    assert calibrate(ctx) is c
    assert c.scale == 1.92 and c.w930 == 900
    assert c.w400 == pytest.approx(381.25, abs=1)
    assert c.dy400 == pytest.approx(21.5, abs=1)
    assert c.dy930 == pytest.approx(21.5, abs=1)
    assert abs(c.dx400) <= 1 and abs(c.dx930) <= 1


@pytest.fixture(scope='module')
def hanzi(ctx):
    return {g.name: g for g in contribute(ctx)}


def test_c_hanzi_plateau(ctx, hanzi):
    g = hanzi['uni554A']
    assert max_abs_diff(newglyph_outline(g, 1, ctx.outline).coords,
                        newglyph_outline(g, PJ_PEAK, ctx.outline).coords) <= 0.5


def test_c_hanzi_masters(ctx, hanzi):
    assert len(hanzi) == 3260 + 2212
    g = hanzi['uni554A']
    for t, master in ((0, 400), (PJ_PEAK, 930)):
        actual = newglyph_outline(g, t, ctx.outline)
        assert max_abs_diff(actual.coords, hanzi_master(ctx, 0x554A, master).coords) <= 1
        assert actual.advance() == 1920
    assert all(g.rule is (Rule.C1_HANZI if g.unicodes else Rule.C2_FORM) for g in hanzi.values())
    assert sum(bool(g.unicodes) for g in hanzi.values()) == 3260


# ``thin`` is the light master's target; None builds without the light weights.
@pytest.mark.parametrize('regular, heavy, thin, master, bound', [
    (350, 1000, None, 400, 350), (420, 1000, None, 400, 420),
    (350.01, 1000, None, 400, 350), (419.99, 1000, None, 400, 420),
    (381.5, 850, None, 930, 850),
    (381.5, 1000, 250, 100, 250), (381.5, 1000, 300, 100, 300),
    (381.5, 1000, 250.01, 100, 250), (381.5, 1000, 299.99, 100, 300),
])
def test_calibration_rejects_search_bounds(monkeypatch, regular, heavy, thin, master, bound):
    from types import SimpleNamespace
    from roofsans.rules import c_hanzi

    font = SimpleNamespace(getBestCmap=lambda: {0x7530: 'test'})
    ctx = SimpleNamespace(
        calibration=None, pretendard=font, shs_jp=font,
        light=None if thin is None else object(),
        ps=SimpleNamespace(outline=lambda _, w: {100: thin, 400: regular, 930: heavy}[w] * 1.92**2),
        js=SimpleNamespace(outline=lambda _, w: w),
    )
    monkeypatch.setattr(c_hanzi, 'calibration_set', lambda _: (0x7530,))
    monkeypatch.setattr(c_hanzi, 'ink_area', lambda area: area)
    monkeypatch.setattr(c_hanzi, 'ink_bounds', lambda _: (0, 0, 1, 1))
    with pytest.raises(ValueError, match=f'w{master}.*{bound}'):
        calibrate(ctx)
