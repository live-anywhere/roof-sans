import hashlib
import json
import re
from pathlib import Path

import pytest

from roofsans.inputs import InputChecksumError, ensure_inputs


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_ensure_inputs_copies_from_refs(tmp_path):
    got = ensure_inputs(tmp_path / "in", refs_root=Path("refs"))
    assert sha256(got.wanted) == "9953a7cfc4a3cba4ef1242abaf89779b3cd15fd9729c2d67d9e9d37a0da967f5"
    assert sha256(got.pretendard) == "bc1d77db0f3cb9c20986b8939aa8a28d5216552d777d082955da22f420535cbb"


def test_checksum_mismatch_raises(tmp_path):
    fake = tmp_path / "refs" / "wanted-sans" / "packages/wanted-sans/fonts/variable"
    fake.mkdir(parents=True); (fake / "WantedSansVariable.ttf").write_bytes(b"x")
    with pytest.raises(InputChecksumError):
        ensure_inputs(tmp_path / "in", refs_root=tmp_path / "refs")


def test_lock_urls_pin_full_commits():
    for e in json.loads(Path("inputs.lock.json").read_text()):
        assert re.search(r"/[0-9a-f]{40}/", e["url"])
