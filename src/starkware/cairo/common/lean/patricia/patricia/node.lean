import patricia.crypto
import patricia.patricia.edge_path

inductive PatriciaNode where
  | Empty
  | Leaf (value: ℕ)
  | Binary (left: PatriciaNode) (right: PatriciaNode)
  | Edge (path: EdgePath) (bottom: PatriciaNode)
deriving Repr, DecidableEq

-- Returns True if the node can be at the bottom of an edge.
def PatriciaNode.valid_edge_bottom (node: PatriciaNode) : Bool := match node with
  | .Leaf _ => True
  | .Binary _ _ => True
  | .Empty => False
  | .Edge _ _ => False

def PatriciaNode.valid (node: PatriciaNode) (height: ℕ) : Bool :=
  match height with
  | 0 => match node with
    | .Empty => True
    | .Leaf value => value ≠ 0
    | _ => False
  | height' + 1 => match node with
    | .Empty => True
    | .Leaf _ => False
    | .Binary left right =>
      PatriciaNode.valid left height' ∧
      PatriciaNode.valid right height' ∧
      left ≠ .Empty ∧
      right ≠ .Empty
    | .Edge path bottom =>
      path.length ≤ height ∧
      PatriciaNode.valid bottom (height - path.length) ∧
      bottom.valid_edge_bottom

-- A valid node at height 0 is either Empty or a non-zero Leaf.
theorem PatriciaNode.valid_height0 {node: PatriciaNode} (h: node.valid 0) :
      node = .Empty ∨ (∃ value, node = .Leaf value ∧ value ≠ 0) := by
    unfold PatriciaNode.valid at h
    cases node <;> try contradiction
    case Empty => simp
    case Leaf value =>
      simp only [ne_eq, decide_not, Bool.not_eq_eq_eq_not, Bool.not_true,
        decide_eq_false_iff_not] at h
      apply Or.inr ⟨value, rfl, h⟩

theorem PatriciaNode.valid_leaf {value: ℕ} {height: ℕ}
    (h: (PatriciaNode.Leaf value).valid height) :
      height = 0 ∧ value ≠ 0 := by
    unfold PatriciaNode.valid at h
    cases height
    case zero =>
      simp only [decide_eq_true_eq] at h
      simp [h]
    case succ height' => contradiction

theorem PatriciaNode.valid_binary {left: PatriciaNode} {right: PatriciaNode} {height: ℕ}
    (h: (PatriciaNode.Binary left right).valid height) :
      ∃ height_m1, height = height_m1 + 1 ∧
      left.valid height_m1 ∧
      right.valid height_m1 ∧
      left ≠ .Empty ∧
      right ≠ .Empty := by
    unfold PatriciaNode.valid at h
    cases height
    case zero => contradiction
    case succ height' =>
      simp only [decide_eq_true_eq] at h
      use height'

theorem PatriciaNode.valid_binary' {left: PatriciaNode} {right: PatriciaNode} {height_m1: ℕ}
    (h: (PatriciaNode.Binary left right).valid (height_m1 + 1)) :
      left.valid height_m1 ∧ right.valid height_m1 ∧ left ≠ .Empty ∧ right ≠ .Empty := by
    unfold PatriciaNode.valid at h
    simp only [decide_eq_true_eq] at h
    exact h

theorem PatriciaNode.valid_edge {path: EdgePath} {bottom: PatriciaNode} {height: ℕ}
    (h: (PatriciaNode.Edge path bottom).valid height) :
      path.length ≤ height ∧
      bottom.valid (height - path.length) ∧
      bottom.valid_edge_bottom := by
    unfold PatriciaNode.valid at h
    cases height
    case zero => contradiction
    case succ height' =>
      simp only [Bool.decide_and, Bool.decide_eq_true, Bool.and_eq_true] at h
      simp only [decide_eq_true_eq] at h
      exact h

theorem PatriciaNode.valid_edge_extend {path: EdgePath} {bottom: PatriciaNode} {height_m1: ℕ} {dir: Fin 2} :
    (PatriciaNode.Edge (path.extend dir) bottom).valid (height_m1 + 1) ↔
    (PatriciaNode.Edge path bottom).valid height_m1 := by
  unfold PatriciaNode.valid
  cases height_m1 <;> simp [EdgePath.length]

