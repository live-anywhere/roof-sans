"""Acceptance 16: the pre-Chinese, pre-light baseline remains independently reproducible."""

import hashlib


def test_without_chinese_reproduces_pre_chinese_font(baseline_path):
    """Update this hash only for an intended non-Chinese rule change, recorded in the build notes."""
    expected = "6a01839de58c49b41cfa6bba64a6653ab8b66fcab74e7150ae55cd4173272325"
    assert hashlib.sha256(baseline_path.read_bytes()).hexdigest() == expected
