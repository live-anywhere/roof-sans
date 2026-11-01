# Roof Sans Simplified Chinese Implementation Plan

> **For agentic workers:** Work task by task. Steps use checkbox (`- [ ]`) syntax for tracking. Do not commit; the owner reviews and commits by hand.

**Goal:** Add the 3,260 missing GB 2312 hanzi, Simplified Chinese alternates for 2,212 present hanzi, and Chinese punctuation under a `locl` ZHS, without changing anything under `ko`, `ja`, or no locale.

**Architecture:** Source Han Sans CN 2.005 becomes a third pinned input. A new sampler reads it with its `avar`. A calibration step finds the Source Han Sans weights and offsets that reproduce Pretendard JP's kanji (from the JP subset). Two new rule modules contribute the hanzi (C1, C2) and the punctuation alternates (C3). The GSUB code adds three lookups and a ZHS language system.

**Tech Stack:** Python 3.12, fontTools 4.60.2, uharfbuzz 0.57.0, pytest 9.2.0 (all pinned; no new dependency).

**Spec:** `docs/ROOF_SANS_SIMPLIFIED_CHINESE_DESIGN.md`, which extends `docs/ROOF_SANS_DESIGN.md`. Read both, plus `AGENTS.md` and `docs/ROOF_SANS_BUILD_NOTES.md`.

## Global Constraints

- Wanted Sans glyphs, Pretendard JP copies, and feature behavior under `ko`, `ja`, and no locale do not change (design Acceptance 1, 2, 7; anti-goals).
- Overlap flags stay as each source sets them.
- `wght` axis 400–1000, default 400; vertical metrics unchanged; Han advance 1920.
- New hanzi interpolate linearly from 400 to `PJ_PEAK` and hold the 930 shape to 1000 (the `_PJ_REGIONS` of `variations.py`).
- The build reads inputs only from `inputs/`; two builds give the same SHA-256.
- No new dependency (no numpy); use `statistics` and plain Python.
- No `git commit`, `stash`, `reset`, `checkout`, or `switch`.
- Build to your own path: `uv run roofsans-build --out build/sc/RoofSansVariable.ttf`, and run acceptance tests with `ROOF_FONT=build/sc/RoofSansVariable.ttf`. Do not build to `fonts/` and do not use `build/test/`.
- Glyph names: C1 `uniXXXX`; C2 and C3 alternates `uniXXXX.zhs` (for example `uni76F4.zhs`, `uniFF01.zhs`, `uni201C.zhs`, `uni00B7.zhs`).
- Measured values to reproduce (design "Measured facts"): GB 2312 hanzi 6,763; present 3,503; C1 3,260 (level 1: 1,335; level 2: 1,925); C2 2,212 (2,210 differing + `唾` U+553E, `毁` U+6BC1); calibration set 1,291.

## Review Focus

1. **Plain `zh` locale.** Flutter apps often pass `Locale('zh')`. Expected: either it selects ZHS, or a test pins that it does not and the README says which locale to use. Pinned in Task 5 (`test_zhs_language_tags`).
2. **Quotes around a Latin word inside Chinese text** (`他说“OK”。`). Expected: both quotes of the pair render the same width. Pinned in Task 5 (`test_zhs_quote_pair_matches`), shaped per script run the way `verify/specimen.py::script_runs` splits text.
3. **A C2 hanzi under `ja` or `ko`.** Expected: Pretendard JP's glyph (or the Korean `locl` form), never the `.zhs` form. Pinned in Task 5 (`test_zhs_forms_only_under_zhs`).
4. **C1 hanzi at 1000.** Expected: the 930 shape, not a fall back toward 400. Pinned in Task 3 (`test_c_hanzi_plateau`).
5. **A C2 hanzi with Korean `ss20` or `jp90` turned on under ZHS.** Expected: no crash and no glyph outside the font; the `.zhs` form or the feature's own target. Pinned in Task 5 (`test_zhs_with_other_cjk_features`).

---

### Task 1: Pin Source Han Sans and sample it

**Files:**
- Modify: `inputs.lock.json`, `src/roofsans/inputs.py`, `src/roofsans/sampling.py`, `src/roofsans/context.py`, `tests/conftest.py`
- Test: `tests/unit/test_sampling.py`, `tests/unit/test_inputs.py` (create it if no inputs test exists)

