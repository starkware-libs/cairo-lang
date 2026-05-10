import patricia.code
import patricia.code_proof.helpers
import patricia.code_proof.updates
import patricia.patricia.tree
import patricia.traverse_result.values
import patricia.traverse_result.weak_valid

-- Given a weakly-valid `res` (see `traverse_result/weak_valid.lean`) and a `traverse_*` trace,
-- `res` is (not-weakly) valid, and The build tree from `res.values` is consistent with the function
-- parameters (see documentation of each function).

-- The built tree is empty.
theorem traverse_empty.root_eq {crypto: Crypto} {n_steps height path: ℕ} {res: TraverseResult}
    {ref: PatriciaTree height}
    (h_weak_valid: res.weak_valid crypto path ref)
    (h: traverse_empty n_steps height path res)
    (h_height: height ≤ crypto.max_height) :
    let values := λ x ↦ res.values path ref (x + path * 2 ^ height)
    res.valid crypto path ref ∧
    PatriciaTree.build height values = .Empty _ := by
  induction n_steps generalizing height path res
  case zero => contradiction
  case succ n_steps_m1 ih =>

  cases height
  case zero =>
    unfold traverse_empty at h
    subst res
    simp only [TraverseResult.valid, PatriciaTree.build, PatriciaNode.build,
      TraverseResult.values]
    constructor
    · use 0
    · simp [TraverseResult.filtered_updates]; rfl

  case succ height_m1 =>
    unfold traverse_empty at h

    rcases h with
      ⟨res₀, res₁, h_traverse₀, h_traverse₁, h_res⟩ |
      ⟨res₀, child_bit, h_traverse, h_res⟩ |
      ⟨res₀, word, length_m2, h_length, h_word, h_traverse, h_res⟩

    · -- Both children.
      simp only [Nat.cast_add, Nat.cast_one, add_sub_cancel_right] at h_traverse₀ h_traverse₁
      intro values

      let values_left := λ x ↦ res₀.values (path * 2) ref.left_subtree (x + path * 2 * 2 ^ height_m1)
      let values_right := λ x ↦ res₁.values (path * 2 + 1) ref.right_subtree (x + (path * 2 + 1) * 2 ^ height_m1)

      subst res
      have h_binary := TraverseResult.weak_valid.binary
        (h_height:=by omega)
        (λ u h ↦ ((traverse_empty.updates h_traverse₀).1 u h).1)
        (λ u h ↦ ((traverse_empty.updates h_traverse₁).1 u h).1)
        (traverse_empty.updates h_traverse₀).2
        (traverse_empty.updates h_traverse₁).2
        h_weak_valid
      have ⟨h_x_valid, h_x⟩ := ih (ref:=ref.left_subtree) h_binary.1
        h_traverse₀ (h_height:=by omega)
      replace h_x : (PatriciaTree.build height_m1 values_left) = .Empty _ := h_x

      have ⟨h_y_valid, h_y⟩ := ih (ref:=ref.right_subtree) (h_binary.2 h_x_valid)
        h_traverse₁ (h_height:=by omega)
      replace h_y : (PatriciaTree.build height_m1 values_right) = .Empty _ := h_y

      refine ⟨TraverseResult.valid.mk_both rfl h_x_valid h_y_valid, ?_⟩
      simp only [PatriciaTree.build, PatriciaNode.build, PatriciaTree.ext_iff] at h_x h_y ⊢

      conv in PatriciaNode.merge _ _ =>
        congr
        · rw [PatriciaNode.build_congr (by
            intro i
            show _ = values_left i
            simp only [values, values_left]
            apply TraverseResult.values_eq_of_filtered_left i
            rw [TraverseResult.filtered_updates.add]
            rw [(by ring: i + path * 2 ^ (height_m1 + 1) = i + path * 2 * 2 ^ height_m1)]
            rw [TraverseResult.filtered_updates.empty_of_disjoint_subtree
                (λ u h ↦ ((traverse_empty.updates h_traverse₁).1 u h).1) _
                (is_in_subtree.mk (path * 2) i) (by simp)
            ]
            rw [List.append_nil]
          )]
        · rw [PatriciaNode.build_congr (by
            intro i
            show _ = values_right i
            simp only [values, values_right]
            apply TraverseResult.values_eq_of_filtered_right i
            rw [TraverseResult.filtered_updates.add]
            rw [(by ring: i + 2 ^ height_m1 + path * 2 ^ (height_m1 + 1) =
              i + (path * 2 + 1) * 2 ^ height_m1)]
            rw [TraverseResult.filtered_updates.empty_of_disjoint_subtree
                (λ u h ↦ ((traverse_empty.updates h_traverse₀).1 u h).1) _
                (is_in_subtree.mk (path * 2 + 1) i) (by simp),
            ]
            rw [List.nil_append]
          )]

      rw [h_x, h_y]
      rfl
    · -- One child.
      simp only [Nat.cast_add, Nat.cast_one, add_sub_cancel_right] at h_traverse
      intro values

      subst res
      fin_cases child_bit
      case «0» =>
        let values_left := λ x ↦ res₀.values (path * 2) ref.left_subtree (x + path * 2 * 2 ^ height_m1)

        have h_single := TraverseResult.weak_valid.single
          (dir:=0) (sibling:=0)
          (λ u h ↦ ((traverse_empty.updates h_traverse).1 u h).1)
          h_weak_valid

        have ⟨h_x_valid, h_x⟩ := ih (ref:=ref.left_subtree) h_single.1
            h_traverse (h_height:=by omega)
        replace h_x : (PatriciaTree.build height_m1 values_left) = .Empty _ := h_x

        have h_right_empty : ref.right_subtree = .Empty _ :=
          PatriciaTree.hash_inj (by omega) h_single.2.symm

        refine ⟨TraverseResult.valid.mk_edge 0 (by rw [← h_single.2]) h_x_valid, ?_⟩
        simp only [PatriciaTree.build, PatriciaNode.build, PatriciaTree.ext_iff] at h_x h_right_empty ⊢

        conv in PatriciaNode.merge _ _ =>
          congr
          · rw [PatriciaNode.build_congr (by
              intro i
              show _ = values_left i
              simp only [values, values_left]
              apply TraverseResult.values_eq_of_filtered_left i
              rw [TraverseResult.filtered_updates.congr (show _ = res₀.updates by simp)]
            )]
          · rw [PatriciaNode.build_congr (by
              intro i
              show _ = ref.right_subtree.at i
              simp only [values]
              have h_eq : i + 2 ^ height_m1 + path * 2 ^ (height_m1 + 1) =
                i + (path * 2 + 1) * 2 ^ height_m1 := by ring
              rw [TraverseResult.values.congr_res (show _ = res₀.updates by rfl)]
              rw [TraverseResult.values.eq_ref_at
                (λ u h ↦ ((traverse_empty.updates h_traverse).1 u h).1)
                (h_eq ▸ is_in_subtree.mk (path * 2 + 1) i) (by simp)]
              simp [PatriciaTree.right_subtree_at]
            ), PatriciaTree.at_build]

        rw [h_x, h_right_empty]
        rfl
      case «1» =>
        let values_right := λ x ↦ res₀.values (path * 2 + 1) ref.right_subtree
          (x + (path * 2 + 1) * 2 ^ height_m1)

        have h_single := TraverseResult.weak_valid.single
          (dir:=1) (sibling:=0)
          (λ u h ↦ ((traverse_empty.updates h_traverse).1 u h).1)
          h_weak_valid

        have ⟨h_x_valid, h_x⟩ :=
          ih (ref:=ref.right_subtree) h_single.1
            h_traverse (h_height:=by omega)
        replace h_x : (PatriciaTree.build height_m1 values_right) = .Empty _ := h_x

        have h_left_empty : ref.left_subtree = .Empty _ :=
          PatriciaTree.hash_inj (by omega) h_single.2.symm

        refine ⟨TraverseResult.valid.mk_edge 1 (by rw [← h_single.2]) h_x_valid, ?_⟩
        simp only [PatriciaTree.build, PatriciaNode.build, PatriciaTree.ext_iff] at h_x h_left_empty ⊢

        conv in PatriciaNode.merge _ _ =>
          congr
          · rw [PatriciaNode.build_congr (by
              intro i
              show _ = ref.left_subtree.at i
              simp only [values]
              have h_eq : i + path * 2 ^ (height_m1 + 1) = i + path * 2 * 2 ^ height_m1 := by ring
              rw [TraverseResult.values.congr_res (show _ = res₀.updates by rfl)]
              rw [TraverseResult.values.eq_ref_at
                (λ u h ↦ ((traverse_empty.updates h_traverse).1 u h).1)
                (h_eq ▸ is_in_subtree.mk (path * 2) i) (by simp)]
              simp [PatriciaTree.left_subtree_at]
            ), PatriciaTree.at_build]
          · rw [PatriciaNode.build_congr (by
              intro i
              show _ = values_right i
              simp only [values, values_right]
              apply TraverseResult.values_eq_of_filtered_right i
              rw [TraverseResult.filtered_updates.congr (show _ = res₀.updates by simp)]
            )]

        rw [h_left_empty, h_x]
        rfl
    · -- Descend.
      have h_eq_nat : ((height_m1 + 1 : ℕ) - (length_m2 + 2 : ℕ) : ℤ) =
        (height_m1 + 1 - (length_m2 + 2) : ℕ) := by omega
      rw [h_eq_nat] at h_traverse

      intro values

      let word_fin : Fin (2 ^ (length_m2 + 2)) := ⟨word, h_word⟩

      subst res
      have ⟨h_descent, h_empty⟩ := TraverseResult.weak_valid.descent
        (h_height:=by omega) (length_m2:=length_m2) (word:=word_fin)
        (h_length:=by omega)
        (λ u h ↦ ((traverse_empty.updates h_traverse).1 u h).1)
        h_weak_valid

      have ⟨h_inner_valid, h_inner_build⟩ :=
        ih h_descent h_traverse (h_height := by omega)

      refine ⟨TraverseResult.valid.mk_descent length_m2 word_fin (by omega) rfl h_inner_valid h_empty, ?_⟩

      apply PatriciaTree.at.inj
      intro i
      simp [PatriciaTree.build_at, PatriciaTree.at_empty, values]
      have ⟨word_i, h_word_i⟩ := is_in_subtree.height_add' (length_m2 + 2) (by omega)
        (is_in_subtree.mk path i)

      let offset : ℕ := word_i * 2 ^ (height_m1 + 1 - (length_m2 + 2))
      have i_ge : i ≥ offset := by
        have := h_word_i.1
        conv at this => rhs; rw [add_mul, mul_assoc, ←Nat.pow_add, Nat.add_sub_cancel' (by omega), add_comm]
        omega
      have i_lt: i - offset < 2 ^ (height_m1 + 1 - (length_m2 + 2)) := by
        have := h_word_i.2
        conv at this => rhs; rw [add_mul, add_mul, mul_assoc, ←Nat.pow_add, Nat.add_sub_cancel' (by omega), one_mul]
        omega

      rw [TraverseResult.values.congr_res (show _ = res₀.updates by rfl)]
      rw [TraverseResult.values.descent (h_in_subtree:=h_word_i) (h_length:=by omega)]

      by_cases h_word_i_eq : word_i = word
      case pos =>
        subst word

        apply PatriciaTree.ext_iff.1 at h_inner_build
        apply PatriciaNode.build_is_empty at h_inner_build
        replace h_inner_build := h_inner_build ⟨(i : ℕ) - offset, i_lt⟩
        simp only at h_inner_build
        have : i - offset + (path * 2 ^ (length_m2 + 2) + ↑word_fin) * 2 ^ (height_m1 + 1 - (length_m2 + 2)) =
            i + path * 2 ^ (height_m1 + 1) := by
          rw [add_mul, mul_assoc, ←Nat.pow_add, Nat.add_sub_cancel' (by omega)]
          show ↑i - offset + (path * 2 ^ (height_m1 + 1) + offset) = _
          omega
        simp only [this] at h_inner_build
        exact h_inner_build
      case neg =>
        rw [TraverseResult.values.eq_ref_at
          (res := res₀)
          (λ u h ↦ ((traverse_empty.updates h_traverse).1 u h).1)
          h_word_i (by simp; omega)]
        rw [h_empty word_i (by intro h; simp [←h, word_fin] at h_word_i_eq)]
        simp [PatriciaTree.at_empty]

mutual
-- See documentation at the top of the file.
-- The build tree is consistent with the `node` hash, and is non-empty.
theorem traverse_non_empty.root_eq {crypto: Crypto} {n_steps height path node: ℕ} {res: TraverseResult}
    {ref: PatriciaTree height}
    (h_valid: res.weak_valid crypto path ref)
    (h: traverse_non_empty crypto n_steps true height path node res)
    (h_height: height ≤ crypto.max_height) :
    let values := λ x ↦ res.values path ref (x + path * 2 ^ height)
    res.valid crypto path ref ∧
    node = (PatriciaTree.build height values).hash crypto ∧
    node ≠ 0 := by
  unfold traverse_non_empty at h

  -- n_steps must be > 0.
  cases n_steps
  case zero => unfold traverse_binary_or_leaf at h; contradiction
  case succ n_steps_m1 =>

  rcases h with ⟨edge, h_open_edge, h_traverse_edge⟩ | h
  · have ⟨h_length_ge, h_length_le, h_edge_path_le, h_node⟩ := h_open_edge
    have ⟨h_valid, h_hash, h_node_len0, h_node_len_ne0, h_hash_ne_zero⟩ :=
      traverse_edge.root_eq h_valid h_traverse_edge h_height h_length_le

    unfold NodeEdge.hash at h_hash h_hash_ne_zero
    rw [ite_cond_eq_false _ _ (by
      simp only [eq_iff_iff, iff_false]
      intro h
      simp [h] at h_length_ge
    )] at h_hash h_hash_ne_zero
    simp only [←h_node] at h_hash h_hash_ne_zero

    exact ⟨h_valid, h_hash.symm, h_hash_ne_zero⟩

  · have ⟨h_valid, h_hash, h_valid_edge_bottom, h_hash_ne_zero⟩ :=
      traverse_binary_or_leaf.root_eq h_valid h h_height
    exact ⟨h_valid, h_hash, h_hash_ne_zero⟩

-- See documentation at the top of the file.
-- The build tree is consistent with the `node` hash, and satisfies `valid_edge_bottom`.
theorem traverse_binary_or_leaf.root_eq {crypto: Crypto} {n_steps height path node: ℕ} {res: TraverseResult}
    {ref: PatriciaTree height}
    (h_weak_valid: res.weak_valid crypto path ref)
    (h: traverse_binary_or_leaf crypto n_steps true height path node res)
    (h_height: height ≤ crypto.max_height) :
    let values := λ x ↦ res.values path ref (x + path * 2 ^ height)
    let tree := PatriciaTree.build height values
    res.valid crypto path ref ∧
    node = tree.hash crypto ∧
    tree.node.valid_edge_bottom ∧
    node ≠ 0 := by
  unfold traverse_binary_or_leaf at h

  -- n_steps must be > 0.
  cases n_steps
  case zero => contradiction
  case succ n_steps_m1 =>

  cases height
  case zero =>
    intro values
    have ⟨_, h_node_ne_zero⟩ := h
    subst res
    have : values 0 = node := by
      simp [values, TraverseResult.values, TraverseResult.filtered_updates]
    simp [PatriciaTree.build, PatriciaNode.build, this, PatriciaTree.hash, h_node_ne_zero,
      PatriciaNode.node_hash, TraverseResult.valid, PatriciaNode.valid_edge_bottom]
  case succ height_m1 =>
    replace ⟨x, y, h_node, h⟩ := h
    rcases h with
      ⟨res₀, res₁, h_traverse₀, h_traverse₁, h_res⟩ |
      ⟨res₁, h_ne_zero, h_traverse, h_res⟩ |
      ⟨res₁, h_ne_zero, h_traverse, h_res⟩
    · -- Binary case.
      simp only [Nat.cast_add, Nat.cast_one, add_sub_cancel_right] at h_traverse₀ h_traverse₁
      intro values

      let values_left := λ x ↦ res₀.values (path * 2) ref.left_subtree (x + path * 2 * 2 ^ height_m1)
      let values_right := λ x ↦ res₁.values (path * 2 + 1) ref.right_subtree (x + (path * 2 + 1) * 2 ^ height_m1)

      subst res
      have h_binary := TraverseResult.weak_valid.binary
        (h_height:=by omega)
        (traverse_non_empty.updates h_traverse₀).1
        (traverse_non_empty.updates h_traverse₁).1
        (traverse_non_empty.updates h_traverse₀).2
        (traverse_non_empty.updates h_traverse₁).2
        h_weak_valid
      have ⟨h_x_valid, h_x_hash, h_x_ne_zero⟩ :=
        traverse_non_empty.root_eq (ref:=ref.left_subtree) h_binary.1
          h_traverse₀ (h_height:=by omega)
      replace h_x_hash : x = (PatriciaTree.build height_m1 values_left).hash crypto := h_x_hash

      have ⟨h_y_valid, h_y_hash, h_y_ne_zero⟩ :=
        traverse_non_empty.root_eq (ref:=ref.right_subtree) (h_binary.2 h_x_valid)
          h_traverse₁ (h_height:=by omega)
      replace h_y_hash : y = (PatriciaTree.build height_m1 values_right).hash crypto := h_y_hash

      have := PatriciaTree.build_hash_binary
        (values:=values)
        (PatriciaTree.build height_m1 values_left)
        (PatriciaTree.build height_m1 values_right)
        (by
          intro i
          rw [PatriciaTree.build_at]
          simp only [values, values_left]
          apply TraverseResult.values_eq_of_filtered_left i
          rw [TraverseResult.filtered_updates.add]
          rw [(by ring: i + path * 2 ^ (height_m1 + 1) = i + path * 2 * 2 ^ height_m1)]
          rw [TraverseResult.filtered_updates.empty_of_disjoint_subtree
            (traverse_non_empty.updates h_traverse₁).1 _
            (is_in_subtree.mk (path * 2) i) (by simp)]
          rw [List.append_nil])
        (by
          intro i
          rw [PatriciaTree.build_at]
          simp only [values, values_right]
          apply TraverseResult.values_eq_of_filtered_right i
          rw [TraverseResult.filtered_updates.add]
          rw [(by ring: i + 2 ^ height_m1 + path * 2 ^ (height_m1 + 1) =
            i + (path * 2 + 1) * 2 ^ height_m1)]
          rw [TraverseResult.filtered_updates.empty_of_disjoint_subtree
            (traverse_non_empty.updates h_traverse₀).1 _
            (is_in_subtree.mk (path * 2 + 1) i) (by simp)]
          rw [List.nil_append])
        (by rw [←h_x_hash]; exact h_x_ne_zero)
        (by rw [←h_y_hash]; exact h_y_ne_zero)

      rw [h_node, h_x_hash, h_y_hash]

      exact ⟨
        TraverseResult.valid.mk_both rfl h_x_valid h_y_valid,
        (by rw [this]; rfl),
        (by rw [this]; rfl),
        by apply crypto.hash_ne_zero'
      ⟩

    · -- Left case.
      simp only [Nat.cast_add, Nat.cast_one, add_sub_cancel_right] at h_traverse
      intro values
      let values_left := λ x ↦ res₁.values (path * 2) ref.left_subtree (x + (path * 2) * 2 ^ height_m1)

      subst res
      have h_single := h_weak_valid.single
        (dir:=0) (sibling:=y)
        (traverse_non_empty.updates h_traverse).1

      have ⟨h_x_valid, h_x_hash, h_x_ne_zero⟩ :=
        traverse_non_empty.root_eq (ref:=ref.left_subtree) h_single.1
          h_traverse (h_height:=by omega)
      replace h_x_hash : x = (PatriciaTree.build height_m1 values_left).hash crypto := h_x_hash

      have : y = ref.right_subtree.hash crypto := h_single.2
      subst y

      have := PatriciaTree.build_hash_binary
        (values:=values)
        (PatriciaTree.build height_m1 values_left)
        ref.right_subtree
        (by
          intro i
          rw [PatriciaTree.build_at]
          simp only [values, values_left]
          apply TraverseResult.values_eq_of_filtered_left i
          rw [TraverseResult.filtered_updates.congr (show _ = res₁.updates by simp)])
        (by
          intro i
          simp only [values]
          have h_eq : i + 2 ^ height_m1 + path * 2 ^ (height_m1 + 1) =
            i + (path * 2 + 1) * 2 ^ height_m1 := by ring
          rw [TraverseResult.values.congr_res (show _ = res₁.updates by simp)]
          rw [TraverseResult.values.eq_ref_at
            (traverse_non_empty.updates h_traverse).1
            (h_eq ▸ is_in_subtree.mk (path * 2 + 1) i) (by simp)]
          simp [PatriciaTree.right_subtree_at])
        (by rw [←h_x_hash]; exact h_x_ne_zero)
        h_ne_zero

      rw [h_node, h_x_hash]

      exact ⟨
        TraverseResult.valid.mk_edge 0 rfl h_x_valid,
        (by rw [this]; rfl),
        (by rw [this]; rfl),
        by apply crypto.hash_ne_zero'
      ⟩
    · -- Right case.
      simp only [Nat.cast_add, Nat.cast_one, add_sub_cancel_right] at h_traverse
      intro values
      let values_right := λ x ↦
        res₁.values (path * 2 + 1) ref.right_subtree (x + (path * 2 + 1) * 2 ^ height_m1)

      subst res
      have h_single := TraverseResult.weak_valid.single
        (dir:=1) (sibling:=x)
        (traverse_non_empty.updates h_traverse).1
        h_weak_valid

      have ⟨h_y_valid, h_y_hash, h_y_ne_zero⟩ :=
        traverse_non_empty.root_eq (ref:=ref.right_subtree) h_single.1
          h_traverse (h_height:=by omega)
      replace h_y_hash : y = (PatriciaTree.build height_m1 values_right).hash crypto := h_y_hash

      have : x = ref.left_subtree.hash crypto := h_single.2
      subst x

      have := PatriciaTree.build_hash_binary
        (values:=values)
        ref.left_subtree
        (PatriciaTree.build height_m1 values_right)
        (by
          intro i
          simp only [values]
          have h_eq : i + path * 2 ^ (height_m1 + 1) = i + path * 2 * 2 ^ height_m1 := by ring
          rw [TraverseResult.values.eq_ref_at
            (res := ((TraverseResult.sibling (PatriciaTree.hash crypto ref.left_subtree)).add res₁))
            (traverse_non_empty.updates h_traverse).1
            (h_eq ▸ is_in_subtree.mk (path * 2) i) (by simp)]
          simp [PatriciaTree.left_subtree_at])
        (by
          intro i
          rw [PatriciaTree.build_at]
          simp only [values, values_right]
          apply TraverseResult.values_eq_of_filtered_right i
          rw [TraverseResult.filtered_updates.congr (show _ = res₁.updates by simp)])
        h_ne_zero
        (by rw [←h_y_hash]; exact h_y_ne_zero)

      rw [h_node, h_y_hash]

      exact ⟨
        TraverseResult.valid.mk_edge 1 rfl h_y_valid,
        (by rw [this]; rfl),
        (by rw [this]; rfl),
        by apply crypto.hash_ne_zero'
      ⟩

-- See documentation at the top of the file.
-- The build tree is consistent with the `edge` argument.
-- In addition, if edge.length = 0 then it satisfies `valid_edge_bottom`.
-- If edge.length ≠ 0 then it is an Edge node with length ≤ crypto.max_height and height ≠ 0.
theorem traverse_edge.root_eq {crypto: Crypto} {n_steps height path: ℕ} {edge: NodeEdge} {res: TraverseResult}
    {ref: PatriciaTree height}
    (h_weak_valid: res.weak_valid crypto path ref)
    (h: traverse_edge crypto n_steps true height path edge res)
    (h_height: height ≤ crypto.max_height)
    (h_length: edge.length ≤ crypto.max_height) :
    let values := λ x ↦ res.values path ref (x + path * 2 ^ height)
    let tree := PatriciaTree.build height values
    res.valid crypto path ref ∧
    tree.hash crypto = edge.hash crypto ∧
    (edge.length = 0 → tree.node.valid_edge_bottom) ∧
    (edge.length ≠ 0 → ∃ e b, tree.node = .Edge e b ∧ e.length ≤ crypto.max_height ∧ height ≠ 0) ∧
    edge.hash crypto ≠ 0 := by
  cases h.view
  case BinaryOrLeaf n_steps_m1 path bottom h' =>
    have ⟨h_valid, h_hash, h_valid_edge_bottom, h_hash_ne_zero⟩ := traverse_binary_or_leaf.root_eq h_weak_valid h' h_height
    exact ⟨
      h_valid,
      (by simp [NodeEdge.hash, h_hash]),
      (by intro; exact h_valid_edge_bottom),
      (by intro; contradiction),
      h_hash_ne_zero
    ⟩

  case Regular n_steps_m1 height_m1 length_m1 edge_path bottom bit h_in_subtree h' =>
    simp only [Order.add_one_le_iff] at h_length
    have : NodeEdge.hash ⟨length_m1 + 1, edge_path, bottom⟩ crypto ≠ 0 := by
      simp [NodeEdge.hash, crypto.hash_ne_zero']
    simp only [ne_eq, this, not_false_eq_true, and_true]

    cases h'.view (by simp) h_in_subtree
    case Both res₀ res₁ h'' =>
      by_cases h_bit : bit = 0
      case pos =>
        subst bit
        simp only [Fin.isValue, ↓reduceIte] at h''
        obtain ⟨h_traverse_edge, h_traverse_empty⟩ := h''

        let values_edge := λ x ↦ res₀.values (path * 2) ref.left_subtree (x + path * 2 * 2 ^ height_m1)
        let values_empty := λ x ↦ res₁.values (path * 2 + 1) ref.right_subtree (x + (path * 2 + 1) * 2 ^ height_m1)

        have h_binary := TraverseResult.weak_valid.binary
          (h_height := by omega)
          (traverse_edge.updates h_traverse_edge).1
          (λ u h ↦ ((traverse_empty.updates h_traverse_empty).1 u h).1)
          (traverse_edge.updates h_traverse_edge).2
          (traverse_empty.updates h_traverse_empty).2
          h_weak_valid

        have ⟨h_valid_edge, h_hash, h_node_len0, h_node_len_ne0, h_hash_ne_zero⟩ :=
          traverse_edge.root_eq (ref := ref.left_subtree) h_binary.1
            h_traverse_edge (h_height := by omega) (h_length := by simp; omega)

        have ⟨h_valid_empty, h_build_empty⟩ :=
          traverse_empty.root_eq (ref := ref.right_subtree) (h_binary.2 h_valid_edge)
            h_traverse_empty (h_height := by omega)

        replace h_hash : (PatriciaTree.build height_m1 values_edge).hash crypto = _ := h_hash

        have h_values_empty_zero : ∀ i: Fin (2 ^ height_m1), values_empty i = 0 := by
          intro i
          apply PatriciaNode.build_is_empty (height := height_m1)
          apply PatriciaTree.ext_iff.1 at h_build_empty
          exact h_build_empty

        use TraverseResult.valid.mk_both rfl h_valid_edge h_valid_empty

        simp only [Nat.add_eq_zero_iff, one_ne_zero, and_false, false_imp_iff, not_false_eq_true,
          true_imp_iff, true_and]
        rw [PatriciaTree.build_edge
          (PatriciaTree.build height_m1 values_edge)
          0
          (by
            intro i
            simp only [PatriciaTree.build_at, values_edge, Fin.isValue, Fin.val_zero, zero_mul, add_zero]
            apply TraverseResult.values_eq_of_filtered_left i
            rw [TraverseResult.filtered_updates.add]
            rw [(by ring : (i : ℕ) + path * 2 ^ (height_m1 + 1) = i + path * 2 * 2 ^ height_m1)]
            rw [TraverseResult.filtered_updates.empty_of_disjoint_subtree
              (λ u h ↦ ((traverse_empty.updates h_traverse_empty).1 u h).1) _
              (is_in_subtree.mk (path * 2) i) (by simp)]
            rw [List.append_nil])
          (by
            intro i
            simp only [Fin.isValue, Fin.val_zero, Nat.sub_zero, one_mul]
            have h_values_eq :
                (res₀.add res₁).values path ref (↑i + 2 ^ height_m1 + path * 2 ^ (height_m1 + 1)) =
                res₁.values (path * 2 + 1) ref.right_subtree (↑i + (path * 2 + 1) * 2 ^ height_m1) := by
              apply TraverseResult.values_eq_of_filtered_right i
              rw [TraverseResult.filtered_updates.add]
              rw [(by ring : (↑i + 2 ^ height_m1 + path * 2 ^ (height_m1 + 1) : ℕ) =
                ↑i + (path * 2 + 1) * 2 ^ height_m1)]
              rw [TraverseResult.filtered_updates.empty_of_disjoint_subtree
                (traverse_edge.updates h_traverse_edge).1 _
                (is_in_subtree.mk (path * 2 + 1) i) (by simp)]
              rw [List.nil_append]
            rw [h_values_eq]
            exact h_values_empty_zero i)
          (by rw [h_hash]; exact h_hash_ne_zero)
        ]

        cases length_m1
        case zero =>
          simp only [PatriciaTree.hash, NodeEdge.hash, ↓reduceIte] at h_hash
          have h := h_node_len0 (by simp)
          replace h : (PatriciaTree.build height_m1 values_edge).node.valid_edge_bottom := h
          unfold PatriciaTree.hash
          rw [PatriciaTree.mk_edge.of_valid_edge_bottom 0 h]
          simp only [Fin.isValue, show edge_path = 0 by
            simpa only [is_in_subtree.height0] using h_in_subtree]
          simp [PatriciaNode.node_hash, NodeEdge.hash, h_hash, h_length]
        case succ length_m2 =>
          have ⟨e, b, h, h_e_length, _⟩ := h_node_len_ne0 (by simp)
          replace h : (PatriciaTree.build height_m1 values_edge).node = .Edge e b := h
          simp only [PatriciaTree.mk_edge, PatriciaNode.mk_edge, h, EdgePath.extend, EdgePath.length,
            PatriciaTree.hash, PatriciaNode.node_hash, NodeEdge.hash] at h_hash ⊢
          apply crypto.h_hash h_e_length (by omega) at h_hash
          constructor
          · simp [h_hash]
          · exact ⟨e.extend 0, b, rfl, by simp; omega⟩
      case neg =>
        have h_bit_one : bit = 1 := by fin_cases bit <;> trivial
        subst bit
        simp only [Fin.isValue, one_ne_zero, ↓reduceIte] at h''
        obtain ⟨h_traverse_empty, h_traverse_edge⟩ := h''

        let values_empty := λ x ↦ res₀.values (path * 2) ref.left_subtree (x + path * 2 * 2 ^ height_m1)
        let values_edge := λ x ↦ res₁.values (path * 2 + 1) ref.right_subtree (x + (path * 2 + 1) * 2 ^ height_m1)

        have h_binary := TraverseResult.weak_valid.binary
          (h_height := by omega)
          (λ u h ↦ ((traverse_empty.updates h_traverse_empty).1 u h).1)
          (traverse_edge.updates h_traverse_edge).1
          (traverse_empty.updates h_traverse_empty).2
          (traverse_edge.updates h_traverse_edge).2
          h_weak_valid

        have ⟨h_valid_empty, h_build_empty⟩ :=
          traverse_empty.root_eq (ref := ref.left_subtree) h_binary.1
            h_traverse_empty (h_height := by omega)

        have ⟨h_valid_edge, h_hash, h_node_len0, h_node_len_ne0, h_hash_ne_zero⟩ :=
          traverse_edge.root_eq (ref := ref.right_subtree) (h_binary.2 h_valid_empty)
            h_traverse_edge (h_height := by omega) (h_length := by simp; omega)

        replace h_hash : (PatriciaTree.build height_m1 values_edge).hash crypto = _ := h_hash

        have h_values_empty_zero : ∀ i: Fin (2 ^ height_m1), values_empty i = 0 := by
          intro i
          apply PatriciaNode.build_is_empty (height := height_m1)
          apply PatriciaTree.ext_iff.1 at h_build_empty
          exact h_build_empty

        use TraverseResult.valid.mk_both rfl h_valid_empty h_valid_edge

        simp only [Nat.add_eq_zero_iff, one_ne_zero, and_false, false_imp_iff, not_false_eq_true,
          true_imp_iff, true_and]
        rw [PatriciaTree.build_edge
          (PatriciaTree.build height_m1 values_edge)
          1
          (by
            intro i
            simp only [PatriciaTree.build_at, values_edge, Fin.isValue, Fin.val_one, one_mul]
            apply TraverseResult.values_eq_of_filtered_right i
            rw [TraverseResult.filtered_updates.add]
            rw [(by ring : (↑i + 2 ^ height_m1 + path * 2 ^ (height_m1 + 1) : ℕ) =
              ↑i + (path * 2 + 1) * 2 ^ height_m1)]
            rw [TraverseResult.filtered_updates.empty_of_disjoint_subtree
              (λ u h ↦ ((traverse_empty.updates h_traverse_empty).1 u h).1) _
              (is_in_subtree.mk (path * 2 + 1) i) (by simp)]
            rw [List.nil_append])
          (by
            intro i
            norm_num
            have h_values_eq :
                (res₀.add res₁).values path ref (↑i + path * 2 ^ (height_m1 + 1)) =
                res₀.values (path * 2) ref.left_subtree (↑i + path * 2 * 2 ^ height_m1) := by
              apply TraverseResult.values_eq_of_filtered_left i
              rw [TraverseResult.filtered_updates.add]
              rw [(by ring : (↑i + path * 2 ^ (height_m1 + 1) : ℕ) = ↑i + path * 2 * 2 ^ height_m1)]
              rw [TraverseResult.filtered_updates.empty_of_disjoint_subtree
                (traverse_edge.updates h_traverse_edge).1 _
                (is_in_subtree.mk (path * 2) i) (by simp)]
              rw [List.append_nil]
            rw [h_values_eq]
            exact h_values_empty_zero i)
          (by rw [h_hash]; exact h_hash_ne_zero)
        ]

        cases length_m1
        case zero =>
          simp only [PatriciaTree.hash, NodeEdge.hash, ↓reduceIte] at h_hash
          have h := h_node_len0 (by simp)
          replace h : (PatriciaTree.build height_m1 values_edge).node.valid_edge_bottom := h
          unfold PatriciaTree.hash
          rw [PatriciaTree.mk_edge.of_valid_edge_bottom 1 h]
          simp only [Fin.isValue, show edge_path = 1 by
            simpa only [is_in_subtree.height0] using h_in_subtree]
          simp [PatriciaNode.node_hash, NodeEdge.hash, h_hash, h_length]
        case succ length_m2 =>
          have ⟨e, b, h, h_e_length, _⟩ := h_node_len_ne0 (by simp)
          replace h : (PatriciaTree.build height_m1 values_edge).node = .Edge e b := h
          simp only [PatriciaTree.mk_edge, PatriciaNode.mk_edge, h, EdgePath.extend, EdgePath.length,
            PatriciaTree.hash, PatriciaNode.node_hash, NodeEdge.hash] at h_hash ⊢
          apply crypto.h_hash h_e_length (by omega) at h_hash
          constructor
          · simp [h_hash]
            rw [Nat.sub_add_cancel (by simpa using h_in_subtree.1)]
          · exact ⟨e.extend 1, b, rfl, by simp; omega⟩

    case SingleNonEmpty res₁ h_traverse =>
      have ⟨h_weak_valid', h_hash_other⟩ := h_weak_valid.single bit 0
        (λ update h_update ↦ h_traverse.updates.1 update h_update)
      have ⟨h_valid, h_hash, h_node_len0, h_node_len_ne0, h_hash_ne_zero⟩ :=
        traverse_edge.root_eq h_weak_valid' h_traverse (by omega) (by simp; omega)

      use TraverseResult.valid.mk_edge bit (by rw [h_hash_other]) h_valid

      let values' := λ x ↦ res₁.values (path * 2 + bit) (ref.subtree bit) (x + (path * 2 + bit) * 2 ^ height_m1)
      replace h_hash : (PatriciaTree.build height_m1 values').hash crypto = _ := h_hash

      have h_empty_subtree : ref.subtree (1 - bit) = PatriciaTree.Empty height_m1 := by
        apply PatriciaTree.hash_inj (crypto:=crypto) (by omega)
        rw [←h_hash_other]
        rfl

      simp only [Nat.add_eq_zero_iff, one_ne_zero, and_false, false_imp_iff, not_false_eq_true,
        true_imp_iff, true_and] at ⊢
      rw [PatriciaTree.build_edge
        (PatriciaTree.build height_m1 values')
        bit
        (by
          intro index
          simp only [PatriciaTree.build_at, values']
          rw [TraverseResult.values.congr_res (show _ = res₁.updates by simp)]
          exact TraverseResult.values.subtree bit _)
        (by
          intro index
          rw [TraverseResult.values.congr_res (show _ = res₁.updates by simp)]
          have h_eq : index.1 + (1 - bit) * 2 ^ height_m1 + path * 2 ^ (height_m1 + 1) =
            index + (path * 2 + (1 - bit)) * 2 ^ height_m1 := by ring
          rw [TraverseResult.values.eq_ref_at h_traverse.updates.1
            (h_eq ▸ is_in_subtree.mk (path * 2 + (1 - bit)) index) (by omega)]
          simp only [add_tsub_cancel_right]

          apply congrArg (λ tree ↦ tree.at index) at h_empty_subtree
          rw [PatriciaTree.subtree_at _ _ index.isLt,
            show ↑(1 - bit: Fin 2) = 1 - (bit: ℕ) by omega] at h_empty_subtree
          rw [h_empty_subtree]
          rw [PatriciaTree.at_empty])
        (by rw [h_hash]; exact h_hash_ne_zero)
      ]

      cases length_m1
      case zero =>
        simp only [PatriciaTree.hash, NodeEdge.hash, ↓reduceIte] at h_hash
        have h := h_node_len0 (by simp)
        replace h : (PatriciaTree.build height_m1 values').node.valid_edge_bottom := h
        unfold PatriciaTree.hash
        rw [PatriciaTree.mk_edge.of_valid_edge_bottom bit h]
        simp only [show edge_path = bit by
          simpa only [is_in_subtree.height0] using h_in_subtree
        ]
        simp [PatriciaNode.node_hash, NodeEdge.hash, h_hash, h_length]

      case succ length_m2 =>
        have ⟨e, b, h, h_e_length, _⟩ := h_node_len_ne0 (by simp)
        replace h : (PatriciaTree.build height_m1 values').node = .Edge e b := h

        simp only [PatriciaTree.mk_edge, PatriciaNode.mk_edge, h, EdgePath.extend, EdgePath.length,
          PatriciaTree.hash, PatriciaNode.node_hash, NodeEdge.hash] at h_hash ⊢
        apply crypto.h_hash h_e_length (by omega) at h_hash
        constructor
        · simp [h_hash]
          rw [Nat.sub_add_cancel h_in_subtree.1]
        · exact ⟨e.extend bit, b, rfl, by simp; omega⟩
    case SingleEmptyLen1 res₁ h_traverse h_bottom_ne_zero h_bottom_binary =>
      rw [show path * 2 + 1 - ↑bit = path * 2 + (1 - bit: Fin 2) by omega] at h_traverse
      have ⟨h_weak_valid', h_hash_other⟩ := h_weak_valid.single (1 - bit) _
        (λ u h_u ↦ (h_traverse.updates.1 u h_u).1)
      have ⟨h_valid, h_empty_subtree⟩ := traverse_empty.root_eq h_weak_valid' h_traverse (by omega)
      use TraverseResult.valid.mk_edge (1 - bit) (by rw [h_hash_other]) h_valid

      let values' := λ x ↦ res₁.values (path * 2 + bit) (ref.subtree bit)
        (x + (path * 2 + bit) * 2 ^ height_m1)

      -- The bit-side build coincides with `ref.subtree bit` because res₁ has no updates there.
      have h_build_eq_subtree : PatriciaTree.build height_m1 values' = ref.subtree bit := by
        apply PatriciaTree.at.inj
        intro index
        rw [PatriciaTree.build_at]
        unfold values'
        rw [TraverseResult.values.eq_ref_at
          (λ u h_u ↦ (h_traverse.updates.1 u h_u).1)
          (is_in_subtree.mk (path * 2 + bit) index) (by omega)]
        simp [add_tsub_cancel_right]

      have h_subtree_hash : (ref.subtree bit).hash crypto = bottom := by
        rw [show ((1 - (1 - bit)) : Fin 2) = bit from by fin_cases bit <;> rfl] at h_hash_other
        exact h_hash_other.symm

      simp only [Nat.add_eq_zero_iff, one_ne_zero, and_false, false_imp_iff, not_false_eq_true,
        true_imp_iff, true_and] at ⊢
      rw [PatriciaTree.build_edge (crypto:=crypto)
        (PatriciaTree.build height_m1 values')
        bit
        (by
          intro index
          simp only [PatriciaTree.build_at, values']
          rw [TraverseResult.values.congr_res (show _ = res₁.updates by simp)]
          exact TraverseResult.values.subtree bit _)
        (by
          intro index
          rw [TraverseResult.values.congr_res (show _ = res₁.updates by simp)]
          rw [show (1 - ↑bit : ℕ) = ↑((1 - bit) : Fin 2) from by fin_cases bit <;> rfl]
          rw [TraverseResult.values.subtree (1 - bit) index]
          apply congrArg (λ tree ↦ tree.at index) at h_empty_subtree
          simp only [PatriciaTree.build_at] at h_empty_subtree
          rw [h_empty_subtree, PatriciaTree.at_empty])
        (by
          rw [h_build_eq_subtree, h_subtree_hash]
          exact h_bottom_ne_zero rfl)
      ]

      unfold PatriciaTree.hash
      unfold PatriciaTree.hash at h_subtree_hash

      cases height_m1
      case zero =>
        rw [PatriciaTree.mk_edge.of_valid_edge_bottom bit (by
          rw [h_build_eq_subtree]
          rcases PatriciaNode.valid_height0 (ref.subtree bit).valid with h | ⟨value, h⟩
          case inl h =>
            have := h_hash_other ▸ (h_bottom_ne_zero rfl)
            simp only [Fin.isValue, sub_sub_cancel, PatriciaTree.hash, h] at this
            contradiction
          case inr h => simp [h, PatriciaNode.valid_edge_bottom]
        )]
        simp [PatriciaNode.node_hash, NodeEdge.hash, h_build_eq_subtree, h_subtree_hash]
        omega

      case succ height_m2 =>
        have ⟨x, y, h_bottom_binary⟩ := h_bottom_binary (by simp) (by omega)
        have h_bottom_binary := (PatriciaTree.of_hash_binary x y (by omega) (h_bottom_binary ▸ h_subtree_hash)).1
        rw [PatriciaTree.mk_edge.of_valid_edge_bottom bit (by
          rw [h_build_eq_subtree, h_bottom_binary]
          rfl
        )]
        simp [PatriciaNode.node_hash, NodeEdge.hash, h_build_eq_subtree, h_subtree_hash]
        omega
    case SingleEmptyLenNe1 length_m2 res₁ h_traverse h_height_ne_one =>
      rw [show path * 2 + 1 - ↑bit = path * 2 + (1 - bit: Fin 2) by omega] at h_traverse
      have ⟨h_weak_valid', h_hash_other⟩ := h_weak_valid.single (1 - bit) _
        (λ u h_u ↦ (h_traverse.updates.1 u h_u).1)
      have ⟨h_valid, h_empty_subtree⟩ := traverse_empty.root_eq h_weak_valid' h_traverse (by omega)
      use TraverseResult.valid.mk_edge (1 - bit) (by rw [h_hash_other]) h_valid

      let values' := λ x ↦ res₁.values (path * 2 + bit) (ref.subtree bit)
        (x + (path * 2 + bit) * 2 ^ height_m1)

      -- The bit-side build coincides with `ref.subtree bit` because res₁ has no updates there.
      have h_build_eq_subtree : PatriciaTree.build height_m1 values' = ref.subtree bit := by
        apply PatriciaTree.at.inj
        intro index
        rw [PatriciaTree.build_at]
        unfold values'
        rw [TraverseResult.values.eq_ref_at
          (λ u h_u ↦ (h_traverse.updates.1 u h_u).1)
          (is_in_subtree.mk (path * 2 + bit) index) (by omega)]
        simp [add_tsub_cancel_right]

      have h_subtree_hash :
          (ref.subtree bit).hash crypto =
            (crypto.hash bottom (edge_path - bit * 2 ^ (length_m2 + 1))) + (length_m2 + 1) := by
        rw [show ((1 - (1 - bit)) : Fin 2) = bit from by fin_cases bit <;> rfl] at h_hash_other
        exact h_hash_other.symm

      simp only [Nat.add_eq_zero_iff, one_ne_zero, and_false, false_imp_iff, not_false_eq_true,
        true_imp_iff, true_and] at ⊢
      rw [PatriciaTree.build_edge (crypto:=crypto)
        (PatriciaTree.build height_m1 values')
        bit
        (by
          intro index
          simp only [PatriciaTree.build_at, values']
          rw [TraverseResult.values.congr_res (show _ = res₁.updates by simp)]
          exact TraverseResult.values.subtree bit _)
        (by
          intro index
          rw [TraverseResult.values.congr_res (show _ = res₁.updates by simp)]
          rw [show (1 - ↑bit : ℕ) = ↑((1 - bit) : Fin 2) from by fin_cases bit <;> rfl]
          rw [TraverseResult.values.subtree (1 - bit) index]
          apply congrArg (λ tree ↦ tree.at index) at h_empty_subtree
          simp only [PatriciaTree.build_at] at h_empty_subtree
          rw [h_empty_subtree, PatriciaTree.at_empty])
        (by
          rw [h_build_eq_subtree, h_subtree_hash]
          simp [crypto.hash_ne_zero'])
      ]

      cases height_m1
      case zero =>
        contradiction
      case succ height_m2 =>
        rw [←h_build_eq_subtree] at h_subtree_hash
        have ⟨b, h_path_lt, h_node_eq, _⟩ :=
          PatriciaTree.of_hash_edge _ length_m2 bottom (by omega) (by omega) h_subtree_hash
        let e : EdgePath := ⟨length_m2, ⟨edge_path - bit * 2 ^ (length_m2 + 1), h_path_lt⟩⟩

        replace h_node_eq : (PatriciaTree.build (height_m2 + 1) values').node = .Edge e b.node :=
          h_node_eq

        simp only [PatriciaTree.mk_edge, PatriciaNode.mk_edge, h_node_eq, EdgePath.extend,
          EdgePath.length, PatriciaTree.hash, PatriciaNode.node_hash, NodeEdge.hash] at h_subtree_hash ⊢
        apply crypto.h_hash (by simp only [e]; omega) (by omega) at h_subtree_hash

        constructor
        · simp [h_subtree_hash]
          rw [Nat.sub_add_cancel (by simpa using h_in_subtree.1)]
        · exact ⟨e.extend bit, b.node, rfl, by simp [EdgePath.length, e]; omega⟩

  case Descent n_steps_m1 height_m1 length_m1 edge_path bottom h_traverse_descent =>
    have ⟨descent_length_m2, descent_length, res₁, h_descent_length, h_descent_length_le,
      h_descent_length_le', word, new_edge, h_new_edge, h_in_subtree,
      h_traverse, h_res⟩ := traverse_edge_descend.implies h_traverse_descent
    letify h_descent_length
    simp only at h_new_edge
    letify h_new_edge

    simp only [Order.add_one_le_iff] at h_length
    simp only at h_descent_length_le

    have h_edge_path_lt : edge_path < 2 ^ (length_m1 + 1) := by
      have := h_in_subtree.2
      simp only at this
      apply lt_of_lt_of_le this
      apply le_of_le_of_eq
      apply Nat.mul_le_mul_right _ (Nat.succ_le_iff.2 word.isLt : (word: ℕ) + 1 ≤ 2 ^ descent_length)
      rw [←Nat.pow_add, ←Nat.add_sub_assoc h_descent_length_le]
      simp

    intro values' tree

    subst res
    have ⟨h_descent, h_empty⟩ := TraverseResult.weak_valid.descent
      (h_height:=by omega) (length_m2:=descent_length_m2) (word:=word)
      (h_length:=by omega)
      (λ u h ↦ (traverse_edge.updates h_traverse).1 u h)
      h_weak_valid

    have ⟨h_valid, h_hash, h_node_len0, h_node_len_ne0, h_hash_ne_zero⟩ :=
      traverse_edge.root_eq h_descent h_traverse (by omega) (by simp [new_edge]; omega)

    set height' := height_m1 + 1 - (descent_length_m2 + 2)
    set values'' : ℕ → ℕ := λ x ↦ TraverseResult.values
      (path * 2 ^ (descent_length_m2 + 2) + ↑word) res₁ (ref.descend word)
      (x + (path * 2 ^ (descent_length_m2 + 2) + ↑word) * 2 ^ height')
    set t := PatriciaTree.build height' values''

    have hash_implies {height': ℕ} (h_le: height' ≤ crypto.max_height) {t: PatriciaTree height'}
        (h_hash: t.hash crypto = new_edge.hash crypto)
        (h_node_len0: new_edge.length = 0 → t.node.valid_edge_bottom)
        (h_h: new_edge.length ≠ 0 → height' ≠ 0) :
        new_edge.length ≤ height' ∧
        ∃ bottom_tree: PatriciaTree (height' - new_edge.length),
          bottom_tree.node.valid_edge_bottom ∧
          (∀ index: ℕ, index < 2 ^ (height' - new_edge.length) →
            bottom_tree.at index = t.at (index + new_edge.path * 2 ^ (height' - new_edge.length))) ∧
          (∀ index: ℕ, index < 2 ^ height' →
            ¬is_in_subtree (height' - new_edge.length) new_edge.path index →
            t.at index = 0) ∧
          bottom_tree.hash crypto = bottom := by
      cases h₀: new_edge.length
      case zero =>
        simp only [new_edge] at h₀
        have h_edge_path_eq : edge_path = word := by
          simpa only [h₀, is_in_subtree.height0] using h_in_subtree
        refine ⟨(by simp), t, h_node_len0 h₀, ?_, ?_, ?_⟩
        · intro index
          simp [new_edge, h_edge_path_eq, h₀]
        · simp [new_edge, h_edge_path_eq, h₀]
          intro index h_in h_notin
          exact absurd (is_in_subtree.mk 0 ⟨_, h_in⟩) (by simp; exact h_notin)
        · simp [h_hash, new_edge, NodeEdge.hash, h₀]

      case succ len_m1 =>

      cases height'
      case zero => exact absurd (h_h (by omega)) (by simp)
      case succ h_m1 =>

      simp only [NodeEdge.hash] at h_hash
      rw [h₀] at h_hash
      have len_le : len_m1 + 1 ≤ crypto.max_height := by
        rw [←h₀]; simp only [new_edge]; omega
      have ⟨bottom_tree, _, h_node, h_hash_bottom⟩ :=
        PatriciaTree.of_hash_edge (crypto:=crypto) _ _ _ len_le h_le h_hash

      have ⟨h_le, _, h_valid_edge_bottom⟩ := PatriciaNode.valid_edge (h_node ▸ t.valid)
      use h_le
      simp only [add_le_add_iff_right] at h_le

      refine ⟨
        ⟨bottom_tree.node, by simp only [Nat.reduceSubDiff]; exact bottom_tree.valid⟩,
        h_valid_edge_bottom, ?_, ?_, ?_
      ⟩
      · intro index h_index
        have : (index: ℕ) < 2 ^ (h_m1 - len_m1) := by
          rw [show h_m1 - len_m1 = h_m1 + 1 - (len_m1 + 1) by omega]
          exact h_index
        conv_rhs => rw [PatriciaTree.at, h_node, PatriciaNode.at_edge _ (h_node ▸ t.valid),
          if_pos (by simp [EdgePath.length]; apply is_in_subtree.mk _ (i:=⟨index, this⟩))]
        simp [EdgePath.length, PatriciaTree.at]
      · intro index h_in h_notin
        rw [PatriciaTree.at, h_node, PatriciaNode.at_edge _ (h_node ▸ t.valid)]
        rw [if_neg h_notin]
      · unfold PatriciaTree.hash at h_hash_bottom ⊢
        rw [h_hash_bottom]

    have ⟨h_le, bottom_tree, h_valid_edge_bottom, h_bottom_at, h_t_at, h_bottom_hash⟩ :=
      hash_implies (by omega) h_hash h_node_len0 (by omega)

    have : length_m1 ≤ height_m1 := by
      simp only [tsub_le_iff_right, new_edge] at h_le
      rw [show height_m1 + 1 - (descent_length_m2 + 2) + descent_length = height_m1 + 1 by omega] at h_le
      simpa using h_le

    let edge_path_ : EdgePath := ⟨length_m1, ⟨edge_path, h_edge_path_lt⟩⟩

    let edge := PatriciaNode.Edge edge_path_ (tree.descend edge_path_.path).node

    have h_eq : height_m1 + 1 - (descent_length_m2 + 2) - new_edge.length =
        height_m1 + 1 - (length_m1 + 1) := by
      simp only [new_edge]; omega

    have h_dl_height : descent_length + (height_m1 + 1 - descent_length) = height_m1 + 1 := by omega

    have bottom_node_valid : bottom_tree.node.valid (height_m1 + 1 - (length_m1 + 1)) :=
      h_eq ▸ bottom_tree.valid

    have index_offset_lt {H L M i b : ℕ} (h_h: H = L + M) (h_i: i < 2 ^ M) (h_b: b < 2 ^ L) :
        i + b * 2 ^ M < 2 ^ H := by
      subst h_h
      calc i + b * 2 ^ M
        _ < (b + 1) * 2 ^ M := by rw [add_mul, one_mul]; omega
        _ ≤ 2 ^ L * 2 ^ M := Nat.mul_le_mul_right _ h_b
        _ = 2 ^ (L + M) := by rw [Nat.pow_add]

    have h_values'' (index: ℕ) (h_index: index < 2 ^ (height_m1 + 1 - descent_length)) :
        values'' index = values' (index + word * 2 ^ (height_m1 + 1 - descent_length)) := by
      simp only [values', values'']
      conv_rhs =>
        rw [TraverseResult.values.descent _ _ _ _ word (by
          have := is_in_subtree.mk (path * 2 ^ descent_length + word) ⟨index, h_index⟩
          convert this using 1
          simp only [add_mul, mul_assoc, ←Nat.pow_add]
          rw [h_dl_height]
          ring
        ) (by omega)]
        rw [TraverseResult.values.congr_res (show _ = res₁.updates by simp)]

      apply congrArg
      simp only [height']
      conv_lhs =>
        rw [add_mul, mul_assoc, ←Nat.pow_add, Nat.add_sub_cancel' (by omega), add_comm (path * _)]
      rw [add_assoc]

    have h_values''₂ (index: ℕ)
        (h_in_subtree: is_in_subtree (height_m1 + 1 - descent_length) word index) :
        values' index = values'' (index - word * 2 ^ (height_m1 + 1 - descent_length)) := by
      rw [h_values'' _ h_in_subtree.sub_offset_lt]
      rw [Nat.sub_add_cancel h_in_subtree.1]

    have tree_descend : (tree.descend edge_path_.path) = ⟨bottom_tree.node, bottom_node_valid⟩ := by
      apply PatriciaTree.at.inj
      intro index
      rw [PatriciaTree.descend_at _ index.isLt,
        PatriciaTree.build_at' _
          (index_offset_lt (by simp [edge_path_]; omega) index.isLt
            edge_path_.path.isLt)]
      simp only [PatriciaTree.at, h_eq] at h_bottom_at
      conv_rhs => simp only [PatriciaTree.at]
      rw [h_bottom_at index index.isLt,
        ←PatriciaTree.at,
        PatriciaTree.build_at' _
          (index_offset_lt (L := new_edge.length) (M := height_m1 + 1 - (length_m1 + 1))
            (by simp only [new_edge]; omega) index.isLt
            (by simpa [new_edge] using h_in_subtree.sub_offset_lt))]
      rw [h_values'' _
        (index_offset_lt (L := new_edge.length) (M := height_m1 + 1 - (length_m1 + 1))
          (by simp only [new_edge]; omega) index.isLt
          (by simpa [new_edge] using h_in_subtree.sub_offset_lt))]
      apply congrArg

      simp only [new_edge, edge_path_, Nat.sub_mul]
      rw [mul_assoc, ←Nat.pow_add]
      rw [show length_m1 + 1 - descent_length + (height_m1 + 1 - (length_m1 + 1)) =
        height_m1 + 1 - (descent_length_m2 + 2) by omega]
      have h_pow_factor : 2 ^ (height_m1 + 1 - (descent_length_m2 + 2)) =
          2 ^ (length_m1 + 1 - descent_length) * 2 ^ (height_m1 + 1 - (length_m1 + 1)) := by
        rw [←Nat.pow_add]; congr 1; omega
      have h_word_le_full :
          ↑word * 2 ^ (height_m1 + 1 - (descent_length_m2 + 2)) ≤
          edge_path * 2 ^ (height_m1 + 1 - (length_m1 + 1)) := by
        rw [h_pow_factor, ←mul_assoc]
        exact Nat.mul_le_mul_right _ h_in_subtree.1
      rw [←Nat.add_sub_assoc h_word_le_full]
      rw [Nat.sub_add_cancel (by omega)]

    have edge_valid : edge.valid (height_m1 + 1) := by
      simp only [PatriciaNode.valid, edge, decide_eq_true_eq, edge_path_, EdgePath.length]
      use (by omega)
      rw [tree_descend]
      refine ⟨bottom_node_valid, h_valid_edge_bottom⟩

    have h_tree_node : tree.node = edge := by
      apply PatriciaNode.at_inj tree.valid edge_valid
      intro index
      rw [←PatriciaTree.at]
      have ⟨word', h⟩ := is_in_subtree.height_add' descent_length h_descent_length_le' (is_in_subtree.mk path index)

      have index_ge : (index: ℕ) ≥ word' * 2 ^ (height_m1 + 1 - descent_length) := by
        have := h.1
        rw [ge_iff_le, ←Nat.sub_le_iff_le_add] at this
        apply le_of_eq_of_le _ this
        conv_rhs =>
          rw [add_mul, mul_assoc, ←Nat.pow_add]
          rw [h_dl_height]
        simp

      have index_lt : (index: ℕ) - word' * 2 ^ (height_m1 + 1 - descent_length) < 2 ^ (height_m1 + 1 - descent_length) := by
        have := h.2
        rw [←Nat.lt_sub_iff_add_lt] at this
        rw [Nat.sub_lt_iff_lt_add index_ge]
        apply lt_of_lt_of_eq this

        conv_lhs =>
          rw [add_mul, add_mul, mul_assoc, ←Nat.pow_add, h_dl_height]
        omega

      simp [tree, PatriciaTree.build_at]

      by_cases h_word'_eq : word = word'
      case pos =>
        subst word
        by_cases h' : is_in_subtree (height_m1 + 1 - edge_path_.length) ↑edge_path_.path ↑index
        case pos =>
          simp only [PatriciaTree.at, h_eq] at h_bottom_at

          rw [PatriciaNode.at_edge _ edge_valid, if_pos h', tree_descend]
          rw [h_bottom_at _ h'.sub_offset_lt]
          rw [←PatriciaTree.at]

          simp only [edge_path_, EdgePath.length]
          conv_rhs => enter [2]; rw [←Nat.sub_add_comm h'.1,
            ←Nat.sub_sub_right _ (Nat.mul_le_mul_right _
              (by simp only [new_edge]; exact Nat.sub_le _ _)),
            ←Nat.sub_mul]
          rw [show edge_path - new_edge.path = word' * 2 ^ (length_m1 + 1 - descent_length) by
            simp only [new_edge]
            have : ↑word' * 2 ^ (length_m1 + 1 - descent_length) ≤ edge_path :=
              h_in_subtree.1
            omega]
          rw [mul_assoc, ←Nat.pow_add]
          rw [show length_m1 + 1 - descent_length + (height_m1 + 1 - (length_m1 + 1))
            = height_m1 + 1 - (descent_length_m2 + 2) by omega]

          rw [h_values''₂ _ ⟨index_ge, by rw [add_mul, one_mul]; omega⟩]
          simp only [t]
          rw [PatriciaTree.build_at' _ index_lt]

        case neg =>
          rw [PatriciaNode.at_edge _ edge_valid, if_neg h']
          rw [h_values''₂ _ ⟨index_ge, by rw [add_mul, one_mul]; omega⟩]

          conv at h_t_at =>
            simp only [t]
            enter [index, h_in, h_notin]
            rw [PatriciaTree.build_at' _ h_in]

          apply h_t_at (h_in:=index_lt)
          simp only [edge_path_, EdgePath.length] at h'
          simp only [new_edge, h_eq]
          intro h''; apply h'

          have h_pow_factor : (2 : ℕ) ^ (height_m1 + 1 - descent_length) =
              2 ^ (length_m1 + 1 - descent_length) * 2 ^ (height_m1 + 1 - (length_m1 + 1)) := by
            rw [←Nat.pow_add]; congr 1; omega

          have h_word_mul_le : (word' : ℕ) * 2 ^ (height_m1 + 1 - descent_length) ≤
              edge_path * 2 ^ (height_m1 + 1 - (length_m1 + 1)) := by
            rw [h_pow_factor, ←mul_assoc]
            exact Nat.mul_le_mul_right _ h_in_subtree.1

          have ⟨h1, h2⟩ := h''
          rw [Nat.sub_mul, mul_assoc, ←h_pow_factor] at h1
          rw [add_mul, one_mul, Nat.sub_mul, mul_assoc, ←h_pow_factor] at h2
          exact ⟨by omega, by rw [add_mul, one_mul]; omega⟩

      case neg =>
        rw [PatriciaNode.at_edge _ edge_valid, if_neg (by
          intro h'
          simp only [edge_path_, EdgePath.length] at h'
          dsimp only at h_in_subtree
          apply h_word'_eq
          refine Fin.ext $ is_in_subtree.inj_path ?_ ⟨index_ge, by rw [add_mul, one_mul]; omega⟩
          refine is_in_subtree.trans (by omega) h' ?_
          convert h_in_subtree using 1
          omega
        )]

        unfold values'
        rw [TraverseResult.values.congr_res (show _ = res₁.updates by simp)]
        rw [TraverseResult.values.eq_ref_at
          (res := res₁)
          (λ u h ↦ (traverse_edge.updates h_traverse).1 u h)
          h
          (by omega)
        ]
        replace h_empty := h_empty word' h_word'_eq
        apply congrArg (λ tree ↦ tree.at (index - word' * 2 ^ (height_m1 + 1 - descent_length))) at h_empty
        rw [PatriciaTree.descend_at (tree:=ref) word' index_lt, PatriciaTree.at_empty] at h_empty
        rw [Nat.sub_add_cancel index_ge] at h_empty
        simp only [add_tsub_cancel_right]
        exact h_empty

    refine ⟨TraverseResult.valid.mk_descent descent_length_m2 word (by omega) rfl h_valid h_empty, ?_⟩
    refine ⟨?_, ?_, ?_, ?_⟩
    · rw [PatriciaTree.hash, h_tree_node, NodeEdge.hash, PatriciaNode.node_hash]
      rw [tree_descend]
      simp only [Nat.add_eq_zero_iff, one_ne_zero, and_false, ↓reduceIte]
      rw [←PatriciaTree.hash, h_bottom_hash]
    · intro; contradiction
    · intro
      rw [h_tree_node]
      use edge_path_, (tree.descend edge_path_.path).node, by rfl
      simp only [EdgePath.length, edge_path_]
      omega
    · simp [NodeEdge.hash]
end

-- See documentation at the top of the file.
-- The tree built is consistent with the `node` hash.
theorem traverse_node.root_eq {crypto: Crypto} {n_steps height path node: ℕ} {res: TraverseResult}
    {ref: PatriciaTree height}
    (h_valid: res.valid crypto path ref)
    (h: traverse_node crypto n_steps true height path node res)
    (h_height: height ≤ crypto.max_height) :
    let values := λ x ↦ res.values path ref (x + path * 2 ^ height)
    node = (PatriciaTree.build height values).hash crypto := by
  by_cases h_node: node = 0
  · simp only [traverse_node, h_node, reduceIte] at h
    have := (traverse_empty.root_eq (h_weak_valid:=h_valid.to_weak_valid) (h:=h) (h_height:=h_height)).2
    simp only at this ⊢
    rw [h_node, this]
    rfl
  · simp only [traverse_node, h_node, reduceIte] at h
    have ⟨_, h, _⟩ := traverse_non_empty.root_eq (h_valid:=h_valid.to_weak_valid) (h:=h) (h_height:=h_height)
    exact h
