"""Acceptance 21: the light axis range and all named weights are advertised."""

import pytest

pytestmark = pytest.mark.acceptance

INSTANCES = (
    (100, "Thin"), (200, "ExtraLight"), (300, "Light"), (400, "Regular"),
    (500, "Medium"), (600, "SemiBold"), (700, "Bold"), (800, "ExtraBold"),
    (900, "Black"), (1000, "ExtraBlack"),
)


def test_axis_and_instances(roof):
    (axis,) = roof["fvar"].axes
    assert (axis.axisTag, axis.minValue, axis.defaultValue, axis.maxValue) == ("wght", 100, 400, 1000)
    assert axis.maxValue <= 1000 and axis.maxValue - axis.minValue <= 1000
    assert roof["OS/2"].usWeightClass == 400
    name = roof["name"]
    assert [(i.coordinates, name.getDebugName(i.subfamilyNameID), name.getDebugName(i.postscriptNameID))
            for i in roof["fvar"].instances] == [
        ({"wght": w}, label, f"RoofSans-{label}") for w, label in INSTANCES
    ]


def test_stat_has_all_ten_weights(roof):
    stat = roof["STAT"].table
    axes = stat.DesignAxisRecord.Axis
    weight_axis = next(i for i, a in enumerate(axes) if a.AxisTag == "wght")
    values = [v for v in stat.AxisValueArray.AxisValue if v.AxisIndex == weight_axis and v.Format == 1]
    assert stat.AxisValueCount == len(stat.AxisValueArray.AxisValue)
    assert len(values) == 10
    assert [(v.AxisIndex, v.Value, roof["name"].getDebugName(v.ValueNameID))
            for v in values] == [(weight_axis, w, label) for w, label in INSTANCES]
