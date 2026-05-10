import patricia.crypto
import patricia.patricia.edge_path
import patricia.patricia.node

structure PatriciaTree (height: ℕ) where
  node: PatriciaNode
  valid: node.valid height

@[ext]
def PatriciaTree.ext {height: ℕ} {node₀ node₁: PatriciaTree height} :
    node₀.node = node₁.node → node₀ = node₁ := by
  intro h
  cases node₀
  cases node₁
  simp only at h
  simp [h]

def PatriciaTree.Empty (height: ℕ) : PatriciaTree height :=
  ⟨.Empty, by cases height <;> simp [PatriciaNode.valid]⟩

def PatriciaTree.build (height: ℕ) (values: ℕ → ℕ) : PatriciaTree height :=
  ⟨.build height values, PatriciaNode.build_valid height values⟩

def PatriciaTree.mk_binary {height_m1: ℕ} (left right: PatriciaTree height_m1)
    (h_left_ne_empty: left.node ≠ .Empty) (h_right_ne_empty: right.node ≠ .Empty) :
    PatriciaTree (height_m1 + 1) :=
  ⟨
    .Binary left.node right.node,
    by simp [PatriciaNode.valid, left.valid, right.valid, h_left_ne_empty, h_right_ne_empty]
  ⟩

def PatriciaTree.mk_edge {height_m1: ℕ} (tree: PatriciaTree height_m1) (dir: Fin 2)
    (h_ne_empty: tree.node ≠ .Empty) :
    PatriciaTree (height_m1 + 1) :=
  ⟨tree.node.mk_edge dir, PatriciaNode.mk_edge_valid dir tree.valid h_ne_empty⟩

-- When `tree.node` is a valid edge bottom (Leaf or Binary), `mk_edge dir` wraps it in a fresh
-- length-1 Edge with `tree.node` as the bottom.
theorem PatriciaTree.mk_edge.of_valid_edge_bottom {height_m1: ℕ} {tree: PatriciaTree height_m1} (dir: Fin 2)
    {h_ne_empty: tree.node ≠ .Empty}
    (h_valid: tree.node.valid_edge_bottom) :
    (tree.mk_edge dir h_ne_empty).node = .Edge (.mk_len1 dir) tree.node := by
  cases h: tree.node
  case Empty => contradiction
  case Leaf value => simp [PatriciaTree.mk_edge, h, PatriciaNode.mk_edge]
  case Binary left right => simp [PatriciaTree.mk_edge, h, PatriciaNode.mk_edge]
  case Edge path bottom => simp [h, PatriciaNode.valid_edge_bottom] at h_valid

theorem PatriciaTree.build_congr {height: ℕ} {values₀ values₁: ℕ → ℕ}
    (h: ∀ i: Fin (2 ^ height), values₀ i = values₁ i) :
    PatriciaTree.build height values₀ = PatriciaTree.build height values₁ := by
  apply PatriciaTree.ext
  apply PatriciaNode.build_congr h

def PatriciaTree.at {height: ℕ} (tree: PatriciaTree height) (index: ℕ) : ℕ :=
  tree.node.at height index

theorem PatriciaTree.at_build {height: ℕ} (tree: PatriciaTree height) :
    PatriciaNode.build height tree.at = tree.node := by
  unfold PatriciaTree.at
  conv => rhs; rw [←PatriciaNode.at_build tree.valid]

theorem PatriciaTree.build_at {height: ℕ} (values: ℕ → ℕ) (index: Fin (2 ^ height)):
    (PatriciaTree.build height values).at index = values index := by
  unfold PatriciaTree.at PatriciaTree.build
  rw [PatriciaNode.build_at]

theorem PatriciaTree.build_at' {height: ℕ} (values: ℕ → ℕ) {index: ℕ} (index_lt: index < 2 ^ height):
    (PatriciaTree.build height values).at index = values index := by
  unfold PatriciaTree.at PatriciaTree.build
  rw [PatriciaNode.build_at values ⟨index, index_lt⟩]

