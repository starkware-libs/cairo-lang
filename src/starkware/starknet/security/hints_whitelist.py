import os

from starkware.starknet.security.secure_hints import HintsWhitelist


def get_hints_whitelist() -> HintsWhitelist:
    return HintsWhitelist.from_file(
        filename=os.path.join(os.path.dirname(__file__), 'whitelists/latest.json'))