-- For a valid Edge at height `height_m1 + 1`, its path either:
-- (1) is a length-1 path `mk_len1 dir` with (valid) `bottom` at `height_m1`, or
-- (2) extends a shorter `path'` whose Edge is valid at `height_m1`.
theorem PatriciaNode.valid_edge_cases {path: EdgePath} {bottom: PatriciaNode} {height_m1: ℕ}
    (h: (PatriciaNode.Edge path bottom).valid (height_m1 + 1)) :
      ∃ dir: Fin 2, (
        (
          path = EdgePath.mk_len1 dir ∧
          bottom.valid height_m1 ∧
          bottom.valid_edge_bottom
        ) ∨ (∃ path': EdgePath,
          path = path'.extend dir ∧
          (PatriciaNode.Edge path' bottom).valid height_m1 ∧
          bottom.valid_edge_bottom
        )
      ) := by
    obtain ⟨dir, h'⟩ := path.cases
    use dir
    cases h'
    case inl h' =>
      apply Or.inl
      use h'
      have := h' ▸ (PatriciaNode.valid_edge h).2
      exact this
    case inr h' =>
      apply Or.inr
      obtain ⟨path', h'⟩ := h'
      use path', h'
      have := h' ▸ (PatriciaNode.valid_edge h)
      refine ⟨?_, this.2.2⟩
      unfold PatriciaNode.valid
      cases height_m1
      case zero => simp [EdgePath.length] at this
      case succ height_m2 =>
        simp only [decide_eq_true_eq]
        simp only [EdgePath.extend] at this
        constructor
        · have := this.1
          rw [add_le_add_iff_right] at this
          exact this
        · simp [EdgePath.length] at this ⊢
          exact this.2

def PatriciaNode.at (height: ℕ) (node: PatriciaNode) (index: ℕ) : ℕ :=
  match height with
  | 0 => match node with
    | .Leaf value => value
    | _ => 0
  | height_m1 + 1 => match node with
    | .Empty => 0
    | .Leaf value => value
    | .Binary left right =>
      if index < 2 ^ height_m1 then
        left.at height_m1 index
      else
        right.at height_m1 (index - 2 ^ height_m1)
    | .Edge path bottom =>
      let chunk := 2 ^ (height_m1 - path.length_m1)
      if is_in_subtree (height_m1 - path.length_m1) path.path index then
        bottom.at (height_m1 - path.length_m1) (index - path.path * chunk)
      else
        0
termination_by height

theorem PatriciaNode.at_empty (height: ℕ) (index: ℕ) :
    PatriciaNode.Empty.at height index = 0 := by
  simp only [PatriciaNode.at.eq_def]
  split <;> simp

theorem PatriciaNode.at_leaf (height: ℕ) (index: ℕ) (value: ℕ) :
    (PatriciaNode.Leaf value).at height index = value := by
  simp only [PatriciaNode.at.eq_def]
  split <;> simp

theorem PatriciaNode.at_binary
    {height: ℕ} {left: PatriciaNode} {right: PatriciaNode} (index: ℕ)
    (h_valid: (PatriciaNode.Binary left right).valid height) :
    (PatriciaNode.Binary left right).at height index =
    if index < 2 ^ (height - 1) then
      left.at (height - 1) index
    else
      right.at (height - 1) (index - 2 ^ (height - 1)) := by
  conv => lhs; unfold PatriciaNode.at
  cases height
  case zero =>
    have ⟨_, h, _, _, _, _⟩ := PatriciaNode.valid_binary h_valid
    simp at h
  case succ height_m1 =>
    simp only [add_tsub_cancel_right]

theorem PatriciaNode.at_edge
    {height: ℕ} {path: EdgePath} {bottom: PatriciaNode} (index: ℕ)
    (h_valid: (PatriciaNode.Edge path bottom).valid height) :
    (PatriciaNode.Edge path bottom).at height index =
    let chunk := 2 ^ (height - path.length)
    if is_in_subtree (height - path.length) path.path index then
      bottom.at (height - path.length) (index - path.path * chunk)
    else
      0 := by
  conv => lhs; unfold PatriciaNode.at
  cases height
  case zero =>
    have ⟨h, _⟩ := PatriciaNode.valid_edge h_valid
    simp [EdgePath.length] at h
  case succ height_m1 =>
    simp only
    have : height_m1 + 1 - path.length = height_m1 - path.length_m1 := by simp [EdgePath.length]
    simp only [this]

-- Extending an edge with `0` (left):
-- (1) On indices in the left half, `at` agrees with the un-extended Edge at `height_m1`.
-- (2) On the right half, it returns `0`.
theorem PatriciaNode.at_left_extend
    {height_m1: ℕ} {path: EdgePath} {bottom: PatriciaNode} (index: ℕ)
    (h_valid: (PatriciaNode.Edge path bottom).valid height_m1) :
    (PatriciaNode.Edge (path.extend 0) bottom).at (height_m1 + 1) index =
    if index < 2 ^ height_m1 then
      (PatriciaNode.Edge path bottom).at height_m1 index
    else
      0 := by
  conv => lhs; unfold PatriciaNode.at
  simp only
  by_cases h: index < 2 ^ height_m1
  case pos =>
    simp only [h, reduceIte]
    conv => rhs; unfold PatriciaNode.at
    cases height_m1
    case zero =>
      have := (valid_edge h_valid).1
      contradiction
    case succ height_m2 =>
      simp only
      apply ite_congr
      · simp [EdgePath.length]
      · intro h'
        simp [EdgePath.length]
      · intro h'; rfl
  case neg =>
    simp only [Fin.isValue, Fin.coe_ofNat_eq_mod, Nat.zero_mod, zero_mul, add_zero, h, ↓reduceIte,
      ite_eq_right_iff]
    intro ⟨h', h''⟩
    exfalso
    apply h
    calc index
      _ < (path.path + 1) * 2 ^ (height_m1 - path.length) := h''
      _ ≤ 2 ^ (path.length_m1 + 1) * 2 ^ (height_m1 - path.length) := Nat.mul_le_mul_right _ (by omega)
      _ = 2 ^ (path.length + (height_m1 - path.length)) := by rw [←Nat.pow_add]
      _ = 2 ^ height_m1 := by rw [Nat.add_sub_cancel' (valid_edge h_valid).1]

-- Extending an edge with `1` (right):
-- (1) On indices in the right half, `at` agrees with the un-extended Edge at `height_m1`.
-- (2) On the left half, it returns `0`.
theorem PatriciaNode.at_right_extend
    {height_m1: ℕ} {path: EdgePath} {bottom: PatriciaNode} (index: ℕ)
    (h_valid: (PatriciaNode.Edge path bottom).valid height_m1) :
    (PatriciaNode.Edge (path.extend 1) bottom).at (height_m1 + 1) index =
    if index < 2 ^ height_m1 then
      0
    else
      (PatriciaNode.Edge path bottom).at height_m1 (index - 2 ^ height_m1)
    := by
  conv => lhs; unfold PatriciaNode.at
  simp only
  by_cases h: index < 2 ^ height_m1
  case neg =>
    simp only [h, reduceIte]
    conv => rhs; unfold PatriciaNode.at
    cases height_m1
    case zero =>
      have := (valid_edge h_valid).1
      contradiction
    case succ height_m2 =>
      simp only
      have : path.length_m1 + 1 + (height_m2 - path.length_m1) = height_m2 + 1 := by
        rw [add_assoc, add_comm 1 _, ←add_assoc, Nat.add_sub_cancel' _]
        have := (valid_edge h_valid).1
        simp [EdgePath.length] at this
        exact this
      apply ite_congr
      · simp only [eq_iff_iff]
        apply and_congr
        · simp [add_mul, ←Nat.pow_add, EdgePath.length, this]
          rw [Nat.le_sub_iff_add_le (Nat.not_lt.1 h)]
        · simp [add_mul, ←Nat.pow_add, EdgePath.length, this]
          rw [Nat.sub_lt_iff_lt_add (Nat.not_lt.1 h)]
          ring_nf
      · intro h'
        simp [add_mul, ←Nat.pow_add, EdgePath.length, this]
        rw [Nat.sub_sub]
        ring_nf
      · intro h'; rfl
  case pos =>
    simp only [Fin.isValue, Fin.coe_ofNat_eq_mod, Nat.mod_succ, one_mul, h, ↓reduceIte,
      ite_eq_right_iff]
    intro ⟨h', h''⟩
    exfalso
    apply Nat.not_le.2 h
    calc index
      _ ≥ (path.path + 2 ^ path.length) * 2 ^ (height_m1 - path.length) := h'
      _ ≥ 2 ^ path.length * 2 ^ (height_m1 - path.length) := Nat.mul_le_mul_right _ (by omega)
      _ = 2 ^ (path.length + (height_m1 - path.length)) := by rw [←Nat.pow_add]
      _ = 2 ^ height_m1 := by rw [Nat.add_sub_cancel' (valid_edge h_valid).1]


--------------------------
-- PatriciaNode.mk_edge --
--------------------------

def PatriciaNode.mk_edge (node: PatriciaNode) (dir: Fin 2) : PatriciaNode :=
  match node with
    | .Edge path bottom => .Edge (path.extend dir) bottom
    | _ => .Edge (.mk_len1 dir) node

theorem PatriciaNode.mk_edge_non_empty {node: PatriciaNode} (dir: Fin 2) :
    node.mk_edge dir ≠ .Empty := by
  unfold PatriciaNode.mk_edge; split <;> simp

theorem PatriciaNode.mk_edge_non_leaf {node: PatriciaNode} (dir: Fin 2) :
    ∀ value, node.mk_edge dir ≠ .Leaf value := by
  unfold PatriciaNode.mk_edge; split <;> simp

theorem PatriciaNode.mk_edge_non_binary {node: PatriciaNode} (dir: Fin 2) :
    ∀ left right, node.mk_edge dir ≠ .Binary left right := by
  unfold PatriciaNode.mk_edge; split <;> simp

-- `mk_edge` either extends the path of an existing Edge, or wraps the node in a fresh length-1 Edge.
theorem PatriciaNode.mk_edge_cases (node: PatriciaNode) (dir: Fin 2) :
    (∃ path bottom, node = .Edge path bottom ∧ node.mk_edge dir = .Edge (path.extend dir) bottom) ∨
    (node.mk_edge dir = .Edge (.mk_len1 dir) node) := by
  unfold PatriciaNode.mk_edge; split <;> simp

theorem PatriciaNode.mk_edge_valid {node: PatriciaNode} (dir: Fin 2)
    (h: node.valid height) (h_ne_empty: node ≠ .Empty) :
    (node.mk_edge dir).valid (height + 1) := by
  unfold PatriciaNode.mk_edge PatriciaNode.valid
  cases node <;> try simpa [PatriciaNode.valid_edge_bottom]
  case Empty => contradiction
  case Edge path bottom =>
    unfold EdgePath.extend EdgePath.length
    unfold PatriciaNode.valid at h
    simp only [decide_eq_true_eq] at h ⊢
    cases height
    case zero => contradiction
    case succ height_m1 =>
      have : height_m1 + 1 - path.length = height_m1- path.length_m1 := by simp [EdgePath.length]
      simp only [decide_eq_true_eq, this] at h
      simp [h]

------------------------
-- PatriciaNode.merge --
------------------------

def PatriciaNode.merge (left right: PatriciaNode) : PatriciaNode :=
    match (left, right) with
    | (.Empty, .Empty) => .Empty
    | (.Empty, _) => right.mk_edge 1
    | (_, .Empty) => left.mk_edge 0
    | (_, _) => .Binary left right

theorem PatriciaNode.merge_valid {left right: PatriciaNode} {height_m1: ℕ}
    (left_valid: left.valid height_m1) (right_valid: right.valid height_m1) :
    (merge left right).valid (height_m1 + 1) := by
  unfold PatriciaNode.merge
  split
  all_goals simp only [imp_false, Prod.mk.injEq] at *
  · rfl
  · exact PatriciaNode.mk_edge_valid 1 right_valid (by simp [*])
  · exact PatriciaNode.mk_edge_valid 0 left_valid (by simp [*])
  · rename_i left_ne_empty right_ne_empty heq
    simp only [←heq] at left_ne_empty right_ne_empty
    simp [PatriciaNode.valid, left_valid, right_valid, left_ne_empty, right_ne_empty]

theorem PatriciaNode.merge_is_empty {left right: PatriciaNode}
    (h: (merge left right) = .Empty) :
    left = .Empty ∧ right = .Empty := by
  unfold PatriciaNode.merge at h
  split at h
  all_goals simp only [imp_false, Prod.mk.injEq] at *
  · assumption
  · simp [PatriciaNode.mk_edge_non_empty] at h
  · simp [PatriciaNode.mk_edge_non_empty] at h
  · contradiction

theorem PatriciaNode.merge_is_binary {left right left' right': PatriciaNode}
    (h: (merge left right) = .Binary left' right') :
    left = left' ∧ right = right' ∧ left ≠ .Empty ∧ right ≠ .Empty := by
  unfold PatriciaNode.merge at h
  split at h <;> try simp [PatriciaNode.mk_edge_non_binary] at h
  simp only [imp_false, Prod.mk.injEq] at *
  use h.1, h.2
  rename_i left_not_empty right_not_empty heq
  simp [left_not_empty, right_not_empty, heq]

theorem PatriciaNode.merge_binary {left right: PatriciaNode}
    (left_ne_empty: left ≠ .Empty) (right_ne_empty: right ≠ .Empty) :
    (merge left right) = .Binary left right := by
  unfold PatriciaNode.merge
  split <;> try
    simp only [imp_false, Prod.mk.injEq] at *
    rename_i heq
    simp [heq] at left_ne_empty right_ne_empty
  rfl

theorem PatriciaNode.merge_non_leaf {left right: PatriciaNode} {value: ℕ} :
    ¬((merge left right) = .Leaf value) := by
  unfold PatriciaNode.merge
  split <;> try simp [PatriciaNode.mk_edge_non_leaf]

-- Merging a non-empty `left` with `Empty` yields `left.mk_edge 0`.
theorem PatriciaNode.non_empty_merge_empty {left: PatriciaNode}
    (left_ne_empty: left ≠ .Empty) :
    (merge left .Empty) = left.mk_edge 0 := by
  unfold PatriciaNode.merge
  split
  all_goals
    rename_i heq
    simp only [imp_false, Prod.mk.injEq] at *
  · simp [heq] at left_ne_empty
  · simp [heq] at left_ne_empty
  · rename_i h_snd
    simp [heq] at h_snd

-- Merging `Empty` with a non-empty `right` yields `right.mk_edge 1`.
theorem PatriciaNode.empty_merge_non_empty {right: PatriciaNode}
    (right_ne_empty: right ≠ .Empty) :
    (merge .Empty right) = right.mk_edge 1 := by
  unfold PatriciaNode.merge
  split
  all_goals
    rename_i heq
    simp only [imp_false, Prod.mk.injEq] at *
  · simp [heq] at right_ne_empty
  · simp [heq] at right_ne_empty
  · rename_i h_fst _
    simp [heq] at h_fst

------------------------
-- PatriciaNode.build --
------------------------

-- Computes the PatriciaNode at the given height and values.
-- values is taken in the range 0 to 2 ^ height - 1.
def PatriciaNode.build (height: ℕ) (values: ℕ → ℕ) : PatriciaNode :=
  match height with
  | 0 => if values 0 = 0 then .Empty else .Leaf (values 0)
  | height_m1 + 1 =>
    let left := PatriciaNode.build height_m1 values
    let right := PatriciaNode.build height_m1 (λ i ↦ values (i + 2 ^ height_m1))
    merge left right

example : PatriciaNode.build 2 (λ i ↦ i) =
  .Binary
    (.Edge { length_m1 := 0, path := 1 } (.Leaf 1))
    (.Binary (.Leaf 2) (.Leaf 3)) := by decide
example : PatriciaNode.build 3 ([0, 1, 0, 0, 2, 3, 0, 0].get ∘ Fin.ofNat 8) =
  .Binary
    (.Edge { length_m1 := 1, path := 1 } (.Leaf 1))
    (.Edge { length_m1 := 0, path := 0 }
      (.Binary (.Leaf 2) (PatriciaNode.Leaf 3))) := by decide
example : PatriciaNode.build 4 (λ i ↦ if i = 11 then 100 else 0) =
  .Edge { length_m1 := 3, path := 11 } (.Leaf 100) := by decide

theorem PatriciaNode.build_valid (height: ℕ) (values: ℕ → ℕ) :
    (PatriciaNode.build height values).valid height := by
  induction height generalizing values
  case zero =>
    simp [PatriciaNode.build]
    split
    · simp [PatriciaNode.valid]
    · simpa [PatriciaNode.valid]
  case succ height_m1 ih =>
    simp [PatriciaNode.build]
    set left := PatriciaNode.build height_m1 values
    set right := PatriciaNode.build height_m1 (λ i ↦ values (i + 2 ^ height_m1))
    have left_valid : left.valid height_m1 := ih _
    have right_valid : right.valid height_m1 := ih _
    exact merge_valid left_valid right_valid

theorem PatriciaNode.build_is_empty {height: ℕ} {values: ℕ → ℕ}
    (h: (PatriciaNode.build height values) = .Empty)
    (index: Fin (2 ^ height)) :
    values index = 0 := by
  induction height generalizing values
  case zero =>
    unfold PatriciaNode.build at h
    simp at h
    simp [(by omega: index = 0), h]
  case succ height_m1 ih =>
    unfold PatriciaNode.build at h
    simp only at h
    set left := PatriciaNode.build height_m1 values
    set right := PatriciaNode.build height_m1 (λ i ↦ values (i + 2 ^ height_m1))
    apply merge_is_empty at h
    by_cases h_index: (index: ℕ) < 2 ^ height_m1
    · exact ih h.1 ⟨index, by omega⟩
    · replace h_index : (index: ℕ) ≥ 2 ^ height_m1 := Nat.not_lt.1 h_index
      have := ih h.2 ⟨index - 2 ^ height_m1, by omega⟩
      simp only [Nat.sub_add_cancel h_index] at this
      exact this

theorem PatriciaNode.build_is_leaf {height: ℕ} {values: ℕ → ℕ} {value: ℕ}
    (h: (PatriciaNode.build height values) = .Leaf value) :
    value = values 0 ∧ height = 0 ∧ value ≠ 0 := by
  cases height
  case zero =>
    unfold PatriciaNode.build at h
    split at h <;> try contradiction
    rename_i h'
    apply Leaf.inj at h
    simp [h] at *
    exact h'
  case succ height_m1 =>
    unfold PatriciaNode.build at h
    simp only [merge_non_leaf] at h

theorem PatriciaNode.build_is_binary {height: ℕ} {values: ℕ → ℕ}
    {left right: PatriciaNode}
    (h: (PatriciaNode.build height values) = .Binary left right) :
    ∃ height_m1,
      height = height_m1 + 1 ∧
      left = PatriciaNode.build height_m1 values ∧
      right = PatriciaNode.build height_m1 (λ i ↦ values (i + 2 ^ height_m1)) := by
  cases height
  case zero =>
    unfold PatriciaNode.build at h
    split at h <;> simp at h
  case succ height_m1 =>
    unfold PatriciaNode.build at h
    simp only at h
    set left' := PatriciaNode.build height_m1 values
    set right' := PatriciaNode.build height_m1 (λ i ↦ values (i + 2 ^ height_m1))
    apply merge_is_binary at h
    use height_m1, by rfl
    subst left' right'
    simp [h]

-- If `build _ values` is an Edge, then `bottom` obtained by building over the path's subtree,
-- and `values` is zero outside that subtree.
theorem PatriciaNode.build_is_edge {height: ℕ} {values: ℕ → ℕ}
    {path: EdgePath} {bottom: PatriciaNode}
    (h: (PatriciaNode.build height values) = .Edge path bottom) :
    let chunk := 2 ^ (height - path.length)
    bottom = PatriciaNode.build (height - path.length) (λ i ↦ values (i + path.path * chunk)) ∧
    (∀ i: Fin (2 ^ height),
      ¬is_in_subtree (height - path.length) path.path i → values i = 0
    ) := by
  induction height generalizing values path
  case zero =>
    unfold PatriciaNode.build at h
    split at h <;> simp at h
  case succ height_m1 ih =>
    unfold PatriciaNode.build at h
    simp only at h
    set left' := PatriciaNode.build height_m1 values
    set right' := PatriciaNode.build height_m1 (λ i ↦ values (i + 2 ^ height_m1))
    unfold PatriciaNode.merge at h
    split at h <;> try contradiction
    · rename_i heq
      have h_left_empty := (Prod.mk.inj heq).1
      cases PatriciaNode.mk_edge_cases right' 1
      case inl h' =>
        replace ⟨path', bottom', h₀, h₁⟩ := h'
        have := Edge.inj (h ▸ h₁)
        rw [this.1]
        simp only [this, EdgePath.length] at ⊢ ih
        simp [ih h₀, Nat.reduceSubDiff, Fin.isValue, Fin.coe_ofNat_eq_mod, Nat.mod_succ]

        have : path'.length_m1 + 1 ≤ height_m1 := by
          have : right'.valid height_m1 := PatriciaNode.build_valid height_m1 _
          exact (PatriciaNode.valid_edge (h₀ ▸ this)).1

        have h_exp : path'.length_m1 + 1 + (height_m1 - (path'.length_m1 + 1)) =
            height_m1 := by
          simp [←Nat.add_sub_assoc this, Nat.add_comm _ height_m1]

        have (i: ℕ) : i + path'.path * 2 ^ (height_m1 - (path'.length_m1 + 1)) + 2 ^ height_m1 =
          i + (path'.path + 2 ^ (path'.length_m1 + 1)) * 2 ^ (height_m1 - (path'.length_m1 + 1)) := by
          rw [add_mul, ←Nat.pow_add, h_exp]
          ring

        constructor
        · conv => enter [1, 2, i]; rw [this]
        · intro ⟨i, i_limit⟩ h_i
          by_cases h_i' : i < 2 ^ height_m1
          case pos h_i' =>
            exact PatriciaNode.build_is_empty h_left_empty ⟨i, by omega⟩
          case neg h_i' =>
            have := (ih h₀).2 ⟨i - 2 ^ height_m1, by omega⟩ (by
              intro h_in_subtree; apply h_i
              simp only [is_in_subtree, add_mul, one_mul] at h_in_subtree ⊢
              have h_pow : 2 ^ (path'.length_m1 + 1) * 2 ^ (height_m1 - (path'.length_m1 + 1)) =
                  2 ^ height_m1 := by rw [← Nat.pow_add, h_exp]
              omega
            )
            simp [Nat.sub_add_cancel (Nat.not_lt.1 h_i')] at this
            exact this
      case inr h' =>
        have := Edge.inj (h ▸ h')
        rw [this.1]
        simp only [this, Fin.isValue, add_tsub_cancel_right, Fin.coe_ofNat_eq_mod, Nat.mod_succ,
          one_mul]
        constructor
        · rfl
        · intro ⟨i, i_limit⟩ h_i
          simp only [is_in_subtree, Nat.reduceAdd] at h_i
          have := PatriciaNode.build_is_empty h_left_empty ⟨i, by omega⟩
          exact this
    · rename_i heq
      have h_right_empty := (Prod.mk.inj heq).2
      cases PatriciaNode.mk_edge_cases left' 0
      case inl h' =>
        replace ⟨path', bottom', h₀, h₁⟩ := h'
        have := Edge.inj (h ▸ h₁)
        rw [this.1]
        simp only [this, EdgePath.length] at ⊢ ih
        simp only [ih h₀, Nat.reduceSubDiff]
        constructor
        · simp
        · intro ⟨i, i_limit⟩ h_i
          simp only [Fin.isValue, Fin.coe_ofNat_eq_mod, Nat.zero_mod, zero_mul, add_zero] at h_i
          by_cases h_i' : i < 2 ^ height_m1
          case pos h_i' =>
            exact (ih h₀).2 ⟨i, by omega⟩ h_i
          case neg h_i' =>
            have := PatriciaNode.build_is_empty h_right_empty ⟨i - 2 ^ height_m1, by omega⟩
            simp [Nat.sub_add_cancel (Nat.not_lt.1 h_i')] at this
            exact this

      case inr h' =>
        have := Edge.inj (h ▸ h')
        rw [this.1]
        simp only [this, Fin.isValue, add_tsub_cancel_right, Fin.coe_ofNat_eq_mod, Nat.zero_mod,
          zero_mul]
        constructor
        · rfl
        · intro ⟨i, i_limit⟩ h_i
          simp only [is_in_subtree, zero_mul, ge_iff_le, zero_le, zero_add, one_mul, true_and,
            not_lt] at h_i
          have := PatriciaNode.build_is_empty h_right_empty ⟨i - 2 ^ height_m1, by omega⟩
          simp only at this
          simp [Nat.sub_add_cancel h_i] at this
          exact this

theorem PatriciaNode.zero_build {height: ℕ} {values: ℕ → ℕ}
    (h: ∀ i: Fin (2 ^ height), values i = 0) :
    PatriciaNode.build height values = .Empty := by
  induction height generalizing values
  case zero =>
    unfold PatriciaNode.build
    simp [h ⟨0, by simp⟩]
  case succ height_m1 ih =>
    unfold PatriciaNode.build PatriciaNode.merge
    simp only
    rw [ih (λ i ↦ h ⟨i, by omega⟩)]
    rw [ih (λ i ↦ h ⟨i + 2 ^ height_m1, by omega⟩)]

theorem PatriciaNode.build_congr {height: ℕ} {values₀ values₁: ℕ → ℕ}
    (h: ∀ i: Fin (2 ^ height), values₀ i = values₁ i) :
    PatriciaNode.build height values₀ = PatriciaNode.build height values₁ := by
  induction height generalizing values₀ values₁
  case zero =>
    unfold PatriciaNode.build
    simp [h ⟨0, by simp⟩]
  case succ height_m1 ih =>
    unfold PatriciaNode.build
    simp only
    rw [ih (λ i ↦ h ⟨i, by omega⟩)]
    rw [ih
      (values₀ := λ i ↦ values₀ (i + 2 ^ height_m1))
      (values₁ := λ i ↦ values₁ (i + 2 ^ height_m1))
      (λ i ↦ h ⟨i + 2^height_m1, by omega⟩)
    ]

-- Building from if-then-else on the halves (`f` on the left half, `g` on the right) is the merge of
-- the two halves' builds.
theorem PatriciaNode.ite_build {height_m1: ℕ} {f g: ℕ → ℕ} :
    PatriciaNode.build (height_m1 + 1) (λ index ↦ if index < 2 ^ height_m1 then f index else g index) =
    PatriciaNode.merge
      (PatriciaNode.build height_m1 f)
      (PatriciaNode.build height_m1 (λ i ↦ g (i + 2 ^ height_m1))) := by
  conv => lhs; unfold build
  simp only
  apply congrArg₂ <;>
  · apply build_congr
    intro i
    simp

theorem PatriciaNode.build_at {height: ℕ} (values: ℕ → ℕ) (index: Fin (2 ^ height)) :
    (PatriciaNode.build height values).at height index = values index := by
  induction height using Nat.strong_induction_on generalizing values
  rename_i height ih
  cases height
  case zero =>
    have : index = 0 := by omega
    unfold PatriciaNode.at
    simp [PatriciaNode.build, this]
    by_cases h: values 0 = 0 <;> simp [h]

  case succ height_m1 =>
    cases h: PatriciaNode.build (height_m1 + 1) values
    case Leaf =>
      have := PatriciaNode.build_is_leaf h
      simp at this
    case Empty => simp [PatriciaNode.at_empty, PatriciaNode.build_is_empty h]
    case Binary left right =>
      have := h ▸ (PatriciaNode.build_valid (height_m1 + 1) values)
      simp only [PatriciaNode.at_binary index this, add_tsub_cancel_right]

      have ⟨height_m1', h_height, h_left, h_right⟩ := PatriciaNode.build_is_binary h
      simp at h_height; subst height_m1'

      by_cases h_index: (index: ℕ) < 2 ^ height_m1
      case pos =>
        have := ih height_m1 (by omega) values ⟨index, h_index⟩
        simp only [h_index, ↓reduceIte, ←this]
        simp [h_left]
      case neg =>
        have := ih height_m1 (by omega)
          (λ i ↦ values (i + 2 ^ height_m1))
          ⟨index - 2 ^ height_m1, by omega⟩
        simp [Nat.sub_add_cancel (Nat.not_lt.1 h_index)] at this
        simp only [h_index, ↓reduceIte, ←this]
        simp [h_right]
    case Edge path bottom =>
      have := h ▸ (PatriciaNode.build_valid (height_m1 + 1) values)
      simp only [PatriciaNode.at_edge index this]
      have ⟨h_bottom, h_outside⟩ := PatriciaNode.build_is_edge h
      set chunk := 2 ^ (height_m1 + 1 - path.length)
      by_cases h_in_subtree : is_in_subtree (height_m1 + 1 - path.length) path.path index
      case pos =>
        simp only [h_in_subtree, ↓reduceIte]
        have h₀ : height_m1 + 1 - path.length = height_m1 - path.length_m1 := by simp [EdgePath.length]
        have := h_in_subtree.sub_offset_lt
        conv at this => rhs; rw [h₀]

        have := ih (height_m1 - path.length_m1) (by omega)
          (λ i ↦ values (i + path.path * chunk))
          ⟨index - path.path * chunk, this⟩
        rw [Nat.sub_add_cancel h_in_subtree.1] at this
        simp only at this
        rw [←this]
        subst bottom
        rw [←h₀]
      case neg =>
        simp only [h_in_subtree, ↓reduceIte]
        exact Eq.symm <| h_outside index (by omega)

theorem PatriciaNode.build_inj {height: ℕ} (values₀ values₁: ℕ → ℕ)
    (h: PatriciaNode.build height values₀ = PatriciaNode.build height values₁)
    (index: Fin (2 ^ height)) :
    values₀ index = values₁ index := by
  rw [←PatriciaNode.build_at values₀ index, h, PatriciaNode.build_at values₁ index]

-----------------------
-- PatriciaNode.hash --
-----------------------

def PatriciaNode.node_hash (crypto: Crypto) (node: PatriciaNode) : ℕ :=
  match node with
  | .Leaf value => value
  | .Binary left right => crypto.hash (left.node_hash crypto) (right.node_hash crypto)
  | .Edge path node => (crypto.hash (node.node_hash crypto) path.path) + path.length
  | .Empty => 0

-- Hash formula for `(Edge path bottom).mk_edge dir`: the path is extended by `dir`, so the encoded
-- path becomes `path.path + dir * 2^path.length` and the encoded length grows by 1.
theorem PatriciaNode.node_hash.edge_mk_edge {crypto: Crypto} (dir: Fin 2)
    {path: EdgePath} {bottom: PatriciaNode} :
    ((PatriciaNode.Edge path bottom).mk_edge dir).node_hash crypto =
    (crypto.hash (bottom.node_hash crypto) (path.path + dir * 2 ^ path.length)) + (path.length + 1) := by
  conv => lhs; unfold PatriciaNode.node_hash
  split <;> try contradiction
  rename_i heq
  cases heq
  rfl

theorem PatriciaNode.node_hash.inj
    {crypto: Crypto} {node₀ node₁: PatriciaNode}
    (h: node₀.node_hash crypto = node₁.node_hash crypto)
    {height: ℕ}
    (height_le_max: height ≤ crypto.max_height)
    (valid₀: node₀.valid height)
    (valid₁: node₁.valid height) :
    node₀ = node₁ := by
  induction height using Nat.strong_induction_on generalizing node₀ node₁
  rename_i height ih
  cases height
  case zero =>
    have valid₀ := PatriciaNode.valid_height0 valid₀
    have valid₁ := PatriciaNode.valid_height0 valid₁
    cases valid₀
    case inl h₀ =>
      cases valid₁
      case inl => simp [*]
      case inr h₁ =>
        obtain ⟨value, h₁⟩ := h₁
        simp [h₀, h₁, node_hash] at h
        simp [h] at h₁
    case inr h₀ =>
      obtain ⟨value, h₀⟩ := h₀
      cases valid₁
      case inl h₁ =>
        simp [h₀, h₁, node_hash] at h
      case inr h₁ =>
        obtain ⟨value, h₁⟩ := h₁
        simp [h₀, h₁, node_hash] at h
        simp [*]

  case succ height_m1 =>
    cases node₀
    case Leaf =>
      have := (PatriciaNode.valid_leaf valid₀).1
      contradiction

    all_goals
      cases node₁
      case Leaf =>
        have := (PatriciaNode.valid_leaf valid₁).1
        contradiction

    all_goals
        unfold node_hash at h

    case Empty.Empty => rfl
    -- Make cases more similar to each other
    all_goals
      apply congrArg (λ x ↦ x + 0) at h
      have (x y : ℕ) : (x + y + 0 = x + y) := by simp
      simp only [this, (by simp: 0 + 0 = 0)] at h

    all_goals
      try
        have := crypto.hash_ne_zero _ _ _ _ (by omega) (by omega) h; contradiction
      try
        have := crypto.hash_ne_zero _ _ _ _ (by omega) (by omega) h.symm; contradiction

    case Binary.Binary =>
      apply crypto.h_hash (by simp) (by simp) at h
      rename_i left₀ right₀ left₁ right₁ _
      have valid₀ := PatriciaNode.valid_binary' valid₀
      have valid₁ := PatriciaNode.valid_binary' valid₁
      have := ih height_m1 (by simp) h.1 (by omega) valid₀.1 valid₁.1
      have := ih height_m1 (by simp) h.2.1 (by omega) valid₀.2.1 valid₁.2.1
      simp [*]

    case Edge.Edge =>
      rename_i path₀ bottom₀ path₁ bottom₁ _
      have valid₀ := PatriciaNode.valid_edge valid₀
      have valid₁ := PatriciaNode.valid_edge valid₁
      apply crypto.h_hash (le_trans valid₀.1 height_le_max) (le_trans valid₁.1 height_le_max) at h
      simp only [←EdgePath.length.eq_def] at h
      have := ih (height_m1 + 1 - path₀.length) (by simp) h.1 (by omega) valid₀.2.1 (h.2.2 ▸ valid₁.2.1)
      simp only [Edge.injEq, and_true, this]
      ext
      · simp only [EdgePath.length, Nat.add_right_cancel_iff] at h
        exact h.2.2
      · exact h.2.1

    case Binary.Edge =>
      rename_i left₀ right₀ path₁ bottom₁ _
      have valid₁ := PatriciaNode.valid_edge valid₁
      apply crypto.h_hash (by simp) (le_trans valid₁.1 height_le_max) at h
      have := h.2.2
      contradiction

    case Edge.Binary =>
      rename_i path₀ bottom₀ left₁ right₁ _
      have valid₀ := PatriciaNode.valid_edge valid₀
      have := height_m1 + 1 ≤ crypto.max_height
      apply crypto.h_hash (le_trans valid₀.1 height_le_max) (by simp) at h
      simp at h

theorem PatriciaNode.node_hash.build_inj
    (crypto: Crypto) (values₀ values₁: ℕ → ℕ)
    (height: ℕ)
    (h: (build height values₀).node_hash crypto = (build height values₁).node_hash crypto)
    (height_le_max: height ≤ crypto.max_height)
    (i: Fin (2 ^ height)) :
    values₀ i = values₁ i := by
  apply PatriciaNode.build_inj
  apply PatriciaNode.node_hash.inj h height_le_max
  · apply PatriciaNode.build_valid
  · apply PatriciaNode.build_valid


-------------------------------
-- Valid nodes are buildable --
-------------------------------

theorem PatriciaNode.at_build {node: PatriciaNode} {height: ℕ}
    (h: node.valid height) :
    PatriciaNode.build height (node.at height) = node := by
  symm
  induction height generalizing node
  case zero =>
    cases PatriciaNode.valid_height0 h
    case inl h => simp [h, PatriciaNode.build, PatriciaNode.at]
    case inr h =>
      obtain ⟨value, h⟩ := h
      simp [h, PatriciaNode.build, PatriciaNode.at]
  case succ height_m1 ih =>
    cases node
    case Leaf =>
      have := PatriciaNode.valid_leaf h
      contradiction
    case Empty =>
      rw [PatriciaNode.zero_build (λ i ↦ PatriciaNode.at_empty _ i)]
    case Binary left right =>
      have ⟨left_valid, right_valid, left_ne_empty, right_ne_empty⟩ := PatriciaNode.valid_binary' h
      unfold PatriciaNode.build
      simp only
      rw [build_congr (by
         intro i
         show _ = left.at height_m1 i
         rw [at_binary _ h]
         simp only [add_tsub_cancel_right, Fin.is_lt, ↓reduceIte]
      )]
      rw [←ih left_valid]

      rw [build_congr (by
         intro i
         show _ = right.at height_m1 i
         rw [at_binary _ h]
         simp only [add_tsub_cancel_right, add_lt_iff_neg_right, not_lt_zero, ↓reduceIte]
      )]
      rw [←ih right_valid]

      simp only [merge_binary left_ne_empty right_ne_empty]
    case Edge path bottom =>
      have ⟨dir, h'⟩ := PatriciaNode.valid_edge_cases h
      cases h'
      case inl h' =>
        have ⟨h_path, bottom_valid, bottom_valid'⟩ := h'
        subst path
        fin_cases dir
        case «0» =>
          rw [build_congr (by
            intro index
            unfold PatriciaNode.at EdgePath.mk_len1
            simp only [is_in_subtree, Nat.sub_zero, zero_add, one_mul, zero_mul, zero_le, true_and]

            let f := λ index ↦ (if ↑index < 2 ^ height_m1 then bottom.at height_m1 index else 0)
            show _ = f index
            simp [f]
          )]
          rw [ite_build]
          conv => enter [2, 2]; rw [zero_build (λ i ↦ rfl)]
          rw [←ih (by simp [h'])]
          rw [non_empty_merge_empty (by by_contra; simp [valid_edge_bottom, this] at bottom_valid')]
          simp [mk_edge]
          split
          · simp [valid_edge_bottom] at h'
          · rfl
        case «1» =>
          rw [build_congr (by
            intro index
            unfold PatriciaNode.at EdgePath.mk_len1
            simp only [is_in_subtree, Nat.sub_zero, one_mul, Nat.reduceAdd, ←Nat.pow_succ',
              Nat.succ_eq_add_one, Fin.is_lt, and_true]
            rw [←ite_not]

            let f := λ index ↦ (if ↑index < 2 ^ height_m1 then 0 else bottom.at height_m1 (index - 2 ^ height_m1))
            show _ = f index
            simp [f]
          )]
          rw [ite_build]
          conv => enter [2, 1]; rw [zero_build (λ i ↦ rfl)]
          conv => enter [2, 2, 2, i]; rw [Nat.add_sub_cancel]
          rw [←ih (by simp [h'])]
          rw [empty_merge_non_empty (by by_contra; simp [valid_edge_bottom, this] at bottom_valid')]
          simp [mk_edge]
          split
          · simp [valid_edge_bottom] at h'
          · rfl
      case inr h =>
        obtain ⟨path', path_extend, h_valid, bottom_valid⟩ := h
        rw [path_extend]
        fin_cases dir
        case «0» =>
          rw [build_congr (by
            intro index
            let f := λ index ↦ (if ↑index < 2 ^ height_m1 then (Edge path' bottom).at height_m1 index else 0)
            show _ = f index
            simp only [Fin.zero_eta, Fin.isValue]
            rw [at_left_extend _ h_valid]
          )]
          rw [ite_build]
          conv => enter [2, 2]; rw [zero_build (λ i ↦ rfl)]
          rw [←ih h_valid]
          rw [non_empty_merge_empty (by simp)]
          rfl
        case «1» =>
          rw [build_congr (by
            intro index
            let f := λ index ↦ (if ↑index < 2 ^ height_m1 then 0 else (Edge path' bottom).at height_m1 (index - 2 ^ height_m1))
            show _ = f index
            simp only [Fin.mk_one, Fin.isValue]
            rw [at_right_extend _ h_valid]
          )]
          rw [ite_build]
          conv => enter [2, 1]; rw [zero_build (λ i ↦ rfl)]
          conv => enter [2, 2, 2, i]; rw [Nat.add_sub_cancel]
          rw [←ih h_valid]
          rw [empty_merge_non_empty (by simp)]
          rfl

-- Corollary: Two valid nodes with the same at()-values are the same
theorem PatriciaNode.at_inj {node₀ node₁: PatriciaNode} {height: ℕ}
    (h_valid₀: node₀.valid height)
    (h_valid₁: node₁.valid height)
    (h: ∀ index: Fin (2 ^ height), node₀.at height index = node₁.at height index) :
    node₀ = node₁ := by
  rw [←PatriciaNode.at_build h_valid₀, build_congr h, PatriciaNode.at_build h_valid₁]
