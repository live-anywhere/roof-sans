import importlib.util
import os
import sys
from pathlib import Path

import skia
import uharfbuzz as hb
from fontTools.ttLib import TTFont

SPECIMEN_PY = Path(__file__).resolve().parents[2] / "verify" / "specimen.py"


def _load_specimen():
    spec = importlib.util.spec_from_file_location("specimen", SPECIMEN_PY)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses look their module up here
    spec.loader.exec_module(module)
    return module


specimen = _load_specimen()

# The specimen reviews the built font; ROOF_FONT points at another build.
ROOF = Path(os.environ.get("ROOF_FONT", "fonts/RoofSansVariable.ttf"))


def test_specimen_renders(inputs, tmp_path):
    paths = specimen.render_specimen(ROOF, inputs, tmp_path)

    sheets = [tmp_path / f"specimen_{w}.png" for w in (400, 700, 1000)]
    zooms = [tmp_path / f"zoom_{w}.png" for w in (400, 700, 1000)]
    assert paths == sheets + zooms
    for path in paths:
        image = skia.Image.open(str(path))
        assert image.width() >= 1000, (path, image.width())

    lines = specimen.load_lines()
    assert len(lines) == 9
    font = hb.Font(hb.Face(hb.Blob.from_file_path(str(ROOF))))
    order = TTFont(ROOF, lazy=True).getGlyphOrder()
    notdef = [
        (n, w)
        for w in (400, 700, 1000)
        for n, line in enumerate(lines, 1)
        if ".notdef" in [order[g.gid] for g in specimen.shape(font, line["text"], line["language"], w)]
    ]
    assert not notdef


def test_naive_row_uses_advances_at_weight(inputs):
    # Wanted Sans has no HVAR; its `zero` widens with weight through gvar phantom points.
    fonts = specimen.Fonts(ROOF, inputs)
    assert [fonts.naive_row("0", w).advance for w in (400, 750, 1000)] == [1280, 1373, 1440]


def test_roof_row_is_shaped_per_script_run(inputs):
    # Shaped as one run, line 3's `—` sits in context with the Hangul and becomes
    # `emdash.case`; renderers end the Han run before it and draw the plain `emdash`.
    fonts = specimen.Fonts(ROOF, inputs)
    line = specimen.load_lines()[2]
    names = [name for _, name, *_ in fonts.roof_row(line["text"], line["language"], 400).glyphs]
    assert "emdash" in names and "emdash.case" not in names
