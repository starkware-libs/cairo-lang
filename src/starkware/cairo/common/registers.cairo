from starkware.cairo.lang.compiler.lib.registers import get_ap, get_fp_and_pc

// Takes the value of a label (relative to program base) and returns the actual runtime address of
// that label in the memory.
//
// Usage example:
//
// func do_callback(...) {
//     ...
// }
//
// func do_thing_then_callback(callback) {
//     ...
//     call abs callback;
// }
//
// func main() {
//     let (callback_address) = get_label_location(do_callback);
//     do_thing_then_callback(callback=callback_address);
// }
func get_label_location(label_value: codeoffset) -> (res: felt*) {
    let (_, pc_val) = get_fp_and_pc();

    ret_pc_label:
    return (res=pc_val + (label_value - ret_pc_label));
}
