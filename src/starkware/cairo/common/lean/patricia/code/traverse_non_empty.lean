import patricia.code.node_edge
import patricia.code.traverse_empty
import patricia.crypto

def open_edge (crypto: Crypto) (node: ℕ) (edge: NodeEdge): Prop :=
---func open_edge{hash_ptr: HashBuiltin*, range_check_ptr}(globals: ParticiaGlobals*, node: felt) -> (
---    edge: NodeEdge*
---) {
---    alloc_locals;
---    local edge: NodeEdge*;
---
---    %{
---        ids.edge = segments.add()
---        ids.edge.length, ids.edge.path, ids.edge.bottom = preimage[ids.node]
---        ids.hash_ptr.result = ids.node - ids.edge.length
---        if __patricia_skip_validation_runner is not None:
---            # Skip validation of the preimage dict to speed up the VM. When this flag is set,
---            # mistakes in the preimage dict will be discovered only in the prover.
---            __patricia_skip_validation_runner.verified_addresses.add(
---                ids.hash_ptr + ids.HashBuiltin.result)
---    %}
---    // Validity checks.
---    assert_in_range(edge.length, 1, MAX_LENGTH + 1);
  edge.length ≥ 1 ∧ edge.length ≤ crypto.max_height ∧
---    // TODO(spapini,27/09/2021): Consider calling assert_nn_lt nondeterministically.
---    assert_lt_felt(edge.path, globals.pow2[edge.length]);
  edge.path < 2 ^ edge.length ∧
---    // Note: we do not explicitly verify that bottom_hash is binary or leaf here, since it will be
---    // verified later in the algorithm if necessary.
---    assert hash_ptr.x = edge.bottom;
  let x := edge.bottom
---    assert hash_ptr.y = edge.path;
  let y := edge.path
---    // PREPARE_ADDITIONAL_HASH_INPUTS_MACRO(hash_ptr)
---    assert node = hash_ptr.result + edge.length;
  node = (crypto.hash x y) + edge.length
---    let hash_ptr = hash_ptr + HashBuiltin.SIZE;
---    return (edge=edge);
---}

mutual

def traverse_non_empty (crypto: Crypto) (n_steps: ℕ) (is_new_tree: Bool) (height: ℤ) (path node: ℕ) (res: TraverseResult) : Prop := (
---func traverse_non_empty{
---    hash_ptr: HashBuiltin*, range_check_ptr, update_ptr: DictAccess*, siblings: Sibling*
---}(globals: ParticiaGlobals*, height: felt, path: felt, node: felt) {
  match n_steps with
  | 0 => False
  | n_steps + 1 =>

---    %{ memory[ap] = 1 if ids.height == 0 or len(preimage[ids.node]) == 2 else 0 %}
---    jmp binary if [ap] != 0, ap++;
---    // Edge.
  (∃ edge: NodeEdge,
---    let (edge) = open_edge(globals=globals, node=node);
    open_edge crypto node edge ∧
---    traverse_edge(globals=globals, height=height, path=path, edge=[edge]);
    traverse_edge crypto n_steps is_new_tree height path edge res
---    return ();
  ) ∨ (
---
---    // Binary.
---    binary:
---    return traverse_binary_or_leaf(globals=globals, height=height, path=path, node=node);
    traverse_binary_or_leaf crypto n_steps is_new_tree height path node res
---}
  ))




