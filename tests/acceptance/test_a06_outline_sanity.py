"""Acceptance 6: harmonized glyphs keep their sources' contour structure at every weight."""

from collections import Counter

import pytest
from sectors import Verdict, interpolate, judge_crossings

from roofsans.axis import H4_LOCS, roof_norm
from roofsans.outline import Outline
from roofsans.rules import h4_letters
from roofsans.rules.h3_enclosed import SUPSUB
from roofsans.rules.h5_symbols import symbol_transform
from roofsans.sanity import check_outline
from roofsans.selection import Rule

pytestmark = pytest.mark.acceptance

# Acceptance 5's weights, 930 (Pretendard JP's master), and every master: H4 and H5 at
# 400/700/850/1000, the sup/sub signs at Wanted Sans's 400/750/1000.
WEIGHTS = (400, 550, 700, 750, 850, 930, 1000)
RULES = (Rule.H4_LETTER, Rule.H5_SYMBOL, Rule.H3_SUPSUB)


def instance_outline(font, name: str) -> Outline:
    glyf = font["glyf"]
    coords, end_pts, flags = glyf[name].getCoordinates(glyf)
    return Outline([tuple(p) for p in coords] + [(0, 0)] * 4, list(end_pts), list(flags))


def sources(ctx, rule: Rule, cp: int, wght: float) -> tuple[Outline, Outline]:
    """The glyph's source at 400 and at the weight the build sampled it at for ``wght`` (R24)."""
    if rule is Rule.H3_SUPSUB:
        name = SUPSUB[cp][0]
        return ctx.ws.outline(name, 400), ctx.ws.outline(name, wght)
    if rule is Rule.H4_LETTER:
        sampled = {t: p.w_prime for t, p in h4_letters.params(ctx).items()}
    else:
        sampled = {t: symbol_transform(ctx, cp, t).sample_wght for t in H4_LOCS}
    name = ctx.pretendard.getBestCmap()[cp]
    return ctx.ps.outline(name, 400), ctx.ps.outline(name, interpolate(sampled, roof_norm(wght)))


def sanity(candidate: Outline, at_400: Outline, sampled: Outline) -> Verdict:
    """Acceptance 6 verdict on ``candidate`` (R24 and its clarification).

    Contour count, orientation, and counter area are judged against the source at 400.
    A crossing the source has at 400 or at the sampled weight is not judged; crossings are
    matched by flattened edge indices, since every rule here keeps the source's points and
    flags while moving them (see ``judge_crossings``).
    """
    verdict = judge_crossings(candidate, [at_400, sampled])
    verdict.failures[:0] = [m for m in check_outline(candidate, at_400) if "self-intersects" not in m]
    return verdict


@pytest.mark.parametrize("wght", WEIGHTS)
def test_harmonized_outlines_are_sane(static, roof, ctx, wght):
    font, cmap = static("roof", wght), roof.getBestCmap()
    bad, accepted, allowed, matched, failed = [], Counter(), [], 0, 0
    for rule in RULES:
        for cp in ctx.selection.codepoints(rule):
            glyph = f"U+{cp:04X} {chr(cp)}"
            verdict = sanity(instance_outline(font, cmap[cp]), *sources(ctx, rule, cp, wght))
            matched += verdict.matched
            if verdict.failures:
                bad.append((glyph, rule.value, verdict.failures))
                failed += sum("sectors" in f for f in verdict.failures)
            if verdict.accepted:
                accepted[glyph] = verdict.accepted
            allowed.extend(f"{glyph} {fold}" for fold in verdict.allowed)
    print(f"{wght}: source crossings matched: {matched}")
    print(f"{wght}: new same-sign crossings accepted (R24): {sum(accepted.values())} in {len(accepted)} glyphs")
    for glyph, count in sorted(accepted.items()):
        print(f"  {glyph}: {count}")
    print(f"{wght}: counter folds allowed (R24 open-counter allowance): {len(allowed)}")
    for fold in allowed:
        print(f"  {fold}")
    print(f"{wght}: failed crossings: {failed}; failed glyphs: {len(bad)}")
    assert not bad, f"{len(bad)} glyphs fail at {wght}: {bad}"
