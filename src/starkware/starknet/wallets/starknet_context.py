import dataclasses

from starkware.starknet.services.api.feeder_gateway.feeder_gateway_client import FeederGatewayClient
from starkware.starknet.services.api.gateway.gateway_client import GatewayClient


@dataclasses.dataclass
class StarknetContext:
    # A textual identifier used to distinguish between different StarkNet networks.
    network_id: str
    # The directory which contains the account information files.
    account_dir: str
    gateway_client: GatewayClient
    feeder_gateway_client: FeederGatewayClient
