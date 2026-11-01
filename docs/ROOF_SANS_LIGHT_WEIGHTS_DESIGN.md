# Roof Sans — Light weights (wght 100–400)

Status: owner's request (2026-11-01); released in Roof Sans 1.1.0 (font version 1.100). This document extends `docs/ROOF_SANS_DESIGN.md`, which stays the binding authority for everything at and above 400.

## Intent

The owner asked for weights 0–400 next to the existing 400–1000. Roof Sans therefore gets Thin, ExtraLight, and Light. The axis starts at 100, not 0. CSS `font-weight` and `OS/2.usWeightClass` start at 1, CSS names 100 Thin, and Pretendard JP names its lightest instance Thin 100.

The difficulty is Wanted Sans. Its variable font and its Glyphs sources have masters only at 400 and 1000 (plus 750 for 70 glyphs). Nothing lighter than Regular is drawn. Pretendard JP (45–930) and Source Han Sans (250–900) do have light masters. Roof Sans's Hangul, Latin, digits, and symbols must stay Wanted Sans, so their light weights are **extrapolated from Wanted Sans's own variation**. No lighter drawing exists upstream.

## Measured facts

Measured on the pinned inputs.

- Between 400 and 750 every Wanted Sans point moves on a straight line (its regions are (0, 1, 1), (0, 0.583, 1), and (0.583, 1, 1)). The 400 → 550 movement therefore gives each point's direction exactly. Of the 12,649 glyphs with outlines, 41 do not vary; the other 12,608 get a light tuple.
- Extrapolated straight to 100, Wanted Sans is lighter than Pretendard JP at 100: its `l` stem is 52.0 units against Pretendard's 63.8, and `한`'s ink is 12% lower. At equal ink, the extrapolated stems also match Pretendard's (see the table below), so ink and stems agree on one mapping.
- Pretendard JP's ink is linear in weight between its 45 and 400 masters. Wanted Sans's extrapolated ink is close to linear too, so one mapping holds across 100–400: Roof weight w shows Wanted Sans extrapolated to e(w) = 400 − (400 − w)(400 − E) / 300, with E = e(100).
- E = **126.0** makes the median ink of the 2,350 KS X 1001 Hangul syllables equal Pretendard JP's at 100. At 400 the two medians differ by 0.07% (Wanted/Pretendard 0.9993); at 700 by 0.9%.

  | Roof `wght` | Wanted `l` stem | Pretendard `l` stem |
  | --- | --- | --- |
  | 100 | 62.0 | 63.8 |
  | 200 | 97.3 | 99.9 |
  | 300 | 132.7 | 135.9 |
  | 400 | 168.0 | 172.0 |

- Extrapolated to E, five Hangul syllables of the ㄲ + ㅜ/ㅡ pattern (`꿈 끈 끓 끕 끛`) fold by about one unit where a 48-unit vertical edge of the first ㄱ's top shrinks below zero. Four Wanted glyphs (`r.numr`, `r.dnom`, `ʳ`, `ᵣ`) cross themselves at every weight except exactly 400, inside Wanted Sans's own range too.
- Wanted Sans's light extrapolation keeps its stroke contrast: at 100 its `e` top is 94 units and its `H` bar 60. Pretendard JP's Thin is nearly monoline (all reference strokes 61–62). This limits H4 below 250 (see L4).
- Pretendard JP's kanji at 100 match Source Han Sans JP at weight 254.0 (median ink ratio), inside Source Han Sans's range (250–900).

## Rules

**L1 — Axis.** `wght` 100–1000, default 400. `roofsans-build --without-light` leaves the light weights out and gives the 400–1000 font unchanged, byte for byte. Normalized t is (wght − 400) / 600 at and above 400, exactly as before, and (wght − 400) / 300 below it. Every tuple and FeatureVariations condition above 400 keeps its value, so the font at 400–1000 is the font before this extension. The range is 900 and the maximum 1000, inside the Skia limits of the design's Weight axis section. Named instances and `STAT` values add Thin 100, ExtraLight 200, and Light 300. `usWeightClass` stays 400.

**L2 — Wanted Sans below 400.** Every Wanted Sans glyph that varies gets one tuple on the region (−1, −1, 0). Its delta continues the glyph's 400 → 550 movement to E. Simple glyphs move their points and phantom points; composites move their component offsets and phantom points. The build solves E with the ink rule above, rounded to a quarter. A simple glyph whose extrapolated outline fails the outline sanity check against its 550 outline (Acceptance 6's contour rules) stops at the lightest whole weight that passes: `끓` at 127, `끕` and `끛` at 130. At E's rounded deltas, `꿈` and `끈` pass. The four `r` forms are compared with their 550 outline, which crosses itself too, so they are not clamped. Wanted Sans's GDEF variation rows (its kerning and mark anchors) get the same extrapolation, one column on (−1, −1, 0) holding each row's 400 → 550 movement continued to E. *(Designer's call: the alternative, holding Wanted Sans at its 400 shape below 400, would leave Hangul and Latin at Regular next to Thin Han and kana.)*

