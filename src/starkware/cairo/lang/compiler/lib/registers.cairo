# Returns the contents of the fp and pc registers of the calling function.
# The pc register's value is the address of the instruction that follows directly after the
# invocation of get_fp_and_pc().
func get_fp_and_pc() -> (fp_val, pc_val):
    # The call instruction itself already places the old fp and the return pc at [ap - 2], [ap - 1].
    return (fp_val=[ap - 2], pc_val=[ap - 1])
end

# Returns the content of the ap register just before this function was invoked.
@known_ap_change
func get_ap() -> (ap_val):
    # Once get_ap() is invoked, fp points to ap + 2 (since the call instruction placed the old fp
    # and pc in memory, advancing ap accordingly).
    # Hence, the desired ap value is fp - 2.
    let (fp_val, pc_val) = get_fp_and_pc()
    return (ap_val=fp_val - 2)
end
