import patricia.traverse_result.valid

-- A strengthened form of `valid`: in addition to the structural validity, every update's
-- value matches the actual leaf value of `ref` at the corresponding index.
def TraverseResult.strong_valid
    (crypto: Crypto) {height: ℕ} (path: ℕ)
    (res: TraverseResult) (ref: PatriciaTree height) : Prop :=
  res.valid crypto path ref ∧
  ∀ u ∈ res.updates, ref.at (u.1 - path * 2 ^ height) = u.2

theorem TraverseResult.strong_valid.to_valid {crypto: Crypto} {height: ℕ} {path: ℕ}
    {res: TraverseResult} {ref: PatriciaTree height}
    (h: res.strong_valid crypto path ref) :
    res.valid crypto path ref :=
  h.1

theorem TraverseResult.strong_valid.mk_binary
    {crypto: Crypto} {height_m1: ℕ} {path: ℕ} {res res₀ res₁: TraverseResult} {ref: PatriciaTree (height_m1 + 1)}
    (h_res: res = res₀.add res₁)
    (h_valid₀: res₀.strong_valid crypto (path * 2) ref.left_subtree)
    (h_valid₁: res₁.strong_valid crypto (path * 2 + 1) ref.right_subtree) :
    res.strong_valid crypto path ref := by
  constructor
  · exact valid.mk_both h_res h_valid₀.1 h_valid₁.1
  · intro u h_u
    simp only [h_res, List.mem_append] at h_u
    cases h_u
    case inl h_u =>
      have h_lt := is_in_subtree.sub_offset_lt ((h_valid₀.1.implies_updates).2 u h_u)

      have := h_valid₀.2 u h_u
      rw [PatriciaTree.left_subtree_at _ h_lt, mul_assoc, ←Nat.pow_succ'] at this
      exact this
    case inr h_u =>
      have h_lt := is_in_subtree.sub_offset_lt ((h_valid₁.1.implies_updates).2 u h_u)
      have h_ge := ((h_valid₁.1.implies_updates).2 u h_u).1
      rw [add_mul, one_mul, mul_assoc, ←Nat.pow_succ'] at h_ge

      have := h_valid₁.2 u h_u
      rw [PatriciaTree.right_subtree_at _ h_lt, add_mul, mul_assoc, ←Nat.pow_succ',
        one_mul, ←Nat.sub_sub, Nat.sub_add_cancel (by omega)] at this
      exact this

theorem TraverseResult.strong_valid.mk_edge
    {crypto: Crypto} {height_m1: ℕ} {path: ℕ} {res res₀: TraverseResult} {ref: PatriciaTree (height_m1 + 1)}
    (dir: Fin 2)
    (h_res: res = (TraverseResult.sibling ((ref.subtree (1 - dir)).hash crypto)).add res₀)
    (h_valid: res₀.strong_valid crypto (path * 2 + dir) (ref.subtree dir)) :
    res.strong_valid crypto path ref := by
  constructor
  · exact valid.mk_edge dir h_res h_valid.1
  · intro u h_u
    simp only [h_res, List.nil_append] at h_u
    have h_lt := is_in_subtree.sub_offset_lt ((h_valid.1.implies_updates).2 u h_u)
    have h_ge := ((h_valid.1.implies_updates).2 u h_u).1
    rw [add_mul, mul_assoc, ←Nat.pow_succ'] at h_ge

    have := h_valid.2 u h_u
    rw [PatriciaTree.subtree_at _ _ h_lt, add_mul, mul_assoc, ←Nat.pow_succ',
      ←Nat.sub_sub, Nat.sub_add_cancel (by omega)] at this
    exact this

theorem TraverseResult.strong_valid.mk_descent
    {crypto: Crypto} {height_m1: ℕ} {path: ℕ} {res₀: TraverseResult} {ref: PatriciaTree (height_m1 + 1)}
    (length_m2: ℕ) (word: Fin (2 ^ (length_m2 + 2)))
    (h_length: length_m2 < height_m1)
    (h_res: res = ((TraverseResult.descent (length_m2 + 2)).add res₀))
    (h_valid: res₀.strong_valid crypto (path * 2 ^ (length_m2 + 2) + word) (ref.descend word))
    (h_empty: ∀ word' : Fin (2 ^ (length_m2 + 2)), word ≠ word' → ref.descend word' = .Empty _) :
    res.strong_valid crypto path ref := by
  constructor
  · exact valid.mk_descent length_m2 word h_length h_res h_valid.1 h_empty
  · intro u h_u
    simp only [h_res, List.nil_append] at h_u
    have h_lt := is_in_subtree.sub_offset_lt ((h_valid.1.implies_updates).2 u h_u)
    have h_ge := ((h_valid.1.implies_updates).2 u h_u).1
    rw [add_mul, mul_assoc, ←Nat.pow_add] at h_ge

    have := h_valid.2 u h_u
    rw [PatriciaTree.descend_at _ h_lt, add_mul, mul_assoc, ←Nat.pow_add,
      ←Nat.sub_sub, Nat.sub_add_cancel (by omega)] at this
    rw [show length_m2 + 2 + (height_m1 + 1 - (length_m2 + 2)) = (height_m1 + 1) by omega] at this
    exact this