**Interfaces:**
- Produces: `Inputs.shs_cn`, `Inputs.shs_jp`, `Inputs.shs_license` (`Path`); `ShsSampler(font: TTFont)` with `outline(name, wght) -> Outline` and `advance(name, wght) -> float` for Source Han Sans weights 250–900; `BuildContext.shs_cn`, `BuildContext.shs_jp` (`TTFont`), `BuildContext.cs`, `BuildContext.js` (`ShsSampler` for CN and JP); conftest fixtures `shs_cn`, `shs_jp`.

- [ ] **Step 1: Write the failing tests.**
  - `test_lock_has_source_han_sans`: the lock has entries `shs_cn`, `shs_jp`, `shs_license` with repo `source-han-sans`, the paths `Variable/TTF/Subset/SourceHanSansCN-VF.ttf`, `Variable/TTF/Subset/SourceHanSansJP-VF.ttf`, `LICENSE.txt`, URLs at commit `a4f7cf94edfb9d7ffbdfc4841de276358bd7e0f2`, and SHA-256 `25a01e41b5cc99893eb35a6cd2cc7611841dc19eb03cbaf7f0c1de8210f2ba0b` and `4acc34926098472741bbb7be5949b80afa7fc08f41ea3cd80dc34f12f7d55bbc` for the two fonts. Compute the license's SHA-256 from the downloaded file and pin it.
  - `test_inputs_fields_match_lock`: the `Inputs` field names equal the lock's `name` values, in order.
  - `test_shs_sampler_matches_fonttools`: for `一 口 龍 熙` in the CN font at 250, 381.25, 655, 900, `ShsSampler.outline` points equal `TTFont.getGlyphSet(location={"wght": w})` drawn through a recording pen within 1e-6, and the advance is 1000.
  - `test_shs_sampler_rejects_out_of_range`: 249 and 901 raise `ValueError`.
- [ ] **Step 2: Run them to see them fail.** `uv run pytest tests/unit/test_inputs.py tests/unit/test_sampling.py -v`
- [ ] **Step 3: Implement.**
  - Lock entries go after the existing four. `Inputs` gains the three fields in lock order. `--from-refs` keeps working: these files are downloaded because `refs/source-han-sans` does not exist.
  - `ShsSampler(_Sampler)`: `_norm(wght)` is `(wght − 250) / 650` mapped through the font's `avar` segment map (`fontTools.varLib.models.piecewiseLinearMap`). Keep `_Sampler._scalar` (no extrapolation).
  - `make_context` loads both fonts and builds both samplers. Add session fixtures `shs_cn` and `shs_jp` in `tests/conftest.py` next to `pretendard`.
- [ ] **Step 4: Run them to see them pass.** Same command; then `uv run pytest -m "not acceptance"` passes.

### Task 2: Select the C1 code points

**Files:**
- Create: `src/roofsans/chinese.py`
- Modify: `src/roofsans/selection.py`, `src/roofsans/context.py`, `src/roofsans/assemble.py` (only if `planned_cmap` needs a branch), tests that pin per-rule counts
- Test: `tests/unit/test_chinese.py`, `tests/unit/test_selection.py` (or the existing file that pins rule counts)

**Interfaces:**
- Produces: `chinese.gb2312_hanzi() -> tuple[int, ...]` (sorted, 6,763), `chinese.gb2312_levels() -> tuple[tuple[int, ...], tuple[int, ...]]` (3,755 and 3,008); `Rule.C1_HANZI`; `select(wanted, pretendard, shs_cn)` assigns `C1_HANZI` to every GB 2312 hanzi neither input maps.

- [ ] **Step 1: Write the failing tests.**
  - `test_gb2312_counts`: 6,763 hanzi; levels 3,755 and 3,008; every one is in U+4E00–9FFF. Decode with Python's `gb2312` codec, lead bytes 0xB0–0xF7, trail bytes 0xA1–0xFE, as `site/build_site.py` does.
  - `test_c1_selection`: `C1_HANZI` has 3,260 code points (1,335 in level 1, 1,925 in level 2); none is in either input's cmap; all are in Source Han Sans CN's cmap; every other rule's count equals the build notes' table (WANTED 12,032, H6_COPY 7,986, …).
  - `test_select_rejects_missing_source`: with a Source Han Sans CN stub that lacks one C1 code point, `select` raises `ValueError` naming it.