def traverse_binary_or_leaf (crypto: Crypto) (n_steps: ℕ) (is_new_tree: Bool) (height: ℤ) (path node: ℕ) (res: TraverseResult) : Prop :=
---func traverse_binary_or_leaf{
---    hash_ptr: HashBuiltin*, range_check_ptr, update_ptr: DictAccess*, siblings: Sibling*
---}(globals: ParticiaGlobals*, height: felt, path: felt, node: felt) {
  match n_steps with
  | 0 => False
  | n_steps + 1 =>

---    if (height == 0) {
  (if height = 0 then
---        // Leaf.
---        assert update_ptr.key = path;
---        tempvar value = [cast(update_ptr, felt*) + globals.access_offset];
---        assert value = node;
---        assert_not_zero(value);
---        let update_ptr = update_ptr + DictAccess.SIZE;
---        return ();
    res = .update ⟨path, node⟩ ∧ node ≠ 0
---    }
  else
---
---    alloc_locals;
---
---    // Binary.
    ∃ x y,
---    let current_hash = hash_ptr;
---    let hash_ptr = hash_ptr + HashBuiltin.SIZE;
      node = crypto.hash x y ∧ (
---    // PREPARE_ADDITIONAL_HASH_INPUTS_MACRO(current_hash)
---    assert current_hash.result = node;
---
---    %{
---        from starkware.python.merkle_tree import decode_node
---        left_child, right_child, case = decode_node(node)
---        left_hash, right_hash = preimage[ids.node]
---
---        # Fill non deterministic hashes.
---        hash_ptr = ids.current_hash.address_
---        memory[hash_ptr + ids.HashBuiltin.x] = left_hash
---        memory[hash_ptr + ids.HashBuiltin.y] = right_hash
---
---        if __patricia_skip_validation_runner:
---            # Skip validation of the preimage dict to speed up the VM. When this flag is set,
---            # mistakes in the preimage dict will be discovered only in the prover.
---            __patricia_skip_validation_runner.verified_addresses.add(
---                hash_ptr + ids.HashBuiltin.result)
---
---        memory[ap] = int(case != 'both')
---    %}
---    jmp skip_both if [ap] != 0, ap++;
---
        (
          ∃ res₀ res₁,
---    // Case 1: the updates are in both subtrees.
---    //
---    // (1) Traverse both children.
---    // (2) No sibling.
---
---    // Traverse both children.
---    %{ vm_enter_scope(dict(node=left_child, **common_args)) %}
---    traverse_non_empty(globals=globals, height=height - 1, path=path * 2, node=current_hash.x);
          traverse_non_empty crypto n_steps is_new_tree (height - 1) (path * 2) x res₀ ∧
---    %{ vm_exit_scope() %}
---    // TODO(spapini,25/08/2021): Fix the consecutive hint issue.
---    tempvar left_child = path * 2;
---    %{ vm_enter_scope(dict(node=right_child, **common_args)) %}
---    traverse_non_empty(
---        globals=globals, height=height - 1, path=left_child + 1, node=current_hash.y
---    );
          traverse_non_empty crypto n_steps is_new_tree (height - 1) (path * 2 + 1) y res₁ ∧
          res = res₀.add res₁
---    %{ vm_exit_scope() %}
        ) ∨ ( -- Left.
          ∃ res₁,
---    return ();
---
---    skip_both:
---    %{ memory[ap] = int(case != 'left') %}
---    jmp skip_left if [ap] != 0, ap++;
---
---    // Case 2: the updates are only in the left subtree.
---    //
---    // (1) Traverse the left child.
---    // (2) The sibling is the right child (must be non-zero).
---
---    // Left.
---    tempvar sib = current_hash.y;
          let sib := y
---    assert_not_zero(sib);
          sib ≠ 0 ∧
---    assert siblings[0] = Sibling(type=0, value=sib);
---    let siblings = &siblings[1];
          let res₀ := TraverseResult.sibling sib
---    %{ vm_enter_scope(dict(node=left_child, **common_args)) %}
---    traverse_non_empty(globals=globals, height=height - 1, path=path * 2, node=current_hash.x);
          traverse_non_empty crypto n_steps is_new_tree (height - 1) (path * 2) x res₁ ∧
          res = res₀.add res₁
---    %{ vm_exit_scope() %}
---    return ();
        ) ∨ ( -- Right.
          ∃ res₁,
---
---    skip_left:
---    %{ assert case == 'right' %}
---
---    // Case 3: the updates are only in the right subtree.
---    //
---    // (1) Traverse the right child.
---    // (2) The sibling is the left child (must be non-zero).
---
---    // Right.
---    tempvar sib = current_hash.x;
          let sib := x
---    assert_not_zero(sib);
          sib ≠ 0 ∧
---    assert siblings[0] = Sibling(type=0, value=sib);
---    let siblings = &siblings[1];
          let res₀ := TraverseResult.sibling sib
---    %{ vm_enter_scope(dict(node=right_child, **common_args)) %}
---    traverse_non_empty(globals=globals, height=height - 1, path=path * 2 + 1, node=current_hash.y);
          traverse_non_empty crypto n_steps is_new_tree (height - 1) (path * 2 + 1) y res₁ ∧
          res = res₀.add res₁
---    %{ vm_exit_scope() %}
---    return ();
---}
        )
      ))

