"""Build the web fonts: one WOFF2 file and a dynamic subset.

The dynamic subset splits the font into WOFF2 files that each hold a disjoint set of
code points, and writes one CSS file with an ``@font-face`` rule per file. Each rule
lists its code points in ``unicode-range``, so a browser downloads only the files
that hold characters on the page.

Shaping rules work only inside one file. A browser shapes each run of characters
with the file that holds them, so a contextual rule, ligature, mark attachment, or
kerning pair whose characters land in different files does not apply. The fixed
groups below keep the rules that matter for Latin text in one file; the rest of the
split follows Google Fonts' frequency-based slicing for Japanese, Korean, and
Simplified Chinese. ``docs/ROOF_SANS_WEB_DISTRIBUTION.md`` lists the known limits.
"""

from __future__ import annotations

import argparse
import io
import os
import re
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

from roofsans.inputs import ensure_files

FAMILY = "Roof Sans"
DEFAULT_FONT = Path("fonts/RoofSansVariable.ttf")
DEFAULT_OUT = Path("dist/web")
FULL_CSS = "roofsans.css"
SUBSET_CSS = "roofsans-dynamic-subset.css"
FULL_WOFF2 = "woff2/RoofSansVariable.woff2"
SUBSET_DIR = "woff2-dynamic-subset"
SUBSET_NAME = "RoofSansVariable.subset.{index}.woff2"
# The license roofsans-build writes next to the font; the web files ship with a copy of it.
LICENSE_NAME = "OFL.txt"

# Code points the slicings did not place go into chunks of at most this many.
LEFTOVER_SIZE = 100
# A slicing subset with fewer unclaimed code points than this is merged with the next one.
MIN_CHUNK = 40

# Google Fonts slicings in the order they claim code points. Japanese goes first so
# kana and the default (Japanese) Han forms follow Japanese frequency; Korean then
# places Hangul and the remaining hanja, and Simplified Chinese the remaining hanzi.
SLICING_ORDER = ("slices_ja", "slices_ko", "slices_zhs")
SLICING_LABELS = {"slices_ja": "ja", "slices_ko": "ko", "slices_zhs": "zhs"}


def _span(*items: int | tuple[int, int]) -> frozenset[int]:
    out: set[int] = set()
    for item in items:
        first, last = item if isinstance(item, tuple) else (item, item)
        out.update(range(first, last + 1))
    return frozenset(out)


# Each code point goes to the first group that lists it; code points the font lacks
# are dropped. "latin" is Google Fonts' latin subset plus every combining diacritical
# mark (U+0300–036F), so marks attach to Basic Latin and Latin-1 bases in one file.
# It also holds U+2018–201D and U+00B7 with the letters around them, which the
# Simplified Chinese quote rule (features/gsub.py, _zhs_quotes) reads as context.
FIXED_GROUPS: tuple[tuple[str, frozenset[int]], ...] = (
    ("latin", _span(
        (0x0000, 0x00FF), 0x0131, (0x0152, 0x0153), (0x02BB, 0x02BC), 0x02C6, 0x02DA, 0x02DC,
        (0x0300, 0x036F), (0x2000, 0x206F), 0x20AC, 0x2122, 0x2191, 0x2193, 0x2212, 0x2215,
        0xFEFF, 0xFFFD,
    )),
    ("latin-ext", _span(
        (0x0100, 0x02FF), (0x1D00, 0x1DBF), (0x1E00, 0x1EFF), (0x20A0, 0x20CF),
        (0x2C60, 0x2C7F), (0xA720, 0xA7FF), (0xAB30, 0xAB6F),
    )),
    ("greek", _span((0x0370, 0x03FF), (0x1F00, 0x1FFF))),
    ("cyrillic", _span((0x0400, 0x052F), (0x1C80, 0x1C8F), (0x2DE0, 0x2DFF), (0xA640, 0xA69F))),
    # Superscripts and subscripts, the rest of the currency signs, combining marks for symbols.
    ("symbols-2070", _span((0x2070, 0x20FF))),
    # Letterlike symbols, number forms, arrows.
    ("symbols-2100", _span((0x2100, 0x21FF))),
    # Mathematical operators, miscellaneous technical.
    ("symbols-2200", _span((0x2200, 0x23FF))),
    # Control pictures, OCR, enclosed alphanumerics.
    ("symbols-2400", _span((0x2400, 0x24FF))),
    # Box drawing to supplemental punctuation.
    ("symbols-2500", _span((0x2500, 0x2E7F))),
)


@dataclass(frozen=True)
class Chunk:
    """One WOFF2 file of the dynamic subset."""

    source: str  # the group or slice that claimed these code points, e.g. "latin", "ko 17"
    codepoints: tuple[int, ...]


