"""H2: decomposable Latin and Vietnamese letters built from Wanted Sans bases and marks."""

from __future__ import annotations

import sys
import unicodedata
import weakref
from dataclasses import dataclass
from functools import cached_property
from typing import Literal

from fontTools.misc.roundTools import otRound
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables
from fontTools.varLib.models import supportScalar

from roofsans.axis import COMPOSITE_LOCS, H4_LOCS
from roofsans.harmonize import apply_zone_map
from roofsans.newglyph import NewGlyph, Part, composite_glyph
from roofsans.rules import h4_letters
from roofsans.selection import Rule, Zone

MarkClass = Literal["top", "bottom", "horn"]
Anchor = tuple[int, int]

# Wanted Sans's mark-to-base lookup for letters; marks with an anchor y > 0 sit above.
WANTED_LETTER_LOOKUP = 7
# Under a mark above, i and j lose their dot, as in Wanted Sans's own í and ĵ.
_DOTLESS = {"i": "dotlessi", "j": "uni0237"}
# Unicode combining class → mark class, for the H4 marks Wanted Sans lacks.
_CCC_CLASS: dict[int, MarkClass] = {230: "top", 220: "bottom", 202: "bottom", 216: "horn"}
_HORN = 0x031B
_HORN_LETTERS = {"o": 0x01A1, "u": 0x01B0, "O": 0x01A0, "U": 0x01AF}
# Ruling R25: Pretendard anchors are re-expressed through o (lowercase) or O (capital).
_REFERENCE = {Zone.LOWER: "o", Zone.CAPITAL: "O"}
# ſ has no Pretendard anchor; Wanted's dot keeps the dot gap of Pretendard's ẛ (R25, R31).
_LONG_S, _LONG_S_DOT, _DOT_ABOVE = 0x017F, 0x1E9B, 0x0307
# Same-class stacking keeps the gap between e and the circumflex of Wanted's ê.
_GAP_COMPOSITE, _GAP_BASE, _GAP_MARK = "ecircumflex", "e", "uni0302"


@dataclass(frozen=True)
class _MarkLookup:
    index: int
    marks: dict[str, tuple[int, int, int]]  # mark → (class index, x, y) at the default
    bases: dict[str, list[Anchor | None]]  # base → anchor per class index at the default
    mark_anchors: dict[str, otTables.Anchor]  # the same anchors with their devices
    base_anchors: dict[str, list[otTables.Anchor | None]]
    classes: dict[MarkClass, int]  # "top" / "bottom" → class index

    def class_index(self, cls: MarkClass) -> int | None:
        """The class of this subtable's marks above or below, if it has one."""
        return self.classes.get(cls)


