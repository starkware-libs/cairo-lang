# Calls func_ptr(args[0], args[1], ..., args[n_args - 1]) and forwards its return value.
# In order to convert a label to pc and use it as a value for the func_ptr argument,
# use get_label_location().
func invoke(func_ptr, n_args : felt, args : felt*):
    invoke_prepare_args(args_end=args + n_args, n_args=n_args)
    call abs func_ptr
    ret
end

# Helper function for invoke().
# Copies the memory range [args_end - n_args, args_end) to the memory range
# [final_ap - n_args, final_ap) where final_ap is the value of ap when the function returns.
func invoke_prepare_args(args_end : felt*, n_args : felt):
    if n_args == 0:
        return ()
    end

    invoke_prepare_args(args_end=args_end - 1, n_args=n_args - 1)
    [ap] = [args_end - 1]; ap++
    return ()
end