def parse_slicing(text: str) -> list[list[int]]:
    """Return the subsets of a Google Fonts slicing strategy (a text proto), in file order."""
    subsets: list[list[int]] = []
    current: list[int] | None = None
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line == "subsets {" and current is None:
            current = []
        elif line == "}" and current is not None:
            subsets.append(current)
            current = None
        elif current is not None and (m := re.fullmatch(r"codepoints: (\d+)", line)):
            current.append(int(m.group(1)))
        else:
            raise ValueError(f"unexpected line in slicing file: {raw!r}")
    if current is not None:
        raise ValueError("slicing file ends inside a subset")
    return subsets


def plan_chunks(codepoints: set[int], slicings: list[tuple[str, list[list[int]]]]) -> list[Chunk]:
    """Split ``codepoints`` into disjoint chunks: fixed groups, then slicings, then leftovers."""
    remaining = set(codepoints)
    chunks: list[Chunk] = []

    def take(source: str, wanted) -> None:
        got = remaining.intersection(wanted)
        if got:
            remaining.difference_update(got)
            chunks.append(Chunk(source, tuple(sorted(got))))

    for name, group in FIXED_GROUPS:
        take(name, group)
    for label, subsets in slicings:
        # A subset an earlier slicing mostly claimed leaves a remnant; merge remnants with
        # the next subsets of the same slicing (neighbours in frequency) up to MIN_CHUNK.
        pending: list[int] = []
        first = 0
        for index, cps in enumerate(subsets):
            if not pending:
                first = index
            pending.extend(cp for cp in cps if cp in remaining)
            if len(pending) >= MIN_CHUNK:
                take(f"{label} {first}" if first == index else f"{label} {first}-{index}", pending)
                pending = []
        if pending:
            last = len(subsets) - 1
            take(f"{label} {first}" if first == last else f"{label} {first}-{last}", pending)
    leftover = sorted(remaining)
    for start in range(0, len(leftover), LEFTOVER_SIZE):
        take(f"leftover {start // LEFTOVER_SIZE}", leftover[start:start + LEFTOVER_SIZE])
    return chunks


def unicode_range(codepoints) -> str:
    """CSS ``unicode-range`` value for ``codepoints``, with runs merged into ranges."""
    spans: list[list[int]] = []
    for cp in sorted(codepoints):
        if spans and cp == spans[-1][1] + 1:
            spans[-1][1] = cp
        else:
            spans.append([cp, cp])
    return ", ".join(f"U+{a:x}" if a == b else f"U+{a:x}-{b:x}" for a, b in spans)


def parse_unicode_range(value: str) -> set[int]:
    """Inverse of ``unicode_range`` (no wildcards)."""
    out: set[int] = set()
    for part in value.split(","):
        first, _, last = part.strip().removeprefix("U+").partition("-")
        out.update(range(int(first, 16), int(last or first, 16) + 1))
    return out


def font_face(url: str, weight: str, codepoints=None) -> str:
    lines = [
        "@font-face {",
        f"  font-family: '{FAMILY}';",
        "  font-style: normal;",
        f"  font-weight: {weight};",
        "  font-display: swap;",
        f"  src: url('{url}') format('woff2');",
    ]
    if codepoints is not None:
        lines.append(f"  unicode-range: {unicode_range(codepoints)};")
    lines.append("}")
    return "\n".join(lines) + "\n"


def _header(font: TTFont, kind: str) -> str:
    version = font["name"].getDebugName(5)
    return (
        f"/* {FAMILY} ({version}), {kind}. Generated by roofsans-web from "
        f"{DEFAULT_FONT.as_posix()}; do not edit by hand.\n"
        f" * Licensed under the SIL Open Font License 1.1; see {LICENSE_NAME}. */\n"
    )


def _weight_range(font: TTFont) -> str:
    axis = next(a for a in font["fvar"].axes if a.axisTag == "wght")
    return f"{axis.minValue:g} {axis.maxValue:g}"


def _subset_options() -> subset.Options:
    options = subset.Options()
    options.layout_features = ["*"]
    options.layout_scripts = ["*"]
    options.name_IDs = ["*"]
    options.name_languages = ["*"]
    options.name_legacy = True
    options.notdef_outline = True
    options.glyph_names = True  # keeps chunks comparable with the full font by glyph name
    options.legacy_kern = True
    return options


def _woff2_bytes(font: TTFont) -> bytes:
    font.flavor = "woff2"
    buffer = io.BytesIO()
    font.save(buffer)
    return buffer.getvalue()


def subset_woff2(font_path: Path, codepoints) -> bytes:
    """A WOFF2 subset of ``font_path`` holding ``codepoints`` and every glyph their rules reach."""
    font = TTFont(font_path, recalcTimestamp=False)
    subsetter = subset.Subsetter(_subset_options())
    subsetter.populate(unicodes=sorted(codepoints))
    subsetter.subset(font)
    return _woff2_bytes(font)


