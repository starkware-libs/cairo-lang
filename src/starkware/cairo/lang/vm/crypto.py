import contextlib

from starkware.crypto.signature import verify as verify_ecdsa  # noqa
from starkware.crypto.signature.fast_pedersen_hash import pedersen_hash  # noqa


def get_crypto_lib_context_manager(flavor):
    return contextlib.suppress()
