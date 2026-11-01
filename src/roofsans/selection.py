"""Decide which build rule owns every code point either input font maps."""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from fontTools.ttLib import TTFont

from roofsans.chinese import gb2312_hanzi


class Rule(StrEnum):
    WANTED = "WANTED"
    C1_HANZI = "C1_HANZI"
    C2_FORM = "C2_FORM"
    C3_PUNCT = "C3_PUNCT"
    H6_COPY = "H6_COPY"
    R3_FULLWIDTH = "R3_FULLWIDTH"
    R3_SIGN = "R3_SIGN"
    H2_COMPOSE = "H2_COMPOSE"
    H3_SEQUENCE = "H3_SEQUENCE"
    H3_FRACTION = "H3_FRACTION"
    H3_ENCLOSED = "H3_ENCLOSED"
    H3_SUPSUB = "H3_SUPSUB"
    H4_LETTER = "H4_LETTER"
    H5_SYMBOL = "H5_SYMBOL"
    EXCLUDED_PUA = "EXCLUDED_PUA"


class SymbolCategory(StrEnum):
    ARROW = "ARROW"
    MATH = "MATH"
    GEOMETRIC = "GEOMETRIC"
    CURRENCY = "CURRENCY"
    OTHER = "OTHER"


class Zone(StrEnum):
    LOWER = "LOWER"
    CAPITAL = "CAPITAL"


# The CJK space and brackets both fonts map; H1 gives them Japanese alternates under `locl`.
JAN_SHARED: tuple[int, ...] = (0x3000, *range(0x3008, 0x3012), 0x3014, 0x3015)

# Design selection rule 2: the Han/Japanese blocks Pretendard JP supplies.
_HAN_JP_BLOCKS = (
    (0x2E80, 0x2FDF), (0x3000, 0x30FF), (0x31F0, 0x31FF), (0x3200, 0x33FF),
    (0x3400, 0x4DBF), (0x4E00, 0x9FFF), (0xF900, 0xFAFF), (0xFF00, 0xFFEF),
    (0x20000, 0x2FFFF),
)
_HALF_FULL = (0xFF00, 0xFFEF)
_PUA = (0xE000, 0xF8FF)
_FULLWIDTH_ALNUM = ((0xFF10, 0xFF19), (0xFF21, 0xFF3A), (0xFF41, 0xFF5A))
_FULLWIDTH_SIGN = ((0xFF01, 0xFF5E), (0xFFE0, 0xFFE6))
_GREEK_CYRILLIC = (
    (0x0370, 0x03FF), (0x1F00, 0x1FFF),
    (0x0400, 0x052F), (0x1C80, 0x1C8F), (0x2DE0, 0x2DFF), (0xA640, 0xA69F),
)

_H3_LISTS: tuple[tuple[Rule, frozenset[int]], ...] = (
    (Rule.H3_SEQUENCE, frozenset((
        *range(0x01C4, 0x01CD), *range(0x01F1, 0x01F4), *range(0x2160, 0x2180),
        0x20A8, 0x2121, 0x213B, 0x2116,
    ))),
    (Rule.H3_FRACTION, frozenset((0x2100, 0x2101, 0x2105, 0x2106))),
    (Rule.H3_ENCLOSED, frozenset((
        *range(0x2469, 0x2474), *range(0x24EB, 0x24F5), 0x277F, 0x2789,
    ))),
    (Rule.H3_SUPSUB, frozenset((*range(0x207A, 0x207F), *range(0x208A, 0x208F)))),
)

_H4_CATEGORIES = frozenset(("Lu", "Ll", "Lt", "Lm", "Lo", "Mn", "Nl"))
_H4_EXCEPTIONS = frozenset((0x318D, 0xA92E))
_CAPITAL_CATEGORIES = frozenset(("Lu", "Lt", "Nl"))

_ARROW_BLOCKS = ((0x2190, 0x21FF), (0x27F0, 0x27FF), (0x2900, 0x297F), (0x1F800, 0x1F8FF))
_MISC_SYMBOLS_ARROWS = (0x2B00, 0x2BFF)
_GEOMETRIC = (0x25A0, 0x25FF)
_MATH_BLOCKS = ((0x2200, 0x22FF), (0x2A00, 0x2AFF), (0x27C0, 0x27EF), (0x2980, 0x29FF))


def _within(cp: int, *ranges: tuple[int, int]) -> bool:
    return any(lo <= cp <= hi for lo, hi in ranges)


@dataclass(frozen=True)
class Selection:
    rules: Mapping[int, Rule]
    symbol_category: Mapping[int, SymbolCategory]
    zone: Mapping[int, Zone]

    def codepoints(self, rule: Rule) -> list[int]:
        return sorted(cp for cp, r in self.rules.items() if r is rule)


