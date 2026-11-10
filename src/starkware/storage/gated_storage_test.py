import pytest

from starkware.storage.gated_storage import (
    MAGIC_HEADER,
    RECORD_LENGTH_BUFFER,
    DeterministicGatedStorage,
    GatedStorage,
)
from starkware.storage.test_utils import MockStorage

# The _compress_value method stores the item in storage1 if the value exceeds the limit or already
# starts with MAGIC_HEADER. To test the MAGIC_HEADER condition in isolation, the limit was set high
# enough to ensure storage1 is used due to the header alone, not because the value exceeds the size
# limit.
LIMIT = len(MAGIC_HEADER) + 10
TEST_KEY = b"key"


@pytest.fixture
def gated_storage():
    return GatedStorage(
        limit=LIMIT + RECORD_LENGTH_BUFFER, storage0=MockStorage(), storage1=MockStorage()
    )


@pytest.fixture
def deterministic_gated_storage():
    return DeterministicGatedStorage(
        limit=LIMIT + RECORD_LENGTH_BUFFER, storage0=MockStorage(), storage1=MockStorage()
    )


@pytest.mark.asyncio
async def test_unique_key_prefix():
    """
    Overflow objects of a prefixed storage land under the prefix in storage1, and pointers
    written by either a prefixed or a non-prefixed storage resolve through both, as long as
    they share storage1.
    """
    storage0, storage1 = MockStorage(), MockStorage()
    limit = LIMIT + RECORD_LENGTH_BUFFER
    prefixed = GatedStorage(
        limit=limit, storage0=storage0, storage1=storage1, unique_key_prefix="witnesses/"
    )
    plain = GatedStorage(limit=limit, storage0=storage0, storage1=storage1)
    value = b"x" * (limit + 1)

    await prefixed.set_value(key=TEST_KEY, value=value)
    assert all(
        ukey.startswith(b"witnesses/") for ukey in storage1.db
    ), "Overflow object not stored under the unique key prefix."
    assert (
        await plain.get_value(key=TEST_KEY) == value
    ), "Prefixed pointer is not resolvable by a non-prefixed storage sharing storage1."

    legacy_key = b"legacy_key"
    await plain.set_value(key=legacy_key, value=value)
    assert (
        await prefixed.get_value(key=legacy_key) == value
    ), "Non-prefixed (legacy) pointer is not resolvable by a prefixed storage sharing storage1."


@pytest.mark.parametrize(
    "storage_type",
    [
        "gated_storage",
        "deterministic_gated_storage",
    ],
)
@pytest.mark.asyncio
async def test_gated_storage(request: pytest.FixtureRequest, storage_type: str):
    storage = request.getfixturevalue(storage_type)

    keys_values = [(b"k0", b"v0"), (b"k1", b"v1" * LIMIT)]
    for k, v in keys_values:
        assert await storage.get_value(key=k) is None
        assert not await storage.has_key(key=k)
        await storage.set_value(key=k, value=v)
        assert await storage.get_value_or_fail(key=k) == v
        assert await storage.has_key(key=k)
        assert not await storage.setnx_value(key=k, value=b"wrong")
        assert await storage.get_value_or_fail(key=k) == v

    assert storage.storage0.db.keys() == {b"k0", b"k1"}
    assert len(storage.storage1.db.keys()) == 1

    for k, _ in keys_values:
        await storage.del_value(k)

    assert len(storage.storage0.db.keys()) == 0
    assert len(storage.storage1.db.keys()) == 0


@pytest.mark.asyncio
async def test_magic_header_gated_storage():
    """
    Tests the edge case where the prefix of a short value is MAGIC_HEADER. In this case, the value
    will be stored in the secondary storage.
    """
    storage0 = MockStorage()
    storage1 = MockStorage()
    storage = GatedStorage(limit=1000, storage0=storage0, storage1=storage1)
    key, value = (b"k0", MAGIC_HEADER + b"v0")
    await storage.set_value(key=key, value=value)
    assert await storage.get_value_or_fail(key=key) == value
    assert storage0.db.keys() == {b"k0"}
    assert len(storage1.db.keys()) == 1
    await storage.del_value(key=key)
    assert len(storage0.db.keys()) == 0
    assert len(storage1.db.keys()) == 0


@pytest.mark.parametrize(
    ("value", "should_compress"),
    [
        # Value is the minimal size such that the condition is met and the value doesn't have the
        # MAGIC_HEADER.
        (bytes(LIMIT - len(TEST_KEY) + 1), True),
        # Value is the maximal size such that the condition is not met and the value doesn't have
        #  the MAGIC_HEADER.
        (bytes(LIMIT - len(TEST_KEY)), False),
        # The value is small enough but has the MAGIC_HEADER prefix.
        (MAGIC_HEADER + b"v", True),
    ],
)
@pytest.mark.asyncio
async def test_compress_value(gated_storage: GatedStorage, value: bytes, should_compress: bool):
    """
    Tests the _compress_value method of GatedStorage.
    """
    new_key, new_value = await gated_storage._compress_value(key=TEST_KEY, value=value)
    assert new_key == TEST_KEY
    if should_compress:
        assert new_value.startswith(MAGIC_HEADER)
        assert await gated_storage.storage1.get_value(key=new_value[len(MAGIC_HEADER) :]) == value
    else:
        assert new_value == value


@pytest.mark.parametrize(
    "storage_type",
    [
        "gated_storage",
        "deterministic_gated_storage",
    ],
)
@pytest.mark.asyncio
async def test_mget_across_tiers(request: pytest.FixtureRequest, storage_type: str):
    """
    `mget` returns values in order across both tiers: small values inline from the primary
    storage, large values from the secondary storage, and None for missing keys.
    """
    storage = request.getfixturevalue(storage_type)
    small_value = b"v0"
    large_value = b"v1" * LIMIT  # Exceeds the limit, so it overflows to the secondary storage.
    await storage.set_value(key=b"k0", value=small_value)
    await storage.set_value(key=b"k1", value=large_value)
    # Key b"k2" is intentionally absent.

    keys = [b"k0", b"k1", b"k2"]
    result = await storage.mget(keys=keys)

    assert result == (small_value, large_value, None)
    # The large value really overflowed to the secondary storage.
    assert len(storage.storage1.db.keys()) == 1
    # mget matches per-key get_value.
    assert result == tuple([await storage.get_value(key=key) for key in keys])
