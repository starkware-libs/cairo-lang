import patricia.code_proof.helpers
import patricia.code_proof.updates
import patricia.code.main
import patricia.code.traverse_empty
import patricia.code.traverse_non_empty
import patricia.is_in_subtree
import patricia.letify

def sorted_singleton (x: ℕ) : List.SortedLT [x] := by simp [List.SortedLT, StrictMono]

def sorted_append {xs ys: List ℕ} (h_xs: List.SortedLT xs) (h_ys: List.SortedLT ys)
    (boundary: ℕ) (xs_lt: ∀ x ∈ xs, x < boundary) (ys_ge: ∀ y ∈ ys, y ≥ boundary) :
    List.SortedLT (xs ++ ys) := by
  rw [List.sortedLT_iff_getElem_lt_getElem_of_lt] at *
  intro i j h_i h_j h_lt

  by_cases h_i_xs: i < xs.length
  case pos =>
    by_cases h_j_xs: j < xs.length
    case pos =>
      rw [List.getElem_append_left h_i_xs, List.getElem_append_left h_j_xs]
      apply h_xs h_lt
    case neg =>
      rw [List.getElem_append_left h_i_xs, List.getElem_append_right (by omega)]
      rw [List.length_append] at h_j
      have := xs_lt xs[i] (by simp)
      have : j - xs.length < ys.length := by omega
      have := ys_ge ys[j - xs.length] (by simp)
      omega
  case neg =>
    by_cases h_j_xs: j < xs.length
    case pos =>
      omega
    case neg =>
      rw [List.getElem_append_right (by omega), List.getElem_append_right (by omega)]
      apply h_ys (by omega)

-- Given a `traverse_*` trace, the keys of `res.updates` are sorted in strictly increasing order.

theorem traverse_empty.sorted {n_steps height path: ℕ} {res: TraverseResult}
    (h_main: traverse_empty n_steps height path res) :
    List.SortedLT (res.updates.map Prod.fst) := by
  induction n_steps generalizing height path res
  case zero => contradiction
  case succ n_steps_m1 ih =>

  cases height
  case zero =>
    simp only [traverse_empty, CharP.cast_eq_zero, ↓reduceIte, TraverseResult.update] at h_main
    simp [h_main, sorted_singleton]
  case succ height_m1 =>
    simp only [traverse_empty, if_neg (show ↑(height_m1 + 1) ≠ (0: ℤ) by omega)] at h_main
    rcases h_main with
      ⟨res₀, res₁, h_traverse₀, h_traverse₁, h_res⟩ |
      ⟨res₀, child_bit, h_traverse, h_res⟩ |
      ⟨res₀, word, length_m2, h_length, h_word, h_traverse, h_res⟩

    · -- Both children.
      simp only [Nat.cast_add, Nat.cast_one, add_sub_cancel_right] at h_traverse₀ h_traverse₁
      replace h_traverse_updates₀ := ih h_traverse₀
      replace h_traverse_updates₁ := ih h_traverse₁

      subst res
      simp only [List.map_append]
      apply sorted_append (ih h_traverse₀) (ih h_traverse₁)
      · intro x
        rw [List.mem_map]
        intro ⟨update, h₀, h₁⟩
        exact h₁ ▸ (h_traverse₀.updates.1 update h₀).1.2
      · intro x
        rw [List.mem_map]
        intro ⟨update, h₀, h₁⟩
        exact h₁ ▸ (h_traverse₁.updates.1 update h₀).1.1

    · -- One child.
      simp only [Nat.cast_add, Nat.cast_one, add_sub_cancel_right] at h_traverse
      subst res
      exact ih (res:=res₀) h_traverse

    · -- Descend.
      norm_cast at h_length
      have h_eq_nat : ((height_m1 + 1 : ℕ) - (length_m2 + 2 : ℕ) : ℤ) =
        (height_m1 + 1 - (length_m2 + 2) : ℕ) := by omega
      rw [h_eq_nat] at h_traverse
      subst res
      exact ih (res:=res₀) h_traverse

mutual
theorem traverse_non_empty.sorted {crypto: Crypto} {n_steps: ℕ} {is_new_tree: Bool}
    {height path node: ℕ} {res: TraverseResult}
    (h: traverse_non_empty crypto n_steps is_new_tree height path node res) :
    List.SortedLT (res.updates.map Prod.fst) := by
  cases n_steps
  case zero => simp [traverse_non_empty] at h

  unfold traverse_non_empty at h
  rcases h with
    ⟨edge, h_open_edge, h_traverse_edge⟩ | h
  · exact traverse_edge.sorted (h:=h_traverse_edge)
  · exact traverse_binary_or_leaf.sorted (h:=h)

