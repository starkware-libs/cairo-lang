import patricia.code_proof.height_ge_zero
import patricia.code.traverse_non_empty
import patricia.is_in_subtree

-- A "view" of `traverse_edge` that exposes its three branches as named
-- constructors.
inductive TraverseEdgeView (crypto: Crypto) (is_new_tree: Bool)  (path: ℕ) (res: TraverseResult) :
    (n_steps: ℕ) → (height: ℕ) → (edge: NodeEdge) → Prop where
  | BinaryOrLeaf
      (n_steps_m1 height edge_path bottom: ℕ)
      (h_inner:
        traverse_binary_or_leaf crypto n_steps_m1 is_new_tree height path bottom res) :
      TraverseEdgeView crypto is_new_tree path res
        (n_steps_m1 + 1) height
        { length := 0, path := edge_path, bottom := bottom }
  | Regular
      (n_steps_m1 height_m1 length_m1 edge_path bottom: ℕ)
      (bit: Fin 2)
      (h_in_subtree: is_in_subtree length_m1 bit edge_path)
      (_h_inner:
        traverse_edge_regular crypto n_steps_m1 is_new_tree (height_m1 + 1) path
          { length := length_m1 + 1, path := edge_path, bottom := bottom } res
          bit
          { length := length_m1, path := edge_path - bit * 2 ^ length_m1, bottom := bottom }) :
      TraverseEdgeView crypto is_new_tree path res
        (n_steps_m1 + 1) (height_m1 + 1)
        { length := length_m1 + 1, path := edge_path, bottom := bottom }
  | Descent
      (n_steps_m1 height_m1 length_m1 edge_path bottom: ℕ)
      (_h_inner:
        traverse_edge_descend crypto n_steps_m1 is_new_tree (height_m1 + 1) path
          { length := length_m1 + 1, path := edge_path, bottom := bottom } res) :
      TraverseEdgeView crypto is_new_tree path res
        (n_steps_m1 + 1) (height_m1 + 1)
        { length := length_m1 + 1, path := edge_path, bottom := bottom }

theorem traverse_edge.view {crypto: Crypto} {n_steps height path: ℕ}
    {edge: NodeEdge} {res: TraverseResult}
    (h: traverse_edge crypto n_steps is_new_tree height path edge res) :
    TraverseEdgeView crypto is_new_tree path res n_steps height edge := by
  have h_height_zero_imp := (traverse_edge.height_ge_zero h).2

  unfold traverse_edge at h

  -- n_steps must be > 0.
  cases n_steps
  case zero => contradiction
  case succ n_steps_m1 =>

  -- Deconstruct edge.
  cases edge
  case mk edge_length edge_path edge_bottom =>

  dsimp only at h

  cases edge_length
  case zero =>
    rw [if_pos rfl] at h
    exact .BinaryOrLeaf n_steps_m1 height edge_path edge_bottom h
  case succ length_m1 =>
    -- height must be > 0.
    cases height
    case zero => simp at h_height_zero_imp
    case succ height_m1 =>

    rw [if_neg (Nat.succ_ne_zero _)] at h
    rcases h with ⟨bit, h_path_ge, h_path_lt, h_inner⟩ | h_descent
    · -- Show `is_in_subtree`.
      have h_in_subtree : is_in_subtree length_m1 bit edge_path := by
        constructor
        · simp at h_path_ge
          norm_cast at h_path_ge
        · rw [Int.sub_lt_iff] at h_path_lt
          norm_cast at h_path_lt
          rw [add_comm, add_mul, one_mul]
          exact h_path_lt

      -- Simplify ℤ casts.
      simp only [add_tsub_cancel_right] at h_inner
      rw [show (edge_path - (bit: ℤ) * 2 ^ length_m1 : ℤ).toNat = edge_path - bit * 2 ^ length_m1 from by
        have h_le : bit * 2 ^ length_m1 ≤ edge_path := by simpa using h_in_subtree.1
        norm_cast
      ] at h_inner

      exact .Regular n_steps_m1 height_m1 length_m1 edge_path edge_bottom bit
        h_in_subtree h_inner
    · exact .Descent n_steps_m1 height_m1 length_m1 edge_path edge_bottom h_descent

