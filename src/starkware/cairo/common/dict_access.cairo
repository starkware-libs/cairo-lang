// Represents an access (read, write or modify) to the dictionary. The dictionary is represented as
// a chronological list of such accesses. The "current" value of a key is the new_value of the last
// access with that key.
// In a valid dictionary, the prev_value of each access is equal to the new_value of the previous
// access to the same key.
struct DictAccess {
    key: felt,
    prev_value: felt,
    new_value: felt,
}
