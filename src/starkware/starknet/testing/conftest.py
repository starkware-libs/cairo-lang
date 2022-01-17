import pytest

from starkware.eth.eth_test_utils import EthTestUtils


@pytest.fixture(scope="session")
def eth_test_utils() -> EthTestUtils:
    with EthTestUtils.context_manager() as val:
        yield val
