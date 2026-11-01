import importlib.util
import json
import sys
from pathlib import Path

from fontTools.ttLib import TTFont

BUILD_SITE_PY = Path(__file__).resolve().parents[2] / "site" / "build_site.py"


def _load_build_site():
    spec = importlib.util.spec_from_file_location("build_site", BUILD_SITE_PY)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


build_site = _load_build_site()


def test_page_facts_match_font(roof_path):
    languages = json.loads(build_site.LANGUAGES_PATH.read_text(encoding="utf-8"))
    assert build_site.stale_facts(TTFont(roof_path), languages) == []
    assert build_site.measure_facts(TTFont(roof_path))["GB 2312 level 2 hanzi"] == (3008, 3008)


def test_stale_fact_is_reported(roof_path, monkeypatch):
    languages = json.loads(build_site.LANGUAGES_PATH.read_text(encoding="utf-8"))
    monkeypatch.setitem(build_site.PAGE_FACTS, "glyphs", (1, None))
    problems = build_site.stale_facts(TTFont(roof_path), languages)
    assert len(problems) == 1 and problems[0].startswith("glyphs:")


def test_page_embeds_font_and_language_lists(roof_path, tmp_path):
    page = build_site.build_site(roof_path, tmp_path).read_text(encoding="utf-8")
    assert "data:font/woff2;base64,d09GMg" in page  # "wOF2" signature
    for marker in ("__FONT_DATA__", "__LATIN_LIST__", "__CYRILLIC_LIST__"):
        assert marker not in page
    assert "Standard Estonian" in page and "Ukrainian" in page

    assert len(page.encode("utf-8")) < 16_000_000
    assert 'lang="zh-CN"' in page and 'data-lang="zh-CN"' in page
    assert 'data-sample="zh"' in page
    assert "6,763" in page and "3,008" in page and "5,034" in page
    assert "TextStyle(fontFamily: 'RoofSans', locale: Locale('zh', 'CN'))" in page
