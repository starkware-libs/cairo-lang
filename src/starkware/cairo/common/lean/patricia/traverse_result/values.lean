import patricia.traverse_result.valid

def TraverseResult.filtered_updates (res: TraverseResult) (index: ℕ) : List (ℕ × ℕ) :=
  res.updates
  |>.filter (λ update ↦ update.1 = index)

theorem TraverseResult.filtered_updates.add {res₀ res₁: TraverseResult} (index: ℕ) :
    (res₀.add res₁).filtered_updates index =
      res₀.filtered_updates index ++ res₁.filtered_updates index := by
  simp [filtered_updates]

theorem TraverseResult.filtered_updates.empty {res: TraverseResult} (index: ℕ)
    (h_no_update: ∀ update ∈ res.updates, update.1 ≠ index) :
    res.filtered_updates index = [] := by
  simp only [filtered_updates, List.filter_eq_nil_iff, decide_eq_true_eq]
  intro update h_update
  exact h_no_update update h_update

theorem TraverseResult.filtered_updates.congr {res₀ res₁: TraverseResult}
    (h_updates: res₀.updates = res₁.updates) :
    res₀.filtered_updates = res₁.filtered_updates := by
  unfold filtered_updates
  rw [h_updates]

-- If `index` appears as the key of some update, then `filtered_updates index` is non-empty.
theorem TraverseResult.filtered_updates.update (res: TraverseResult) (index: ℕ)
    (h_update: index ∈ res.updates.map Prod.fst) :
    res.filtered_updates index ≠ [] := by
  simp only [List.mem_map] at h_update
  have ⟨pair, _, _⟩ := h_update
  subst index
  simp [filtered_updates]
  use pair.2

def TraverseResult.values {height: ℕ} (path: ℕ) (res: TraverseResult) (ref: PatriciaTree height)
    (index: ℕ) : ℕ :=
  res.filtered_updates index
  |>.headD (index, ref.at (index - path * 2 ^ height))
  |>.snd

theorem TraverseResult.values.no_update {height: ℕ} (path: ℕ) (res: TraverseResult) (ref: PatriciaTree height)
    (index: ℕ)
    (h_no_update: index ∉ res.updates.map Prod.fst) :
    res.values path ref index = ref.at (index - path * 2 ^ height) := by
  unfold values filtered_updates
  rw [List.filter_eq_nil_iff.2 (by
    intro update h_update
    simp only [List.mem_map, not_exists, not_and] at h_no_update
    simp [h_no_update _ h_update]
  )]
  simp

theorem TraverseResult.values.update {height: ℕ} (path: ℕ) (res: TraverseResult) (ref: PatriciaTree height)
    (index: ℕ)
    (h_update: index ∈ res.updates.map Prod.fst) :
    res.values path ref index = (
      res.filtered_updates index
      |>.head (filtered_updates.update res index h_update)
      |>.snd
    ) := by
  unfold values
  simp [List.head?_eq_some_head (filtered_updates.update res index h_update)]

theorem TraverseResult.values.of_mem_updates
    {crypto: Crypto} {height: ℕ} {path: ℕ}
    {res: TraverseResult} {ref: PatriciaTree height}
    {key val: ℕ}
    (h_valid: res.valid crypto path ref)
    (h_mem: (key, val) ∈ res.updates) :
    res.values path ref key = val := by
  have h_key_mem : key ∈ res.updates.map Prod.fst := List.mem_map.mpr ⟨(key, val), h_mem, rfl⟩
  rw [TraverseResult.values.update path res ref key h_key_mem]
  apply h_valid.unique_value _ h_mem

  set p := (res.filtered_updates key).head
    (TraverseResult.filtered_updates.update res key h_key_mem)
  have h_p_mem : p ∈ res.filtered_updates key := List.head_mem _

  simp only [TraverseResult.filtered_updates, List.mem_filter, decide_eq_true_eq] at h_p_mem
  exact h_p_mem.2 ▸ h_p_mem.1

