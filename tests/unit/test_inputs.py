import hashlib
import json
import re
from dataclasses import fields
from pathlib import Path

import pytest

from roofsans.inputs import Inputs, InputChecksumError, LOCK_PATH, ensure_inputs


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

COMMIT = 'a4f7cf94edfb9d7ffbdfc4841de276358bd7e0f2'


def test_lock_has_source_han_sans():
    entries = {e['name']: e for e in json.loads(LOCK_PATH.read_text())}
    for key, path, digest in (
        ('shs_cn', 'Variable/TTF/Subset/SourceHanSansCN-VF.ttf', '25a01e41b5cc99893eb35a6cd2cc7611841dc19eb03cbaf7f0c1de8210f2ba0b'),
        ('shs_jp', 'Variable/TTF/Subset/SourceHanSansJP-VF.ttf', '4acc34926098472741bbb7be5949b80afa7fc08f41ea3cd80dc34f12f7d55bbc'),
        ('shs_license', 'LICENSE.txt', 'fcac737e761ec63dbfbdce11030a1780161920d80315edba9c8beff1c2bac5a2'),
    ):
        entry = entries[key]
        assert entry['repo'] == 'source-han-sans'
        assert entry['path'] == path
        assert entry['url'] == f'https://raw.githubusercontent.com/adobe-fonts/source-han-sans/{COMMIT}/{path}'
        assert entry['sha256'] == digest


def test_inputs_fields_match_lock():
    assert [f.name for f in fields(Inputs)] == [e['name'] for e in json.loads(LOCK_PATH.read_text())]
