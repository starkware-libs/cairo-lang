# Returns the contents of the fp and pc registers of the calling function.
# The pc register's value is the address of the instruction that follows directly after the
# invocation of get_fp_and_pc().
func get_fp_and_pc() -> (fp_val, pc_val):
    # The call instruction itself already places the old fp and the return pc at [fp - 2], [fp - 1].
    # Thus, we can simply return, and the calling function may regard these as the return values
    # of this function.
    return (...)
end

# Returns the content of the ap register just before this function was invoked.
func get_ap() -> (ap_val):
    # Once get_ap() is invoked, fp points to ap + 2 (since the call instruction placed the old fp
    # and pc in memory, advancing ap accordingly).
    # Calling dummy_func places fp and pc at [fp], [fp + 1] (respectively), and advances ap by 2.
    # Hence, going two cells above we get [fp] = ap + 2, and by subtracting 2 we get the desired ap
    # value.
    call dummy_func
    return (ap_val=[ap - 2] - 2)
end

func dummy_func():
    return ()
end

# Takes the value of a label (relative to program base) and returns the actual runtime address of
# that label in the memory.
#
# Example usage:
#
# func do_callback(...):
#     ...
# end
#
# func do_thing_then_callback(callback):
#     ...
#     call abs callback
# end
#
# func main():
#     let (callback_address) = get_label_location(do_callback)
#     do_thing_then_callback(callback=callback_address)
# end
func get_label_location(label_value) -> (res):
    let (_, pc_val) = get_fp_and_pc()

    ret_pc_label:
    return (res=label_value + pc_val - ret_pc_label)
end