The build adds these tuples to Wanted Sans in memory before any rule runs (`src/roofsans/light.py`), so every rule that reads Wanted Sans outlines, offsets, or anchors reads them down to 100.

**L3 — Pretendard JP copies (H6).** Han, kana, and Japanese punctuation show Pretendard JP at the same weight from 100 to 930. Pretendard's (−1, −1, 0) tuple is its 45 master; at Roof's −1 (100) Pretendard has moved 300/355 of the way, so its deltas are scaled by 300/355 and rounded. IUP-omitted points stay omitted. Pretendard's kana weight alternates keep their weights: its thresholds below 400 (wght 231.0, 366.0, and 367.0) become Roof conditions at t = −0.5634, −0.1133, and −0.1100, where before they were clamped to 400. Pretendard's kerning deltas on its light region carry over with the same scaling.

**L4 — Derived glyphs.** R3, H2, H3, and C3 build their composites at t = −1 and −0.5 as well as at the existing locations. H3's enclosed figures and sup/sub signs, which use only Wanted Sans parts, add t = −1. H4 and H5 add masters at 100 and 250, with `w′`, δy, and the H5 sample weights solved there as at the other masters:

| Master | H4 `w′` | H4 δy | H5 arrow sample | H5 math sample |
| --- | --- | --- | --- | --- |
| 100 | 94.97 | 10.78 | 162.97 | 131.80 |
| 250 | 241.78 | 8.80 | 275.78 | 238.18 |

H4 cannot meet Acceptance 5's stroke limits below 250. Its one y offset per master moves every horizontal stroke of a Pretendard letter together, and at Thin Pretendard's strokes are nearly equal while Wanted Sans's extrapolated ones keep their contrast. Measured on the built font at 100, the reference median is +5.8%, the worst reference stroke +16.7% (`H` bar), and the worst letter stroke −20.2% (`ε` top). In font units that is at most 19 units, about 0.15 px at 16 px. Acceptance 26 sets the light limits from these measurements.