- [ ] **Step 2: Run them to see them fail.**
- [ ] **Step 3: Implement.** `planned_cmap` names C1 glyphs with `roof_glyph_name` (the existing non-H6 branch), so it may need no change. Check that `site/build_site.py` and `select` share the GB 2312 decoding (have `build_site.py` import `chinese.gb2312_levels` if it is simpler).
- [ ] **Step 4: Run them to see them pass.** `uv run pytest -m "not acceptance"`.

### Task 3: Calibrate and build the hanzi (C1, C2)

**Files:**
- Create: `src/roofsans/rules/c_hanzi.py`
- Modify: `src/roofsans/build.py` (add `c_hanzi` to `CONTRIBUTORS` after `h3_enclosed`), `src/roofsans/context.py` (cache the calibration)
- Test: `tests/unit/test_c_hanzi.py`, `tests/acceptance/test_a12_c_hanzi.py`, `tests/acceptance/test_a13_calibration.py`

**Interfaces:**
- Consumes: `ShsSampler`, `chinese.gb2312_hanzi`, `Rule.C1_HANZI`, `remap_pretendard_tuples`, `simple_glyph`-style rounding from `newglyph.py`.
- Produces:
  - `@dataclass(frozen=True) class Calibration: w400: float; w930: float; scale: float; dx400: float; dy400: float; dx930: float; dy930: float`
  - `calibration_set(ctx) -> tuple[int, ...]` (1,291 code points)
  - `calibrate(ctx) -> Calibration` (cached on the context)
  - `zhs_forms(ctx) -> tuple[int, ...]` (2,212 code points, sorted)
  - `hanzi_master(ctx, cp: int, master: int) -> Outline`, `master` 400 or 930: Source Han Sans CN at the calibrated weight, transformed
  - `contribute(ctx) -> list[NewGlyph]`: 3,260 C1 glyphs (`rule=Rule.C1_HANZI`, `unicodes=(cp,)`) and 2,212 C2 alternates (`uniXXXX.zhs`, `unicodes=()`, `rule=Rule.C1_HANZI`).

- [ ] **Step 1: Write the failing unit tests.**
  - `test_calibration_set`: 1,291 code points; `田` and `熙` are in it; `唾` and `毁` are not.
  - `test_zhs_forms`: 2,212 code points; contains `唾 毁 埃 安`; excludes `田 熙`; every one is in the Roof cmap and in GB 2312.
  - `test_calibration_values`: `scale == 1.92`; `w930 == 900`; `w400` within 381.25 ± 1; `dy400` and `dy930` within 21.5 ± 1; `|dx400|` and `|dx930|` ≤ 1.
  - `test_c_hanzi_plateau`: for a C1 glyph (`啊` U+554A), the outline from `newglyph_outline` at t = 1 equals the one at `PJ_PEAK` within 0.5.
  - `test_c_hanzi_masters`: for `啊`, the outline at t = 0 equals `hanzi_master(ctx, 0x554A, 400)` within 1 unit and at `PJ_PEAK` equals `hanzi_master(ctx, 0x554A, 930)` within 1 unit; the advance is 1920 at both.
- [ ] **Step 2: Run them to see them fail.**
- [ ] **Step 3: Implement.**
  - **Form comparison** (`zhs_forms`, `calibration_set`): compare the CN and JP default-instance outlines with `DecomposingRecordingPen` value equality and equal advances. Code points the JP subset does not map go to `zhs_forms` and stay out of the calibration set.
  - **Calibration**, deterministic, no per-glyph corrections:
    - `scale` is fixed at 1.92, so the advance is exactly 1920.
    - `w400`: the Source Han Sans JP weight in [350, 420] where the median over the calibration set of (Pretendard ink area at 400) / (Source Han Sans ink area × 1.92²) equals 1. The ratio falls as the weight rises; bisect to 0.01, then round to 0.25.
    - `w930`: the same at Pretendard 930, searched in [850, 900]; the measured answer is the bound 900, because Pretendard's 930 kanji are about 0.6% heavier than Source Han Sans's maximum.
    - `dx`, `dy` per master: the median, over the calibration set and both edges, of (Pretendard ink-box edge − 1.92 × Source Han Sans ink-box edge).
    - Ink area: absolute signed area of the decomposed outline (reuse `measure.py` if it has one). Ink box: `Outline.bounds()`.
  - **Glyphs:** masters at 400 and 930 from `hanzi_master`, rounded like `simple_glyph`; deltas = master930 − master400, IUP-optimized at tolerance 0.5; tuples via `remap_pretendard_tuples([TupleVariation({"wght": (0.0, 1.0, 1.0)}, deltas)])`. Keep the source glyph's flags (including `OVERLAP_SIMPLE`). `source` = the Source Han Sans glyph name.
  - Print the calibration values to stderr during the build, as the H4 solver does, so the build notes can record them.
