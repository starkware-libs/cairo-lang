import patricia.code.traverse_empty
import patricia.code.traverse_non_empty
import patricia.code_proof.helpers
import patricia.is_in_subtree
import patricia.letify

-- Given a `traverse_*` trace, every update in `res.updates` lies in the `(height, path)` subtree,
-- and `res.updates` is non-empty.

-- In addition: each update writes the value `0`.
theorem traverse_empty.updates {n_steps height path: ℕ} {res: TraverseResult}
    (h_main: traverse_empty n_steps height path res) :
    (∀ update ∈ res.updates,
      is_in_subtree height path update.1 ∧
      update.2 = 0
    ) ∧
    res.updates ≠ [] := by
  induction n_steps generalizing height path res
  case zero => contradiction
  case succ n_steps_m1 ih =>

  cases height
  case zero =>
    simp only [traverse_empty, CharP.cast_eq_zero, ↓reduceIte] at h_main
    simp [is_in_subtree.height0, h_main]
  case succ height_m1 =>
    simp only [traverse_empty, if_neg (show ↑(height_m1 + 1) ≠ (0: ℤ) by omega)] at h_main
    rcases h_main with
      ⟨res₀, res₁, h_traverse₀, h_traverse₁, h_res⟩ |
      ⟨res₀, child_bit, h_traverse, h_res⟩ |
      ⟨res₀, word, length_m2, h_length, h_word, h_traverse, h_res⟩

    · -- Both children.
      simp only [Nat.cast_add, Nat.cast_one, add_sub_cancel_right] at h_traverse₀ h_traverse₁
      replace ⟨h_traverse_updates₀, h_exists_update₀⟩ := ih h_traverse₀
      replace ⟨h_traverse_updates₁, _⟩ := ih h_traverse₁
      subst res
      simp only [List.mem_append]
      refine ⟨?_, ?_⟩
      · intro update h_update
        cases h_update
        case inl h_update =>
          have ⟨h₀, h₁⟩ := h_traverse_updates₀ _ h_update
          exact ⟨is_in_subtree.height_add1 (dir:=0) h₀, h₁⟩
        case inr h_update =>
          have ⟨h₀, h₁⟩ := h_traverse_updates₁ _ h_update
          exact ⟨is_in_subtree.height_add1 (dir:=1) h₀, h₁⟩
      · apply List.append_ne_nil_of_left_ne_nil h_exists_update₀

    · -- One child.
      simp only [Nat.cast_add, Nat.cast_one, add_sub_cancel_right] at h_traverse
      replace ⟨h_traverse_updates, h_exists_update⟩ := ih h_traverse
      subst res
      refine ⟨?_, h_exists_update⟩
      intro update h_update
      have ⟨h₀, h₁⟩ := h_traverse_updates _ h_update
      exact ⟨is_in_subtree.height_add1 (dir:=child_bit) h₀, h₁⟩

    · -- Descend.
      norm_cast at h_length
      have h_eq_nat : ((height_m1 + 1 : ℕ) - (length_m2 + 2 : ℕ) : ℤ) =
        (height_m1 + 1 - (length_m2 + 2) : ℕ) := by omega
      rw [h_eq_nat] at h_traverse

      replace ⟨h_traverse_updates, h_exists_update⟩ := ih h_traverse
      subst res
      refine ⟨?_, h_exists_update⟩
      intro update h_update
      have ⟨h₀, h₁⟩ := h_traverse_updates _ h_update
      refine ⟨?_, by omega⟩
      exact is_in_subtree.height_add (word:=⟨word, h_word⟩) h_length h₀

mutual
theorem traverse_non_empty.updates {crypto: Crypto} {n_steps: ℕ} {is_new_tree: Bool}
    {height path node: ℕ} {res: TraverseResult}
    (h: traverse_non_empty crypto n_steps is_new_tree height path node res) :
    (∀ update ∈ res.updates, is_in_subtree height path update.1) ∧ res.updates ≠ [] := by
  cases n_steps
  case zero => simp [traverse_non_empty] at h

  unfold traverse_non_empty at h
  rcases h with
    ⟨edge, h_open_edge, h_traverse_edge⟩ | h
  · exact traverse_edge.updates (h:=h_traverse_edge)
  · exact traverse_binary_or_leaf.updates (h:=h)

