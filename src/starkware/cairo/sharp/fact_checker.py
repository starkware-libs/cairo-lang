from web3 import HTTPProvider, Web3

FACT_REGISTRY_ABI = [
    {
        "constant": True,
        "inputs": [{"internalType": "bytes32", "name": "fact", "type": "bytes32"}],
        "name": "isValid",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function",
    }
]


class FactChecker:
    """
    Checks if a fact is registered in a given fact registry.
    """

    def __init__(self, fact_registry_address: str, node_rpc_url: str):
        """
        fact_registry_address: the Ethereum address of the fact-registry to check.
        node_rpc_url: the URL of an Ethereum node, used to query the blockchain state.
        """

        # Initialize a contract instance, used to query the fact-registry contract.
        w3 = Web3(HTTPProvider(node_rpc_url))
        self.contract = w3.eth.contract(  # type: ignore
            address=fact_registry_address, abi=FACT_REGISTRY_ABI
        )

    def is_valid(self, fact: str) -> bool:
        """
        Returns true if and only if the fact is registered on-chain.
        The function does not wait for confirmations (reorgs can revert registration).
        """

        return self.contract.functions.isValid(fact).call()
