from roofsans.rules.h6_copy import contribute, copy_closure
from roofsans.selection import JAN_SHARED


def test_closure_renames_and_plateaus(ctx):
    names = copy_closure(ctx)
    assert names["uni300C"] == "uni300C.pj" and names["uni6F22"] == "uni6F22"
    assert all(names[n] for n in ("uni4E73.loclJAN", "uni30AC.varAlt01", "uni4E08.uv018"))
    g = {x.name: x for x in contribute(ctx)}["uni6F22"]
    assert {tuple(round(v, 4) for v in tv.axes["wght"]) for tv in g.variations} == {(0.0, 0.8834, 1.0), (0.8834, 1.0, 1.0)}


def test_closure_covers_jan_shared_and_components(ctx):
    names = copy_closure(ctx)
    pcmap = ctx.pretendard.getBestCmap()
    assert all(names[pcmap[cp]].endswith(".pj") for cp in JAN_SHARED) and len(JAN_SHARED) == 13
    copies = {g.name: g for g in contribute(ctx)}
    assert set(copies) == set(names.values())
    for g in copies.values():
        if g.glyph.isComposite():
            assert all(c.glyphName in copies for c in g.glyph.components), g.name
