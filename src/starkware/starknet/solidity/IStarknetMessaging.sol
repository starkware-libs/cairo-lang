// SPDX-License-Identifier: Apache-2.0.
pragma solidity >=0.6.0 <0.9.0;

import "starkware/starknet/solidity/IStarknetMessagingEvents.sol";

interface IStarknetMessaging is IStarknetMessagingEvents {
    /**
      Returns the max fee (in Wei) that StarkNet will accept per single message.
    */
    function getMaxL1MsgFee() external pure returns (uint256);

    /**
      Returns `msg_fee + 1` if there is a pending message associated with the given 'msgHash',
      otherwise, returns 0.
    */
    function l1ToL2Messages(bytes32 msgHash) external view returns (uint256);

    /**
      Returns number of consumable messages with hash of `msgHash`.
    */
    function l2ToL1Messages(bytes32 msgHash) external view returns (uint256);

    /**
      Returns the hash of an L1 -> L2 message.
    */
    function l1ToL2MsgHash(
        address fromAddress,
        uint256 toAddress,
        uint256 selector,
        uint256[] calldata payload,
        uint256 nonce
    ) external pure returns (bytes32);

    /**
      Returns the hash of an L2 -> L1 message.
    */
    function l2ToL1MsgHash(
        uint256 fromAddress,
        address toAddress,
        uint256[] calldata payload
    ) external pure returns (bytes32);

    /**
      Sends a message to an L2 contract.
      This function is payable, the payed amount is the message fee.

      Returns the hash of the message and the nonce of the message.
    */
    function sendMessageToL2(
        uint256 toAddress,
        uint256 selector,
        uint256[] calldata payload
    ) external payable returns (bytes32, uint256);

    /**
      Consumes a message that was sent from an L2 contract.

      Returns the hash of the message.
    */
    function consumeMessageFromL2(uint256 fromAddress, uint256[] calldata payload)
        external
        returns (bytes32);

    /**
      Starts the cancellation of an L1 to L2 message.
      A message can be canceled messageCancellationDelay() seconds after this function is called.

      Note: This function may only be called for a message that is currently pending and the caller
      must be the sender of the that message.
    */
    function startL1ToL2MessageCancellation(
        uint256 toAddress,
        uint256 selector,
        uint256[] calldata payload,
        uint256 nonce
    ) external returns (bytes32);

    /**
      Cancels an L1 to L2 message, this function should be called at least
      messageCancellationDelay() seconds after the call to startL1ToL2MessageCancellation().
      A message may only be cancelled by its sender.
      If the message is missing, the call will revert.

      Note that the message fee is not refunded.
    */
    function cancelL1ToL2Message(
        uint256 toAddress,
        uint256 selector,
        uint256[] calldata payload,
        uint256 nonce
    ) external returns (bytes32);
}