theorem PatriciaTree.at.inj {height: ℕ} {tree₀ tree₁: PatriciaTree height}
    (h: ∀ index: Fin (2 ^ height), tree₀.at index = tree₁.at index) :
    tree₀ = tree₁ := by
  apply PatriciaTree.ext
  apply PatriciaNode.at_inj tree₀.valid tree₁.valid h

theorem PatriciaTree.at_empty {height: ℕ} :
    (PatriciaTree.Empty height).at i = 0 := by
  simp [PatriciaTree.at, PatriciaTree.Empty, PatriciaNode.at_empty]

def PatriciaTree.hash (crypto: Crypto) {height: ℕ} (tree: PatriciaTree height) : ℕ :=
  tree.node.node_hash crypto

theorem PatriciaTree.hash_inj {crypto: Crypto} {height: ℕ} {tree₀ tree₁: PatriciaTree height}
    (height_le_max: height ≤ crypto.max_height)
    (h: tree₀.hash crypto = tree₁.hash crypto) :
    tree₀ = tree₁ := by
  apply PatriciaTree.ext
  apply PatriciaNode.node_hash.inj h (by omega) tree₀.valid tree₁.valid

-- At height 0, a tree's hash coincides with its single value at index 0.
theorem PatriciaTree.hash_height0 {crypto: Crypto} (tree: PatriciaTree 0) :
    tree.hash crypto = tree.at 0 := by
  unfold PatriciaTree.hash PatriciaTree.at
  rcases PatriciaNode.valid_height0 tree.valid with h | ⟨v, h, _⟩
  · simp [h, PatriciaNode.node_hash, PatriciaNode.at_empty]
  · simp [h, PatriciaNode.node_hash, PatriciaNode.at_leaf]

def PatriciaTree.subtree {height_m1: ℕ} (tree: PatriciaTree (height_m1 + 1)) (dir: Fin 2) : PatriciaTree height_m1 :=
  .build height_m1 (λ i ↦ tree.node.at (height_m1 + 1) (i + dir * 2 ^ height_m1))

def PatriciaTree.left_subtree {height_m1: ℕ} (tree: PatriciaTree (height_m1 + 1)) : PatriciaTree height_m1 :=
  subtree tree 0

def PatriciaTree.right_subtree {height_m1: ℕ} (tree: PatriciaTree (height_m1 + 1)) : PatriciaTree height_m1 :=
  subtree tree 1

theorem PatriciaTree.subtree_at {height_m1: ℕ} (tree: PatriciaTree (height_m1 + 1)) (dir: Fin 2)
    {i: ℕ} (h: i < 2 ^ height_m1) :
    (tree.subtree dir).at i = tree.at (i + dir * 2 ^ height_m1) := by
  unfold PatriciaTree.subtree PatriciaTree.at PatriciaTree.build
  simp [PatriciaNode.build_at (index:=⟨i, h⟩)]

theorem PatriciaTree.left_subtree_at {height_m1: ℕ} (tree: PatriciaTree (height_m1 + 1))
    {i: ℕ} (h: i < 2 ^ height_m1) :
    tree.left_subtree.at i = tree.at i := by
  unfold PatriciaTree.left_subtree PatriciaTree.at PatriciaTree.subtree PatriciaTree.build
  simp [PatriciaNode.build_at (index:=⟨i, h⟩)]

theorem PatriciaTree.right_subtree_at {height_m1: ℕ} (tree: PatriciaTree (height_m1 + 1))
    {i: ℕ} (h: i < 2 ^ height_m1) :
    tree.right_subtree.at i = tree.at (i + 2 ^ height_m1) := by
  unfold PatriciaTree.right_subtree PatriciaTree.at PatriciaTree.subtree PatriciaTree.build
  simp [PatriciaNode.build_at (index:=⟨i, h⟩)]

def PatriciaTree.descend
    {height: ℕ} (tree: PatriciaTree height)
    {length: ℕ} (word: Fin (2 ^ (length: ℕ))) : PatriciaTree (height - length) :=
  .build (height - length) (λ i ↦ tree.node.at height (i + word * 2 ^ (height - length)))