The same contrast shows in Wanted Sans's own letters. Its horizontals thicken more slowly than its stems between 400 and 1000, so going lighter they also thin more slowly: at 100 the `e` top bar is 94 units against an `l` stem of 62 (`n` arch 71, `o` top 69). That is the extrapolation of Wanted Sans's design, not a rule of Roof Sans, and the owner should judge it in the specimen review (Acceptance 28). *(Designer's call: per-stroke tuning would be the per-glyph work the design rules out in H4.)*

**L5 — Simplified Chinese (C1, C2, C3).** The calibration adds a third master: the Source Han Sans weight whose kanji reproduce Pretendard JP's at 100 (254.0), with its own dx and dy. C1 and C2 glyphs get a tuple on (−1, −1, 0) from that master. C3 punctuation centers interpolate between the 100 and 400 calibrated centers.

## Acceptance

Items 1–20 (`docs/ROOF_SANS_DESIGN.md` and `docs/ROOF_SANS_SIMPLIFIED_CHINESE_DESIGN.md`) still pass, unchanged; they cover 400–1000. New items:

21. **Axis and names.** `fvar` `wght` is 100–1000 with default 400, and lists Thin 100, ExtraLight 200, Light 300, then Wanted Sans's seven instances. `STAT` has an axis value for each of the ten weights. `usWeightClass` is 400.
22. **Unchanged above 400.** `roofsans-build --without-light` is byte-identical to the font committed before this extension (SHA-256 `da7a7fe8…75b87d`), and `--without-light --without-chinese` to the pre-Chinese font (`6a01839d…272325`, Acceptance 16's baseline). The light build adds data only on regions below 0 ((−1, −1, 0), and for glyphs with a 250 master also (−1, −0.5, 0) and (−1, −1, −0.5)), FeatureVariations conditions below 0, and the three named instances and STAT values: every glyph's default outline, advance, and tuples above 0 equal the `--without-light` build's, and HarfBuzz shapes the specimen lines identically at 400–1000 under no locale, `ko`, `ja`, and `zh-CN`. *(Checked once for this branch: 0 of 28,404 glyphs differ, 0 of 684 shaping runs differ.)*
23. **Wanted Sans below 400.** At 100, 200, and 300 every Wanted Sans glyph's outline and advance equal Wanted Sans's 400 → 550 line continued to e(w), where e(w) uses E, or the glyph's clamped weight for the glyphs the build lists. The limit is 1 unit for simple glyphs (delta rounding plus the IUP tolerance) and 1.5 units for composites measured decomposed, whose offset deltas are rounded once more. At most 10 glyphs are clamped, each at a weight ≤ 150.
24. **Weight match.** At 100, 200, and 300, the median ink of the 2,350 KS X 1001 Hangul syllables is within ±1% of Pretendard JP's at the same weight, and the `l` stem within ±5% of Pretendard's.
25. **Copies below 400.** Every H6 copy's outline and advance at 100 and 250 match Pretendard JP at the same weight within 1 unit, and within 1.5 units for composites measured decomposed (their component and offset deltas are each scaled and rounded). The kana alternates switch at the same weights as in Pretendard JP, on both sides of each of its three light thresholds.
26. **Derived glyphs below 400.** At 100, 175, 250, and 300:
    - R3 fullwidth glyphs: the outline is the Wanted Sans ASCII outline, centered; the advance is 1920.
    - H4: zone heights ±2 units and the `l` stem ±3%, as in Acceptance 5. Horizontal strokes, per group: at 250 and above, Acceptance 5's limits (median ±3%, each ±10%); below 250, median within ±7% and each stroke within ±21%. *(Limits set from the measured values; designer's call.)*
    - H5: arrows centered at 725 ±5, math operators at 540 ±5.
    - H3: `⑩`–`⑳` share Wanted Sans's ring outline.
    - H2 at 100 and 250: each Wanted mark on a Wanted letter sits where Wanted Sans's own GPOS, with the light tuples, puts it (±2 units), decomposed input shapes like the precomposed glyph, and marks measured against Pretendard's precomposed letters stay within Acceptance 7's limits, except `ȓ` (52 units) and `Ȓ` (21), whose breves Pretendard moves far more with weight. Side bearings follow the design's rule with four more allowed overhangs at 100 (`Ĭ ĭ ǰ ḧ`; build notes section 14). *(Designer's call.)*
    - C1/C2: each glyph equals Source Han Sans CN at the 100 calibrated weight, transformed, within 1 unit at 100. The 1,291 calibration hanzi built from Source Han Sans JP reproduce Pretendard JP at 100: ink box worst edge within 5 units for at least 99% of the set and within 32 units for every glyph; ink area within ±1% in the median and ±3% for each glyph. 100 is a calibrated master like 400, so it gets 400's kind of limits. The four glyphs over 5 units (`熙` 31.3, `摹` 15.4, `蔓` 11.9, `荻` 8.0) are the same outliers as at 400 (`熙` 19.1 there): Pretendard draws them differently from Source Han Sans, and the difference grows toward Pretendard's 45 master. *(Limits set from the measured values; designer's call.)*
    - C3: ink centers within 1 unit of the interpolated Source Han Sans centers.
27. **Outline sanity below 400.** Acceptance 6's contour rules hold at 100, 175, 250, and 300 for every glyph Roof Sans builds or extrapolates, including every Wanted Sans glyph against its 550 outline.
28. **Visual review and distribution.** The specimen sheet at 100, 200, and 300 shows no visible jump in weight, x-height, baseline, or symbol axis between scripts. `dist/web/` declares `font-weight: 100 1000`. The specimen page states the new range. The build notes record E, the clamped glyphs, the light calibration values, and the new file size.
29. **Flutter.** The Flutter check (Acceptance 10) adds w100–w300. It stays outstanding with the rest of Acceptance 10 on Android.

## Non-goals

- Weights below 100. Wanted Sans extrapolated further would fold more glyphs, and Pretendard JP has nothing below 45.
- Hand-drawn light masters, or any per-glyph tuning beyond the clamp in L2.
- Changing anything at or above 400.

## Anti-goals

- Any change to the font at 400–1000.
- Hangul or Latin that stays at Regular next to Thin Han and kana, or the reverse.
- A light glyph that folds, collapses a counter, or reverses a contour.

## Costs

- The font grows from 16,230,096 to 21,013,072 bytes (+4.8 MB, +29%): almost every glyph gets one more tuple, and the 1,675 glyphs with a 250 master (H4, H5, and the composites) two.
- The build takes about 38 s instead of about 20 s; solving E and the sanity checks in L2 take about 11 s.
- A product that does not need the light weights can ship the `--without-light` build (16.2 MB, 400–1000) instead.

## Decisions

Owner's decision (2026-11-01): add weights below 400, as one variable font.

Designer's calls. Check these while reading:

1. The axis starts at 100 (Thin), not 0.
2. Wanted Sans's light weights are its own 400 → 550 movement, extrapolated (L2).
3. E is set by matching Hangul ink with Pretendard JP at 100, so Roof's 100 is Pretendard's 100 for Han and kana and the same visual weight for Hangul.
4. Glyphs that would fold stop at the lightest weight that keeps them intact; three Hangul syllables are affected.
5. Instances are named Thin, ExtraLight, and Light, as in Pretendard JP.
6. H4's stroke limits are relaxed below 250 instead of adding per-glyph tuning (L4, Acceptance 26).
7. H4 and H5 use light masters at 100 and 250; composites add 100 and 250, Wanted-only H3 glyphs add 100.
