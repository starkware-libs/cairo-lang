// SPDX-License-Identifier: Apache-2.0.
pragma solidity >=0.6.0 <0.9.0;

interface ExternalInitializer {
    event LogExternalInitialize(bytes data);

    function initialize(bytes calldata data) external;
}
