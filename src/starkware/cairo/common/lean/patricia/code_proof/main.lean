import patricia.code_proof.root_eq
import patricia.code_proof.sorted
import patricia.code_proof.strong_valid
import patricia.code.main

-- Top-level correctness: given an `old_tree` whose hash is `prev_root` and a successful run of
-- `patricia_update_using_update_constants`,
-- there exists a `new_tree` hashing to `new_root` such that:
-- (1) non-update leaves are unchanged and
-- (2) each update's prev/new values match the trees.
theorem patricia_update_using_update_constants.correctness {crypto: Crypto}
    {n_steps height prev_root new_root: ℕ} {updates: List Update}
    (h: patricia_update_using_update_constants crypto n_steps height prev_root new_root updates)
    {old_tree: PatriciaTree height}
    (h_ref: old_tree.hash crypto = prev_root) :
    ∃ new_tree: PatriciaTree height,
      new_tree.hash crypto = new_root ∧
      (∀ leaf: Fin (2 ^ height), (leaf.1 ∉ updates.map Update.key) →
        new_tree.at leaf = old_tree.at leaf) ∧
      (∀ update ∈ updates,
        (old_tree.at update.key = update.prev) ∧
        (new_tree.at update.key = update.new)) := by
  by_cases h_n_updates: updates.length = 0
  case pos =>
    simp only [patricia_update_using_update_constants, h_n_updates, reduceIte] at h
    use old_tree
    simp [h, h_ref, List.length_eq_zero_iff.1 h_n_updates]
  case neg =>
    simp [patricia_update_using_update_constants, h_n_updates, reduceIte] at h
    have ⟨siblings, h_traverse₀, h_traverse₁⟩ := h

    -- Previous tree is valid with respect to the reference tree.
    have h_strong_valid₀ := traverse_prev_tree.strong_valid (h_ref:=h_ref) (h:=h_traverse₀)
    have h_valid₀ := h_strong_valid₀.1

    -- New TraverseResult is also valid with respect to the reference tree.
    let res₁: TraverseResult := {siblings := siblings, updates := updates.map (λ update ↦ (update.key, update.new))}
    have h_height : height ≤ crypto.max_height := h_traverse₀.1
    have h_valid₁ := TraverseResult.valid.change_update_values
      (h_valid:=h_valid₀) (res₁:=res₁) (h_same_siblings:=rfl) (h_same_update_keys:=by
        simp only [List.map_map, res₁]
        apply List.map_congr_left (by intro update h_update; show _ = update.key; rfl)
      )

    have h_new_root := traverse_node.root_eq (h_valid:=h_valid₁) (h:=h_traverse₁) (h_height:=h_height)
    let values := λ x ↦ TraverseResult.values 0 res₁ old_tree (x + 0 * 2 ^ height)

    use PatriciaTree.build height values
    refine ⟨?_, ?_, ?_⟩
    · simp [h_new_root, values]
    · intro leaf h_no_update
      simp only [PatriciaTree.build_at, values]
      rw [TraverseResult.values.no_update (h_no_update:=by
        simp only [zero_mul, add_zero, res₁, List.map_map, List.mem_map]
        by_contra ⟨update, h_update, h⟩
        simp at h
        simp only [List.mem_map, not_exists, not_and] at h_no_update
        have := h_no_update _ h_update
        contradiction
      )]
      simp
    · intro update h_update
      have h_update_key : update.key < 1 * 2 ^ height :=
        ((h_valid₀.implies_updates).2 ⟨update.key, update.prev⟩ (by
          rw [List.mem_map]; use update
        )).2
      rw [one_mul] at h_update_key

      constructor
      · have h_update' : (update.key, update.prev) ∈ updates.map (λ u ↦ (u.key, u.prev)) := by
          rw [List.mem_map]; exact ⟨update, h_update, rfl⟩
        simpa using h_strong_valid₀.2 (update.key, update.prev) h_update'
      · rw [PatriciaTree.build_at _ ⟨update.key, h_update_key⟩]
        apply TraverseResult.values.of_mem_updates h_valid₁
        simp only [res₁, List.mem_map, zero_mul, add_zero]
        exact ⟨update, h_update, rfl⟩

-- A hash is valid for a given height if there exists a Patricia tree with that hash.
def valid_hash (crypto: Crypto) (height: ℕ) (hash: ℕ) :=
  height ≤ crypto.max_height ∧ ∃ tree: PatriciaTree height, tree.hash crypto = hash

theorem valid_hash.empty (crypto: Crypto) {height: ℕ} (h_height: height ≤ crypto.max_height) :
    valid_hash crypto height 0 := by
  refine ⟨h_height, .Empty _, rfl⟩

-- The value of a leaf that corresponds to a given hash.
def valid_hash.at_rel {crypto: Crypto} {height: ℕ} {hash: ℕ}
    (_h_valid: valid_hash crypto height hash)
    (leaf: ℕ) (value: ℕ) :=
  ∃ tree: PatriciaTree height, tree.hash crypto = hash ∧ tree.at leaf = value