-- A "view" of `traverse_edge_regular`.
inductive TraverseEdgeRegularView
    (crypto: Crypto) (n_steps_m1: ℕ) (is_new_tree: Bool) (height_m1 path: ℕ)
    (new_edge: NodeEdge) (bit: Fin 2) :
    NodeEdge → TraverseResult → Prop where
  | Both
      {edge: NodeEdge}
      (res₀ res₁: TraverseResult)
      (_h_traverse:
        if bit = 0 then
          traverse_edge crypto n_steps_m1 is_new_tree height_m1 (path * 2) new_edge res₀ ∧
          traverse_empty n_steps_m1 height_m1 (path * 2 + 1) res₁
        else
          traverse_empty n_steps_m1 height_m1 (path * 2) res₀ ∧
          traverse_edge crypto n_steps_m1 is_new_tree height_m1 (path * 2 + 1) new_edge res₁) :
      TraverseEdgeRegularView crypto n_steps_m1 is_new_tree height_m1 path new_edge bit
        edge (res₀.add res₁)
  | SingleNonEmpty
      {edge: NodeEdge}
      (res₁: TraverseResult)
      (_h_traverse:
        traverse_edge crypto n_steps_m1 is_new_tree height_m1 (path * 2 + bit) new_edge res₁) :
      TraverseEdgeRegularView crypto n_steps_m1 is_new_tree height_m1 path new_edge bit
        edge ((TraverseResult.sibling 0).add res₁)
  | SingleEmptyLen1
      (bottom: ℕ)
      (res₁: TraverseResult)
      (_h_traverse_empty:
        traverse_empty n_steps_m1 height_m1 (path * 2 + 1 - bit) res₁)
      (h_bottom_ne_zero: is_new_tree → bottom ≠ 0)
      (h_bottom_binary: is_new_tree → height_m1 ≠ 0 → ∃ x y, bottom = crypto.hash x y) :
      TraverseEdgeRegularView crypto n_steps_m1 is_new_tree height_m1 path new_edge bit
        { length := 1, path := bit, bottom := bottom }
        ((TraverseResult.sibling bottom).add res₁)
  | SingleEmptyLenNe1
      (length_m2 edge_path bottom: ℕ)
      (res₁: TraverseResult)
      (_h_traverse_empty:
        traverse_empty n_steps_m1 height_m1 (path * 2 + 1 - bit) res₁)
      (h_height_ne_one: height_m1 ≠ 0) :
      TraverseEdgeRegularView crypto n_steps_m1 is_new_tree height_m1 path new_edge bit
        { length := length_m2 + 2, path := edge_path, bottom := bottom }
        ((TraverseResult.sibling
            (crypto.hash bottom new_edge.path + new_edge.length)).add res₁)

theorem traverse_edge_regular.view {crypto: Crypto} {n_steps_m1: ℕ} {is_new_tree: Bool} {height_m1 path: ℕ}
    {edge new_edge: NodeEdge} {res: TraverseResult} {bit: Fin 2}
    (h: traverse_edge_regular crypto n_steps_m1 is_new_tree (height_m1 + 1) path edge res bit new_edge)
    (h_edge_ne_zero: edge.length ≠ 0)
    (h_in_subtree: is_in_subtree (edge.length - 1) bit edge.path) :
    TraverseEdgeRegularView crypto n_steps_m1 is_new_tree height_m1 path new_edge bit edge res := by
  unfold traverse_edge_regular at h
  rcases h with
    ⟨res₀, res₁, h_traverse, h_res⟩ |
    ⟨res₁, h_traverse, h_res⟩ |
    ⟨res₁, h_edge_length_one, h_traverse_empty, h_res⟩
  · subst h_res
    exact .Both res₀ res₁ (by simpa using h_traverse)
  · subst h_res
    exact .SingleNonEmpty res₁ (by simpa using h_traverse)
  · cases edge
    case mk edge_length edge_path bottom =>

    match h: edge_length with
    | 0 => contradiction
    | 1 =>
      simp only [↓reduceIte] at h_res
      let res₀ := TraverseResult.sibling bottom
      have ⟨h_bottom_ne_zero, h_res⟩ :
          (is_new_tree → bottom ≠ 0) ∧
          res = res₀.add res₁ := by
        cases height_m1
        case zero =>
          rw [if_neg (by simp)] at h_res
          exact ⟨λ _ ↦ h_res.1, h_res.2⟩
        case succ height_m2 =>
          rw [if_pos (by omega)] at h_res
          refine ⟨?_, h_res.2⟩
          intro h_new_tree
          have ⟨x, y, h⟩ := h_res.1 h_new_tree
          rw [h]
          apply crypto.hash_ne_zero'

      subst h_res
      simp only [show edge_path = bit by
        simpa only [Nat.sub_self, is_in_subtree.height0] using h_in_subtree
      ]
      exact TraverseEdgeRegularView.SingleEmptyLen1 (new_edge:=new_edge) bottom res₁
        (by simpa using h_traverse_empty)
        h_bottom_ne_zero
        (by
          intro h_new_tree h_height
          simp [h_new_tree, h_height] at h_res
          exact h_res.1
        )
    | length_m2 + 2 =>
      rw [if_neg (by omega : (length_m2 + 1 + 1 : ℕ) ≠ 1)] at h_res
      subst h_res

      exact TraverseEdgeRegularView.SingleEmptyLenNe1 length_m2 edge_path bottom res₁
        (by simpa using h_traverse_empty)
        (by intro h_height; simp [h_height] at h_edge_length_one)

