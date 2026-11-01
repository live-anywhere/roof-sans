# Roof Sans — Simplified Chinese design

Status: approved and built (2026-11-01). Revised during the build where marked.

This document extends `docs/ROOF_SANS_DESIGN.md`. Everything there stays binding unless a section below changes it. Its rules are summarized in the main design (selection rule 6, OpenType features, Acceptance 11–20); this file keeps the full rules, measurements, and reasons. Build values are in `docs/ROOF_SANS_BUILD_NOTES.md`, section 12.

## Intent

The LiveAnywhere app has a Chinese mode that shows the whole app UI in Chinese. Roof Sans maps only 3,503 of the 6,763 hanzi in GB 2312. The other 3,260 fall back to the device's system font, so one sentence mixes two typefaces. The owner sees this today.

The 3,503 hanzi Roof Sans already has are Pretendard JP's Japanese forms. In Chinese text, many of them look foreign to a mainland reader: `直 骨 角 八 安 本` are drawn differently in the Chinese and Japanese standards.

The goal is that the Chinese mode reads as one typeface, in Simplified Chinese forms, and that the added hanzi sit with the existing Han glyphs in style, size, and weight.

## Owner's decisions (2026-11-01)

1. Unify on the form that most Chinese readers find comfortable. The designer proposed Simplified Chinese (mainland China, Singapore, Malaysia) and the owner agreed.
2. Coverage is the GB 2312 range: all 6,763 hanzi. The owner accepted that the file grows by an estimated 3–5 MB.
3. Ship one file now. Splitting the Chinese part into a separate file later must stay possible (see "Splitting later").

Assumption, not yet checked against the app: the app's Chinese strings are Simplified Chinese. If they are Traditional, this design does not remove the mixed fonts, because Traditional text uses different code points.

## Measured facts (2026-11-01)

These were measured in a scratch session against the pinned Pretendard JP input, the committed `fonts/RoofSansVariable.ttf` (11,798,960 bytes, SHA-256 `6a01839d…272325`), and Source Han Sans 2.005. The build notes gave an earlier build's size and SHA-256 (11,779,304 bytes, `9927013a…8defe`); they now record the committed value, which `roofsans-build --without-chinese` reproduces.

- **Pretendard JP's kanji are Source Han Sans JP, scaled.** Simple kanji (`一 口 日 田 書`) have the same contour and point counts in both fonts. Their ink boxes match Source Han Sans × 1.92 with an x offset of about 0 (±2 units) and a y offset of about +21 (+20 to +23). 1.92 maps Source Han Sans's 1000-unit em onto Pretendard's 1920-unit Han advance. Complex kanji (`東 漢 愛`) differ by a few points, so Pretendard converted the outlines to TrueType on its own; outlines cannot be compared point by point.
- **Weight correspondence, by ink area** over 14 kanji (`一口日田国東京語漢字書愛鬱龍`): Pretendard 400 matches Source Han Sans at 377.5–384 (median 381.25), with an ink-area ratio of 1.0000–1.0004. Pretendard 930 matches Source Han Sans 900, its maximum, with Pretendard 0.3–0.9% heavier. Pretendard 700 matches Source Han Sans at about 650–660.
- **The match over the whole calibration set** (the 1,291 hanzi defined under "Form differences"), with Source Han Sans JP × 1.92 against Pretendard JP:

  | Pretendard | Source Han Sans | dx | dy | worst ink-box edge error per glyph: median / 99th percentile / max | glyphs over 3 units | ink-area ratio: median (min–max) |
  | --- | --- | --- | --- | --- | --- | --- |
  | 400 | 381.25 | −0.01 | +21.66 | 1.4 / 2.9 / 19.1 | 9 | 1.0008 (0.990–1.018) |
  | 930 | 900 | −0.16 | +21.44 | 2.6 / 5.0 / 6.7 | 363 | 1.0056 (0.992–1.028) |

  At 400 the outliers are `熙` (19 units), `摹` (9), `蔓` (8), and `荻` (5). Their shapes differ slightly between Pretendard's Source Han Sans and version 2.005, so no single transform fits every glyph. At 930 the errors are larger because Pretendard's heaviest kanji are about 0.6% heavier than Source Han Sans's maximum weight; the new hanzi are that much lighter at 930–1000. A 2.6-unit error is 0.14% of the 1920-unit em.
