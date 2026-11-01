# Roof Sans — Web distribution

Roof Sans is 16.2 MB as TTF and 5.74 MB as WOFF2. A web page that shows a few sentences of Korean should not download all of it. Like Pretendard's "dynamic subset", the web build splits the font into small WOFF2 files and lists each file's code points in a CSS `unicode-range`. A browser then downloads only the files whose range covers characters on the page.

`roofsans-web` (`src/roofsans/web.py`) builds everything in `dist/web/` from `fonts/RoofSansVariable.ttf`. `dist/web/` is committed, because jsDelivr serves the files from a Git tag.

## Contents of `dist/web/`

| Path | What it is |
| --- | --- |
| `roofsans-dynamic-subset.css` | One `@font-face` per subset file, each with a `unicode-range`. 159,764 bytes. |
| `woff2-dynamic-subset/RoofSansVariable.subset.N.woff2` | 245 files, 7,799,040 bytes in total, median 26,092 bytes, largest 114,424 bytes. |
| `roofsans.css` | One `@font-face` for the whole font. |
| `woff2/RoofSansVariable.woff2` | The whole font as WOFF2, 5,740,140 bytes. |

Every `@font-face` uses the family name `Roof Sans`, `font-weight: 400 1000`, `font-style: normal`, and `font-display: swap`. Every file keeps the `wght` axis (`fvar`, `gvar`, `STAT`), the family names, and every OpenType rule that applies to its glyphs. fontTools drops the features and the feature name records that have no glyph in a file (for example, file 0 keeps 53 of the font's 65 GSUB features). A requested weight below 400 renders at 400, as in Flutter.

## How the split works

`plan_chunks` assigns each code point of the font to exactly one file, in this order:

1. **Fixed groups**, for the scripts where the shaping rules matter most:

   | Group | Code points | File size |
   | --- | --- | --- |
   | `latin` | Google Fonts' `latin` subset plus every combining diacritical mark (U+0300–036F) | 68,188 bytes |
   | `latin-ext` | U+0100–02FF, U+1D00–1DBF, U+1E00–1EFF, U+20A0–20CF, U+2C60–2C7F, U+A720–A7FF, U+AB30–AB6F (Vietnamese is here) | 96,340 bytes |
   | `greek`, `cyrillic` | the Greek and Cyrillic blocks | 55,540 and 45,580 bytes |
   | `symbols-2070` … `symbols-2500` | U+2070–20FF, U+2100–21FF, U+2200–23FF, U+2400–24FF, U+2500–2E7F | 8,376–22,680 bytes each |

   `latin` keeps the combining marks with their Basic Latin and Latin-1 bases, so marks attach correctly. It also keeps the quotes and the middle dot with the letters around them. The Simplified Chinese rule that keeps `It’s` and `l·l` proportional reads those letters as context (`_zhs_quotes` in `features/gsub.py`).

2. **Google Fonts slicings**, in the order Japanese, Korean, Simplified Chinese. These are the frequency-based slicing strategies Google Fonts uses for Noto Sans JP, KR, and SC (repository `googlefonts/nam-files`, Apache-2.0, pinned at commit `2a68014b…` in `inputs.lock.json`). Each slicing subset that still has unclaimed code points becomes a file. A subset with fewer than 40 unclaimed code points (`MIN_CHUNK`) is merged with the next subsets of the same slicing. Without merging there are 322 files, 81 of them with fewer than 20 code points; with merging there are 245 files, and the download sizes in the table below stay within 1%.

3. **Leftovers**, the code points no group or slicing lists, in files of at most 100 code points (2 files).

fontTools also adds the bidi mirror of a bracket to the file that holds the bracket (its default `bidi_closure`). A mirrored bracket in right-to-left text then comes from the same file. This adds a few duplicate glyphs. The CSS ranges stay disjoint.

The font has 524 Unicode variation sequences (format 14 cmap: U+FE00 and the ideographic variation selectors U+E0100–E0107, for example `喝` + U+FE00 → `uni559D.uv001`). fontTools keeps a sequence only when both the base and the selector are requested, so `subset_request` adds to each file the selectors of the bases it holds. The selectors are not listed in any `unicode-range`: a browser shapes a selector with the font of the character before it. In Chrome, eight sequences drawn with the dynamic subset matched the single file pixel for pixel.

### Why Japanese first

Han ideographs appear in all three slicings, and the first slicing to claim a character decides which file holds it. The order was chosen from estimates on sample text (see "Download sizes" for the sentences). The estimates are relative: glyph data × a constant, using the same constant for each order.

| Order | Korean sentence | Japanese sentence | Chinese sentence |
| --- | --- | --- | --- |
| ja → ko → zhs (chosen) | 8 files, 86 | 13 files, 154 | 33 files, 586 |
| ko → ja → zhs | 8 files, 87 | 22 files, 526 | 33 files, 826 |
| ja → zhs → ko | 10 files, 137 | 13 files, 154 | 33 files, 586 |
| zhs → ja → ko | 10 files, 173 | 16 files, 587 | 9 files, 323 |

Interleaving the three slicings by frequency rank was also tried: compared with the chosen order, the Chinese sentence cost about 0.56 times as much and the Japanese sentence about 2.5 times as much. LiveAnywhere's main languages are Korean and Japanese, and Roof Sans's default Han forms are Japanese, so the chosen order favors them. Chinese text costs more (see below).

## Download sizes

Measured on the committed `dist/web/` of Roof Sans 1.2.0 (bytes of the files a page needs):

| Text | Distinct characters | Files | Bytes |
| --- | --- | --- | --- |
| An English sentence | 28 | 1 | 68,428 |
| A Korean UI sentence (`라이브 방송을 시작하려면 …`) | 53 | 8 | 170,288 |
| A Japanese paragraph (`吾輩は猫である。…`) | 63 | 13 | 333,628 |
| A Chinese paragraph (`我们的直播平台支持多种语言。…`) | 56 | 32 | 1,124,824 |
| Every string in the LiveAnywhere admin web source | 1,176 | 68 | 1,709,504 |
| The whole font, for comparison | all | 1 | 5,740,140 |

In Chrome, with Roof Sans 1.0.0, the check page in "Verification" (Korean, Japanese, Chinese, Greek, Cyrillic, Vietnamese, and Latin text at three weights) loaded 33 subset files, 1,151,040 bytes.

## Known limits

A browser shapes each run of characters with the file that holds them. A contextual substitution, ligature, mark attachment, or kerning pair whose characters are in different files does not apply. Where text must look exactly like the full font, use `roofsans.css` instead.

- **Colon and ellipsis after Hangul.** Wanted Sans's `calt` raises `:` and `…` when they follow Hangul (`colon.case` is 228 units higher; `ellipsis.calt3` is 616 units higher). Hangul and these signs are in different files, so with the dynamic subset `시간: 오후` and `한글…` keep the default baseline forms. Hyphens, dashes, and `@` next to Hangul get `.loclhang` forms instead of `.case` forms, but those have the same outlines, so they look the same.
- **Kerning between `latin` and `latin-ext` letters.** Measured at `wght` 400: `T` + `ō` loses 200 units of kerning, `T` + `ỳ` loses 144, and `Ł` + `ó` loses 56; the amounts vary with weight. (`T` + `ý` is not affected: both are in `latin`.) Vietnamese, Polish, Czech, Turkish, and similar text is affected where a basic letter meets an extended one.
- **Decomposed letters.** HarfBuzz composes `i` + U+0323 into `ị` (U+1ECB) when the font has it. That glyph is in `latin-ext`, so the `latin` file draws `i` and attaches the dot below with GPOS instead. The result is close but not the same glyph. `test_decomposed_letter_outside_latin_keeps_its_mark` pins this behavior.
- **Chinese pages cost more** than Japanese ones because Japanese frequency decides the Han files (see "Why Japanese first").

## Usage

```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/live-anywhere/roof-sans@v1.2.0/dist/web/roofsans-dynamic-subset.css">
```

```css
body { font-family: 'Roof Sans', sans-serif; }
```

- Use `roofsans.css` instead for the single 5.74 MB file.
- jsDelivr serves a minified copy of any `.css` file when `.min` is added before the extension (`roofsans-dynamic-subset.min.css`). Its limits are 20 MB per file and 150 MB per package; the largest file in the repository is the 16.2 MB TTF.
- Language forms follow the HTML `lang` attribute, as Flutter's `TextStyle(locale:)` does: `lang="ja"` for Japanese punctuation, `lang="zh-CN"` (or `zh-Hans`) for Simplified Chinese forms, `lang="ko"` for Korean hanja forms.

## Verification

- `tests/unit/test_web.py`: parsing the slicing files, range formatting, the split order, remnant merging, and the CSS text.
- `tests/acceptance/test_web_dist.py`:
  - the files partition the font's code points;
  - each file maps exactly its range (plus bidi mirrors) and keeps the axis;
  - every variation sequence is in the file that holds its base, and sequences for all nine selectors shape like the whole font;
  - the CSS states the weight range;
  - the full WOFF2 matches the TTF;
  - shaping samples in Latin, Vietnamese, Simplified Chinese, Japanese, Korean hanja, Hangul, Greek, and Cyrillic give the same glyphs and positions at `wght` 400, 700, and 1000 when shaped per file as a browser does (with uharfbuzz) and when shaped with the whole font;
  - the committed `dist/web/` equals a fresh build byte for byte.
- In Chrome, the check page (`build/web-check/index.html`, not committed) set each sample in the dynamic-subset family and in the single-file family. The widths matched for every sample except the ones that contain the limits above (Vietnamese `Tiếng Việt`, and `시간: 오후 한글… 가-나 Tý Łódź`, where the `Łó` pair differs). The screenshots showed the colon and ellipsis difference after Hangul. Variation sequences drawn on a canvas matched the single file pixel for pixel.

## Updating

- After a font change: run `uv run roofsans-build`, then `uv run roofsans-web`, and commit `fonts/` and `dist/web/` together. The tests fail while `dist/web/` is stale.
- To move to newer slicing data: change the `slices_*` entries in `inputs.lock.json` on purpose and re-measure the numbers in this document.
