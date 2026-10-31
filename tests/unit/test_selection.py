from roofsans.selection import Rule, SymbolCategory, Zone, roof_glyph_name, select


def test_counts(wanted, pretendard):
    s = select(wanted, pretendard)
    n = lambda r: len(s.codepoints(r))
    assert n(Rule.WANTED) == 12032 and n(Rule.EXCLUDED_PUA) == 382
    assert n(Rule.R3_FULLWIDTH) == 62 and n(Rule.R3_SIGN) == 23 and n(Rule.H2_COMPOSE) == 228
    assert n(Rule.H6_COPY) == 7986
    assert n(Rule.H3_SEQUENCE) == 127   # 80 unit squares + 47
    assert n(Rule.H3_ENCLOSED) == 23 and n(Rule.H3_SUPSUB) == 10
    assert n(Rule.H3_FRACTION) + n(Rule.H4_LETTER) + n(Rule.H5_SYMBOL) == 1227
    assert sum(1 for r in s.rules.values() if r is not Rule.EXCLUDED_PUA) == 21718


def test_examples(wanted, pretendard):
    s = select(wanted, pretendard)
    assert s.rules[ord("「")] is Rule.WANTED and s.rules[ord("、")] is Rule.H6_COPY
    assert s.rules[ord("㎏")] is Rule.H3_SEQUENCE and s.rules[ord("＄")] is Rule.R3_SIGN
    assert s.rules[ord("＼")] is Rule.H6_COPY and s.rules[ord("（")] is Rule.H6_COPY
    assert s.rules[ord("ự")] is Rule.H2_COMPOSE and s.rules[ord("ά")] is Rule.H4_LETTER
    assert s.rules[ord("ŋ")] is Rule.H4_LETTER and s.zone[ord("Ж")] is Zone.CAPITAL
    assert s.symbol_category[ord("⇒")] is SymbolCategory.ARROW
    assert s.symbol_category[ord("≤")] is SymbolCategory.MATH
    assert s.symbol_category[ord("▲")] is SymbolCategory.GEOMETRIC
    assert s.symbol_category[ord("₫")] is SymbolCategory.CURRENCY
    assert s.rules[0x318D] is Rule.H5_SYMBOL


def test_naming():
    assert roof_glyph_name(0x1EA7, set()) == "uni1EA7"
    assert roof_glyph_name(0x1F850, set()) == "u1F850"
    assert roof_glyph_name(0x1EA7, {"uni1EA7"}) == "uni1EA7.roof"