theorem TraverseResult.values.congr_res
    {res₀ res₁: TraverseResult}
    (h_updates: res₀.updates = res₁.updates)
    {height: ℕ} (path: ℕ) (ref: PatriciaTree height) (index: ℕ) :
    res₀.values path ref index = res₁.values path ref index := by
  unfold values
  rw [filtered_updates.congr h_updates]

-- For an `index` lying inside the descent subtree, `res.values` at the parent agrees with
-- `res.values` at the descended subtree (both indexed by the same absolute `index`).
theorem TraverseResult.values.descent
    {height length: ℕ} (path: ℕ) (res: TraverseResult) (ref: PatriciaTree height)
    (index: ℕ)
    (word: Fin (2 ^ length))
    (h_in_subtree: is_in_subtree (height - length) (path * 2 ^ length + word) index)
    (h_length: length ≤ height):
    res.values path ref index =
      res.values (path * 2 ^ length + word) (ref.descend word) index := by
  let offset : ℕ := path * 2 ^ height + word * 2 ^ (height - length)
  have i_ge : index ≥ offset := by
    have := h_in_subtree.1
    conv at this => rhs; rw [add_mul, mul_assoc, ←Nat.pow_add, Nat.add_sub_cancel' (by omega), add_comm]
    omega
  have i_lt: index - offset < 2 ^ (height - length) := by
    have := h_in_subtree.2
    conv at this => rhs; rw [add_mul, add_mul, mul_assoc, ←Nat.pow_add, Nat.add_sub_cancel' (by omega), one_mul]
    omega

  have : index - (path * 2 ^ length + ↑word) * 2 ^ (height - length) =
      index - path * 2 ^ height - word * 2 ^ (height - length) := by
    rw [add_mul, mul_assoc, ←Nat.pow_add, Nat.add_sub_cancel' (by omega)]
    omega
  unfold values
  rw [PatriciaTree.descend_at word (by omega)]
  rw [this, Nat.sub_add_cancel (by omega)]

theorem TraverseResult.values.change_update_values₀ {height: ℕ} (path: ℕ) (res₀ res₁: TraverseResult) (ref: PatriciaTree height)
    (h_same_update_keys: res₀.updates.map Prod.fst = res₁.updates.map Prod.fst)
    (index: ℕ)
    (h_no_update: index ∉ res₀.updates.map Prod.fst) :
    res₀.values path ref index = res₁.values path ref index := by
  rw [values.no_update (h_no_update:=h_no_update)]
  rw [values.no_update (h_no_update:=h_same_update_keys ▸ h_no_update)]

-- Value-alignment lemmas for half-indices (used in `root_eq`-style proofs).

-- The index `i + dir · 2^height_m1 + path · 2^(height_m1+1)` can equivalently be addressed
-- relative to the parent (`path`, `ref`) or relative to the child subtree
-- (`path * 2 + dir`, `ref.subtree dir`).
theorem TraverseResult.values.subtree
    {height_m1 path: ℕ}
    {res: TraverseResult} {ref: PatriciaTree (height_m1 + 1)}
    (dir: Fin 2) (i: Fin (2 ^ height_m1)) :
    res.values path ref (i + dir * 2 ^ height_m1 + path * 2 ^ (height_m1 + 1)) =
    res.values (path * 2 + dir) (ref.subtree dir) (i + (path * 2 + dir) * 2 ^ height_m1) := by
  simp only [TraverseResult.values, add_tsub_cancel_right]
  rw [
    show (i + (path * 2 + dir) * 2 ^ height_m1 : ℕ) = i + dir * 2 ^ height_m1 + path * 2 ^ (height_m1 + 1) by ring,
    PatriciaTree.subtree_at _ _ i.isLt]

-- If `res.filtered_updates` at a left-half index matches `res_side.filtered_updates` at the
-- same index, then `res.values` at the root agrees with `res_side.values` at the left
-- child's coordinate.
theorem TraverseResult.values_eq_of_filtered_left
    {height_m1 path: ℕ}
    {res res': TraverseResult} {ref: PatriciaTree (height_m1 + 1)}
    (i: Fin (2 ^ height_m1))
    (h_filtered_eq:
      res.filtered_updates (i + path * 2 ^ (height_m1 + 1)) =
      res'.filtered_updates (i + path * 2 ^ (height_m1 + 1))) :
    res.values path ref (i + path * 2 ^ (height_m1 + 1)) =
    res'.values (path * 2) ref.left_subtree (i + path * 2 * 2 ^ height_m1) := by
  simp only [TraverseResult.values, add_tsub_cancel_right]
  rw [show (i + path * 2 * 2 ^ height_m1 : ℕ) = i + path * 2 ^ (height_m1 + 1) from by ring,
    h_filtered_eq, PatriciaTree.left_subtree_at _ i.isLt]

-- Symmetric: right-half index ⇒ `res.values` agrees with `res'.values` at right child's coord.
theorem TraverseResult.values_eq_of_filtered_right
    {height_m1 path: ℕ}
    {res res': TraverseResult} {ref: PatriciaTree (height_m1 + 1)}
    (i: Fin (2 ^ height_m1))
    (h_filtered_eq:
      res.filtered_updates (i + 2 ^ height_m1 + path * 2 ^ (height_m1 + 1)) =
      res'.filtered_updates (i + 2 ^ height_m1 + path * 2 ^ (height_m1 + 1))) :
    res.values path ref (i + 2 ^ height_m1 + path * 2 ^ (height_m1 + 1)) =
    res'.values (path * 2 + 1) ref.right_subtree (i + (path * 2 + 1) * 2 ^ height_m1) := by
  simp only [TraverseResult.values, add_tsub_cancel_right]
  have : i + (path * 2 + 1) * 2 ^ height_m1 =
    i + 2 ^ height_m1 + path * 2 ^ (height_m1 + 1) := by ring
  rw [this, h_filtered_eq, PatriciaTree.right_subtree_at _ i.isLt]

-- If every update of `res` is confined to `path`'s subtree, and `i` lies in a
-- DIFFERENT subtree `path'` (at the same level), then `res.filtered_updates i` is empty.
theorem TraverseResult.filtered_updates.empty_of_disjoint_subtree
    {height path': ℕ} {res: TraverseResult}
    (h_updates_right: ∀ u ∈ res.updates, is_in_subtree height path u.1)
    (i: ℕ)
    (h_i: is_in_subtree height path' i)
    (h_path: path ≠ path') :
    res.filtered_updates i = [] := by
  apply TraverseResult.filtered_updates.empty
  intro update h_update h_eq
  have h₁ := h_updates_right update h_update
  exact absurd (is_in_subtree.inj_path h₁ (h_eq ▸ h_i)) h_path

-- When `res`'s updates all fall in `path₀`'s subtree at level `height'` and `i` lies in a
-- disjoint subtree `path₁` (at the same level), no update covers `i`,
-- so `res.values path ref i` falls back to the original reference tree's value `ref.at (i - path * 2^height)`.
theorem TraverseResult.values.eq_ref_at
    {height height' path path₀ path₁ i: ℕ}
    {res: TraverseResult} {ref: PatriciaTree height}
    (h_updates_right: ∀ u ∈ res.updates, is_in_subtree height' path₀ u.1)
    (h_i: is_in_subtree height' path₁ i)
    (h_path: path₀ ≠ path₁) :
    res.values path ref i = ref.at (i - path * 2^height) := by
  simp only [TraverseResult.values]
  rw [filtered_updates.empty_of_disjoint_subtree h_updates_right _ h_i h_path]
  rw [List.headD_nil]
