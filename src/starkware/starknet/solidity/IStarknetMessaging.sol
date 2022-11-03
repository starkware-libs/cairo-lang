// SPDX-License-Identifier: Apache-2.0.
pragma solidity ^0.6.12;

import "./IStarknetMessagingEvents.sol";

interface IStarknetMessaging is IStarknetMessagingEvents {
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
      Cancels an L1 to L2 message, this function should be called messageCancellationDelay() seconds
      after the call to startL1ToL2MessageCancellation().

      Note that the message fee is not refunded.
    */
    function cancelL1ToL2Message(
        uint256 toAddress,
        uint256 selector,
        uint256[] calldata payload,
        uint256 nonce
    ) external returns (bytes32);
}