- [ ] **Step 4: Run the unit tests to see them pass.**
- [ ] **Step 5: Write the acceptance tests (design Acceptance 12 and 13).**
  - `test_a12_source_fidelity`: for every C1 and C2 glyph, at Roof 400 and 930 the outline equals Source Han Sans CN at the calibrated weight after the transform within 1 unit; at 1000 it equals 930; advance 1920 at 400, 750, 1000. Sample the Roof font with the instancer fixture (`static("roof", w)`).
  - `test_a13_calibration_match`: build the 1,291 calibration hanzi from Source Han Sans JP with the same `Calibration`; against Pretendard JP at 400, 700 (the linear interpolation of the two transformed masters at 300/530, which is how the shipped glyphs interpolate; sampling Source Han Sans directly at an interpolated weight gives an area median of 0.978 because its own interpolation is not linear), and 930. Ink boxes are true curve bounds (a C-specific helper), not `Outline.bounds()`, which includes off-curve points: worst ink-box edge error per glyph ≤ 3 units for ≥ 99% and ≤ 20 for all at 400; ≤ 5 for ≥ 99% and ≤ 8 for all at 700 and 930; ink-area ratio median within ±1%, each glyph within ±3%. Print the glyphs over the 99% limit.
- [ ] **Step 6: Build and run them.** `uv run roofsans-build --out build/sc/RoofSansVariable.ttf`, then `ROOF_FONT=build/sc/RoofSansVariable.ttf uv run pytest tests/acceptance/test_a12_c_hanzi.py tests/acceptance/test_a13_calibration.py -v`. If `test_a13` fails at 700 only, report the measured distribution instead of changing the method; the coordinator decides.

### Task 4: Chinese punctuation alternates (C3)

**Files:**
- Create: `src/roofsans/rules/c_punct.py`
- Modify: `src/roofsans/build.py` (add `c_punct` after `c_hanzi`)
- Test: `tests/unit/test_c_punct.py`, `tests/acceptance/test_a15_c_punct.py`

**Interfaces:**
- Consumes: `Calibration` and `calibrate` from Task 3; `composite_glyph`; Roof's R3_SIGN glyphs.
- Produces: `ZHS_SIGNS = (0xFF01, 0xFF1A, 0xFF1B, 0xFF1F)`, `ZHS_QUOTES = (0x2018, 0x2019, 0x201C, 0x201D, 0x00B7)`, `contribute(ctx) -> list[NewGlyph]` (9 alternates named `uniXXXX.zhs`, `unicodes=()`).

- [ ] **Step 1: Write the failing tests.**
  - `test_c_punct_parts`: each sign alternate is a composite of the same single Wanted Sans component as Roof's default glyph for that code point (`exclam`, `colon`, `semicolon`, `question` or their `.case` names as R3_SIGN found them); each quote alternate's component is the Wanted Sans glyph `ctx.cmap` gives the code point; advance 1920 at every `COMPOSITE_LOCS` location.
  - `test_c_punct_centers`: at t = 0, the alternate's ink center x is within 1 unit of 1.92 × (Source Han Sans CN ink center x at `w400`) + `dx400` (measured CN centers at 400: `！` 250, `：` 250, `；` 244, `？` 247, `‘` 879, `’` 121, `“` 794, `”` 206, `·` 500, in 1000 units).
- [ ] **Step 2: Run them to see them fail.**
- [ ] **Step 3: Implement.** For each `COMPOSITE_LOCS` location t, sample Source Han Sans CN at s(t) = `w400` + (`w930` − `w400`) × min(t / `PJ_PEAK`, 1) and use dx/dy interpolated the same way; component x offset = target ink center − the Wanted component's ink center at t; y offset 0 (Wanted's own height is kept, as R3_SIGN does).
- [ ] **Step 4: Run them to see them pass.**
- [ ] **Step 5: Write `test_a15_c_punct_placement`** (design Acceptance 15): at 400, 750, 1000 each alternate's drawing equals its Wanted component shifted in x only, and its ink center x is within 1 unit of the target. Build and run it as in Task 3.

### Task 5: `locl` ZHS

