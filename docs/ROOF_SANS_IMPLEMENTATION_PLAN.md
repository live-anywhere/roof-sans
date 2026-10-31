# Roof Sans Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `fonts/RoofSansVariable.ttf`, a single `wght` 400–1000 variable font made of Wanted Sans plus harmonized Pretendard JP glyphs, from a reproducible Python build with an acceptance test suite.

**Architecture:** The build starts from the Wanted Sans variable binary and leaves its glyphs, variations, and features untouched. A selection step assigns every Pretendard-only code point to one rule. One module per rule returns `NewGlyph` records (outline or composite at `wght` 400, plus `gvar` tuples on the Roof axis). An assembly step inserts them and rebuilds `cmap`, then the features and finalize steps add OpenType data, names, and licensing. Harmonized glyphs are built as master outlines at 400/700/1000 and converted to tuples with `fontTools.varLib.models.VariationModel`. Copied Pretendard glyphs keep their own tuples, re-mapped to the new axis with a 930→1000 plateau.

**Tech Stack:** Python 3.12 managed by `uv`; fontTools 4.60.2; skia-python 144.1 (specimen rendering and point-in-path tests); uharfbuzz (shaping tests and specimen); opentype-sanitizer (`ots-sanitize`); pytest. Flutter 3.44.9 through FVM for the device check.

**Status (2026-10-31):** executed. During implementation, rulings changed several steps of this plan. They include `H4_LOCS` with a master at 850, the δy objective, the enclosed-number figures, anchors that vary with weight, marks on H4 bases, and sorted FeatureLists. `docs/ROOF_SANS_BUILD_NOTES.md` section 6 records each change with its reason. Where this plan and the build notes disagree, the build notes and the code are current.

**Spec:** `docs/ROOF_SANS_DESIGN.md`. Executors read both documents. Section names such as "H4" and "Acceptance 5" refer to it.

## Global Constraints

- Inputs: Wanted Sans `WantedSansVariable.ttf` 1.003 at upstream commit `02c9b822349c188ada95f9e2d90c2ed18f853235`, SHA-256 `9953a7cfc4a3cba4ef1242abaf89779b3cd15fd9729c2d67d9e9d37a0da967f5`; Pretendard JP `PretendardJPVariable.ttf` 1.309 at upstream commit `7aeb0698819be2b4097dae8ec8fe6a795e5cf3ae`, SHA-256 `bc1d77db0f3cb9c20986b8939aa8a28d5216552d777d082955da22f420535cbb`.
- Both inputs use 2048 UPM. Output UPM stays 2048.
- `wght` axis 400–1000, default 400. The axis maximum stays ≤ 1000 and the range ≤ 1000. Named instances are Wanted Sans's: Regular 400, Medium 500, SemiBold 600, Bold 700, ExtraBold 800, Black 900, ExtraBlack 1000.
- Metrics from Wanted Sans: `hhea` 1950/−494/0; `OS/2` typo 1752/−296/0 with `USE_TYPO_METRICS` off; win 1950/494; `sxHeight` 1032; `sCapHeight` 1448.
- Pretendard JP's 930 master sits at Roof normalized `530/600`, stored as F2Dot14 `14473/16384` (0.88336).
- Han, kana, and Japanese punctuation hold the 930 shape from 930 to 1000. All other Pretendard-derived glyphs keep matching Wanted Sans up to 1000.
- Overlap flags (`OVERLAP_SIMPLE`, `OVERLAP_COMPOUND`) stay as the sources set them.
- Family `Roof Sans`, file `RoofSansVariable.ttf`, version 1.000. No naming field contains "Pretendard", "Source", "Inter", or "M PLUS 1" (reserved font names in the upstream licenses).
- License: SIL OFL 1.1 with every upstream copyright line.
- Python dependencies are pinned with `==` in `pyproject.toml` and locked in `uv.lock`.
- No agent runs `git commit`, `git stash`, or `git reset`. Each task ends with a commit checkpoint for the owner.
- `refs/` is never committed and never modified. The build reads inputs from `inputs/` (git-ignored), filled by `roofsans-fetch`.
- Measure variable advances from phantom points or from `fontTools.varLib.instancer`, never from `TTGlyphSet[...].width` before drawing. That attribute returns the default `hmtx` advance until the glyph is drawn. Wanted Sans's `zero` advance is 1280/1373/1440 at 400/750/1000.

## Review Focus

1. **Decomposed (NFD) input.** Vietnamese typed on some keyboards, macOS file names, and kana with U+3099/U+309A arrive decomposed. HarfBuzz should compose them to the precomposed Roof glyph, so `ấ` typed as `a` + U+0302 + U+0301 renders as the single H2 glyph. Pinned in Task 9 (`test_nfd_latin_composes`) and Task 11 (`test_nfd_kana_composes`).
2. **Japanese brackets next to Latin or digits under `ja`.** In `ID「abc」` or `2026「新」`, script itemization gives the brackets the Latin or Common script, so a `kana`/`hani`-only `JAN` lookup would leave a narrow Korean pair inside Japanese UI. A Japanese UI user expects fullwidth brackets. Task 11 also registers the `JAN` lookup under `DFLT` and `latn` and pins it with `test_jan_brackets_after_latin`.
3. **Weights below 400.** The app's pubspec declares PretendardJP Thin (200) and Light (300) today. With Roof Sans, `FontWeight.w200`/`w300` clamp to 400 and render as Regular, with no fallback to another family. Task 14 adds a w300 row to the Flutter specimen, and Task 15 adds a migration note to the README.
4. **Variation selectors outside the 524 sequences.** Text such as a Han base + U+E0108, or a selector after a Latin letter, should render the base glyph with an invisible selector, not `.notdef`. Pinned in Task 5 (`test_unknown_variation_selector_falls_back`).
5. **Composite marks at in-between weights.** H2 composites combine Wanted Sans bases (masters 400/750/1000) with H4 marks (masters 400/700/1000). At 550 and 850 a mark must stay on its anchor, as Wanted Sans's own `ê` does. Pinned in Task 9 (`test_mark_alignment_between_masters`).

---

## File Structure

```
pyproject.toml, uv.lock, .python-version   Task 1   project, pinned deps, console scripts
.gitignore                                 Task 1   ignores refs/, inputs/, build/, .venv/
inputs.lock.json                           Task 1   pinned input URLs and SHA-256
src/roofsans/__init__.py                   Task 1
src/roofsans/inputs.py                     Task 1   fetch/verify inputs
src/roofsans/selection.py                  Task 2   code point → rule, naming rule
src/roofsans/axis.py                       Task 3   axis constants and normalization
src/roofsans/outline.py                    Task 3   Outline type, coordinate helpers
src/roofsans/sampling.py                   Task 3   Pretendard/Wanted outline at any wght
src/roofsans/variations.py                 Task 3   tuple remap, masters → tuples
src/roofsans/newglyph.py                   Task 3   NewGlyph, composite builder
src/roofsans/embolden.py                   Task 4   FT_Outline_EmboldenXY port
src/roofsans/measure.py                    Task 4   ray-cast strokes, zones
src/roofsans/sanity.py                     Task 4   outline sanity (Acceptance 6)
src/roofsans/context.py                    Task 5   BuildContext
src/roofsans/assemble.py                   Task 5   insert glyphs, cmap incl. format 14
src/roofsans/build.py                      Task 5   build() and roofsans-build CLI
src/roofsans/rules/h6_copy.py              Task 5   H6 copies and closure
src/roofsans/rules/{r3_fullwidth,h3_construct}.py   Task 6
src/roofsans/rules/h3_enclosed.py          Task 7   enclosed numbers, sup/sub signs
src/roofsans/harmonize.py                  Task 8   w′, δy, zone maps
src/roofsans/rules/h4_letters.py           Task 8
src/roofsans/rules/h2_compose.py           Task 9
src/roofsans/rules/h5_symbols.py           Task 10
src/roofsans/features/{__init__,gsub,gpos,gdef}.py  Task 11
src/roofsans/finalize.py                   Task 12  names, OS/2, head, license text
fonts/RoofSansVariable.ttf, OFL.txt        Task 12  build outputs, committed
verify/specimen.py, verify/specimen_lines.json      Task 13
verify/flutter_specimen/**                 Task 14
README.md, AGENTS.md, docs/ROOF_SANS_BUILD_NOTES.md Task 15
tests/conftest.py                          Task 1
tests/unit/test_<module>.py                owning task
tests/acceptance/test_aNN_*.py             owning task (see each task)
```

Tasks 5–12 each own whole files. Task 5 creates every rule module as a stub (`def contribute(ctx): return []`) and the stub `features/__init__.py` and `finalize.py`. A later task replaces its stub file entirely. Nothing else edits `build.py`.

## Dependencies and parallel groups

| Group | Tasks | Starts after | Notes |
| --- | --- | --- | --- |
| A | 1 | — | |
| B | 2, 3, 4, 14 | 1 | disjoint files |
| C | 5 | 2, 3 | |
| D | 6, 7, 8 | 5 (and 4 for 7, 8) | disjoint files |
| E | 9, 10 | 8 | disjoint files |
| F | 11 | 6, 9, 10 | |
| G | 12 | 11 | |
| H | 13, 15 | 12 | disjoint files |
| I | 16 | all | main session only |

Every task's implementer is a Codex worker. A fresh reviewer from the other provider checks each task before its dependents start. Task 16 is the main session's.

Test code in this plan calls small helpers such as `shape`, `max_abs_diff`, or `wanted_component_offsets`. Define each one in the test file that uses it, unless an Interfaces block names it.

Unit tests run with `uv run pytest -m "not acceptance"`. Acceptance tests need the built font and run with `uv run pytest -m acceptance`. They are expected to fail until Task 12 is done. Each task runs its own acceptance file against a fresh build to check its part.

---

### Task 1: Project scaffold and pinned inputs

**Files:**
- Create: `pyproject.toml`, `uv.lock`, `.python-version`, `.gitignore`, `inputs.lock.json`, `src/roofsans/__init__.py`, `src/roofsans/inputs.py`, `tests/conftest.py`
- Test: `tests/unit/test_inputs.py`

