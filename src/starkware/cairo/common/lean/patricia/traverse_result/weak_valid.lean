import patricia.traverse_result.valid

-- A weaker version of valid that allows the siblings to be either truncated (prefix of)
-- or extended (super-list of) to become valid.
def TraverseResult.weak_valid
    (crypto: Crypto) {height: ℕ} (path: ℕ)
    (res: TraverseResult) (ref: PatriciaTree height) : Prop :=
  ∃ valid_siblings extra_siblings extra_siblings': List (ℕ × ℕ),
    TraverseResult.valid crypto path { siblings := valid_siblings, updates := res.updates } ref ∧
    valid_siblings ++ extra_siblings = res.siblings ++ extra_siblings'

theorem TraverseResult.valid.to_weak_valid
    {crypto: Crypto} {height: ℕ} {path: ℕ} {res: TraverseResult} {ref: PatriciaTree height}
    (h_valid: res.valid crypto path ref) :
    res.weak_valid crypto path ref := by
  exact ⟨res.siblings, [], [], h_valid, rfl⟩

-- If (res_left.add res_right) is weak_valid with res_left/res_right's updates in their
-- respective subtrees (both non-empty), then res_left is weak_valid for the left subtree,
-- and moreover, if res_left is strongly valid, then res_right is weak_valid for the right.
theorem TraverseResult.weak_valid.binary
    {crypto: Crypto} {height_m1 path: ℕ}
    {res_left res_right: TraverseResult}
    {ref: PatriciaTree (height_m1 + 1)}
    (h_height: height_m1 + 1 ≤ crypto.max_height)
    (h_updates_left: ∀ u ∈ res_left.updates, is_in_subtree height_m1 (path * 2) u.1)
    (h_updates_right: ∀ u ∈ res_right.updates, is_in_subtree height_m1 (path * 2 + 1) u.1)
    (h_res_left_ne: res_left.updates ≠ [])
    (h_res_right_ne: res_right.updates ≠ [])
    (h: (res_left.add res_right).weak_valid crypto path ref) :
    res_left.weak_valid crypto (path * 2) ref.left_subtree ∧
    (res_left.valid crypto (path * 2) ref.left_subtree →
      res_right.weak_valid crypto (path * 2 + 1) ref.right_subtree) := by
  have ⟨valid_siblings, extra_siblings, extra_siblings', h_valid, h_siblings_rel⟩ := h

  have ⟨res₀, res₁, h_res, h_valid₀, h_valid₁⟩ := valid.binary_elim h_valid (by
    have ⟨update, h_update⟩ := List.exists_mem_of_ne_nil _ h_res_left_ne
    exact ⟨update, by simp [h_update], h_updates_left _ h_update⟩
  ) (by
    have ⟨update, h_update⟩ := List.exists_mem_of_ne_nil _ h_res_right_ne
    exact ⟨update, by simp [h_update], h_updates_right _ h_update⟩
  )

  have h_updates_split : res₀.updates ++ res₁.updates = res_left.updates ++ res_right.updates := by
    simpa using (congrArg TraverseResult.updates h_res).symm
  have h_siblings_split : res₀.siblings ++ res₁.siblings = valid_siblings := by
    simpa using (congrArg TraverseResult.siblings h_res).symm
  have h_in_subtree₀ := (valid.implies_updates h_valid₀).2
  have h_in_subtree₁ := (valid.implies_updates h_valid₁).2

  have h_res₀_updates : res₀.updates = res_left.updates :=
    is_in_subtree.append_eq h_updates_split
      h_in_subtree₀ h_in_subtree₁ h_updates_left h_updates_right
  have h_res₁_updates : res₁.updates = res_right.updates := by
    have h_cancel := h_updates_split
    rw [h_res₀_updates] at h_cancel
    exact List.append_cancel_left h_cancel

  rw [(show res₀ = { siblings := res₀.siblings, updates := res_left.updates } from by
    ext <;> simp [h_res₀_updates]
  )] at h_valid₀
  rw [show res₁ = { siblings := res₁.siblings, updates := res_right.updates } from by
    ext <;> simp [h_res₁_updates]
  ] at h_valid₁

  rw [←h_siblings_split] at h_siblings_rel
  simp only [List.append_assoc] at h_siblings_rel

  constructor
  · -- Left weak_valid.
    exact ⟨res₀.siblings, _, _, h_valid₀, h_siblings_rel⟩
  · -- Right weak_valid, assuming res_left is (strongly) valid.
    intro h_left_valid

    have h_prefix : res₀.siblings <+: res_left.siblings ∨ res_left.siblings <+: res₀.siblings := by
      rcases List.append_eq_append_iff.1 h_siblings_rel with ⟨k, h_eq, _⟩ | ⟨k, h_eq, _⟩
      · exact Or.inl ⟨k, h_eq.symm⟩
      · exact Or.inr ⟨k, h_eq.symm⟩

    have h_res₀_eq_res_left : res₀.siblings = res_left.siblings := by
      rcases h_prefix with h_fwd | h_bwd
      · have h_eq := valid.eq_of_prefix (by omega) h_valid₀ h_left_valid (by simp) h_fwd
        simpa using congrArg (·.siblings) h_eq
      · have h_eq := valid.eq_of_prefix (by omega) h_left_valid h_valid₀ (by simp) h_bwd
        simpa using (congrArg (·.siblings) h_eq).symm
    refine ⟨res₁.siblings, extra_siblings, extra_siblings', h_valid₁, ?_⟩

    rw [h_res₀_eq_res_left] at h_siblings_rel
    exact List.append_cancel_left h_siblings_rel

