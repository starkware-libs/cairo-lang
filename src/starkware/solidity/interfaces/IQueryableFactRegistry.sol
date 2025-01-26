// SPDX-License-Identifier: Apache-2.0.
pragma solidity >=0.6.0 <0.9.0;

import "starkware/solidity/interfaces/IFactRegistry.sol";

/*
  Extends the IFactRegistry interface with a query method that indicates
  whether the fact registry has successfully registered any fact or is still empty of such facts.
*/
interface IQueryableFactRegistry is IFactRegistry {
    /*
      Returns true if at least one fact has been registered.
    */
    function hasRegisteredFact() external view returns (bool);
}
