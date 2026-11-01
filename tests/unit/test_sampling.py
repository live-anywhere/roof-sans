import pytest
from fontTools.misc.roundTools import otRound

from roofsans.sampling import PretendardSampler, WantedSampler

from helpers import max_abs_diff


def test_wanted_advance_varies(wanted):
    ws = WantedSampler(wanted)
    assert [round(ws.advance("zero", w)) for w in (400, 750, 1000)] == [1280, 1373, 1440]


def test_pretendard_extrapolates(pretendard):
    ps = PretendardSampler(pretendard)
    a, b, c = (ps.outline("l", w).coords[0] for w in (400, 930, 1000))
    assert c[0] - b[0] == pytest.approx((b[0] - a[0]) * 70 / 530, abs=0.01)


def test_decompose_applies_transform(ps, static):
    for w in (400, 930):
        ox, oy = (lambda c: (c.x, c.y))(static("pretendard", w)["glyf"]["arrowdown"].components[0])
        up = ps.outline("arrowup", w)
        down = ps.outline("arrowdown", w)
        rotated = [(ox - x, oy - y) for x, y in up.coords[:-4]]
        assert down.end_pts == up.end_pts
        assert max_abs_diff(down.coords[:-4], rotated) <= 0.5


def _instance_coords(font, name):
    glyf = font["glyf"]
    coords, _, _ = glyf[name].getCoordinates(glyf)
    return [tuple(p) for p in coords]


# Simple, nested composites, a scaled component (uni042E), and a mirror (arrowdown).
PRETENDARD_GLYPHS = ("l", "Acircumflex", "uni1EAC", "uni042E", "arrowdown")


@pytest.mark.parametrize("w", [45, 200, 700, 930])
def test_pretendard_matches_instance(ps, static, w):
    font = static("pretendard", w)
    for name in PRETENDARD_GLYPHS:
        o = ps.outline(name, w)
        assert max_abs_diff(o.coords[:-4], _instance_coords(font, name)) <= 1, name
        assert otRound(o.advance()) == font["hmtx"][name][0], name


WANTED_GLYPHS = ("A", "Aacute", "uni01CD", "d", "zero")


@pytest.mark.parametrize("w", [400, 550, 750, 850, 1000])
def test_wanted_matches_instance(ws, static, w):
    font = static("wanted", w)
    for name in WANTED_GLYPHS:
        o = ws.outline(name, w)
        assert max_abs_diff(o.coords[:-4], _instance_coords(font, name)) <= 1, name
        assert otRound(o.advance()) == font["hmtx"][name][0], name


def test_weight_range_checked(ps, ws):
    with pytest.raises(ValueError):
        ps.outline("l", 1101)
    with pytest.raises(ValueError):
        ws.outline("A", 399)


@pytest.mark.parametrize('w', [250, 381.25, 655, 900])
def test_shs_sampler_matches_fonttools(shs_cn, w):
    from fontTools.pens.recordingPen import DecomposingRecordingPen
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    from roofsans.sampling import ShsSampler

    sampler = ShsSampler(shs_cn)
    glyphs = shs_cn.getGlyphSet(location={'wght': w})
    for cp in map(ord, '一口龍熙'):
        name = shs_cn.getBestCmap()[cp]
        pen = DecomposingRecordingPen(glyphs)
        glyphs[name].draw(pen)
        ttpen = TTGlyphPen(None)
        pen.replay(ttpen)
        glyph = ttpen.glyph(round=lambda x: x)
        assert max_abs_diff(sampler.outline(name, w).points, glyph.coordinates) <= 1e-6
        assert sampler.advance(name, w) == pytest.approx(1000)


def test_shs_sampler_rejects_out_of_range(shs_cn):
    from roofsans.sampling import ShsSampler

    sampler = ShsSampler(shs_cn)
    for w in (249, 901):
        with pytest.raises(ValueError):
            sampler.outline(shs_cn.getBestCmap()[ord('一')], w)
