"""Outline emboldening: a port of FreeType's ``FT_Outline_EmboldenXY``."""

from __future__ import annotations

import math

from roofsans.outline import Outline, Point


def _signed_area2(o: Outline) -> float:
    """Twice the total signed area of the point polygons; negative is clockwise."""
    area = 0.0
    for pts in o.contours():
        area += sum(pts[i - 1][0] * pts[i][1] - pts[i][0] * pts[i - 1][1] for i in range(len(pts)))
    return area


def embolden_xy(o: Outline, x_strength: float, y_strength: float) -> Outline:
    """Return ``o`` thickened by ``x_strength``/``y_strength`` units (``src/base/ftoutln.c``).

    Point count, order, flags, and the phantom points stay as they are. Orientation
    comes from the total signed area, so outer contours grow whichever way a glyph
    runs (mirrored components reverse their contours).
    """
    xs, ys = x_strength / 2, y_strength / 2
    if xs == 0 and ys == 0:
        return Outline(list(o.coords), list(o.end_pts), list(o.flags))
    area = _signed_area2(o)
    if area == 0:
        if o.end_pts:
            raise ValueError("cannot embolden an outline without orientation")
        return Outline(list(o.coords), list(o.end_pts), list(o.flags))
    truetype = area < 0

    pts = [list(p) for p in o.points]
    first = 0
    for last in o.end_pts:
        in_v: Point = (0.0, 0.0)
        anchor: Point = (0.0, 0.0)
        l_in = l_anchor = 0.0
        # j cycles through the points; i advances only when points move; k is the first moved point.
        i, j, k = last, first, -1
        while j != i and i != k:
            if j != k:
                dx, dy = pts[j][0] - pts[i][0], pts[j][1] - pts[i][1]
                l_out = math.hypot(dx, dy)
                if l_out == 0:
                    j = j + 1 if j < last else first
                    continue
                out_v = (dx / l_out, dy / l_out)
            else:
                out_v, l_out = anchor, l_anchor

            if l_in != 0:
                if k < 0:
                    k, anchor, l_anchor = i, in_v, l_in
                d = in_v[0] * out_v[0] + in_v[1] * out_v[1]
                # Shift only if the turn is less than about 160 degrees.
                if d > -0.9375:
                    d += 1
                    # Shift along the lateral bisector, toward the contour's outside.
                    sx, sy = in_v[1] + out_v[1], in_v[0] + out_v[0]
                    if truetype:
                        sx = -sx
                    else:
                        sy = -sy
                    # Limit the shift so collapsing segments stay in hand.
                    q = out_v[0] * in_v[1] - out_v[1] * in_v[0]
                    if truetype:
                        q = -q
                    l = min(l_in, l_out)
                    # Non-strict inequalities avoid dividing by zero when q == l == 0.
                    sx = sx * xs / d if xs * q <= l * d else sx * l / q
                    sy = sy * ys / d if ys * q <= l * d else sy * l / q
                else:
                    sx = sy = 0.0
                while i != j:
                    pts[i][0] += xs + sx
                    pts[i][1] += ys + sy
                    i = i + 1 if i < last else first
            else:
                i = j
            in_v, l_in = out_v, l_out
            j = j + 1 if j < last else first
        first = last + 1

    return Outline([tuple(p) for p in pts] + list(o.coords[-4:]), list(o.end_pts), list(o.flags))