-- Edge-style counterpart of `weak_valid.binary`: if `(sibling first_sibling).add res_side`
-- is weak_valid at the parent, with `res_side`'s updates confined to the `dir` subtree,
-- then `res_side` is weak_valid at that subtree, and — assuming `res_side` is strongly
-- valid — `first_sibling` is the hash of the OTHER (1 - dir) subtree.
theorem TraverseResult.weak_valid.single
    {crypto: Crypto} {height_m1 path: ℕ}
    {res_side: TraverseResult}
    {ref: PatriciaTree (height_m1 + 1)}
    (dir: Fin 2)
    (sibling: ℕ)
    (h_updates_side:
      ∀ update ∈ res_side.updates, is_in_subtree height_m1 (path * 2 + dir) update.1)
    (h: ((TraverseResult.sibling sibling).add res_side).weak_valid crypto path ref) :
    res_side.weak_valid crypto (path * 2 + dir) (ref.subtree dir) ∧
    sibling = (ref.subtree (1 - dir)).hash crypto := by
  have ⟨valid_siblings, extra_siblings, extra_siblings', h_valid, h_siblings_rel⟩ := h

  have ⟨res_inner, h_res_eq, h_valid_inner⟩ := valid.edge_elim h_valid dir (by
    simp only
    cases valid_siblings
    case nil => simp
    case cons head' rem =>
      simp only [List.cons_append, List.nil_append, List.cons.injEq] at h_siblings_rel
      simp only [List.head?_cons, Option.some.injEq, forall_eq', h_siblings_rel.1]
  ) h_updates_side

  have h_parent_updates : ((TraverseResult.sibling sibling).add res_side).updates
      = res_side.updates := by simp
  have h_parent_siblings : ((TraverseResult.sibling sibling).add res_side).siblings
      = (0, sibling) :: res_side.siblings := by simp
  rw [h_parent_updates] at h_valid
  rw [h_parent_siblings] at h_siblings_rel

  have h_valid_siblings_eq :
      valid_siblings = (0, (ref.subtree (1 - dir)).hash crypto) :: res_inner.siblings := by
    simpa using (congrArg TraverseResult.siblings h_res_eq)
  rw [h_valid_siblings_eq] at h_siblings_rel

  constructor
  · exact ⟨res_inner.siblings, extra_siblings, extra_siblings',
      (congrArg TraverseResult.updates h_res_eq) ▸ h_valid_inner,
      congrArg List.tail h_siblings_rel⟩
  · simp only [List.cons_append, List.cons.injEq, Prod.mk.injEq] at h_siblings_rel
    exact h_siblings_rel.1.2.symm

-- Descent-style counterpart of `weak_valid.binary` and `weak_valid.edge`: if
-- `(descent length).add res_side` is `weak_valid` at the parent, with
-- updates confined to the descent subtree at `(path * 2 ^ length + word)`, then `res_side`
-- is `weak_valid` at that descent subtree.
theorem TraverseResult.weak_valid.descent
    {crypto: Crypto} {height_m1 path: ℕ}
    {res_side: TraverseResult}
    {ref: PatriciaTree (height_m1 + 1)}
    (h_height: height_m1 + 1 ≤ crypto.max_height)
    (length_m2: ℕ) (word: Fin (2 ^ (length_m2 + 2)))
    (h_length: length_m2 + 2 ≤ height_m1 + 1)
    (h_updates_side:
      ∀ update ∈ res_side.updates,
        is_in_subtree (height_m1 + 1 - (length_m2 + 2))
          (path * 2 ^ (length_m2 + 2) + word) update.1)
    (h: ((TraverseResult.descent (length_m2 + 2)).add res_side).weak_valid crypto path ref) :
    res_side.weak_valid crypto (path * 2 ^ (length_m2 + 2) + word) (ref.descend word) ∧
    (∀ word' : Fin (2 ^ (length_m2 + 2)), word ≠ word' → ref.descend word' = .Empty _) := by
  have ⟨valid_siblings, extra_siblings, extra_siblings', h_valid, h_siblings_rel⟩ := h

  have ⟨res_inner, h_res_eq, h_valid_inner, h_empty⟩ :=
    valid.descent_elim' ⟨by omega, h_height⟩ h_valid length_m2 (by
      intro head h_head
      cases valid_siblings
      case nil => contradiction
      case cons head' rem =>
        simp only [List.cons_append, List.cons.injEq] at h_siblings_rel
        simp only [List.head?_cons, Option.some.injEq, h_siblings_rel.1] at h_head
        exact h_head.symm
    ) h_length word h_updates_side

  have h_eq_updates := congrArg TraverseResult.updates h_res_eq
  simp only [List.nil_append] at h_eq_updates

  have h_eq_siblings := congrArg TraverseResult.siblings h_res_eq
  simp only at h_eq_siblings

  rw [h_eq_siblings] at h_siblings_rel
  simp only [List.cons_append, List.cons.injEq, true_and, List.nil_append] at h_siblings_rel

  exact ⟨⟨res_inner.siblings, extra_siblings, extra_siblings',
    h_eq_updates ▸ h_valid_inner, h_siblings_rel⟩, h_empty⟩
