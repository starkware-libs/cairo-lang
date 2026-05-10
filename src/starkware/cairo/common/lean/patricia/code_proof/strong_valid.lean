import patricia.code
import patricia.code_proof.updates
import patricia.code_proof.helpers
import patricia.traverse_result.strong_valid

-- The `traverse_*` functions imply `strong_valid` (see `traverse_result/strong_valid.lean`).

theorem traverse_empty.strong_valid {crypto: Crypto} {n_steps height path: ℕ} {res: TraverseResult}
    (h: traverse_empty n_steps height path res)
    (h_height: height ≤ crypto.max_height) :
    res.strong_valid crypto path (.Empty height) := by
  induction n_steps generalizing height path res
  case zero => contradiction
  case succ n_steps_m1 ih =>

  cases height
  case zero =>
    unfold traverse_empty at h
    subst res
    refine ⟨?_, ?_⟩
    · simp [TraverseResult.valid]
    · intro u h_u
      simp only [List.mem_singleton] at h_u
      simp [h_u, PatriciaTree.at_empty]
  case succ height_m1 =>
    simp only [traverse_empty, if_neg (show ↑(height_m1 + 1) ≠ (0: ℤ) by omega)] at h

    rcases h with
      ⟨res₀, res₁, h_traverse₀, h_traverse₁, h_res⟩ |
      ⟨res₀, child_bit, h_traverse, h_res⟩ |
      ⟨res₀, word, length_m2, h_length, h_word, h_traverse, h_res⟩

    · -- Both children.
      simp only [Nat.cast_add, Nat.cast_one, add_sub_cancel_right] at h_traverse₀ h_traverse₁
      have h_strong₀ := ih h_traverse₀ (h_height := by omega)
      have h_strong₁ := ih h_traverse₁ (h_height := by omega)
      refine ⟨?_, ?_⟩
      · apply TraverseResult.valid.mk_both (h_res:=h_res)
        · simp only [PatriciaTree.left_subtree, PatriciaTree.empty_subtree (dir:=0)]
          exact h_strong₀.1
        · simp only [PatriciaTree.right_subtree, PatriciaTree.empty_subtree (dir:=1)]
          exact h_strong₁.1
      · subst res
        intro u h_u
        simp only [List.mem_append] at h_u
        cases h_u
        case inl h_u => simp [←h_strong₀.2 u h_u, PatriciaTree.at_empty]
        case inr h_u => simp [←h_strong₁.2 u h_u, PatriciaTree.at_empty]
    · -- One child.
      simp only [Nat.cast_add, Nat.cast_one, add_sub_cancel_right] at h_traverse
      have h_strong := ih h_traverse (h_height := by omega)
      refine ⟨?_, ?_⟩
      · apply TraverseResult.valid.mk_edge (dir:=child_bit) (res₀:=res₀)
        · simp only [h_res, PatriciaTree.empty_subtree]
          rfl
        · simp only [PatriciaTree.empty_subtree]
          exact h_strong.1
      · subst res
        intro u h_u
        simp only [List.nil_append] at h_u
        simp [←h_strong.2 u h_u, PatriciaTree.at_empty]
    · -- Descend.
      have h_eq_nat : ((height_m1 + 1 : ℕ) - (length_m2 + 2 : ℕ) : ℤ) =
        (height_m1 + 1 - (length_m2 + 2) : ℕ) := by omega
      rw [h_eq_nat] at h_traverse
      have h_strong := ih h_traverse (h_height := by omega)
      refine TraverseResult.strong_valid.mk_descent length_m2 ⟨word, h_word⟩ (by omega) h_res ?_ ?_
      · simpa only [PatriciaTree.empty_descend] using h_strong
      · intro word' _
        exact PatriciaTree.empty_descend _ _