- **Source Han Sans CN variable TTF.** The `release` branch of `adobe-fonts/source-han-sans` at commit `a4f7cf94edfb9d7ffbdfc4841de276358bd7e0f2` (2025-06-25, version 2.005) has `Variable/TTF/Subset/SourceHanSansCN-VF.ttf`: 17,749,860 bytes, SHA-256 `25a01e41b5cc99893eb35a6cd2cc7611841dc19eb03cbaf7f0c1de8210f2ba0b`. It is TrueType-flavored (`glyf`/`gvar`), 1000 UPM, `wght` 250–900 with an `avar` table, 31,072 glyphs, and 30,926 code points. It maps all 6,763 GB 2312 hanzi with Simplified Chinese forms as the defaults. The JP subset in the same folder (`SourceHanSansJP-VF.ttf`, 9,564,672 bytes, SHA-256 `4acc34926098472741bbb7be5949b80afa7fc08f41ea3cd80dc34f12f7d55bbc`) has the Japanese forms.
- **GB 2312 hanzi in Roof Sans:** 3,503 present, 3,260 missing (level 1: 1,335 of 3,755; level 2: 1,925 of 3,008).
- **Form differences.** Of the 3,503 present hanzi, Source Han Sans JP maps 3,501. Of those, 2,210 have a Source Han Sans CN outline that differs from Source Han Sans JP (for example `埃挨哀癌矮隘鞍安俺按暗案`), and 1,291 are identical in both subsets. The JP subset does not map `唾` U+553E or `毁` U+6BC1; Pretendard JP has them, and its `毁` has 15 contours where Source Han Sans CN's has 14.
- **Punctuation.** Of the 175 CJK punctuation and fullwidth code points both subsets map, 9 differ between CN and JP, all at 400:
  - `！：；？` (U+FF01, FF1A, FF1B, FF1F): CN puts the ink at the left of the em (center x 244–250 of 1000); JP centers it (494–500).
  - `‘’“”` (U+2018, 2019, 201C, 201D): CN uses fullwidth forms (advance 1000) with the ink pushed toward the quoted text (`“` center 794, `”` center 206). JP uses proportional forms (advance 278 / 474).
  - `·` (U+00B7): CN uses a fullwidth, centered dot (advance 1000, center 500). JP uses a proportional one (561).
  - `，。、` and the brackets `「」『』【】〔〕《》〈〉` are the same in both subsets.
- **Size.** Roof Sans's Han glyphs take 749 bytes each on average (measured on a Han-only subset of the built font). About 5,480 new glyphs add about 4.1 MB, so the font would grow from 11.8 MB to about 15.9 MB. The glyph count would rise from 22,923 to about 28,400, well under the 65,535 limit.
- **GB 2312 symbols Roof Sans lacks:** 189 non-hanzi code points: 25 math and other symbols (`∶∧∨∪∩∈∷⊥∥∠⌒⊙∮≡≌∽∝≮≯∵∴♂♀◎〓`), 50 enclosed and parenthesized numbers (`⒈`–`⒛`, `⑴`–`⒇`, `㈠`–`㈩`), `￣`, 37 bopomofo letters, and 76 box-drawing characters. Pretendard JP lacks them too.

## Glyph selection

Three new rules join the selection in `docs/ROOF_SANS_DESIGN.md`.

