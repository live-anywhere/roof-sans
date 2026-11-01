# Agent notes for Roof Sans

This repository builds `fonts/RoofSansVariable.ttf`, a `wght` 100–1000 variable font made of Wanted Sans plus harmonized Pretendard JP glyphs, with Simplified Chinese hanzi and forms from Source Han Sans CN, and its web fonts in `dist/web/`. Read these before changing anything:

- `docs/ROOF_SANS_DESIGN.md`: what the font must be. It is the binding authority, including its Acceptance list and Anti-goals.
- `docs/ROOF_SANS_SIMPLIFIED_CHINESE_DESIGN.md`: the Simplified Chinese extension (rules C1–C3), its measurements, and Acceptance 11–20.
- `docs/ROOF_SANS_LIGHT_WEIGHTS_DESIGN.md`: the weights below 400 (rules L1–L5): Wanted Sans extrapolated from its own variation, and Acceptance 21–29.
- `docs/ROOF_SANS_BUILD_NOTES.md`: the decisions made while building it, the tolerances the tests use, and the measured values.
- `docs/ROOF_SANS_WEB_DISTRIBUTION.md`: the web build (one WOFF2 and the dynamic subset), how the split is made, and its known limits.
- `docs/ROOF_SANS_IMPLEMENTATION_PLAN.md`: the original task plan. Where it disagrees with the build notes, the build notes are current.

## Commands

Run every command from the repository root.

```sh
uv sync                                    # Python 3.12 and the pinned dependencies
uv run roofsans-fetch                      # download and verify the inputs into inputs/
uv run roofsans-fetch --from-refs refs     # or copy them from local upstream checkouts in refs/
uv run roofsans-build                      # write fonts/RoofSansVariable.ttf, fonts/OFL.txt, OFL.txt (about 40 s)
uv run roofsans-web                        # write dist/web/ from fonts/RoofSansVariable.ttf (about 40 s)
uv run pytest                              # unit and acceptance tests (builds into build/test/)
```

Narrower runs:

```sh
uv run pytest -m "not acceptance"                        # unit tests only; never reads or builds the font
uv run roofsans-build --out build/<name>/RoofSansVariable.ttf
uv run roofsans-build --without-light --out build/<name>/RoofSansVariable.ttf   # the 400–1000 font, byte-identical to before the light weights
ROOF_FONT=build/<name>/RoofSansVariable.ttf uv run pytest -m acceptance
ROOF_FONT=fonts/RoofSansVariable.ttf ROOF_WEB=build/<name>-web uv run pytest tests/acceptance/test_web_dist.py   # reuse a web build
```

The Flutter rendering check (design Acceptance 10) lives in `verify/flutter_specimen/`. Its own `README.md` lists its commands.

The specimen web page is built with `uv run python site/build_site.py --out build/site`. If a font change alters a number the page states, the script stops; update `site/specimen.html` and `PAGE_FACTS` in `site/build_site.py` together, and regenerate `site/languages.json` with Hyperglot when language support changes.

## Rules

