// SPDX-License-Identifier: Apache-2.0.
pragma solidity ^0.6.12;

import "./IERC721.sol";
import "./IERC721Receiver.sol";
import "../ERC165.sol";
import "../../libraries/Addresses.sol";

/**
  ERC721 Non-Fungible Token Standard basic implementation
  see https://eips.ethereum.org/EIPS/eip-721.
*/
contract ERC721 is ERC165, IERC721 {
    //  Equals to `bytes4(keccak256("onERC721Received(address,address,uint256,bytes)"))`
    //  which can be also obtained as `IERC721Receiver(0).onERC721Received.selector`.
    bytes4 private constant ERC721_RECEIVED = 0x150b7a02;

    // Count of tokens owned by owner.
    mapping(address => uint256) private holderBalance;

    // Token holder address to their list of owned tokens.
    mapping(uint256 => address) internal tokenOwners;

    // Approved addresses to token ID.
    mapping(uint256 => address) private tokenApprovals;

    // Operator approvals per owner.
    mapping(address => mapping(address => bool)) private operatorApprovals;

    // bytes4(keccak256('balanceOf(address)')) == 0x70a08231
    // bytes4(keccak256('ownerOf(uint256)')) == 0x6352211e
    // bytes4(keccak256('approve(address,uint256)')) == 0x095ea7b3
    // bytes4(keccak256('getApproved(uint256)')) == 0x081812fc
    // bytes4(keccak256('setApprovalForAll(address,bool)')) == 0xa22cb465
    // bytes4(keccak256('isApprovedForAll(address,address)')) == 0xe985e9c5
    // bytes4(keccak256('transferFrom(address,address,uint256)')) == 0x23b872dd
    // bytes4(keccak256('safeTransferFrom(address,address,uint256)')) == 0x42842e0e
    // bytes4(keccak256('safeTransferFrom(address,address,uint256,bytes)')) == 0xb88d4fde
    // => 0x70a08231 ^ 0x6352211e ^ 0x095ea7b3 ^ 0x081812fc ^
    //    0xa22cb465 ^ 0xe985e9c ^ 0x23b872dd ^ 0x42842e0e ^ 0xb88d4fde == 0x80ac58cd .
    bytes4 private constant INTERFACE_ID_ERC721 = 0x80ac58cd;

    using Addresses for address;

    constructor() public {
        registerInterface(INTERFACE_ID_ERC721);
    }

    function balanceOf(address owner) public view override returns (uint256) {
        require(owner != address(0), "ERC721: balance query for the zero address");
        return holderBalance[owner];
    }

    function ownerOf(uint256 tokenId) public view override returns (address) {
        address owner = tokenOwners[tokenId];
        require(owner != address(0), "ERC721: owner query for nonexistent token");
        return owner;
    }

    /**
      Approves another address to transfer the given token ID
      The zero address indicates there is no approved address.
      There can only be one approved address per token at a given time.
      Can only be called by the token owner or an approved operator.
    */
    function approve(address to, uint256 tokenId) public override {
        address owner = ownerOf(tokenId);
        require(to != owner, "ERC721: approval to current owner");
        require(
            msg.sender == owner || isApprovedForAll(owner, msg.sender),
            "ERC721: approve caller is not owner nor approved for all"
        );

        _approve(to, tokenId);
    }

    function getApproved(uint256 tokenId) public view override returns (address) {
        require(_exists(tokenId), "ERC721: approved query for nonexistent token");

        return tokenApprovals[tokenId];
    }

    /**
      Sets/unsets the approval of a given operator.
    */
    function setApprovalForAll(address operator, bool approved) public override {
        require(operator != msg.sender, "ERC721: approve to caller");

        operatorApprovals[msg.sender][operator] = approved;
        emit ApprovalForAll(msg.sender, operator, approved);
    }

    /**
      Tells whether an operator is approved by a given owner.
    */
    function isApprovedForAll(address owner, address operator) public view override returns (bool) {
        return operatorApprovals[owner][operator];
    }

    function transferFrom(
        address from,
        address to,
        uint256 tokenId
    ) public override {
        require(
            _isApprovedOrOwner(msg.sender, tokenId),
            "ERC721: transfer caller is not owner nor approved"
        );
        _transfer(from, to, tokenId);
    }

    function safeTransferFrom(
        address from,
        address to,
        uint256 tokenId
    ) public override {
        safeTransferFrom(from, to, tokenId, "");
    }

    function safeTransferFrom(
        address from,
        address to,
        uint256 tokenId,
        bytes memory _data
    ) public override {
        require(
            _isApprovedOrOwner(msg.sender, tokenId),
            "ERC721: transfer caller is not owner nor approved"
        );
        _safeTransfer(from, to, tokenId, _data);
    }

    function _safeTransfer(
        address from,
        address to,
        uint256 tokenId,
        bytes memory _data
    ) internal {
        _transfer(from, to, tokenId);
        require(
            _checkOnERC721Received(from, to, tokenId, _data),
            "ERC721: transfer to non ERC721Receiver implementer"
        );
    }

    function _exists(uint256 tokenId) internal view returns (bool) {
        return tokenOwners[tokenId] != address(0);
    }

    function _isApprovedOrOwner(address spender, uint256 tokenId) internal view returns (bool) {
        require(_exists(tokenId), "ERC721: operator query for nonexistent token");
        address owner = ownerOf(tokenId);
        return (spender == owner ||
            getApproved(tokenId) == spender ||
            isApprovedForAll(owner, spender));
    }

    function _safeMint(address to, uint256 tokenId) internal {
        _safeMint(to, tokenId, "");
    }

    function _safeMint(
        address to,
        uint256 tokenId,
        bytes memory _data
    ) internal {
        _mint(to, tokenId);
        require(
            _checkOnERC721Received(address(0), to, tokenId, _data),
            "ERC721: transfer to non ERC721Receiver implementer"
        );
    }

    function _mint(address to, uint256 tokenId) internal {
        require(to != address(0), "ERC721: mint to the zero address");
        require(!_exists(tokenId), "ERC721: token already minted");

        _beforeTokenTransfer(address(0), to, tokenId);

        holderBalance[to] += 1;

        tokenOwners[tokenId] = to;

        emit Transfer(address(0), to, tokenId);
    }

    function _burn(uint256 tokenId) internal {
        address owner = ownerOf(tokenId);

        _beforeTokenTransfer(owner, address(0), tokenId);

        // Clear approvals.
        _approve(address(0), tokenId);

        holderBalance[owner] -= 1;

        tokenOwners[tokenId] = address(0);

        emit Transfer(owner, address(0), tokenId);
    }

    function _transfer(
        address from,
        address to,
        uint256 tokenId
    ) internal {
        require(ownerOf(tokenId) == from, "ERC721: transfer of token that is not own");
        require(to != address(0), "ERC721: transfer to the zero address");

        _beforeTokenTransfer(from, to, tokenId);

        // Clear approvals from the previous owner.
        _approve(address(0), tokenId);

        holderBalance[from] -= 1;

        holderBalance[to] += 1;

        tokenOwners[tokenId] = to;

        emit Transfer(from, to, tokenId);
    }

    /**
      Internal function to invoke {IERC721Receiver-onERC721Received} on a target address.
      The call is not executed if the target address is not a contract.

      @param from address representing the previous owner of the given token ID
      @param to target address that will receive the tokens
      @param tokenId uint256 ID of the token to be transferred
      @param _data bytes optional data to send along with the call
      @return bool whether the call correctly returned the expected magic value.
    */
    function _checkOnERC721Received(
        address from,
        address to,
        uint256 tokenId,
        bytes memory _data
    ) private returns (bool) {
        if (!to.isContract()) {
            return true;
        }
        (bool success, bytes memory returndata) = to.call(
            abi.encodeWithSelector(
                IERC721Receiver(to).onERC721Received.selector,
                msg.sender,
                from,
                tokenId,
                _data
            )
        );
        if (!success) {
            if (returndata.length > 0) {
                assembly {
                    let returndata_size := mload(returndata)
                    revert(add(32, returndata), returndata_size)
                }
            } else {
                revert("ERC721: transfer to non ERC721Receiver implementer");
            }
        } else {
            bytes4 retval = abi.decode(returndata, (bytes4));
            return (retval == ERC721_RECEIVED);
        }
    }

    function _approve(address to, uint256 tokenId) private {
        tokenApprovals[tokenId] = to;
        emit Approval(ownerOf(tokenId), to, tokenId);
    }

    /**
      Virtual function Hook that is called before any token transfer / minting /burning.
    */
    function _beforeTokenTransfer(
        address from,
        address to,
        uint256 tokenId
    ) internal {}
}