mutual
theorem traverse_non_empty.strong_valid {crypto: Crypto} {n_steps: ℕ} {is_new_tree: Bool}
    {height path node: ℕ} {res: TraverseResult}
    {ref: PatriciaTree height}
    (h_ref: ref.hash crypto = node)
    (h: traverse_non_empty crypto n_steps is_new_tree height path node res)
    (h_height: height ≤ crypto.max_height) :
    res.strong_valid crypto path ref := by
  cases n_steps
  case zero => unfold traverse_non_empty at h; contradiction

  unfold traverse_non_empty at h
  rcases h with
    ⟨edge, h_open_edge, h_traverse_edge⟩ | h
  · have ⟨h_length_ge, h_length_le, h_edge_path_le, h_node⟩ := h_open_edge
    refine traverse_edge.strong_valid ?_ h_traverse_edge h_height h_length_le
    simp only [h_ref, h_node, NodeEdge.hash, right_eq_ite_iff]
    intro h
    simp [h] at h_length_ge
  · exact traverse_binary_or_leaf.strong_valid h_ref (h:=h) h_height

theorem traverse_binary_or_leaf.strong_valid {crypto: Crypto} {n_steps: ℕ} {is_new_tree: Bool}
    {height path node: ℕ} {res: TraverseResult}
    {ref: PatriciaTree height}
    (h_ref: ref.hash crypto = node)
    (h: traverse_binary_or_leaf crypto n_steps is_new_tree height path node res)
    (h_height: height ≤ crypto.max_height) :
    res.strong_valid crypto path ref := by
  cases n_steps
  case zero => unfold traverse_binary_or_leaf at h; contradiction

  cases height
  case zero =>
    unfold traverse_binary_or_leaf at h
    have ⟨h_res, _⟩ := h
    subst res
    constructor
    · simp [TraverseResult.valid]
    · intro u h_u
      simp only [List.mem_singleton] at h_u
      subst u
      simp only [pow_zero, mul_one, Nat.sub_self]
      rw [←h_ref, PatriciaTree.hash_height0]
  case succ height_m1 =>
    unfold traverse_binary_or_leaf at h
    replace ⟨x, y, h_node, h⟩ := h
    rcases h with
      ⟨res₀, res₁, h_traverse₀, h_traverse₁, h_res⟩ |
      ⟨res₁, h_ne_zero, h_traverse, h_res⟩ |
      ⟨res₁, h_ne_zero, h_traverse, h_res⟩
    · -- Binary case.
      simp only [Nat.cast_add, Nat.cast_one, add_sub_cancel_right] at h_traverse₀ h_traverse₁
      simp only [h_node] at h_ref
      have ⟨h₀, h₁, h₂⟩ := PatriciaTree.of_hash_binary _ _ (by omega) h_ref

      exact TraverseResult.strong_valid.mk_binary h_res
        (traverse_non_empty.strong_valid h₁ h_traverse₀ (by omega))
        (traverse_non_empty.strong_valid h₂ h_traverse₁ (by omega))
    · -- Left case.
      simp only [Nat.cast_add, Nat.cast_one, add_sub_cancel_right] at h_traverse
      simp only [h_node] at h_ref
      have ⟨h₀, h₁, h₂⟩ := PatriciaTree.of_hash_binary _ _ (by omega) h_ref

      apply TraverseResult.strong_valid.mk_edge (dir:=0) (res₀:=res₁) (by subst res y; rfl)
      exact traverse_non_empty.strong_valid h₁ h_traverse (by omega)
    ·  -- Right case.
      simp only [Nat.cast_add, Nat.cast_one, add_sub_cancel_right] at h_traverse
      simp only [h_node] at h_ref
      have ⟨h₀, h₁, h₂⟩ := PatriciaTree.of_hash_binary _ _ (by omega) h_ref

      apply TraverseResult.strong_valid.mk_edge (dir:=1) (res₀:=res₁) (by subst res x; rfl)
      exact traverse_non_empty.strong_valid (ref:=ref.right_subtree) h₂ h_traverse (by omega)

