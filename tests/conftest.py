from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


@pytest.fixture
def k01_path():
    return FIXTURES / "K01.yaml"


@pytest.fixture
def g01_path():
    return FIXTURES / "G01.yaml"
