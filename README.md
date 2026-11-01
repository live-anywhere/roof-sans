# Roof Sans

Roof Sans is a single variable font (`wght` 400–1000) for the LiveAnywhere Flutter app and web pages. It replaces the static PretendardJP files the app ships today.

It is **Wanted Sans as the base, with Pretendard JP filling every character Wanted Sans lacks**:

- Every character Wanted Sans has (Hangul, Latin, digits, punctuation, symbols) is Wanted Sans, unchanged.
- Han ideographs, kana, and Japanese punctuation come from Pretendard JP, unchanged.
- The GB 2312 hanzi Pretendard JP lacks (3,260), and Simplified Chinese forms for 2,212 hanzi it has, come from Source Han Sans CN, scaled and weighted to match Pretendard JP's kanji. The Chinese forms apply only to text tagged Chinese.
- Everything else Pretendard JP adds (Vietnamese and other Latin letters, Greek, Cyrillic, IPA, combining marks, arrows, math, unit squares, enclosed numbers, fractions) is rebuilt from Wanted Sans parts or matched to Wanted Sans's heights, weights, and symbol axes, so it does not stand out next to Wanted Sans text.

The output is `fonts/RoofSansVariable.ttf`, plus web fonts in `dist/web/` (see "Web usage"). The design is in `docs/ROOF_SANS_DESIGN.md`; the Simplified Chinese extension and its reasons are in `docs/ROOF_SANS_SIMPLIFIED_CHINESE_DESIGN.md`. The decisions and measured values from the build are in `docs/ROOF_SANS_BUILD_NOTES.md`.

## Build