**Interfaces:**
- Produces:
  - `roofsans.inputs.Inputs` (frozen dataclass): `wanted: Path`, `pretendard: Path`, `wanted_ofl: Path`, `pretendard_license: Path`.
  - `ensure_inputs(cache_dir: Path = Path("inputs"), refs_root: Path | None = None) -> Inputs`. Copies from `refs_root/<repo>/<path>` when that file exists, otherwise downloads the pinned URL. Verifies SHA-256 and raises `InputChecksumError(name, expected, actual)` on mismatch. Never writes under `refs_root`.
  - Console scripts: `roofsans-fetch [--from-refs DIR]` → `roofsans.inputs:main`; `roofsans-build [--out PATH]` → `roofsans.build:main` (module created in Task 5).
  - `tests/conftest.py` fixtures (session scope): `inputs`, `wanted` and `pretendard` (`TTFont`); `ws`, `ps` (`WantedSampler`, `PretendardSampler` from Task 3) and `ctx` (`roofsans.context.make_context(inputs)` from Task 5), each imported inside its fixture; `roof_path` (env `ROOF_FONT` if set, else `roofsans.build.build(Path("build/test/RoofSansVariable.ttf"))`, imported inside the fixture), `roof` (`TTFont`), `static(font_key: str, wght: float) -> TTFont` (cached `instantiateVariableFont` result; keys `"wanted"`, `"pretendard"`, `"roof"`). Register the `acceptance` marker.

- [ ] **Step 1: Write `pyproject.toml` and lock.** `requires-python = "==3.12.*"`; dependencies `fonttools==4.60.2`, `skia-python==144.1`, `uharfbuzz`, `opentype-sanitizer`, `pytest`. Run `uv python pin 3.12` and `uv lock`, then replace each unpinned name with `==<version uv.lock resolved>`. Package layout `src/roofsans`.
- [ ] **Step 2: Write `.gitignore`** with `refs/`, `inputs/`, `build/`, `.venv/`, `__pycache__/`, `verify/flutter_specimen/assets/fonts/`, `verify/flutter_specimen/build/`, `verify/flutter_specimen/.dart_tool/`.
- [ ] **Step 3: Write `inputs.lock.json`** with four entries. Each has `name`, `repo` (`pretendard` or `wanted-sans`), `path`, `url` = `https://raw.githubusercontent.com/<owner>/<repo>/<full commit>/<path>`, and `sha256`. The two fonts use the values in Global Constraints; the license files are `wanted-sans/OFL.txt` and `pretendard/LICENSE` at the same commits. Compute their SHA-256 with `shasum -a 256` from `refs/`.
- [ ] **Step 4: Write the failing tests**

```python
def test_ensure_inputs_copies_from_refs(tmp_path):
    got = ensure_inputs(tmp_path / "in", refs_root=Path("refs"))
    assert sha256(got.wanted) == "9953a7cfc4a3cba4ef1242abaf89779b3cd15fd9729c2d67d9e9d37a0da967f5"
    assert sha256(got.pretendard) == "bc1d77db0f3cb9c20986b8939aa8a28d5216552d777d082955da22f420535cbb"

def test_checksum_mismatch_raises(tmp_path):
    fake = tmp_path / "refs" / "wanted-sans" / "packages/wanted-sans/fonts/variable"
    fake.mkdir(parents=True); (fake / "WantedSansVariable.ttf").write_bytes(b"x")
    with pytest.raises(InputChecksumError):
        ensure_inputs(tmp_path / "in", refs_root=tmp_path / "refs")

def test_lock_urls_pin_full_commits():
    for e in json.loads(Path("inputs.lock.json").read_text()):
        assert re.search(r"/[0-9a-f]{40}/", e["url"])
```

- [ ] **Step 5: Run** `uv run pytest tests/unit/test_inputs.py -v`. Expected: FAIL (`ensure_inputs` not defined).
- [ ] **Step 6: Implement `roofsans/inputs.py`** (urllib download into a temp file, then verify, then move).
- [ ] **Step 7: Run** the same command. Expected: PASS. Then run `uv run roofsans-fetch --from-refs refs` and check that `inputs/` holds four files.
- [ ] **Step 8: Commit checkpoint (owner):** `build: add project scaffold and pinned inputs`. Files: `pyproject.toml uv.lock .python-version .gitignore inputs.lock.json src/roofsans/__init__.py src/roofsans/inputs.py tests/conftest.py tests/unit/test_inputs.py`.

---

### Task 2: Glyph selection

**Files:**
- Create: `src/roofsans/selection.py`
- Test: `tests/unit/test_selection.py`

**Interfaces:**
- Consumes: `Inputs` (Task 1).
- Produces:
  - `class Rule(StrEnum)`: `WANTED`, `H6_COPY`, `R3_FULLWIDTH`, `R3_SIGN`, `H2_COMPOSE`, `H3_SEQUENCE`, `H3_FRACTION`, `H3_ENCLOSED`, `H3_SUPSUB`, `H4_LETTER`, `H5_SYMBOL`, `EXCLUDED_PUA`.
  - `class SymbolCategory(StrEnum)`: `ARROW`, `MATH`, `GEOMETRIC`, `CURRENCY`, `OTHER`.
  - `class Zone(StrEnum)`: `LOWER`, `CAPITAL`.
  - `@dataclass(frozen=True) class Selection`: `rules: Mapping[int, Rule]`, `symbol_category: Mapping[int, SymbolCategory]`, `zone: Mapping[int, Zone]` (H4 code points only), and `codepoints(rule: Rule) -> list[int]` (sorted).
  - `select(wanted: TTFont, pretendard: TTFont) -> Selection`.
  - `roof_glyph_name(cp: int, taken: set[str]) -> str`: `uniXXXX` (BMP) or `uXXXXX`, plus `.roof` if the name is in `taken`. Used for every glyph the build synthesizes or harmonizes.
  - `JAN_SHARED: tuple[int, ...]` = U+3000, U+3008–U+3011, U+3014, U+3015 (the 13 shared code points of H1).

Classification, applied in this order to each code point either font maps. The counts in Step 1 were measured with Python 3.9's Unicode 13.0 data. If Python 3.12's Unicode 15.0 data changes a count, report the differing code points before changing the test.

1. Wanted Sans maps it → `WANTED`.
2. U+E000–F8FF → `EXCLUDED_PUA`.
3. U+FF10–FF19, FF21–FF3A, FF41–FF5A → `R3_FULLWIDTH`. U+FF01–FF5E or U+FFE0–FFE6 whose Pretendard glyph is a composite with exactly one component, where Wanted Sans has a glyph of that component's name → `R3_SIGN` (23 code points: `！＂＃＄％＆＇＋，．：；＜＞？＠＾｀｜￠￡￥￦`; five of them use `.case` components such as `plus.case`).
4. In a rule-2 block (U+2E80–2FDF, 3000–30FF, 31F0–31FF, 3200–33FF, 3400–4DBF, 4E00–9FFF, F900–FAFF, FF00–FFEF, 20000–2FFFF): `H3_SEQUENCE` when Pretendard's glyph is a composite whose component closure contains a glyph Pretendard maps to a code point below U+0250 or to U+00B2/B3/B9, and the code point is outside U+FF00–FFEF. Otherwise `H6_COPY`. The remaining fullwidth punctuation (for example `（` drawn as an outline, `＼` and `～` whose components Wanted Sans lacks) stays `H6_COPY`.
5. Greek (U+0370–03FF, 1F00–1FFF) or Cyrillic (U+0400–052F, 1C80–1C8F, 2DE0–2DFF, A640–A69F) → `H4_LETTER`.
6. A Latin letter (name contains `LATIN`, category `L*`) with a canonical (untagged) decomposition → `H2_COMPOSE`.
7. Explicit H3 lists:
   - `H3_SEQUENCE`: digraphs U+01C4–01CC, 01F1–01F3; Roman numerals U+2160–217F; U+20A8 `₨`, U+2121 `℡`, U+213B `℻`, U+2116 `№`.
   - `H3_FRACTION`: `<fraction>` decompositions (`⅓ ⅚ ⅟`) plus U+2100, 2101, 2105, 2106 (`℀ ℁ ℅ ℆`, whose `<compat>` decompositions contain `/`). `⅍` U+214D has no decomposition and Wanted Sans has no `A.numr`/`S.dnom`, so it falls to step 9 (`OTHER`).
   - `H3_ENCLOSED`: U+2469–2473 (`⑩`–`⑳`), U+24EB–24F4 (`⓫`–`⓴`), U+277F (`❿`), U+2789 (`➉`).
   - `H3_SUPSUB`: U+207A–207E, U+208A–208E.
8. Category `Lu Ll Lt Lm Lo Mn Nl`, except U+318D (`ㆍ`) and U+A92E → `H4_LETTER`. Zone `CAPITAL` for `Lu Lt Nl`, else `LOWER`.
9. Anything else → `H5_SYMBOL`, with category:
   - `CURRENCY`: category `Sc`.
   - `ARROW`: U+2190–21FF, 27F0–27FF, 2900–297F, 1F800–1F8FF, or U+2B00–2BFF with `ARROW` in the name.
   - `GEOMETRIC`: U+25A0–25FF, or other U+2B00–2BFF.
   - `MATH`: category `Sm`, or U+2200–22FF, 2A00–2AFF, 27C0–27EF, 2980–29FF.
   - `OTHER`: the rest.

- [ ] **Step 1: Write the failing tests** with the counts measured on the pinned inputs.

```python
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
```

- [ ] **Step 2: Run** `uv run pytest tests/unit/test_selection.py -v`. Expected: FAIL (import error).
- [ ] **Step 3: Implement `selection.py`** following the ordered classification above.
- [ ] **Step 4: Run** the same command. Expected: PASS. If a count differs, print the differing code points. Fix the classifier when it disagrees with the order above; escalate when the order itself looks wrong.
- [ ] **Step 5: Commit checkpoint (owner):** `build: classify input code points by selection rule`. Files: `src/roofsans/selection.py tests/unit/test_selection.py`.

---

### Task 3: Variation core

**Files:**
- Create: `src/roofsans/axis.py`, `src/roofsans/outline.py`, `src/roofsans/sampling.py`, `src/roofsans/variations.py`, `src/roofsans/newglyph.py`
- Test: `tests/unit/test_sampling.py`, `tests/unit/test_variations.py`, `tests/unit/test_newglyph.py`