**Files:**
- Modify: `src/roofsans/features/gsub.py`, `src/roofsans/features/gdef.py` (only if the 9 + 2,212 alternates are not classed automatically)
- Test: `tests/unit/test_features.py`, `tests/acceptance/test_a14_zhs.py`; update `tests/acceptance/test_a07_features.py` only where it pins lookup or feature counts

**Interfaces:**
- Consumes: `c_hanzi.zhs_forms`, `c_punct.ZHS_SIGNS`, `c_punct.ZHS_QUOTES`, `JAN_SHARED`, the existing `mappings["jan"]`.
- Produces: GSUB lookups appended after the current last one (98), in this order: `zhs_hanzi` (2,212 entries), `zhs_punct` (the 13 JAN mappings plus the 4 sign alternates), `zhs_quotes` (5 entries). Two new `locl` FeatureRecords: one with [`zhs_hanzi`, `zhs_punct`, `zhs_quotes`] for `hani`, one with [`zhs_punct`, `zhs_quotes`] for `latn` and `DFLT` (revised during the build: a `hani`-only quotes lookup split the pair in `他说“OK”。`). LangSys `ZHS ` under `DFLT`, `hani`, `latn`, each = that script's default feature indices + its ZHS `locl` record.

- [ ] **Step 1: Write the failing tests.**
  - Unit: lookup count and order; `ZHS ` exists under exactly `DFLT`, `hani`, `latn`; `sort_features` leaves the FeatureList sorted; every Wanted LangSys still turns on the same feature tags as before.
  - `test_zhs_language_tags`: shape `直` with uharfbuzz under each of `zh`, `zh-CN`, `zh-Hans`, `zh-SG`, `zh-TW`, `zh-HK`, `zh-Hant`, `ja`, `ko`, and no language; pin which ones give `uni76F4.zhs`. Expected from the design: `zh-CN`, `zh-Hans`, `zh-SG` do; `zh-TW`, `zh-HK`, `zh-Hant`, `ja`, `ko`, none do not; record what `zh` does and pin it.
  - `test_zhs_switches`: under `zh-CN`, all 2,212 C2 code points give their `.zhs` glyph; the 13 shared code points give their `.pj` glyphs; `！：；？` give `.zhs`; `“中”` (script `hani`) and `“abc”` (script `latn`) give `uni201C.zhs`/`uni201D.zhs`; `ID「abc」` (script `latn`) gives the `.pj` brackets.
  - `test_zhs_forms_only_under_zhs` (Review Focus 3): under `ja`, `ko`, and no language, no shaped glyph name ends in `.zhs` for a sample of all 2,212 C2 code points plus `！：；？‘’“”·`.
  - `test_zhs_quote_pair_matches` (Review Focus 2): `他说“OK”。` split with `verify/specimen.py::script_runs` and shaped per run under `zh-CN`: both quotes are the `.zhs` glyphs with the same advance (1920).
  - `test_zhs_with_other_cjk_features` (Review Focus 5): under `zh-CN` with `ss20`, `jp90`, `fwid` each on, shaping `直安毁！“` returns only glyphs that exist in the font.
  - `test_unchanged_outside_zhs` (design Acceptance 14): under `ko`, `ja`, `zh-TW`, and no language, glyph ids and advances equal those of `fonts/RoofSansVariable.ttf` (the committed build) on a sample with Korean, Japanese, Latin, and 200 present GB 2312 hanzi. Map glyph ids through names, because the new font appends glyphs.
- [ ] **Step 2: Run them to see them fail.**
- [ ] **Step 3: Implement** in `gsub.carry`, after the JAN mapping, following the JAN pattern.
- [ ] **Step 4: Run the unit tests, build, and run the acceptance tests.** Also run `ROOF_FONT=build/sc/RoofSansVariable.ttf uv run pytest tests/acceptance/test_a07_features.py -v`.

### Task 6: Licensing and OS/2

**Files:**
- Modify: `src/roofsans/finalize.py`
- Test: `tests/unit/test_finalize.py`

**Interfaces:**
- Consumes: `Inputs.shs_license`.

- [ ] **Step 1: Write the failing tests.**
  - `OFL.txt` contains the header of Source Han Sans's `LICENSE.txt` verbatim (every line before `This Font Software is licensed`), after Pretendard's header, with `\n` line ends; Pretendard's "Copyright 2014-2021 Adobe" line stays.
  - Name ID 0 contains "Copyright 2014-2025 Adobe (http://www.adobe.com/)" with no "Reserved Font Name" clause, and still contains every line it has today.
  - `OS/2` code page ranges include 932 (Japanese) and 936 (Chinese Simplified).