-- Structured form of `traverse_edge_descend`:
-- Extracts
-- (1) `descent_length` (≥ 2 and bounded by both `edge.length` and `height_m1 + 1`),
-- (2) the descended `word` (with `is_in_subtree` evidence),
-- (3) the shorter (and lower) `new_edge`, and
-- (4) an inner `traverse_edge`.
theorem traverse_edge_descend.implies {crypto: Crypto} {n_steps_m1: ℕ} {is_new_tree: Bool}
    {height_m1 path: ℕ} {edge: NodeEdge} {res: TraverseResult}
    (h_traverse: traverse_edge_descend crypto n_steps_m1 is_new_tree (height_m1 + 1) path edge res) :
    ∃ (descent_length_m2 descent_length: ℕ) (res₁: TraverseResult),
    (descent_length = descent_length_m2 + 2) ∧
    (descent_length ≤ edge.length) ∧
    (descent_length ≤ height_m1 + 1) ∧
    ∃ (word: Fin (2 ^ descent_length)) (new_edge: NodeEdge),
    let new_length := edge.length - descent_length
    let new_path := edge.path - word * 2 ^ new_length
    (new_edge = { length := new_length, path := new_path, bottom := edge.bottom }) ∧
    is_in_subtree new_length word edge.path ∧
    traverse_edge crypto n_steps_m1 is_new_tree ↑(height_m1 + 1 - descent_length) (path * 2 ^ descent_length + word) new_edge res₁ ∧
    res = (TraverseResult.descent (descent_length_m2 + 2)).add res₁ := by
  unfold traverse_edge_descend at h_traverse
  have ⟨descent_length, word, res₁, descent_length_ge, descent_length_le, word_lt,
    new_path_ge, new_path_lt, h_traverse, h_res⟩ := h_traverse
  have descent_length_le' : descent_length ≤ height_m1 + 1 := by
    have := (traverse_edge.height_ge_zero h_traverse).1
    omega

  have h_word_le : word * 2 ^ (edge.length - descent_length) ≤ edge.path := by linarith

  rw [
    show ((height_m1: ℤ)  + 1 - ↑descent_length) = (height_m1 + 1 - descent_length : ℕ) by
      omega,
    show (edge.path : ℤ) - ↑word * 2 ^ (edge.length - descent_length) =
        ((edge.path - word * 2 ^ (edge.length - descent_length) : ℕ) : ℤ) by
      rw [Nat.cast_sub h_word_le]; push_cast; ring,
    Int.toNat_natCast,
  ] at h_traverse

  have h_in_subtree : is_in_subtree (edge.length - descent_length) word edge.path := by
    unfold is_in_subtree
    refine ⟨h_word_le, ?_⟩
    have h_lt : (edge.path : ℤ) < (↑word + 1) * 2 ^ (edge.length - descent_length) := by linarith
    exact_mod_cast h_lt

  refine
    ⟨(descent_length - 2), descent_length, res₁, by omega, descent_length_le, descent_length_le',
    ⟨word, word_lt⟩, _, rfl, h_in_subtree, h_traverse, by rwa [Nat.sub_add_cancel (by omega)]⟩