theorem PatriciaTree.descend_at {height: ℕ} {tree: PatriciaTree height}
    {length: ℕ} (word: Fin (2 ^ (length: ℕ))) {i: ℕ} (h: i < 2 ^ (height - length)) :
    (tree.descend word).at i = tree.at (i + word * 2 ^ (height - length)) := by
  unfold PatriciaTree.descend PatriciaTree.at PatriciaTree.build
  simp [PatriciaNode.build_at (index:=⟨i, h⟩)]

theorem PatriciaTree.descend_zero {height: ℕ} {tree: PatriciaTree height}
    (word: Fin (2 ^ 0)) :
    tree.descend word = tree := by
  apply PatriciaTree.at.inj
  intro index
  simp [PatriciaTree.descend_at word]

-- For a tree built directly as `.Binary left.node right.node`, its left/right subtrees recover
-- `left` and `right`.
theorem PatriciaTree.of_binary {height_m1: ℕ} (left right: PatriciaTree height_m1)
    (h: (PatriciaNode.Binary left.node right.node).valid (height_m1 + 1)) :
    let tree: PatriciaTree (height_m1 + 1) := ⟨.Binary left.node right.node, h⟩
    (tree.left_subtree = left) ∧ (tree.right_subtree = right) := by
  have ⟨left_valid, right_valid, _, _⟩ := PatriciaNode.valid_binary' h
  constructor
  · apply PatriciaTree.at.inj
    intro index
    rw [PatriciaTree.left_subtree_at _ (by omega)]
    simp [PatriciaTree.at, PatriciaNode.at_binary _ h]
  · apply PatriciaTree.at.inj
    intro index
    rw [PatriciaTree.right_subtree_at _ (by omega)]
    simp [PatriciaTree.at, PatriciaNode.at_binary _ h]

