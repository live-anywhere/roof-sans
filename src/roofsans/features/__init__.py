"""OpenType features: Wanted Sans's GSUB and GPOS kept intact, plus Pretendard JP's CJK features."""

from __future__ import annotations

from fontTools.ttLib import TTFont

from roofsans.features import gdef, gpos, gsub


def apply_features(font: TTFont, ctx) -> None:
    gsub.carry(font, ctx)
    gpos.carry(font, ctx)
    gdef.classify(font, ctx)
