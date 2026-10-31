"""Render the Acceptance 9 specimen sheet: Roof Sans rows next to the naive merge.

Each line of ``specimen_lines.json`` gets two rows per weight. The Roof row is shaped
with HarfBuzz per script run under the line's language and drawn from the built
font's outlines at HarfBuzz positions. The naive row takes each character from Wanted Sans when Wanted
maps it, else from Pretendard JP at ``min(w, 930)`` (tinted), unshaped. Guide lines
mark the baseline, the x-height (1032), and the cap height (1448).

Usage: ``uv run python verify/specimen.py --out build/specimen``
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import skia
import uharfbuzz as hb
from fontTools.pens.basePen import BasePen, NullPen
from fontTools.ttLib import TTFont

from roofsans.inputs import Inputs, ensure_inputs

LINES_PATH = Path(__file__).with_name("specimen_lines.json")
DEFAULT_ROOF = Path("fonts/RoofSansVariable.ttf")
WEIGHTS = (400, 700, 1000)
PRETENDARD_MAX_WGHT = 930
SHEET_PX_PER_EM = 64
ZOOM_PX_PER_EM = 128
ZOOM_LINES = (8, 9)
GUIDES = ((0, 0xFFB0B0B0), (1032, 0xFF4A90E2), (1448, 0xFFB0B0B0))
PRETENDARD_TINT = 0xFFD0461E
LABEL_COLOR = 0xFF707070
SEPARATOR_COLOR = 0xFFE0E0E0
MARGIN = 20


@dataclass(frozen=True)
class Shaped:
    """One shaped glyph: its glyph id and pen position in font units."""

    gid: int
    x: int
    y: int


@dataclass(frozen=True)
class Row:
    """Glyphs to draw on one line, positioned in font units, and the line's advance."""

    glyphs: list[tuple[object, str, float, float, int]]  # glyph set, name, x, y, color
    advance: float


class _SkiaPen(BasePen):
    """Draw font units into a skia path at ``scale``, origin at (dx, dy), y pointing down."""

    def __init__(self, glyph_set, scale: float, dx: float, dy: float) -> None:
        super().__init__(glyph_set)
        self.path = skia.Path()
        self.scale = scale
        self.dx = dx
        self.dy = dy

    def _pt(self, p):
        return p[0] * self.scale + self.dx, self.dy - p[1] * self.scale

    def _moveTo(self, p):
        self.path.moveTo(*self._pt(p))

    def _lineTo(self, p):
        self.path.lineTo(*self._pt(p))

    def _qCurveToOne(self, p1, p2):
        self.path.quadTo(*self._pt(p1), *self._pt(p2))

    def _curveToOne(self, p1, p2, p3):
        self.path.cubicTo(*self._pt(p1), *self._pt(p2), *self._pt(p3))

    def _closePath(self):
        self.path.close()


def load_lines(path: Path = LINES_PATH) -> list[dict]:
    """Return the specimen lines: ``[{"language": str | None, "text": str}]``."""
    return json.loads(path.read_text(encoding="utf-8"))


def shape(font: hb.Font, text: str, language: str | None, wght: float) -> list[Shaped]:
    """Shape ``text`` per script run at ``wght``; return each glyph with its pen position in font units."""
    return _shape(font, text, language, wght)[0]


def script_runs(text: str) -> list[tuple[str | None, str]]:
    """Split ``text`` into script runs the way renderers itemize it.

    Common and inherited characters (HarfBuzz guesses no script for them) join the
    preceding run; leading ones join the first run with a script.
    """
    runs: list[list] = []
    for ch in text:
        probe = hb.Buffer()
        probe.add_str(ch)
        probe.guess_segment_properties()
        script = probe.script
        if runs and (script is None or runs[-1][0] in (None, script)):
            runs[-1][0] = runs[-1][0] or script
            runs[-1][1] += ch
        else:
            runs.append([script, ch])
    return [(script, run) for script, run in runs]


def _shape(font: hb.Font, text: str, language: str | None, wght: float) -> tuple[list[Shaped], int]:
    font.set_variations({"wght": wght})
    out, x, y = [], 0, 0
    for script, run in script_runs(text):
        buf = hb.Buffer()
        buf.add_str(run)
        if script:
            buf.script = script
        if language:
            buf.language = language
        buf.guess_segment_properties()
        hb.shape(font, buf, {})
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            out.append(Shaped(info.codepoint, x + pos.x_offset, y + pos.y_offset))
            x += pos.x_advance
            y += pos.y_advance
    return out, x