def traverse_edge_regular (crypto: Crypto) (n_steps_m1: ℕ) (is_new_tree: Bool) (height: ℤ) (path: ℕ) (edge: NodeEdge)
    (res: TraverseResult) (bit: Fin 2) (new_edge: NodeEdge) : Prop :=
  (
    ∃ (res₀ res₁: TraverseResult),
---    // Traverse edge regular.
---
---    // Case 1: the updates are in both subtrees.
---    //
---    // (1) traverse both children.
---    // (2) No sibling.
---
---    // Traverse both children.
---    if (bit == 0) {
    (if bit = 0 then
---        %{ vm_enter_scope(dict(node=left_child, **common_args)) %}
---        traverse_edge(globals=globals, height=height - 1, path=path * 2, edge=new_edge);
      traverse_edge crypto n_steps_m1 is_new_tree (height - 1) (path * 2) new_edge res₀ ∧
---        %{ vm_exit_scope() %}
---        local hash_ptr: HashBuiltin* = hash_ptr;
---
---        %{ vm_enter_scope(dict(node=right_child, **common_args)) %}
---        traverse_empty(globals=globals, height=height - 1, path=path * 2 + 1);
      traverse_empty n_steps_m1 (height - 1) (path * 2 + 1) res₁
---        %{ vm_exit_scope() %}
---        return ();
---    } else {
    else
---        %{ vm_enter_scope(dict(node=left_child, **common_args)) %}
---        traverse_empty(globals=globals, height=height - 1, path=path * 2);
      traverse_empty n_steps_m1 (height - 1) (path * 2) res₀ ∧
---        %{ vm_exit_scope() %}
---
---        %{ vm_enter_scope(dict(node=right_child, **common_args)) %}
---        traverse_edge(globals=globals, height=height - 1, path=path * 2 + 1, edge=new_edge);
      traverse_edge crypto n_steps_m1 is_new_tree (height - 1) (path * 2 + 1) new_edge res₁
---        %{ vm_exit_scope() %}
---        return ();
---    }
    ) ∧
    res = res₀.add res₁
---
---    skip_both:
---    %{ memory[ap] = int(case == 'right') ^ ids.bit %}
---    jmp skip_non_empty_child if [ap] != 0, ap++;
---
  ) ∨ (
    ∃ res₁,
---    // Case 2: all the updates are in one of the two subtrees and the other subtree is zero
---    //   (in particular, all the updates are in the direction of the edge).
---    //
---    // (1) traverse the non-empty child.
---    // (2) sibling is zero.
---
---    // Traverse the non-empty child.
---    assert siblings[0] = Sibling(type=0, value=0);
---    let siblings = &siblings[1];
    let res₀ := TraverseResult.sibling 0
---    %{
---        new_node = left_child if ids.bit == 0 else right_child
---        vm_enter_scope(dict(node=new_node, **common_args))
---    %}
---    traverse_edge(globals=globals, height=height - 1, path=path * 2 + bit, edge=new_edge);
    traverse_edge crypto n_steps_m1 is_new_tree (height - 1) (path * 2 + bit) new_edge res₁ ∧
    res = res₀.add res₁
---    %{ vm_exit_scope() %}
---    return ();
---
  ) ∨ (
    ∃ res₁,
---    skip_non_empty_child:
---    // Case 3: all the updates are in one of the two subtrees and that subtree is zero
---    //   (in particular, all the updates have zero values).
---    //
---    // (1) Traverse the empty child to visit the updates.
---    // (2) Its sibling is:
---    //   (a) If edge.length > 1, an edge of length smaller by 1:
---    //       H(edge.bottom, new_path) + (edge.length - 1)
---    //   (b) If edge.length = 1, the sibling is edge.bottom.
---    //
---    // We require height == 1 => edge.length = 1, for the following to be true:
---    // If edge.length > 1, then height > 1 => sibling is not a leaf.
---    // In this case the sibling `H(edge.bottom, new_path) + (edge.length - 1)` represents
---    // a proper edge. Since it's the sibling, it is identical in both prev and new trees, and
---    // therefore (as it appears in the prev tree), it must be a valid edge
---    // (its length is <= height and its bottom is not empty and not an edge).
---
---    if (height == 1) {
---        assert edge.length = 1;
---    }
    (height = 1 → edge.length = 1) ∧
---
---    // Traverse the empty child.
---    local range_check_ptr = range_check_ptr;
---    local new_hash_ptr: HashBuiltin*;
---
---    // Reserve a spot for the sibling. It is more efficient to compute it after the recursive
---    // traversal.
---    let current_sibling = &siblings[0];
---    let siblings = &siblings[1];
---
---    // Traverse empty side.
---    %{
---        new_node = left_child if ids.bit == 1 else right_child
---        vm_enter_scope(dict(node=new_node, **common_args))
---    %}
---    traverse_empty(globals=globals, height=height - 1, path=path * 2 + 1 - bit);
    traverse_empty n_steps_m1 (height - 1) (path * 2 + 1 - bit) res₁ ∧
---    %{ vm_exit_scope() %}
---
---    // Check that the resulting topology is valid.
---    //
---    // To illustrate, consider the following example: an edge A->B of length L, children C,X of B,
---    // and a deleted child D of C (D may be a deleted leaf, or a subtree that becomes empty):
---    //
---    //     A                A
---    //      \                \
---    //       \ L              \
---    //        \                \ L+1
---    //         B        ->      \
---    //       /   \               \
---    //      C     X               X
---    //       \
---    //        D
---    //
---    // By the traversal of the previous tree, we know X is a valid node, but we do not guarantee the
---    // type of node X is - it could potentially be an edge node, in which case the above drawing is
---    // an invalid tree topology (if X is the bottom of an edge A->X, then X cannot be an edge, as
---    // two consecutive edges is illegal in a Patricia tree).
---    // Without the following check, a malicious prover could inject an invalid edge node starting at
---    // X. This is especially important for allowing escape-hatch mechanisms: if a user only has the
---    // data-availability (state of the leaves), in order to prove the state of any leaf the user
---    // must rely on the tree being well-formed.
---    if (edge.length == 1) {
    if edge.length = 1 then
---        // In this case, the sibling is the bottom of our edge.
---        // Make sure edge.bottom is binary or a non-zero leaf.
---        assert [current_sibling] = Sibling(type=0, value=edge.bottom);
      let res₀ := TraverseResult.sibling edge.bottom
---        if (height != 1) {
      if height ≠ 1 then
---            // This check should only be done on the new tree.
---            if (globals.access_offset == 2) {
        (is_new_tree → (∃ x y,
---                // PREPARE_ADDITIONAL_HASH_INPUTS_MACRO(hash_ptr)
---                hash_ptr.result = edge.bottom;
               edge.bottom = crypto.hash x y
---                %{
---                    ids.hash_ptr.x, ids.hash_ptr.y = preimage[ids.edge.bottom]
---                    if __patricia_skip_validation_runner:
---                        # Skip validation of the preimage dict to speed up the VM. When this flag is
---                        # set, mistakes in the preimage dict will be discovered only in the prover.
---                        __patricia_skip_validation_runner.verified_addresses.add(
---                            ids.hash_ptr + ids.HashBuiltin.result)
---                %}
---                let hash_ptr = hash_ptr + HashBuiltin.SIZE;
---                return ();
---            } else {
---                return ();
---            }
---        } else {
        )) ∧
        res = res₀.add res₁
      else
---            // As `height = edge.length = 1`, edge.bottom is a leaf and we only need to check that
---            // it is not zero.
---            assert_not_zero(edge.bottom);
        edge.bottom ≠ 0 ∧
        res = res₀.add res₁
---        }
---        return ();
---    }
    else
---
---    // This is the case where we split an edge.
---    let (hash) = hash2(edge.bottom, new_edge.path);
      let hash := crypto.hash edge.bottom new_edge.path
---    assert [current_sibling] = Sibling(type=0, value=hash + new_edge.length);
      res = (TraverseResult.sibling (hash + new_edge.length)).add res₁
---    return ();
  )
