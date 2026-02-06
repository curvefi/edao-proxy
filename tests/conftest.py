import boa
import pytest


@pytest.fixture(autouse=True)
def _fast_mode():
    boa.env.enable_fast_mode()


@pytest.fixture()
def deployer():
    return boa.env.generate_address()
