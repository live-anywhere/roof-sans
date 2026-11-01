# Roof Sans — Build notes

These notes record how the build implements `docs/ROOF_SANS_DESIGN.md`: the input pinning, the glyph naming, the decisions made where the design or the plan was open or wrong, the tolerances the tests use, and the values the build solves or measures. The design stays the binding authority. Where these notes and `docs/ROOF_SANS_IMPLEMENTATION_PLAN.md` disagree, these notes describe the code as built.

Labels such as "R17" are the numbers of the rulings made during implementation. They are kept so a reviewer can trace a decision. Each entry here states the decision in full; the ruling log is not needed to read it.

All values are in font units (2048 per em) unless stated otherwise. "t" is the normalized Roof axis position: t = (wght − 400) / 600.

## 1. Inputs and pinning

`inputs.lock.json` pins seven files. Each entry has the upstream repository, the path, a `raw.githubusercontent.com` URL at the full 40-character commit, and the SHA-256. The last three came with the Simplified Chinese extension (section 12).

| Name | File | Commit | SHA-256 | Bytes |
| --- | --- | --- | --- | --- |
| `wanted` | `WantedSansVariable.ttf` (1.003) | `02c9b822349c188ada95f9e2d90c2ed18f853235` | `9953a7cf…a967f5` | 4,669,352 |
| `pretendard` | `PretendardJPVariable.ttf` (1.309) | `7aeb0698819be2b4097dae8ec8fe6a795e5cf3ae` | `bc1d77db…535cbb` | 13,087,888 |
| `wanted_ofl` | Wanted Sans `OFL.txt` | `02c9b82…` | `db345ad0…0d4331` | 4,394 |
| `pretendard_license` | Pretendard `LICENSE` | `7aeb069…` | `82e9c8a4…f088d70a` | 4,816 |
| `shs_cn` | Source Han Sans `SourceHanSansCN-VF.ttf` (2.005, `Variable/TTF/Subset/`) | `a4f7cf94edfb9d7ffbdfc4841de276358bd7e0f2` | `25a01e41…f2ba0b` | 17,749,860 |
| `shs_jp` | Source Han Sans `SourceHanSansJP-VF.ttf` (2.005, same folder) | `a4f7cf9…` | `4acc3492…7f55bbc` | 9,564,672 |
| `shs_license` | Source Han Sans `LICENSE.txt` | `a4f7cf9…` | `fcac737e…c2bac5a2` | 4,463 |

`roofsans-fetch` (`src/roofsans/inputs.py`) fills `inputs/` in lock order:

1. A file already in `inputs/` whose SHA-256 matches the lock is reused.
2. Otherwise, with `--from-refs DIR`, the file is copied from `DIR/<repo>/<path>` when it exists there.
3. Otherwise it is downloaded from the lock URL.

The data goes to a temporary file in `inputs/`, is checked, and is then moved into place. A mismatch removes the temporary file and raises `InputChecksumError`. Nothing is written under `refs/`. The build itself only reads `inputs/`. The test fixture `inputs` calls the same function with `refs/` as the copy source, so tests copy from `refs/` when it exists and download otherwise.

Python dependencies are pinned with `==` in `pyproject.toml` and locked in `uv.lock`: Python 3.12 (3.12.13 in the current `.venv`), fontTools 4.60.2, skia-python 144.1, uharfbuzz 0.57.0, opentype-sanitizer 9.2.0, pytest 9.2.0, brotli 1.2.1, and the build backend uv_build 0.11.27. brotli was added for the specimen page: fontTools needs it to write WOFF2, which keeps the self-contained page near 5 MB instead of 16 MB with the TTF. The plan's selection counts were measured with Python 3.9's Unicode 13.0 data; Python 3.12's Unicode 15.0 data gives the same count for every rule.

The package version in `pyproject.toml` is `1.0.0` because PEP 440 normalizes `1.000`. The font's own version, 1.000, is set by `finalize.py`.

## 2. What the build produces

`roofsans-build` (`src/roofsans/build.py`) runs these steps:

1. Load both inputs and assign every code point either font maps to one rule (`selection.py`).
2. Collect the Pretendard glyphs to copy and name them (`rules/h6_copy.py`).
3. Plan the cmap.
4. Run the rule modules in a fixed order: `h6_copy`, `r3_fullwidth`, `h4_letters`, `h5_symbols`, `h2_compose`, `h3_construct`, `h3_enclosed`. A later rule may use a glyph an earlier rule contributed; for example, unit squares use H4's `Ω`.
5. Insert the glyphs into the Wanted Sans binary. If any planned code point has no glyph, the build stops with `no glyph for N planned code points (RULE: n, …)` (R11).
6. Write the cmap (formats 4, 12, and 14), the OpenType features, and the names, then save the font and the license text.

Counts on the pinned inputs:

| Rule | Code points | What it does |
| --- | --- | --- |
| `WANTED` | 12,032 | Wanted Sans glyph, unchanged |
| `H6_COPY` | 7,986 | Pretendard JP glyph copied unchanged (Han, kana, Japanese punctuation) |
| `R3_FULLWIDTH` | 62 | fullwidth digits and letters from Wanted Sans ASCII |
| `R3_SIGN` | 23 | fullwidth signs from Wanted Sans, at Pretendard's position |
| `H2_COMPOSE` | 228 | decomposable Latin letters, including Vietnamese |
| `H3_SEQUENCE` | 127 | 80 unit squares, 11 digraphs, 32 Roman numerals, `₨ № ℡ ℻` |
| `H3_FRACTION` | 7 | `℀ ℁ ℅ ℆ ⅓ ⅚ ⅟` |
| `H3_ENCLOSED` | 23 | `⑩`–`⑳`, `⓫`–`⓴`, `❿`, `➉` |
| `H3_SUPSUB` | 10 | `⁺⁻⁼⁽⁾ ₊₋₌₍₎` |
| `H4_LETTER` | 1,012 | harmonized Pretendard letters (669 lowercase zone, 343 capital zone) |
| `H5_SYMBOL` | 208 | aligned Pretendard symbols (OTHER 114, CURRENCY 30, ARROW 27, GEOMETRIC 20, MATH 17) |
| `EXCLUDED_PUA` | 382 | Pretendard's Private Use Area, left out |

