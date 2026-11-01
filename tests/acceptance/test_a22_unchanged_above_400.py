"""Acceptance 22: disabling light rules reproduces the pre-extension font."""

import hashlib
import os
from pathlib import Path

import pytest
from fontTools.ttLib import TTFont
from test_a01_wanted_identity import structure

pytestmark = pytest.mark.acceptance


@pytest.fixture(scope="module")
def nolight_path(inputs):
    if os.environ.get("ROOF_NOLIGHT"):
        return Path(os.environ["ROOF_NOLIGHT"])
    from roofsans.build import build

    return build(Path("build/test-nolight/RoofSansVariable.ttf"), inputs, light=False)


def test_without_light_reproduces_pre_extension_font(nolight_path):
    assert hashlib.sha256(nolight_path.read_bytes()).hexdigest() == (
        "da7a7fe8197d2b5209cac0a9b6a313e42a975762f2015ab26b5be3dc7e75b87d"
    )


def test_all_default_and_positive_glyph_data_unchanged(nolight_path, roof):
    original = TTFont(nolight_path)
    assert original.getGlyphOrder() == roof.getGlyphOrder()
    bad = []
    for name in original.getGlyphOrder():
        if structure(original["glyf"][name]) != structure(roof["glyf"][name]):
            bad.append((name, "default outline"))
        if original["hmtx"][name] != roof["hmtx"][name]:
            bad.append((name, "default metrics"))
        positive = [tv for tv in roof["gvar"].variations.get(name, []) if tv.axes["wght"][1] > 0]
        if positive != original["gvar"].variations.get(name, []):
            bad.append((name, "positive tuples"))
    assert not bad, f"{len(bad)} differences above 400: {bad[:20]}"


def test_positive_feature_variations_unchanged(nolight_path, roof):
    """At every t ≥ 0 the same FeatureVariations record applies, with the same substitutions.

    The kana records whose thresholds lie below 400 differ in their stored minimum (clamped to
    0 without the light weights, negative with them), so the records are compared by what
    applies at each location, not by their stored conditions.
    """

    def records(font):
        out = []
        for record in font["GSUB"].table.FeatureVariations.FeatureVariationRecord:
            ranges = [(c.FilterRangeMinValue, c.FilterRangeMaxValue) for c in record.ConditionSet.ConditionTable]
            substitutions = tuple((r.FeatureIndex, tuple(r.Feature.LookupListIndex))
                                  for r in record.FeatureTableSubstitution.SubstitutionRecord)
            out.append((ranges, substitutions))
        return out

    def active(recs, t):
        return next((subs for ranges, subs in recs if all(lo <= t <= hi for lo, hi in ranges)), ())

    light, original = records(roof), records(TTFont(nolight_path))
    edges = {lo for recs in (light, original) for ranges, _ in recs for lo, _ in ranges if lo >= 0}
    locations = sorted({i / 64 for i in range(65)} | edges | {e - 1 / 16384 for e in edges if e > 0})
    assert original and [active(light, t) for t in locations] == [active(original, t) for t in locations]
