import os
from pathlib import Path

import pytest
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

from roofsans.inputs import ensure_inputs

# Modules from later tasks are imported inside their fixtures, so collection works
# before they exist.


# Fixtures that read the built font; a test that uses one is an acceptance test (ruling R40).
FONT_FIXTURES = {"roof", "roof_path", "baseline_path"}


def pytest_configure(config):
    config.addinivalue_line("markers", "acceptance: needs the built Roof Sans font")


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config, items):
    for item in items:
        if FONT_FIXTURES & set(getattr(item, "fixturenames", ())):
            item.add_marker(pytest.mark.acceptance)


@pytest.fixture(scope="session")
def inputs():
    return ensure_inputs(refs_root=Path("refs"))


@pytest.fixture(scope="session")
def wanted(inputs):
    return TTFont(inputs.wanted)


@pytest.fixture(scope="session")
def pretendard(inputs):
    return TTFont(inputs.pretendard)


@pytest.fixture(scope="session")
def shs_cn(inputs):
    return TTFont(inputs.shs_cn)


@pytest.fixture(scope="session")
def shs_jp(inputs):
    return TTFont(inputs.shs_jp)


@pytest.fixture(scope="session")
def ws(wanted):
    from roofsans.sampling import WantedSampler

    return WantedSampler(wanted)


@pytest.fixture(scope="session")
def ps(pretendard):
    from roofsans.sampling import PretendardSampler

    return PretendardSampler(pretendard)


@pytest.fixture(scope="session")
def ctx(inputs):
    from roofsans.context import make_context

    return make_context(inputs)


@pytest.fixture(scope="session")
def roof_path():
    if os.environ.get("ROOF_FONT"):
        return Path(os.environ["ROOF_FONT"])
    from roofsans.build import build

    return build(Path("build/test/RoofSansVariable.ttf"))


@pytest.fixture(scope="session")
def baseline_path(inputs):
    """One reproducible pre-Chinese font per session, unless ROOF_BASELINE overrides it."""
    if os.environ.get("ROOF_BASELINE"):
        return Path(os.environ["ROOF_BASELINE"])
    from roofsans.build import build

    return build(Path("build/test-baseline/RoofSansVariable.ttf"), inputs, chinese=False, light=False)


@pytest.fixture(scope="session")
def roof(roof_path):
    return TTFont(roof_path)


@pytest.fixture(scope="session")
def static(request, inputs):
    """Return ``static(font_key, wght)``: a cached instance of one input at ``wght``.

    ``wght`` is on the font's own axis, so ``"pretendard"`` takes 45–930. Each
    instance is made from a fresh load, leaving the session fonts untouched.
    """
    cache: dict[tuple[str, float], TTFont] = {}

    def path_of(font_key: str) -> Path:
        if font_key == "wanted":
            return inputs.wanted
        if font_key == "pretendard":
            return inputs.pretendard
        if font_key == "roof":
            return request.getfixturevalue("roof_path")
        raise KeyError(font_key)

    def get(font_key: str, wght: float) -> TTFont:
        key = (font_key, wght)
        if key not in cache:
            font = TTFont(path_of(font_key))
            cache[key] = instantiateVariableFont(font, {"wght": wght}, inplace=True)
        return cache[key]

    return get
