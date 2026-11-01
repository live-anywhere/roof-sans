# flutter_specimen

Android rendering check for Roof Sans under Flutter 3.44.9 (design Acceptance 10).
The screen draws mixed Korean/Latin/Japanese/hanja text at w100–w900, once through
`fontWeight` and once through the `wght` axis, and compares Roof Sans line metrics
against PretendardJP.

```sh
fvm install   # uses .fvmrc (3.44.9)
tool/stage_fonts.sh <RoofSansVariable.ttf> <PretendardJP-static-dir>
fvm flutter analyze
fvm flutter test
fvm flutter run   # on an Android emulator
```

`assets/fonts/` is git-ignored; stage the fonts before building.

With the system bold-text setting on, Flutter's `Text` merges `FontWeight.bold`
into every style. Every `fontWeight` line then requests w700, and the `wght` lines
keep their axis value with a style weight of w700, which can trigger fake bold. The
line labels show this. With bold text on, only the `fontWeight` lines show what the
app draws.
