# Agent notes for Roof Sans

This repository builds `fonts/RoofSansVariable.ttf`, a `wght` 400–1000 variable font made of Wanted Sans plus harmonized Pretendard JP glyphs, with Simplified Chinese hanzi and forms from Source Han Sans CN, and its web fonts in `dist/web/`. Read these before changing anything:

- `docs/ROOF_SANS_DESIGN.md`: what the font must be. It is the binding authority, including its Acceptance list and Anti-goals.
- `docs/ROOF_SANS_SIMPLIFIED_CHINESE_DESIGN.md`: the Simplified Chinese extension (rules C1–C3), its measurements, and Acceptance 11–20.
- `docs/ROOF_SANS_BUILD_NOTES.md`: the decisions made while building it, the tolerances the tests use, and the measured values.
- `docs/ROOF_SANS_WEB_DISTRIBUTION.md`: the web build (one WOFF2 and the dynamic subset), how the split is made, and its known limits.
- `docs/ROOF_SANS_IMPLEMENTATION_PLAN.md`: the original task plan. Where it disagrees with the build notes, the build notes are current.

## Commands

Run every command from the repository root.

```sh
uv sync                                    # Python 3.12 and the pinned dependencies
uv run roofsans-fetch                      # download and verify the inputs into inputs/
uv run roofsans-fetch --from-refs refs     # or copy them from local upstream checkouts in refs/
uv run roofsans-build                      # write fonts/RoofSansVariable.ttf, fonts/OFL.txt, OFL.txt
uv run roofsans-web                        # write dist/web/ from fonts/RoofSansVariable.ttf (about 40 s)
uv run pytest                              # unit and acceptance tests (builds into build/test/)
```

Narrower runs:

```sh
uv run pytest -m "not acceptance"                        # unit tests only; never reads or builds the font
uv run roofsans-build --out build/<name>/RoofSansVariable.ttf
ROOF_FONT=build/<name>/RoofSansVariable.ttf uv run pytest -m acceptance
ROOF_FONT=fonts/RoofSansVariable.ttf ROOF_WEB=build/<name>-web uv run pytest tests/acceptance/test_web_dist.py   # reuse a web build
```

The Flutter rendering check (design Acceptance 10) lives in `verify/flutter_specimen/`. Its own `README.md` lists its commands.