-- The value defined by `valid_hash.at_rel` exists and is unique.
theorem valid_hash.at_rel_prop {crypto: Crypto} {height: ℕ} {hash: ℕ}
    (h_valid: valid_hash crypto height hash)
    (leaf: ℕ) :
    ∃! value, h_valid.at_rel leaf value := by
  have ⟨_, tree₀, h_hash₀⟩ := h_valid
  exact ⟨tree₀.at leaf, ⟨tree₀, h_hash₀, rfl⟩, λ value₁ h_value₁ ↦ by
    have ⟨tree₁, h_hash₁, h_tree₁_at⟩ := h_value₁
    have h_tree_eq := PatriciaTree.hash_inj (by assumption) (h_hash₀ ▸ h_hash₁)
    subst tree₀
    exact h_tree₁_at.symm
  ⟩

noncomputable def valid_hash.at {crypto: Crypto} {height: ℕ} {hash: ℕ}
    (h_valid: valid_hash crypto height hash) (leaf: ℕ) :=
  Classical.choose (h_valid.at_rel_prop leaf).exists

theorem valid_hash.at_of_at_rel {crypto: Crypto} {height: ℕ} {hash: ℕ}
    (h_valid: valid_hash crypto height hash)
    {leaf value: ℕ}
    (tree_at: h_valid.at_rel leaf value) :
    h_valid.at leaf = value := by
  apply (h_valid.at_rel_prop leaf).unique _ tree_at
  exact Classical.choose_spec (h_valid.at_rel_prop leaf).exists

theorem valid_hash.at_of_tree_at {crypto: Crypto} {height: ℕ} {hash: ℕ}
    (h_valid: valid_hash crypto height hash)
    (tree: PatriciaTree height) (h_hash: tree.hash crypto = hash)
    {leaf: ℕ} :
    h_valid.at leaf = tree.at leaf := by
  apply at_of_at_rel
  exact ⟨tree, h_hash, rfl⟩

theorem valid_hash.at_empty (crypto: Crypto) {height: ℕ} (h_height: height ≤ crypto.max_height) :
    (empty crypto h_height).at leaf = 0 := by
  rw [at_of_tree_at (empty crypto h_height) (.Empty _) rfl]
  rw [PatriciaTree.at_empty]

-- Variant of `correctness` phrased in terms of `valid_hash`:
-- From a valid `prev_root` derive a valid `new_root` plus the same leaf-level guarantees,
-- represented by `valid_hash.at`.
theorem patricia_update_using_update_constants.correctness_valid_hash {crypto: Crypto}
    {n_steps height prev_root new_root: ℕ} {updates: List Update}
    (h: patricia_update_using_update_constants crypto n_steps height prev_root new_root updates)
    (h_prev_valid: valid_hash crypto height prev_root) :
    ∃ h_new_valid: valid_hash crypto height new_root,
      (∀ leaf: Fin (2 ^ height), (leaf.1 ∉ updates.map Update.key) →
        h_prev_valid.at leaf = h_new_valid.at leaf) ∧
      (∀ update ∈ updates,
        (h_prev_valid.at update.key = update.prev) ∧
        (h_new_valid.at update.key = update.new)) := by
  have ⟨h_height, old_tree, h_old_tree_hash⟩ := h_prev_valid
  have ⟨new_tree, h_new_tree_hash, h_no_updates, h_updates⟩ := correctness h h_old_tree_hash
  have h_new_valid: valid_hash crypto height new_root := ⟨h_height, new_tree, h_new_tree_hash⟩
  refine ⟨h_new_valid, ?_, ?_⟩
  · intro leaf h_no_update
    rw [valid_hash.at_of_tree_at h_prev_valid old_tree h_old_tree_hash,
      valid_hash.at_of_tree_at h_new_valid new_tree h_new_tree_hash,
      h_no_updates leaf h_no_update]
  · intro update h_update
    rw [valid_hash.at_of_tree_at h_prev_valid old_tree h_old_tree_hash,
      valid_hash.at_of_tree_at h_new_valid new_tree h_new_tree_hash]
    simp [h_updates update h_update]

