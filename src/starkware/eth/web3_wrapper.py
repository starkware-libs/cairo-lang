from web3 import Web3


def web3_type_fix():
    if not hasattr(Web3, "to_checksum_address"):
        Web3.to_checksum_address = Web3.toChecksumAddress  # type: ignore
    if not hasattr(Web3, "is_checksum_address"):
        Web3.is_checksum_address = Web3.isChecksumAddress  # type: ignore
    if not hasattr(Web3, "is_connected"):
        Web3.is_connected = Web3.isConnected  # type: ignore


def web3_contract_create_filter_fix(event):
    if not hasattr(event, "create_filter"):
        event.create_filter = event.createFilter


web3_type_fix()
