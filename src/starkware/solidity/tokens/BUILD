load("//bazel_utils:solidity.bzl", "sol_library")

package(default_visibility = ["//visibility:public"])

sol_library(
    name = "erc20_sol",
    srcs = [
        "//src/starkware/solidity/tokens/ERC20:ERC20.sol",
        "//src/starkware/solidity/tokens/ERC20:IERC20.sol",
        "//src/starkware/solidity/tokens/ERC20:IERC20Metadata.sol",
    ],
    deps = [],
)

sol_library(
    name = "token_interfaces_sol",
    srcs = [
        "//src/starkware/solidity/tokens/ERC1155:IERC1155.sol",
        "//src/starkware/solidity/tokens/ERC20:IERC20.sol",
        "//src/starkware/solidity/tokens/ERC721:IERC721.sol",
    ],
    deps = [],
)