theorem traverse_binary_or_leaf.sorted {crypto: Crypto} {n_steps: ℕ} {is_new_tree: Bool}
    {height path node: ℕ} {res: TraverseResult}
    (h: traverse_binary_or_leaf crypto n_steps is_new_tree height path node res) :
    List.SortedLT (res.updates.map Prod.fst) := by
  cases n_steps
  case zero => simp [traverse_binary_or_leaf] at h

  unfold traverse_binary_or_leaf at h
  cases height
  case zero =>
    simp only [CharP.cast_eq_zero, ↓reduceIte, ne_eq] at h
    simp [h.1, sorted_singleton]
  case succ height_m1 =>
    replace ⟨x, y, h_node, h⟩ := h
    rcases h with
      ⟨res₀, res₁, h_traverse₀, h_traverse₁, h_res⟩ |
      ⟨res₁, h_ne_zero, h_traverse, h_res⟩ |
      ⟨res₁, h_ne_zero, h_traverse, h_res⟩
    · simp only [Nat.cast_add, Nat.cast_one, add_sub_cancel_right] at h_traverse₀ h_traverse₁
      subst res
      simp only [List.map_append]
      apply sorted_append
        (traverse_non_empty.sorted h_traverse₀) (traverse_non_empty.sorted h_traverse₁)
      · intro key
        rw [List.mem_map]
        intro ⟨update, h₀, h₁⟩
        exact h₁ ▸ ((traverse_non_empty.updates h_traverse₀).1 update h₀).2
      · intro key
        rw [List.mem_map]
        intro ⟨update, h₀, h₁⟩
        exact h₁ ▸ ((traverse_non_empty.updates h_traverse₁).1 update h₀).1
    · simp only [Nat.cast_add, Nat.cast_one, add_sub_cancel_right] at h_traverse
      subst res
      exact traverse_non_empty.sorted (res:=res₁) h_traverse
    · simp only [Nat.cast_add, Nat.cast_one, add_sub_cancel_right] at h_traverse
      subst res
      exact traverse_non_empty.sorted (res:=res₁) h_traverse

theorem traverse_edge.sorted {crypto: Crypto} {n_steps height path: ℕ} {edge: NodeEdge}
    {res: TraverseResult}
    (h: traverse_edge crypto n_steps is_new_tree height path edge res) :
    List.SortedLT (res.updates.map Prod.fst) := by
  cases h.view
  case BinaryOrLeaf n_steps_m1 path bottom h' =>
    exact traverse_binary_or_leaf.sorted h'
  case Regular n_steps_m1 height_m1 length_m1 edge_path bottom bit h_in_subtree h' =>
    cases h'.view (by simp) h_in_subtree

    case Both res₀ res₁ h'' =>
      by_cases h_bit: bit = 0
      case pos =>
        simp only [if_pos h_bit] at h''
        have ⟨h_traverse₀, h_traverse₁⟩ := h''

        simp only [List.map_append]
        apply sorted_append
          (traverse_edge.sorted h_traverse₀) (traverse_empty.sorted h_traverse₁)
        · intro key
          rw [List.mem_map]
          intro ⟨update, h₀, h₁⟩
          exact h₁ ▸ ((traverse_edge.updates h_traverse₀).1 update h₀).2
        · intro key
          rw [List.mem_map]
          intro ⟨update, h₀, h₁⟩
          exact h₁ ▸ ((traverse_empty.updates h_traverse₁).1 update h₀).1.1
      case neg =>
        simp only [h_bit, reduceIte] at h''
        have ⟨h_traverse₀, h_traverse₁⟩ := h''

        simp only [List.map_append]
        apply sorted_append
          (traverse_empty.sorted h_traverse₀) (traverse_edge.sorted h_traverse₁)
        · intro key
          rw [List.mem_map]
          intro ⟨update, h₀, h₁⟩
          exact h₁ ▸ (h_traverse₀.updates.1 update h₀).1.2
        · intro key
          rw [List.mem_map]
          intro ⟨update, h₀, h₁⟩
          exact h₁ ▸ (h_traverse₁.updates.1 update h₀).1
    case SingleNonEmpty res₁ h_traverse =>
      exact traverse_edge.sorted (res:=res₁) h_traverse
    case SingleEmptyLen1 res₁ h_traverse _ _ =>
      exact h_traverse.sorted (res:=res₁)
    case SingleEmptyLenNe1 res₁ h_traverse _ =>
      exact h_traverse.sorted (res:=res₁)
  case Descent n_steps_m1 height_m1 length_m1 edge_path bottom h_traverse_descent =>
    have ⟨descent_length_m2, descent_length, res₁, h_descent_length, h_descent_length_le,
      h_descent_length_le', word, new_edge, h_new_edge, h_in_subtree,
      h_traverse, h_res⟩ := traverse_edge_descend.implies h_traverse_descent
    subst h_res
    exact h_traverse.sorted (res:=res₁)
end