def roof_glyph_name(cp: int, taken: set[str]) -> str:
    """Name a glyph the build synthesizes or harmonizes, avoiding names in ``taken``."""
    name = f"uni{cp:04X}" if cp <= 0xFFFF else f"u{cp:05X}"
    return f"{name}.roof" if name in taken else name


def _component_closure(glyf, name: str) -> set[str]:
    """Every glyph a composite reaches through its components, at any depth."""
    seen: set[str] = set()
    stack = [name]
    while stack:
        glyph = glyf[stack.pop()]
        if not glyph.isComposite():
            continue
        for comp in glyph.components:
            if comp.glyphName not in seen:
                seen.add(comp.glyphName)
                stack.append(comp.glyphName)
    return seen


def _symbol_category(cp: int) -> SymbolCategory:
    category = unicodedata.category(chr(cp))
    if category == "Sc":
        return SymbolCategory.CURRENCY
    in_misc_arrows = _within(cp, _MISC_SYMBOLS_ARROWS)
    if _within(cp, *_ARROW_BLOCKS) or (in_misc_arrows and "ARROW" in unicodedata.name(chr(cp), "")):
        return SymbolCategory.ARROW
    if _within(cp, _GEOMETRIC) or in_misc_arrows:
        return SymbolCategory.GEOMETRIC
    if category == "Sm" or _within(cp, *_MATH_BLOCKS):
        return SymbolCategory.MATH
    return SymbolCategory.OTHER


def select(wanted: TTFont, pretendard: TTFont, shs_cn: TTFont, chinese: bool = True) -> Selection:
    """Classify every code point either font maps, in the design's rule order."""
    wanted_cmap = wanted.getBestCmap()
    pretendard_cmap = pretendard.getBestCmap()
    wanted_glyphs = set(wanted.getGlyphOrder())
    glyf = pretendard["glyf"]

    # Pretendard glyphs that stand for a Latin letter, digit, or sign.
    latin_glyphs = {
        g for cp, g in pretendard_cmap.items() if cp < 0x0250 or cp in (0x00B2, 0x00B3, 0x00B9)
    }

    rules: dict[int, Rule] = {}
    symbol_category: dict[int, SymbolCategory] = {}
    zone: dict[int, Zone] = {}

    def classify(cp: int) -> Rule:
        if cp in wanted_cmap:
            return Rule.WANTED
        if _within(cp, _PUA):
            return Rule.EXCLUDED_PUA
        if _within(cp, *_FULLWIDTH_ALNUM):
            return Rule.R3_FULLWIDTH
        glyph = glyf[pretendard_cmap[cp]]
        if (
            _within(cp, *_FULLWIDTH_SIGN)
            and glyph.isComposite()
            and len(glyph.components) == 1
            and glyph.components[0].glyphName in wanted_glyphs
        ):
            return Rule.R3_SIGN
        if _within(cp, *_HAN_JP_BLOCKS):
            if (
                not _within(cp, _HALF_FULL)
                and glyph.isComposite()
                and _component_closure(glyf, pretendard_cmap[cp]) & latin_glyphs
            ):
                return Rule.H3_SEQUENCE
            return Rule.H6_COPY
        if _within(cp, *_GREEK_CYRILLIC):
            return Rule.H4_LETTER
        char = chr(cp)
        category = unicodedata.category(char)
        decomposition = unicodedata.decomposition(char)
        if (
            "LATIN" in unicodedata.name(char, "")
            and category.startswith("L")
            and decomposition
            and not decomposition.startswith("<")
        ):
            return Rule.H2_COMPOSE
        for rule, members in _H3_LISTS:
            if cp in members:
                return rule
        if decomposition.startswith("<fraction>"):
            return Rule.H3_FRACTION
        if category in _H4_CATEGORIES and cp not in _H4_EXCEPTIONS:
            return Rule.H4_LETTER
        return Rule.H5_SYMBOL

    for cp in sorted(wanted_cmap.keys() | pretendard_cmap.keys()):
        rule = rules[cp] = classify(cp)
        if rule is Rule.H4_LETTER:
            capital = unicodedata.category(chr(cp)) in _CAPITAL_CATEGORIES
            zone[cp] = Zone.CAPITAL if capital else Zone.LOWER
        elif rule is Rule.H5_SYMBOL:
            symbol_category[cp] = _symbol_category(cp)

    if chinese:
        source_cmap = shs_cn.getBestCmap()
        for cp in gb2312_hanzi():
            if cp in rules:
                continue
            if cp not in source_cmap:
                raise ValueError(f"Source Han Sans CN lacks C1 U+{cp:04X}")
            rules[cp] = Rule.C1_HANZI

    return Selection(rules=rules, symbol_category=symbol_category, zone=zone)