Requirements: [uv](https://docs.astral.sh/uv/). uv installs Python 3.12 and the pinned dependencies.

```sh
uv sync
uv run roofsans-fetch
uv run roofsans-build
uv run pytest
```

- `uv run roofsans-fetch` downloads the pinned input fonts (Wanted Sans, Pretendard JP, and the Source Han Sans CN and JP subsets), their license files, and the Google Fonts slicing files the web build uses into `inputs/`, and checks each file's SHA-256 against `inputs.lock.json`. A file already in `inputs/` with the right checksum is reused.
- If you have the upstream repositories checked out under `refs/wanted-sans` and `refs/pretendard` at the pinned commits, copy those inputs from there instead of downloading them. The Source Han Sans files are still downloaded unless `refs/source-han-sans` exists:

  ```sh
  uv run roofsans-fetch --from-refs refs
  ```

- `uv run roofsans-build` writes `fonts/RoofSansVariable.ttf`, `fonts/OFL.txt`, and `OFL.txt`. It takes about 20 seconds. The build is deterministic: the same inputs give a byte-identical font.
- `uv run roofsans-web` writes `dist/web/` from `fonts/RoofSansVariable.ttf`: the font as one WOFF2 file and as a dynamic subset of 245 WOFF2 files, each with its CSS, and a copy of `fonts/OFL.txt`. It takes about 40 seconds. Run it after every font build and commit `dist/web/` with the font; the tests fail while it is stale.
- `uv run roofsans-build --without-chinese --out <path>` builds the font without the Simplified Chinese extension. It reproduces the font from before the extension with the later changes (version 1.300, no Wanted Sans logo, the 1.3.0 license notices), and the tests use it as the "before" font.
- `uv run pytest` runs the unit tests and the acceptance tests. The acceptance tests build their own copies of the font into `build/test/` and `build/test-baseline/`. The full run takes about 5 minutes.

## Specimen page

The specimen page is published at <https://live-anywhere.github.io/roof-sans/>. It introduces the font and lets you try it: a text box to type into with weight, size, and `lang` controls, the weight axis and the seven named weights, the supported languages, the `ko`/`ja`/`zh-CN` differences, symbols, every OpenType feature with its default rendering beside the feature turned on, and web and Flutter usage. Its layout and colors follow GitHub's repository page (Primer), in light and dark themes that follow the system setting.

`site/specimen.html` is the page source. Build it from the current font and open it through a local web server:

```sh
uv run python site/build_site.py --out build/site
uv run python -m http.server -d build/site 8000   # then open http://localhost:8000/
```

- The script writes `index.html` and `RoofSansVariable.woff2` (5.74 MB). The WOFF2 file is byte-identical to `dist/web/woff2/RoofSansVariable.woff2` and the release asset. The page loads the whole font as one file rather than the dynamic subset, so it shows the shaping that crosses subset files (see "Web usage").
- It fills in the font version, the release tag (`v` + the `pyproject.toml` version, used for the jsDelivr and download links), and the file sizes.
- It checks that the numbers the page states (code points, glyphs, the weight range and named weights, the number of OpenType features, Hangul, hanja and kanji coverage, language counts) still match the font, and stops with the list of numbers to update if they do not. The language lists come from `site/languages.json`, produced with Hyperglot 0.8.2 on this font.
- It also checks that the OpenType features tab describes each GSUB and GPOS feature of the font exactly once. Each row names its tags in a `data-feature` attribute; a feature added to or removed from the font stops the build until the tab is updated.
- `.github/workflows/pages.yml` runs the same build on every push to `dev` and `main`, so a stale number fails the run. A push to `main` also deploys the page to GitHub Pages (repository Settings → Pages → Source: GitHub Actions).

## Web usage

Load the dynamic subset from jsDelivr and use the family `Roof Sans`:

```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/live-anywhere/roof-sans@v1.3.0/dist/web/roofsans-dynamic-subset.css">
```

```css
body { font-family: 'Roof Sans', sans-serif; }
```

- The font is split into 245 small WOFF2 files, each listed with a `unicode-range`. The browser downloads only the files that hold characters on the page: a Korean UI sentence needs 8 files (170 KB), where the whole font is 5.74 MB.
- Weights 400–1000 come from the variable axis (`font-weight: 400 1000`). Weights below 400 render as 400.
- Language forms follow the HTML `lang` attribute: `lang="ja"` for Japanese punctuation, `lang="zh-CN"` for Simplified Chinese forms, `lang="ko"` for Korean hanja forms.
- `roofsans.css` loads the whole font as one file instead.
- Shaping rules do not cross file boundaries. For example, a colon or ellipsis right after Hangul keeps its baseline position, and kerning between basic and extended Latin letters (such as `T` + `ō`) is lost. Use `roofsans.css` where that matters. `docs/ROOF_SANS_WEB_DISTRIBUTION.md` lists the limits, the measured sizes, and how the split is made.

## Flutter usage

Copy `fonts/RoofSansVariable.ttf` into the app and declare it as one asset with no `weight` entries:

```yaml
flutter:
  fonts:
    - family: RoofSans
      fonts:
        - asset: assets/fonts/RoofSansVariable.ttf
  assets:
    - assets/fonts/OFL.txt
```

The OFL asks an app that bundles the font to carry its copyright notices and license text (OFL FAQ 1.20). Copy `fonts/OFL.txt` next to the font and add it to the app's license page:

```dart
LicenseRegistry.addLicense(() async* {
  final license = await rootBundle.loadString('assets/fonts/OFL.txt');
  yield LicenseEntryWithLineBreaks(['Roof Sans'], license);
});
```

### Weights

On Flutter 3.41 and later, use `FontWeight`. Flutter maps it to the `wght` axis:

```dart
const TextStyle(fontFamily: 'RoofSans', fontWeight: FontWeight.w700)
```

Before Flutter 3.41, `FontWeight` is not mapped to the axis. Set the axis value with `fontVariations` and leave `fontWeight` unset:

```dart
const TextStyle(fontFamily: 'RoofSans', fontVariations: [FontVariation('wght', 700)])
```

On those versions, a `fontWeight` of w600 or more makes Flutter draw a fake bold on top of the font (see "Known issue" below).

### Korean hanja forms

Han characters use Pretendard JP's Japanese forms by default, the same as the app today. Korean hanja forms (537 characters) are applied when the text style is tagged Korean:

```dart
const TextStyle(fontFamily: 'RoofSans', locale: Locale('ko'))
```

Set the locale on the `TextStyle`, as for Japanese punctuation below; the same locale caveats apply.

They can also be turned on directly with the `ss20` stylistic set:

```dart
const TextStyle(fontFamily: 'RoofSans', fontFeatures: [FontFeature('ss20')])
```

### Japanese punctuation

Japanese text needs the `ja` locale. Set it on the text style:

```dart
const TextStyle(fontFamily: 'RoofSans', locale: Locale('ja', 'JP'))
```

Where the locale comes from matters:

- `TextStyle(locale: …)` works. It was checked on Flutter web (CanvasKit, Flutter 3.44.9).
- `Text(locale: …)` and the app locale (`Localizations`) do not reach the font on Flutter web; the brackets stay narrow.
- On Android, Flutter passes the paragraph locale down to text styles, so the app locale should work there, but this is not verified yet (no emulator run).

See "Migration from PretendardJP" below.

### Simplified Chinese

Roof Sans maps all 6,763 GB 2312 hanzi. Chinese text should be tagged Chinese, the same way Japanese text is tagged `ja`:

```dart
const TextStyle(fontFamily: 'RoofSans', locale: Locale('zh', 'CN'))
```

- With the tag, 2,212 hanzi switch from Pretendard JP's Japanese forms to Simplified Chinese forms (for example `直`, `骨`, `安`). `！：；？` move to the left of the em box. `“”‘’·` become fullwidth, also around Latin words; an apostrophe or middle dot inside a Latin word (`It’s`, `l·l`) keeps its normal width. The ideographic space and the 12 brackets `〈〉《》「」『』【】〔〕` switch to the same forms as under `ja` (fullwidth, except `〈〉` at 698 units).
- Plain `zh`, `zh-CN`, `zh-Hans`, and `zh-SG` all select the Chinese forms. `zh-TW`, `zh-HK`, and `zh-Hant` do not: Traditional Chinese is not supported, and that text shows the default forms.
- Without the tag, every GB 2312 hanzi still comes from Roof Sans, so no character falls back to a system font. The 2,212 hanzi keep their Japanese forms, though.
- The same locale caveats as for Japanese apply: `TextStyle(locale: …)` works on Flutter web; `Text(locale: …)` and the app locale do not reach the font there; Android is unverified.
- The GB 2312 symbols outside the hanzi rows (for example `⑴`, `㈠`, bopomofo, and box drawing) are not in Roof Sans.

## Known issue: Flutter 3.32 and earlier

On Flutter 3.32 and earlier, some Hangul jamo (for example ㅅ and ㄴ) can draw as hollow outlines when text is bold on Android or Flutter web (CanvasKit).

- Cause: these Flutter versions do not map `FontWeight` to the `wght` axis, so a `fontWeight` of w600 or more turns on Skia's fake bold. The Android bold-text accessibility setting does the same. The Skia in these versions runs a path simplification step on glyphs that carry the TrueType overlap flags, and that step fails on Hangul built from overlapping contours. The fake-bold stroke then leaves the jamo hollow.
- Wanted Sans and PretendardJP have the same defect. Roof Sans keeps the overlap flags as the sources set them.
- Flutter 3.35 and later ship a Skia without that step. Flutter 3.41 and later also map `FontWeight` to the axis, so fake bold is not used at all.
- On Flutter 3.32 and earlier, use `fontVariations` for weights and avoid `fontWeight` of w600 or more. The bold-text accessibility setting can still trigger the issue.

References: flutter/flutter#159678, orioncactus/pretendard#177, flutter/flutter#175771. The design's "Flutter rendering" section has the full analysis.

## Migration from PretendardJP

- **Line height does not change.** Roof Sans takes its vertical metrics from Wanted Sans. On Android they resolve to the same values as PretendardJP (ascender 1950, descender −494 at 2048 units per em).
- **Weights below 400 render as 400.** The axis starts at 400. `FontWeight.w100`, `w200`, and `w300` render as Regular, and Flutter does not fall back to another family.
- **Japanese brackets need the `ja` locale.** Thirteen code points are shared between Korean and Japanese text: U+3000 (ideographic space) and `〈〉《》「」『』【】〔〕`. By default they use Wanted Sans's proportional Korean forms (for example, `「` is 640 units wide, where PretendardJP's is 1920). With the `ja` locale they switch to Pretendard JP's Japanese forms: fullwidth (1920 units), except `〈〉`, which Pretendard JP draws 698 units wide. This also applies to brackets next to Latin text or digits, such as `ID「abc」`. For Japanese UI, set `TextStyle(locale: Locale('ja', 'JP'))` (see "Japanese punctuation" above); the app locale alone does not work on Flutter web and is unverified on Android.
- **Remove the `weight` entries** for PretendardJP from `pubspec.yaml` and declare the single Roof Sans asset as shown above.