def _classes(marks: dict[str, tuple[int, int, int]], bases: dict[str, list[Anchor | None]]) -> dict[MarkClass, int]:
    """Which class sits above and which below.

    With two classes, the one whose base anchors sit higher (median y) is above; mark anchor
    y does not tell, since Pretendard anchors some marks above with y ≤ 0. A one-class
    subtable (overlays, the ogonek) sits above when its first mark's anchor y > 0.
    """
    count = 1 + max(c for c, _, _ in marks.values())
    if count == 1:
        _, _, y = next(iter(marks.values()))
        return {"top" if y > 0 else "bottom": 0}
    medians = []
    for c in range(count):
        ys = sorted(row[c][1] for row in bases.values() if row[c] is not None)
        medians.append(ys[len(ys) // 2])
    top = max(range(count), key=medians.__getitem__)
    return {"top": top, "bottom": min(range(count), key=medians.__getitem__)}


def _mark_lookups(font: TTFont) -> list[_MarkLookup]:
    """The MarkBasePos subtables of ``font``'s ``mark`` feature, in lookup order."""
    gpos = font["GPOS"].table
    features = {tuple(f.Feature.LookupListIndex) for f in gpos.FeatureList.FeatureRecord if f.FeatureTag == "mark"}
    if len(features) != 1:
        raise ValueError(f"expected one set of mark lookups, found {sorted(features)}")
    (indices,) = features
    out = []
    for i in indices:
        for st in gpos.LookupList.Lookup[i].SubTable:
            st = getattr(st, "ExtSubTable", st)
            if not isinstance(st, otTables.MarkBasePos):
                continue
            mark_records = dict(zip(st.MarkCoverage.glyphs, st.MarkArray.MarkRecord))
            base_anchors = {g: list(r.BaseAnchor) for g, r in zip(st.BaseCoverage.glyphs, st.BaseArray.BaseRecord)}
            marks = {g: (r.Class, r.MarkAnchor.XCoordinate, r.MarkAnchor.YCoordinate) for g, r in mark_records.items()}
            bases = {g: [(a.XCoordinate, a.YCoordinate) if a else None for a in row] for g, row in base_anchors.items()}
            mark_anchors = {g: r.MarkAnchor for g, r in mark_records.items()}
            out.append(_MarkLookup(i, marks, bases, mark_anchors, base_anchors, _classes(marks, bases)))
    return out


def _device_evaluator(font: TTFont, scalar):
    """Anchor → its (x, y) where ``scalar(support)`` gives each region's scalar, from GDEF's
    ItemVariationStore (ruling R35: both inputs' anchors vary through device tables)."""
    store = font["GDEF"].table.VarStore
    tags = [a.axisTag for a in font["fvar"].axes]
    scalars = [
        scalar({tag: (a.StartCoord, a.PeakCoord, a.EndCoord) for tag, a in zip(tags, r.VarRegionAxis)})
        for r in store.VarRegionList.Region
    ]

    def delta(dev) -> float:
        if dev is None:
            return 0.0
        if dev.DeltaFormat != 0x8000:
            raise ValueError(f"unexpected device format {dev.DeltaFormat}")
        data = store.VarData[dev.StartSize]
        return sum(d * scalars[ri] for d, ri in zip(data.Item[dev.EndSize], data.VarRegionIndex))

    def at(anchor: otTables.Anchor) -> tuple[float, float]:
        x, y = anchor.XCoordinate, anchor.YCoordinate
        if anchor.Format == 3:
            return (x + delta(anchor.XDeviceTable), y + delta(anchor.YDeviceTable))
        return (float(x), float(y))

    return at


def _letter_lookups(lookups: list[_MarkLookup]) -> list[_MarkLookup]:
    """The lookups with a class above and a class below (not the overlay or ogonek lookups)."""
    return [lk for lk in lookups if lk.class_index("top") is not None and lk.class_index("bottom") is not None]


def _covering(lookups: list[_MarkLookup], base: str, mark: str) -> _MarkLookup | None:
    for lk in lookups:
        if mark in lk.marks and base in lk.bases and lk.bases[base][lk.marks[mark][0]] is not None:
            return lk
    return None


def _wanted_offsets(font: TTFont, name: str, t: float) -> list[tuple[float, float]]:
    """Component offsets of Wanted Sans composite ``name`` at Roof normalized ``t``."""
    comps = font["glyf"][name].components
    out = [[float(c.x), float(c.y)] for c in comps]
    for tv in font["gvar"].variations.get(name, []):
        s = supportScalar({"wght": t}, tv.axes)
        for i, d in enumerate(tv.coordinates[: len(comps)]):
            if s and d is not None:
                out[i][0] += d[0] * s
                out[i][1] += d[1] * s
    return [(x, y) for x, y in out]


def _center_x(bounds: tuple[float, float, float, float]) -> float:
    return (bounds[0] + bounds[2]) / 2


class _Anchors:
    """Anchors of one build context at Roof normalized locations (ruling R35)."""

    def __init__(self, ctx) -> None:
        self.ctx = ctx
        self.wanted = _mark_lookups(ctx.wanted)
        self.pretendard = _mark_lookups(ctx.pretendard)
        letters = [lk for lk in self.wanted if lk.index == WANTED_LETTER_LOOKUP]
        lookup_type = ctx.wanted["GPOS"].table.LookupList.Lookup[WANTED_LETTER_LOOKUP].LookupType
        if lookup_type != 4 or len(letters) != 1:
            raise ValueError(f"Wanted Sans GPOS lookup {WANTED_LETTER_LOOKUP} is not one MarkBasePos subtable")
        self.letters = letters[0]
        self.wanted_glyphs = set(ctx.wanted.getGlyphOrder())
        self.pcmap = ctx.pretendard.getBestCmap()
        self.h4_codepoints = {ctx.cmap[cp]: cp for cp in ctx.selection.codepoints(Rule.H4_LETTER)}
        self._wanted_at = {}
        self._pretendard_at = {}

    # Anchors with their device deltas.

    def wanted_at(self, anchor: otTables.Anchor, t: float) -> tuple[float, float]:
        """A Wanted Sans anchor at Roof normalized ``t`` (Wanted's axis is the Roof axis)."""
        if t not in self._wanted_at:
            self._wanted_at[t] = _device_evaluator(self.ctx.wanted, lambda s: supportScalar({"wght": t}, s))
        return self._wanted_at[t](anchor)

    def pretendard_at(self, anchor: otTables.Anchor, w: float) -> tuple[float, float]:
        """A Pretendard anchor at Pretendard weight ``w``, extrapolated past 930 as the sampler does."""
        if w not in self._pretendard_at:
            ps = self.ctx.ps
            norm = ps._norm(w)
            self._pretendard_at[w] = _device_evaluator(self.ctx.pretendard, lambda s: ps._scalar(s, norm))
        return self._pretendard_at[w](anchor)

    def _h4_interpolated(self, f, t: float) -> tuple[float, ...]:
        """``f(loc, w′)`` at each H4 master, interpolated to ``t`` as the H4 glyphs are."""
        params = h4_letters.params(self.ctx)
        values = [f(loc, params[loc].w_prime) for loc in H4_LOCS]
        return tuple(_interpolate(H4_LOCS, list(v), t) for v in zip(*values))

    def letter_anchor(self, base: str, cls: MarkClass, t: float) -> tuple[float, float] | None:
        anchor = self.letters.base_anchors[base][self.letters.class_index(cls)]
        return None if anchor is None else self.wanted_at(anchor, t)

    def gap(self, t: float) -> float:
        """Clearance between ``e``'s top and the circumflex's ink bottom in Wanted's ``ê`` at ``t``."""
        names = [c.glyphName for c in self.ctx.wanted["glyf"][_GAP_COMPOSITE].components]
        dy = _wanted_offsets(self.ctx.wanted, _GAP_COMPOSITE, t)[names.index(_GAP_MARK)][1]
        return dy + self.ctx.outline(_GAP_MARK, t).bounds()[1] - self.ctx.outline(_GAP_BASE, t).bounds()[3]

    def derived_anchor(self, base: str, cls: MarkClass, t: float) -> tuple[float, float]:
        """An anchor for a Wanted letter its lookup lacks (``ae``): the ink center x at the
        height of ``o``'s (or ``O``'s) anchor, as most of Wanted's letter anchors sit."""
        cp = min(c for c, g in self.ctx.wanted.getBestCmap().items() if g == base)
        zone = Zone.CAPITAL if unicodedata.category(chr(cp)) in ("Lu", "Lt") else Zone.LOWER
        y = self.letter_anchor(_REFERENCE[zone], cls, t)[1]
        return (_center_x(self.ctx.outline(base, t).bounds()), y)

    # Pretendard anchors in Wanted Sans's convention (rulings R25, R35).

    def _zone_map(self, zone: Zone, t: float = 0.0):
        p = h4_letters.params(self.ctx)[t]
        return p.lower_map if zone is Zone.LOWER else p.capital_map

    def _pretendard_anchor(self, glyph: str, cls: MarkClass) -> otTables.Anchor | None:
        """Pretendard's base anchor of ``glyph`` for ``cls``, from the first letter lookup that has one."""
        for lk in _letter_lookups(self.pretendard):
            c = lk.class_index(cls)
            if glyph in lk.base_anchors and lk.base_anchors[glyph][c] is not None:
                return lk.base_anchors[glyph][c]
        return None

    def converted(self, anchor, ref, zone: Zone, cls: MarkClass, t: float) -> tuple[float, float]:
        """Pretendard ``anchor`` at ``t``: x as Pretendard has it at w′, y re-expressed against
        reference letter ``_REFERENCE[zone]``, whose Pretendard anchor is ``ref``, per H4 master."""

        def at(loc: float, w: float) -> tuple[float, float]:
            (x, y), (_, ref_y) = self.pretendard_at(anchor, w), self.pretendard_at(ref, w)
            m = self._zone_map(zone, loc)
            return (x, apply_zone_map(m, y) - apply_zone_map(m, ref_y))

        x, dy = self._h4_interpolated(at, t)
        return (x, self.letter_anchor(_REFERENCE[zone], cls, t)[1] + dy)

    def h4_mark_anchor(self, mark: str, cls: MarkClass, t: float) -> tuple[float, float]:
        source = self.pcmap[self.h4_codepoints[mark]]
        lk = _covering(self.pretendard, "o", source)
        if lk is None:
            raise ValueError(f"{mark}: Pretendard has no mark anchor for {source}")
        c = lk.marks[source][0]
        # Ruling R31: Pretendard's class (where it attaches on o) must match the combining class.
        if (lk.bases["o"][c][1] > 0) != (cls == "top"):
            raise ValueError(f"{mark}: Pretendard anchors {source} in a class other than {cls}")
        zone = self.ctx.selection.zone[self.h4_codepoints[mark]]
        return self.converted(lk.mark_anchors[source], lk.base_anchors["o"][c], zone, cls, t)

    def h4_base_anchor(self, base: str, cls: MarkClass, t: float) -> tuple[float, float] | None:
        cp = self.h4_codepoints[base]
        if cp == _LONG_S:
            return self._long_s_anchor(t) if cls == "top" else None
        zone = self.ctx.selection.zone[cp]
        a = self._pretendard_anchor(self.pcmap[cp], cls)
        ref = self._pretendard_anchor(_REFERENCE[zone], cls)
        if a is None or ref is None:
            return self.h4_derived_anchor(base, zone, cls, t)
        return self.converted(a, ref, zone, cls, t)

    def h4_derived_anchor(self, base: str, zone: Zone, cls: MarkClass, t: float) -> tuple[float, float] | None:
        """An anchor for an H4 letter Pretendard leaves without one (R36 amendment): the ink center x,
        at the reference letter's anchor height, moved out for taller (or deeper) letters so the
        mark keeps the reference letter's clearance from the ink."""
        ref = _REFERENCE[zone]
        ref_y = self.letter_anchor(ref, cls, t)[1]
        drawn = self.ctx.outline(base, t)
        if not drawn.points:
            return None
        ref_ink, ink = self.ctx.outline(ref, t).bounds(), drawn.bounds()
        if cls == "top":
            y = max(ref_y, ink[3] + ref_y - ref_ink[3])
        else:
            y = min(ref_y, ink[1] + ref_y - ref_ink[1])
        return (_center_x(ink), y)

    @cached_property
    def _long_s_dots(self) -> list[tuple[float, float]]:
        """Per H4 master, where Wanted's dot goes on ``ſ``: (ink center x, ink bottom).

        Ruling R31: harmonizing ``ẛ`` would pull its dot down by about δy into the ``ſ``, so the
        dot keeps Pretendard's raw gap over its ``ſ`` at w′, measured from the Roof ``ſ``'s top.
        """
        out = []
        for loc in H4_LOCS:
            drawn = self.ctx.ps.outline(self.pcmap[_LONG_S_DOT], h4_letters.params(self.ctx)[loc].w_prime)
            contours = drawn.contours()
            dot = max(contours, key=lambda c: min(y for _, y in c))
            body_top = max(y for c in contours if c is not dot for _, y in c)
            gap = min(y for _, y in dot) - body_top
            roof_top = self.ctx.outline(self.ctx.cmap[_LONG_S], loc).bounds()[3]
            out.append(((min(x for x, _ in dot) + max(x for x, _ in dot)) / 2, roof_top + gap))
        return out

    def _long_s_landing(self, t: float) -> tuple[float, float]:
        """Offset that puts Wanted's dot (ink center x, ink bottom) where ``_long_s_dots`` says at ``t``."""
        dots = self._long_s_dots
        dot_cx = _interpolate(H4_LOCS, [d[0] for d in dots], t)
        dot_bottom = _interpolate(H4_LOCS, [d[1] for d in dots], t)
        ink = self.ctx.outline(self.ctx.cmap[_DOT_ABOVE], t).bounds()
        return (dot_cx - _center_x(ink), dot_bottom - ink[1])

    def _long_s_anchor(self, t: float) -> tuple[float, float]:
        _, mx, my = mark_anchor(self.ctx, self.ctx.cmap[_DOT_ABOVE], t)
        dx, dy = self._long_s_landing(t)
        return (mx + dx, my + dy)

    # Horn letters.

    @cached_property
    def _horn_measures(self) -> dict[str, tuple[float, float, Zone]]:
        """Per base: (rx, ry, zone) from the horn contour of Pretendard's horn letter at 400.

        The horn contour is the one the letter has beyond its base's contours (Pretendard's
        letters draw their own horn, not a translate of ``uni031B``)."""
        out = {}
        for base, cp in _HORN_LETTERS.items():
            letter = self.ctx.ps.outline(self.pcmap[cp], 400)
            plain = self.ctx.ps.outline(self.pcmap[ord(base)], 400)
            own = {tuple(map(tuple, c)) for c in plain.contours()}
            extra = [c for c in letter.contours() if tuple(map(tuple, c)) not in own]
            if len(extra) != 1:
                raise ValueError(f"{self.pcmap[cp]}: expected one horn contour, found {len(extra)}")
            rx = min(x for x, _ in extra[0]) - plain.bounds()[2]
            ry = min(y for _, y in extra[0])
            out[base] = (rx, ry, Zone.CAPITAL if base.isupper() else Zone.LOWER)
        return out

    def horn_offset(self, base: str, t: float) -> tuple[float, float]:
        rx, ry, zone = self._horn_measures[base]
        # The zone maps exist at the H4 masters; the H4 horn interpolates between them.
        ys = [apply_zone_map(self._zone_map(zone, loc), ry) for loc in H4_LOCS]
        y_min = _interpolate(H4_LOCS, ys, t)
        horn = self.ctx.outline(self.ctx.cmap[_HORN], t).bounds()
        return (self.ctx.outline(base, t).bounds()[2] + rx - horn[0], y_min - horn[1])

    def horn_advance(self, base: str, t: float) -> float:
        """Ruling R30: Pretendard's side bearing right of the horn, never below the base's advance."""
        params = h4_letters.params(self.ctx)
        w_prime = _interpolate(H4_LOCS, [params[loc].w_prime for loc in H4_LOCS], t)
        letter = self.pcmap[_HORN_LETTERS[base]]
        bearing = self.ctx.ps.advance(letter, w_prime) - self.ctx.ps.outline(letter, w_prime).bounds()[2]
        horn_right = self.ctx.outline(self.ctx.cmap[_HORN], t).bounds()[2] + self.horn_offset(base, t)[0]
        return max(self.ctx.advance(base, t), horn_right + bearing)


def _interpolate(locs: tuple[float, ...], values: list[float], t: float) -> float:
    for (a, va), (b, vb) in zip(zip(locs, values), zip(locs[1:], values[1:])):
        if t <= b:
            return va + (t - a) * (vb - va) / (b - a)
    raise ValueError(f"location {t} is outside {locs}")


# Anchors per build context; BuildContext is unhashable, so key by id (as h4_letters does).
_ANCHORS: dict[int, tuple[weakref.ref, _Anchors]] = {}


def _anchors(ctx) -> _Anchors:
    key = id(ctx)
    entry = _ANCHORS.get(key)
    if entry is None or entry[0]() is not ctx:
        entry = (weakref.ref(ctx, lambda _: _ANCHORS.pop(key, None)), _Anchors(ctx))
        _ANCHORS[key] = entry
    return entry[1]


def mark_anchor(ctx, mark: str, t: float = 0.0) -> tuple[MarkClass, float, float]:
    """The class and anchor of Roof mark glyph ``mark`` at Roof normalized ``t``.

    Wanted Sans marks use Wanted's letter lookup (or, for the ogonek, the first Wanted
    lookup that has it). H4 marks take their class from the combining class and their
    anchor from Pretendard (rulings R25, R35); the horn's anchor is its ink (xMin, yMin)
    at the default master.
    """
    a = _anchors(ctx)
    if mark in a.wanted_glyphs:
        lk = a.letters if mark in a.letters.marks else next(lk for lk in a.wanted if mark in lk.marks)
        cls: MarkClass = "top" if lk.marks[mark][0] == lk.class_index("top") else "bottom"
        return (cls, *a.wanted_at(lk.mark_anchors[mark], t))
    cls = _CCC_CLASS.get(unicodedata.combining(chr(a.h4_codepoints[mark])))
    if cls is None:
        raise ValueError(f"{mark}: no H2 mark class for its combining class")
    if cls == "horn":
        x_min, y_min, _, _ = ctx.outline(mark, 0.0).bounds()
        return (cls, otRound(x_min), otRound(y_min))
    return (cls, *a.h4_mark_anchor(mark, cls, t))


def base_anchor(ctx, base: str, cls: MarkClass, t: float = 0.0) -> tuple[float, float] | None:
    """Base anchor of ``base`` for ``cls`` at ``t``: Wanted's letter lookup, or Pretendard's for H4 bases."""
    a = _anchors(ctx)
    if cls == "horn":
        if base not in _HORN_LETTERS:
            return None
        _, mx, my = mark_anchor(ctx, ctx.cmap[_HORN])
        dx, dy = a.horn_offset(base, t)
        return (mx + dx, my + dy)
    if base in a.letters.bases:
        return a.letter_anchor(base, cls, t)
    if base in a.wanted_glyphs:
        return a.derived_anchor(base, cls, t)
    if base in a.h4_codepoints:
        return a.h4_base_anchor(base, cls, t)
    return None


def wanted_letter_bases(ctx) -> list[str]:
    """The bases of Wanted Sans's letter lookup, in its coverage order."""
    return list(_anchors(ctx).letters.bases)


def wanted_letter_marks(ctx) -> list[str]:
    """The marks of Wanted Sans's letter lookup, in its coverage order."""
    return list(_anchors(ctx).letters.marks)


def horn_offset(ctx, base: str, t: float) -> tuple[float, float]:
    """Offset of the horn component on Wanted Sans ``base`` (o u O U) at Roof normalized ``t``."""
    return _anchors(ctx).horn_offset(base, t)


def _attachment(ctx, base: str, mark: str, t: float) -> tuple[float, float]:
    """Base anchor − mark anchor at ``t``."""
    a = _anchors(ctx)
    lk = _covering(a.wanted, base, mark)
    if lk is not None:
        bx, by = a.wanted_at(lk.base_anchors[base][lk.marks[mark][0]], t)
        mx, my = a.wanted_at(lk.mark_anchors[mark], t)
        return (bx - mx, by - my)
    cls, mx, my = mark_anchor(ctx, mark, t)
    anchor = base_anchor(ctx, base, cls, t)
    if anchor is None:
        raise ValueError(f"{base} has no {cls} anchor for {mark}")
    return (anchor[0] - mx, anchor[1] - my)


def components(ctx, cp: int) -> list[str]:
    """Base and marks of ``cp`` in canonical order, as Roof glyph names."""
    chars = unicodedata.normalize("NFD", chr(cp))
    marks = [ctx.cmap[ord(c)] for c in chars[1:]]
    base = ctx.cmap[ord(chars[0])]
    if chars[0] in _DOTLESS and any(mark_anchor(ctx, m)[0] == "top" for m in marks):
        base = _DOTLESS[chars[0]]
    return [base, *marks]


def placed_parts(ctx, cp: int, t: float) -> list[Part]:
    """The parts of ``cp`` at Roof normalized ``t``: the base at the origin, then each mark."""
    base, *marks = components(ctx, cp)
    a = _anchors(ctx)
    parts: list[Part] = [(base, 0.0, 0.0)]
    placed: dict[MarkClass, Part] = {}
    for mark in marks:
        cls = mark_anchor(ctx, mark)[0]
        if cls == "horn":
            dx, dy = horn_offset(ctx, base, t)
        elif cls in placed:
            if cls != "top":
                raise ValueError(f"U+{cp:04X}: two marks below are not supported")
            # Stack above the lower mark, centered on it, with the ê gap (decision 13).
            lower, ldx, ldy = placed[cls]
            lb, ub = ctx.outline(lower, t).bounds(), ctx.outline(mark, t).bounds()
            dx = ldx + _center_x(lb) - _center_x(ub)
            dy = ldy + lb[3] + a.gap(t) - ub[1]
        else:
            dx, dy = _attachment(ctx, base, mark, t)
        placed[cls] = (mark, dx, dy)
        parts.append((mark, dx, dy))
    return parts


def _available(ctx, name: str) -> bool:
    return name in ctx.contributed or name in ctx.wanted["glyf"].glyphs


def contribute(ctx) -> list[NewGlyph]:
    pcmap = ctx.pretendard.getBestCmap()
    out, skipped = [], []
    for cp in ctx.selection.codepoints(Rule.H2_COMPOSE):
        names = [ctx.cmap[ord(c)] for c in unicodedata.normalize("NFD", chr(cp))]
        # Ruling R11: a part from a rule that has not landed yet skips the glyph.
        if not all(_available(ctx, n) for n in names):
            skipped.append(cp)
            continue
        parts = {t: placed_parts(ctx, cp, t) for t in COMPOSITE_LOCS}
        base = parts[0.0][0][0]
        if ctx.cmap[_HORN] in names:
            advance = {t: _anchors(ctx).horn_advance(base, t) for t in COMPOSITE_LOCS}
        else:
            advance = {t: ctx.advance(base, t) for t in COMPOSITE_LOCS}
        out.append(composite_glyph(ctx.cmap[cp], parts, advance, (cp,), Rule.H2_COMPOSE, pcmap[cp]))
    if skipped:
        listed = " ".join(f"U+{cp:04X}" for cp in skipped)
        print(f"h2_compose: skipped {Rule.H2_COMPOSE} (components not built yet): {listed}", file=sys.stderr)
    return out
