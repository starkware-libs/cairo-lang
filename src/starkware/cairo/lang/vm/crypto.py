import contextlib

from starkware.crypto.signature.fast_pedersen_hash import async_pedersen_hash_func  # noqa
from starkware.crypto.signature.fast_pedersen_hash import pedersen_hash  # noqa
from starkware.crypto.signature.fast_pedersen_hash import pedersen_hash_func  # noqa
from starkware.crypto.signature.signature import verify as verify_ecdsa  # noqa


def get_crypto_lib_context_manager(flavor):
    return contextlib.suppress()