- [ ] **Step 2: Run them to see them fail.**
- [ ] **Step 3: Implement.** Add `inputs.shs_license` to `copyright_lines` and `write_license`; add 936 next to `JIS_CODE_PAGE`.
- [ ] **Step 4: Run them to see them pass.**

### Task 7: Existing acceptance tests and the full run

**Files:**
- Modify: `tests/acceptance/test_a04_cmap.py` (and any other test that pins totals: code points, glyph count, cmap equality with the selection)
- Create: `tests/acceptance/test_a11_gb2312.py`

- [ ] **Step 1: Write `test_a11_gb2312`** (design Acceptance 11): all 6,763 GB 2312 hanzi map; the cmap equals the committed `fonts/RoofSansVariable.ttf` cmap plus exactly the 3,260 C1 code points, every other entry unchanged.
- [ ] **Step 2: Update count pins.** New totals: cmap 21,718 + 3,260 = 24,978 code points; glyphs 22,923 + 3,260 + 2,212 + 9 = 28,404. Update only tests whose meaning is a total; do not loosen identity tests.
- [ ] **Step 3: Determinism.** `tests/acceptance/test_build_determinism.py` passes.
- [ ] **Step 4: Full run.** `uv run roofsans-build --out build/sc/RoofSansVariable.ttf` then `ROOF_FONT=build/sc/RoofSansVariable.ttf uv run pytest`; every test passes, including Acceptance 1–9 unchanged. Report the build time, file size, SHA-256, glyph count, the calibration values, the Acceptance 13 outliers, and the `zh` result of `test_zhs_language_tags`.

### Task 8: Verification assets and the specimen page

**Files:**
- Modify: `verify/specimen_lines.json`, `verify/flutter_specimen/lib/main.dart`, `site/build_site.py`, `site/specimen.html`, `tests/unit/test_specimen.py` (if it pins the line count), `tests/acceptance/test_site.py` (if needed)

- [ ] **Step 1: Specimen lines** (design Acceptance 17): add, with language `zh-CN`, a UI-style paragraph `欢迎回来！您的预订已确认。请在“我的行程”中查看详情：入住时间为下午三点；如有疑问，请联系客服。《使用条款》【重要】` and a mixed line `他说“OK”。啊阿埃挨哎唉哀皑癌蔼矮艾碍爱隘鞍氨安俺按暗岸胺案`; add the paragraph once more with language `ja`. Run `verify/specimen.py` against `build/sc/RoofSansVariable.ttf` and save the sheets under `build/sc/specimen/`.
- [ ] **Step 2: Flutter specimen** (design Acceptance 18): add a Chinese line using `TextStyle(fontFamily: 'RoofSans', locale: Locale('zh', 'CN'))` and the same text untagged, next to the existing `ja` lines. Do not run Flutter; the coordinator does.
- [ ] **Step 3: Specimen page** (design Acceptance 20): add a measured fact `GB 2312 level 2 hanzi`; update `PAGE_FACTS` to the new values (code points 24,978; glyphs 28,404; GB 2312 level 1 3,755/3,755; level 2 3,008/3,008; Big5 re-measured); update `site/specimen.html`: Simplified Chinese listed as supported (GB 2312), a `zh-CN` sample next to the `ja`/`ko` samples, and the Flutter usage snippet with `locale: Locale('zh', 'CN')`. `uv run python site/build_site.py --out build/sc/site --font build/sc/RoofSansVariable.ttf` (add a `--font` option if the script has none) passes its checks.
- [ ] **Step 4: Run** `uv run pytest -m "not acceptance"` and `ROOF_FONT=build/sc/RoofSansVariable.ttf uv run pytest tests/acceptance/test_site.py`.

### Task 9 (coordinator): Documentation, default build, and checks

- Fold C1–C3 into `docs/ROOF_SANS_DESIGN.md` (selection rule, OpenType features, Acceptance 11–20, non-goals, decisions), keep `docs/ROOF_SANS_SIMPLIFIED_CHINESE_DESIGN.md` as the decision record, and add a build-notes section with the inputs, calibration values, counts, outliers, size, and the corrected SHA-256 history.
- README: Chinese usage (`TextStyle(locale: Locale('zh', 'CN'))`), the inputs list, and the license holders.
- Build the default path once no worker runs; run the full suite; review the specimen sheets and the specimen page in a browser; run the Flutter specimen on Flutter web.
