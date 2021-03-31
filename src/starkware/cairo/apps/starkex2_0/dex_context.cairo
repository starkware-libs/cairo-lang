# ***********************************************************************
# * This code is licensed under the Cairo Program License.              *
# * The license can be found in: licenses/CairoProgramLicense.txt       *
# ***********************************************************************

from starkware.cairo.apps.starkex2_0.common.registers import get_fp_and_pc

# A representation of a DEX context struct.

struct DexContext:
    member vault_tree_height : felt
    member order_tree_height : felt
    member global_expiration_timestamp : felt
end

# Returns a pointer to a new DexContext struct.
func make_dex_context(vault_tree_height, order_tree_height, global_expiration_timestamp) -> (
        addr : DexContext*):
    let (__fp__, _) = get_fp_and_pc()
    return (addr=cast(__fp__ - 2 - DexContext.SIZE, DexContext*))
end
