# Roof Sans — Design

Status: approved for planning; revised with facts found while planning (2026-10-31); extended with Simplified Chinese (2026-11-01, `docs/ROOF_SANS_SIMPLIFIED_CHINESE_DESIGN.md`); extended with weights 100–400 (2026-11-01, `docs/ROOF_SANS_LIGHT_WEIGHTS_DESIGN.md`)

## Intent

Roof Sans is a single variable font for the LiveAnywhere Flutter app (`liveanywhere/app`, package `live1month`). It replaces the static PretendardJP files the app ships today.

The owner prefers Wanted Sans's Latin letters, digits, and symbols over Pretendard's; they read as more consistent. Wanted Sans has no Han ideographs and no Japanese kana, though, so it cannot serve Japanese text or hanja on its own. Roof Sans is therefore **Wanted Sans as the base, with Pretendard JP filling every character Wanted Sans lacks**. Han and Japanese glyphs come over unchanged. Everything else Pretendard adds is rebuilt from Wanted Sans parts or adjusted to Wanted Sans's metrics, so it does not stand out next to Wanted Sans text.

The app also has a Chinese mode. Pretendard JP lacks 3,260 of the 6,763 GB 2312 hanzi, and its kanji are Japanese forms, so Roof Sans adds the missing hanzi and Simplified Chinese forms from Source Han Sans CN (rules C1–C3 below). The full reasoning and measurements are in `docs/ROOF_SANS_SIMPLIFIED_CHINESE_DESIGN.md`.

The axis runs from Thin 100 to ExtraBlack 1000. Wanted Sans has nothing lighter than Regular 400, so below 400 each Wanted Sans glyph continues its own variation, at the weight where its Hangul matches Pretendard JP's (rules L1–L5). Everything at 400 and above stays as this document describes. The full reasoning and measurements are in `docs/ROOF_SANS_LIGHT_WEIGHTS_DESIGN.md`.

## Inputs

| Source | File | Version | Upstream commit in `refs/` |
| --- | --- | --- | --- |
| Wanted Sans | `refs/wanted-sans/packages/wanted-sans/fonts/variable/WantedSansVariable.ttf` | 1.003 | `02c9b82` (v1.0.3+1) |
| Pretendard JP | `refs/pretendard/packages/pretendard-jp/dist/public/variable/PretendardJPVariable.ttf` | 1.309 | `7aeb069` (v1.3.9+18) |
| Source Han Sans CN | `adobe-fonts/source-han-sans` `Variable/TTF/Subset/SourceHanSansCN-VF.ttf` (downloaded; no `refs/` checkout) | 2.005 | `a4f7cf9` (`release` branch) |
| Source Han Sans JP | `Variable/TTF/Subset/SourceHanSansJP-VF.ttf`, same commit; used only to calibrate and to compare forms, no glyph ships | 2.005 | `a4f7cf9` |

Pretendard JP is the right Pretendard flavor: the plain Pretendard build has kana but **no Han ideographs** (its 0 CJK Unified Ideographs vs. 7,138 in Pretendard JP).

Wanted Sans and Pretendard JP use 2048 UPM, are TrueType-flavored variable fonts with a single `wght` axis, and carry no HVAR/MVAR. The Source Han Sans subsets are TrueType-flavored too, with 1000 UPM, `wght` 250–900, and an `avar` table.

## Glyph selection rule

