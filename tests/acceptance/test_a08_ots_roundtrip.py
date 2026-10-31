"""Acceptance 8: the font passes OTS sanitization and fontTools round-trips cleanly."""

from io import BytesIO

import ots
import pytest
from fontTools.ttLib import TTFont

pytestmark = pytest.mark.acceptance


def test_ots_sanitize(roof_path, tmp_path):
    result = ots.sanitize(str(roof_path), str(tmp_path / "ots.ttf"), capture_output=True)
    assert result.returncode == 0, (result.stdout + result.stderr).decode()


def test_binary_roundtrip(roof_path):
    # Without recalcTimestamp=False, save() and compile() would stamp head.modified with the current time.
    font = TTFont(roof_path, recalcTimestamp=False)
    buf = BytesIO()
    font.save(buf)
    buf.seek(0)
    again = TTFont(buf, recalcTimestamp=False)
    original = TTFont(roof_path, recalcTimestamp=False)
    assert sorted(again.keys()) == sorted(original.keys())
    differing = [
        tag
        for tag in original.keys()
        if tag != "GlyphOrder" and again[tag].compile(again) != original[tag].compile(original)
    ]
    assert not differing


def test_xml_roundtrip(roof_path, tmp_path):
    xml = tmp_path / "roof.ttx"
    TTFont(roof_path).saveXML(xml)
    font = TTFont()
    font.importXML(xml)
    font.save(tmp_path / "roof.ttf")
    assert sorted(TTFont(tmp_path / "roof.ttf").keys()) == sorted(TTFont(roof_path).keys())
