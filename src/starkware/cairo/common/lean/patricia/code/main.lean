import patricia.code.traverse_empty
import patricia.code.traverse_non_empty

def traverse_node (crypto: Crypto) (n_steps: ℕ) (is_new_tree: Bool) (height path node: ℕ) (res: TraverseResult) : Prop :=
---func traverse_node{
---    hash_ptr: HashBuiltin*, range_check_ptr, update_ptr: DictAccess*, siblings: Sibling*
---}(globals: ParticiaGlobals*, height: felt, path: felt, node: felt) {
---    if (node == 0) {
  if node = 0 then
---        // Empty:
---        traverse_empty(globals=globals, height=height, path=path);
    traverse_empty n_steps height path res
---        return ();
---    }
  else
---
---    return traverse_non_empty(globals=globals, height=height, path=path, node=node);
    traverse_non_empty crypto n_steps is_new_tree height path node res
---}


def traverse_prev_tree (crypto: Crypto) (n_steps height prev_root: ℕ) (res: TraverseResult) : Prop :=
---func traverse_prev_tree{hash_ptr: HashBuiltin*, range_check_ptr, siblings: Sibling*}(
---    patricia_update_constants: PatriciaUpdateConstants*,
---    update_ptr: DictAccess*,
---    n_updates: felt,
---    height: felt,
---    prev_root: felt,
---    new_root: felt,
---) {
---    %{
---        from starkware.cairo.common.patricia_utils import canonic, patricia_guess_descents
---        from starkware.python.merkle_tree import build_update_tree
---
---        # Build modifications list.
---        modifications = []
---        DictAccess_key = ids.DictAccess.key
---        DictAccess_new_value = ids.DictAccess.new_value
---        DictAccess_SIZE = ids.DictAccess.SIZE
---        for i in range(ids.n_updates):
---            curr_update_ptr = ids.update_ptr.address_ + i * DictAccess_SIZE
---            modifications.append((
---                memory[curr_update_ptr + DictAccess_key],
---                memory[curr_update_ptr + DictAccess_new_value]))
---
---        node = build_update_tree(ids.height, modifications)
---        descent_map = patricia_guess_descents(
---            ids.height, node, preimage, ids.prev_root, ids.new_root)
---        del modifications
---        __patricia_skip_validation_runner = globals().get(
---            '__patricia_skip_validation_runner')
---
---        common_args = dict(
---            preimage=preimage, descent_map=descent_map,
---            __patricia_skip_validation_runner=__patricia_skip_validation_runner)
---        common_args['common_args'] = common_args
---    %}
---
---    let update_end: DictAccess* = &update_ptr[n_updates];
---
---    // Traverse prev tree.
---    assert_le(height, MAX_LENGTH);
  height ≤ crypto.max_height ∧
---    %{ vm_enter_scope(dict(node=node, **common_args)) %}
---    with update_ptr {
---        traverse_node(
---            globals=new ParticiaGlobals(
---                pow2=patricia_update_constants.globals_pow2, access_offset=DictAccess.prev_value
---            ),
---            height=height,
---            path=0,
---            node=prev_root,
---        );
  traverse_node crypto n_steps false height (path:=0) prev_root res
---    }
---    %{ vm_exit_scope() %}
---    assert update_ptr = update_end;
---    return ();
---}

structure Update where
  (key prev new: ℕ)

def patricia_update_using_update_constants
    (crypto: Crypto) (n_steps height prev_root new_root: ℕ) (updates: List Update) : Prop :=
---func patricia_update_using_update_constants{hash_ptr: HashBuiltin*, range_check_ptr}(
---    patricia_update_constants: PatriciaUpdateConstants*,
---    update_ptr: DictAccess*,
---    n_updates: felt,
---    height: felt,
---    prev_root: felt,
---    new_root: felt,
---) {
---    if (n_updates == 0) {
  if updates.length = 0 then
---        prev_root = new_root;
    prev_root = new_root
---        return ();
---    }
  else
---
---    let update_end = &update_ptr[n_updates];
---
---    alloc_locals;
---
---    // Traverse prev tree.
---    let (local original_siblings: Sibling*) = alloc();
    ∃ (siblings: List (ℕ × ℕ)),
---    let siblings = original_siblings;
---    with siblings {
---        traverse_prev_tree(
---            patricia_update_constants=patricia_update_constants,
---            update_ptr=update_ptr,
---            n_updates=n_updates,
---            height=height,
---            prev_root=prev_root,
---            new_root=new_root,
---        );
    traverse_prev_tree crypto n_steps height prev_root
      {siblings := siblings, updates := updates.map (λ update ↦ (update.key, update.prev))} ∧
---    }
---    local siblings_end: Sibling* = siblings;
---
---    // Traverse new tree.
---    let siblings = original_siblings;
---    %{ vm_enter_scope(dict(node=node, **common_args)) %}
---    // Note: the height is enforced to be smaller or equal to MAX_LENGTH in `traverse_prev_tree`.
---    with update_ptr, siblings {
---        traverse_node(
---            globals=new ParticiaGlobals(
---                pow2=patricia_update_constants.globals_pow2, access_offset=DictAccess.new_value
---            ),
---            height=height,
---            path=0,
---            node=new_root,
---        );
       traverse_node crypto n_steps true height 0 new_root
         {siblings := siblings, updates := updates.map (λ update ↦ (update.key, update.new))}
---    }
---    %{ vm_exit_scope() %}
---    assert update_ptr = update_end;
---    assert siblings = siblings_end;
---    return ();
---}
