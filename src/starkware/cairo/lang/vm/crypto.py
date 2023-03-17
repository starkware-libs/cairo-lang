import contextlib

from starkware.cairo.common.poseidon_hash import (  # noqa
    poseidon_hash,
    poseidon_hash_func,
    poseidon_hash_many,
    poseidon_hash_single,
    poseidon_perm,
)
from starkware.crypto.signature.fast_pedersen_hash import pedersen_hash  # noqa
from starkware.crypto.signature.fast_pedersen_hash import pedersen_hash_func  # noqa
from starkware.crypto.signature.signature import verify as verify_ecdsa  # noqa


def get_crypto_lib_context_manager(flavor):
    return contextlib.suppress()