theorem traverse_binary_or_leaf.updates {crypto: Crypto} {n_steps: ℕ} {is_new_tree: Bool}
    {height path node: ℕ} {res: TraverseResult}
    (h: traverse_binary_or_leaf crypto n_steps is_new_tree height path node res) :
    (∀ update ∈ res.updates, is_in_subtree height path update.1) ∧ res.updates ≠ [] := by
  cases n_steps
  case zero => simp [traverse_binary_or_leaf] at h

  unfold traverse_binary_or_leaf at h
  cases height
  case zero =>
    simp only [CharP.cast_eq_zero, ↓reduceIte, ne_eq] at h
    simp [h, is_in_subtree.height0]
  case succ height_m1 =>
    replace ⟨x, y, h_node, h⟩ := h
    rcases h with
      ⟨res₀, res₁, h_traverse₀, h_traverse₁, h_res⟩ |
      ⟨res₁, h_ne_zero, h_traverse, h_res⟩ |
      ⟨res₁, h_ne_zero, h_traverse, h_res⟩
    · simp only [Nat.cast_add, Nat.cast_one, add_sub_cancel_right] at h_traverse₀ h_traverse₁
      simp only [h_res, List.mem_append]
      constructor
      · intro update h_update
        cases h_update
        case inl h_update =>
          apply is_in_subtree.height_add1 (dir:=0)
          exact (traverse_non_empty.updates h_traverse₀).1 update h_update
        case inr h_update =>
          apply is_in_subtree.height_add1 (dir:=1)
          exact (traverse_non_empty.updates h_traverse₁).1 update h_update
      · intro h_eq
        exact (traverse_non_empty.updates h_traverse₀).2 (List.append_eq_nil_iff.mp h_eq).1
    · simp only [Nat.cast_add, Nat.cast_one, add_sub_cancel_right] at h_traverse
      simp only [h_res, List.nil_append]
      constructor
      · intro update h_update
        apply is_in_subtree.height_add1 (dir:=0)
        exact (traverse_non_empty.updates h_traverse).1 update h_update
      · intro h_eq
        exact (traverse_non_empty.updates h_traverse).2 h_eq
    · simp only [Nat.cast_add, Nat.cast_one, add_sub_cancel_right] at h_traverse
      simp only [h_res, List.nil_append]
      constructor
      · intro update h_update
        apply is_in_subtree.height_add1 (dir:=1)
        exact (traverse_non_empty.updates h_traverse).1 update h_update
      · intro h_eq
        exact (traverse_non_empty.updates h_traverse).2 h_eq

theorem traverse_edge.updates {crypto: Crypto} {n_steps height path: ℕ} {edge: NodeEdge} {res: TraverseResult}
    (h: traverse_edge crypto n_steps is_new_tree height path edge res) :
    (∀ update ∈ res.updates, is_in_subtree height path update.1) ∧ res.updates ≠ [] := by
  cases h.view
  case BinaryOrLeaf n_steps_m1 path bottom h' =>
    exact traverse_binary_or_leaf.updates h'
  case Regular n_steps_m1 height_m1 length_m1 edge_path bottom bit h_in_subtree h' =>
    cases h'.view (by simp) h_in_subtree

    case Both res₀ res₁ h'' =>
      by_cases h_bit: bit = 0
      case pos =>
        simp only [if_pos h_bit] at h''
        have ⟨h_traverse₀, h_traverse₁⟩ := h''

        constructor
        · intro update h_update
          simp only [List.mem_append] at h_update
          cases h_update
          case inl h_update =>
            apply is_in_subtree.height_add1 (dir:=0)
            exact (traverse_edge.updates h_traverse₀).1 update h_update
          case inr h_update =>
            apply is_in_subtree.height_add1 (dir:=1)
            exact ((traverse_empty.updates h_traverse₁).1 update h_update).1
        · apply List.append_ne_nil_of_left_ne_nil (traverse_edge.updates h_traverse₀).2
      case neg =>
        simp only [h_bit, reduceIte] at h''
        have ⟨h_traverse₀, h_traverse₁⟩ := h''

        constructor
        · intro update h_update
          simp only [List.mem_append] at h_update
          cases h_update
          case inl h_update =>
            apply is_in_subtree.height_add1 (dir:=0)
            exact ((traverse_empty.updates h_traverse₀).1 update h_update).1
          case inr h_update =>
            apply is_in_subtree.height_add1 (dir:=1)
            exact (traverse_edge.updates h_traverse₁).1 update h_update
        · apply List.append_ne_nil_of_right_ne_nil _ (traverse_edge.updates h_traverse₁).2
    case SingleNonEmpty res₁ h_traverse  =>
      constructor
      · intro update h_update
        apply is_in_subtree.height_add1 (dir:=bit)
        exact (traverse_edge.updates h_traverse).1 update h_update
      · exact (traverse_edge.updates h_traverse).2
    case SingleEmptyLen1 res₁ h_traverse _ _ =>
      have h_in_subtree_res₁ : ∀ update ∈ res₁.updates,
          is_in_subtree (height_m1 + 1) path update.1 := by
        intro update h_update
        apply is_in_subtree.height_add1 (dir:=1 - bit)
        rw [show ↑(1 - bit) = 1 - ↑bit by omega, ←Nat.add_sub_assoc (by omega)]
        exact ((traverse_empty.updates h_traverse).1 update h_update).1
      exact ⟨h_in_subtree_res₁, (traverse_empty.updates h_traverse).2⟩
    case SingleEmptyLenNe1 res₁ h_traverse _ =>
      have h_in_subtree_res₁ : ∀ update ∈ res₁.updates,
          is_in_subtree (height_m1 + 1) path update.1 := by
        intro update h_update
        apply is_in_subtree.height_add1 (dir:=1 - bit)
        rw [show ↑(1 - bit) = 1 - ↑bit by omega, ←Nat.add_sub_assoc (by omega)]
        exact ((traverse_empty.updates h_traverse).1 update h_update).1
      exact ⟨h_in_subtree_res₁, (traverse_empty.updates h_traverse).2⟩
  case Descent n_steps_m1 height_m1 length_m1 edge_path bottom h_traverse_descent =>
    have ⟨descent_length_m2, descent_length, res₁, h_descent_length, h_descent_length_le,
      h_descent_length_le', word, new_edge, h_new_edge, h_in_subtree,
      h_traverse, h_res⟩ := traverse_edge_descend.implies h_traverse_descent
    letify h_descent_length
    simp only at h_new_edge
    letify h_new_edge
    subst h_res

    constructor
    · intro update h_update
      apply is_in_subtree.height_add h_descent_length_le'
      exact (traverse_edge.updates h_traverse).1 update h_update
    · exact (traverse_edge.updates h_traverse).2
end
