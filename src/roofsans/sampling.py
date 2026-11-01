"""Outlines of the input fonts at any weight, with composites decomposed."""

from __future__ import annotations

from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import OVERLAP_COMPOUND
from fontTools.varLib.iup import iup_delta
from fontTools.varLib.models import piecewiseLinearMap, supportScalar

from roofsans.axis import roof_norm
from roofsans.outline import Outline, Point, combine


def _transform(pts: list[Point], m, dx: float, dy: float) -> list[Point]:
    # Same convention as fontTools GlyphCoordinates.transform; the offset is unscaled.
    (a, b), (c, d) = m
    return [(x * a + y * c + dx, x * b + y * d + dy) for x, y in pts]


class _Sampler:
    def __init__(self, font: TTFont) -> None:
        self._glyf = font["glyf"]
        self._hmtx = font["hmtx"].metrics
        self._vmtx = font["vmtx"].metrics if "vmtx" in font else None
        self._gvar = font["gvar"].variations
        self._data: dict[str, tuple] = {}

    def _norm(self, wght: float) -> float:
        raise NotImplementedError

    def _scalar(self, support: dict, norm: float) -> float:
        return supportScalar({"wght": norm}, support)

    def _glyph_data(self, name: str) -> tuple:
        """Return (default coords, controls, [(support, deltas with IUP expanded)])."""
        if name not in self._data:
            coords, controls = self._glyf._getCoordinatesAndControls(name, self._hmtx, self._vmtx)
            coords = [tuple(p) for p in coords]
            tuples = []
            for tv in self._gvar.get(name, []):
                deltas = tv.coordinates
                if None in deltas:
                    if controls.numberOfContours < 0:
                        # Composite glyphs have no IUP: omitted points do not move.
                        deltas = [d or (0, 0) for d in deltas]
                    else:
                        deltas = iup_delta(deltas, coords, controls.endPts)
                tuples.append((tv.axes, [tuple(d) for d in deltas]))
            self._data[name] = (coords, controls, tuples)
        return self._data[name]

    def _varied(self, name: str, norm: float) -> tuple[list[Point], object]:
        coords, controls, tuples = self._glyph_data(name)
        out = list(coords)
        for support, deltas in tuples:
            s = self._scalar(support, norm)
            if s == 0:
                continue
            out = [(p[0] + d[0] * s, p[1] + d[1] * s) for p, d in zip(out, deltas)]
        return out, controls

    def _outline(self, name: str, norm: float) -> Outline:
        coords, controls = self._varied(name, norm)
        if controls.numberOfContours >= 0:
            return Outline(coords, list(controls.endPts), list(controls.flags))
        glyph = self._glyf[name]
        parts = []
        for i, comp in enumerate(glyph.components):
            part = self._outline(comp.glyphName, norm)
            dx, dy = coords[i]
            m = getattr(comp, "transform", ((1, 0), (0, 1)))
            moved = _transform(part.points, m, dx, dy)
            parts.append(Outline(moved + part.coords[-4:], part.end_pts, part.flags))
        overlap = any(c.flags & OVERLAP_COMPOUND for c in glyph.components)
        return combine(parts, coords[-4:], overlap)

    def outline(self, name: str, wght: float) -> Outline:
        return self._outline(name, self._norm(wght))

    def advance(self, name: str, wght: float) -> float:
        coords, _ = self._varied(name, self._norm(wght))
        return coords[-3][0] - coords[-4][0]


class PretendardSampler(_Sampler):
    """Pretendard JP (masters 45/400/930), extrapolated linearly past 930 up to 1100."""

    def _norm(self, wght: float) -> float:
        if not 45 <= wght <= 1100:
            raise ValueError(f"Pretendard weight {wght} is outside 45–1100")
        return (wght - 400) / 355 if wght < 400 else (wght - 400) / 530

    def _scalar(self, support: dict, norm: float) -> float:
        # The (0, 1, 1) tuple keeps its linear ramp past the 930 master.
        return supportScalar({"wght": norm}, support, extrapolate=True, axisRanges={"wght": (-1.0, 1.0)})


class WantedSampler(_Sampler):
    """Wanted Sans (masters 400/750/1000); its axis is the Roof axis."""

    def _norm(self, wght: float) -> float:
        if not 400 <= wght <= 1000:
            raise ValueError(f"Wanted Sans weight {wght} is outside 400–1000")
        return roof_norm(wght)


class ShsSampler(_Sampler):
    """Source Han Sans, including its non-linear avar weight mapping."""

    def __init__(self, font: TTFont) -> None:
        super().__init__(font)
        self._segments = font["avar"].segments["wght"]

    def _norm(self, wght: float) -> float:
        if not 250 <= wght <= 900:
            raise ValueError(f"Source Han Sans weight {wght} is outside 250–900")
        return piecewiseLinearMap((wght - 250) / 650, self._segments)
