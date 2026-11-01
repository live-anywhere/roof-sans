"""Fetch and verify the pinned upstream inputs listed in inputs.lock.json."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path

LOCK_PATH = Path(__file__).resolve().parents[2] / "inputs.lock.json"


class InputChecksumError(Exception):
    def __init__(self, name: str, expected: str, actual: str) -> None:
        super().__init__(f"{name}: expected SHA-256 {expected}, got {actual}")
        self.name = name
        self.expected = expected
        self.actual = actual


@dataclass(frozen=True)
class Inputs:
    wanted: Path
    pretendard: Path
    wanted_ofl: Path
    pretendard_license: Path
    shs_cn: Path
    shs_jp: Path
    shs_license: Path


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _fetch(entry: dict, dest: Path, refs_root: Path | None) -> None:
    """Copy or download one entry to a temp file, verify it, then move it to dest."""
    source = refs_root / entry["repo"] / entry["path"] if refs_root is not None else None
    fd, tmp_name = tempfile.mkstemp(dir=dest.parent, prefix=f".{dest.name}.")
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as out:
            if source is not None and source.is_file():
                with source.open("rb") as src:
                    shutil.copyfileobj(src, out)
            else:
                with urllib.request.urlopen(entry["url"]) as resp:
                    shutil.copyfileobj(resp, out)
        actual = _sha256(tmp)
        if actual != entry["sha256"]:
            raise InputChecksumError(entry["name"], entry["sha256"], actual)
        tmp.chmod(0o644)  # mkstemp creates 0600
        os.replace(tmp, dest)
    finally:
        tmp.unlink(missing_ok=True)


def ensure_inputs(cache_dir: Path = Path("inputs"), refs_root: Path | None = None) -> Inputs:
    """Return verified local copies of the pinned inputs.

    A cached file whose SHA-256 matches the lock is reused. Otherwise the file is
    copied from ``refs_root/<repo>/<path>`` when that exists, else downloaded from
    the pinned URL. Nothing is written under ``refs_root``.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for entry in json.loads(LOCK_PATH.read_text()):
        dest = cache_dir / Path(entry["path"]).name
        if not (dest.is_file() and _sha256(dest) == entry["sha256"]):
            _fetch(entry, dest, refs_root)
        paths[entry["name"]] = dest
    return Inputs(**paths)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="roofsans-fetch", description=__doc__)
    parser.add_argument(
        "--from-refs",
        type=Path,
        metavar="DIR",
        help="copy inputs from local upstream checkouts in DIR instead of downloading",
    )
    args = parser.parse_args(argv)
    inputs = ensure_inputs(refs_root=args.from_refs)
    for path in vars(inputs).values():
        print(path)
