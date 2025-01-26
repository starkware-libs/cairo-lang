// SPDX-License-Identifier: Apache-2.0.
pragma solidity >=0.6.0 <0.9.0;

abstract contract MGovernance {
    function _isGovernor(address user) internal view virtual returns (bool);

    /*
      Allows calling the function only by a Governor.
    */
    modifier onlyGovernance() {
        require(_isGovernor(msg.sender), "ONLY_GOVERNANCE");
        _;
    }

    function initGovernance() internal virtual;
}
