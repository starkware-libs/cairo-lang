import patricia.traverse_result.traverse_result

def traverse_empty (n_steps: ℕ) (height: ℤ) (path: ℕ) (res: TraverseResult) : Prop :=
---func traverse_empty{update_ptr: DictAccess*, range_check_ptr, siblings: Sibling*}(
---    globals: ParticiaGlobals*, height: felt, path: felt
---) {
  match n_steps with
  | 0 => False
  | n_steps_m1 + 1 =>

---    if (height == 0) {
  if height = 0 then
---        assert update_ptr.key = path;
---        let value = [cast(update_ptr, felt*) + globals.access_offset];
---        assert value = 0;
---        let update_ptr = update_ptr + DictAccess.SIZE;
    res = .update ⟨path, 0⟩
---        return ();
---    }
  else ((
    ∃ (res₀ res₁: TraverseResult),
---
---    // Decide non deterministically if we should traverse both children or just one.
---    // This is more efficient that trying to determine it from update_ptr.
---    %{
---        from starkware.python.merkle_tree import decode_node
---        left_child, right_child, case = decode_node(node)
---        memory[ap] = 1 if case != 'both' else 0
---    %}
---    jmp skip_both if [ap] != 0, ap++;
---
---    // Traverse both children.
---    %{ vm_enter_scope(dict(node=left_child, **common_args)) %}
---    traverse_empty(globals=globals, height=height - 1, path=path * 2);
      traverse_empty n_steps_m1 (height - 1) (path * 2) res₀ ∧
---    %{ vm_exit_scope() %}
---
---    %{ vm_enter_scope(dict(node=right_child, **common_args)) %}
---    traverse_empty(globals=globals, height=height - 1, path=path * 2 + 1);
      traverse_empty n_steps_m1 (height - 1) (path * 2 + 1) res₁ ∧
      res = res₀.add res₁
---    %{ vm_exit_scope() %}
---    return ();
  ) ∨ (
---
---    skip_both:
---    %{
---        descend = descent_map.get((ids.height, ids.path))
---        memory[ap] = 0 if descend is None else 1
---    %}
---    jmp skip_single if [ap] != 0, ap++;
---
---    // Single.
---    let child_bit = [ap];
    ∃ (res₀: TraverseResult) (child_bit: Fin 2),
---    %{
---        ids.child_bit = 0 if case == 'left' else 1
---        new_node = left_child if case == 'left' else right_child
---        vm_enter_scope(dict(node=new_node, **common_args))
---    %}
---    child_bit = child_bit * child_bit, ap++;
---    assert siblings[0] = Sibling(type=0, value=0);
---    let siblings = &siblings[1];
    let res_sib := TraverseResult.sibling 0
---    traverse_empty(globals=globals, height=height - 1, path=path * 2 + child_bit);
    traverse_empty n_steps_m1 (height - 1) (path * 2 + child_bit) res₀ ∧
    res = res_sib.add res₀
---    %{ vm_exit_scope() %}
---    return ();
  ) ∨ (
---
---    skip_single:
---    // Descend.
---    tempvar length;
---    tempvar word;
    ∃ (res₀: TraverseResult) (word length_m2: ℕ),
      let length := length_m2 + 2;
---    %{ ids.length, ids.word = descend %}
---    assert siblings[0] = Sibling(type=1, value=length);
---    let siblings = &siblings[1];
      let res_sib := TraverseResult.descent length
---
---    assert_in_range(length, 2, height + 1);
      length ≤ height ∧
---    tempvar length_pow2 = globals.pow2[length];
---    // TODO(spapini,27/09/2021): Consider calling assert_nn_lt nondeterministically.
---    assert_lt_felt(word, length_pow2);
      word < 2 ^ length ∧
---    %{
---        new_node = node
---        for i in range(ids.length - 1, -1, -1):
---            new_node = new_node[(ids.word >> i) & 1]
---        vm_enter_scope(dict(node=new_node, **common_args))
---    %}
---    traverse_empty(globals=globals, height=height - length, path=path * length_pow2 + word);
      traverse_empty n_steps_m1 (height - length) (path * 2 ^ length + word) res₀ ∧
---    %{ vm_exit_scope() %}
---    return ();
      res = res_sib.add res₀
  ))
---}