- **No agent commits, stashes, or resets.** Do not run `git commit`, `git stash`, `git reset`, `git checkout`, `git switch`, or any other command that changes git state. The owner reviews and commits by hand.
- **`refs/` is never modified and never committed.** It holds upstream checkouts of Wanted Sans and Pretendard for reference and for `roofsans-fetch --from-refs`. It is git-ignored.
- **The build reads its inputs only from `inputs/`.** `roofsans-fetch` fills `inputs/` from the URLs and SHA-256 values in `inputs.lock.json`. Do not edit files in `inputs/` by hand, and do not point build code at `refs/`. Changing an input means changing `inputs.lock.json` on purpose and re-checking every measured value in the build notes.
- **Dependencies are pinned** with `==` in `pyproject.toml` and locked in `uv.lock`. Do not add or upgrade one without a reason recorded in the build notes. A fontTools upgrade can change the output bytes.
- **Wanted Sans glyphs must not change at 400–1000.** Any change to Wanted Sans's outlines, advances, variations, metrics, or feature behavior for code points it covers would make Roof Sans differ from Wanted Sans where it must match. `test_a01_wanted_identity.py` and `test_a07_features.py::test_wanted_behavior_unchanged` check this. Below 400 every Wanted Sans glyph follows its own 400 → 550 movement (`src/roofsans/light.py`); the only data the light weights add to Wanted Sans glyphs is one tuple on the region (−1, −1, 0) and one GDEF column on that region.
- **Overlap flags stay as the sources set them.** Do not clear `OVERLAP_SIMPLE` or `OVERLAP_COMPOUND` (see the design's "Flutter rendering" section).
- **The axis maximum stays ≤ 1000 and the range ≤ 1000.** Skia reads a variable font's `wght` value as the typeface weight only within those limits. The axis is 100–1000 (range 900).
- **Nothing at or above 400 changes with the light weights.** `roofsans-build --without-light` must stay byte-identical to the 400–1000 font (`test_a22_unchanged_above_400.py`), and `--without-light --without-chinese` to the pre-Chinese font (`test_a16_baseline.py`). A rule that adds a light master gets its locations through `ctx.locs(...)`, which drops t < 0 when the build has no light weights.
- **`dist/web/` is a build output of the committed font.** After any change to `fonts/RoofSansVariable.ttf`, run `uv run roofsans-web` and commit both. `test_committed_dist_matches_a_fresh_build` fails while `dist/web/` is stale. Without `ROOF_WEB`, the web tests build into `build/test-web/`.
- **The build is deterministic.** Two builds from the same inputs give the same SHA-256 (`test_build_determinism.py`). `fonts/RoofSansVariable.ttf` and `OFL.txt` are build outputs meant to be committed. The build also writes `fonts/OFL.txt`, a copy of `OFL.txt`; whether it is committed is the owner's decision. If a change alters the font, rebuild the default path and say so in your report, with the new SHA-256.

## The advance-measurement trap

Measure variable advances from the phantom points (`roofsans.sampling` does this) or from a `fontTools.varLib.instancer` instance. Never read `TTGlyphSet[name].width` before the glyph is drawn: until then that attribute returns the default `hmtx` advance, not the advance at the requested location. Wanted Sans's advances vary with weight. For example, `zero` is 1280 / 1373 / 1440 at 400 / 750 / 1000.

## Acceptance tests and parallel work

- Acceptance tests (`-m acceptance`) need a built font. With `ROOF_FONT` set they test that file. Without it, the `roof_path` fixture builds into `build/test/RoofSansVariable.ttf` first.
- `test_a22_unchanged_above_400.py` and `test_a16_baseline.py` build `--without-light` fonts into `build/test-nolight/` and `build/test-baseline/`. Point `ROOF_NOLIGHT` and `ROOF_BASELINE` at existing `--without-light` and `--without-light --without-chinese` builds to skip those builds.
- Every test that reads the built font is an acceptance test. `tests/conftest.py` adds the marker to any test that uses the `roof` or `roof_path` fixture. A test that reaches the font only through `static("roof", …)` must carry `@pytest.mark.acceptance` itself, because the hook cannot see that use.
- When several agents work at once, each one builds to its own path, for example `uv run roofsans-build --out build/<task>/RoofSansVariable.ttf`, and runs the acceptance tests with `ROOF_FONT` set to that file.
- While others are working, do not build to the default path `fonts/RoofSansVariable.ttf`, and do not use the shared `build/test/` path (a plain `uv run pytest` writes there).
- A default-path build also overwrites `OFL.txt` at the repository root.

## Where the code is

- `src/roofsans/selection.py` assigns every code point to one rule (`Rule`). Each rule has one module in `src/roofsans/rules/`. Each module's `contribute(ctx)` returns `NewGlyph` records.
- `src/roofsans/build.py` runs the contributors in a fixed order (`h6_copy`, `r3_fullwidth`, `h4_letters`, `h5_symbols`, `h2_compose`, `h3_construct`, `h3_enclosed`, `c_hanzi`, `c_punct`). A later rule may use glyphs an earlier one contributed. The build fails if any planned code point has no glyph.
- `src/roofsans/light.py` solves the Wanted Sans light tuples (its extrapolation weight E and the glyphs it clamps). `make_context` adds them to Wanted Sans in memory before any rule runs, so rules read Wanted Sans down to 100; `build.py` adds the same data to the output font.
- `src/roofsans/features/` adds the OpenType data; `src/roofsans/finalize.py` writes names, `head`, `OS/2`, and the license text.
- `src/roofsans/web.py` splits the built font for the web (`roofsans-web`). It reads only the font and the `slices_*` inputs.
- Unit tests are in `tests/unit/`; acceptance tests, numbered by the design's Acceptance items, are in `tests/acceptance/`.

When a decision changes what the font contains or how it is checked, record it in `docs/ROOF_SANS_BUILD_NOTES.md` with the reason and the measured numbers.