def _subset_job(job: tuple[str, tuple[int, ...]]) -> bytes:
    font_path, codepoints = job
    return subset_woff2(Path(font_path), codepoints)


def variation_selectors(font: TTFont) -> dict[int, set[int]]:
    """Base code point → the variation selectors the font's format 14 cmap pairs with it."""
    out: dict[int, set[int]] = {}
    for table in font["cmap"].tables:
        if table.format == 14:
            for selector, entries in table.uvsDict.items():
                for base, _ in entries:
                    out.setdefault(base, set()).add(selector)
    return out


def subset_request(chunk: Chunk, selectors: dict[int, set[int]]) -> tuple[int, ...]:
    """The code points to subset for ``chunk``: its own, plus the variation selectors of its bases.

    fontTools keeps a variation sequence only when both the base and the selector are
    requested. The selectors are not in the CSS ``unicode-range``: a browser shapes a
    selector with the font of the character before it.
    """
    extra = set().union(*(selectors.get(cp, ()) for cp in chunk.codepoints))
    return tuple(sorted(set(chunk.codepoints) | extra))


@dataclass(frozen=True)
class WebBuild:
    out_dir: Path
    chunks: list[Chunk]
    files: list[Path]  # every file written, relative to out_dir


def load_slicings(paths: dict[str, Path]) -> list[tuple[str, list[list[int]]]]:
    return [(SLICING_LABELS[key], parse_slicing(paths[key].read_text(encoding="utf-8"))) for key in SLICING_ORDER]


def build_web(
    font_path: Path, slicings: list[tuple[str, list[list[int]]]], out_dir: Path, jobs: int | None = None
) -> WebBuild:
    """Write the full WOFF2, the dynamic subset, their CSS files, and the license under ``out_dir``."""
    license_path = font_path.parent / LICENSE_NAME
    if not license_path.is_file():
        raise FileNotFoundError(f"{license_path} is missing; roofsans-build writes it next to the font")
    font = TTFont(font_path, recalcTimestamp=False)
    weight = _weight_range(font)
    chunks = plan_chunks(set(font.getBestCmap()), slicings)

    subset_dir = out_dir / SUBSET_DIR
    subset_dir.mkdir(parents=True, exist_ok=True)
    for stale in subset_dir.glob("*.woff2"):
        stale.unlink()
    (out_dir / FULL_WOFF2).parent.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    (out_dir / FULL_WOFF2).write_bytes(_woff2_bytes(TTFont(font_path, recalcTimestamp=False)))
    written.append(Path(FULL_WOFF2))

    selectors = variation_selectors(font)
    work = [(str(font_path), subset_request(chunk, selectors)) for chunk in chunks]
    with ProcessPoolExecutor(max_workers=jobs or os.cpu_count()) as pool:
        blobs = list(pool.map(_subset_job, work))
    faces = []
    for index, (chunk, blob) in enumerate(zip(chunks, blobs)):
        rel = Path(SUBSET_DIR) / SUBSET_NAME.format(index=index)
        (out_dir / rel).write_bytes(blob)
        written.append(rel)
        faces.append(f"/* [{index}] {chunk.source} */\n" + font_face(f"./{rel.as_posix()}", weight, chunk.codepoints))

    full_css = _header(font, "single file") + font_face(f"./{FULL_WOFF2}", weight)
    subset_css = _header(font, f"dynamic subset in {len(chunks)} files") + "".join(faces)
    for name, text in ((FULL_CSS, full_css), (SUBSET_CSS, subset_css)):
        (out_dir / name).write_text(text, encoding="utf-8", newline="\n")
        written.append(Path(name))
    (out_dir / LICENSE_NAME).write_bytes(license_path.read_bytes())
    written.append(Path(LICENSE_NAME))
    return WebBuild(out_dir, chunks, written)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="roofsans-web", description=__doc__.split("\n\n")[0])
    parser.add_argument("--font", type=Path, default=DEFAULT_FONT, help="built font to split")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output directory")
    parser.add_argument("--jobs", type=int, default=None, help="parallel subset processes")
    args = parser.parse_args(argv)
    slicings = load_slicings(ensure_files(set(SLICING_ORDER)))
    result = build_web(args.font, slicings, args.out, args.jobs)
    sizes = [(args.out / f).stat().st_size for f in result.files if f.parent.name == SUBSET_DIR]
    print(f"{args.out}: {len(result.chunks)} subset files, {sum(sizes):,} bytes in total, "
          f"largest {max(sizes):,} bytes")


if __name__ == "__main__":
    main()
