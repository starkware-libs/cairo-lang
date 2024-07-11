// SPDX-License-Identifier: MIT.
pragma solidity ^0.6.12;

import "./IERC1155.sol";
import "./IERC1155Receiver.sol";
import "../ERC165.sol";
import "../../libraries/Addresses.sol";

/**
  Implementation of the basic standard multi-token.
  See https://eips.ethereum.org/EIPS/eip-1155
  Originally based on code by Enjin: https://github.com/enjin/erc-1155

  _Available since v3.1.
*/
contract ERC1155 is ERC165, IERC1155 {
    using Addresses for address;

    // Mapping from token ID to account balances.
    mapping(uint256 => mapping(address => uint256)) internal _balances;

    // Mapping from account to operator approvals.
    mapping(address => mapping(address => bool)) private _operatorApprovals;

    // bytes4(keccak256('balanceOf(address,uint256)')) == 0x00fdd58e
    // bytes4(keccak256('balanceOfBatch(address[],uint256[])')) == 0x4e1273f4
    // bytes4(keccak256('setApprovalForAll(address,bool)')) == 0xa22cb465
    // bytes4(keccak256('isApprovedForAll(address,address)')) == 0xe985e9c5
    // bytes4(keccak256('safeTransferFrom(address,address,uint256,uint256,bytes)')) == 0xf242432a
    // bytes4(keccak256('safeBatchTransferFrom(address,address,uint256[],uint256[],bytes)')) == 0x2eb2c2d6
    // => 0x00fdd58e ^ 0x4e1273f4 ^ 0xa22cb465 ^
    //    0xe985e9c5 ^ 0xf242432a ^ 0x2eb2c2d6 == 0xd9b67a26 .
    bytes4 private constant INTERFACE_ID_ERC1155 = 0xd9b67a26;

    constructor() public {
        registerInterface(INTERFACE_ID_ERC1155);
    }

    /**
      See {IERC1155-balanceOf}.

      Requirements:

      - `account` cannot be the zero address.
    */
    function balanceOf(address account, uint256 id) public view virtual override returns (uint256) {
        require(account != address(0), "ERC1155: balance query for the zero address");
        return _balances[id][account];
    }

    /**
      See {IERC1155-balanceOfBatch}.

      Requirements:

      - `accounts` and `ids` must have the same length.
    */
    function balanceOfBatch(address[] memory accounts, uint256[] memory ids)
        public
        view
        virtual
        override
        returns (uint256[] memory)
    {
        require(accounts.length == ids.length, "ERC1155: accounts and ids length mismatch");

        uint256[] memory batchBalances = new uint256[](accounts.length);

        for (uint256 i = 0; i < accounts.length; ++i) {
            batchBalances[i] = balanceOf(accounts[i], ids[i]);
        }

        return batchBalances;
    }

    /**
      See {IERC1155-setApprovalForAll}.
    */
    function setApprovalForAll(address operator, bool approved) public virtual override {
        require(msg.sender != operator, "ERC1155: setting approval status for self");

        _operatorApprovals[msg.sender][operator] = approved;
        emit ApprovalForAll(msg.sender, operator, approved);
    }

    /**
      See {IERC1155-isApprovedForAll}.
    */
    function isApprovedForAll(address account, address operator)
        public
        view
        virtual
        override
        returns (bool)
    {
        return _operatorApprovals[account][operator];
    }

    /**
      See {IERC1155-safeTransferFrom}.
    */
    function safeTransferFrom(
        address from,
        address to,
        uint256 id,
        uint256 amount,
        bytes memory data
    ) public virtual override {
        require(
            from == msg.sender || isApprovedForAll(from, msg.sender),
            "ERC1155: caller is not owner nor approved"
        );
        _safeTransferFrom(from, to, id, amount, data);
    }

    /**
      See {IERC1155-safeBatchTransferFrom}.
    */
    function safeBatchTransferFrom(
        address from,
        address to,
        uint256[] memory ids,
        uint256[] memory amounts,
        bytes memory data
    ) public virtual override {
        require(
            from == msg.sender || isApprovedForAll(from, msg.sender),
            "ERC1155: transfer caller is not owner nor approved"
        );
        _safeBatchTransferFrom(from, to, ids, amounts, data);
    }

    /**
      Transfers `amount` tokens of token type `id` from `from` to `to`.

      Emits a {TransferSingle} event.

      Requirements:

      - `to` cannot be the zero address.
      - `from` must have a balance of tokens of type `id` of at least `amount`.
      - If `to` refers to a smart contract, it must implement {IERC1155Receiver-onERC1155Received} and return the
      acceptance magic value.
    */
    function _safeTransferFrom(
        address from,
        address to,
        uint256 id,
        uint256 amount,
        bytes memory data
    ) internal virtual {
        require(to != address(0), "ERC1155: transfer to the zero address");

        address operator = msg.sender;

        uint256 fromBalance = _balances[id][from];
        require(fromBalance >= amount, "ERC1155: insufficient balance for transfer");
        _balances[id][from] = fromBalance - amount;
        _balances[id][to] += amount;

        emit TransferSingle(operator, from, to, id, amount);
        _doSafeTransferAcceptanceCheck(operator, from, to, id, amount, data);
    }

    /**
      Emits a {TransferBatch} event.

      Requirements:

      - If `to` refers to a smart contract, it must implement {IERC1155Receiver-onERC1155BatchReceived} and return the
      acceptance magic value.
    */
    function _safeBatchTransferFrom(
        address from,
        address to,
        uint256[] memory ids,
        uint256[] memory amounts,
        bytes memory data
    ) internal virtual {
        require(ids.length == amounts.length, "ERC1155: ids and amounts length mismatch");
        require(to != address(0), "ERC1155: transfer to the zero address");

        address operator = msg.sender;

        for (uint256 i = 0; i < ids.length; ++i) {
            uint256 id = ids[i];
            uint256 amount = amounts[i];

            uint256 fromBalance = _balances[id][from];
            require(fromBalance >= amount, "ERC1155: insufficient balance for transfer");
            _balances[id][from] = fromBalance - amount;
            _balances[id][to] += amount;
        }

        emit TransferBatch(operator, from, to, ids, amounts);
        _doSafeBatchTransferAcceptanceCheck(operator, from, to, ids, amounts, data);
    }

    /**
      Creates `amount` tokens of token type `id`, and assigns them to `to`.

      Emits a {TransferSingle} event.

      Requirements:

      - `to` cannot be the zero address.
      - If `to` refers to a smart contract, it must implement {IERC1155Receiver-onERC1155Received} and return the
      acceptance magic value.
    */
    function _mint(
        address to,
        uint256 id,
        uint256 amount,
        bytes memory data
    ) internal virtual {
        require(to != address(0), "ERC1155: mint to the zero address");

        address operator = msg.sender;

        _balances[id][to] += amount;
        emit TransferSingle(operator, address(0), to, id, amount);
        _doSafeTransferAcceptanceCheck(operator, address(0), to, id, amount, data);
    }

    /**
      Requirements:

      - `ids` and `amounts` must have the same length.
      - If `to` refers to a smart contract, it must implement {IERC1155Receiver-onERC1155BatchReceived} and return the
      acceptance magic value.
    */
    function _mintBatch(
        address to,
        uint256[] memory ids,
        uint256[] memory amounts,
        bytes memory data
    ) internal virtual {
        require(to != address(0), "ERC1155: mint to the zero address");
        require(ids.length == amounts.length, "ERC1155: ids and amounts length mismatch");

        address operator = msg.sender;

        for (uint256 i = 0; i < ids.length; i++) {
            _balances[ids[i]][to] += amounts[i];
        }

        emit TransferBatch(operator, address(0), to, ids, amounts);
        _doSafeBatchTransferAcceptanceCheck(operator, address(0), to, ids, amounts, data);
    }

    /**
      Destroys `amount` tokens of token type `id` from `from`

      Requirements:

      - `from` cannot be the zero address.
      - `from` must have at least `amount` tokens of token type `id`.
    */
    function _burn(
        address from,
        uint256 id,
        uint256 amount
    ) internal virtual {
        require(from != address(0), "ERC1155: burn from the zero address");

        address operator = msg.sender;

        uint256 accountBalance = _balances[id][from];
        require(accountBalance >= amount, "ERC1155: burn amount exceeds balance");
        _balances[id][from] = accountBalance - amount;

        emit TransferSingle(operator, from, address(0), id, amount);
    }

    /**
      Requirements:

      - `ids` and `amounts` must have the same length.
    */
    function _burnBatch(
        address from,
        uint256[] memory ids,
        uint256[] memory amounts
    ) internal virtual {
        require(from != address(0), "ERC1155: burn from the zero address");
        require(ids.length == amounts.length, "ERC1155: ids and amounts length mismatch");

        address operator = msg.sender;

        for (uint256 i = 0; i < ids.length; i++) {
            uint256 id = ids[i];
            uint256 amount = amounts[i];
            uint256 accountBalance = _balances[id][from];
            require(accountBalance >= amount, "ERC1155: burn amount exceeds balance");
            _balances[id][from] = accountBalance - amount;
        }

        emit TransferBatch(operator, from, address(0), ids, amounts);
    }

    function _doSafeTransferAcceptanceCheck(
        address operator,
        address from,
        address to,
        uint256 id,
        uint256 amount,
        bytes memory data
    ) private {
        if (to.isContract()) {
            try IERC1155Receiver(to).onERC1155Received(operator, from, id, amount, data) returns (
                bytes4 response
            ) {
                if (response != IERC1155Receiver(to).onERC1155Received.selector) {
                    revert("ERC1155: ERC1155Receiver rejected tokens");
                }
            } catch Error(string memory reason) {
                revert(reason);
            } catch {
                revert("ERC1155: transfer to non ERC1155Receiver implementer");
            }
        }
    }

    function _doSafeBatchTransferAcceptanceCheck(
        address operator,
        address from,
        address to,
        uint256[] memory ids,
        uint256[] memory amounts,
        bytes memory data
    ) private {
        if (to.isContract()) {
            try
                IERC1155Receiver(to).onERC1155BatchReceived(operator, from, ids, amounts, data)
            returns (bytes4 response) {
                if (response != IERC1155Receiver.onERC1155BatchReceived.selector) {
                    revert("ERC1155: ERC1155Receiver rejected tokens");
                }
            } catch Error(string memory reason) {
                revert(reason);
            } catch {
                revert("ERC1155: transfer to non ERC1155Receiver implementer");
            }
        }
    }
}