-- For a length-1 Edge in direction `dir`, the `dir`-subtree is `bottom` and the opposite
-- subtree is empty.
theorem PatriciaTree.of_edge_len1 {height_m1: ℕ}
    (tree: PatriciaTree (height_m1 + 1)) (dir: Fin 2) (bottom: PatriciaTree height_m1)
    (h_node: tree.node = PatriciaNode.Edge (EdgePath.mk_len1 dir) bottom.node) :
    tree.subtree dir = bottom ∧ tree.subtree (1 - dir) = .Empty _:= by
  have h_valid := h_node ▸ tree.valid
  constructor
  · apply PatriciaTree.at.inj
    intro index
    rw [PatriciaTree.subtree_at _ _ (by omega)]
    simp only [PatriciaTree.at, h_node, PatriciaNode.at_edge _ h_valid]
    rw [ite_cond_eq_true _ _ (by
      simp only [eq_iff_iff, iff_true, add_tsub_cancel_right]
      exact is_in_subtree.mk dir index
    )]
    simp
  · apply PatriciaTree.at.inj
    intro index
    rw [PatriciaTree.subtree_at _ _ (by omega), PatriciaTree.at_empty]
    simp only [PatriciaTree.at, h_node, PatriciaNode.at_edge _ h_valid]
    rw [ite_cond_eq_false _ _ (by
      simp only [eq_iff_iff, iff_false, add_tsub_cancel_right]
      intro h_in_subtree
      have h_in_subtree' := is_in_subtree.mk ↑(1 - dir) index
      exact absurd (h_in_subtree.inj_path h_in_subtree') (by omega)
    )]

-- If tree is of the form `PatriciaNode.Edge (edge_path.extend dir) bottom`,
-- the `dir`-subtree is the corresponding shorter Edge (with the same bottom),
-- and the opposite subtree (`1 - dir`) is empty.
theorem PatriciaTree.of_edge_extend {height_m1: ℕ}
    (tree: PatriciaTree (height_m1 + 1)) (edge_path: EdgePath) (dir: Fin 2)
    (bottom: PatriciaNode)
    (h_node: tree.node = PatriciaNode.Edge (edge_path.extend dir) bottom) :
    ∃ h_valid: (PatriciaNode.Edge edge_path bottom).valid height_m1,
    tree.subtree dir = ⟨PatriciaNode.Edge edge_path bottom, h_valid⟩ ∧
    tree.subtree (1 - dir) = .Empty _ := by
  have h_valid := h_node ▸ tree.valid
  let extend_valid := PatriciaNode.valid_edge_extend.1 h_valid
  use extend_valid
  constructor
  · apply PatriciaTree.at.inj
    intro index
    rw [PatriciaTree.subtree_at _ _ (by omega)]
    fin_cases dir
    case «0» => simp [PatriciaTree.at, h_node, PatriciaNode.at_left_extend _ extend_valid]
    case «1» => simp [PatriciaTree.at, h_node, PatriciaNode.at_right_extend _ extend_valid]
  · apply PatriciaTree.at.inj
    intro index
    rw [PatriciaTree.subtree_at _ _ (by omega), PatriciaTree.at_empty]
    fin_cases dir
    case «0» => simp [PatriciaTree.at, h_node, PatriciaNode.at_left_extend _ extend_valid]
    case «1» => simp [PatriciaTree.at, h_node, PatriciaNode.at_right_extend _ extend_valid]

theorem PatriciaTree.empty_subtree (height_m1: ℕ) (dir: Fin 2) :
    let node : PatriciaTree (height_m1 + 1) := .Empty (height_m1 + 1)
    node.subtree dir = .Empty height_m1 := by
  unfold PatriciaTree.subtree PatriciaTree.build
  apply PatriciaTree.ext
  apply PatriciaNode.at_inj (PatriciaNode.build_valid _ _) ((PatriciaTree.Empty height_m1).valid)
  intro index
  simp [PatriciaTree.Empty, PatriciaNode.build_at, PatriciaNode.at_empty]

theorem PatriciaTree.empty_descend (height: ℕ) {length: ℕ} (word: Fin (2 ^ (length: ℕ))) :
    (PatriciaTree.Empty height).descend word = .Empty _ := by
  unfold PatriciaTree.descend PatriciaTree.build
  apply PatriciaTree.ext
  apply PatriciaNode.at_inj (PatriciaNode.build_valid _ _) ((PatriciaTree.Empty _).valid)
  intro index
  simp [PatriciaTree.Empty, PatriciaNode.build_at, PatriciaNode.at_empty]

-- If a tree's hash is of the form `crypto.hash hash_left hash_right` (binary hash),
-- then the tree is Binary, and its subtrees' hashes match `hash_left` and `hash_right`.
theorem PatriciaTree.of_hash_binary {crypto: Crypto} {height_m1: ℕ} {tree: PatriciaTree (height_m1 + 1)}
    (hash_left hash_right: ℕ)
    (h_height_le_max: height_m1 < crypto.max_height)
    (h_hash: tree.hash crypto = crypto.hash hash_left hash_right) :
    tree.node = .Binary tree.left_subtree.node tree.right_subtree.node ∧
    tree.left_subtree.hash crypto = hash_left ∧
    tree.right_subtree.hash crypto = hash_right := by
  unfold PatriciaTree.hash PatriciaNode.node_hash at h_hash
  split at h_hash
  · rename_i h_node
    have := (PatriciaNode.valid_leaf (h_node ▸ tree.valid)).1
    contradiction
  · rename_i left' right' h_eq
    apply crypto.h_hash' at h_hash
    have ⟨left_valid, right_valid, _, _⟩ := PatriciaNode.valid_binary' (h_eq ▸ tree.valid)
    have := PatriciaTree.of_binary ⟨left', left_valid⟩ ⟨right', right_valid⟩ (h_eq ▸ tree.valid)
    simp [PatriciaTree.ext_iff] at this

    have h_left : left' = tree.left_subtree.node := by
      rw [←this.1]
      conv in left'.Binary right' => rw [←h_eq]

    have h_right : right' = tree.right_subtree.node := by
      rw [←this.2]
      conv in left'.Binary right' => rw [←h_eq]

    simp [←h_hash, h_eq, h_left, h_right]
    trivial
  · rename_i path node h_node
    have h_hash : _ = crypto.hash hash_left hash_right + 0 := h_hash
    have := (PatriciaNode.valid_edge (h_node ▸ tree.valid)).1
    apply crypto.h_hash (by omega) (by omega) at h_hash
    simp [EdgePath.length] at h_hash
  · exact absurd (Eq.symm h_hash) (crypto.hash_ne_zero' hash_left hash_right)

-- If a tree's hash is of the form `crypto.hash hash_bottom path + (length_m1 + 1)` (edge hash),
-- then the tree is Edge with that path, length, and a bottom with hash `hash_bottom`.
theorem PatriciaTree.of_hash_edge
    {crypto: Crypto} {height_m1: ℕ} {tree: PatriciaTree (height_m1 + 1)}
    (path length_m1: ℕ) (hash_bottom: ℕ)
    (h_length: length_m1 + 1 ≤ crypto.max_height)
    (h_height_le_max: height_m1 + 1 ≤ crypto.max_height)
    (h_hash: tree.hash crypto = (crypto.hash hash_bottom path) + (length_m1 + 1)) :
    ∃ (bottom: PatriciaTree (height_m1 - length_m1))
      (h_path: path < 2 ^ (length_m1 + 1)),
      tree.node = .Edge ⟨length_m1, ⟨path, h_path⟩⟩ bottom.node ∧
      bottom.hash crypto = hash_bottom := by
  unfold PatriciaTree.hash PatriciaNode.node_hash at h_hash
  split at h_hash
  · rename_i h_node
    have := (PatriciaNode.valid_leaf (h_node ▸ tree.valid)).1
    contradiction
  · rename_i left' right' h_eq
    have h_hash : crypto.hash (left'.node_hash crypto) (right'.node_hash crypto) + 0 = _ := h_hash
    apply crypto.h_hash (by omega) h_length at h_hash
    simp at h_hash
  · rename_i path' node h_node
    have ⟨h_path'_length, node_valid, h_valid_edge_bottom⟩ := PatriciaNode.valid_edge (h_node ▸ tree.valid)
    apply crypto.h_hash (by omega) (by omega) at h_hash
    simp only [EdgePath.length, Nat.add_right_cancel_iff] at h_hash
    have ⟨h_hash_node, h_hash_path, h_hash_length⟩ := h_hash
    simp only [EdgePath.length, h_hash_length, Nat.reduceSubDiff] at node_valid
    have h_path_lt := h_hash_length ▸ h_hash_path ▸ path'.path.2
    use ⟨node, node_valid⟩, h_path_lt
    have : path' = ⟨length_m1, ⟨path, h_path_lt⟩⟩ := by
      apply EdgePath.ext <;> simp [h_hash]
    rw [h_node, this, ←h_hash_node]
    trivial
  · exact absurd (Eq.symm h_hash) (crypto.hash_ne_zero hash_bottom _ _ 0 (by omega) (by omega))

-- Hash of a built tree where both halves of `values` are non-empty subtrees.
theorem PatriciaTree.build_hash_binary
    {crypto: Crypto} {height_m1: ℕ} {values: ℕ → ℕ}
    (left right: PatriciaTree height_m1)
    (h_left: ∀ i: Fin (2 ^ height_m1), values i = left.at i)
    (h_right: ∀ i: Fin (2 ^ height_m1), values (i + 2 ^ height_m1) = right.at i)
    (h_left_ne: left.hash crypto ≠ 0)
    (h_right_ne: right.hash crypto ≠ 0) :
    PatriciaTree.build (height_m1 + 1) values = PatriciaTree.mk_binary left right
      (by intro h_empty; apply h_left_ne; simp [PatriciaTree.hash, h_empty, PatriciaNode.node_hash])
      (by intro h_empty; apply h_right_ne; simp [PatriciaTree.hash, h_empty, PatriciaNode.node_hash]) := by
  apply PatriciaTree.ext
  simp only [PatriciaTree.build, PatriciaNode.build]
  conv in PatriciaNode.merge _ _ =>
    congr
    · rw [PatriciaNode.build_congr h_left]
    · rw [PatriciaNode.build_congr (λ i ↦ h_right i)]
  rw [PatriciaTree.at_build, PatriciaTree.at_build]
  rw [PatriciaNode.merge_binary
    (by intro h_empty; apply h_left_ne; simp [PatriciaTree.hash, h_empty, PatriciaNode.node_hash])
    (by intro h_empty; apply h_right_ne; simp [PatriciaTree.hash, h_empty, PatriciaNode.node_hash])]
  rfl

-- If `values` matches `tree_dir` on the `dir` half and is zero on the other half, then
-- `build (height_m1 + 1) values` equals `tree_dir.mk_edge dir`.
theorem PatriciaTree.build_edge
    {crypto: Crypto} {height_m1: ℕ} {values: ℕ → ℕ}
    (tree_dir: PatriciaTree height_m1) (dir: Fin 2)
    (h_dir: ∀ i: Fin (2 ^ height_m1), values (i + dir * 2 ^ height_m1) = tree_dir.at i)
    (h_other_dir: ∀ i: Fin (2 ^ height_m1), values (i + (1 - dir) * 2 ^ height_m1) = 0)
    (h_ne_zero: tree_dir.hash crypto ≠ 0) :
    (PatriciaTree.build (height_m1 + 1) values) = (tree_dir.mk_edge dir (
      by intro h_empty; apply h_ne_zero; simp [PatriciaTree.hash, h_empty, PatriciaNode.node_hash]
    )) := by
  have tree_ne_empty : tree_dir.node ≠ .Empty := by
    intro h_empty; apply h_ne_zero; simp [PatriciaTree.hash, h_empty, PatriciaNode.node_hash]
  apply PatriciaTree.ext
  simp only [PatriciaTree.build, PatriciaNode.build]
  fin_cases dir
  case «0» =>
    simp only [zero_mul, add_zero, tsub_zero, one_mul] at h_dir h_other_dir
    conv in PatriciaNode.merge _ _ =>
      congr
      · rw [PatriciaNode.build_congr h_dir]
      · rw [PatriciaNode.zero_build h_other_dir]

    rw [PatriciaTree.at_build]
    rw [PatriciaNode.non_empty_merge_empty tree_ne_empty]
    simp only [Fin.isValue, Fin.zero_eta, PatriciaTree.mk_edge]
  case «1» =>
    simp only [one_mul, tsub_self, zero_mul, add_zero] at h_dir h_other_dir
    conv in PatriciaNode.merge _ _ =>
      congr
      · rw [PatriciaNode.zero_build h_other_dir]
      · rw [PatriciaNode.build_congr h_dir]

    rw [PatriciaTree.at_build]
    rw [PatriciaNode.empty_merge_non_empty tree_ne_empty]
    simp only [Fin.isValue, Fin.mk_one, PatriciaTree.mk_edge]

-- Descending by a `word` that matches the full edge path produces the edge's bottom tree.
theorem PatriciaTree.descend_full {height length: ℕ}
    {tree: PatriciaTree height} {edge_path: EdgePath}
    {bottom_tree: PatriciaTree (height - length)}
    (h_node: tree.node = .Edge edge_path bottom_tree.node)
    (word: Fin (2 ^ length))
    (h_word: (word : ℕ) = edge_path.path)
    (h_len: length = edge_path.length) :
    tree.descend word = bottom_tree := by
  apply PatriciaTree.at.inj
  intro index
  rw [PatriciaTree.descend_at _ index.isLt]
  unfold PatriciaTree.at
  rw [h_node, PatriciaNode.at_edge _ (h_node ▸ tree.valid), h_word, ←h_len,
    if_pos (is_in_subtree.mk (↑edge_path.path : ℕ) index), Nat.add_sub_cancel]
