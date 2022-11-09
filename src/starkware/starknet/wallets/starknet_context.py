import dataclasses


@dataclasses.dataclass
class StarknetContext:
    # A textual identifier used to distinguish between different StarkNet networks.
    network_id: str
    # The directory which contains the account information files.
    account_dir: str
