import cachetools
import pytest

from starkware.starknet.core.os.contract_class.compiled_class_hash import (
    compute_compiled_class_hash,
    run_compiled_class_hash,
)
from starkware.starknet.core.os.contract_class.utils import set_class_hash_cache
from starkware.starknet.core.test_contract.test_utils import get_test_compiled_class
from starkware.starknet.services.api.contract_class.contract_class import CompiledClass


@pytest.fixture
def compiled_class() -> CompiledClass:
    return get_test_compiled_class()


def compute_compiled_class_hash_using_cairo(compiled_class: CompiledClass) -> int:
    runner = run_compiled_class_hash(compiled_class=compiled_class)
    _, class_hash = runner.get_return_values(2)
    return class_hash


def test_compiled_class_hash(compiled_class: CompiledClass):
    """
    Tests that the hash of a constant contract does not change.
    """
    expected_compiled_class_hash = 0x64FE2D71ABA33FC59ACB622B95157D54989B130F1FB3F9253A655F88B50DD02
    # Assert that our test Python hash computation is equivalent to static value.
    cairo_computed_compiled_class_hash = compute_compiled_class_hash_using_cairo(
        compiled_class=compiled_class
    )
    assert expected_compiled_class_hash == cairo_computed_compiled_class_hash, (
        f"Computed compiled class hash: {hex(cairo_computed_compiled_class_hash)} "
        f"does not match the expected value: {hex(expected_compiled_class_hash)}."
    )

    cache: cachetools.LRUCache = cachetools.LRUCache(maxsize=10)
    with set_class_hash_cache(cache=cache):
        assert len(cache) == 0

        python_computed_compiled_class_hash: int = compute_compiled_class_hash(
            compiled_class=compiled_class
        )
        assert len(cache) == 1

        assert python_computed_compiled_class_hash == expected_compiled_class_hash, (
            f"Computed compiled class hash: {hex(python_computed_compiled_class_hash)} "
            f"does not match the expected value: {hex(expected_compiled_class_hash)}."
        )