## License

The fonts — `fonts/RoofSansVariable.ttf`, the web files in `dist/web/`, and the release files — are licensed under the SIL Open Font License 1.1. See `OFL.txt` (copies are in `fonts/OFL.txt` and `dist/web/OFL.txt`). It lists every copyright holder:

- Wanted Lab, Inc. and The Wanted Sans Project Authors (Wanted Sans)
- Kil Hyung-jin (Pretendard)
- Adobe (Source Han Sans, through Pretendard JP and directly for the Simplified Chinese hanzi)
- The Inter Project Authors (Inter, which Pretendard's Latin, Greek, and Cyrillic come from)
- The M+ FONTS Project Authors (M PLUS 1)
- LiveAnywhere Inc. (Roof Sans's changes and additions)

The Reserved Font Names in the upstream licenses are "Pretendard", "Source", "Inter", and "M PLUS 1". The name "Roof Sans" contains none of them. Wanted Sans has no Reserved Font Name, and Roof Sans adds none.

Wanted Sans and the Wanted logo are trademarks of Wanted Lab, Inc.; Pretendard is a trademark of Kil Hyung-jin, Inter of rsms, and Source of Adobe. The OFL grants no trademark rights, so Roof Sans leaves out Wanted Sans's logo glyphs (U+F0000–F0003) and the `liga` feature that formed them from `wanted_logo`. The trademark notices stay in the font's name ID 7 and in `OFL.txt`.

Everything else in this repository — the build code, the tests, the specimen page, and the documentation — is licensed under the MIT license (`LICENSE`). The specimen page's icons are GitHub Primer Octicons, Copyright (c) 2026 GitHub Inc., under the MIT license.
