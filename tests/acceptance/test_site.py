import importlib.util
import json
import re
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


def test_page_describes_every_feature(roof_path):
    page = build_site.TEMPLATE_PATH.read_text(encoding="utf-8")
    assert build_site.feature_problems(TTFont(roof_path), page) == []


def test_undescribed_feature_is_reported(roof_path):
    page = build_site.TEMPLATE_PATH.read_text(encoding="utf-8")
    assert 'data-feature="case"' in page
    problems = build_site.feature_problems(TTFont(roof_path), page.replace('data-feature="case"', ""))
    assert problems == ["features the font has but the page does not describe: case"]


def test_page_links_font_and_fills_markers(roof_path, tmp_path):
    page = build_site.build_site(roof_path, tmp_path).read_text(encoding="utf-8")
    assert (tmp_path / build_site.WOFF2_NAME).read_bytes()[:4] == b"wOF2"
    assert f'url("{build_site.WOFF2_NAME}")' in page
    assert re.search(r"__[A-Z0-9_]+__", page) is None
    assert "Standard Estonian" in page and "Ukrainian" in page
    assert f"roof-sans@v{build_site.package_version()}/dist/web/" in page

    assert len(page.encode("utf-8")) < 1_000_000
    assert 'lang="zh-CN"' in page and 'data-lang="zh-CN"' in page
    assert 'data-sample="zh"' in page
    assert "6,763" in page and "3,008" in page and "5,034" in page
    assert "TextStyle(fontFamily: 'RoofSans', locale: Locale('zh', 'CN'))" in page
    assert 'id="panel-features"' in page and 'href="#features"' in page