---
---    descend:

def traverse_edge_descend (crypto: Crypto) (n_steps_m1: ℕ) (is_new_tree: Bool) (height: ℤ) (path: ℕ) (edge: NodeEdge) (res: TraverseResult) : Prop :=
---    descend:
---    // Descent: descend `length` (>= 2) levels along the edge in a single step.
---    // `word` represents the next `length` bits of the path.
---    //
---    // (1) Recurse on the truncated edge.
---    // (2) Record `length` as a Sibling entry in the siblings list.
---
---    local length;
---    local word;
  ∃ (length word: ℕ) (res₁: TraverseResult),
---    %{ ids.length, ids.word = descend %}
---    assert siblings[0] = Sibling(type=1, value=length);
---    let siblings = &siblings[1];
  let res₀ := TraverseResult.descent length
---
---    // Check that the descend is valid.
---    assert_in_range(length, 2, edge.length + 1);
  length ≥ 2 ∧ length ≤ edge.length ∧
---    tempvar length_pow2 = globals.pow2[length];
---    tempvar new_length = edge.length - length;
  let new_length := edge.length - length
---    tempvar new_length_pow2 = globals.pow2[new_length];
---    tempvar new_path = edge.path - word * new_length_pow2;
  let new_path := (edge.path: ℤ) - word * 2 ^ new_length
