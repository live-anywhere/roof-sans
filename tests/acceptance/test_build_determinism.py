"""Two builds from the same inputs are byte-identical, also under a different hash seed."""

import hashlib
import os
import subprocess
import sys

import pytest

from roofsans.build import build

pytestmark = pytest.mark.acceptance


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_build_determinism(tmp_path, inputs):
    here = build(tmp_path / "a" / "RoofSansVariable.ttf", inputs)
    # The second build runs in its own interpreter, so set and str-keyed dict order differ.
    seed = "1" if os.environ.get("PYTHONHASHSEED") != "1" else "2"
    there = tmp_path / "b" / "RoofSansVariable.ttf"
    script = (
        "import sys; from pathlib import Path; from roofsans.build import build; from roofsans.inputs import Inputs; "
        "build(Path(sys.argv[1]), Inputs(*map(Path, sys.argv[2:])))"
    )
    args = [str(there), *(str(p) for p in vars(inputs).values())]
    subprocess.run([sys.executable, "-c", script, *args], env={**os.environ, "PYTHONHASHSEED": seed}, check=True)
    assert sha256(here) == sha256(there)
