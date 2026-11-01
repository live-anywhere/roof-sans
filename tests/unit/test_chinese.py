import pytest

from roofsans.chinese import gb2312_hanzi, gb2312_levels
from roofsans.selection import Rule, select


def test_gb2312_counts():
    a, b = gb2312_levels()
    assert (len(a), len(b), len(gb2312_hanzi())) == (3755, 3008, 6763)
    assert gb2312_hanzi() == tuple(sorted(set(a) | set(b)))
    assert all(0x4E00 <= cp <= 0x9FFF for cp in gb2312_hanzi())


def test_c1_selection(wanted, pretendard, shs_cn):
    s = select(wanted, pretendard, shs_cn)
    c1 = set(s.codepoints(Rule.C1_HANZI))
    assert len(c1) == 3260
    assert [len(c1 & set(level)) for level in gb2312_levels()] == [1335, 1925]
    assert not c1 & (wanted.getBestCmap().keys() | pretendard.getBestCmap().keys())
    assert c1 <= shs_cn.getBestCmap().keys()


def test_select_rejects_missing_source(wanted, pretendard, shs_cn):
    cmap = dict(shs_cn.getBestCmap())
    cp = next(cp for cp in gb2312_hanzi() if cp not in wanted.getBestCmap() and cp not in pretendard.getBestCmap())
    del cmap[cp]
    class Missing:
        def getBestCmap(self):
            return cmap
    with pytest.raises(ValueError, match=f'U\\+{cp:04X}'):
        select(wanted, pretendard, Missing())