---    // TODO(spapini,27/09/2021): Consider calling assert_nn_lt nondeterministically.
---    assert_lt_felt(word, length_pow2);
  word < 2 ^ length ∧
---    assert_lt_felt(new_path, new_length_pow2);
  new_path ≥ 0 ∧ new_path < 2 ^ new_length ∧
---
---    let new_edge: NodeEdge = NodeEdge(length=new_length, path=new_path, bottom=edge.bottom);
  let new_edge: NodeEdge := { length := new_length, path := new_path.toNat, bottom := edge.bottom }
---    %{
---        new_node = node
---        for i in range(ids.length - 1, -1, -1):
---            new_node = new_node[(ids.word >> i) & 1]
---        vm_enter_scope(dict(node=new_node, **common_args))
---    %}
---    traverse_edge(
---        globals=globals, height=height - length, path=path * length_pow2 + word, edge=new_edge
---    );
  traverse_edge crypto n_steps_m1 is_new_tree (height - length) (path * 2 ^ length + word) new_edge res₁ ∧
---    %{ vm_exit_scope() %}
---
---    return ();
  res = res₀.add res₁
---}



def traverse_edge (crypto: Crypto) (n_steps: ℕ) (is_new_tree: Bool) (height: ℤ) (path: ℕ) (edge: NodeEdge) (res: TraverseResult) : Prop :=
---func traverse_edge{
---    hash_ptr: HashBuiltin*, range_check_ptr, update_ptr: DictAccess*, siblings: Sibling*
---}(globals: ParticiaGlobals*, height: felt, path: felt, edge: NodeEdge) {
  match n_steps with
  | 0 => False
  | n_steps_m1 + 1 =>
---    if (edge.length == 0) {
  (if edge.length = 0 then
---        return traverse_binary_or_leaf(globals=globals, height=height, path=path, node=edge.bottom);
    traverse_binary_or_leaf crypto n_steps_m1 is_new_tree height path edge.bottom res
---    }
  else (
    (
      ∃ bit: Fin 2,
---
---    alloc_locals;
---
---    %{
---        descend = descent_map.get((ids.height, ids.path))
---        memory[ap] = 0 if descend is None else 1
---    %}
---    jmp descend if [ap] != 0, ap++;
---
---    // Extract one bit from the edge. edge.length is guaranteed to be >= 1.
---    local new_length = edge.length - 1;
      let new_length := edge.length - 1
---    local bound = globals.pow2[new_length];
      let bound := 2 ^ new_length
---    local bit;
---    %{ ids.bit = (ids.edge.path >> ids.new_length) & 1 %}
---    bit * bit = bit;
---    local new_path = edge.path - bit * bound;
      let new_path := (edge.path: ℤ) - bit * bound;
---    // TODO(spapini,27/09/2021): Consider calling assert_nn_lt nondeterministically.
---    assert_lt_felt(new_path, bound);
      new_path ≥ 0 ∧ new_path < bound ∧
---    local new_edge: NodeEdge = NodeEdge(length=new_length, path=new_path, bottom=edge.bottom);
      let new_edge: NodeEdge := { length := new_length, path := new_path.toNat, bottom := edge.bottom }
---
---    // Decide case.
---    %{
---        from starkware.python.merkle_tree import decode_node
---        left_child, right_child, case = decode_node(node)
---        memory[ap] = int(case != 'both')
---    %}
---    jmp skip_both if [ap] != 0, ap++;
---
---    // Traverse edge regular.
      traverse_edge_regular crypto n_steps_m1 is_new_tree height path edge res bit new_edge
    ) ∨
    traverse_edge_descend crypto n_steps_m1 is_new_tree height path edge res
  ))
end
