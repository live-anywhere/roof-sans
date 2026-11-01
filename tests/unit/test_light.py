"""Light solve and in-memory extension, without reading or building Roof Sans."""

from copy import deepcopy

import pytest
from fontTools.ttLib.tables.TupleVariation import TupleVariation
from fontTools.misc.roundTools import otRound

from roofsans.axis import roof_norm, roof_wght
from roofsans.finalize import LIGHT_INSTANCES
from roofsans.light import extend_wanted, ks_hangul, solve
from roofsans.sampling import WantedSampler
from roofsans.variations import LIGHT_REGION, PJ_LIGHT_SCALE, remap_pretendard_tuples


@pytest.fixture(scope="module")
def light_data(wanted, pretendard):
    # solve is the expensive part (~11 s); all tests here share this one result.
    return solve(wanted, pretendard)


def test_ks_hangul():
    syllables = ks_hangul()
    assert len(syllables) == len(set(syllables)) == 2350
    assert all(0xAC00 <= cp <= 0xD7A3 for cp in syllables)


def test_solve(light_data):
    assert 100 <= light_data.wght <= 200
    assert light_data.tuples
    assert all(tv.axes == {"wght": (-1, -1, 0)} for tv in light_data.tuples.values())
    assert len(light_data.clamped) <= 10
    assert all(light_data.wght < w <= 150 for w in light_data.clamped.values())


def test_extend_keeps_original_range(wanted, ws, light_data):
    font = deepcopy(wanted)
    extend_wanted(font, light_data)
    assert font["fvar"].axes[0].minValue == 100
    sampler = WantedSampler(font)
    cmap = wanted.getBestCmap()
    for char in "Al0한꿈":
        name = cmap[ord(char)]
        for weight in (400, 550, 750, 1000):
            assert sampler.outline(name, weight) == ws.outline(name, weight)
            assert sampler.advance(name, weight) == ws.advance(name, weight)
    assert wanted["fvar"].axes[0].minValue == 400


def test_pretendard_light_tuple_scaled_with_omissions():
    coords = [None, (17, -31), (-40, 21), None, (0, 0)]
    source = TupleVariation({"wght": (-1, -1, 0)}, coords)
    (result,) = remap_pretendard_tuples([source])
    assert PJ_LIGHT_SCALE == 300 / 355
    assert result.axes == {"wght": LIGHT_REGION}
    assert result.coordinates == [None if p is None else (otRound(p[0] * 300 / 355), otRound(p[1] * 300 / 355)) for p in coords]
    assert source.coordinates == coords


def test_light_instance_names():
    assert LIGHT_INSTANCES == ((100, "Thin"), (200, "ExtraLight"), (300, "Light"))


@pytest.mark.parametrize("weight, norm", [(100, -1), (250, -0.5), (400, 0), (550, 0.25), (1000, 1)])
def test_light_axis_normalization(weight, norm):
    assert roof_norm(weight) == norm
    assert roof_wght(norm) == weight