The cmap has 21,718 code points and 524 variation sequences. The font has 22,923 glyphs: 12,663 from Wanted Sans, 8,537 Pretendard copies, 1,699 glyphs for the other rules (`➉` shares `⑩`'s glyph), and 24 helper glyphs.

The counts above are without the Simplified Chinese extension. With it, `C1_HANZI` adds 3,260 code points, so the cmap has 24,978 code points and the font 28,404 glyphs (section 12).

The build takes about 20 seconds with the extension (12–14 seconds without). The font committed before the extension (`roofsans-build --without-chinese` reproduces it) is 11,798,960 bytes with SHA-256 `6a01839de58c49b41cfa6bba64a6653ab8b66fcab74e7150ae55cd4173272325`. An earlier version of these notes gave `9927013a…8defe` (11,779,304 bytes), from a build before the last change to the committed font. Two builds from the same inputs are byte-identical (`test_build_determinism.py`).

## 3. Glyph naming

- Wanted Sans glyphs keep their names.
- Pretendard copies keep Pretendard's names. A copy whose name Wanted Sans already uses gets the suffix `.pj`. There are 68 such copies: the 13 shared CJK punctuation glyphs (for example `uni300C.pj`), quotes such as `quoteright.pj` and `quotedblbase.pj`, and Hangul compatibility jamo such as `uni3131.pj` that Pretendard uses as components of its enclosed Hangul.
- Every glyph the build synthesizes or harmonizes is named `uniXXXX` (BMP) or `uXXXXX`, with the suffix `.roof` when that name is already taken. No name is taken in the current build, so no `.roof` glyph exists.
- Helper glyphs with no code point start with `roof.`: `roof.ring` and `roof.disc` (the enclosures), `roof.pair.10`–`roof.pair.20` (the figure pairs inside the ring), and `roof.knockpair.10`–`roof.knockpair.20` (the knocked-out figure pairs inside the disc).
- `➉` U+2789 maps to `⑩`'s glyph `uni2469`; there is no separate glyph (R14).

## 4. Axis and variation data

- The Roof axis is `wght` 400–1000, default 400. Constants are in `src/roofsans/axis.py`.
- Pretendard JP's 930 master sits at t = 530/600, stored as F2Dot14 `14473/16384` (0.88336, `PJ_PEAK`). Wanted Sans's 750 master sits at t = 0.58331298828125 (`W_MID`), the value stored in its `gvar` regions.
- **Copied Pretendard glyphs** keep their own `gvar` tuples. A tuple on the region (0, 1, 1) is replaced by two tuples with the same deltas: (0, `PJ_PEAK`, 1) and (`PJ_PEAK`, 1, 1). The glyph then reaches its 930 shape at `PJ_PEAK` and holds it to 1000. Tuples with a negative peak (Pretendard's range below 400) are dropped. Any other region raises an error, so an input change cannot pass silently.
- **Harmonized glyphs** are built as master outlines and turned into `gvar` tuples with `fontTools.varLib.models.VariationModel` (`tuples_from_masters`). H4 letters and H5 symbols use masters at t = 0, 0.5, 0.75, 1 (`H4_LOCS`, 400/700/850/1000). Composites use t = 0, 0.5, `W_MID`, 1 (`COMPOSITE_LOCS`). The enclosed numbers and sup/sub signs use t = 0, `W_MID`, 1.
- **Sampling past 930.** `PretendardSampler` evaluates Pretendard's tuples with extrapolation, so it can sample any weight from 45 to 1100.
- **Component transforms (R4).** 47 Pretendard composites use a 2×2 component transform: mirrors such as `parenright` (mirrored `parenleft`) and `uni3009` (mirrored `uni3008`), rotations such as `arrowdown` (`arrowup` turned 180°), and one scale (`Ю` uses `hyphen` at x-scale 0.70001220703125). The samplers decompose composites with the full transform and with the component offsets varied through `gvar`. A mirror reverses the contour direction, and the points are kept as the transform gives them. The emboldening code therefore takes orientation from the total signed area of the glyph, not from each contour.
- **Rounding.** Delta rounding (≤ 0.5) and the IUP optimization tolerance (0.5) can add up, so a master reconstructed from `tuples_from_masters` is within 1 unit of its outline, not within 0.5 (0.749 measured over `A a zero S g` at 25-unit steps). Tests on harmonized glyphs therefore allow at least 1 unit.
- **Composite offsets (R20).** `composite_glyph` used to round each master offset to an integer before computing deltas, so values at `W_MID` drifted by up to 1 unit, and a fullwidth glyph's two side gaps differed by up to 2. It now computes the deltas from unrounded offsets and advances and rounds them progressively. Every master reconstructs within 0.5.
- **Overlap flags.** Copies keep their flags. Every composite in both inputs sets `OVERLAP_COMPOUND` on its first component, so `composite_glyph` does the same for every composite it builds (R21). An outline decomposed from a composite carries `OVERLAP_SIMPLE` on its first point.

## 5. The corrected advance fact

The design's planning found that Wanted Sans's advances vary with weight. For example, `zero` is 1280 / 1373 / 1440 at 400 / 750 / 1000. A measurement that misses this sees a fixed advance.

The trap: in fontTools, `TTGlyphSet[name].width` returns the default `hmtx` advance until the glyph has been drawn, even when the glyph set was made for another location. All code measures variable advances from the phantom points instead (`Outline.advance()` in the samplers), or from a `fontTools.varLib.instancer` instance. This matters for rule 3 (each fullwidth glyph needs its own centering offset per weight), H3 sequences (cumulative advances), and the H5 advance ratio.

## 6. Decisions by rule

### Selection

- `JAN_SHARED` has 13 code points: U+3000, U+3008–3011, U+3014, U+3015 (R9). Earlier text said 11; that was a counting error. The ranges, the character list `　〈〉《》「」『』【】〔〕`, and both fonts agree on 13.
- Zone (lowercase or capital) for every H4 letter comes from the Unicode category: `Lu Lt Nl` are capitals, everything else uses the lowercase zone. This includes Greek and Cyrillic.
- 22 Greek and Cyrillic code points that are not letters (spacing accents, U+037E `;`, U+0387 `·`) fall under H4 with the lowercase zone, because H4 takes the Greek and Cyrillic blocks whole.
- `〈 〉` U+2329/232A are outside the design's Han/Japanese blocks, so they are H5 symbols (category OTHER) and follow H5's weight rule, not the 930 plateau.

### H6 copies

- The copy set starts from the `H6_COPY` glyphs, the 13 `JAN_SHARED` glyphs, the 524 variation-sequence targets, and the outputs of Pretendard GSUB lookups 34 (`locl` KOR), 73–76 (`jp78 jp83 jp90 nlck`), and 77–85 (the `rlig` kana alternates). It then adds every component of a copied composite, recursively. That gives 8,537 glyphs. 12 of them are composites, and 5 of those carry a 2×2 transform.
- Copies are sampled through `PretendardSampler` when the build measures them, because only the sampler applies component transforms.
- Of the copies, 8,536 carry an overlap flag in Pretendard, and all 8,537 keep Pretendard's flags.

### Rule 3: fullwidth letters and signs

- `R3_FULLWIDTH`: one component, the Wanted Sans ASCII glyph, at x offset (1920 − Wanted advance(t)) / 2 at each `COMPOSITE_LOCS` location; advance 1920. Worst difference between the left and right gaps: 0 at 400 and 1000, 0.996 at 750.
- `R3_SIGN`: one component, the Wanted Sans glyph with the name of Pretendard's single component (five are `.case` glyphs such as `plus.case`). Its ink-box center x is placed on the ink-box center x of Pretendard's fullwidth glyph sampled at min(wght, 930). The Wanted component itself follows Wanted Sans to 1000. Worst ink-center error: 0.497 at 750.

### H3 sequences and fractions

- Unit squares (U+3380–33DD) take the code points of the components of Pretendard's composite, in order, and use the Roof cmap glyph for each one. None of the 80 squares uses a component transform (R5). `sequence_parts` raises an error if a future input adds one.
- Eleven squares, `㎕` among them, use U+00B5 MICRO SIGN, as Pretendard's composites do (R15). Wanted Sans has that glyph, so they use Wanted's `uni00B5`, not Greek `μ`. Only `㏀ ㏁` need an H4 glyph (`Ω`, `uni03A9`).
- Digraphs, Roman numerals, `₨ ℡ ℻` use the Unicode compatibility decomposition.
- `№` U+2116 has no useful decomposition, so the plan chose `N` + `ordmasculine` (`º`).
- Fractions are `<first>.numr` + `fraction` + `<last>.dnom`, the way Wanted Sans builds `½`; `⅟` has no denominator. `fraction_offsets` reproduces Wanted's own `onehalf`, `onequarter`, and `threequarters` exactly.
- Offsets are the cumulative Roof advances at each location; the advance is their sum.

### H3 enclosed numbers

Scope: the 23 code points Pretendard JP has and Wanted Sans lacks: `⑩`–`⑳`, `⓫`–`⓴`, `❿`, and `➉` (22 glyphs). Wanted Sans already has `①`–`⑨`, `⓪`, `❶`–`❾`, `⓿`, and the other enclosed forms in U+2460–24FF and U+2776–2793 that either font maps. No other enclosed number is in either font.

The final rule (R22 as amended, and R27 with both addenda):

- `roof.ring` is contours 0–1 of Wanted's `①` (`uni2460`), with `uni2460`'s own `gvar` deltas sliced to those points. The ring therefore equals `①`'s ring exactly at every weight. `roof.disc` is the largest contour of `❶` (`uni2776`).
- Figures come from Wanted's own enclosed digits, not from `.numr`: ring numbers from `⓪` and `①`–`⑨` (the contours other than the ring), disc numbers from `⓿` and `❶`–`❾` (the contours other than the disc). Wanted's `.numr` figures overlap themselves (the crossbar of `4` over its stem, the flag of `1` over its stem). Reversed inside a disc, each overlap winds back to ink and leaves black slivers in the white figures. Wanted draws its enclosed figures without overlaps, and the disc figures are already reversed.
- The two figures sit side by side with the `.numr` pair's ink gap, scaled by the figure-height ratio. Each figure keeps Wanted's vertical position.
- The pair is scaled about its ink center by s(t) = min(1, limit / reach). "Reach" is the distance from the pair's ink center to its farthest ink point. "Limit" is the inner radius of the ring (or the disc's radius) minus Wanted's tightest distance from a single figure in `①`–`⑨` (`❶`–`❾`) to that circle.
- There is no stroke restoration. Restoring the stroke weight with an outline offset made the ring numbers dark blobs at 1000 (`⑳` was unreadable). On the discs, the offset folded concave corners into ink inside the white figures (up to 7,404 units² in `⓴` at 1000).
- Each enclosed glyph is a composite: the ring or disc plus its pair helper, centered on the enclosure's ink, with the enclosure's advance (1878 / 1934 / 1974 at 400 / 750 / 1000).

Measured scale s at 400 / 750 / 1000: ring and disc numbers both range 0.64–0.83 at 400 and 0.63–0.80 at 1000. `⑪ ⓫` are the largest (0.833 at 400), and `⑳ ⓴` are the smallest (0.640 / 0.632 / 0.627 for `⑳`). Figure stems are s × the enclosed `1`'s stem (136 / 180.3 / 212), so the stem ratio equals s.

Earlier rules that were tried and replaced:

- Plain `.numr` pairs overran the ring's inner gap in 9 of 11 numbers at 1000, and `⑳` crossed the ring.
- A straight-gap target shrank the pairs to s = 0.32–0.57 and closed counters.

### H3 superscript and subscript signs

`⁺⁻⁼⁽⁾ ₊₋₌₍₎` are simple glyphs built from Wanted's `plus minus equal parenleft parenright` at t = 0, `W_MID`, 1:

1. Scale by k = 0.5 (height of `zero.dnom` / height of `zero` at 400).
2. Embolden in x and y by (k_s − k) × the sign's stroke, where k_s = figure stem of `one.dnom` / figure stem of `one`. The figure stem is the first horizontal run at 25% of the glyph height (R16). The plan's 75% height crossed the flag of Wanted's `1`, not its stem. k_s = 0.7907 / 0.6464 / 0.6029.
3. Shift y by −strength/2 (R23). FreeType's emboldening keeps bottom edges and raises tops by the full strength, which would lift each sign by 18–26 units at 400.
4. Shift y by +936 (superscript) or −208 (subscript), the offsets Wanted Sans uses for `²` and `₂`.
5. Set the advance to k × the source advance, with the ink centered.

Wanted's own `+` is thinner than its `1` at heavy weights (bar / stem 1.023 / 0.900 / 0.863). The rule keeps that ratio, so the test checks the sign-to-figure ratio within 2% (R18), not an absolute stroke width. Measured for `⁺`: 1.029 / 0.899 / 0.862 against Wanted's 1.023 / 0.900 / 0.863.

### H4 letters

Method per master (`src/roofsans/harmonize.py`):

1. Sample Pretendard at w′, the weight where its `l` stem equals Wanted's at the target weight.
2. Embolden in y only by δy, with x strength 0 (`embolden_xy`, a port of FreeType's `FT_Outline_EmboldenXY`). x and the advance are unchanged.
3. Map y piecewise-linearly so each zone lands on Wanted's value: descender, bottom overshoot, baseline, x-height, top overshoot, and ascender for the lowercase zone; bottom overshoot, baseline, cap height, and top overshoot for capitals. The Pretendard zones are measured after emboldening.
4. Keep Pretendard's advance sampled at w′.

Solved values (the solver runs at build time, and its results are cached per build context):

| Master wght | w′ | δy | F |
| --- | --- | --- | --- |
| 400 | 388.85 | 7.10 | 0.360 |
| 700 | 672.18 | 41.24 | 0.757 |
| 850 | 813.33 | 61.34 | 0.934 |
| 1000 | 954.22 | 80.26 | 0.993 |

How δy is chosen (R17): δy is the value in [0, 200] that minimizes F = max(|median r| / 0.03, max |r| / 0.10). r is the relative error (Roof − Wanted) / Wanted of each horizontal stroke that `test_a05_h4` checks, in two groups:

- reference group: Pretendard `o` top, `o` bottom, `e` top, `H` bar, `n` arch;
- letter group: Cyrillic `о` top and bottom, `е` top, `п` arch, `Н` bar, and Greek `ο ε π`.

The median term takes the worse of the two groups' medians. F ≤ 1 means every Acceptance 5 stroke check passes. The pair list is defined once in `harmonize.py` (`REFERENCE_STROKES`, `LETTER_STROKES`) and shared by the solver and the test. The solver searches a 0.25-unit grid, then refines within ±0.25 of the best point; ties go to the middle of the F ≤ 1 window.

Two simpler rules fail Acceptance 5:

- The plan's zero-median rule over the reference group gives δy 5.0 / 48.1 / 94.3 and fails `е` top at 1000 (+12.7%).
- The spike's values (13 / 37.5 / 78.5) came from a different set: its "`o` top" and "`e` top" columns measured the bottom strokes. That set fails the reference median at 400 (+3.6%) and the letter median at 700 (−3.2%).

At 1000 the window where F ≤ 1 is only about δy 80–80.5. Wanted's `e` top (304) is much thinner than its `o` (360), while Pretendard's `е` follows its `о`. Any change to the zone glyphs or the stroke measurement can break `test_a05_h4`.

Other H4 decisions (R19):

- **Masters at 400, 700, 850, and 1000.** With three masters, the letter-group median at 850 was −3.2%, 0.2 points outside ±3%.
- **Cyrillic `у`** is compared with Wanted's `y` (−432), not `g` (−460). Pretendard's `у` ends at the depth of its own `p y q`.
- **Cyrillic `н п` stems.** Pretendard draws them thinner than its `n` (375 and 371 against 400 at w′ 954), as optical compensation, and H4 keeps that. The test checks that the Roof `н`/Wanted `n` stem ratio equals Pretendard's own `н`/`n` ratio within ±3%. Raw differences against Wanted's `n` at 1000: `н` −6.2%, `п` −7.3%.

Letter group on the built font:

| wght | median | worst stroke |
| --- | --- | --- |
| 400 | −0.6% | `о` bottom −3.7% |
| 700 | −2.25% | `е` top +7.4% |
| 1000 | −3.0% | `е` top +9.9% |

At 700–1000, thickening by δy fills some sharp notches and narrows some apertures. Section 8 explains how the outline check treats this.

### H5 symbols

Each category maps through a reference glyph both fonts have (`src/roofsans/rules/h5_symbols.py`):

- ARROW → `→`: height ratio, its own advance ratio, center 725;
- MATH → `+`: width ratio, center 540;
- GEOMETRIC → `■` (`●` for the one circle, `◯`): height ratio, centered on Wanted's measured center;
- CURRENCY and OTHER: identity, sampled at H4's w′.

For ARROW and MATH, the sample weight is solved so that the scaled stroke equals Wanted's (three iterations from H4's w′). The vertical shift maps the Pretendard reference's measured center at the sample weight onto 725 or 540 (R29 addendum). Pretendard's `+` center rises from 566 to 588.7 across its weights, so a fixed center would put `+` at about 564 at 1000.

| Category | wght | scale | shift_y | advance ratio | sample wght | scaled stroke / Wanted |
| --- | --- | --- | --- | --- | --- | --- |
| ARROW | 400 | 0.9986 | 91.9 | 1.0956 | 381.90 | 152.0 / 152.0 |
| ARROW | 700 | 0.9361 | 132.2 | 1.0834 | 760.52 | 234.5 / 235.0 |
| ARROW | 850 | 0.9004 | 155.1 | 1.0764 | 975.34 | 275.2 / 276.5 |
| ARROW | 1000 | 0.8929 | 160.1 | 1.0725 | 1100 (clamped) | 301.5 / 318.0 |
| MATH | 400 | 1.1309 | −100.1 | 1.1309 | 348.93 | 164.0 / 164.0 |
| MATH | 700 | 1.0977 | −92.1 | 1.0977 | 626.59 | 250.1 / 250.0 |
| MATH | 850 | 1.0840 | −91.1 | 1.0840 | 772.89 | 293.0 / 293.0 |
| MATH | 1000 | 1.0701 | −90.0 | 1.0701 | 923.31 | 336.1 / 336.0 |
| GEOMETRIC (`■`) | 400 / 1000 | 1.0618 / 1.0784 | −43.8 / −54.7 | = scale | H4 w′ | — |
| GEOMETRIC (`●`) | 400 / 1000 | 1.0700 / 1.0898 | −48.7 / −64.0 | = scale | H4 w′ | — |

- **Clamp at 1100 (R28).** Pretendard's `→` head grows with weight, so the height-ratio scale falls as the sample weight rises. At 1000 no weight in 45–1100 reaches Wanted's 318 shaft; the best is 301.5 at 1100. The sample weight is clamped at 1100, and arrows at 1000 are 5.2% lighter than Wanted's `→`. `CLAMPED_STROKES = {(ARROW, 1.0)}` lists the clamp, and a unit test asserts it.
- **Off-axis symbols (R29).** Pretendard draws `↩ ↪` (the hook rises above the head), `≤ ≥` (center 589), `∞` (616), and `⋯` (723) off its own axis (`+` at 566). The per-category transform keeps that offset, scaled. Measured centers at 400 / 1000: `↩↪` 835.5 / 800.0, `≤≥` 566.0 / 566.0, `∞` 596.5 / 571.0, `⋯` 718.0 / 685.0.

### H2 letters (Vietnamese and other decomposable Latin)

Each of the 228 letters is a composite of the Wanted base plus marks, in NFD order (`src/roofsans/rules/h2_compose.py`). Marks are Wanted's when it has them (19 marks), otherwise H4 marks: `uni0309` hook above (24 uses), `uni0311` inverted breve (12), and `uni031B` horn (24).

- **Offsets.** At each `COMPOSITE_LOCS` location: base anchor − mark anchor + Δ(t). Anchors come from Wanted's GPOS mark-to-base lookup 7 (lookup 9 for the ogonek `uni0328`). Δ(t) is the variation of the mark offset in an existing Wanted composite with the same base and mark class; for example, `ê`'s circumflex moves with weight. Every Wanted composite group with the same base and class has the same Δ, so the choice of source composite does not matter.
- **Pretendard anchors (R25).** Pretendard's anchors sit at a different height (lowercase top 1268, capital 1630) from Wanted's (1032, 1448). Every Pretendard anchor y is re-expressed through a reference letter both fonts anchor: y = Wanted reference anchor y + map(Pretendard anchor y) − map(Pretendard reference anchor y). The reference is `o` top for marks and lowercase bases and `O` top for capital bases; "map" is the H4 zone map at 400; x is unchanged. Results: `uni0309` (top, −596, 1005), `uni0311` (top, −620, 903).
- **Mark classes (R31).** An H4 mark is used only when Pretendard's class for it (top or bottom, from where Pretendard attaches it on `o`) agrees with the class its Unicode combining class gives. This drops `uni0305` and `uni0343`, which Pretendard anchors as bottom marks.
- **`ae`.** Wanted's lookup 7 has no anchor for `ae`, which `ǣ ǽ` need. Its top anchor is derived: x is the ink center (942), and y is `o`'s anchor height (1032).
- **Bases Wanted Sans lacks (R10).** `Ǯ ǯ ẛ` decompose to `Ʒ ʒ ſ`, which Wanted Sans does not have. They use the H4 glyphs. Their anchors come from Pretendard's base anchors through the rule above: `ʒ` top (612, 1032), `Ʒ` top (664, 1448).
- **`ẛ` (R31 amendment).** `ſ` has no Pretendard anchor. The dot (Wanted's `uni0307`) keeps Pretendard's own gap above the long s. At each H4 master, the dot's ink bottom = the Roof `ſ` ink top + Pretendard's dot gap at w′. Its ink center x = Pretendard's dot center x at w′. Placing the dot on the harmonized Pretendard dot instead made it touch the `ſ` at 1000, because harmonization lowers the dot by about δy. Clearance (dot bottom − `ſ` top) at 400 / 550 / 700 / 850 / 1000: 113 / 95.5 / 78 / 60.7 / 43.
- **Two marks on the same side (design decision 13, R25).** The plan left the stacking method open. The upper mark's ink bottom sits G(t) above the lower mark's ink top, where G(t) is the clearance between `e`'s top and the circumflex's ink bottom in Wanted's `ê` (G = 166 at 400). The upper mark's ink center x equals the lower mark's ink center x, so the stack is centered. A mark above plus a mark below follows Wanted's `ệ`. Example: `ầ` = `a` + circumflex at (634, 0) + grave at (739, 470).
- **Horn derivation.** The plan expected to find `uni031B` as a translated contour inside Pretendard's `ơ ư Ơ Ư`. None of them contains one: Pretendard draws each letter's horn separately. The build measures the horn's offset (rx = horn xMin − base xMax, ry = horn yMin, at Pretendard 400) on the one contour each horn letter has beyond its base. That gives o (−214, 816), u (−52, 808), O (−260, 1152), U (−92, 1108). At each t the horn's ink xMin = Wanted base xMax(t) + rx and its ink yMin = the zone-mapped ry. The horn itself is Pretendard's combining horn `uni031B`, harmonized per H4. The horn's mark anchor is its own ink (xMin, yMin) at 400. Tone marks on horn letters attach to the base's top anchor.
- **Horn-letter advance (R30 as amended).** With the base advance, the horn ran into the next letter (`ư` by 96 / 150 / 199 at 400 / 700 / 1000). The 24 horn letters take advance(t) = max(Wanted base advance(t), Roof horn ink xMax(t) + Pretendard's horn right side bearing at w′(t)). That bearing = Pretendard letter advance − Pretendard letter ink xMax. Widening over the base at t = 0 / 0.5 / `W_MID` / 1: `ơ` +0 / +32 / +42 / +94, `ư` +40 / +110 / +121 / +176, `Ơ` +0 / +4 / +14 / +61, `Ư` +129 / +175 / +182 / +216. Every other H2 letter keeps its base's advance.

### Mark anchors (final wave A)

The design first assumed that Wanted Sans's GPOS anchors are static. They are not: Wanted's letter base anchors (lookups 4 and 6–9) are AnchorFormat3 with variation devices on the (0, 1, 1) region, and Pretendard's mark and base anchors are AnchorFormat3 on (−1, −1, 0) and (0, 1, 1). Wanted's mark anchors are static (AnchorFormat1). With static anchors, the hook above on `ả ẻ ỏ ủ …` sat +70 units right of the base center at 400 and −69 left of it at 1000, and Wanted marks on bases without a Wanted composite drifted by up to 128 units (`ẋ ẍ`) at 1000 (final review I1).

- **H2 offsets (R35).** At each `COMPOSITE_LOCS` location, a mark's offset is base anchor(t) − mark anchor(t). Wanted anchors take their device deltas at t. Pretendard anchors take theirs at w′(t), extrapolated past 930 the way `PretendardSampler` extrapolates outlines. R25's y conversion uses each H4 master's zone map and is interpolated over `H4_LOCS`. No correction comes from Wanted composites any more; a unit test checks that the 252 Wanted composites the rule can reproduce match within 2 units (worst: `ę` 1.67 at `W_MID`).
- **Results.** Every I1 letter now matches Wanted's own GPOS placement at 400, 700, and 1000 (difference 0). The hook letters sit +68/+65/+59 from the base center at 400/700/1000, as in Pretendard. Seven H4-mark letters (`ả ȃ ȓ Ȓ Ȇ Ẻ ử`) differ from Pretendard's precomposed letters by up to 17.5 units, because R25 keeps Wanted's base anchors on Wanted letters and those sit differently relative to the ink.
- **Marks on H4 bases (R36).** The `mark` feature gets four lookups after Wanted's: H4 marks on Wanted letters (top, bottom), the horn, and one two-class lookup with 40 marks (Wanted's marks plus the 12 served H4 marks) on all 846 H4 letters. Before this, `а́` put the acute 678 units right of the letter's center; now Russian stress marks, Greek, and IPA marks attach. Pretendard has anchors for 501 top and 374 bottom positions; the other 344 top and 471 bottom anchors are derived from the ink (ink-center x; the `o`/`O` reference anchor y, moved out so taller or deeper letters keep `o`'s clearance). Only Pretendard's two-class top/bottom lookups supply base anchors.
- All new anchors vary with weight through new GDEF ItemVariationStore rows at `COMPOSITE_LOCS`. `buildMarkBasePosSubtable` replaces the deprecated `buildMarkBasePos`.
- **Not attached (known limitations):** the ogonek on H4 letters (Wanted's ogonek lookup anchors at the right edge, which does not fit the H4 bottom anchor), and marks on decomposed `ae`/`AE` (Wanted has no `ae` anchor). HarfBuzz composes the common sequences to precomposed glyphs, so only already-decomposed text is affected.
- **Tests.** `test_decomposed_marks` compares every H2 letter's mark offset at 400/700/1000 with Wanted's own GPOS (Wanted marks) or Pretendard's precomposed letter (H4 marks). Review Focus 5 covers the hook letters and the I1 letters. A new acceptance test, `test_a09_side_bearings.py`, compares the ink side bearings of every rebuilt glyph with its Pretendard source at 400 and 1000 and flags anything more than 40 units worse, with an allow-list (see section 11).

### OpenType features

Wanted's GSUB lookups 0–81 and its GPOS lookups 0–14 keep their indices and contents (`src/roofsans/features/`). The Pretendard data is appended:

- **GSUB lookups 82–98:** 82 `locl` KOR (Pretendard 34, 537 hanja), 83 `fwid` (71), 84 `pwid` (72), 85–88 `jp78 jp83 jp90 nlck` (73–76), 89–97 the kana weight alternates (77–85), and 98 `locl` JAN (13 code points). New features: `fwid jp78 jp83 jp90 locl(KOR) locl(JAN) nlck pwid ss20`. `ss20` carries the same 537 Korean forms that Pretendard calls `ss05`, because Wanted Sans uses `ss05` for a Latin alternate.
- **Feature order (R38).** The OpenType spec requires the FeatureList to be sorted by tag, and OTS warned about the appended features. After the features are added, `sort_features` sorts the GSUB FeatureList by tag and remaps every feature index in the language systems and in FeatureVariations. Records with the same tag keep their order, so Wanted's 11 `locl` records come before `locl` KOR and `locl` JAN. Wanted's feature indices therefore change (for example, `rlig` moves from 46 to 54), but each language system turns on the same features, so shaping is unchanged (`test_wanted_behavior_unchanged`). GPOS needs no sort: its four records (`kern kern mark mark`) are already in order, and the build adds lookups to them but no features.
- **`ss20` UI name (R39).** `ss20` has stylistic-set `FeatureParams` like Wanted's `ss01`–`ss16`. Its name is Pretendard's own `ss05` name, "Korean localization", written on Windows only, like Wanted's feature names. It takes the next free name ID, 308.
- Carried entries: KOR 537, `fwid` 103 of 154, `pwid` 103 of 154, `jp78` 586, `jp83` 386, `jp90` 160, `nlck` 214 of 215, kana 42, JAN 13. Entries are re-mapped by code point through the Roof cmap, so an entry drops when either end has no code point or no Roof glyph. In `fwid` and `pwid`, 51 entries each drop this way; their targets are Pretendard's unencoded `.full` glyphs. `nlck` drops `uni5349.001`, which is not copied.
- **Scripts and languages.** `hani` and `kana` are added; their default LangSys is the `DFLT` default list plus `ss20 jp78 jp83 jp90 nlck fwid pwid`. Those seven features are also added to the default LangSys of `DFLT`, `latn`, and `hang`, but not to Wanted's Latin language systems (AZE, TRK, …). `KOR` is added under `hani`.
- **`locl` JAN under `DFLT` and `latn` as well as `hani` and `kana` (design decision 12).** Script itemization gives brackets next to Latin text or digits the Latin or Common script. In `ID「abc」` a `hani`/`kana`-only lookup would leave narrow Korean brackets inside Japanese UI. `test_jan_brackets_after_latin` pins this. There is no `hang`/JAN language system.
- **`〈〉` under JAN (R13).** Pretendard JP's own glyphs for U+3008/3009 are 698 units wide; its only alternates (`.hang`) are also 698. The design's intent is Pretendard JP's Japanese forms, so `locl` JAN maps all 13 shared code points to their `.pj` copies, and the two angle brackets stay 698 wide. The other 11 are 1920.
- **Kana weight alternates (`rlig` FeatureVariations).** Pretendard's thresholds are converted from Pretendard's normalized axis to the Roof axis (wght = 400 + 530·s, or 400 + 355·s below 0), clamped to [0, 1], and rounded to F2Dot14. The result is merged with Wanted's own record (`rlig` → lookups 35 and 74 at t ≥ 0.41668701171875) into one record per distinct threshold, in descending order. Pretendard's three negative thresholds all clamp to 0, so only the first is kept.

  | t ≥ | lookups |
  | --- | --- |
  | 0.61163330078125 | 35, 74, 89–97 |
  | 0.6099853515625 | 35, 74, 89–96 |
  | 0.41668701171875 | 35, 74, 89–95 |
  | 0.38836669921875 | 89–95 |
  | 0.38665771484375 | 89–94 |
  | 0.1666259765625 | 89–93 |
  | 0.16497802734375 | 89–92 |
  | 0.0 | 89–91 |

- **GPOS lookups 15–18.** 15 is a kern lookup with the 9 Pretendard pairs whose two glyphs are both copied (all between `.pj` quotes and `〈〉`, none weight-dependent). 16–18 are mark-to-base lookups for H4 marks: top (`uni0309 uni0311 uni0340 uni0341 uni0342 uni0344 uni20F0`) and bottom (`uni0319 uni031E uni032A uni0332 uni0347`) on lookup 7's 530 bases, and horn (`uni031B`) on `o u O U`. They are appended to Wanted's existing `kern` and `mark` features, so they apply in every language system.
- **13 of 164 H4 combining marks have mark-to-base positioning.** The other 151 have no usable Pretendard anchor or no top/bottom class. The build prints them to stderr. Precomposed H2 glyphs cover normal text.
- **Variable anchors.** Wanted's anchors vary with weight through device tables. The new base anchors take masters at `COMPOSITE_LOCS`, so decomposed input lands where the precomposed H2 glyph puts the mark (for example, `ơ`'s horn base anchor moves +164 in x at 1000). 46 rows are appended to Wanted's GDEF variation store, with three new regions. `test_decomposed_marks` compares decomposed shaping with the precomposed glyph within ±2 units, not with the base anchor x, because Pretendard's hook ink center sits 68 units right of its anchor by design (R26).
- **GDEF.** Class 3 (mark) for the 164 H4 combining marks; class 1 (base) for every other new glyph.
- **Script order.** OTS requires sorted script tags, so the ScriptList is DFLT, hang, hani, kana, latn. Nothing refers to scripts by index.

### Names, metrics, and licensing

- Name IDs below 256 are exactly 0–6, 13, 14, and 25 (R33). IDs 7 (trademark), 10 (description), and every localized record are dropped. Wanted's platform layout is kept: 0–6, 13, and 14 on Mac (1, 0, 0) and Windows (3, 1, 0x409); 25 and IDs 256 and up on Windows only.
- Records 256 and up (the axis, instance, and feature names) replace `WantedSansVariable` with `RoofSans` and `Wanted Sans` with `Roof Sans`. Instance PostScript names are `RoofSans-<Style>`.
- Name ID 0 is Wanted Sans's own name ID 0 ("Copyright © 2024 Wanted Lab, Inc."), followed by every upstream `Copyright` line, joined with spaces, without the Reserved Font Name clauses and their commas.
- `OFL.txt` starts with Wanted Sans's name ID 0 notice when Wanted's `OFL.txt` header does not already contain it (it does not). Then come the header of Wanted's `OFL.txt` and the header of Pretendard's `LICENSE`, both verbatim (every copyright line, every Reserved Font Name line, and Adobe's sentence "Source is a trademark of Adobe…"), then Wanted's OFL 1.1 text. The file is written as UTF-8 with `\n` line ends.
- The plan kept Pretendard's Inter line ("Copyright (c) 2016 The Inter Project Authors") in both places: Pretendard's Latin, Greek, and Cyrillic come from Inter, and H4 copies those drawings.
- `head.fontRevision` 1.000; `created` and `modified` are fixed at 2026-10-31T00:00:00Z so the build is deterministic. `OS/2.achVendID` is `ROOF`. Unicode ranges are recalculated (bits 7, 9, 24, 30, 39, 40, 49, 50, 55, 59, 61, 64, 67, 68, and 116 are added); code page bit 17 (Japanese) is added. `OS/2.xAvgCharWidth` is recalculated from every nonzero advance (R39): 1770, where Wanted's value is 1714.
- Metrics are Wanted's, unchanged: `hhea` 1950 / −494 / 0, `OS/2` typo 1752 / −296 / 0 with `USE_TYPO_METRICS` off, win 1950 / 494, x-height 1032, cap height 1448.
- The build writes `OFL.txt` next to the font. A default-path build also copies it to the repository root.

## 7. Tolerances used by the tests

| Check | Tolerance | Why |
| --- | --- | --- |
| Wanted Sans glyphs (`test_a01`) | exact, at 400 / 750 / 1000, plus equal variable `glyf` and `gvar` entries | the design forbids any change to them |
| Pretendard copies and variation-sequence targets (`test_a02`, `test_a04`) | 0 at 400 and 930; 1 unit at 700 | exact at Pretendard's masters; 700 is between masters, where instance rounding differs by up to 1 |
| Copies at 1000 | equal to 930 | the plateau |
| Fullwidth outlines (`test_a03`) | 0.001 per point | unrounded instances carry float noise of about 1e-5 |
| Fullwidth side gaps; fullwidth sign ink center (`test_a03`) | 1 unit | each offset is rounded to the nearest unit (≤ 0.5 per side, measured 0.996 for the two gaps together) |
| H4 zone heights (`test_a05_h4`) | ±2 units | design Acceptance 5 |
| H4 `l` stem; stroke median; each stroke | ±3%; ±3%; ±10% | design Acceptance 5 |
| H4 `н п` stem ratio | ±3% of Pretendard's own ratio | R19 |
| H5 axes (`test_a05_h5`) | 725 ±5, 540 ±5; off-axis offsets ±5 | design Acceptance 5 |
| H5 scaled stroke (unit) | 1% | three solver iterations; ARROW at 850 lands 0.47% low |
| Enclosed ring (`test_a05_h3_enclosed`) | exact | the ring is `①`'s own deltas |
| Enclosed pair reach | ≤ limit + 2 units | the limit is measured on rounded instances |
| Ink inside disc figures | ≤ 1 unit², rasterized at 4 px per unit | catches the knockout slivers of R27 |
| Sup/sub sign-to-figure ratio (unit) | 2% | R18 |
| Mark positions: decomposed vs. precomposed (`test_a07`) | ±2 units | R26 |
| Mark alignment between masters (Review Focus 5) | 1 unit | composite offsets reconstruct within 0.5 |
| `tuples_from_masters` round trip (unit) | 1 unit (0.5 for the brief's `A` case) | delta rounding plus IUP tolerance |
| Composite offsets (unit) | 0.5 | R20 |
| Sampler vs. fontTools instancer (unit) | 1 unit | rounding of the instancer output |
| H4 δy solve (unit) | F ≤ 1 at each master | R17 |
| Outline sanity (`test_a06`) | see section 8 | |
| Flutter line metrics (`verify/flutter_specimen`) | 0.01 logical px | design Acceptance 10 |

## 8. Outline sanity (Acceptance 6)

`check_outline` (`src/roofsans/sanity.py`) compares a glyph with a reference outline:

- the contour count must match;
- each contour keeps the sign of its area;
- an inner contour (a counter) must keep an area above 1 unit²;
- a new self-intersection is reported.

Messages for an inner contour contain the word `collapsed` (for example `contour 1 collapsed: orientation reversed` or `contour 1 collapsed: self-intersects`); outer contours use messages without it (R7). An emboldened counter can fold over itself and keep its area sign (Pretendard `o` with a y strength of 900), so a new self-intersection on an inner contour also counts as collapsed.

For harmonized glyphs (`H4_LETTER`, `H5_SYMBOL`, `H3_SUPSUB`), `test_a06_outline_sanity.py` runs at 400, 550, 700, 750, 850, 930, and 1000. Thickening by δy makes the edge below a sharp notch rise past the edge above it at 700–1000, and makes a thickened stroke touch a neighboring stroke of the same contour. These crossings are same-sign overlaps: the filled shape equals the union of the strokes, with no hole and no twist. The rule (R24 and its clarification, in `tests/acceptance/sectors.py`):

- A new crossing fails when the crossing contour's own winding forms a twist (an opposite pair of sectors at 0, as in (0, −1, 0, 1)), or when the total winding around it has opposite signs (ink in a hole, or a hole in ink).
- A same-sign overlap passes, and the source's overlap flag stays set.
- One twist passes and is listed separately: a counter whose reversed area is above 0 and at most 1 unit² (`FOLD_ALLOWANCE`) while the counter keeps a positive area.
- "New" is judged against the source sampled at the weight the build used (w′ for H4, the sample weight for H5, Wanted at the same weight for sup/sub), and also against the source at 400. A crossing the source already has (for example Pretendard `ɕ` U+0255 at 900–954) is excused. Source crossings are matched one to one by flattened edge indices (within 32 edges, one flattened quadratic segment), because H4 moves a source crossing by 5–60 units. Matching falls back to location within 4 units when the point counts differ.

Results on the built font:

| wght | source crossings matched | new same-sign overlaps (glyphs) | counter folds allowed | failures |
| --- | --- | --- | --- | --- |
| 400 | 358 | 0 (0) | 0 | 0 |
| 550 | 358 | 85 (52) | 0 | 0 |
| 700 | 361 | 108 (59) | 0 | 0 |
| 750 | 361 | 110 (60) | 0 | 0 |
| 850 | 363 | 124 (65) | 0 | 0 |
| 930 | 362 | 133 (67) | 0 | 0 |
| 1000 | 357 | 165 (90) | 1: `д` U+0434, reversed area 0.22 unit² | 0 |

Every new same-sign overlap is in an H4 letter (Greek, Cyrillic, IPA and Latin Extended, combining marks; for example `ѕ ʤ Ω ᷔ ɕ`). No H5 symbol or sup/sub sign has one. The enclosed numbers and their helpers have no crossing.

## 9. Verification

- `uv run pytest` runs every unit and acceptance test. On 2026-10-31: 194 passed in 3 minutes 44 seconds, most of it spent instancing the 22,923-glyph font.
- `test_a08_ots_roundtrip.py` runs `ots-sanitize` (exit code 0) and checks that fontTools round-trips the binary and the XML.
- The fresh-copy check replaces the plan's `git clone`, because the repository had no commits yet (R8). The non-ignored working tree is copied into an empty directory (`git ls-files --others --cached --exclude-standard -z | rsync --from0 --files-from=- …`). Then `uv sync`, `uv run roofsans-fetch` (network download), and `uv run roofsans-build` run there. On 2026-10-31 the copy downloaded the four inputs in 2 seconds and built the font in 14 seconds. Its SHA-256 (`9927013a…8defe`) equaled that of `fonts/RoofSansVariable.ttf` in the repository, and `uv run pytest` in the copy passed (194 tests).
- **Language support** (stated on the specimen page, `site/`). Hyperglot 0.8.2 (`--validity preliminary`, base characters, living and constructed languages, primary orthographies) finds 483 Latin-script, 77 Cyrillic-script, and 2 Greek-script languages, plus Korean. Hyperglot has no data for Japanese, so CJK coverage is measured against national character sets decoded with Python's codecs: Hangul syllables 11,172 of 11,172; KS X 1001 hanja 4,888 of 4,888; JIS X 0208 level 1 and 2 kanji 2,965 and 3,390, all present; before the Simplified Chinese extension, GB 2312 level 1 hanzi 2,420 of 3,755 (64%) and Big5 frequent hanzi 4,611 of 5,401 (85%), so Chinese was listed as not supported. With it, GB 2312 levels 1 and 2 are 3,755 of 3,755 and 3,008 of 3,008, Big5 frequent hanzi 5,034 of 5,401, and the page lists Simplified Chinese (GB 2312) as supported; Traditional Chinese is not. The missing kana `ゕ ゖ`, JIS logic and set symbols, box drawing, and parenthesized numbers such as `⑴` are absent from both inputs too; no non-PUA input code point is missing from Roof Sans. `site/build_site.py` re-measures these numbers on every page build.
- The visual review (Acceptance 9) uses the specimen sheet from `verify/specimen.py` and `verify/specimen_lines.json`. Besides the design's seven lines, it has two lines for the decisions above (R32): stacked capitals, horn letters, Greek and Cyrillic accents (line 8); notch and aperture glyphs, two-digit enclosed numbers, off-axis symbols, fractions, and unit squares (line 9).
- The Flutter check (Acceptance 10) is the app in `verify/flutter_specimen/` (Flutter 3.44.9 through FVM). It draws w300–w900 through `fontWeight` and through the `wght` axis, and it compares line metrics with PretendardJP.
- **Acceptance 10 on an Android emulator is outstanding.** The AVD `Medium_Phone_API_36.1` does not boot: its system image folder lacks `system.img` and `vendor.img` ("No initial system image"), and the disk is 99% full (8 GB free). Reinstalling the image is the owner's call.
- **Flutter web proxy (CanvasKit).** As substitute evidence, the specimen app ran on Flutter web (Flutter 3.44.9, font `9927013a…8defe`). CanvasKit uses the same FreeType-based Skia and SkParagraph as Android, but this is not the Android check. Results:
  - The `fontWeight` lines match the `wght` lines at w300–w900, so the weights are real (w300 renders as 400).
  - No glyph is hollow, including the lines where SkParagraph applies fake bold (bold-text setting on, the wght 500 line).
  - Line heights equal PretendardJP's at 12, 16, and 24 px. The ascent differs by 1 font unit (Roof `hhea` 1950; the static PretendardJP's typo ascender 1949 with `USE_TYPO_METRICS`), which is 0.012 px at 24 px.
  - `locl` JAN applies through `TextStyle(locale:)` (the `ja` line is 71 px wider) but not through `Text.locale` or `Localizations` on Flutter web (that line is unchanged). On native Android, Flutter's `ParagraphBuilder` passes the paragraph locale down to text styles; that path is unverified without an emulator. README recommends `TextStyle(locale:)`.

## 10. Known warnings

- The build prints "features: 151 H4 marks have no anchor and no mark-to-base: …" to stderr (see section 6, OpenType features).

## 11. Open for review

These need the owner's visual judgment in the specimen sheet or on a device. All tests pass for each of them.

- **Simplified Chinese assumes the app's Chinese strings are Simplified.** Traditional strings would use different code points, many of them still missing. Chinese forms need `TextStyle(locale: Locale('zh', 'CN'))` (or plain `zh`) in the app; untagged Chinese text shows every hanzi in Roof Sans but with Japanese forms for 2,212 of them (section 12).
- **The font grew to 16.2 MB** with the Chinese extension (from 11.8 MB). Splitting the Chinese part into its own file later is possible from the same rules (`--without-chinese` is the first half); see the Chinese design's "Splitting later".
- **Acceptance 10 on Android is not done.** Only the Flutter web proxy ran (section 9). The Android emulator check, including whether the app locale reaches `locl` JAN there, waits for the owner to reinstall the AVD system image.
- **`⅟` U+215F overhangs the next glyph (R37).** Its advance is 734 / 908 at 400 / 1000 while its ink reaches 1160 / 1354 (right side bearing −426 / −446). This is kept on purpose: the slash ends where `½` puts its `.dnom`, so `⅟` followed by a denominator sets like `½`. Pretendard JP's own `⅟` overhangs too (−322 at 400, −362 at 930). Judge `⅟x` in specimen line 7. If the overlap is too much, cap it at Pretendard's ratio rather than removing it.
- **`ǫ ǭ` ogonek overhangs the next glyph.** The right side bearing is −44 / −288 at 400 / 1000, against Pretendard's +88 / +58. The placement equals Wanted's own GPOS for `o` + U+0328 (lookup 9), so it follows the rule, but Wanted's `ą ę ų` right-align the ogonek with the letter instead. A fix would align the ogonek's ink right edge with the base's, as in `ą`.

- **Two marks on one side, and tall stacked capitals.** Wanted Sans has no precedent for two marks above one letter. Some stacked capitals rise above the `hhea` ascender 1950: `Ắ` reaches 2382 (Pretendard 1992), and `Ǖ` reaches 2188 (Pretendard 2172). Wanted Sans has no `.case` marks for capitals except the ogonek.
- **Scaled-only figures in `⑩`–`⑳` and `⓫`–`⓴`.** The figure pairs are scaled to 0.63–0.83 with no stroke restoration, so their strokes are lighter than `①`'s and `❶`'s by the same factor.
- **Narrowed apertures and filled notches at 1000.** H4's δy thickening narrows apertures in `ѕ ʂ ʤ` and fills sharp notches in `В З Ω` (and `δ`). The outlines are same-sign overlaps (section 8).
- **`〈〉` stay 698 wide under `ja`.** The other 11 shared CJK code points become 1920 wide. The alternative is to map them to a fullwidth form; Pretendard JP has none.
- **`⋯` sits at cap-height middle,** as Pretendard draws it, not on the math axis.
- **Arrows are 5.2% light at 1000** (the 1100 clamp in H5).
- **`ẛ` dot x.** The dot uses Pretendard's absolute dot x, but Pretendard draws `ẛ`'s body 73 units right of its `ſ`, so relative to the body the Roof dot sits 52–71 units further right than in Pretendard's `ẛ`. A fix would measure the dot x relative to the body.
- **Seven H4-mark letters follow Wanted's base anchors** (`ả ȃ ȓ Ȓ Ȇ Ẻ ử`) and differ from Pretendard's precomposed letters by up to 17.5 units (section 6, Mark anchors).
- **Side-bearing allow-list (`test_a09_side_bearings.py`).** Besides `⅟` and the ogonek letters: `Ȅ ȅ ȍ Ȉ ȉ ȑ Ḭ ḭ Ḯ ḯ` overhang more than Pretendard's because Wanted's double grave, tilde below, and diaeresis-acute are wider than `I i r` (they match Wanted's own GPOS placement); fullwidth `Ｗ` and `％` overhang their 1920 cell at 1000 (`Ｗ` −144, `％` −85) because Wanted's `W` and `%` are centered without scaling (rule 3).
- **Capital ogonek without `.case`.** `Ǫ Ǭ` use `uni0328`, the glyph the cmap gives U+0328, not Wanted's `uni0328.case`.

Also noted during the build:

- The horn on `ơ ư Ơ Ư` is Pretendard's combining horn, harmonized per H4. It grows from 452 to 716 units tall between 400 and 1000, as Pretendard's `uni031B` does.
- At 1000, H4's lowercase zone map has a slope of 1.115 above the x-height and 0.885 below it, so horizontal strokes of marks and in the ascender band come out about 26% heavier relative to the letter body.
- Decomposed `i` or `j` followed by an H4 top mark (for example `i` + U+0311) keeps the dot. Wanted's `ccmp` lookup 31 swaps in `dotlessi` only before Wanted's own 14 top marks. Fixing it would change a Wanted lookup. HarfBuzz composes these sequences to the precomposed H2 glyph anyway, because the font maps it.
- 22 Greek and Cyrillic non-letters (spacing accents, `;`, `·`) are harmonized with the lowercase zone map, and `〈 〉` U+2329/232A follow H5 (section 6, Selection).

## 12. Simplified Chinese (rules C1–C3)

The design is `docs/ROOF_SANS_SIMPLIFIED_CHINESE_DESIGN.md`; the plan is `docs/ROOF_SANS_SIMPLIFIED_CHINESE_PLAN.md`. Built on 2026-11-01.

### Code

- `src/roofsans/chinese.py` decodes GB 2312 (levels 1 and 2) with Python's `gb2312` codec; `site/build_site.py` uses the same decoder.
- `selection.py` assigns `C1_HANZI` to the GB 2312 hanzi neither Wanted Sans nor Pretendard JP maps. `Rule.C2_FORM` and `Rule.C3_PUNCT` label the unencoded alternates; no code point gets them.
- `sampling.ShsSampler` reads Source Han Sans with its `avar` (weights 250–900, no extrapolation). The CN and JP subsets have identical `fvar` and `avar`, so a weight calibrated on JP means the same on CN.
- `rules/c_hanzi.py` calibrates and builds C1 and C2; `rules/c_punct.py` builds C3. `build.py` runs them after `h3_enclosed`.
- `features/gsub.py` appends lookups for ZHS (section "OpenType" below).
- `roofsans-build --without-chinese` skips C1–C3, the ZHS lookups, the Source Han Sans license lines, and code page 936. It reproduces the pre-extension font byte for byte (`6a01839d…272325`). The acceptance fixture `baseline_path` builds it (or reads `$ROOF_BASELINE`) as the "before" font for A11 and A14, and `test_a16_baseline.py` pins its SHA-256. Update that value only when a change to the non-Chinese rules is intended, and record it here.

### Counts

| Item | Count |
| --- | --- |
| GB 2312 hanzi | 6,763 (level 1: 3,755; level 2: 3,008) |
| Present before the extension | 3,503 (Pretendard JP's Japanese forms) |
| C1, added | 3,260 (level 1: 1,335; level 2: 1,925) |
| C2, `.zhs` alternates | 2,212: 2,210 whose CN outline differs from JP, plus `唾 毁` (not in the JP subset) |
| Calibration set (CN and JP outlines identical) | 1,291 |
| C3, `.zhs` punctuation | 9 (`！：；？‘’“”·`) |
| Non-GB 2312 code points switched through shared glyphs | 199 (U+2Exx 6, U+2Fxx 81, U+F9xx 79, U+FAxx 33) |

The font has 24,978 code points and 28,404 glyphs (22,923 + 3,260 + 2,212 + 9). Both format 4 cmap subtables compile to 51,206 bytes (5,045 segments), 14,329 bytes under the 65,535-byte limit; a test asserts the limit. GSUB has 103 lookups.

### Calibration

One set of values for every glyph, solved at build time and cached on the context:

| Value | Result | How |
| --- | --- | --- |
| scale | 1.92 | fixed: Source Han Sans's 1000-unit advance becomes 1920 |
| `w400` | 381.5 | Source Han Sans weight in [350, 420] where the median ink-area ratio (Pretendard 400 / scaled Source Han Sans) is 1; bisected, rounded to 0.25 |
| `w930` | 900 | the same at Pretendard 930 in [850, 900]; the answer is the upper bound, because Pretendard's 930 kanji are about 0.6% heavier than Source Han Sans's maximum |
| dx400, dy400 | −0.020, +21.649 | median of Pretendard ink-box edge − 1.92 × Source Han Sans edge |
| dx930, dy930 | −0.160, +21.440 | the same at 930 |

- Ink boxes in the C rules are true curve bounds (a helper in `c_hanzi.py`), not `Outline.bounds()`, which includes off-curve points. With control boxes, `戊 戍` missed by 15.6 units at 930.
- The calibration raises an error if `w400` lands on either search bound or `w930` on its lower bound.
- New glyphs have two masters (400 and 930) and the copied Han regions `(0, PJ_PEAK, 1)` and `(PJ_PEAK, 1, 1)`: linear to 930, held to 1000.

Acceptance 13 on the 1,291 calibration hanzi, built from the JP subset with these values (edge = worst ink-box edge error per glyph, in units):

| wght | edge median / p99 / max | within the 99% limit | ink-area ratio median (min–max) | over the 99% limit |
| --- | --- | --- | --- | --- |
| 400 | 1.42 / 2.91 / 19.06 | 1,283 of 1,291 within 3 | 1.0002 (0.989–1.018) | `忤 忱 摹 漫 熙 相 荻 蔓` (`熙` 19.1, `摹` 9.3, `蔓` 7.7, `荻` 5.5, the rest ≤ 3.13) |
| 700 | 1.78 / 3.60 / 6.19 | 1,290 within 5 | 1.0042 (0.994–1.025) | `熙` 6.19 |
| 930 | 2.56 / 4.96 / 6.72 | 1,280 within 5 | 1.0056 (0.992–1.028) | `卩 叱 史 尾 想 椅 洗 熙 狂 玩 相` (≤ 6.72) |

The outliers at 400 come from small shape differences between Pretendard's Source Han Sans and version 2.005. At 700 the check uses the linear interpolation of the two transformed masters, which is what the font contains. Sampling Source Han Sans directly at an interpolated weight gives an ink-area median of 0.978, because its own interpolation is not linear; that is why the masters are interpolated linearly, like Pretendard's.

### Punctuation (C3)

- `！：；？` use the same Wanted Sans component as Roof's default fullwidth glyph (R3_SIGN). `‘’“”·` use Wanted Sans's `quoteleft quoteright quotedblleft quotedblright periodcentered`. Advance 1920; only x moves.
- Target ink center x = 1.92 × Source Han Sans CN's ink center at the calibrated weight + dx, linear between the 400 and 930 targets. Source centers at `w400`, in 1000 units: `！` 250, `：` 250, `；` 243.4, `？` 247.0, `‘` 879.3, `’` 120.7, `“` 793.9, `”` 206.1, `·` 500.

### OpenType

- GSUB lookups 99 (`zhs_hanzi`, 2,212 entries), 100 (`zhs_punct`, 17: the 13 JAN mappings and `！：；？`), and a chained-context quotes lookup with a referenced single substitution. Language system `ZHS ` under `hani` (all three) and under `latn` and `DFLT` (punctuation and quotes).
- The quotes lookup skips `’` and `·` between two "alnum" glyphs: every glyph the Roof cmap maps from a code point below U+3000 with Unicode category L* or Nd. `It’s`, `McDonald’s`, `l·l`, and `2’30` keep Wanted Sans's glyphs; `他说“OK”。`, `“abc”`, `列奥纳多·达·芬奇` switch.
- The quotes lookup applies in every ZHS script, not only `hani`: with `hani` only, `他说“OK”。` gave a 1920-wide `“` (Han run) and a 796-wide `”` (Latin run).
- HarfBuzz (uharfbuzz 0.57.0) selects ZHS for `zh`, `zh-CN`, `zh-Hans`, `zh-SG`, `zh-Hans-CN`, `zh-Hans-HK`, `cmn`, and `wuu`; not for `zh-TW`, `zh-HK`, `zh-Hant`, `zh-MO`, or `yue`.
- With `ss20` on under `zh-CN`, a hanzi in both sets (258, for example `乳`) takes the Korean form, because lookup 82 runs before 99. A test pins it.
- Every `.zhs` glyph and every C1 glyph is GDEF class 1.

### Licensing and OS/2

- `OFL.txt` adds Source Han Sans's `LICENSE.txt` header verbatim after Pretendard's. Name ID 0 adds `Copyright 2014-2025 Adobe (http://www.adobe.com/)`; Pretendard's `2014-2021 Adobe` line stays.
- OS/2 code page bit 18 (936) is set. Unicode ranges do not change. `xAvgCharWidth` goes from 1770 to 1799.

### Output and verification

- Output: 16,230,096 bytes, SHA-256 `da7a7fe8197d2b5209cac0a9b6a313e42a975762f2015ab26b5be3dc7e75b87d`, about 20 seconds to build. The pre-extension font was 11,798,960 bytes; the estimate was 15.9 MB.
- The specimen page is 7.7 MB (WOFF2 inside).
- Tests: `uv run pytest` passed 302 tests in 5 minutes 5 seconds on 2026-11-01. It built `build/test/` (`da7a7fe8…`, equal to the default-path build) and `build/test-baseline/` (`6a01839d…`).
- Reviews: a Codex builder check of the design; a Claude review of the implementation (no blocker; its findings are fixed or recorded above).
- Visual review (Acceptance 17): the specimen sheets at 400, 700, and 1000 show no jump in size, position, or weight between C1 hanzi and present hanzi under `zh-CN`.
- Flutter web (Acceptance 18, Flutter 3.44.9, CanvasKit): `TextStyle(locale: Locale('zh', 'CN'))` applies the C2 forms and the Chinese punctuation; untagged Chinese text draws every hanzi from Roof Sans with the Japanese forms; line metrics still match PretendardJP. Android is still outstanding (section 11).
