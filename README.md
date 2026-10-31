# Roof Sans

Roof Sans is a single variable font (`wght` 400–1000) for the LiveAnywhere Flutter app. It replaces the static PretendardJP files the app ships today.

It is **Wanted Sans as the base, with Pretendard JP filling every character Wanted Sans lacks**:

- Every character Wanted Sans has (Hangul, Latin, digits, punctuation, symbols) is Wanted Sans, unchanged.
- Han ideographs, kana, and Japanese punctuation come from Pretendard JP, unchanged.
- Everything else Pretendard JP adds (Vietnamese and other Latin letters, Greek, Cyrillic, IPA, combining marks, arrows, math, unit squares, enclosed numbers, fractions) is rebuilt from Wanted Sans parts or matched to Wanted Sans's heights, weights, and symbol axes, so it does not stand out next to Wanted Sans text.

The output is `fonts/RoofSansVariable.ttf`. The design is in `docs/ROOF_SANS_DESIGN.md`. The decisions and measured values from the build are in `docs/ROOF_SANS_BUILD_NOTES.md`.

## Build

Requirements: [uv](https://docs.astral.sh/uv/). uv installs Python 3.12 and the pinned dependencies.

```sh
uv sync
uv run roofsans-fetch
uv run roofsans-build
uv run pytest
```

- `uv run roofsans-fetch` downloads the two pinned input fonts and their license files into `inputs/` and checks each file's SHA-256 against `inputs.lock.json`. A file already in `inputs/` with the right checksum is reused.
- If you have the upstream repositories checked out under `refs/wanted-sans` and `refs/pretendard` at the pinned commits, copy the inputs from there instead of downloading them:

  ```sh
  uv run roofsans-fetch --from-refs refs
  ```

- `uv run roofsans-build` writes `fonts/RoofSansVariable.ttf`, `fonts/OFL.txt`, and `OFL.txt`. It takes 12–14 seconds. The build is deterministic: the same inputs give a byte-identical font.
- `uv run pytest` runs the unit tests and the acceptance tests. The acceptance tests build their own copy of the font into `build/test/`. The full run takes about 4 minutes.

## Flutter usage

Copy `fonts/RoofSansVariable.ttf` into the app and declare it as one asset with no `weight` entries:

```yaml
flutter:
  fonts:
    - family: RoofSans
      fonts:
        - asset: assets/fonts/RoofSansVariable.ttf
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

Roof Sans is licensed under the SIL Open Font License 1.1. See `OFL.txt` (a copy is also written to `fonts/OFL.txt`). It lists every upstream copyright holder:

- Wanted Lab, Inc. and The Wanted Sans Project Authors (Wanted Sans)
- Kil Hyung-jin (Pretendard)
- Adobe (Source Han Sans)
- The Inter Project Authors (Inter, which Pretendard's Latin, Greek, and Cyrillic come from)
- The M+ FONTS Project Authors (M PLUS 1)

The Reserved Font Names in the upstream licenses are "Pretendard", "Source", "Inter", and "M PLUS 1". The name "Roof Sans" contains none of them. Wanted Sans has no Reserved Font Name.
