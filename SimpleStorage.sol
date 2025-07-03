// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract SimpleStorage {
    uint256 public myNumber;

    function set(uint256 _newNumber) public {
        myNumber = _newNumber;
    }

    function get() public view returns (uint256) {
        return myNumber;
    }
}