theorem traverse_edge.strong_valid {crypto: Crypto} {n_steps: ℕ} {is_new_tree: Bool}
    {height path: ℕ} {edge: NodeEdge} {res: TraverseResult}
    {ref: PatriciaTree height}
    (h_ref: ref.hash crypto = edge.hash crypto)
    (h: traverse_edge crypto n_steps is_new_tree height path edge res)
    (h_height: height ≤ crypto.max_height)
    (h_length: edge.length ≤ crypto.max_height) :
    res.strong_valid crypto path ref := by
  cases h.view

  case BinaryOrLeaf n_steps_m1 edge_path bottom h' =>
    exact traverse_binary_or_leaf.strong_valid h_ref h' h_height

  case Regular n_steps_m1 height_m1 length_m1 edge_path bottom_hash bit h_in_subtree h' =>
    have ⟨bottom_tree, h_edge_path, h_ref_node, h_hash_bottom⟩ := PatriciaTree.of_hash_edge edge_path length_m1 bottom_hash
          (by omega) (by omega) h_ref
    let edge_path_: EdgePath := ⟨length_m1, ⟨edge_path, h_edge_path⟩⟩
    simp only [Order.add_one_le_iff] at h_length

    cases traverse_edge_regular.view h' (by simp) h_in_subtree

    case Both res₀ res₁ h'' =>
      have ⟨h_dir, h_other_dir⟩:
          (ref.subtree bit).hash crypto = NodeEdge.hash ⟨length_m1, edge_path - bit * 2 ^ length_m1, bottom_hash⟩ crypto ∧
          ref.subtree (1 - bit) = PatriciaTree.Empty _ := by
        rcases edge_path_.cases' bit h_in_subtree with h | ⟨edge_path', h⟩
        · have : length_m1 = 0 := congrArg EdgePath.length_m1 h
          subst length_m1
          simp only [show edge_path = bit by
            simpa only [is_in_subtree.height0] using h_in_subtree
          ] at *
          have ⟨h₀, h₁⟩ := PatriciaTree.of_edge_len1 ref bit bottom_tree h_ref_node
          rw [h₀, h₁]
          simp [NodeEdge.hash, h_hash_bottom]
        · have : length_m1 = edge_path'.length := congrArg EdgePath.length_m1 h

          simp [show edge_path = ↑edge_path'.path + bit * 2 ^ edge_path'.length by
            show edge_path_.path.1 = _; rw [h]
          ] at *

          subst length_m1
          have ⟨_, h₀, h₁⟩ := PatriciaTree.of_edge_extend ref edge_path' bit bottom_tree.node
            (by rw [h_ref_node])
          simp [h₀, h₁, NodeEdge.hash, ←h_hash_bottom, PatriciaTree.hash, PatriciaNode.node_hash]

      by_cases h_bit: bit = 0
      case pos =>
        subst bit
        simp only [reduceIte] at h''
        have ⟨h_traverse₀, h_traverse₁⟩ := h''

        apply TraverseResult.strong_valid.mk_binary (by rfl)
        · refine traverse_edge.strong_valid (ref:=ref.left_subtree) ?_ h_traverse₀ (h_height:=by omega)
            (h_length:=by simp only; omega)
          simp [PatriciaTree.left_subtree, h_dir, NodeEdge.hash]
        · simp only [sub_zero] at h_other_dir
          rw [PatriciaTree.right_subtree, h_other_dir]
          exact traverse_empty.strong_valid (crypto:=crypto) h_traverse₁ (by omega)
      case neg =>
        have : bit = 1 := by fin_cases bit <;> trivial
        subst bit
        simp only [Fin.isValue, one_ne_zero, ↓reduceIte,
          Fin.coe_ofNat_eq_mod, Nat.mod_succ, one_mul] at h''
        have ⟨h_traverse₀, h_traverse₁⟩ := h''

        apply TraverseResult.strong_valid.mk_binary (by rfl)
        · simp only [sub_self] at h_other_dir
          rw [PatriciaTree.left_subtree, h_other_dir]
          exact traverse_empty.strong_valid (crypto:=crypto) h_traverse₀ (by omega)
        · refine traverse_edge.strong_valid (ref:=ref.right_subtree) ?_ h_traverse₁ (h_height:=by omega)
            (h_length:=by simp only; omega)
          simp [PatriciaTree.right_subtree, h_dir, NodeEdge.hash]

    case SingleNonEmpty res₁ h_traverse =>
      have ⟨h_hash_dir, h_hash_other⟩ :
          (ref.subtree bit).hash crypto = NodeEdge.hash ⟨length_m1, edge_path - bit * 2 ^ length_m1, bottom_hash⟩ crypto ∧
          (ref.subtree (1 - bit)).hash crypto = 0 := by
        rcases edge_path_.cases' bit h_in_subtree with h | ⟨edge_path', h⟩
        · have : length_m1 = 0 := congrArg EdgePath.length_m1 h
          subst length_m1

          simp only [show edge_path = bit by
            simpa only [is_in_subtree.height0] using h_in_subtree
          ] at *
          have ⟨h₀, h₁⟩ := PatriciaTree.of_edge_len1 ref bit bottom_tree h_ref_node
          simp [h₀, h₁, NodeEdge.hash, h_hash_bottom]
          rfl
        · have : length_m1 = edge_path'.length := congrArg EdgePath.length_m1 h
          subst length_m1

          have h_edge_path_eq : edge_path = edge_path'.path + bit * 2 ^ edge_path'.length := by
            show edge_path_.path.1 = _
            rw [h]
          have ⟨_, h₀, h₁⟩ := PatriciaTree.of_edge_extend ref edge_path' bit bottom_tree.node (by
            rw [h_ref_node, ←h])
          simp [h₀, h₁, NodeEdge.hash, ←h_hash_bottom, PatriciaTree.hash, PatriciaNode.node_hash,
            h_edge_path_eq]
          rfl

      apply TraverseResult.strong_valid.mk_edge (dir:=bit) (by rw [h_hash_other])
      refine traverse_edge.strong_valid ?_ h_traverse (h_height:=by omega) (h_length:=Nat.le_of_lt h_length)
      rw [h_hash_dir, ←Int.toNat_sub]

    case SingleEmptyLen1 res₁ h_traverse _ _ =>
      have ⟨h₀, h₁⟩ := PatriciaTree.of_edge_len1 ref bit bottom_tree h_ref_node
      apply TraverseResult.strong_valid.mk_edge (dir:=1 - bit) (res₀:=res₁)
      case h_res => rw [←h_hash_bottom, ←h₀, sub_sub_cancel]
      case h_valid =>
        rw [h₁]
        rw [show ↑(1 - bit: Fin 2) = 1 - ↑bit by fin_cases bit <;> trivial, ←Nat.add_sub_assoc (by omega)]
        exact traverse_empty.strong_valid (crypto:=crypto) h_traverse (by omega)

    case SingleEmptyLenNe1 length_m2 res₁ h_traverse _ =>
      rcases edge_path_.cases' bit h_in_subtree with h | ⟨edge_path', h⟩
      · have : length_m2 + 1 = 0 := congrArg EdgePath.length_m1 h
        contradiction
      have h_edge_path'_length : edge_path'.length = length_m2 + 1 := (congrArg EdgePath.length_m1 h).symm

      replace h_ref_node : ref.node = .Edge (edge_path'.extend bit) bottom_tree.node := h ▸ h_ref_node
      have ⟨_, h₀, h₁⟩ := PatriciaTree.of_edge_extend ref edge_path' bit bottom_tree.node (by
        rw [h_ref_node, ←h])

      have h_edge_path_eq : edge_path - bit * 2 ^ (length_m2 + 1) = edge_path'.path := by
        show edge_path_.path.1 - _ = _
        rw [h]
        simp [h_edge_path'_length]

      apply TraverseResult.strong_valid.mk_edge (dir:=1 - bit) (res₀:=res₁)
      case h_res =>
        rw [sub_sub_cancel, h₀, ←h_hash_bottom]
        apply congrArg₂ _ (congrArg _ _) (by rfl)
        simp only [h_edge_path_eq]
        exact congrArg _ (by rw [h_edge_path'_length])
      case h_valid =>
        rw [h₁]
        rw [show ↑(1 - bit: Fin 2) = 1 - ↑bit by fin_cases bit <;> trivial, ←Nat.add_sub_assoc (by omega)]
        exact traverse_empty.strong_valid (crypto:=crypto) h_traverse (by omega)

  case Descent n_steps_m1 height_m1 length_m1 edge_path bottom h_traverse_descent =>
    have ⟨descent_length_m2, descent_length, res₁, h_descent_length, h_descent_length_le,
      h_descent_length_le', word, new_edge, h_new_edge, h_in_subtree,
      h_traverse, h_res⟩ := traverse_edge_descend.implies h_traverse_descent
    letify h_descent_length
    simp only at h_new_edge
    letify h_new_edge

    simp only [Order.add_one_le_iff] at h_length
    simp only at h_in_subtree h_descent_length_le

    simp only [NodeEdge.hash, Nat.add_eq_zero_iff, one_ne_zero, and_false, ↓reduceIte] at h_ref
    have ⟨bottom_tree, _, h_ref_node, h_hash_bottom⟩ :=
      PatriciaTree.of_hash_edge _ length_m1 _ (by omega) (by omega) h_ref

    have h_path_le : length_m1 + 1 ≤ height_m1 + 1 :=
      (PatriciaNode.valid_edge (h_ref_node ▸ ref.valid)).1

    apply TraverseResult.strong_valid.mk_descent descent_length_m2 word (by omega) h_res ?_ ?_
    · refine traverse_edge.strong_valid (ref:=ref.descend word) ?_ h_traverse (by omega)
        (by simp [new_edge]; omega)
      simp only [new_edge]
      rw [←h_hash_bottom]

      simp only [PatriciaTree.hash]

      by_cases h: descent_length = length_m1 + 1
      case pos =>
        have h_edge_path : edge_path = word := by
          simpa [←h, Nat.sub_self, is_in_subtree.height0] using h_in_subtree

        rw [PatriciaTree.descend_full (bottom_tree:=⟨bottom_tree.node, _⟩) h_ref_node]
        · simp [←h, NodeEdge.hash]
        · rw [←h_edge_path]
        · exact h
        · simp only [h, Nat.reduceSubDiff]
          exact bottom_tree.valid
      case neg =>
        have h_new_edge_path_lt : new_edge.path < 2 ^ (length_m1 - descent_length + 1) := by
          rw [show length_m1 - descent_length + 1 = length_m1 + 1 - descent_length from by omega]
          exact h_in_subtree.sub_offset_lt

        let new_edge_ : PatriciaNode :=
          .Edge ⟨length_m1 - descent_length, ⟨new_edge.path, h_new_edge_path_lt⟩⟩ bottom_tree.node

        suffices h: (ref.descend word).node = new_edge_ by
          unfold new_edge_ at h
          rw [h]
          simp only [PatriciaNode.node_hash, NodeEdge.hash]
          rw [if_neg (by omega), EdgePath.length]
          simp only [new_edge]
          rw [show length_m1 - descent_length + 1 = length_m1 + 1 - descent_length by omega]

        have h_new_edge_valid: new_edge_.valid (height_m1 + 1 - descent_length) := by
          unfold new_edge_ PatriciaNode.valid
          simp only
          split
          · omega
          · simp only [Order.add_one_le_iff, Bool.decide_and, Bool.decide_eq_true,
              Bool.and_eq_true, decide_eq_true_eq]
            have := PatriciaNode.valid_edge (h_ref_node ▸ ref.valid)
            refine ⟨by omega, ?_, this.2.2⟩
            convert this.2.1 using 2
            simp [EdgePath.length] at this ⊢
            omega

        apply PatriciaNode.at_inj (ref.descend word).valid h_new_edge_valid

        intro index
        conv_lhs =>
          rw [←PatriciaTree.at, PatriciaTree.descend_at _ index.isLt, PatriciaTree.at, h_ref_node]
          rw [PatriciaNode.at_edge _ (h_ref_node ▸ ref.valid)]
        rw [PatriciaNode.at_edge _ h_new_edge_valid]
        simp only [EdgePath.length]

        let d := descent_length_m2 + 1
        let n := new_edge.length
        let r := height_m1 - length_m1

        have h₀ : height_m1 = r + n + d := by simp only [r, n, d, new_edge]; omega
        have h₁ : descent_length = d + 1 := by omega
        have h₂ : length_m1 = d + n := by simp only [d, n, new_edge]; omega

        have : word * 2 ^ n ≤ edge_path := by
          have := h_in_subtree.1
          simpa only [h₂, h₁, Nat.reduceSubDiff, add_tsub_cancel_left, ge_iff_le] using this

        apply ite_congr
        · simp only [h₀, h₁, h₂, new_edge]
          unfold is_in_subtree
          rw [show r + n + d + 1 - (d + 1) = r + n by omega]
          rw [show r + n + d + 1 - (d + n + 1) = r by omega]
          rw [show r + n - (d + n - (d + 1) + 1) = r by omega]
          rw [show d + n + 1 - (d + 1) = n by omega]
          apply congrArg₂
          · conv_rhs => rw [Nat.sub_mul, mul_assoc, ←Nat.pow_add']
            simp only [ge_iff_le, tsub_le_iff_right]
          · rw [Nat.add_lt_iff_lt_sub_right]
            suffices h : (edge_path + 1) * 2 ^ r - ↑word * 2 ^ (r + n) =
                (edge_path - ↑word * 2 ^ n + 1) * 2 ^ r by rw [h]

            rw [Nat.pow_add' 2 r n, ←mul_assoc, ←Nat.sub_mul]
            apply congrArg₂ _ _ (by rfl)
            omega
        · intro
          convert rfl using 2
          · omega
          · simp only [h₀, h₁, h₂]
            simp only [Nat.reduceSubDiff, add_tsub_cancel_right, new_edge]
            rw [Nat.sub_mul, mul_assoc, ←Nat.pow_add]
            rw [show (r + n - (d + n - (d + 1) + 1)) = r by omega]
            rw [show r + n + d - (d + n) = r by omega]
            rw [add_comm r]
            rw [Nat.sub_sub_right _ (by rw [Nat.pow_add 2 n r, ←mul_assoc]; simp [this])]
        · intro; rfl

    · intro word' h_word_ne
      apply PatriciaTree.at.inj
      intro index
      simp only [PatriciaTree.descend_at _ index.isLt, PatriciaTree.at_empty]
      simp only [PatriciaTree.at, h_ref_node, PatriciaNode.at_edge _ (h_ref_node ▸ ref.valid)]
      rw [if_neg (by
        intro h_in_subtree'
        simp only [EdgePath.length] at h_in_subtree'
        refine h_word_ne (Fin.ext (is_in_subtree.inj_path ?_ (is_in_subtree.mk _ index)))
        refine is_in_subtree.trans (by omega) h_in_subtree' ?_
        convert h_in_subtree using 1
        omega
      )]
end

theorem traverse_node.strong_valid {crypto: Crypto} {n_steps: ℕ} {is_new_tree: Bool} {height path node: ℕ} {res: TraverseResult}
    {ref: PatriciaTree height}
    (h_ref: ref.hash crypto = node)
    (h: traverse_node crypto n_steps is_new_tree height path node res)
    (h_height: height ≤ crypto.max_height) :
    res.strong_valid crypto path ref := by
  by_cases h_node: node = 0
  case pos =>
    simp only [traverse_node, h_node, reduceIte] at h
    have h_strong_empty := traverse_empty.strong_valid h (by omega)
    have h_ref_empty : ref = .Empty height := by
      apply PatriciaTree.hash_inj (crypto:=crypto) (height_le_max:=by omega)
      rw [h_ref, h_node]
      rfl
    rw [h_ref_empty]
    exact h_strong_empty
  case neg =>
    simp only [traverse_node, h_node, reduceIte] at h
    apply traverse_non_empty.strong_valid (h_ref:=h_ref) (h:=h) (h_height:=h_height)


theorem traverse_prev_tree.strong_valid {crypto: Crypto} {n_steps height node: ℕ} {res: TraverseResult}
    {ref: PatriciaTree height}
    (h_ref: ref.hash crypto = node)
    (h: traverse_prev_tree crypto n_steps height node res) :
    res.strong_valid crypto 0 ref := by
  have ⟨h_height, h_traverse_node⟩ := h
  apply traverse_node.strong_valid (h_ref:=h_ref) (h:=h_traverse_node) (h_height:=h_height)
