// SPDX-License-Identifier: Apache-2.0.
pragma solidity ^0.8.0;

import "./Output.sol";

library StarknetState {
    struct State {
        uint256 globalRoot;
        int256 blockNumber;
        uint256 blockHash;
    }

    function copy(State storage state, State memory stateFrom) internal {
        state.globalRoot = stateFrom.globalRoot;
        state.blockNumber = stateFrom.blockNumber;
        state.blockHash = stateFrom.blockHash;
    }

    /**
      Validates that the previous block number that appears in the proof is the current block
      number.

      To protect against re-entrancy attacks, we read the block number at the beginning
      and validate that we have the expected block number at the end.
      This function must be called at the beginning of the updateState transaction.
    */
    function checkPrevBlockNumber(State storage state, uint256[] calldata starknetOutput) internal {
        uint256 expectedPrevBlockNumber;
        if (state.blockNumber == -1) {
            expectedPrevBlockNumber = 0x800000000000011000000000000000000000000000000000000000000000000;
        } else {
            expectedPrevBlockNumber = uint256(state.blockNumber);
        }
        require(
            starknetOutput[StarknetOutput.PREV_BLOCK_NUMBER_OFFSET] == expectedPrevBlockNumber,
            "INVALID_PREV_BLOCK_NUMBER"
        );
    }

    /**
      Validates that the current block number is the new block number.
      This is used to protect against re-entrancy attacks.
    */
    function checkNewBlockNumber(State storage state, uint256[] calldata starknetOutput) internal {
        require(
            uint256(state.blockNumber) == starknetOutput[StarknetOutput.NEW_BLOCK_NUMBER_OFFSET],
            "REENTRANCY_FAILURE"
        );
    }

    /**
      Validates that the 'blockNumber' and the previous root are consistent with the
      current state and updates the state.
    */
    function update(State storage state, uint256[] calldata starknetOutput) internal {
        checkPrevBlockNumber(state, starknetOutput);

        // Check the blockNumber first as the error is less ambiguous then INVALID_PREVIOUS_ROOT.
        int256 newBlockNumber = int256(starknetOutput[StarknetOutput.NEW_BLOCK_NUMBER_OFFSET]);
        require(newBlockNumber > state.blockNumber, "INVALID_NEW_BLOCK_NUMBER");
        state.blockNumber = newBlockNumber;

        require(
            starknetOutput[StarknetOutput.PREV_BLOCK_HASH_OFFSET] == state.blockHash,
            "INVALID_PREV_BLOCK_HASH"
        );
        state.blockHash = starknetOutput[StarknetOutput.NEW_BLOCK_HASH_OFFSET];

        uint256[] calldata commitment_tree_update = StarknetOutput.getMerkleUpdate(starknetOutput);
        require(
            state.globalRoot == CommitmentTreeUpdateOutput.getPrevRoot(commitment_tree_update),
            "INVALID_PREVIOUS_ROOT"
        );
        state.globalRoot = CommitmentTreeUpdateOutput.getNewRoot(commitment_tree_update);
    }
}
