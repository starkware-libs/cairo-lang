// Maximum length of an edge.
const MAX_LENGTH = 251;

// A struct of globals that are passed throughout the algorithm.
struct ParticiaGlobals {
    // An array of size MAX_LENGTH, where pow2[i] = 2**i.
    pow2: felt*,
    // Offset of the relevant value field in DictAccess.
    // 1 if the previous tree is traversed and 2 if the new tree is traversed.
    access_offset: felt,
}

// Represents an edge node: a subtree with a path, s.t. all leaves not under that path are 0.
struct NodeEdge {
    length: felt,
    path: felt,
    bottom: felt,
}

// Holds the constants needed for Patricia updates.
struct PatriciaUpdateConstants {
    globals_pow2: felt*,
}