**Interfaces:**
- Produces:
  - `axis.py`: `ROOF_MIN = 400`, `ROOF_MAX = 1000`, `PJ_PEAK = 14473 / 16384`, `W_MID = 0.58331298828125` (Wanted Sans's 750 master), `H4_LOCS = (0.0, 0.5, 1.0)`, `COMPOSITE_LOCS = (0.0, 0.5, W_MID, 1.0)`, `roof_norm(wght: float) -> float`, `roof_wght(norm: float) -> float`.
  - `outline.py`: `@dataclass class Outline`: `coords: list[tuple[float, float]]` (outline points followed by the 4 phantom points), `end_pts: list[int]`, `flags: list[int]`. Also `advance(self) -> float`, `bounds(self) -> tuple[float, float, float, float]`, `contours(self) -> list[list[tuple[float, float]]]`, `transformed(self, fn: Callable[[float, float], tuple[float, float]]) -> Outline` (outline points only), `to_glyph(self) -> Glyph` (rounded with `otRound`).
  - `sampling.py`:
    - `PretendardSampler(font)` with `outline(name: str, wght: float) -> Outline` for 45 ≤ wght ≤ 1100. Composites are decomposed. Below 400 it interpolates toward the 45 master; above 400 it applies the (0, 1, 1) tuple with scalar `(wght − 400) / 530`, unclamped, so it extrapolates past 930. Also `advance(name, wght) -> float`.
    - `WantedSampler(font)` with `outline(name, wght)` (400–1000, decomposed, all regions) and `advance(name, wght)`.
    - Both expand IUP-omitted points (`fontTools.varLib.iup.iup_delta`) and use `fontTools.varLib.models.supportScalar`.
  - `variations.py`:
    - `remap_pretendard_tuples(tvs: list[TupleVariation]) -> list[TupleVariation]`. Drops tuples whose region is negative. Replaces each `(0, 1, 1)` tuple with two tuples carrying the same deltas: `(0, PJ_PEAK, 1)` and `(PJ_PEAK, 1, 1)`. That gives a linear ramp to 930 and a plateau to 1000.
    - `tuples_from_masters(masters: Mapping[float, Sequence[tuple[float, float]]], end_pts: list[int] | None) -> list[TupleVariation]`. The keys are Roof normalized locations and must include 0.0. Uses `VariationModel`, rounds deltas with `otRound`, drops all-zero tuples, and applies `iup_delta_optimize` with tolerance 0.5 when `end_pts` is given.
  - `newglyph.py`:
    - `@dataclass class NewGlyph`: `name: str`, `glyph: Glyph`, `advance: int`, `variations: list[TupleVariation]`, `unicodes: tuple[int, ...]`, `rule: Rule`, `source: str`.
    - `simple_glyph(name, masters: Mapping[float, Outline], unicodes, rule, source) -> NewGlyph`. The default glyph is `masters[0.0].to_glyph()` with the source's overlap flag kept.
    - `composite_glyph(name, parts: Mapping[float, list[Part]], advance: Mapping[float, float], unicodes, rule, source) -> NewGlyph`, with `Part = tuple[str, float, float]` (component name, dx, dy). All locations must list the same components in the same order. Offsets and the advance become tuple deltas on component points and phantom points.
    - `newglyph_outline(g: NewGlyph, norm: float, resolve: Callable[[str, float], Outline]) -> Outline`. `resolve` returns a component's outline at a location.

- [ ] **Step 1: Write the failing tests**

```python
def test_wanted_advance_varies(wanted):
    ws = WantedSampler(wanted)
    assert [round(ws.advance("zero", w)) for w in (400, 750, 1000)] == [1280, 1373, 1440]

def test_pretendard_extrapolates(pretendard):
    ps = PretendardSampler(pretendard)
    a, b, c = (ps.outline("l", w).coords[0] for w in (400, 930, 1000))
    assert c[0] - b[0] == pytest.approx((b[0] - a[0]) * 70 / 530, abs=0.01)

def test_remap_plateau(pretendard, static):
    name = pretendard.getBestCmap()[ord("漢")]
    tvs = remap_pretendard_tuples(pretendard["gvar"].variations[name])
    at = lambda t: interpolated_coords(pretendard["glyf"], name, tvs, t)   # test helper
    assert at(1.0) == at(PJ_PEAK)
    assert max_abs_diff(at(roof_norm(700)), static("pretendard", 700)["glyf"][name]) <= 1

def test_masters_roundtrip(wanted):
    ws = WantedSampler(wanted)
    m = {t: ws.outline("A", roof_wght(t)).coords for t in (0.0, W_MID, 1.0)}
    tvs = tuples_from_masters(m, ws.outline("A", 400).end_pts)
    for w in (400, 550, 750, 900, 1000):
        assert max_abs_diff(apply(m[0.0], tvs, roof_norm(w)), ws.outline("A", w).coords) <= 0.5

def test_composite_offsets_vary(wanted):
    ws = WantedSampler(wanted)
    adv = {t: ws.advance("zero", roof_wght(t)) for t in COMPOSITE_LOCS}
    g = composite_glyph("t", {t: [("zero", (1920 - adv[t]) / 2, 0)] for t in COMPOSITE_LOCS},
                        {t: 1920 for t in COMPOSITE_LOCS}, (), Rule.R3_FULLWIDTH, "test")
    o = newglyph_outline(g, 1.0, lambda n, t: ws.outline(n, roof_wght(t)))
    assert o.advance() == 1920 and o.bounds()[0] == pytest.approx(ws.outline("zero", 1000).bounds()[0] + 240, abs=0.5)
```

`interpolated_coords`, `apply`, and `max_abs_diff` are small test helpers in `tests/unit/helpers.py`, owned by this task.

- [ ] **Step 2: Run** `uv run pytest tests/unit/test_sampling.py tests/unit/test_variations.py tests/unit/test_newglyph.py -v`. Expected: FAIL (imports).
- [ ] **Step 3: Implement the five modules** with the signatures above.
- [ ] **Step 4: Run** the same command. Expected: PASS.
- [ ] **Step 5: Commit checkpoint (owner):** `build: add variation sampling and tuple builders`. Files: the five modules, `tests/unit/helpers.py`, and the three test files.

---

### Task 4: Outline geometry: embolden, measurement, sanity

**Files:**
- Create: `src/roofsans/embolden.py`, `src/roofsans/measure.py`, `src/roofsans/sanity.py`
- Test: `tests/unit/test_embolden.py`, `tests/unit/test_measure.py`, `tests/unit/test_sanity.py`

**Interfaces:**
- Consumes: `Outline`, `WantedSampler`, `PretendardSampler` (Task 3).
- Produces:
  - `embolden_xy(o: Outline, x_strength: float, y_strength: float) -> Outline`. A port of FreeType `FT_Outline_EmboldenXY` (`src/base/ftoutln.c`). It keeps point count and order and leaves phantom points unchanged. Each contour point moves along the vertex bisector by half the strength. Orientation comes from the total signed area (TrueType outer contours are clockwise). For each point, with unit vectors `in` and `out` of the adjacent segments, `d = in·out`: if `d > −0.9375`, the shift is `(strength/2) · (in + out) / (1 + d)`, rotated toward the contour's outside and limited by `min(len_in, len_out)` the way FreeType limits it. With `x_strength = 0` this is the spike's `embolden_y`.
  - `measure.py`:
    - `horizontal_runs(o: Outline, y: float) -> list[tuple[float, float]]` and `vertical_runs(o: Outline, x: float) -> list[tuple[float, float]]`: exact crossings of a ray with the outline (each quadratic segment flattened into 32 lines), paired under the nonzero rule.
    - Named strokes, with `Stroke = Literal["l_stem", "o_top", "o_bottom", "e_top", "H_bar", "n_arch"]`: `l_stem` is the first horizontal run at `yMin + 0.75 · height`; `o_top`/`o_bottom` are the last/first vertical runs at the bbox center x; `e_top` is the last vertical run at the center x; `H_bar` is the single vertical run at the center x; `n_arch` is the last vertical run at the center x.
    - `stroke(o: Outline, kind: Stroke) -> float`.
    - `@dataclass(frozen=True) class Zones`: `lower: tuple[float, ...]` = (`g` yMin, `p` yMin, `o` yMin, 0, `x` yMax, `o` yMax, `l` yMax); `capital: tuple[float, ...]` = (`O` yMin, 0, `H` yMax, `O` yMax).
    - `zones_of(outline_of: Callable[[str], Outline]) -> Zones`.
  - `sanity.py`: `check_outline(candidate: Outline, reference: Outline) -> list[str]`. It returns an empty list when the outline passes. Failures:
    - a different contour count;
    - a contour whose signed-area sign differs from the reference's;
    - a contour that self-intersects (flattened, O(n²) segment test) when the reference's contour does not;
    - an inner contour whose absolute area is ≤ 1 unit².

- [ ] **Step 1: Write the failing tests.** The expected values are the design's Wanted Sans measurements.

```python
@pytest.mark.parametrize("w,l,o,e,h,n", [(400,168,160,160,164,156),(700,284,260,233,278,243),(1000,400,360,305,392,322)])
def test_wanted_strokes(wanted, w, l, o, e, h, n):
    ws = WantedSampler(wanted)
    got = [stroke(ws.outline(c, w), k) for c, k in (("l","l_stem"),("o","o_top"),("e","e_top"),("H","H_bar"),("n","n_arch"))]
    assert got == pytest.approx([l, o, e, h, n], abs=2)

def test_wanted_zones(wanted):
    z = zones_of(lambda c: WantedSampler(wanted).outline(c, 400))
    assert z.lower == pytest.approx((-460, -432, z.lower[2], 0, 1032, 1060, 1448), abs=1)
    assert z.capital[2] == pytest.approx(1448, abs=1)

def test_embolden_y_only_keeps_x(pretendard):
    o = PretendardSampler(pretendard).outline("o", 400)
    e = embolden_xy(o, 0, 20)
    assert [p[0] for p in e.coords] == [p[0] for p in o.coords]
    assert stroke(e, "o_top") == pytest.approx(stroke(o, "o_top") + 20, abs=1)

def test_sanity_flags_collapse(pretendard):
    o = PretendardSampler(pretendard).outline("o", 400)
    assert check_outline(o, o) == []
    assert any("collapsed" in m for m in check_outline(embolden_xy(o, 0, 900), o))
```

- [ ] **Step 2: Run** `uv run pytest tests/unit/test_embolden.py tests/unit/test_measure.py tests/unit/test_sanity.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement the three modules.**
- [ ] **Step 4: Run** the same command. Expected: PASS.
- [ ] **Step 5: Commit checkpoint (owner):** `build: add embolden, stroke measurement, and outline sanity`. Files: the three modules and three tests.

---

### Task 5: Assembly, H6 copies, cmap, and build CLI

**Files:**
- Create: `src/roofsans/context.py`, `src/roofsans/assemble.py`, `src/roofsans/build.py`, `src/roofsans/rules/__init__.py`, `src/roofsans/rules/h6_copy.py`
- Create (stubs that return `[]` or do nothing): `src/roofsans/rules/{r3_fullwidth,h2_compose,h3_construct,h3_enclosed,h4_letters,h5_symbols}.py`, `src/roofsans/features/__init__.py`, `src/roofsans/finalize.py`
- Test: `tests/unit/test_h6_copy.py`, `tests/acceptance/test_a01_wanted_identity.py`, `tests/acceptance/test_a02_pretendard_copies.py`, `tests/acceptance/test_a04_cmap.py`

**Interfaces:**
- Consumes: Tasks 1–3.
- Produces:
  - `make_context(inputs: Inputs) -> BuildContext`: loads both fonts and runs `select`. The `cmap` and `pj_names` fields stay empty until `build` fills them.
  - `@dataclass class BuildContext`: `inputs: Inputs`, `wanted: TTFont` (read-only), `pretendard: TTFont`, `selection: Selection`, `ws: WantedSampler`, `ps: PretendardSampler`, `cmap: dict[int, str]` (the planned Roof cmap, filled before contributors run), `pj_names: dict[str, str]` (Pretendard glyph name → Roof name for copied glyphs), and `contributed: dict[str, NewGlyph]`. Methods:
    - `outline(name: str, norm: float) -> Outline`: Wanted glyph, contributed glyph, or copied glyph.
    - `advance(name: str, norm: float) -> float`.
  - `assemble.planned_cmap(ctx) -> dict[int, str]`: Wanted's cmap, `pj_names` for `H6_COPY`, and `roof_glyph_name` for every other non-excluded rule. One exception: U+2789 `➉` maps to the glyph of U+2469 `⑩`, the way Wanted Sans maps `➀`–`➈` to `①`–`⑨`'s glyphs.
  - `assemble.insert(font: TTFont, glyphs: list[NewGlyph]) -> None`: appends glyphs to the glyph order and sets `glyf`, `hmtx` (advance; lsb from `xMin`), and `gvar`.
  - `assemble.write_cmap(font, cmap: dict[int, str], uvs: dict[int, list[tuple[int, str]]]) -> None`: formats 4 (3/1, 0/3), 12 (3/10, 0/4), and 14 (0/5).
  - `rules.h6_copy.contribute(ctx) -> list[NewGlyph]`, plus `copy_closure(ctx) -> dict[str, str]`, which fills `ctx.pj_names`. The closure is:
    - glyphs of the `H6_COPY` code points;
    - Pretendard's glyphs for `JAN_SHARED`;
    - all format-14 targets;
    - outputs of Pretendard GSUB lookups 34 (`locl` KOR), 73–76 (`jp78` `jp83` `jp90` `nlck`), and 77–85 (`rlig` feature-variation kana alternates);
    - composite components, recursively.

    Names keep Pretendard's name when Wanted Sans lacks it; otherwise they get the suffix `.pj` (for example `uni300C.pj`, `plus.pj`). Outlines are copied unchanged with renamed components, `gvar` goes through `remap_pretendard_tuples`, and advances come from Pretendard's `hmtx`.
  - `build.build(out: Path, inputs: Inputs | None = None) -> Path`. Order:
    1. `ensure_inputs`;
    2. `ctx`;
    3. `copy_closure`;
    4. `planned_cmap`;
    5. contributors in the fixed order `h6_copy`, `r3_fullwidth`, `h4_letters`, `h5_symbols`, `h2_compose`, `h3_construct`, `h3_enclosed`, each added to `ctx.contributed` before the next runs;
    6. `insert` and `write_cmap`;
    7. `features.apply_features(font, ctx)`;
    8. `finalize.finalize(font, ctx)`;
    9. save with `recalcTimestamp=False`;
    10. `finalize.write_license(out.parent / "OFL.txt", ctx.inputs)`, then copy that file to the repository root `OFL.txt` when `out` is the default path.

    `main()` parses `--out` (default `fonts/RoofSansVariable.ttf`). The `finalize.py` stub defines `finalize` and `write_license` as no-ops.

- [ ] **Step 1: Write the failing unit test**

```python
def test_closure_renames_and_plateaus(ctx):   # ctx fixture builds BuildContext from inputs
    names = copy_closure(ctx)
    assert names["uni300C"] == "uni300C.pj" and names["uni6F22"] == "uni6F22"
    assert all(names[n] for n in ("uni4E73.loclJAN", "uni30AC.varAlt01", "uni4E08.uv018"))
    g = {x.name: x for x in contribute(ctx)}["uni6F22"]
    assert {tuple(round(v, 4) for v in tv.axes["wght"]) for tv in g.variations} == {(0.0, 0.8834, 1.0), (0.8834, 1.0, 1.0)}
```

- [ ] **Step 2: Write the acceptance tests** (marker `acceptance`):
  - `test_a01_wanted_identity`: for every Wanted Sans code point at `wght` 400, 750, and 1000, the Roof glyph's coordinates, end points, and advance equal Wanted Sans's in `static(...)` instances. Also, the Roof `glyf` and `gvar` entries for those glyph names are structurally equal to Wanted's.
  - `test_a02_pretendard_copies`: for every glyph in `ctx.pj_names` at 400, 700, and 930, the coordinates match Pretendard's static instance (exact at 400 and 930, ≤ 1 unit at 700) and the advance is equal. For copies whose code point is Han, kana, or Japanese punctuation, and for every unencoded copy, the instance at 1000 equals the one at 930.
  - `test_a04_cmap`: the Roof cmap equals `planned_cmap` exactly, with no code point in U+E000–F8FF. All 524 sequences of Pretendard's format-14 subtable are present and point to `pj_names[target]`. Each target's outline passes the `test_a02` comparison.
  - `test_unknown_variation_selector_falls_back` (Review Focus 4): shaping `漢\U000E0108` and `A︀` with uharfbuzz gives the base glyph plus a zero-advance glyph, with no `.notdef`.
- [ ] **Step 3: Run** `uv run pytest tests/unit/test_h6_copy.py -v`. Expected: FAIL.
- [ ] **Step 4: Implement** `context.py`, `assemble.py`, `build.py`, `rules/h6_copy.py`, and the stubs.
- [ ] **Step 5: Run** `uv run pytest tests/unit/test_h6_copy.py -v` (expected: PASS). Then run `uv run roofsans-build --out build/t5.ttf && ROOF_FONT=build/t5.ttf uv run pytest tests/acceptance/test_a01_wanted_identity.py tests/acceptance/test_a02_pretendard_copies.py -v`. Expected: PASS. `test_a04_cmap` fails until Tasks 6–10 land; record the missing count.
- [ ] **Step 6: Commit checkpoint (owner):** `build: assemble Wanted Sans base with Pretendard JP CJK copies`. Files: every file listed under this task.

---

### Task 6: Fullwidth letters and signs (rule 3) and H3 sequences and fractions

**Files:**
- Modify (replace stubs): `src/roofsans/rules/r3_fullwidth.py`, `src/roofsans/rules/h3_construct.py`
- Test: `tests/unit/test_h3_construct.py`, `tests/acceptance/test_a03_fullwidth.py`, `tests/acceptance/test_a05_h3_components.py`

**Interfaces:**
- Consumes: `BuildContext` (Task 5), `composite_glyph`, `COMPOSITE_LOCS` (Task 3).
- Produces: `r3_fullwidth.contribute(ctx)` and `h3_construct.contribute(ctx)`, both returning composites. Also, in `h3_construct`:
  - `sequence_parts(ctx, cp: int) -> list[str]`: component names in order;
  - `fraction_parts(ctx, cp: int) -> list[str]`: `[numr, "fraction", dnom]` or `[numr, "fraction"]`;
  - `fraction_offsets(ctx, parts: Sequence[str], t: float) -> list[tuple[str, float, float]]`: cumulative-advance placement at location `t`, used for both fractions and sequences.

Rules:
- **Rule 3:** for each `R3_FULLWIDTH` code point `u`, use one component, the Wanted glyph for `u − 0xFEE0`. At each location `t` in `COMPOSITE_LOCS`, the offset is `dx(t) = (1920 − ctx.advance(base, t)) / 2` and the advance is 1920.
- **Rule 3 signs (`R3_SIGN`, design decision 11):** one component, the Wanted glyph with the same name as Pretendard's single component (`comma`, `plus.case`, …). Keep Pretendard's Japanese placement: at each `t`, choose `dx(t)` so the Wanted component's ink-box center x equals the ink-box center x of Pretendard's fullwidth glyph at `min(t_wght, 930)`. `，` stays at the bottom left, and `！` stays centered. y offset 0; advance 1920. These glyphs follow Wanted Sans to 1000 (no plateau).
- **Sequence:** the components are Roof cmap glyphs, so a component Wanted Sans lacks resolves to its H4/H5 glyph (`μ ℓ Ω ∕`). Unit squares take their component code points from Pretendard's composite, in order, and keep any 2×2 component transform. Digraphs, Roman numerals, `₨ ℡ ℻` use their Unicode compatibility decomposition. `№` is `N` + `ordmasculine`. The x offsets are the cumulative Roof advances at each location; y is 0; the advance is the sum.
- **Fraction:** `<first part>.numr` + `fraction` + `<last part>.dnom` (`⅟` has no denominator). Parts are digits (`one.numr`) or lowercase letters (`a.numr`, `c.dnom`). The x offsets are cumulative advances.

- [ ] **Step 1: Write the failing tests.** Two of them check the construction rule against Wanted Sans's own glyphs.

```python
def test_fraction_rule_reproduces_wanted_onehalf(ctx):
    for t in COMPOSITE_LOCS:
        parts = fraction_offsets(ctx, ("one.numr", "fraction", "two.dnom"), t)   # helper in module
        assert parts == [(n, x, 0) for n, x in wanted_component_offsets(ctx.wanted, "onehalf", t)]

def test_sequence_unit_square_uses_wanted_k_g(ctx):
    assert sequence_parts(ctx, ord("㎏")) == ["k", "g"]
    assert sequence_parts(ctx, ord("㎕")) == ["uni03BC", "l"]
    assert sequence_parts(ctx, ord("Ⅳ")) == ["I", "V"]
```

- [ ] **Step 2: Write the acceptance tests:**
  - `test_a03_fullwidth_signs` (Acceptance 3, decision 11): for each of the 23 `R3_SIGN` code points at 400, 750, and 1000, the instance outline equals the same-named Wanted Sans glyph shifted by `dx`, its ink center x is within 1 unit of Pretendard's fullwidth glyph at `min(wght, 930)`, and the advance is 1920.
  - `test_a03_fullwidth` (Acceptance 3): for each of the 62 code points at 400, 750, and 1000, the instance outline equals the Wanted Sans ASCII outline shifted by `dx`, `|left gap − right gap| ≤ 1` unit, and the advance is 1920.
  - `test_a05_h3_components` (Acceptance 5, H2/H3 part for H3): every `H3_SEQUENCE`/`H3_FRACTION` glyph is a composite. Each component is a Wanted Sans glyph whenever Wanted Sans maps the component's code point, and every component name exists in the font.
- [ ] **Step 3: Run** `uv run pytest tests/unit/test_h3_construct.py -v`. Expected: FAIL.
- [ ] **Step 4: Implement both modules.**
- [ ] **Step 5: Run** the unit test (expected: PASS). Then build and run both acceptance files with `ROOF_FONT`. Expected: PASS once Task 8 has landed; before that, components resolving to H4 glyphs are reported missing.
- [ ] **Step 6: Commit checkpoint (owner):** `build: synthesize fullwidth letters and H3 sequences from Wanted Sans`. Files: the two modules and three tests.

---

### Task 7: Enclosed numbers and superscript/subscript signs

**Files:**
- Modify (replace stub): `src/roofsans/rules/h3_enclosed.py`
- Test: `tests/unit/test_h3_enclosed.py`, `tests/acceptance/test_a05_h3_enclosed.py`

**Interfaces:**
- Consumes: Tasks 3, 4, 5.
- Produces: `contribute(ctx)`, which returns the helper glyphs plus the 22 encoded glyphs (`➉` shares `⑩`'s glyph through the cmap):
  - `roof.ring`: contours 0–1 of Wanted's `uni2460` at each W location, advance = `uni2460`'s.
  - `roof.disc`: the largest-bbox contour of Wanted's `uni2776`.
  - `roof.knockout.<digit>`: the digit's `.numr` outline with every contour reversed.
  - Also `sign_stroke(o: Outline, source: str) -> float`, the per-source stroke measurement defined in rule 2 below.

Rules:
- `⑩`–`⑳` = `roof.ring` + two `<digit>.numr` components. `⓫`–`⓴` and `❿` = `roof.disc` + two `roof.knockout.<digit>` components. At each location, the pair's ink bbox is centered on the ring's (or disc's) ink-bbox center, and the advance equals the ring's.
- `⁺⁻⁼⁽⁾` and `₊₋₌₍₎` are simple glyphs made from Wanted's `plus minus equal parenleft parenright` at each of `0.0, W_MID, 1.0`:
  1. Scale about the origin by `k = height(zero.dnom) / height(zero)` at 400.
  2. Embolden in x and y by `(k_s − k) · sign_stroke(source)`, where `k_s = stroke(one.dnom, "l_stem") / stroke(one, "l_stem")` at that master. `sign_stroke` is defined per source: `plus` uses the `l_stem` measurement (horizontal run at 75% height, which crosses only the vertical bar); `minus` and `equal` use the first vertical run at the center x; the parentheses use the first horizontal run at 50% height.
  3. Shift y by +936 (superscript) or −208 (subscript), the offsets Wanted uses for `²` and `₂`.
  4. Set the advance to `k ·` the source advance, with the ink centered in it.

- [ ] **Step 1: Write the failing tests**

```python
def test_ring_is_shared_by_wanted_circled_digits(ctx):
    for u in range(0x2460, 0x2469):
        for t in (0.0, 1.0):
            assert wanted_contours(ctx, u, t)[:2] == ring_contours(ctx, t)

def test_supsub_stroke_matches_superior_figures(ctx):
    g = {x.name: x for x in contribute(ctx)}["uni207A"]
    for t in (0.0, W_MID, 1.0):
        o = newglyph_outline(g, t, ctx.outline)
        assert sign_stroke(o, "plus") == pytest.approx(stroke(ctx.outline("one.dnom", t), "l_stem"), rel=0.10)
```

- [ ] **Step 2: Write `test_a05_h3_enclosed`** (Acceptance 5, H3): at 400, 550, 700, 850, and 1000, the first two contours of `⑩`–`⑳`'s instance outlines equal the first two contours of `①`'s instance at the same weight, and `cmap[0x2789] == cmap[0x2469]`. Every helper and enclosed glyph passes `check_outline` against its 400 outline.
- [ ] **Step 3: Run** `uv run pytest tests/unit/test_h3_enclosed.py -v`. Expected: FAIL.
- [ ] **Step 4: Implement `h3_enclosed.py`.**
- [ ] **Step 5: Run** the unit test (expected: PASS). Then build and run `test_a05_h3_enclosed.py` with `ROOF_FONT`. Expected: PASS.
- [ ] **Step 6: Commit checkpoint (owner):** `build: build enclosed numbers and sup/sub signs from Wanted Sans parts`. Files: module and two tests.

---

### Task 8: H4 letter harmonization

**Files:**
- Create: `src/roofsans/harmonize.py`
- Modify (replace stub): `src/roofsans/rules/h4_letters.py`
- Test: `tests/unit/test_harmonize.py`, `tests/acceptance/test_a05_h4.py`

**Interfaces:**
- Consumes: Tasks 3, 4, 5.
- Produces:
  - `@dataclass(frozen=True) class MasterParams`: `norm: float`, `wght: float`, `w_prime: float`, `dy: float`, `lower_map: ZoneMap`, `capital_map: ZoneMap`.
  - `ZoneMap = tuple[tuple[float, float], ...]`: sorted (source y, target y) pairs.
  - `apply_zone_map(m: ZoneMap, y: float) -> float`: piecewise linear between the pairs; outside them, a shift by the nearest pair's offset.
  - `solve_w_prime(ps, ws, wght: float) -> float`: bisection on [45, 1100] until Pretendard's `l_stem` equals Wanted's at `wght` within 0.05 units.
  - `harmonize_outline(o: Outline, zone: Zone, p: MasterParams) -> Outline`: first `embolden_xy(o, 0, p.dy)`, then `y → apply_zone_map(map, y)`. x and the phantom points stay unchanged, so Pretendard's advance at `w′` is kept.
  - `solve_dy(ps, ws, wght: float, w_prime: float) -> float`: bisection on [0, 200] for the δy where the median of (Wanted stroke − harmonized Pretendard stroke) over `o_top`, `o_bottom`, `e_top`, `H_bar`, `n_arch` is 0. The zone maps are rebuilt for each candidate δy from the emboldened Pretendard zones.
  - `solve_masters(ps, ws) -> dict[float, MasterParams]` for `H4_LOCS`. It is cached on `ctx` by `h4_letters`.
  - `h4_letters.contribute(ctx)`: for each `H4_LETTER` code point, sample Pretendard at each master's `w′`, harmonize with the code point's zone, and call `simple_glyph`. Also `h4_letters.params(ctx) -> dict[float, MasterParams]`, used by Tasks 9 and 10.

- [ ] **Step 1: Write the failing tests** with the spike's values.

```python
def test_w_prime(ps, ws):
    assert [round(solve_w_prime(ps, ws, w)) for w in (400, 700, 1000)] == pytest.approx([387, 672, 952], abs=3)

def test_dy(ps, ws):
    got = [solve_dy(ps, ws, w, solve_w_prime(ps, ws, w)) for w in (400, 700, 1000)]
    assert got == pytest.approx([13, 37.5, 78.5], abs=3)

def test_zone_map_hits_wanted_heights(ps, ws):
    p = solve_masters(ps, ws)[1.0]
    x = harmonize_outline(ps.outline("x", p.w_prime), Zone.LOWER, p)
    assert x.bounds()[3] == pytest.approx(1032, abs=1)
```

- [ ] **Step 2: Write `test_a05_h4`** (Acceptance 5, H4), parametrized over `wght` 400, 550, 700, 850, and 1000.
  - Heights, on the Roof instances: Cyrillic `х` top and Greek `ο` top/bottom match Wanted's `x` and `o` (1032 and the overshoots); Cyrillic `р` bottom matches `p`; `у` bottom matches `g`; Cyrillic `Н` top matches 1448; `О` matches `O`'s overshoots. Tolerance ±2 units.
  - Weights, on the Roof instances: `н`/`п` vertical stem vs. Wanted `n` within ±3%. The horizontal strokes `о` top/bottom, `е` top, `п` arch, `Н` bar, and Greek `ο ε π` vs. Wanted `o o e n H` and `o e n`: median within ±3%, each within ±10%.
  - Reference glyphs: Pretendard's `l o e H n` are run through the same masters and `tuples_from_masters`, then interpolated at the test weight. `l_stem` must be within ±3% of Wanted's, and the reference median within ±3%.
- [ ] **Step 3: Run** `uv run pytest tests/unit/test_harmonize.py -v`. Expected: FAIL.
- [ ] **Step 4: Implement `harmonize.py` and `h4_letters.py`.**
- [ ] **Step 5: Run** the unit test (expected: PASS). Then build and run `test_a05_h4.py` with `ROOF_FONT`. Expected: PASS. Report the solved `w′` and δy values.
- [ ] **Step 6: Commit checkpoint (owner):** `build: harmonize Pretendard letters to Wanted Sans height and weight`. Files: two modules and two tests.

---

### Task 9: H2 decomposable Latin, Vietnamese, and horn letters

**Files:**
- Modify (replace stub): `src/roofsans/rules/h2_compose.py`
- Test: `tests/unit/test_h2_compose.py`, `tests/acceptance/test_a05_h2_components.py`

**Interfaces:**
- Consumes: Tasks 3, 5, and 8 (`h4_letters.params`, H4 mark glyphs `uni0309`, `uni031B`, and others).
- Produces:
  - `contribute(ctx)`: 228 composites.
  - `mark_anchor(ctx, mark: str) -> tuple[MarkClass, int, int]` and `base_anchor(ctx, base: str, cls: MarkClass) -> tuple[int, int] | None`, with `MarkClass = Literal["top", "bottom", "horn"]`.
  - `horn_offset(ctx, base: str, t: float) -> tuple[float, float]`.
  - Task 11 uses all three to build mark-to-base lookups.

Rules:
- **Decomposition:** full canonical decomposition (NFD). The base is the Wanted glyph for the first character; `i`/`j` become `dotlessi`/`uni0237` under a top mark. Each mark is the Roof cmap glyph for its code point, so Wanted's mark is used when Wanted has one, otherwise the H4 mark.
- **Classes:**
  - Wanted marks take their class from Wanted's GPOS lookup 7 (anchor y > 0 means top).
  - H4 marks take their class from the Unicode combining class: 230 → top, 220/202 → bottom, 216 → horn.
  - An H4 mark's anchor is Pretendard's GPOS mark anchor (for example `hook` (−596, 1244)), with y passed through `apply_zone_map(lower_map)` at the default master.
  - Base anchors come from Wanted's lookup 7.
- **Offset per location `t` in `COMPOSITE_LOCS`:** `base_anchor − mark_anchor + Δ(base, class, t)`. Δ is the variation of the matching component offset in an existing Wanted composite with the same base and a mark of the same class (for example `ecircumflex` for `e` + top). It is 0 when no such composite exists.
- **Same-class stacking** (`ầ ấ ẩ ẫ ằ ắ ẳ ẵ`, `ǖ ǘ ǚ ǜ`, and others): the upper mark keeps the lower mark's x alignment. Its ink bottom sits `G(t)` above the lower mark's ink top, where `G(t)` is the clearance between `e`'s top and `uni0302`'s ink bottom in Wanted's `ecircumflex` at `t`. Above-plus-below follows Wanted's `uni1EC7`.
- **Horn:** in Pretendard's `ohorn`/`uhorn`/`Ohorn`/`Uhorn`, find the contour that is a translate of `uni031B`. Record `rx` = that contour's xMin − the base's xMax and `ry` = its yMin, both at Pretendard 400. At each `t`, the Roof horn's ink xMin = Wanted base xMax(t) + `rx`, and its ink yMin = `apply_zone_map(map, ry)` (lower map for `o`/`u`, capital map for `O`/`U`). Tone marks on horn letters attach to the base's top anchor.

- [ ] **Step 1: Write the failing tests**

```python
def test_rule_reproduces_wanted_composites(ctx):
    for name in ("ecircumflex", "abreve", "Ecircumflex", "uni1EC7", "uni1EAD"):
        for t in COMPOSITE_LOCS:
            assert rebuilt_offsets(ctx, name, t) == wanted_component_offsets(ctx.wanted, name, t)

def test_vietnamese_uses_wanted_marks(ctx):
    g = {x.name: x for x in contribute(ctx)}
    assert component_names(g["uni1EA7"]) == ["a", "uni0302", "gravecomb"]
    assert component_names(g["uni1EF1"]) == ["u", "uni031B", "dotbelowcomb"]

def test_horn_touches_base(ctx):
    for base in ("o", "u", "O", "U"):
        for t in COMPOSITE_LOCS:
            assert horn_ink_xmin(ctx, base, t) <= ctx.outline(base, t).bounds()[2] + 2

def test_nfd_latin_composes(roof_path):            # Review Focus 1, marker acceptance
    for cp in h2_codepoints():
        assert shape(roof_path, unicodedata.normalize("NFD", chr(cp))) == [cmap(cp)]

def test_mark_alignment_between_masters(roof_path): # Review Focus 5, marker acceptance
    for w in (550, 850):
        assert mark_center_x(roof_path, "uni1EA7", "uni0302", w) == pytest.approx(
            mark_center_x(roof_path, "acircumflex", "uni0302", w), abs=1)
```

- [ ] **Step 2: Write `test_a05_h2_components`** (Acceptance 5, H2/H3 part for H2): every H2 glyph is a composite whose base and marks are Wanted glyphs whenever Wanted maps those code points. The only non-Wanted marks are H4 marks.
- [ ] **Step 3: Run** `uv run pytest tests/unit/test_h2_compose.py -m "not acceptance" -v`. Expected: FAIL.
- [ ] **Step 4: Implement `h2_compose.py`.**
- [ ] **Step 5: Run** the unit tests (expected: PASS). Then build and run `tests/acceptance/test_a05_h2_components.py` and the two acceptance tests above. Expected: PASS.
- [ ] **Step 6: Commit checkpoint (owner):** `build: compose Vietnamese and accented Latin from Wanted Sans parts`. Files: module and two tests.

---

### Task 10: H5 symbols and outline sanity across harmonized glyphs

**Files:**
- Modify (replace stub): `src/roofsans/rules/h5_symbols.py`
- Test: `tests/unit/test_h5_symbols.py`, `tests/acceptance/test_a05_h5.py`, `tests/acceptance/test_a06_outline_sanity.py`

**Interfaces:**
- Consumes: Tasks 3, 4, 5, and 8 (`h4_letters.params`).
- Produces: `contribute(ctx)`, and `category_transform(ctx, cat: SymbolCategory, t: float) -> Transform` with `@dataclass(frozen=True) class Transform`: `scale: float`, `shift_y: float`, `advance_ratio: float`, `sample_wght: float`.

Rules (per master in `H4_LOCS`):
- `ARROW` (reference `→`): `scale` is the Wanted/Pretendard ink-height ratio; `shift_y` moves Pretendard's scaled center (634·s) onto Wanted's center (725); `advance_ratio` is the Wanted/Pretendard advance ratio of `→`.
- `MATH` (reference `+`): `scale` is the ink-width ratio; `shift_y` moves the axis 566·s onto 540; `advance_ratio = scale`.
- `GEOMETRIC`: reference `●` for code points whose name contains `CIRCLE`, otherwise `■`. `scale` is the ink-height ratio; `shift_y` aligns the centers; `advance_ratio = scale`.
- `CURRENCY` and `OTHER`: identity.
- `sample_wght`: for `ARROW`, solve Pretendard `→` shaft thickness (vertical run at 25% of the ink width) × `scale` = Wanted's. For `MATH`, use the same rule on the `+` bar. For the other categories, use H4's `w′`. Iterate `scale` and `sample_wght` three times.
- Each glyph's x is scaled about the origin and re-centered so its ink-center/advance ratio stays Pretendard's. The new advance is Pretendard's advance × `advance_ratio`.

- [ ] **Step 1: Write the failing tests**

```python
def test_arrow_transform_lands_on_725(ctx):
    for t in H4_LOCS:
        tr = category_transform(ctx, SymbolCategory.ARROW, t)
        assert 634 * tr.scale + tr.shift_y == pytest.approx(725, abs=2)

def test_math_axis(ctx):
    tr = category_transform(ctx, SymbolCategory.MATH, 0.0)
    assert 566 * tr.scale + tr.shift_y == pytest.approx(540, abs=2)
```

- [ ] **Step 2: Write the acceptance tests:**
  - `test_a05_h5`: at 400, 550, 700, 850, and 1000, the ink center y of `← → ↔ ⟵ ⟶ ⟷ ⇐ ⇒ ⇔ ⟸ ⟹ ⟺ ↩ ↪ 🡐 🡒` is 725 ±5, and the center of `≤ ≥ ≪ ≫ ∞ ⋯` is 540 ±5.
  - `test_a06_outline_sanity` (Acceptance 6): every `H4_LETTER`, `H5_SYMBOL`, and `H3_SUPSUB` glyph passes `check_outline(instance at w, pretendard_or_wanted_source at 400)` at 400, 550, 700, 850, 930, 1000, and at each master.
- [ ] **Step 3: Run** `uv run pytest tests/unit/test_h5_symbols.py -v`. Expected: FAIL.
- [ ] **Step 4: Implement `h5_symbols.py`.**
- [ ] **Step 5: Run** the unit test (expected: PASS). Then build and run both acceptance files with `ROOF_FONT`. Expected: PASS. If sanity fails, list the glyphs and escalate; do not tune per glyph (Designer's call 10).
- [ ] **Step 6: Commit checkpoint (owner):** `build: align Pretendard symbols to Wanted Sans axes`. Files: module and three tests.

---

### Task 11: OpenType features

**Files:**
- Modify (replace stub): `src/roofsans/features/__init__.py`
- Create: `src/roofsans/features/gsub.py`, `src/roofsans/features/gpos.py`, `src/roofsans/features/gdef.py`
- Test: `tests/unit/test_features.py`, `tests/acceptance/test_a07_features.py`

**Interfaces:**
- Consumes: `ctx.pj_names`, `ctx.cmap` (Task 5); `mark_anchor`, `base_anchor`, `horn_offset` (Task 9).
- Produces: `apply_features(font: TTFont, ctx: BuildContext) -> None`, `gsub.carry(font, ctx)`, `gpos.carry(font, ctx)`, and `gdef.classify(font, ctx)`.

GSUB:
1. Keep every Wanted lookup, feature, and script at its index.
2. Append copies of Pretendard lookups with renamed glyphs; drop entries whose glyphs are absent:
   - 34 → `locl` (KOR) and `ss20`;
   - 73, 74, 75, 76 → `jp78`, `jp83`, `jp90`, `nlck`;
   - 71, 72 → `fwid`, `pwid`, re-mapped by code point (source cp → target cp through `ctx.cmap`);
   - 77–85 → the kana `rlig` alternates.
3. Add a new lookup `JAN`: `JAN_SHARED` Wanted glyphs → `pj_names[...]` (`.pj`).
4. Add scripts `hani` and `kana`. Their default LangSys is the `DFLT` default feature list plus `ss20 jp78 jp83 jp90 nlck fwid pwid`. Also:
   - `hani`/`KOR ` = default + `locl`(KOR);
   - `hani`/`JAN `, `kana`/`JAN `, `DFLT`/`JAN `, `latn`/`JAN ` = that script's default + `locl`(JAN).
   - Add `ss20 jp78 jp83 jp90 nlck fwid pwid` to the default LangSys of `DFLT`, `latn`, and `hang`.
5. Merge feature variations:
   - Convert each Pretendard condition `s` to `wght` (`400 + 530s` when `s ≥ 0`, `400 + 355s` when negative), then to Roof `t`, clamped to [0, 1] and rounded to F2Dot14. The maximum stays 1.0.
   - Emit records in descending `t`. Each record substitutes the shared `rlig` feature with Wanted's FV lookups (when `t ≥ 0.41668701171875`) plus every Pretendard alternate lookup active at `t`.

GPOS:
- Append a `kern` PairPos lookup holding Pretendard lookup 1–2 pairs whose two glyphs are both in `pj_names` values (it may be empty; then skip it and report).
- Append MarkBasePos lookups for H4 marks: one for the top class on Wanted lookup 7's top base anchors, one for the bottom class, and one for the horn class on `o u O U`. The horn base anchor is the horn mark anchor plus `horn_offset(base, 0.0)`.
- Register all of these in every script's default LangSys and the new LangSys entries.

GDEF: class 3 (mark) for H4 combining marks, class 1 for other new glyphs.

Drop all other Pretendard features (`cpsp`, `mark`, `mkmk`, Latin `ss`/`cv`, `case`, `frac`, `sups`, `calt`, `ccmp`, `aalt`, `locl` ROM/CAT). Wanted's `aalt` is unchanged.

- [ ] **Step 1: Write the failing unit test**

```python
def test_fv_conditions_remap():
    assert to_roof_t(0.69244384765625) == pytest.approx((400 + 0.69244384765625 * 530 - 400) / 600, abs=1e-4)
    assert to_roof_t(-0.47607421875) == 0.0
```

- [ ] **Step 2: Write `test_a07_features`** (Acceptance 7) with uharfbuzz at `wght` 400 unless stated:
  - `test_wanted_behavior_unchanged`: shape `The quick brown fox 0123456789 ½ ffi (A) [B] ê ñ ș 한글 테스트 ㄱㄴ` with Wanted and Roof. Do it for the default features, each of `ss01`–`ss16` and `cv01`–`cv22`, and `frac sups subs tnum zero case`, under languages none/`ko`/`tr`, at `wght` 400 and 1000. Glyph names and positions must be identical.
  - `test_kor_hanja`: for each of the 537 entries of Pretendard lookup 34: with `language="ko"`, script `hani`, the result is the renamed KOR form. With `features={"ss20": True}` and no language, the result is the same. With no language and no features, the result is the default form.
  - `test_jan_punctuation`: `あ　〈〉《》「」『』【】〔〕あ` gives `.pj` glyphs with advance 1920 under `language="ja"`, and Wanted glyphs under `ko` and with no language.
  - `test_jan_brackets_after_latin` (Review Focus 2): `ID「abc」` and `2026「新」` under `ja` give `uni300C.pj`/`uni300D.pj`.
  - `test_jp_variants`: for every mapping in Pretendard lookups 73–76, the Roof result with the feature on equals `pj_names[target]`.
  - `test_kana_weight_alternates`: for each input glyph of lookups 77–85 and each `wght` in 400, 500, 600, 700, 767, 800, 900, 930, 1000, the Roof glyph equals `pj_names[...]` of Pretendard's result at `min(wght, 930)`.
  - `test_nfd_kana_composes` (Review Focus 1): `が` and `パ` shape to the glyphs of `が` and `パ`.
  - `test_decomposed_marks`: `ỏ` puts the `uni0309` mark's center x on `o`'s top anchor x ±2, and `ơ` attaches at the horn anchor.
- [ ] **Step 3: Run** `uv run pytest tests/unit/test_features.py -v`. Expected: FAIL.
- [ ] **Step 4: Implement the four feature modules.**
- [ ] **Step 5: Run** the unit test (expected: PASS). Then build and run `test_a07_features.py` with `ROOF_FONT`. Expected: PASS. Report the carried kern pair count.
- [ ] **Step 6: Commit checkpoint (owner):** `build: carry Pretendard JP CJK features and add JAN punctuation`. Files: four modules and two tests.

---

### Task 12: Names, metrics, licensing, OTS, round-trip, and determinism

**Files:**
- Modify (replace stub): `src/roofsans/finalize.py`
- Create (build outputs, committed): `fonts/RoofSansVariable.ttf`, `OFL.txt`
- Test: `tests/unit/test_finalize.py`, `tests/acceptance/test_a08_ots_roundtrip.py`, `tests/acceptance/test_a04_cmap.py` (already written in Task 5; must pass now), `tests/acceptance/test_build_determinism.py`

**Interfaces:**
- Consumes: `BuildContext`.
- Produces:
  - `finalize(font, ctx) -> None`.
  - `copyright_lines(inputs: Inputs) -> list[str]`: every `Copyright ...` line plus its `with Reserved Font Name ...` line, verbatim, from Wanted's `OFL.txt` first and then Pretendard's `LICENSE`. That is Wanted Sans Project Authors, Kil Hyung-jin, Adobe, The Inter Project Authors, and The M+ FONTS Project Authors.
  - `write_license(path: Path, inputs: Inputs) -> None`: writes those lines, then the OFL 1.1 body from Wanted's `OFL.txt`. `build` already calls it (Task 5, step 10), so this task replaces only the stub body.

`finalize` sets:
- `name`:
  - 0 = `copyright_lines` joined with a space, without the RFN clauses;
  - 1 = `Roof Sans`; 2 = `Regular`; 3 = `1.000;ROOF;RoofSans-Regular`; 4 = `Roof Sans Regular`; 5 = `Version 1.000`; 6 = `RoofSans-Regular`;
  - 13 = `This Font Software is licensed under the SIL Open Font License, Version 1.1.`; 14 = `https://openfontlicense.org`; 25 = `RoofSans`;
  - drop 8, 9, 11, 12, 16, 17, 21, 22;
  - keep the instance and STAT name IDs, rewritten wherever they contain `Wanted Sans` → `Roof Sans`.
- `head.fontRevision = 1.0`, and `created = modified` = 2026-10-31T00:00:00Z.
- The `OS/2` and `hhea` metrics in Global Constraints, unchanged from Wanted. `achVendID = "ROOF"`. Recompute `ulUnicodeRange`. Set code page bit 17 (JIS) in addition to Wanted's bits.

- [ ] **Step 1: Write the failing tests**

```python
def test_names(roof):
    n = roof["name"]
    assert n.getDebugName(1) == "Roof Sans" and n.getDebugName(5) == "Version 1.000"
    for rec in n.names:
        if rec.nameID not in (0, 13, 14):
            assert not re.search(r"Pretendard|Source|Inter|M PLUS 1|Wanted Sans", rec.toUnicode())
    assert "Kil Hyung-jin" in n.getDebugName(0) and "M+ FONTS" in n.getDebugName(0) and "Inter Project" in n.getDebugName(0)

def test_metrics(roof):
    h, o = roof["hhea"], roof["OS/2"]
    assert (h.ascent, h.descent, h.lineGap) == (1950, -494, 0)
    assert (o.sTypoAscender, o.sTypoDescender, o.sTypoLineGap, o.usWinAscent, o.usWinDescent) == (1752, -296, 0, 1950, 494)
    assert not o.fsSelection & (1 << 7) and (o.sxHeight, o.sCapHeight) == (1032, 1448)
    a = roof["fvar"].axes[0]
    assert (a.axisTag, a.minValue, a.defaultValue, a.maxValue) == ("wght", 400, 400, 1000)
```

- [ ] **Step 2: Write the acceptance tests:**
  - `test_a08_ots_roundtrip` (Acceptance 8): `ots-sanitize fonts/RoofSansVariable.ttf build/ots.ttf` exits 0. Saving to `BytesIO` and reloading gives an equal `compile()` for every table. `saveXML` then `importXML` then save succeeds.
  - `test_build_determinism`: two builds into separate temp dirs have equal SHA-256.
- [ ] **Step 3: Run** `uv run pytest tests/unit/test_finalize.py -v`. Expected: FAIL.
- [ ] **Step 4: Implement `finalize.py`.**
- [ ] **Step 5: Run** `uv run roofsans-build` and `uv run pytest -v` (all unit and acceptance tests). Expected: every test PASS. Paste the summary line into the report.
- [ ] **Step 6: Commit checkpoint (owner):** `build: finalize names and licensing and add the first Roof Sans build`. Files: `src/roofsans/finalize.py fonts/RoofSansVariable.ttf OFL.txt` and the three tests.

---

### Task 13: Specimen sheet (Acceptance 9)

**Files:**
- Create: `verify/specimen.py`, `verify/specimen_lines.json`
- Test: `tests/unit/test_specimen.py`

**Interfaces:**
- Consumes: the built font, `Inputs`.
- Produces: `render_specimen(roof: Path, inputs: Inputs, out_dir: Path, weights=(400, 700, 1000)) -> list[Path]`, plus a CLI: `uv run python verify/specimen.py --out build/specimen`.

Behavior:
- **Roof rows:** each line is shaped with uharfbuzz using its `language`, with variations `wght=w`. Outlines are drawn with skia from `roof.getGlyphSet(location={"wght": w})`, using HarfBuzz advances.
- **Naive rows:** per character, Wanted at `w` when Wanted maps it, else Pretendard at `min(w, 930)`, unshaped, with Pretendard glyphs tinted `#D0461E` (the spike's `naive.py` method).
- Both rows get guide lines at y = 0, 1032, and 1448.
- Output: one PNG per weight with Roof and naive rows interleaved, at 64 px per em.

`specimen_lines.json` holds `[{"language": ..., "text": ...}]` with exactly:
1. `ja`: `「東京」へ行きます。今日は、とても暑い！（テスト）『確認』【注意】〔例〕〈山〉《本》　終わり`
2. `ko`: the same text.
3. `ko`: `大韓民國 漢字 學校 樂園 — 무게 5㎏, 넓이 30㎡, 거리 12㎞, 용량 500㎖`. `樂` is in lookup 34; the implementer swaps in another KOR-form hanja if one is missing.
4. none: `Tiếng Việt: cảm ơn, Thưởng, người, Đặng Thị Ngọc Ẩn — ầ ấ ẩ ẫ ậ ằ ắ ẳ ẵ ặ ờ ớ ở ỡ ợ ừ ứ ử ữ ự`
5. none: `Hoxen Жажда Шехонь Москва λαβγδεζ Ελληνικά — xоxо ŋ ə ʃ ƒ`
6. none: `→ ⇒ ↩ ← ↔ ⟶ 1+2≤3 ≥ ≠ ∞ ∑ √ $ € ₩ ₫ ● ■ ▲ ◆`
7. none: `①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳ ⓫⓴ ½ ⅓ ¼ ⅚ ⅟ x² x⁺ x⁻ x⁼ x⁽ⁿ⁾ H₂O ₊₋ Ⅳ ㎏`

- [ ] **Step 1: Write the failing test.** `test_specimen_renders`: `render_specimen(...)` writes three PNGs, each at least 1000 px wide, and every line's shaped Roof glyph list contains no `.notdef`.
- [ ] **Step 2: Run** `uv run pytest tests/unit/test_specimen.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement `specimen.py`.**
- [ ] **Step 4: Run** the test (expected: PASS) and the CLI. List the PNG paths in the report. The visual verdict belongs to Task 16.
- [ ] **Step 5: Commit checkpoint (owner):** `verify: add specimen sheet against the naive merge`. Files: `verify/specimen.py verify/specimen_lines.json tests/unit/test_specimen.py`.

---

### Task 14: Flutter specimen app (Acceptance 10 harness)

**Files:**
- Create: `verify/flutter_specimen/.fvmrc` (`{"flutter": "3.44.9"}`), `pubspec.yaml`, `analysis_options.yaml`, `lib/main.dart`, `test/line_metrics_test.dart`, `tool/stage_fonts.sh`, and the Android scaffold from `fvm flutter create --platforms android --org dev.roofsans flutter_specimen`.

**Interfaces:**
- Consumes: a font file path. Until Task 12 lands, the Wanted Sans VF serves as a stand-in.
- Produces:
  - `tool/stage_fonts.sh <roof.ttf> <pretendard-static-dir>`: copies the font to `assets/fonts/RoofSansVariable.ttf`, and `PretendardJP-Regular.ttf` and `PretendardJP-Bold.ttf` from the given directory (the app's `assets/font/PretendardJP/`) to `assets/fonts/`.
  - The app screen.

`pubspec.yaml` depends on `flutter_localizations`. It declares family `RoofSans` (one asset, no weight entries) and family `PretendardJP` (Regular 400, Bold 700).

`lib/main.dart` shows one scrolling screen:
1. A header with `boldText: ${MediaQuery.boldTextOf(context)}` and `locale: ${Localizations.localeOf(context)}`, plus a `SegmentedButton` with `ko` and `ja`. The button sets `MaterialApp.locale` to `Locale('ko','KR')` or `Locale('ja','JP')`; `supportedLocales` are those two.
2. For each weight `w300, w400, w500, w600, w700, w800, w900`: a label `wNNN` and `Text(sample, style: TextStyle(fontFamily: 'RoofSans', fontWeight: FontWeight.wNNN, fontSize: 18))`. Under it, the same text with `fontVariations: [FontVariation('wght', NNN)]` and no `fontWeight`, so a real weight and the axis setting can be compared line by line. `sample` = `한글 ㅅㄴ 강남 Latin 0123 日本語「東京」へ、カタカナ 漢字 大韓民國 ①⑩ ½⅓ cảm ơn`.
3. A metrics table. For `RoofSans` and `PretendardJP` at font sizes 12, 16, and 24, it lays out `한글 Aa 日本` with `TextPainter` (no `height` override). It shows `height`, `ascent`, and `descent` from `computeLineMetrics().first`, and `MATCH` or `DIFF` per size, comparing within 0.01 logical px.

`test/line_metrics_test.dart` loads both families with `FontLoader` from `assets/fonts/` and asserts the same equality at 12, 16, and 24.

- [ ] **Step 1: Write the failing test** `line_metrics_test.dart` as described.
- [ ] **Step 2: Run** `cd verify/flutter_specimen && fvm flutter test`. Expected: FAIL (fonts not staged, or the screen is missing).
- [ ] **Step 3: Implement** `main.dart` and `stage_fonts.sh`. Stage with `tool/stage_fonts.sh ../../inputs/WantedSansVariable.ttf /Users/huke/Development/liveanywhere/app/assets/font/PretendardJP`.
- [ ] **Step 4: Run** `fvm flutter analyze` (expected: no issues) and `fvm flutter test` (expected: PASS, because Wanted and PretendardJP both resolve to 1950/−494).
- [ ] **Step 5: Commit checkpoint (owner):** `verify: add Flutter specimen app for the Android check`. Files: everything under `verify/flutter_specimen/` except git-ignored paths.

---

### Task 15: README, agent notes, and build notes

**Files:**
- Create: `README.md`, `AGENTS.md`, `docs/ROOF_SANS_BUILD_NOTES.md`

**Interfaces:**
- Consumes: final behavior from Tasks 1–14.

Content:
- `README.md`:
  - what Roof Sans is (from the design's Intent);
  - build: `uv sync`, `uv run roofsans-fetch` (or `--from-refs refs`), `uv run roofsans-build`, `uv run pytest`;
  - Flutter usage: a pubspec snippet with one asset and no weight entries; `FontWeight` on Flutter ≥ 3.41; `fontVariations: [FontVariation('wght', 700)]` on older versions; Korean hanja forms via `locale: Locale('ko')` or `FontFeature('ss20')`;
  - the known issue for Flutter ≤ 3.32 (hollow Hangul under fake bold, per the design's Flutter section);
  - migration notes: weights below 400 render as 400; Japanese brackets need `ja` locale;
  - license.
- `AGENTS.md`: the commands above, the no-commit rule, the `refs/` rule, and the advance-measurement trap from Global Constraints.
- `docs/ROOF_SANS_BUILD_NOTES.md`:
  - input pinning;
  - glyph naming (`.pj`, `.roof`, `roof.*` helpers);
  - tolerances used by the tests and why;
  - the corrected advance fact;
  - the choices this plan made where the design was open (Vietnamese same-side stacking, horn derivation, `№`, the enclosed-number scope, JAN under `DFLT`/`latn`, the `rlig` kana alternates, the Inter copyright);
  - the solved `w′`/δy values.

- [ ] **Step 1: Write the three files.**
- [ ] **Step 2: Verify:** every command in `README.md` runs as written from a fresh clone (`git clone . /tmp/roof-check && cd /tmp/roof-check && uv sync && uv run roofsans-fetch && uv run roofsans-build`). Expected: the build completes and the SHA-256 equals the committed font's.
- [ ] **Step 3: Commit checkpoint (owner):** `docs: add README, agent notes, and build notes`. Files: the three files.

---

### Task 16: Final verification (main session)

**Files:** none created. Screenshots go to `build/verify/`.

- [ ] **Step 1:** `uv run pytest -v`. Expected: all PASS (Acceptance 1–8 plus Review Focus tests).
- [ ] **Step 2: Acceptance 9.** Open `build/specimen/*.png`. Check each line for a visible jump in x-height, baseline, weight, or symbol axis between Roof glyphs. Compare with the naive rows. Record the verdict per line.
- [ ] **Step 3: Acceptance 10.**
  1. Start the emulator in a visible Orca terminal: `~/Library/Android/sdk/emulator/emulator -avd Medium_Phone_API_36.1`.
  2. Stage the fonts: `tool/stage_fonts.sh ../../fonts/RoofSansVariable.ttf /Users/huke/Development/liveanywhere/app/assets/font/PretendardJP`.
  3. Run `fvm flutter run -d emulator-5554` in a second visible terminal.
  4. For each of the four combinations of `adb shell settings put secure font_weight_adjustment 0|300` (bold text off/on; restart the app after each change) and the `ko`/`ja` segment:
     - capture `adb exec-out screencap -p > build/verify/<locale>_<bold>.png`;
     - confirm the header shows the expected `boldText` and locale;
     - confirm there are no hollow glyphs;
     - confirm each `fontWeight` line matches its `fontVariations` line (real weights, not fake bold);
     - confirm every metrics row says `MATCH`;
     - confirm the w300 row renders like w400.
  5. Run `fvm flutter test`.
- [ ] **Step 4:** Report the results and the commit checkpoints that remain open to the owner.

---

## Coverage map

| Design item | Task |
| --- | --- |
| Inputs, pinning | 1 |
| Selection rules 1–5 | 2, 5 (H6, IVS), 6 (rule 3 letters and signs) |
| H1 | 5 (copies), 11 (`locl` JAN) |
| H2 | 9, 11 (mark-to-base) |
| H3 | 6, 7 |
| H4 | 4, 8 |
| H5 | 10 |
| H6 | 5 |
| Weight axis, plateau, extrapolation | 3, 5, 8, 10, 12 |
| Vertical metrics | 12 |
| OpenType features | 11 |
| Flutter rendering decision | 15 (README), 16 |
| Naming and licensing | 12 |
| Deliverables | 1, 5, 12, 15 |
| Acceptance 1, 2, 4 | 5 (+ 12 for 4) |
| Acceptance 3 | 6 |
| Acceptance 5 | 6, 7, 8, 9, 10 |
| Acceptance 6 | 10 |
| Acceptance 7 | 11 |
| Acceptance 8 | 12 |
| Acceptance 9 | 13, 16 |
| Acceptance 10 | 14, 16 |
