from enum import Enum


class StorageDomain(Enum):
    ON_CHAIN = 0
    OFF_CHAIN = 1

    def assert_onchain(self):
        assert self is StorageDomain.ON_CHAIN, "Only on-chain storage is currently supported."
