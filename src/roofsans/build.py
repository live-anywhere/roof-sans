"""Build RoofSansVariable.ttf from the pinned inputs (the roofsans-build CLI)."""

from __future__ import annotations

import argparse
import shutil
from collections import Counter
from pathlib import Path

from fontTools.ttLib import TTFont

from roofsans import features, finalize
from roofsans.assemble import drop_wanted_logo, insert, planned_cmap, planned_uvs, write_cmap
from roofsans.context import make_context
from roofsans.inputs import Inputs, ensure_inputs
from roofsans.rules import (
    c_hanzi,
    c_punct,
    h2_compose,
    h3_construct,
    h3_enclosed,
    h4_letters,
    h5_symbols,
    h6_copy,
    r3_fullwidth,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = Path("fonts/RoofSansVariable.ttf")

# Fixed order: a later rule may use glyphs an earlier one contributed.
CONTRIBUTORS = (
    h6_copy, r3_fullwidth, h4_letters, h5_symbols, h2_compose, h3_construct, h3_enclosed,
    c_hanzi, c_punct,
)


def build(out: Path, inputs: Inputs | None = None, chinese: bool = True) -> Path:
    inputs = inputs or ensure_inputs()
    ctx = make_context(inputs, chinese=chinese)
    h6_copy.copy_closure(ctx)
    ctx.cmap = planned_cmap(ctx)
    for module in CONTRIBUTORS:
        if not chinese and module in (c_hanzi, c_punct):
            continue
        for g in module.contribute(ctx):
            if g.name in ctx.contributed:
                raise ValueError(f"{module.__name__} contributes {g.name} twice")
            ctx.contributed[g.name] = g

    font = TTFont(inputs.wanted, recalcTimestamp=False)
    drop_wanted_logo(font)
    insert(font, list(ctx.contributed.values()))
    names = set(font.getGlyphOrder())
    missing = Counter(ctx.selection.rules[cp] for cp, g in ctx.cmap.items() if g not in names)
    if missing:
        detail = ", ".join(f"{rule}: {n}" for rule, n in sorted(missing.items()))
        raise ValueError(f"no glyph for {sum(missing.values())} planned code points ({detail})")
    write_cmap(font, ctx.cmap, planned_uvs(ctx))
    features.apply_features(font, ctx)
    finalize.finalize(font, ctx)

    out.parent.mkdir(parents=True, exist_ok=True)
    font.save(out)
    license_path = out.parent / "OFL.txt"
    finalize.write_license(license_path, ctx.inputs, chinese=chinese)
    if out.resolve() == (REPO_ROOT / DEFAULT_OUT).resolve():
        shutil.copyfile(license_path, REPO_ROOT / "OFL.txt")
    return out


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="roofsans-build", description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help=f"output font (default {DEFAULT_OUT})")
    parser.add_argument("--without-chinese", action="store_true", help="reproduce the pre-Chinese font")
    args = parser.parse_args(argv)
    print(build(args.out, chinese=not args.without_chinese))
