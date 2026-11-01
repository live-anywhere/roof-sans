"""Acceptance 23: every Wanted glyph follows its independent 400 → 550 line."""

import pytest

from roofsans.sampling import WantedSampler

pytestmark = pytest.mark.acceptance


@pytest.mark.parametrize("wght", (100, 200, 300))
def test_wanted_light_extrapolation(wanted, ws, roof, ctx, wght):
    assert 100 <= ctx.light.wght <= 200
    assert len(ctx.light.clamped) <= 10
    assert all(ctx.light.wght < w <= 150 for w in ctx.light.clamped.values())
    sampler = WantedSampler(roof)
    bad = []
    worst = {kind: {"outline": (0, ""), "advance": (0, "")} for kind in ("simple", "composite")}
    for name in wanted.getGlyphOrder():
        # ws reads the input Wanted font, never ctx.ws (which already has light tuples).
        a, b = ws.outline(name, 400), ws.outline(name, 550)
        got = sampler.outline(name, wght)
        endpoint = ctx.light.clamped.get(name, ctx.light.wght)
        effective = 400 - (400 - wght) * (400 - endpoint) / 300
        k = (effective - 400) / 150
        expected = [(x + (u - x) * k, y + (v - y) * k)
                    for (x, y), (u, v) in zip(a.points, b.points)]
        assert got.end_pts == a.end_pts and got.flags == a.flags, name
        assert len(got.points) == len(expected), name
        error = max((abs(p[i] - q[i]) for p, q in zip(got.points, expected) for i in (0, 1)), default=0)
        adv = ws.advance(name, 400) + (ws.advance(name, 550) - ws.advance(name, 400)) * k
        advance_error = abs(sampler.advance(name, wght) - adv)
        kind = "composite" if wanted["glyf"][name].isComposite() else "simple"
        worst[kind]["outline"] = max(worst[kind]["outline"], (error, name))
        worst[kind]["advance"] = max(worst[kind]["advance"], (advance_error, name))
        # Component point rounding, IUP error, and rounded parent offsets accumulate.
        outline_tolerance = 1.5 if kind == "composite" else 1
        if error > outline_tolerance or advance_error > 1:
            bad.append((name, error, advance_error))
    print(f"WANTED_LIGHT wght={wght} E={ctx.light.wght} clamped={ctx.light.clamped} worst={worst}")
    assert not bad, f"{len(bad)} differ at {wght}: {bad[:20]}"


def test_wanted_gdef_rows_follow_the_line(wanted, roof, ctx):
    """Wanted Sans's GDEF rows (its kerning and anchors) continue their 400 → 550 movement to E
    at 100, move linearly in between, and keep every value above 400."""
    from fontTools.misc.roundTools import otRound
    from fontTools.varLib.varStore import VarStoreInstancer

    source, built = wanted["GDEF"].table.VarStore, roof["GDEF"].table.VarStore
    k = (ctx.light.wght - 400) / 150
    src = {t: VarStoreInstancer(source, wanted["fvar"].axes, {"wght": t}) for t in (0.25, 0.75, 1.0)}
    out = {t: VarStoreInstancer(built, roof["fvar"].axes, {"wght": t}) for t in (-1.0, -0.5, 0.25, 0.75, 1.0)}
    bad, moving = [], 0
    for outer, data in enumerate(source.VarData):
        for inner in range(len(data.Item)):
            index = (outer << 16) | inner
            light = otRound(src[0.25][index] * k)
            moving += light != 0
            if out[-1.0][index] != light or abs(out[-0.5][index] - light / 2) > 1e-9:
                bad.append((outer, inner, out[-1.0][index], light))
            bad.extend((outer, inner, t) for t in (0.25, 0.75, 1.0) if out[t][index] != src[t][index])
    assert moving > 100
    assert not bad, bad[:10]
