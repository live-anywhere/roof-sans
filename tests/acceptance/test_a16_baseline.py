"""Acceptance 16: the pre-Chinese baseline remains independently reproducible."""

import hashlib


def test_without_chinese_reproduces_pre_chinese_font(baseline_path):
    """Update this hash only for an intended non-Chinese rule change, recorded in the build notes."""
    # The committed pre-Chinese font (`6a01839d…272325`) with version 1.200 in `head` and name IDs 3 and 5.
    expected = "4b4791d6815c4d6ee59bef123325db039c90691f27d1289647b29511f8ad0606"
    assert hashlib.sha256(baseline_path.read_bytes()).hexdigest() == expected
