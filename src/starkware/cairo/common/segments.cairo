# Relocates src_ptr to dest_ptr.
# 'src_ptr' must point to the start of a temporary segment.
#
# See add_relocation_rule() in src/starkware/cairo/lang/vm/memory_dict.py for more details.
func relocate_segment(src_ptr : felt*, dest_ptr : felt*):
    %{ memory.add_relocation_rule(src_ptr=ids.src_ptr, dest_ptr=ids.dest_ptr) %}

    # Add a verifier side assert that src_ptr and dest_ptr are indeed equal.
    assert src_ptr = dest_ptr
    return ()
end