1. **Every code point Wanted Sans maps stays Wanted Sans** as the default glyph. This includes Hangul, Latin, digits, punctuation, symbols, and the 13 CJK brackets/space Wanted Sans already has (`　〈〉《》「」『』【】〔〕`). Rule H1 adds Japanese alternates for those 11, reached only through `locl`.
2. **Code points Wanted Sans lacks, inside the Han/Japanese blocks, come from Pretendard JP.** The blocks are: CJK Radicals Supplement, Kangxi Radicals, CJK Symbols and Punctuation, Hiragana, Katakana, Katakana Phonetic Extensions, Enclosed CJK Letters and Months, CJK Compatibility, CJK Unified Ideographs and Extension A, CJK Compatibility Ideographs, Halfwidth and Fullwidth Forms, and the Supplementary Ideographic Plane. Pretendard JP adds roughly 7.7k Han code points, 184 kana, and the related punctuation. Glyphs in these blocks that Pretendard builds from Latin letters or digits (unit squares such as `㎏㎡`) are rebuilt from Wanted Sans parts per rule H3. *(Owner's decision: their Latin follows Wanted Sans.)*
3. **Exception — fullwidth digits and letters (U+FF10–FF19, FF21–FF3A, FF41–FF5A, 62 code points):** build them from Wanted Sans's ASCII glyphs, centered in Pretendard's fullwidth advance (1920 units). The owner asked for Wanted Sans digits throughout. These are Wanted Sans glyphs in every respect except position: they follow Wanted Sans's variation data across the whole axis, with no 930 plateau. Wanted Sans's advances vary with weight (`0` is 1280/1373/1440 at 400/750/1000), so each glyph's centering offset varies too and needs its own variation data. Fullwidth punctuation and halfwidth katakana still come from Pretendard JP, because their placement inside the em box is Japanese-specific. One exception: 23 fullwidth signs that Pretendard builds from a single Latin glyph (`！＂＃＄％＆＇＋，．：；＜＞？＠＾｀｜￠￡￥￦`) are rebuilt from the same-named Wanted Sans glyph. The new glyph keeps Pretendard's placement in the em box, so `，` stays at the bottom left and `！` stays centered; only the drawing changes. *(Designer's call.)*
4. **Every other code point Pretendard JP has and Wanted Sans lacks is added, harmonized to Wanted Sans** per "Design harmonization" (about 1,535 code points: Latin Extended and Vietnamese, IPA, Greek, Cyrillic, combining marks, arrows, math, currency, enclosed and number forms). *(Owner's decision.)*
   - **Excluded: Pretendard's 382 Private Use Area code points (U+E000–F8FF).** They are private slots for Pretendard's own alternates, such as its numerator and denominator figures. No text uses them, and they would bring Pretendard-style digits back. *(Designer's call.)*
5. **Unicode variation sequences:** keep Pretendard JP's format-14 `cmap` subtable. It has 524 sequences on 503 Han bases, with selectors U+FE00 and U+E0100–E0107. Also keep the alternate glyphs those sequences point to, with their variations, even though they have no ordinary code point. Wanted Sans has no format-14 subtable, so nothing conflicts. *(Designer's call.)*
6. **Simplified Chinese (rules C1–C3).** *(Owner's decisions, 2026-11-01: Simplified Chinese, the GB 2312 range, one file.)*
   - **C1:** the 3,260 GB 2312 hanzi neither Wanted Sans nor Pretendard JP maps come from Source Han Sans CN. They are default glyphs in every locale.
   - **C2:** 2,212 present GB 2312 hanzi get an unencoded Simplified Chinese alternate from Source Han Sans CN, reached only through `locl` ZHS: the 2,210 whose CN outline differs from the JP subset's, plus `唾 毁`, which the JP subset does not map. Defaults stay Pretendard JP's Japanese forms. 199 compatibility ideographs and radicals that share a glyph with a C2 hanzi switch with it.
   - **C1/C2 construction:** Source Han Sans CN sampled at the weights that reproduce Pretendard JP's 400 and 930 kanji, scaled by 1.92, shifted to Pretendard's position, with Pretendard's two-region variation (linear to 930, held to 1000). The weights and offsets are calibrated at build time on the 1,291 GB 2312 hanzi whose CN and JP forms are identical.
   - **C3:** under `locl` ZHS, the 13 shared CJK code points take the same Pretendard JP forms as under JAN; `！：；？` keep Wanted Sans's drawing at Source Han Sans CN's left position; `‘’“”·` become fullwidth Wanted Sans drawings in every script, so quote pairs around Latin words stay matched; `’` and `·` between two Latin, Greek, or Cyrillic letters or digits keep their width.
   - **Excluded:** Traditional Chinese forms, the 189 GB 2312 non-hanzi Roof Sans lacks, and hanzi beyond GB 2312.

## Design harmonization

### What a naive merge looks like

A preview takes Wanted Sans where it has the code point and Pretendard JP otherwise. It shows these visible breaks; the measurements are at `wght` 400 in font units:

- **Japanese punctuation mixes two systems.** Wanted Sans's brackets are proportional Korean forms (`「` 640, `《` 984 wide). Pretendard JP's punctuation is fullwidth Japanese (1920). So `「東京」へ…、…！（テスト）` mixes narrow brackets with fullwidth commas, periods and parentheses. U+3000 is 1770 in Wanted Sans, while the Han width is 1920.
- **Pretendard lowercase sits taller.** x-height is 1086 vs. 1032, overshoot 1100 vs. 1060, and the `g` descender is −430 vs. −460. Cap height and ascender are 1448 in both. Vietnamese words such as `cảm ơn` and `Thưởng` mix letters of two heights and two `o` shapes. Wanted Sans covers only 30 of 98 Vietnamese letters.
- **Symbols sit on different axes.**
  - Math operators: `+` is centered at 566 in Pretendard and 540 in Wanted Sans, so `≤` floats above `+`.
  - Arrows: `→` is centered at 634 vs. 725, so `⇒` and `↩` sit about 90 units low next to `→`.
  - Geometric shapes: Pretendard's `●` is 7% smaller (1580 vs. 1688).
- **Number forms mix designs.**
  - Pretendard's `⑩` has a thinner, smaller ring than Wanted Sans's `⑨`.
  - `⅓` does not match Wanted Sans's `½`.
  - `x⁺` does not match `x²`.
  - `Ⅳ` and `㎏` carry Pretendard's letter shapes.
- **What already matches:**
  - Stem weights are the same at equal `wght`. The `I` stem is 180/300/380 in Pretendard and 176/296/376 in Wanted Sans at 400/700/900, so no weight remapping is needed.
  - Han and kana sit well with the Hangul.

### Rules

Prefer, in order: build the glyph from Wanted Sans parts, then adjust a Pretendard glyph to Wanted Sans's metrics, then copy a Pretendard glyph as is.

- **H1 — Japanese punctuation by locale.** The 13 shared code points keep Wanted Sans's Korean forms by default. Add `locl` lookups for language `JAN` under scripts `kana`, `hani`, `latn`, and `DFLT` that substitute Pretendard JP's fullwidth Japanese forms for them, including a 1920-wide U+3000. The punctuation takes the script of the text around it; `latn` and `DFLT` cover brackets around Latin text such as `ID「abc」`. The app sets locale `ja_JP` for Japanese, so Japanese UI gets a consistent fullwidth set. *(Designer's call.)*
- **H2 — Decomposable Latin letters, including Vietnamese.** 228 of the 442 Pretendard-only Latin letters have a canonical decomposition. Build each one from:
  - the Wanted Sans base letter;
  - marks: Wanted Sans's mark when it has one (for example grave, acute, tilde, dot below, circumflex, breve), otherwise Pretendard's mark adjusted per H4;
  - positions from Wanted Sans's mark anchors (GPOS mark-to-base).

  Wanted Sans's own precomposed letters shift the mark with weight (`ê`'s circumflex moves +28 units at 1000). Its GPOS anchors vary the same way: they are AnchorFormat3 with device tables, and so are Pretendard JP's. So offsets come from the anchors evaluated at each master with their variation deltas. The weight-dependent correction seen in an existing Wanted Sans composite with the same base and mark class should then be about zero; reproducing Wanted Sans's own `ê ă Ê ệ ậ` is the check. *(Corrected after the final review: an earlier version called the anchors static. That premise made the hook above drift left of center at heavy weights.)* Wanted Sans only stacks one mark above and one below (`ệ`). For two marks above (Vietnamese `ầ ấ ẩ ẫ ằ ắ ẳ ẵ`, and `ǖ ǘ ǚ ǜ`), stack them vertically, centered, with the gap Wanted Sans leaves between `e` and its circumflex in `ê`. *(Designer's call; judge it in the visual review.)* Horn letters (`ơ ư Ơ Ư` and their accented forms) are the Wanted Sans base plus Pretendard's horn, attached at the base's right shoulder. Their advance widens so the horn keeps Pretendard's right side bearing.
  - Pretendard's anchors sit higher than Wanted Sans's (lowercase top 1268 vs. 1032). Pretendard marks are therefore placed relative to the `o`/`O` anchor both fonts share.
  - Bases Wanted Sans lacks (`Ʒ ʒ ſ`) use their H4 glyphs. `ẛ`'s dot keeps Pretendard's gap above the long s.
- **H3 — Glyphs Pretendard builds from letters, digits or signs** are rebuilt from Wanted Sans glyphs, spaced with Wanted Sans advances:
  - unit squares (`㎏` = Wanted Sans `k` + `g`);
  - Roman numerals (`Ⅳ` = `I` + `V`);
  - digraphs (`ǅ ǈ ǉ`) and letterlike symbols (`℡`).

  Number forms follow Wanted Sans's own constructions:
  - fractions: `numr` + `fraction` + `dnom`, the way Wanted Sans builds `½`;
  - enclosed numbers Wanted Sans lacks (`⑩`–`⑳`, `⓫`–`⓴`, `❿`, `➉`): Wanted Sans's ring (or the filled disc of `❶`) plus two figures taken from Wanted Sans's own enclosed digits (`⓪①`–`⑨`, `⓿❶`–`❾`). The pair is scaled down, without a stroke offset, until its farthest ink point keeps Wanted Sans's tightest figure-to-ring clearance. Plain `.numr` pairs overran the ring at heavy weights. Their self-overlapping strokes also left ink inside knocked-out figures. Restoring the stroke weight turned the pairs into blobs at 1000;
  - superscript and subscript signs (`⁺⁻⁼⁽⁾`, `₊₋₌₍₎`): Wanted Sans's signs at the scale and position of its superior/inferior figures. Scaling thins their strokes, and Wanted Sans cannot be sampled past 1000, so restore the stroke weight with an x-and-y outline offset, then shift down by half the offset so the sign stays centered. The stroke keeps Wanted Sans's own sign-to-figure ratio; at heavy weights its `+` is thinner than its `1`.
- **H4 — Pretendard letters that cannot be built from Wanted Sans are copied, then matched to Wanted Sans in height and weight.** *(Owner's decision.)*
  - **Scope:**
    - letters with no decomposition (`ŋ ə ʃ ƒ`, IPA, Latin Extended-B);
    - the whole Greek and Cyrillic alphabets;
    - the Pretendard marks used by H2.

    Greek and Cyrillic come whole from Pretendard and share no letter with Latin, so each script stays consistent within itself. *(Designer's call.)*
  - **Why matching is needed.** The two fonts thicken strokes differently as weight grows.
    - Vertical stems are close. The `l` stem is 168/284/400 in Wanted Sans and 172/296/≈419 in Pretendard at 400/700/1000; the Pretendard value at 1000 is extrapolated.
    - Pretendard's horizontal strokes fall behind. The `o` top is 160/260/360 vs. 152/229/≈306, and the `H` bar is 164/278/392 vs. 158/247/≈326.
    - Copied as-is, Pretendard letters look too contrasty and light in bold.
    - Pretendard lowercase also sits taller. x-height is 1086 vs. 1032, and the `p`/`g` descenders are −408/−430 vs. −432/−460.
  - **Method,** for each output master:
    1. **Vertical stems:** sample Pretendard at the weight `w′` where its `l` stem equals Wanted Sans's at the target weight. Interpolate between Pretendard's 45/400/930 masters, extrapolating past 930 when needed. The spike measured `w′` = 387 / 672 / 952 for 400 / 700 / 1000; the build solves 388.85 / 672.18 / 813.33 / 954.22 for 400 / 700 / 850 / 1000.
    2. **Horizontal strokes:** offset the outline in y only, by `δy`. Use FreeType's `FT_Outline_EmboldenXY` algorithm with zero x strength; it moves points along the vertex bisector and keeps the point structure, so masters stay compatible.
       - Choose `δy` to best meet Acceptance 5's horizontal-stroke check. The build minimizes F = max(|median r| / 0.03, max |r| / 0.10), where r is the relative error of each stroke Acceptance 5 measures: Pretendard's `o` top/bottom, `e` top, `H` bar, `n` arch, and Cyrillic `о е п Н` and Greek `ο ε π`, each against Wanted Sans. A plain zero-median solve fails `е` top at 1000.
       - Spike values: `δy` = 13 / 37.5 / 78.5 units. Build values: 7.10 / 41.24 / 61.34 / 80.26 at 400 / 700 / 850 / 1000 (F ≤ 0.993; at 1000 the feasible window is only about 80–80.5).
       - One value per master, not per glyph. Wanted Sans's own horizontal strokes vary by glyph (at 1000, `o` is 360 and `e` is 305), so a per-glyph target does not exist.
    3. **Heights:** after steps 1–2, remap y piecewise-linearly so each zone lands on Wanted Sans's value, measured at that master.
       - Lowercase letters, modifier letters, and marks: descender, bottom overshoot, baseline, x-height, top overshoot, ascender.
       - Capitals: bottom overshoot, baseline, cap height, top overshoot.
    4. Keep Pretendard's advance widths as sampled at `w′`; they vary with weight, like Wanted Sans's.
  - **Spike result** (Wanted Sans / matched Pretendard, font units):

    The spike's `o` and `e` columns measured the bottom strokes, not the tops, as the build found.

    | `wght` | `l` stem | `o` bottom | `e` bottom | `H` bar | `n` arch | x-height |
    | --- | --- | --- | --- | --- | --- | --- |
    | 400 | 168 / 167 | 160 / 159 | 160 / 158 | 164 / 166 | 156 / 164 | 1032 / 1032 |
    | 700 | 284 / 284 | 260 / 247 | 233 / 241 | 278 / 269 | 243 / 250 | 1032 / 1032 |
    | 1000 | 400 / 400 | 360 / 340 | 305 / 328 | 392 / 380 | 322 / 329 | 1032 / 1032 |

    Counters stay open at 1000 (`а е д ж`).
  - Masters: generate these glyphs at 400, 700, and 1000 at least. `w′` and `δy` are not linear in weight, so two masters would drift in between. The build uses 400, 700, 850, and 1000: with three masters the letter median at 850 missed ±3% by 0.2%.
  - At 700–1000, thickening by `δy` closes some sharp notches and narrows some apertures (`В З Ω δ`, `ѕ ʂ ʤ`). The resulting self-intersections are same-sign overlaps: the filled shape equals the union of the strokes, with no hole or twist.
- **H5 — Pretendard symbols are aligned to Wanted Sans by category.** Each category maps through a reference glyph both fonts have:
  - arrows → `→`: center 725, height, and advance;
  - math operators → `+`: axis 540 and size;
  - geometric shapes → `●` and `■`;
  - currency → `$`: already aligned.

  Apply the reference's scale and vertical shift to every Pretendard symbol in the category. When the scale is not 1, keep strokes as thick as Wanted Sans's reference by sampling Pretendard at a compensating weight for each master.
  - The shift maps the Pretendard reference's measured center at the compensating weight onto 725 or 540; Pretendard's `+` center rises from 566 to about 589 across its weights.
  - Symbols Pretendard draws off its own axis keep that offset, scaled: `↩ ↪` (the hook rises above the head), `≤ ≥`, `∞`, and `⋯` (at cap-height middle).
  - When no sample weight reaches the stroke target, the weight is clamped at 1100. Arrows at 1000 are then 5.2% lighter than Wanted Sans's `→`, because Pretendard's arrowhead grows with weight.
- **H6 — Han, kana, and Japanese punctuation glyphs are copied unchanged.** Their weights and metrics already match.

## Weight axis

- `wght` axis 100–1000, default 400. At and above 400 it is Wanted Sans's axis, normalized the same way. Named instances are Thin 100, ExtraLight 200, Light 300, then Wanted Sans's own (Regular 400 … ExtraBlack 1000). The range below 400 is specified in `docs/ROOF_SANS_LIGHT_WEIGHTS_DESIGN.md` (L1–L5).
- Wanted Sans glyphs keep their exact variation data at 400–1000: masters at 400 and 1000 for all glyphs, plus an intermediate master at 750 for 70 glyphs. Below 400 they add one extrapolated tuple (L2).
- Pretendard JP's axis runs 45–930 (default 400). Han, kana, and Japanese punctuation follow Pretendard at the same `wght` value from 100 to 930 (L3). Other Pretendard-derived glyphs are sampled at the weight H4 or H5 picks. Above 930 they behave by group:
  - **Han, kana, and Japanese punctuation hold the 930 shape from 930 to 1000.** Dense Han would risk closing counters if pushed further. They must not fall back toward 400 past 930, which a single tent peaking at 930 would do.
  - **All other Pretendard-derived glyphs (Latin, Greek, Cyrillic, marks, symbols) keep matching Wanted Sans up to 1000** through H4's weight matching and H5's stroke compensation. At 1000 this samples Pretendard slightly past its 930 master (`w′` ≈ 952) and adds the y offset. Holding at 930 would leave them visibly lighter than Wanted Sans's own letters. Every such glyph must pass the outline sanity check in Acceptance. *(Designer's call.)*
- Weights line up: at the same `wght`, Pretendard's and Wanted Sans's Hangul ink areas differ by about 1–1.2% (e.g., `한` at 700: 1,471,583 vs. 1,485,211 units²). Pretendard's Han glyphs at a given `wght` therefore sit visually with Wanted Sans's Hangul at that `wght`.
- **Hard constraint:** the axis maximum must stay ≤ 1000 and the range ≤ 1000. Skia only reads a variable font's `wght` value as the typeface weight under those limits (`SkFontHost_FreeType.cpp`, scanner). Flutter's correct bold rendering depends on that (see below).

## Vertical metrics and spacing

- Take every metric from Wanted Sans: `hhea` 1950/−494/0, `OS/2` typo 1752/−296/0 with `USE_TYPO_METRICS` off, win 1950/494, x-height 1032, cap height 1448.
- Line height on Android then matches today's PretendardJP (both resolve to 1950/−494 from `hhea`), so app layouts should not shift.
- Pretendard glyphs keep their own advance widths (Han and kana: 1920), except where H2, H3, or H5 set them from Wanted Sans parts or references.

## OpenType features

- **Wanted Sans's GSUB and GPOS stay intact**, including its `ss01`–`ss16`, `cv01`–`cv22`, `locl`, `kern`, and `mark`. Tags keep Wanted Sans's meanings.
- **Carry over Pretendard JP's CJK features for the added glyphs:**
  - `locl` under script `hani`, language `KOR`: 537 Korean hanja forms, applied automatically when text is tagged Korean (Flutter `locale: ko`).
  - New `locl` lookups for language `JAN` under `kana`, `hani`, `latn`, and `DFLT` (rule H1).
  - Pretendard JP's kana weight alternates: an `rlig` FeatureVariations record (lookups 77–85) swaps 42 kana to `.varAlt01` forms above weight thresholds. Carry it over, with the thresholds re-mapped to the new axis normalization, and merge it with any FeatureVariations Wanted Sans already has.
  - The same Korean-form set as an opt-in stylistic set. Pretendard JP uses `ss05` for it, but Wanted Sans's `ss05` already means a Latin alternate, so **move Pretendard's set to `ss20`** (unused by Wanted Sans).
  - `jp78`, `jp83`, `jp90`, `nlck` (Japanese variant forms), and `fwid`/`pwid` where both ends of a substitution exist in Roof Sans.
  - Any GPOS data that applies to added glyphs (for example, CJK punctuation kerning), if present.
- Drop Pretendard's Latin-oriented features (its `ss`/`cv` sets, `case`, `frac`, `sups`, …); Wanted Sans's versions apply. Added Latin, Greek, and Cyrillic glyphs do not need to join them.
- Added combining marks (for example U+0309 hook above, U+031B horn) get mark-to-base positioning on Wanted Sans bases, so decomposed input still renders. Precomposed glyphs from H2 cover normal text.
- Default Han forms are Pretendard JP's Japanese forms, the same as the app today.
- **`locl` ZHS (rules C2 and C3):** a `ZHS ` language system under `hani` (hanzi, punctuation, and quote lookups) and under `latn` and `DFLT` (punctuation and quote lookups). HarfBuzz selects it for `zh`, `zh-CN`, `zh-Hans`, and `zh-SG`; `zh-TW`, `zh-HK`, and `zh-Hant` select ZHT/ZHH, which get no lookups. No stylistic set carries the Chinese forms.

## Flutter rendering (the Pretendard "bug")

Reference: flutter/flutter#159678 and orioncactus/pretendard#177. Symptom: on Android (and Flutter web CanvasKit), some Hangul jamo such as ㅅ and ㄴ draw as hollow outlines when text is bold.

Root cause, verified in this session:

1. Flutter before 3.41 did not map `FontWeight` to the `wght` axis. A single-file variable font reports weight 400, so SkParagraph turned on fake bold for w600+ (`wanted >= 600 && wanted - 400 >= 200`). Android's accessibility bold-text setting triggers the same path.
2. Skia's FreeType backend applies fake bold by stroking the glyph path. From 2022-03 (`b3275e1fd6`) to 2025-05 (`b029c60ae4`), Skia first ran pathops `Simplify` on any glyph with the `OVERLAP_SIMPLE`/`OVERLAP_COMPOUND` flag. `Simplify` failed on Hangul jamo built from overlapping contours, and the stroke then left them hollow.
3. Impeller does not avoid this. It still rasterizes glyphs into its atlas through Skia (`impeller/typographer/backends/skia/typographer_context_skia.cc`, `DrawGlyph` → `SkCanvas::drawGlyphs` with `setEmbolden`).
4. **Wanted Sans has the same defect.** Its Hangul is built the same way, and it reproduces identically.

Verification, in a scratch harness:
- CanvasKit 0.39.1 (2023 Skia) reproduces the hollow jamo for both fonts.
- With the overlap flags cleared, the jamo render correctly under the same Skia.
- CanvasKit 0.41.1 (current Skia) renders the original fonts correctly.

Status for the target app:
- The app pins Flutter **3.44.9** (`.fvmrc`).
- Flutter 3.35.0+ ships the Skia without `Simplify`.
- Flutter 3.41.0+ maps `FontWeight` to `wght` (flutter/flutter#175771), and Skia then reports the cloned typeface's weight, so fake bold does not trigger at all.

Decision: **keep the overlap flags as the sources set them.** No font-side workaround is needed for the target Flutter. Clearing the flags would only help Flutter ≤ 3.32, and its effect on other rasterizers was not evaluated. Document the limitation for older Flutter versions in the README.

## Naming and licensing

- Family `Roof Sans`, variable file `RoofSansVariable.ttf`, version 1.000. Names must not contain the Reserved Font Names in Pretendard's OFL: "Pretendard", "Source", "Inter", or "M PLUS 1". "Wanted Sans" has no RFN.
- License: SIL OFL 1.1. The shipped `OFL.txt` lists every upstream copyright line verbatim:
  - Pretendard: Kil Hyung-jin
  - Adobe (Source Han Sans), from Pretendard's `LICENSE` and, for rules C1–C3, from Source Han Sans's own `LICENSE.txt` header
  - The Inter Project Authors (Pretendard's Latin, Greek, and Cyrillic come from Inter)
  - The M+ FONTS Project Authors (M PLUS 1)
  - Wanted Lab, Inc. / The Wanted Sans Project Authors
- Name ID 0 summarizes them.

## Deliverables

- `RoofSansVariable.ttf`.
- A reproducible build script in this repo. It takes the two pinned input files and produces the font with no manual steps; Python with pinned dependencies is expected.
- A verification step (see acceptance).
- `README.md`: what Roof Sans is, how to build it, and Flutter usage. The usage section covers a pubspec snippet, `FontWeight` on Flutter ≥ 3.41, `fontVariations` on older versions, and Korean forms via locale or `ss20`.
- License files.

## Acceptance

1. For every code point Wanted Sans maps, the default outline and advance at `wght` 400, 750, and 1000 match Wanted Sans exactly.
2. For every glyph copied unchanged from Pretendard JP (rule H6, plus glyphs reached through variation sequences and carried-over CJK features), the outline and advance at `wght` 400, 700, and 930 match Pretendard JP.
   - For Han, kana, and Japanese punctuation, the outline at 1000 equals the one at 930.
3. For each synthesized fullwidth digit or letter, at `wght` 400, 750, and 1000:
   - the outline equals the matching Wanted Sans ASCII outline, shifted horizontally so it sits centered in the advance;
   - the advance is 1920.
4. The cmap equals the selection rule above, with no unexpected additions or losses, and no PUA code point from Pretendard. All 524 variation sequences resolve to the same outlines as in Pretendard JP.
5. Harmonization checks, at `wght` 400, 550, 700, 850, and 1000 (the in-between weights catch interpolation drift):
   - H4, heights: zone heights equal Wanted Sans's (x-height 1032, cap height 1448, descenders, overshoots) ±2 units.
   - H4, weights:
     - the `l` stem is within ±3% of Wanted Sans's;
     - the median of the reference horizontal strokes is within ±3%, and each one within ±10%;
     - the same holds for the horizontal strokes of Cyrillic `н п о е` and Greek `ο ε π` against Wanted Sans's `n o e`;
     - Cyrillic `н п` stems keep Pretendard's own stem ratio to its `n` within ±3%. Pretendard thins them as optical compensation, about 6% at 1000. Cyrillic `у` descends to Wanted Sans's `y`, not `g`.
   - H5: arrows are centered at 725 ±5 and math operators at 540 ±5. Symbols Pretendard draws off its axis keep their scaled offset ±5.
   - H3: enclosed numbers `⑩`–`⑳` share the ring outline of Wanted Sans's `①`–`⑨`.
   - H2/H3: rebuilt composites reference Wanted Sans glyphs wherever the rule says so.
6. Outline sanity for every glyph sampled past 930 or offset by H4/H5: contour directions keep their sign, and no collapsed counter (each counter keeps a positive area at every master). A new self-intersection fails when the crossing contour twists on its own, or when the total winding around it changes sign (ink in a hole, or a hole in ink). A same-sign overlap, where the fill equals the union of the strokes, passes. A twist whose reversed lobe is ≤ 1 unit² inside an open counter passes and is listed. Crossings the source already has at the sampled weight are excused one-to-one.
7. Features:
   - Wanted Sans feature behavior is unchanged on a Latin/Hangul sample.
   - `locl` KOR and `ss20` switch the 537 hanja.
   - `locl` JAN switches the 13 shared CJK punctuation code points to Pretendard JP's forms: fullwidth, except `〈〉`, which Pretendard JP draws 698 units wide.
   - `jp90` and friends still work.
8. The font passes OTS sanitization (`ots-sanitize`) and fontTools round-trips cleanly.
9. Visual review: a specimen sheet at `wght` 400, 700, and 1000, rendered from the built font, shown next to the naive-merge baseline. It covers:
   - a Japanese sentence with punctuation, under `ja` and `ko`;
   - Korean with hanja and unit squares;
   - Vietnamese;
   - Greek and Cyrillic next to Latin;
   - arrows and math;
   - `①`–`⑳`, fractions, and superscripts.

   No visible jump in x-height, baseline, weight, or symbol axis.
10. Rendering check in Flutter 3.44.9 on an Android emulator: mixed Korean/Latin/Japanese/hanja text at w400–w900, with the system bold-text setting both off and on, and the app locale set to `ko` and `ja`.
    - No hollow glyphs.
    - Real weights, not fake bold.
    - Line heights unchanged against PretendardJP.
11–20. Simplified Chinese: cmap coverage of GB 2312, source fidelity, the calibration match with Pretendard JP's kanji, `locl` ZHS behavior and isolation, C3 placement, sanity and determinism, the visual review, the Flutter check, size, and the specimen page. The items and their limits are in `docs/ROOF_SANS_SIMPLIFIED_CHINESE_DESIGN.md`, "Acceptance". Items 1–10 still apply unchanged to the font with C1–C3.
21–29. Light weights: the axis and names, nothing changed at 400 and above, Wanted Sans's extrapolation and its weight match with Pretendard JP, copies, derived glyphs, outline sanity, the visual review, and the Flutter check below 400. The items and their limits are in `docs/ROOF_SANS_LIGHT_WEIGHTS_DESIGN.md`, "Acceptance".

## Non-goals

- Static instance files, web fonts (WOFF2), italic, hinting, vertical-writing features.
- Weights below 100.
- New type design: Greek, Cyrillic, IPA, and letters without a decomposition keep Pretendard's drawings, matched in height and weight per H4; nothing is redrawn by hand.
- Width and proportion matching for those letters. They keep Pretendard's advances and shapes; for example, Pretendard's `о` is about 7% narrower than Wanted Sans's `o`.
- Traditional Chinese (`zh-TW`, `zh-HK`) forms, hanzi beyond GB 2312, the GB 2312 non-hanzi Roof Sans lacks, and Chinese forms for `…` and `—`.

## Anti-goals

- Any change to Wanted Sans's default shapes, spacing, metrics, or feature behavior for code points it already covers. That would defeat the reason for the font.
- Letters of two different x-heights inside one word, or symbols sitting off Wanted Sans's axes.
- Pretendard-styled digits or Latin letters showing up where Wanted Sans parts exist.
- A Han/kana weight that falls back to Regular above 930.
- Line-height changes in the app.

## Left to the builder

- **Merge technique.** Recommended: start from the Wanted Sans VF binary and add Pretendard JP's glyphs with fontTools (`glyf`, `gvar`, `hmtx`, `cmap`, GSUB/GPOS lookups).
  - Re-map Pretendard's `gvar` tuples onto the new axis normalization: Pretendard's 930 lands at normalized 0.8833 on 400–1000.
  - The 930→1000 plateau and the linear extrapolation each need their own region data.
  - Building new master outlines and running `varLib` is equally acceptable.
  - Rebuilding from the Glyphs sources is an acceptable alternative if it meets the acceptance checks.
- How to read or derive anchors for H2. Wanted Sans's GPOS mark-to-base data covers its own marks. Horn and hook-above attachment points may need to be derived from outline extremes.
- Glyph-name collisions and renaming, `post` table format, `aalt` regeneration, GDEF classes for added glyphs, and kerning for added Latin/Greek/Cyrillic (none is required).
- How the inputs are pinned (git submodules, vendored files, or download with checksums).
- Repository layout and the exact verification tooling.

## Decisions

Owner's decisions (2026-10-31):

1. Wanted Sans is the base; Pretendard JP fills only what Wanted Sans lacks.
2. Digits follow Wanted Sans everywhere.
3. Pretendard-only characters outside the Han/Japanese blocks are included, harmonized to Wanted Sans.
4. Latin parts of Pretendard glyphs (unit squares and similar) follow Wanted Sans.
5. Overlap flags stay; no font-side workaround for Flutter ≤ 3.32.
6. Pretendard letters that cannot be built from Wanted Sans parts are matched to Wanted Sans in height and weight (H4).

Owner's decision (2026-11-01, later): weights below 400 in the same file. The axis starts at 100; the designer's calls for that extension are listed in `docs/ROOF_SANS_LIGHT_WEIGHTS_DESIGN.md`.

Owner's decisions (2026-11-01): Simplified Chinese for the app's Chinese mode, covering all GB 2312 hanzi, in the same single file; splitting it into its own file later must stay possible. The designer's calls for that extension are listed in `docs/ROOF_SANS_SIMPLIFIED_CHINESE_DESIGN.md`.

Designer's calls. Check these while reading:

1. Fullwidth digits and Latin letters are synthesized from Wanted Sans and follow its weights to 1000.
2. The Korean hanja stylistic set moves from `ss05` to `ss20`.
3. Family name `Roof Sans`, file `RoofSansVariable.ttf`.
4. Pretendard JP's 524 Han variation sequences (IVS) are kept.
5. Pretendard's 382 PUA code points are excluded.
6. Japanese punctuation switches to fullwidth forms under `locl` JAN (H1). Korean and other locales keep Wanted Sans's forms.
7. Greek and Cyrillic come whole from Pretendard and are matched per H4. No letter is shared with Latin.
8. Pretendard symbols are moved and scaled onto Wanted Sans's axes, with stroke compensation (H5).
9. Non-CJK Pretendard glyphs keep matching Wanted Sans up to 1000; Han and kana hold at 930.
10. H4 weight matching uses one vertical sampling weight and one y offset per master, not per-glyph tuning.
11. The 23 fullwidth signs that Pretendard builds from a single Latin glyph are rebuilt from Wanted Sans's glyphs, keeping Pretendard's placement.
12. The Japanese `locl` also applies under `latn` and `DFLT`, so brackets around Latin text in Japanese UI are fullwidth too.
13. Two marks above one letter (Vietnamese `ầ ấ ẩ ẫ ằ ắ ẳ ẵ`, `ǖ ǘ ǚ ǜ`) stack vertically, centered, with the gap Wanted Sans's `ê` uses. Wanted Sans has no precedent for this.
14. Pretendard JP's kana weight alternates (an `rlig` FeatureVariations record) are carried over.
