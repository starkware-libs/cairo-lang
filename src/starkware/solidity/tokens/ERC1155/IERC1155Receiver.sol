// SPDX-License-Identifier: Apache-2.0.
pragma solidity ^0.6.12;

/**
  Note: The ERC-165 identifier for this interface is 0x4e2312e0.
*/
interface IERC1155Receiver {
    /**
      Handles the receipt of a single ERC1155 token type.
      @dev An ERC1155-compliant smart contract MUST call this function on the token recipient contract, at the end of a `safeTransferFrom` after the balance has been updated.
      This function MUST return `bytes4(keccak256("onERC1155Received(address,address,uint256,uint256,bytes)"))` (i.e. 0xf23a6e61) if it accepts the transfer.
      This function MUST revert if it rejects the transfer.
      Return of any other value than the prescribed keccak256 generated value MUST result in the transaction being reverted by the caller.
      @param operator  The address which initiated the transfer (i.e. msg.sender)
      @param from      The address which previously owned the token
      @param id        The ID of the token being transferred
      @param value     The amount of tokens being transferred
      @param data      Additional data with no specified format
      @return           `bytes4(keccak256("onERC1155Received(address,address,uint256,uint256,bytes)"))` .
    */
    function onERC1155Received(
        address operator,
        address from,
        uint256 id,
        uint256 value,
        bytes calldata data
    ) external returns (bytes4);

    /**
      Handles the receipt of multiple ERC1155 token types.
      @dev An ERC1155-compliant smart contract MUST call this function on the token recipient contract, at the end of a `safeBatchTransferFrom` after the balances have been updated.
      This function MUST return `bytes4(keccak256("onERC1155BatchReceived(address,address,uint256[],uint256[],bytes)"))` (i.e. 0xbc197c81) if it accepts the transfer(s).
      This function MUST revert if it rejects the transfer(s).
      Return of any other value than the prescribed keccak256 generated value MUST result in the transaction being reverted by the caller.
      @param operator  The address which initiated the batch transfer (i.e. msg.sender)
      @param from      The address which previously owned the token
      @param ids       An array containing ids of each token being transferred (order and length must match values array)
      @param values    An array containing amounts of each token being transferred (order and length must match ids array)
      @param data      Additional data with no specified format
      @return           `bytes4(keccak256("onERC1155BatchReceived(address,address,uint256[],uint256[],bytes)"))` .
    */
    function onERC1155BatchReceived(
        address operator,
        address from,
        uint256[] calldata ids,
        uint256[] calldata values,
        bytes calldata data
    ) external returns (bytes4);
}
