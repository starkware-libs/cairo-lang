from starkware.cairo.common.cairo_builtins import PoseidonBuiltin
from starkware.cairo.common.dict import DictAccess
from starkware.cairo.common.patricia_utils import PatriciaUpdateConstants
from starkware.cairo.common.patricia_with_sponge import (
    patricia_update_using_update_constants as patricia_update_using_update_constants_with_sponge,
)
from starkware.cairo.common.sponge_as_hash import SpongeHashBuiltin

func patricia_update_using_update_constants{poseidon_ptr: PoseidonBuiltin*, range_check_ptr}(
    patricia_update_constants: PatriciaUpdateConstants*,
    update_ptr: DictAccess*,
    n_updates: felt,
    height: felt,
    prev_root: felt,
    new_root: felt,
) {
    let hash_ptr = cast(poseidon_ptr, SpongeHashBuiltin*);

    with hash_ptr {
        patricia_update_using_update_constants_with_sponge(
            patricia_update_constants=patricia_update_constants,
            update_ptr=update_ptr,
            n_updates=n_updates,
            height=height,
            prev_root=prev_root,
            new_root=new_root,
        );
    }

    // Update poseidon_ptr.
    let poseidon_ptr = cast(hash_ptr, PoseidonBuiltin*);

    return ();
}
