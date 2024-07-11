// SPDX-License-Identifier: Apache-2.0.
pragma solidity ^0.6.12;

/**
  Interface of the ERC165 standard, as defined in the
  https://eips.ethereum.org/EIPS/eip-165[EIP].


*/
interface IERC165 {
    function supportsInterface(bytes4 interfaceId) external view returns (bool);
}
