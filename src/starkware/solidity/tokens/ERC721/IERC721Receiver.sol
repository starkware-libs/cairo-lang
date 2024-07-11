// SPDX-License-Identifier: Apache-2.0.
pragma solidity ^0.6.12;

interface IERC721Receiver {
    function onERC721Received(
        address operator,
        address from,
        uint256 tokenId,
        bytes calldata data
    ) external returns (bytes4);
}
