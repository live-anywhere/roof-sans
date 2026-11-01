"""Acceptance 14: ZHS localization and unchanged behavior in all previous locales."""

import importlib.util
from collections import Counter
from pathlib import Path
from functools import cache
import sys

import pytest
from fontTools.ttLib import TTFont

from test_a07_features import shape
from roofsans.chinese import gb2312_hanzi
from roofsans.rules.c_hanzi import zhs_forms
from roofsans.rules.c_punct import ZHS_QUOTES, ZHS_SIGNS
from roofsans.selection import JAN_SHARED
from roofsans.rules.h6_copy import copy_closure

pytestmark = pytest.mark.acceptance

# Pinned from the reviewed input cmap: 199 aliases of the C2 source glyphs.
NON_GB_SHARED_C2 = tuple(int(cp, 16) for cp in """
2E8E 2E93 2E9F 2EA0 2EC4 2EDD
2F07 2F08 2F0A 2F0B 2F10 2F15 2F1B 2F1C 2F25 2F26 2F27 2F2B 2F2D 2F33 2F34 2F35
2F38 2F3C 2F40 2F41 2F42 2F44 2F45 2F46 2F4B 2F4D 2F4E 2F4F 2F50 2F52 2F54 2F55
2F56 2F57 2F59 2F5E 2F60 2F61 2F74 2F77 2F78 2F79 2F7A 2F7E 2F82 2F84 2F85 2F88
2F89 2F8A 2F8D 2F90 2F93 2F94 2F95 2F96 2F97 2F98 2F9A 2F9D 2F9F 2FA0 2FA2 2FA3
2FA6 2FAA 2FAB 2FAE 2FB3 2FBB 2FBC 2FBD 2FC0 2FC1 2FC5 2FC9 2FCB 2FCD 2FCE 2FCF 2FD5
F904 F909 F90A F911 F912 F916 F91C F925 F928 F929 F92A F92B F92C F92E F93B F940 F946 F94F
F951 F955 F958 F959 F960 F961 F968 F96A F96C F96D F971 F973 F975 F977 F979 F97C F981 F983
F989 F99C F99D F99E F99F F9A0 F9A2 F9A3 F9A4 F9A8 F9A9 F9AC F9AD F9AF F9B0 F9B2 F9B5
F9BA F9BC F9C2 F9C9 F9CA F9CB F9CC F9CD F9CE F9D1 F9D2 F9DA F9DB F9DC F9E1 F9E5 F9E6
F9EB F9EC F9ED F9F3 F9F7 F9F8 F9F9 F9FB F9FE
FA00 FA01 FA03 FA04 FA0B FA17 FA19 FA1A FA1B FA1C FA30 FA31 FA33 FA34 FA35 FA38 FA3A FA3D
FA3F FA41 FA44 FA45 FA4B FA4C FA4D FA4E FA50 FA51 FA55 FA59 FA5C FA60 FA67
""".split())


def names(path, text, **kw):
    return [g[0] for g in shape(path, text, **kw)]


def test_zhs_language_tags(roof_path):
    enabled = {'zh', 'zh-CN', 'zh-Hans', 'zh-SG'}
    for language in ('zh', 'zh-CN', 'zh-Hans', 'zh-SG', 'zh-TW', 'zh-HK', 'zh-Hant', 'ja', 'ko', None):
        actual = names(roof_path, '直', language=language)
        print('ZHS_LANGUAGE', language, actual)
        assert (actual == ['uni76F4.zhs']) == (language in enabled), (language, actual)


def test_zhs_switches(ctx, roof_path):
    pj_names = copy_closure(ctx)
    points = zhs_forms(ctx)
    assert names(roof_path, ''.join(map(chr, points)), language='zh-CN', script='Hani') == [
        f'uni{cp:04X}.zhs' for cp in points]
    for script in ('Hani', 'Latn', 'DFLT'):
        assert names(roof_path, ''.join(map(chr, JAN_SHARED)), language='zh-CN', script=script) == [
            pj_names[ctx.pretendard.getBestCmap()[cp]] for cp in JAN_SHARED]
        assert names(roof_path, ''.join(map(chr, ZHS_SIGNS)), language='zh-CN', script=script) == [
            f'uni{cp:04X}.zhs' for cp in ZHS_SIGNS]
    assert names(roof_path, '“中”', language='zh-CN', script='Hani')[::2] == ['uni201C.zhs', 'uni201D.zhs']
    quotes = ''.join(map(chr, ZHS_QUOTES))
    assert names(roof_path, quotes, language='zh-CN', script='Hani') == [f'uni{cp:04X}.zhs' for cp in ZHS_QUOTES]
    assert names(roof_path, quotes, language='zh-CN', script='Latn') == [f'uni{cp:04X}.zhs' for cp in ZHS_QUOTES]
    assert names(roof_path, '“abc”', language='zh-CN', script='Latn')[::4] == ['uni201C.zhs', 'uni201D.zhs']
    latin = names(roof_path, 'ID「abc」', language='zh-CN', script='Latn')
    assert 'uni300C.pj' in latin and 'uni300D.pj' in latin