The specimen web page is built with `uv run python site/build_site.py --out build/site` and served from that folder (it loads `RoofSansVariable.woff2` by a relative URL, so open it through `uv run python -m http.server -d build/site`, not as a file). `.github/workflows/pages.yml` builds it on pushes to `dev` and `main` and deploys it to GitHub Pages from `main` (<https://live-anywhere.github.io/roof-sans/>). If a font change alters a number the page states, the script stops and the workflow fails; update `site/specimen.html` and `PAGE_FACTS` in `site/build_site.py` together, and regenerate `site/languages.json` with Hyperglot when language support changes. The script also stops when the font's GSUB/GPOS feature tags differ from the `data-feature` attributes of the page's OpenType features tab; describe an added feature there (and check its sample with HarfBuzz) or remove a dropped one.

## Rules

- **No agent commits, stashes, or resets.** Do not run `git commit`, `git stash`, `git reset`, `git checkout`, `git switch`, or any other command that changes git state. The owner reviews and commits by hand.
- **`refs/` is never modified and never committed.** It holds upstream checkouts of Wanted Sans and Pretendard for reference and for `roofsans-fetch --from-refs`. It is git-ignored.
- **The build reads its inputs only from `inputs/`.** `roofsans-fetch` fills `inputs/` from the URLs and SHA-256 values in `inputs.lock.json`. Do not edit files in `inputs/` by hand, and do not point build code at `refs/`. Changing an input means changing `inputs.lock.json` on purpose and re-checking every measured value in the build notes.
- **Dependencies are pinned** with `==` in `pyproject.toml` and locked in `uv.lock`. Do not add or upgrade one without a reason recorded in the build notes. A fontTools upgrade can change the output bytes.
- **Wanted Sans glyphs must not change.** Any change to Wanted Sans's outlines, advances, variations, metrics, or feature behavior for code points it covers would make Roof Sans differ from Wanted Sans where it must match. `test_a01_wanted_identity.py` and `test_a07_features.py::test_wanted_behavior_unchanged` check this. The one exception is Wanted Sans's logo (U+F0000–F0003) and its `liga`, which 1.3.0 removed because the logo is Wanted Lab's trademark (build notes section 15).
- **License notices stay complete.** The font is SIL OFL 1.1: `OFL.txt` and name IDs 0 and 7 keep every upstream copyright line and trademark notice, plus LiveAnywhere's line. The build writes them (`finalize.py`); do not edit `OFL.txt` by hand. The build code, tests, site, and docs are MIT (`LICENSE`). Do not ship another company's logo or trademark glyph.
- **Overlap flags stay as the sources set them.** Do not clear `OVERLAP_SIMPLE` or `OVERLAP_COMPOUND` (see the design's "Flutter rendering" section).
- **No weights below 400.** Roof Sans 1.1.0 added 100–399 and 1.2.0 removed them: only 400 and above is used, and they made every file about a third larger. Do not bring them back without the owner's decision; the code is at tag `v1.1.0` (build notes section 14).
- **The axis maximum stays ≤ 1000 and the range ≤ 1000.** Skia reads a variable font's `wght` value as the typeface weight only within those limits.
- **`dist/web/` is a build output of the committed font.** After any change to `fonts/RoofSansVariable.ttf`, run `uv run roofsans-web` and commit both. `test_committed_dist_matches_a_fresh_build` fails while `dist/web/` is stale. Without `ROOF_WEB`, the web tests build into `build/test-web/`.
- **The build is deterministic.** Two builds from the same inputs give the same SHA-256 (`test_build_determinism.py`). `fonts/RoofSansVariable.ttf` and `OFL.txt` are build outputs meant to be committed. The build also writes `fonts/OFL.txt`, a copy of `OFL.txt`; it is committed too, and `roofsans-web` copies it into `dist/web/`. If a change alters the font, rebuild the default path and say so in your report, with the new SHA-256.

## The advance-measurement trap

Measure variable advances from the phantom points (`roofsans.sampling` does this) or from a `fontTools.varLib.instancer` instance. Never read `TTGlyphSet[name].width` before the glyph is drawn: until then that attribute returns the default `hmtx` advance, not the advance at the requested location. Wanted Sans's advances vary with weight. For example, `zero` is 1280 / 1373 / 1440 at 400 / 750 / 1000.

## Acceptance tests and parallel work

- Acceptance tests (`-m acceptance`) need a built font. With `ROOF_FONT` set they test that file. Without it, the `roof_path` fixture builds into `build/test/RoofSansVariable.ttf` first.
- Every test that reads the built font is an acceptance test. `tests/conftest.py` adds the marker to any test that uses the `roof` or `roof_path` fixture. A test that reaches the font only through `static("roof", …)` must carry `@pytest.mark.acceptance` itself, because the hook cannot see that use.
- When several agents work at once, each one builds to its own path, for example `uv run roofsans-build --out build/<task>/RoofSansVariable.ttf`, and runs the acceptance tests with `ROOF_FONT` set to that file.
- While others are working, do not build to the default path `fonts/RoofSansVariable.ttf`, and do not use the shared `build/test/` path (a plain `uv run pytest` writes there).
- A default-path build also overwrites `OFL.txt` at the repository root.

## Where the code is

- `src/roofsans/selection.py` assigns every code point to one rule (`Rule`). Each rule has one module in `src/roofsans/rules/`. Each module's `contribute(ctx)` returns `NewGlyph` records.
- `src/roofsans/build.py` removes Wanted Sans's logo from the base font (`assemble.drop_wanted_logo`), then runs the contributors in a fixed order (`h6_copy`, `r3_fullwidth`, `h4_letters`, `h5_symbols`, `h2_compose`, `h3_construct`, `h3_enclosed`, `c_hanzi`, `c_punct`). A later rule may use glyphs an earlier one contributed. The build fails if any planned code point has no glyph.
- `src/roofsans/features/` adds the OpenType data; `src/roofsans/finalize.py` writes names, `head`, `OS/2`, and the license text.
- `src/roofsans/web.py` splits the built font for the web (`roofsans-web`). It reads only the font, the `OFL.txt` next to it, and the `slices_*` inputs.
- Unit tests are in `tests/unit/`; acceptance tests, numbered by the design's Acceptance items, are in `tests/acceptance/`.

When a decision changes what the font contains or how it is checked, record it in `docs/ROOF_SANS_BUILD_NOTES.md` with the reason and the measured numbers.
