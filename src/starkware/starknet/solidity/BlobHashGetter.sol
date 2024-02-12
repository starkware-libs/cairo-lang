// SPDX-License-Identifier: Apache-2.0.
pragma solidity ^0.6.12;

/**
  A factory for creating contracts from EVM bytecode.
*/
contract ContractFactory {
    constructor(bytes memory code) public {
        uint256 size = code.length;
        assembly {
            return(add(code, 0x20), size)
        }
    }
}

library BlobHashGetter {
    // The bytescode for retrieving the blob hash.
    // See https://github.com/ethstorage/eip4844-blob-hash-getter/blob/main/README.md for a detailed
    // explanation.
    bytes internal constant CODE = hex"6000354960005260206000F3";

    // Storage slot to hold the deployed hash getter address.
    // Web3.keccak(text="BLOB_HASH_GETTER_CONTRACT_SLOT").
    bytes32 internal constant BLOB_HASH_GETTER_CONTRACT_SLOT =
        0xd599dde24be23990034c1ef263a0e367ed5609a1c3122cb48d78c560328abb89;

    /**
      Deploys the bytecode that retrieves the hash of a blob, using the DATAHASH (0x49) opcode.
      The deployed code accepts blob index as 32-byte input, and outputs blob hash as 32 bytes.
    */
    function deploy() internal returns (address) {
        address getter = address(new ContractFactory(CODE));
        assembly {
            sstore(BLOB_HASH_GETTER_CONTRACT_SLOT, getter)
        }
        return getter;
    }

    /**
      Accepts a blob index and returns its versioned hash.
      Deploys the hash getter code if it wasn't deployed yet.
    */
    function getBlobHash(uint256 idx) internal returns (bytes32) {
        address getter;
        assembly {
            getter := sload(BLOB_HASH_GETTER_CONTRACT_SLOT)
        }
        if (getter == address(0x0)) {
            getter = deploy();
        }

        bool success;
        bytes32 blobHash;
        assembly {
            mstore(0x0, idx)

            success := staticcall(gas(), getter, 0x0, 0x0, 0x20, 0x20)

            blobHash := mload(0x20)
        }

        require(success, "GET_BLOB_HASH_FAILED");
        return blobHash;
    }
}