def test_zhs_shared_non_gb_codepoints(roof, roof_path):
    cmap = roof.getBestCmap()
    mapping = roof['GSUB'].table.LookupList.Lookup[99].SubTable[0].mapping
    gb = set(gb2312_hanzi())
    shared = {cp for cp, glyph in cmap.items() if cp not in gb and glyph in mapping}
    assert shared == set(NON_GB_SHARED_C2)
    assert len(shared) == 199
    assert Counter(cp >> 8 for cp in shared) == {0x2E: 6, 0x2F: 81, 0xF9: 79, 0xFA: 33}
    for cp in NON_GB_SHARED_C2:
        assert names(roof_path, chr(cp), language='zh-CN', script='Hani') == [mapping[cmap[cp]]]
        for language in ('ja', 'ko', None):
            assert not any(g.endswith('.zhs') for g in names(
                roof_path, chr(cp), language=language, script='Hani'))


@pytest.mark.parametrize('language', ['ja', 'ko', 'zh-TW', None])
@pytest.mark.parametrize('script', ['Hani', 'Latn', 'DFLT', 'Kana'])
def test_zhs_forms_only_under_zhs(ctx, roof_path, language, script):
    text = ''.join(map(chr, (*zhs_forms(ctx), *ZHS_SIGNS, *ZHS_QUOTES)))
    assert not any(g.endswith('.zhs') for g in names(roof_path, text, language=language, script=script))


@cache
def specimen_script_runs():
    spec = importlib.util.spec_from_file_location('zhs_specimen', Path('verify/specimen.py'))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.script_runs


def test_zhs_quote_pair_matches(roof_path):
    quotes = []
    for script, run in specimen_script_runs()('他说“OK”。'):
        shaped = shape(roof_path, run, script=script, language='zh-CN')
        for char, glyph in zip(run, shaped):
            if char in '“”':
                quotes.append((char, script, glyph[0], glyph[1]))
    print('ZHS_QUOTE_PAIR', quotes)
    assert [(q[2], q[3]) for q in quotes] == [('uni201C.zhs', 1920), ('uni201D.zhs', 1920)], quotes


@pytest.mark.parametrize('script', ['Hani', 'Latn', 'DFLT'])
@pytest.mark.parametrize('text', ['It’s', 'McDonald’s', 'l·l', '2’30', 'α’β', 'а·б', 'ȁ’ȃ', 'ə·ʃ'])
def test_zhs_alnum_apostrophe_and_dot_stay_proportional(roof_path, baseline_path, text, script):
    for w in (400, 750, 1000):
        actual = shape(roof_path, text, language='zh-CN', script=script, wght=w)
        expected = shape(baseline_path, text, language='zh-CN', script=script, wght=w)
        assert actual == expected, (text, script, w, actual, expected)


@pytest.mark.parametrize('text', ['他说“OK”。', '“abc”', '‘abc’', '“中”', '列奥纳多·达·芬奇'])
def test_zhs_quotes_switch_outside_alnum_words(roof_path, text):
    expected = [f'uni{ord(ch):04X}.zhs' for ch in text if ord(ch) in ZHS_QUOTES]
    for w in (400, 750, 1000):
        actual = [g for script, run in specimen_script_runs()(text)
                  for g in shape(roof_path, run, script=script, language='zh-CN', wght=w)
                  if g[0].startswith(('uni201', 'uni00B7')) and g[0].endswith('.zhs')]
        assert [(g[0], g[1]) for g in actual] == [(name, 1920) for name in expected]


@pytest.mark.parametrize('feature', ['ss20', 'jp90', 'fwid'])
def test_zhs_with_other_cjk_features(roof_path, roof, feature):
    out = names(roof_path, '乳直安毁！“', language='zh-CN', features={feature: True})
    assert out and '.notdef' not in out
    assert set(out) <= set(roof.getGlyphOrder())
    if feature == 'ss20':
        assert out[0] == 'uni4E73.loclJAN'
        assert names(roof_path, '乳', language='zh-CN') == ['uni4E73.zhs']


@pytest.mark.parametrize('language', ['ko', 'ja', 'zh-TW', None])
def test_unchanged_outside_zhs(roof_path, baseline_path, language):
    cmap = TTFont(baseline_path).getBestCmap()
    present = [cp for cp in gb2312_hanzi() if cp in cmap]
    sample = '한글 漢字 東京「ID」 abc 012 ½ 直安毁！‘’“”·' + ''.join(map(chr, present[::len(present)//200][:200]))
    for w in (400, 750, 1000):
        for script, run in specimen_script_runs()(sample):
            assert shape(roof_path, run, wght=w, language=language, script=script) == shape(
                baseline_path, run, wght=w, language=language, script=script), (language, w, script, run)