-- Sample usage of `correctness_valid_hash`:
-- three sequential updates starting from the empty tree (root = 0).
-- For a `key` that is updated in runs 0 and 2 and untouched in run 1, the initial
-- prev-value must be 0 (empty tree) and the new-value written in run 0 must match the value read
-- in run 2.
example {crypto: Crypto} {height: ℕ}
    -- The height fits within the crypto's max height.
    (h_height: height ≤ crypto.max_height)
    -- The function arguments.
    {root₁ root₂ root₃: ℕ} {updates₀ updates₁ updates₂ : List Update}
    -- Run 0: from the empty tree (root 0) to `root₁` with `updates₀`.
    (h₀: patricia_update_using_update_constants crypto n_steps height 0 root₁ updates₀)
    -- Run 1: from `root₁` to `root₂` with `updates₁`.
    (h₁: patricia_update_using_update_constants crypto n_steps height root₁ root₂ updates₁)
    -- Run 2: from `root₂` to `root₃` with `updates₂`.
    (h₂: patricia_update_using_update_constants crypto n_steps height root₂ root₃ updates₂)
    -- A leaf index inside the tree.
    (key: Fin (2 ^ height))
    (value₀ value₁ value₂ value₃: ℕ)
    -- Run 0 updates `key` from `value₀` to `value₁`.
    (h_update₀: ⟨key, value₀, value₁⟩ ∈ updates₀)
    -- Run 1 does not touch `key`.
    (h_no_update: (key: ℕ) ∉ updates₁.map Update.key)
    -- Run 2 updates `key` from `value₂` to `value₃`.
    (h_update₂: ⟨key, value₂, value₃⟩ ∈ updates₂):
    value₀ = 0 ∧ value₁ = value₂ := by
  have ⟨valid₁, h_no_updates₀, h_updates₀⟩ :=
    patricia_update_using_update_constants.correctness_valid_hash h₀ (.empty _ h_height)
  have ⟨valid₂, h_no_updates₁, h_updates₁⟩ :=
    patricia_update_using_update_constants.correctness_valid_hash h₁ valid₁
  have ⟨valid₃, h_no_updates₂, h_updates₂⟩ :=
    patricia_update_using_update_constants.correctness_valid_hash h₂ valid₂

  have ⟨w₀, w₁⟩ := h_updates₀ _ h_update₀
  have w₂ := h_no_updates₁ _ h_no_update
  have ⟨w₃, w₄⟩ := h_updates₂ _ h_update₂
  simp only [valid_hash.at_empty crypto h_height] at w₀ w₁ w₂ w₃ w₄
  exact ⟨w₀.symm, w₁ ▸ w₂ ▸ w₃⟩

-- If two runs of `patricia_update_using_update_constants` share the same `height`, `prev_root`,
-- and `updates`, then they produce the same `new_root`.
theorem patricia_update_using_update_constants.deterministic {crypto: Crypto}
    {n_steps n_steps' height prev_root new_root new_root': ℕ} {updates: List Update}
    (h₀: patricia_update_using_update_constants crypto n_steps height prev_root new_root updates)
    (h₁: patricia_update_using_update_constants crypto n_steps' height prev_root new_root' updates)
    (h_prev_valid: valid_hash crypto height prev_root) :
    new_root' = new_root := by
  have ⟨valid₀, h_no_updates₀, h_updates₀⟩ := correctness_valid_hash h₀ h_prev_valid
  have ⟨valid₁, h_no_updates₁, h_updates₁⟩ := correctness_valid_hash h₁ h_prev_valid

  have ⟨_, tree₀, h_hash₀⟩ := valid₀
  have ⟨_, tree₁, h_hash₁⟩ := valid₁

  rw [←h_hash₀, ←h_hash₁]
  apply congrArg
  apply PatriciaTree.at.inj
  intro leaf
  by_cases h_leaf : leaf.1 ∈ updates.map Update.key
  case pos =>
    have ⟨u, h_u, h_key⟩ := List.mem_map.1 h_leaf
    have h_update₀ := h_updates₀ u h_u
    rw [valid₀.at_of_tree_at _ h_hash₀, h_key] at h_update₀
    have h_update₁ := h_updates₁ u h_u
    rw [valid₁.at_of_tree_at _ h_hash₁, h_key] at h_update₁
    exact h_update₀.2 ▸ h_update₁.2
  case neg =>
    have h_no_update₀ := h_no_updates₀ leaf h_leaf
    rw [valid₀.at_of_tree_at _ h_hash₀] at h_no_update₀
    have h_no_update₁ := h_no_updates₁ leaf h_leaf
    rw [valid₁.at_of_tree_at _ h_hash₁] at h_no_update₁
    exact h_no_update₁ ▸ h_no_update₀

-- A successful run of `patricia_update_using_update_constants` implies that the keys of the updates
-- are sorted in strictly increasing order.
theorem patricia_update_using_update_constants.sorted {crypto: Crypto}
    {n_steps height prev_root new_root: ℕ} {updates: List Update}
    (h: patricia_update_using_update_constants crypto n_steps height prev_root new_root updates) :
    List.SortedLT (updates.map Update.key) := by
  unfold patricia_update_using_update_constants at h
  split at h
  case isTrue =>
    rw [(List.length_eq_zero_iff.1 (by assumption) : updates = [])]
    simp [List.SortedLT, StrictMono]
  case isFalse h_n_updates =>
    have ⟨_, _, h⟩ := h
    unfold traverse_node at h
    split at h
    case isTrue h_traverse =>
      have := h.sorted
      simp only [List.map_map] at this
      exact this
    case isFalse h_traverse =>
      have := h.sorted
      simp only [List.map_map] at this
      exact this
