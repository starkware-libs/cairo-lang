from enum import Enum
from typing import Set

from starkware.python.utils import from_bytes

FEE_TOKEN_ADDRESS = 0x49D36570D4E46F48E99674BD3FCC84644DDD6B96F7C741B1562B82F9E004DC7


class StarknetChainId(Enum):
    MAINNET = from_bytes(b"SN_MAIN")
    TESTNET = from_bytes(b"SN_GOERLI")
    TESTNET2 = from_bytes(b"SN_GOERLI2")

    def is_private(self) -> bool:
        return self.name in PRIVATE_CHAIN_IDS


PRIVATE_CHAIN_IDS: Set[str] = set()


CHAIN_ID_TO_FEE_TOKEN_ADDRESS = {chain_enum: FEE_TOKEN_ADDRESS for chain_enum in StarknetChainId}
