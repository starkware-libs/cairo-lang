# ***********************************************************************
# * This code is licensed under the Cairo Program License.              *
# * The license can be found in: licenses/CairoProgramLicense.txt       *
# ***********************************************************************

# Returns the contents of the fp and pc registers of the calling function.
# The pc register's value is the address of the instruction that follows directly after the
# invocation of get_fp_and_pc().
func get_fp_and_pc() -> (fp_val, pc_val):
    # The call instruction itself already places the old fp and the return pc at [ap - 2], [ap - 1].
    return (fp_val=[ap - 2], pc_val=[ap - 1])
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