class Fonts:
    """The built font and both inputs, with glyph sets cached per weight."""

    def __init__(self, roof: Path, inputs: Inputs) -> None:
        self.roof = TTFont(roof)
        self.roof_hb = hb.Font(hb.Face(hb.Blob.from_file_path(str(roof))))
        self.order = self.roof.getGlyphOrder()
        self.upem = self.roof["head"].unitsPerEm  # Wanted Sans and Pretendard JP share it
        self.wanted = TTFont(inputs.wanted)
        self.pretendard = TTFont(inputs.pretendard)
        self.wanted_cmap = self.wanted.getBestCmap()
        self.pretendard_cmap = self.pretendard.getBestCmap()
        self._sets: dict[tuple[int, float], object] = {}

    def glyph_set(self, font: TTFont, wght: float):
        key = (id(font), wght)
        if key not in self._sets:
            self._sets[key] = font.getGlyphSet(location={"wght": wght})
        return self._sets[key]

    def roof_row(self, text: str, language: str | None, wght: float, color: int = skia.ColorBLACK) -> Row:
        glyph_set = self.glyph_set(self.roof, wght)
        shaped, advance = _shape(self.roof_hb, text, language, wght)
        return Row([(glyph_set, self.order[g.gid], g.x, g.y, color) for g in shaped], advance)

    def naive_row(self, text: str, wght: float) -> Row:
        wanted = self.glyph_set(self.wanted, wght)
        pretendard = self.glyph_set(self.pretendard, min(wght, PRETENDARD_MAX_WGHT))
        glyphs, x = [], 0.0
        for ch in text:
            cp = ord(ch)
            if cp in self.wanted_cmap:
                glyph_set, name, color = wanted, self.wanted_cmap[cp], skia.ColorBLACK
            elif cp in self.pretendard_cmap:
                glyph_set, name, color = pretendard, self.pretendard_cmap[cp], PRETENDARD_TINT
            else:
                continue
            glyphs.append((glyph_set, name, x, 0.0, color))
            # Neither input has HVAR: the advance at this weight comes from the gvar
            # phantom points, which only drawing applies; `.width` before drawing is
            # the default master's.
            glyph = glyph_set[name]
            glyph.draw(NullPen())
            x += glyph.width
        return Row(glyphs, x)


def _draw_glyphs(canvas: skia.Canvas, row: Row, scale: float, x0: float, baseline: float) -> None:
    for glyph_set, name, x, y, color in row.glyphs:
        pen = _SkiaPen(glyph_set, scale, x0 + x * scale, baseline - y * scale)
        glyph_set[name].draw(pen)
        canvas.drawPath(pen.path, skia.Paint(AntiAlias=True, Color=color))


def _sheet(fonts: Fonts, numbered: list[tuple[int, dict]], wght: float, px_per_em: float) -> skia.Image:
    """Interleave a Roof row and a naive row per line, each under a small label."""
    scale = px_per_em / fonts.upem
    label_scale = scale * 0.3
    label_h = px_per_em * 0.45
    glyph_h = px_per_em * 1.6
    ascent = px_per_em * 1.15  # room above the baseline for stacked marks on capitals

    rows = []
    for n, line in numbered:
        language = line["language"]
        tag = f"{n} {language or 'none'}"
        rows.append((f"{tag} Roof {wght}", fonts.roof_row(line["text"], language, wght)))
        rows.append((f"{tag} naive {wght}", fonts.naive_row(line["text"], wght)))
    labels = [fonts.roof_row(text, None, 400, LABEL_COLOR) for text, _ in rows]

    width = int(MARGIN * 2 + max(row.advance * scale for _, row in rows))
    height = int(len(rows) * (label_h + glyph_h) + MARGIN)
    surface = skia.Surface(width, height)
    canvas = surface.getCanvas()
    canvas.clear(skia.ColorWHITE)
    top = 0.0
    for i, ((_, row), label) in enumerate(zip(rows, labels)):
        if i and i % 2 == 0:
            canvas.drawLine(0, top, width, top, skia.Paint(Color=SEPARATOR_COLOR, StrokeWidth=1))
        _draw_glyphs(canvas, label, label_scale, MARGIN, top + label_h * 0.8)
        baseline = top + label_h + ascent
        for y, color in GUIDES:
            gy = baseline - y * scale
            canvas.drawLine(0, gy, width, gy, skia.Paint(Color=color, StrokeWidth=1))
        _draw_glyphs(canvas, row, scale, MARGIN, baseline)
        top += label_h + glyph_h
    return surface.makeImageSnapshot()


def render_specimen(roof: Path, inputs: Inputs, out_dir: Path, weights=WEIGHTS) -> list[Path]:
    """Write ``specimen_<w>.png`` (all lines) and ``zoom_<w>.png`` (lines 8–9) per weight.

    Returns the sheets in weight order, then the zooms in weight order.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    fonts = Fonts(roof, inputs)
    numbered = list(enumerate(load_lines(), 1))
    zoomed = [(n, line) for n, line in numbered if n in ZOOM_LINES]
    sheets, zooms = [], []
    for w in weights:
        for name, lines, px, paths in (
            (f"specimen_{w}.png", numbered, SHEET_PX_PER_EM, sheets),
            (f"zoom_{w}.png", zoomed, ZOOM_PX_PER_EM, zooms),
        ):
            path = out_dir / name
            _sheet(fonts, lines, w, px).save(str(path), skia.kPNG)
            paths.append(path)
    return sheets + zooms


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Render the Roof Sans specimen sheet against the naive merge.")
    parser.add_argument("--out", type=Path, required=True, help="output directory for the PNGs")
    parser.add_argument("--font", type=Path, default=DEFAULT_ROOF, help="built Roof Sans font")
    args = parser.parse_args(argv)
    for path in render_specimen(args.font, ensure_inputs(refs_root=Path("refs")), args.out):
        print(path)


if __name__ == "__main__":
    main()
