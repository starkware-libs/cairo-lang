import os

from starkware.cairo.common.dict import DictManager
from starkware.cairo.common.small_merkle_tree import MerkleTree
from starkware.cairo.common.test_utils import CairoFunctionRunner
from starkware.cairo.lang.builtins.hash.hash_builtin_runner import CELLS_PER_HASH
from starkware.cairo.lang.compiler.cairo_compile import compile_cairo_files
from starkware.native_crypto.native_crypto import pedersen_hash

CAIRO_FILE = os.path.join(os.path.dirname(__file__), 'small_merkle_tree.cairo')
PRIME = 2**251 + 17 * 2**192 + 1
MERKLE_HEIGHT = 2


def test_cairo_merkle_multi_update():
    program = compile_cairo_files([CAIRO_FILE], prime=PRIME, debug_info=True)
    runner = CairoFunctionRunner(program)

    dict_manager = DictManager()
    squashed_dict_start = dict_manager.new_dict(
        segments=runner.segments, initial_dict={1: 10, 2: 20, 3: 30})

    # Change the value at 1 from 10 to 11 and at 3 from 30 to 31.
    squashed_dict = [1, 10, 11, 3, 30, 31]
    squashed_dict_end = runner.segments.write_arg(ptr=squashed_dict_start, arg=squashed_dict)
    dict_tracker = dict_manager.get_tracker(squashed_dict_start)
    dict_tracker.current_ptr = squashed_dict_end
    dict_tracker.data[1] = 11
    dict_tracker.data[3] = 31

    runner.run(
        'small_merkle_tree', runner.hash_builtin.base, squashed_dict_start, squashed_dict_end,
        MERKLE_HEIGHT, hint_locals=dict(__dict_manager=dict_manager))
    hash_ptr, prev_root, new_root = runner.get_return_values(3)
    N_MERKLE_TREES = 2
    N_HASHES_PER_TREE = 3
    assert hash_ptr == \
        runner.hash_builtin.base + N_MERKLE_TREES * N_HASHES_PER_TREE * CELLS_PER_HASH
    assert prev_root == pedersen_hash(pedersen_hash(0, 10), pedersen_hash(20, 30))
    assert new_root == pedersen_hash(pedersen_hash(0, 11), pedersen_hash(20, 31))


def test_merkle_tree():
    tree = MerkleTree(tree_height=2, default_leaf=10)
    expected_hash = pedersen_hash(pedersen_hash(10, 10), pedersen_hash(10, 10))
    assert tree.compute_merkle_root([]) == expected_hash
    # Change leaf 1 to 7.
    expected_hash = pedersen_hash(pedersen_hash(10, 7), pedersen_hash(10, 10))
    assert tree.compute_merkle_root([(1, 7)]) == expected_hash
    assert tree.compute_merkle_root([]) == expected_hash
