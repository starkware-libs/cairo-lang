import patricia.code.traverse_empty
import patricia.code.traverse_non_empty

-- The `traverse_*` functions imply `height ≥ 0`.

theorem traverse_empty.height_ge_zero {n_steps: ℕ} {height: ℤ} {path: ℕ} {res: TraverseResult}
    (h_traverse: traverse_empty n_steps height path res) :
    height ≥ 0 := by
  induction n_steps generalizing height path res
  case zero => contradiction
  case succ n_steps_m1 ih =>
    unfold traverse_empty at h_traverse
    by_cases h_height_zero : height = 0
    case pos => omega
    case neg =>
      simp only [if_neg h_height_zero] at h_traverse
      rcases h_traverse with
        ⟨res₀, res₁, h_traverse₀, h_traverse₁, h_res⟩ |
        ⟨res₀, child_bit, h_traverse, h_res⟩ |
        ⟨res₀, word, length_m2, h_length, h_word, h_traverse, h_res⟩
      · have := ih h_traverse₀
        omega
      · have := ih h_traverse
        omega
      · have := ih h_traverse
        omega

mutual
theorem traverse_non_empty.height_ge_zero {crypto: Crypto} {n_steps: ℕ} {is_new_tree: Bool} {height: ℤ} {path node: ℕ} {res: TraverseResult}
    (h_traverse: traverse_non_empty crypto n_steps is_new_tree height path node res) :
    height ≥ 0 := by
  unfold traverse_non_empty at h_traverse
  cases n_steps
  case zero => contradiction
  case succ n_steps_m1 =>

  rcases h_traverse with
    ⟨edge, h_open_edge, h_traverse_edge⟩ | h
  · exact (traverse_edge.height_ge_zero h_traverse_edge).1
  · exact traverse_binary_or_leaf.height_ge_zero h

theorem traverse_binary_or_leaf.height_ge_zero {crypto: Crypto} {n_steps: ℕ} {is_new_tree: Bool} {height: ℤ} {path node: ℕ} {res: TraverseResult}
    (h_traverse: traverse_binary_or_leaf crypto n_steps is_new_tree height path node res) :
    height ≥ 0 := by
  unfold traverse_binary_or_leaf at h_traverse
  cases n_steps
  case zero => contradiction
  case succ n_steps_m1 =>

  by_cases h_height_zero : height = 0
  case pos => omega
  case neg =>

  simp only [if_neg h_height_zero] at h_traverse
  replace ⟨x, y, h_node, h_traverse⟩ := h_traverse
  rcases h_traverse with
    ⟨res₀, res₁, h_traverse₀, h_traverse₁, h_res⟩ |
    ⟨res₁, h_ne_zero, h_traverse, h_res⟩ |
    ⟨res₁, h_ne_zero, h_traverse, h_res⟩

  all_goals
  · have := traverse_non_empty.height_ge_zero (by assumption)
    omega

theorem traverse_edge.height_ge_zero {crypto: Crypto} {n_steps: ℕ} {is_new_tree: Bool} {height: ℤ} {path: ℕ} {edge: NodeEdge} {res: TraverseResult}
    (h_traverse: traverse_edge crypto n_steps is_new_tree height path edge res) :
    height ≥ 0 ∧ (height = 0 → edge.length = 0) := by
  unfold traverse_edge at h_traverse
  cases n_steps
  case zero => contradiction
  case succ n_steps_m1 =>

  simp only at h_traverse
  split at h_traverse
  · exact ⟨traverse_binary_or_leaf.height_ge_zero (by assumption), by intro; trivial⟩
  · rcases h_traverse with ⟨bit, _, _, h⟩ | h
    · unfold traverse_edge_regular at h
      rcases h with ⟨_, _, h, _⟩ | ⟨_, h, _⟩ | ⟨_, _, h, _⟩
      · split at h
        · have := traverse_edge.height_ge_zero h.1; omega
        · have := traverse_edge.height_ge_zero h.2; omega
      · have := traverse_edge.height_ge_zero h; omega
      · have := traverse_empty.height_ge_zero h; omega
    · unfold traverse_edge_descend at h
      have ⟨_, _, _, _, _, _, _, _, h, _⟩ := h
      have := traverse_edge.height_ge_zero h; omega
end