1. **C1 — missing GB 2312 hanzi.** The 3,260 GB 2312 hanzi that neither Wanted Sans nor Pretendard JP maps come from Source Han Sans CN, built per "Building the hanzi". They are the default glyphs for their code points in every locale; no other locale has a form for them.
2. **C2 — Simplified Chinese forms for present hanzi.** For the 2,212 present GB 2312 hanzi that need one, add the Source Han Sans CN glyph as an unencoded alternate. The default stays Pretendard JP's Japanese form, so Korean, Japanese, and untagged text do not change. The alternate is reached only through `locl` for Chinese (see "OpenType features").
   - C2 takes the 2,210 hanzi whose Source Han Sans CN outline differs from Source Han Sans JP.
   - It also takes `唾` and `毁`, which the JP subset does not map, so nothing shows that Pretendard's glyph already has the Chinese form. *(Designer's call.)*
   - The 1,291 present hanzi whose CN and JP outlines are identical get no alternate. Pretendard JP's glyph already shows the Chinese form.
   - Han characters outside GB 2312 get no alternate of their own. 199 of them share a glyph with a C2 hanzi (79 + 33 CJK compatibility ideographs in U+F9xx/FAxx, 81 Kangxi radicals, 6 CJK radicals supplement characters; for example `八` and the radical `⼋` share one glyph), so the C2 substitution reaches them too. Giving them separate glyphs would change the cmap for no practical gain in Chinese UI text. A test pins the list. *(Designer's call, from the review.)*
3. **C3 — Chinese punctuation.** Under the Chinese `locl`:
   - The 13 code points shared with Wanted Sans (`　〈〉《》「」『』【】〔〕`) switch to the same Pretendard JP glyphs that `locl` JAN uses (the `.pj` copies). Source Han Sans CN and JP draw these the same way. `〈〉` therefore stay 698 units wide, as under JAN.
   - `！：；？` switch to new alternates: the same Wanted Sans drawing that Roof's default glyph uses (rule R3_SIGN), with its ink center x placed on Source Han Sans CN's ink center after the C1 transform. The advance stays 1920. This is R3_SIGN with Chinese placement instead of Japanese placement. *(Designer's call, following design decision 11.)*
   - `‘’“”·` switch to new fullwidth alternates: Wanted Sans's own `quoteleft`, `quoteright`, `quotedblleft`, `quotedblright`, and `periodcentered` drawings, placed on Source Han Sans CN's ink center after the C1 transform, with advance 1920. This applies in every script under ZHS, including quotes around Latin words. *(Designer's call, revised during the build.)*
     - Chinese convention (GB/T 15834) and Source Han Sans CN set these quotes fullwidth around Latin words too.
     - A `hani`-only rule split pairs: in `他说“OK”。`, script itemization gives `“` the Han script and `”` the Latin script, so the opening quote was 1920 wide and the closing one 796. Flutter's text shaping itemizes the same way.
     - Exception: `’` and `·` between two Latin, Greek, or Cyrillic letters or digits do not switch, so apostrophes and middle dots inside words (`It’s`, `McDonald’s`, `l·l`, `2’30`) keep their width. A chained-context rule implements it. *(Designer's call, from the review.)*
   - `，。、．` and the other fullwidth punctuation already match the CN positions and do not change.

Everything else Roof Sans contains stays as it is, including its 3,503 present hanzi as default glyphs.

## Building the hanzi

C1 and C2 glyphs come from Source Han Sans CN, transformed to sit exactly where Pretendard JP's kanji sit, at every weight.

- **Two masters, like Pretendard JP's kanji.** Sample Source Han Sans CN at two weights: `w400`, the Source Han Sans weight that matches Pretendard's 400 master, and `w930`, the one that matches Pretendard's 930 master (measured at about 381 and 900). Use a static instance at each weight (for example `fontTools.varLib.instancer`), so `avar` and Source Han Sans's intermediate masters are applied. Both instances come from one variable glyph, so their point structures match.
- **Transform.** Scale both masters by 1.92 in x and y, then shift by (dx, dy). The measured values are dx ≈ 0 and dy ≈ +21. The advance is 1920.
- **Calibration.** The builder fits `w400`, `w930`, the scale, dx, and dy by matching Source Han Sans JP glyphs against Pretendard JP's copies of the same code points. The 1,291 GB 2312 hanzi whose CN and JP outlines are identical are the calibration set. One set of values applies to every glyph; there are no per-glyph corrections. The fit uses ink area and ink box, not point positions, because Pretendard's TrueType conversion differs (see "Measured facts"). The fitted values and the glyphs that miss by more than the 99% limit in Acceptance 13 are recorded in the build notes.
- **Variation data.** Turn the two masters into `gvar` tuples with the same regions as the copied Pretendard Han glyphs: linear from 400 to `PJ_PEAK` (Pretendard's 930), then holding that shape to 1000. Between 400 and 930, the new glyphs then interpolate exactly the way Pretendard JP's kanji do. They follow Pretendard JP's interpolation, not Source Han Sans's own intermediate masters.
- **Overlap flags** stay as Source Han Sans sets them.
- **Names.** C1 glyphs are `uniXXXX`. C2 and C3 alternates are `uniXXXX.zhs` (for example `uni76F4.zhs` for `直` and `uniFF01.zhs`).
- **GDEF.** Class 1 (base) for every new glyph, like the other added glyphs.

## OpenType features

- New GSUB lookups are appended after lookup 98, and the FeatureList is sorted by tag as the current build does (R38):
  - `locl` hanzi: the 2,212 C2 substitutions;
  - `locl` punctuation: the 13 shared code points and `！：；？`;
  - `locl` quotes: `‘’“”·`.
- A language system `ZHS ` is added:
  - under `hani` with all three lookups;
  - under `latn` and `DFLT` with the punctuation and quotes lookups, so brackets, `！？`, and quotes next to Latin text or digits in Chinese UI switch as well. This follows design decision 12 for JAN.
- The ZHS language systems also get the features the script's default language system turns on (`ss20 jp78 jp83 jp90 nlck fwid pwid` and Wanted Sans's defaults), as KOR does.
- **Which locales reach ZHS.** In HarfBuzz (uharfbuzz 0.57.0), `zh-CN`, `zh-Hans`, `zh-SG`, and plain `zh` select ZHS; a test pins this.
- `zh-TW`, `zh-HK`, and `zh-Hant` select ZHT or ZHH, which get no lookups. Text tagged with them shows the defaults.
- No stylistic set is added for the Chinese forms. *(Designer's call; one can be added later, like `ss20` for Korean.)*

## Flutter usage

The Chinese mode must tag its text Chinese, the same way Japanese needs `ja` today: `TextStyle(fontFamily: 'RoofSans', locale: Locale('zh', 'CN'))`. The same caveats as for `ja` apply: `TextStyle(locale:)` works on Flutter web; `Text.locale` and the app locale do not reach the font there; Android is unverified. Without the locale, Chinese mode still gets every GB 2312 hanzi in one typeface, but the 2,212 C2 hanzi keep their Japanese forms. The README gets a section for this.

## Inputs and licensing

- `inputs.lock.json` gains three files from `adobe-fonts/source-han-sans` at commit `a4f7cf94edfb9d7ffbdfc4841de276358bd7e0f2`:
  - `Variable/TTF/Subset/SourceHanSansCN-VF.ttf` (the C1/C2/C3 source);
  - `Variable/TTF/Subset/SourceHanSansJP-VF.ttf` (used only for calibration and for the C2 form comparison; no glyph from it ships);
  - `LICENSE.txt`.
- The build still reads only `inputs/`. `roofsans-fetch` downloads them; `refs/` does not need a Source Han Sans checkout.
- Source Han Sans is SIL OFL 1.1 with the Reserved Font Name "Source". The family stays "Roof Sans", which does not contain it.
- `OFL.txt` adds the header of Source Han Sans's `LICENSE.txt` verbatim. It currently reads "Copyright 2014-2025 Adobe (http://www.adobe.com/), with Reserved Font Name 'Source'. Source is a trademark of Adobe in the United States and/or other countries." Pretendard's Adobe line ("2014-2021") stays as well. Name ID 0 adds the new Adobe line without the Reserved Font Name clause.
- `OS/2`: code page bit 18 (Chinese Simplified, code page 936) is set, and the Unicode ranges are recalculated.

## Weight axis, metrics, spacing

No change. The new hanzi behave like the existing Han glyphs: they follow Pretendard JP's weights from 400 to 930 and hold the 930 shape to 1000. Vertical metrics stay Wanted Sans's. Han advances are 1920.

## Splitting later

The owner may want the Chinese part in its own file later. The build keeps C1–C3 in their own rule modules and their own lookups, so a later build option can produce two files from the same rules:

- `RoofSansVariable.ttf` without C1–C3 (today's font);
- `RoofSansSCVariable.ttf` with C1, with the C2 and C3 forms as the defaults instead of `locl` alternates, because `locl` cannot reach across files.

The app would then switch `fontFamily` in Chinese mode instead of setting the locale. Splitting saves app size only if the Chinese file is not bundled for every user, for example if it is downloaded when Chinese mode is chosen. Two bundled files would be larger than one, because the shared glyphs appear in both. This split is not built now.

## Acceptance

All existing Acceptance items (1–10 in `docs/ROOF_SANS_DESIGN.md`) still pass, unchanged. In particular, every Wanted Sans glyph and every Pretendard JP copy stays identical (Acceptance 1 and 2), and shaping under `ko`, `ja`, and no locale is unchanged. New items:

11. **cmap.** All 6,763 GB 2312 hanzi map to a glyph. The cmap equals today's cmap plus exactly the 3,260 C1 code points. No other code point is added, removed, or remapped.
12. **Source fidelity.** At `wght` 400 and 930, each C1 and C2 glyph's outline equals Source Han Sans CN at the calibrated weight, after the transform, within 1 unit. At 1000 it equals the 930 shape. The advance is 1920 at every weight.
13. **Match with the existing Han glyphs.** Building the 1,291 calibration hanzi from Source Han Sans JP with the same parameters reproduces Pretendard JP's copies at `wght` 400, 700, and 930. At 700 the comparison uses the linear interpolation of the two transformed masters, which is what the font contains. Ink boxes are true curve bounds. This is the evidence that new and existing hanzi match in size, position, and weight. *(Limits set from the measured distribution; designer's call.)*
    - Ink box, worst edge per glyph: at 400, within 3 units for at least 99% of the set and within 20 units for every glyph; at 700 and 930, within 5 units for at least 99% and within 8 units for every glyph.
    - Ink area: within ±1% in the median and ±3% for each glyph.
    - Glyphs over the 99% limit are listed in the build notes.
14. **Features.**
    - Under the tags that select ZHS, all 2,212 C2 hanzi, the 13 shared code points, `！：；？`, and `‘’“”·` switch, in Han and Latin runs alike; both quotes of `他说“OK”。` have the same advance.
    - Under `ko`, `ja`, `zh-TW`, and no locale, shaping output equals the current build on a sample that includes GB 2312 hanzi, Korean, Japanese, and Latin text.
    - Which tags select ZHS is pinned in a test.
15. **C3 placement.** Each `！：；？‘’“”·` alternate's ink center x is within 1 unit of Source Han Sans CN's ink center after the transform, at 400, 750, and 1000. The drawing equals the Wanted Sans glyph, shifted.
16. **Sanity and determinism.** OTS sanitization and the fontTools round trip pass (Acceptance 8). Two builds give the same SHA-256.
17. **Visual review.** The specimen sheet (`verify/specimen.py`) gets Chinese lines: a UI-style Chinese paragraph with `，。！？“”《》`, and a line mixing C1 hanzi with present hanzi, at 400, 700, and 1000, under `zh-CN` and `ja`. No visible jump in size, position, or weight between C1 hanzi and present hanzi.
18. **Flutter.** `verify/flutter_specimen` gets a Chinese line with `TextStyle(locale: Locale('zh', 'CN'))`. On Flutter web, the C2 forms and Chinese punctuation apply. Android stays outstanding with the rest of Acceptance 10.
19. **Size.** The build notes record the new file size and glyph count.
20. **Specimen page.** `site/specimen.html` and `PAGE_FACTS` in `site/build_site.py` state the new coverage (GB 2312 6,763 of 6,763) and list Simplified Chinese as supported.

## Non-goals

- Traditional Chinese (`zh-TW`, `zh-HK`): no ZHT or ZHH forms, and no completion of Big5.
- The 189 GB 2312 non-hanzi Roof Sans lacks (symbols, enclosed numbers, bopomofo, box drawing). They would need H3/H5-style rules of their own. *(Designer's call; a later task can add them.)*
- Hanzi beyond GB 2312 (GB 18030, 通用规范汉字表).
- Chinese forms for `…` and `—`. They stay Wanted Sans's in every locale, as under `ja`.
- Chinese spacing features (`halt`, `chws`, `vchw`) and vertical writing.
- Splitting into two files now.

## Anti-goals

- Any change to rendering under `ko`, `ja`, or no locale: Wanted Sans glyphs, Pretendard JP copies, and feature behavior stay exactly as they are.
- New hanzi that look larger, smaller, higher, or heavier than the existing Han glyphs next to them.
- Japanese forms for GB 2312 hanzi in Chinese text when the text is tagged Chinese.
- A Han weight that falls back toward Regular above 930.

## Left to the builder

- The calibration method and the final values for `w400`, `w930`, the scale, dx, and dy.
- How to decide "the CN outline differs from JP": outline equality between the two subsets at their default instance is the method used for the counts above.
- How to measure the C3 ink centers and anchor them to the transform.
- Rule names in `selection.py`, the module layout under `src/roofsans/rules/`, and the test layout.
- Whether `PAGE_FACTS` needs new fields for GB 2312.

## Designer's calls to check while reading

1. Simplified Chinese forms apply only under the Chinese `locl`; defaults stay Japanese for the 2,212 C2 hanzi.
2. Source Han Sans CN 2.005 is the source, calibrated against Pretendard JP through the JP subset.
3. `！：；？` keep Wanted Sans's drawing at Chinese positions (R3_SIGN with CN placement).
4. `‘’“”·` become fullwidth Wanted Sans drawings under ZHS, in every script (revised from Han text only, because a Han-only rule split quote pairs around Latin words).
5. ZHS also applies under `latn` and `DFLT` for brackets, `！：；？`, and quotes, as JAN does for brackets.
6. The 189 GB 2312 non-hanzi stay out of scope.
7. `〈〉` stay 698 wide under ZHS, as under JAN.
8. No stylistic set for the Chinese forms.
9. `唾` and `毁` get CN alternates, because the JP subset cannot show that Pretendard's glyphs already have the Chinese form.
10. Acceptance 13 uses limits set from the measured distribution (99% within 3 or 5 units, every glyph within 20 or 8), not a single limit for every glyph.
11. Apostrophes and middle dots between Latin letters or digits keep Wanted Sans's width under ZHS.
12. 199 compatibility ideographs and radicals that share a glyph with a C2 hanzi switch with it under ZHS.
