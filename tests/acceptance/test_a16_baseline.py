"""Acceptance 16: the pre-Chinese baseline remains independently reproducible."""

import hashlib


def test_without_chinese_reproduces_pre_chinese_font(baseline_path):
    """Update this hash only for an intended non-Chinese rule change, recorded in the build notes."""
    # The committed pre-Chinese font (`6a01839d…272325`) at version 1.300: without Wanted Sans's
    # logo and `liga`, with name IDs 0 and 7 as in 1.3.0 (build notes section 15).
    expected = "93cd005f51f97c7d8f514ed8631e749a0f0e2331bf38cd4ab4d599d75cd0835f"
    assert hashlib.sha256(baseline_path.read_bytes()).hexdigest() == expected
