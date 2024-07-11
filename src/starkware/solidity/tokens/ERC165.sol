// SPDX-License-Identifier: Apache-2.0.
pragma solidity ^0.6.12;

import "./IERC165.sol";

/**
  Implementation of the {IERC165} interface.

  Contracts may inherit from this and call {registerInterface} to declare
  their support of an interface.
*/
abstract contract ERC165 is IERC165 {
    /*
      INTERFACE_ID_ERC165 = bytes4(keccak256('supportsInterface(bytes4)')) == 0x01ffc9a7.
    */
    bytes4 private constant INTERFACE_ID_ERC165 = 0x01ffc9a7;

    mapping(bytes4 => bool) private supportedInterfaces;

    constructor() public {
        // Derived contracts need only register support for their own interfaces,
        // Support for ERC165 itself here.
        registerInterface(INTERFACE_ID_ERC165);
    }

    function supportsInterface(bytes4 interfaceId) public view override returns (bool) {
        return supportedInterfaces[interfaceId];
    }

    function registerInterface(bytes4 interfaceId) internal {
        require(interfaceId != 0xffffffff, "ERC165: invalid interface id");
        supportedInterfaces[interfaceId] = true;
    }
}
