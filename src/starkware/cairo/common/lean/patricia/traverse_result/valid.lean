import patricia.traverse_result.traverse_result
import patricia.patricia.tree

-- `res.valid crypto path ref` says that `res` is a well-formed traversal of the subtree of `ref`
-- rooted at `(height, path)`, with the following properties:
-- * The siblings must match the subtrees of the reference tree.
-- * The update values are not checked (Compare this with `strong_valid`).
--
-- `valid` is defined as follows:
-- (1) At the leaf level (height 0) it is a single update `(path, *)`
--   (note that the value is not enforced).
-- (2) At `height > 0` it is one of three structural shapes that mirror the `traverse_*` branches:
--   * Binary : `res = res₀.add res₁` with `res₀`/`res₁` valid for the left/right subtrees.
--   * Edge : `res = (sibling h).add res₀` where `h` is the OTHER subtree's hash and `res₀` is
--       valid for the chosen direction's subtree.
--   * Descent : `res = (descent length).add res₀` where the `word`-indexed sub-subtree (at depth
--       `length ≥ 2`) holds `res₀` and all sibling sub-subtrees at that depth are empty.
def TraverseResult.valid
    (crypto: Crypto) {height: ℕ} (path: ℕ)
    (res: TraverseResult) (ref: PatriciaTree height) : Prop :=
  match height with
  | 0 =>
    ∃ val, res = .update (path, val)
  | height_m1 + 1 => (
    -- Binary case.
    ∃ (res₀ res₁: TraverseResult),
      res = res₀.add res₁ ∧
      res₀.valid crypto (path * 2) ref.left_subtree ∧
      res₁.valid crypto (path * 2 + 1) ref.right_subtree
  ) ∨ (
    -- Edge.
    ∃ (res₀: TraverseResult) (dir: Fin 2),
      let sibling := ((ref.subtree (1 - dir)).hash crypto)
      res = (TraverseResult.sibling sibling).add res₀ ∧
      res₀.valid crypto (path * 2 + dir) (ref.subtree dir)
  ) ∨ (
    -- Descent.
    ∃ (res₀: TraverseResult) (length_m2: ℕ) (word: Fin (2 ^ (length_m2 + 2))),
      let length := length_m2 + 2
      res = (TraverseResult.descent length).add res₀ ∧
      -- The following condition is equivalent to `length ≤ height`.
      length_m2 < height_m1 ∧
      res₀.valid crypto (path * 2 ^ length + word) (ref.descend word) ∧
      (∀ word' : Fin (2 ^ (length_m2 + 2)), word ≠ word' → ref.descend word' = .Empty _)
  )

------------------------
-- valid constructors --
------------------------

theorem TraverseResult.valid.mk_both
    {crypto: Crypto} {height_m1: ℕ} {path: ℕ} {res res₀ res₁: TraverseResult} {ref: PatriciaTree (height_m1 + 1)}
    (h_res: res = res₀.add res₁)
    (h_valid₀: res₀.valid crypto (path * 2) ref.left_subtree)
    (h_valid₁: res₁.valid crypto (path * 2 + 1) ref.right_subtree) :
    res.valid crypto path ref := by
  unfold valid
  exact Or.inl ⟨res₀, res₁, h_res, h_valid₀, h_valid₁⟩

theorem TraverseResult.valid.mk_edge
    {crypto: Crypto} {height_m1: ℕ} {path: ℕ} {res res₀: TraverseResult} {ref: PatriciaTree (height_m1 + 1)}
    (dir: Fin 2)
    (h_res: res = (TraverseResult.sibling ((ref.subtree (1 - dir)).hash crypto)).add res₀)
    (h_valid: res₀.valid crypto (path * 2 + dir) (ref.subtree dir)) :
    res.valid crypto path ref := by
  unfold valid
  exact Or.inr <| Or.inl ⟨res₀, dir, h_res, h_valid⟩

theorem TraverseResult.valid.mk_descent
    {crypto: Crypto} {height_m1: ℕ} {path: ℕ} {res₀: TraverseResult} {ref: PatriciaTree (height_m1 + 1)}
    (length_m2: ℕ) (word: Fin (2 ^ (length_m2 + 2)))
    (h_length: length_m2 < height_m1)
    (h_res: res = ((TraverseResult.descent (length_m2 + 2)).add res₀))
    (h_valid: res₀.valid crypto (path * 2 ^ (length_m2 + 2) + word) (ref.descend word))
    (h_empty: ∀ word' : Fin (2 ^ (length_m2 + 2)), word ≠ word' → ref.descend word' = .Empty _) :
    res.valid crypto path ref := by
  unfold valid
  exact Or.inr <| Or.inr ⟨res₀, length_m2, word, h_res, h_length, h_valid, h_empty⟩

-----------------------
-- valid eliminators --
-----------------------

-- Eliminator for `valid` at a successor height: given a `h_valid: res.valid crypto path ref` at
-- `height_m1 + 1`, splits into the three structural cases (Binary / Edge / Descent).
--
-- Usage example:
--   cases h_valid using TraverseResult.valid.elim_succ
--   case Binary  res₀ res₁ h_res h_valid₀ h_valid₁ => ...
--   case Edge    res' dir h_res h_valid => ...
--   case Descent res' length_m2 word h_res h_length h_valid h_empty => ...
@[elab_as_elim]
theorem TraverseResult.valid.elim_succ
    {crypto: Crypto} {height_m1: ℕ} {path: ℕ}
    {res: TraverseResult} {ref: PatriciaTree (height_m1 + 1)}
    {motive: res.valid crypto path ref → Prop}
    (Binary:
      ∀ (res₀ res₁: TraverseResult)
        (h_res: res = res₀.add res₁)
        (h_valid₀: res₀.valid crypto (path * 2) ref.left_subtree)
        (h_valid₁: res₁.valid crypto (path * 2 + 1) ref.right_subtree),
        motive (mk_both h_res h_valid₀ h_valid₁))
    (Edge:
      ∀ (res': TraverseResult) (dir: Fin 2)
        (h_res: res = (TraverseResult.sibling ((ref.subtree (1 - dir)).hash crypto)).add res')
        (h_valid: res'.valid crypto (path * 2 + dir) (ref.subtree dir)),
        motive (mk_edge dir h_res h_valid))
    (Descent:
      ∀ (res': TraverseResult) (length_m2: ℕ) (word: Fin (2 ^ (length_m2 + 2)))
        (h_res: res = (TraverseResult.descent (length_m2 + 2)).add res')
        (h_length: length_m2 < height_m1)
        (h_valid: res'.valid crypto (path * 2 ^ (length_m2 + 2) + word) (ref.descend word))
        (h_empty: ∀ word' : Fin (2 ^ (length_m2 + 2)), word ≠ word' → ref.descend word' = .Empty _),
        motive (mk_descent length_m2 word h_length h_res h_valid h_empty)) :
    ∀ (h: res.valid crypto path ref), motive h := by
  intro h
  unfold valid at h
  rcases h with
    ⟨res₀, res₁, h_res, h_valid₀, h_valid₁⟩ |
    ⟨res', dir, h_res, h_valid⟩ |
    ⟨res', length_m2, word, h_res, h_length, h_valid, h_empty⟩
  · exact Binary res₀ res₁ h_res h_valid₀ h_valid₁
  · exact Edge res' dir h_res h_valid
  · exact Descent res' length_m2 word h_res h_length h_valid h_empty

-- A `valid` result has at least one update and every update key lies in the subtree at
-- `(height, path)`.
theorem TraverseResult.valid.implies_updates
    {crypto: Crypto} {height: ℕ} {path: ℕ} {res: TraverseResult} {ref: PatriciaTree height}
    (h_valid₀: res.valid crypto path ref) :
    res.updates ≠ [] ∧ ∀ update ∈ res.updates, is_in_subtree height path update.1 := by
  induction height using Nat.strong_induction_on generalizing res path
  rename_i height ih
  cases height
  case zero =>
    unfold valid at h_valid₀
    have ⟨_, _⟩ := h_valid₀
    subst res
    simp [is_in_subtree.height0]
  case succ height_m1 =>
    cases h_valid₀ using TraverseResult.valid.elim_succ
    case Binary res₀ res₁ h_res h_valid₀ h_valid₁ =>
      subst res
      simp only [is_in_subtree.height_add1']
      constructor
      · simp [ih _ (by simp) h_valid₀]
      · intro update h_update

        simp only [List.mem_append] at h_update
        cases h_update
        case inl h_update =>
          exact Or.inl ((ih _ (by simp) h_valid₀).2 update h_update)
        case inr h_update =>
          exact Or.inr ((ih _ (by simp) h_valid₁).2 update h_update)
    case Edge res₀ dir h_res h_valid =>
      subst res
      constructor
      · simp [ih _ (by simp) h_valid]
      · intro update h_update
        apply is_in_subtree.height_add1 (dir:=dir)
        exact (ih _ (by simp) h_valid).2 update h_update
    case Descent res₀ length_m2 word h_res h_height h_valid h_empty =>
      subst res
      constructor
      · simp [ih _ (by simp) h_valid]
      · intro update h_update
        apply is_in_subtree.height_add (word:=word) (length_le_height:=by omega)
        exact (ih _ (by simp) h_valid).2 update h_update

theorem TraverseResult.valid.unique_value
    {crypto: Crypto} {height: ℕ} {path: ℕ}
    {res: TraverseResult} {ref: PatriciaTree height}
    {key val val': ℕ}
    (h_valid: res.valid crypto path ref)
    (h_mem: (key, val) ∈ res.updates)
    (h_mem': (key, val') ∈ res.updates) :
    val = val' := by
  induction height using Nat.strong_induction_on generalizing res path
  rename_i height ih
  cases height
  case zero =>
    unfold valid at h_valid
    have ⟨_, h_res_eq⟩ := h_valid
    subst res
    simp at h_mem h_mem'
    rw [h_mem.2, h_mem'.2]
  case succ height_m1 =>
    cases h_valid using TraverseResult.valid.elim_succ
    case Binary res₀ res₁ h_res_split h_valid₀ h_valid₁ =>
      subst res
      simp only [List.mem_append] at h_mem h_mem'
      cases h_mem
      case inl h_mem =>
        cases h_mem'
        case inl h_mem' => exact ih _ (by simp) h_valid₀ h_mem h_mem'
        case inr h_mem' =>
          have h_left := (implies_updates h_valid₀).2 _ h_mem
          have h_right := (implies_updates h_valid₁).2 _ h_mem'
          exact absurd (is_in_subtree.inj_path h_left h_right) (by simp)
      case inr h_mem =>
        cases h_mem'
        case inl h_mem' =>
          have h_right := (implies_updates h_valid₁).2 _ h_mem
          have h_left := (implies_updates h_valid₀).2 _ h_mem'
          exact absurd (is_in_subtree.inj_path h_left h_right) (by simp)
        case inr h_mem' => exact ih _ (by simp) h_valid₁ h_mem h_mem'
    case Edge res₀ dir h_res_split h_valid =>
      subst res
      simp only [List.nil_append] at h_mem h_mem'
      exact ih _ (by simp) h_valid h_mem h_mem'
    case Descent res₀ length_m2 word h_res_split h_length h_valid h_empty =>
      subst res
      simp only [List.nil_append] at h_mem h_mem'
      exact ih _ (by simp) h_valid h_mem h_mem'

theorem TraverseResult.valid.exists_update
    {crypto: Crypto} {height: ℕ} {path: ℕ} {res: TraverseResult} {ref: PatriciaTree height}
    (h_valid: res.valid crypto path ref) :
    ∃ update ∈ res.updates, is_in_subtree height path update.1 := by
  have ⟨update, h_update⟩ := List.exists_mem_of_ne_nil _ (h_valid.implies_updates).1
  exact ⟨update, h_update, (h_valid.implies_updates).2 update h_update⟩

-- If res has updates in both subtrees, it must be in the binary disjunct.
theorem TraverseResult.valid.binary_elim
    {crypto: Crypto} {height_m1 path: ℕ} {res: TraverseResult}
    {ref: PatriciaTree (height_m1 + 1)}
    (h_valid: res.valid crypto path ref)
    (h_left_update: ∃ update ∈ res.updates, is_in_subtree height_m1 (path * 2) update.1)
    (h_right_update: ∃ update ∈ res.updates, is_in_subtree height_m1 (path * 2 + 1) update.1) :
    ∃ res₀ res₁ : TraverseResult, res = res₀.add res₁ ∧
      res₀.valid crypto (path * 2) ref.left_subtree ∧
      res₁.valid crypto (path * 2 + 1) ref.right_subtree := by
  cases h_valid using TraverseResult.valid.elim_succ
  case Binary res₀ res₁ h_eq h_valid₀ h_valid₁ =>
    exact ⟨res₀, res₁, h_eq, h_valid₀, h_valid₁⟩
  case Edge res₀ dir h_res h_valid =>
    have h_res_updates : res.updates = res₀.updates := by cases h_res; simp_all
    fin_cases dir
    case «0» =>
      obtain ⟨update, h_update, h_in_subtree⟩ := h_right_update
      rw [h_res_updates] at h_update
      have := (h_valid.implies_updates).2 update h_update
      exact absurd (is_in_subtree.inj_path this h_in_subtree) (by simp)
    case «1» =>
      obtain ⟨update, h_update, h_in_subtree⟩ := h_left_update
      rw [h_res_updates] at h_update
      have := (h_valid.implies_updates).2 update h_update
      exact absurd (is_in_subtree.inj_path this h_in_subtree) (by simp)
  case Descent res₀ length_m2 word h_res h_length h_valid h_empty =>
    -- All updates of res₀ live in a single sub-subtree (determined by the top bit
    -- of `word`), so they can't span both `path * 2` and `path * 2 + 1`.
    exfalso
    have h_res_updates : res.updates = res₀.updates := by rw [h_res]; rfl

    have h_height_eq : height_m1 + 1 - (length_m2 + 2) = height_m1 - (length_m2 + 1) :=
      by omega

    by_cases h_word : (word: ℕ) < 2 ^ (length_m2 + 1)
    case pos =>
      have ⟨update, h_update, h_update_right⟩ := h_res_updates ▸ h_right_update
      have h_deep := h_height_eq ▸ (implies_updates h_valid).2 update h_update
      have h_update_left : is_in_subtree height_m1 (path * 2) update.1 := by
        exact is_in_subtree.height_add_left (length_m1 := length_m2 + 1)
          (word := ⟨word, h_word⟩) (by omega) h_deep
      exact absurd (is_in_subtree.inj_path h_update_left h_update_right) (by simp)
    case neg =>
      have ⟨update, h_update, h_update_left⟩ := h_res_updates ▸ h_left_update
      have h_deep := h_height_eq ▸ (implies_updates h_valid).2 update h_update
      have h_word_ge : 2 ^ (length_m2 + 1) ≤ (word: ℕ) := Nat.not_lt.mp h_word
      have h_update_right : is_in_subtree height_m1 (path * 2 + 1) update.1 := by
        exact is_in_subtree.height_add_right (length_m1 := length_m2 + 1)
          (by omega) h_word_ge word.2 h_deep
      exact absurd (is_in_subtree.inj_path h_update_left h_update_right) (by simp)

-- If all updates sit in a single subtree and the first sibling is ≤ max_height
-- (so it cannot be a node hash), then `res` must be in the Descent disjunct.
theorem TraverseResult.valid.descent_elim
    {crypto: Crypto} {height_m1 path: ℕ} {res: TraverseResult}
    (h_height: height_m1 ≥ 1)
    {ref: PatriciaTree (height_m1 + 1)}
    (h_valid: res.valid crypto path ref)
    (length_m2: ℕ)
    (h_first_sibling: ∀ head, res.siblings.head? = some head → head = (1, length_m2 + 2))
    (h_updates_in_subtree:
      ∃ dir: Fin 2, ∀ update ∈ res.updates, is_in_subtree height_m1 (path * 2 + dir) update.1) :
    ∃ (res₀: TraverseResult) (word: Fin (2 ^ (length_m2 + 2))),
      res = (TraverseResult.descent (length_m2 + 2)).add res₀ ∧
      res₀.valid crypto (path * 2 ^ (length_m2 + 2) + word) (ref.descend word) ∧
      (∀ word' : Fin (2 ^ (length_m2 + 2)), word ≠ word' → ref.descend word' = .Empty _) := by
  cases h_valid using TraverseResult.valid.elim_succ
  case Binary res₀ res₁ h_res h_valid₀ h_valid₁ =>
    exfalso
    replace ⟨dir, h_updates_in_subtree⟩ := h_updates_in_subtree

    -- Binary case: updates span both subtrees, contradicting `h_all_in_subtree`.
    subst res
    have ⟨h_res₀_updates_ne, h_in_subtree₀⟩ := implies_updates h_valid₀
    have ⟨h_res₁_updates_ne, h_in_subtree₁⟩ := implies_updates h_valid₁
    fin_cases dir
    · obtain ⟨update, h_update_in_res₁⟩ := List.exists_mem_of_ne_nil _ h_res₁_updates_ne
      have h_update_in_parent : update ∈ (res₀.add res₁).updates := by simp [h_update_in_res₁]
      have h_in_left := h_updates_in_subtree update h_update_in_parent
      have h_in_right := h_in_subtree₁ update h_update_in_res₁
      simp at h_in_left
      exact absurd (is_in_subtree.inj_path h_in_left h_in_right) (by simp)
    · obtain ⟨update, h_update_in_res₀⟩ := List.exists_mem_of_ne_nil _ h_res₀_updates_ne
      have h_update_in_parent : update ∈ (res₀.add res₁).updates := by simp [h_update_in_res₀]
      have h_in_right := h_updates_in_subtree update h_update_in_parent
      have h_in_left := h_in_subtree₀ update h_update_in_res₀
      exact absurd (is_in_subtree.inj_path h_in_left h_in_right) (by simp)
  case Edge res₀ dir h_res h_valid =>
    exfalso
    subst res
    simp only [List.singleton_append, List.head?_cons, Option.some_inj] at h_first_sibling
    unfold PatriciaTree.hash PatriciaNode.node_hash at h_first_sibling
    split at h_first_sibling
    · rename_i h_eq
      have : height_m1 = 0 := (PatriciaNode.valid_leaf (h_eq ▸ (ref.subtree (1 - dir)).valid)).1
      simp [this] at h_height
    · simp at h_first_sibling
    · simp at h_first_sibling
    · simp at h_first_sibling
  case Descent res₀ length_m2' word h_res h_length h_valid h_empty =>
    subst res
    simp only [List.singleton_append, List.head?_cons] at h_first_sibling
    have : length_m2' = length_m2 := by simp at h_first_sibling; simp [h_first_sibling]
    subst length_m2'
    exact ⟨res₀, word, rfl, h_valid, h_empty⟩

-- Variant of `descent_elim` where the descent `word` is given by the caller (instead of being
-- existentially produced) and updates are assumed to lie in that specific descent subtree.
theorem TraverseResult.valid.descent_elim'
    {crypto: Crypto} {height_m1 path: ℕ} {res: TraverseResult}
    (h_height: height_m1 ≥ 1 ∧ height_m1 + 1 ≤ crypto.max_height)
    {ref: PatriciaTree (height_m1 + 1)}
    (h_valid: res.valid crypto path ref)
    (length_m2: ℕ)
    (h_first_sibling: ∀ head, res.siblings.head? = some head → head = (1, length_m2 + 2))
    (h_length: length_m2 + 2 ≤ height_m1 + 1)
    (word: Fin (2 ^ (length_m2 + 2))) :
    let height := height_m1 + 1
    let length := length_m2 + 2
    (∀ update ∈ res.updates, is_in_subtree (height - length) (path * 2 ^ length + word) update.1) →
    ∃ (res₀: TraverseResult),
      res = (TraverseResult.descent length).add res₀ ∧
      res₀.valid crypto (path * 2 ^ length + word) (ref.descend word) ∧
      (∀ word' : Fin (2 ^ (length_m2 + 2)), word ≠ word' → ref.descend word' = .Empty _) := by
  simp only
  intro h_updates_in_subtree
  have ⟨res₀, word', h_res, h_valid', h_empty⟩ := descent_elim h_height.1 h_valid length_m2 h_first_sibling (by
    by_cases h_word : (word: ℕ) < 2 ^ (length_m2 + 1)
    case pos =>
      use 0
      intro update h_update
      have h_deep := h_updates_in_subtree update h_update
      rw [show height_m1 + 1 - (length_m2 + 2) = height_m1 - (length_m2 + 1) from by omega]
        at h_deep
      simpa using is_in_subtree.height_add_left (length_m1 := length_m2 + 1)
        (word := ⟨word, h_word⟩) (by omega) h_deep
    case neg =>
      use 1
      intro update h_update
      have h_deep := h_updates_in_subtree update h_update
      rw [show height_m1 + 1 - (length_m2 + 2) = height_m1 - (length_m2 + 1) from by omega]
        at h_deep
      exact is_in_subtree.height_add_right (length_m1 := length_m2 + 1)
        (by omega) (Nat.not_lt.1 h_word) word.2 h_deep
  )
  subst res
  have : word = word' := by
    have h_res₀_ne := (implies_updates h_valid).1
    have ⟨update, h_update_in⟩ := List.exists_mem_of_ne_nil _ h_res₀_ne
    have h_path_eq := is_in_subtree.inj_path
      (h_updates_in_subtree update h_update_in)
      ((implies_updates h_valid').2 update h_update_in)
    omega
  subst word'
  exact ⟨res₀, rfl, h_valid', h_empty⟩

-- Given res.valid with updates all in a single shallow subtree and the first sibling
-- equal to the hash of the OTHER shallow subtree, `res` must be in the Edge disjunct.
theorem TraverseResult.valid.edge_elim
    {crypto: Crypto} {height_m1 path: ℕ} {res: TraverseResult}
    {ref: PatriciaTree (height_m1 + 1)}
    (h_valid: res.valid crypto path ref)
    (dir: Fin 2)
    (h_first_sibling: ∀ head, res.siblings.head? = some head → head.1 = 0)
    (h_updates_in_subtree: ∀ update ∈ res.updates, is_in_subtree height_m1 (path * 2 + dir) update.1) :
    ∃ (res₀: TraverseResult),
      res = (TraverseResult.sibling ((ref.subtree (1 - dir)).hash crypto)).add res₀ ∧
      res₀.valid crypto (path * 2 + dir) (ref.subtree dir) := by
  cases h_valid using TraverseResult.valid.elim_succ
  case Binary res₀ res₁ h_res h_valid₀ h_valid₁ =>
    -- Binary: updates span both shallows, contradicts h_updates_in_subtree.
    exfalso
    subst res
    have ⟨h_res₀_ne, h_res₀_in⟩ := implies_updates h_valid₀
    have ⟨h_res₁_ne, h_res₁_in⟩ := implies_updates h_valid₁
    fin_cases dir
    · have ⟨update, h_update⟩ := List.exists_mem_of_ne_nil _ h_res₁_ne
      have h_update' : update ∈ (res₀.add res₁).updates := by simp [h_update]
      have h_left := h_updates_in_subtree update h_update'
      have h_right := h_res₁_in update h_update
      simp at h_left
      exact absurd (is_in_subtree.inj_path h_left h_right) (by simp)
    · have ⟨update, h_update⟩ := List.exists_mem_of_ne_nil _ h_res₀_ne
      have h_update' : update ∈ (res₀.add res₁).updates := by simp [h_update]
      have h_right := h_updates_in_subtree update h_update'
      have h_left := h_res₀_in update h_update
      exact absurd (is_in_subtree.inj_path h_left h_right) (by simp)

  case Edge res₀ dir' h_res h_valid =>
    -- Edge: force dir = dir' from updates being in one subtree.
    subst res
    suffices h_dir : dir = dir' from by
      subst dir'
      exact ⟨res₀, rfl, h_valid⟩

    have ⟨update, h_update⟩ := List.exists_mem_of_ne_nil _ (implies_updates h_valid).1
    have h_update' :
        update ∈ ((TraverseResult.sibling ((ref.subtree (1 - dir')).hash crypto)).add res₀).updates :=
      by simp [h_update]
    have h_dir := h_updates_in_subtree update h_update
    have h_dir' := (implies_updates h_valid).2 update h_update
    have := is_in_subtree.inj_path h_dir h_dir'
    omega

  case Descent res₀ length_m2 word h_res h_length h_valid h_empty =>
    subst res
    simp at h_first_sibling

-- `valid` only depends on the update *keys* (and siblings), not the values:
-- replacing the values in updates with arbitrary ones preserves validity.
theorem TraverseResult.valid.change_update_values {crypto: Crypto} {height: ℕ} {path: ℕ} {res₀ res₁: TraverseResult} {ref: PatriciaTree height}
    (h_valid: res₀.valid crypto path ref)
    (h_same_siblings: res₀.siblings = res₁.siblings)
    (h_same_update_keys: res₀.updates.map Prod.fst = res₁.updates.map Prod.fst) :
    res₁.valid crypto path ref := by
  induction height using Nat.strong_induction_on generalizing path res₀ res₁
  rename_i height ih
  cases height
  case zero =>
    unfold valid at h_valid ⊢
    obtain ⟨val, rfl⟩ := h_valid
    obtain ⟨updates, siblings⟩ := res₁
    simp only at h_same_siblings h_same_update_keys
    cases updates
    case nil => simp at h_same_update_keys
    case cons u rest =>
      cases rest
      case cons => simp at h_same_update_keys
      case nil =>
        simp only [List.map_cons, List.map_nil, List.cons.injEq, and_true] at h_same_update_keys
        exact ⟨u.2, by ext <;> simp [h_same_update_keys, h_same_siblings]⟩
  case succ height_m1 =>
    cases h_valid using TraverseResult.valid.elim_succ
    case Binary res_left res_right h_res h_valid₀ h_valid₁ =>
      obtain ⟨updates, siblings⟩ := res₁
      have : res_left.updates.length = (res_left.updates.map Prod.fst).length := by simp
      subst res₀
      simp only [List.map_append] at h_same_update_keys

      apply mk_both
        (res₀ := { updates := updates.take res_left.updates.length, siblings := res_left.siblings })
        (res₁ := { updates := updates.drop res_left.updates.length, siblings := res_right.siblings })
      · simp only at h_same_siblings
        subst siblings
        simp
      · apply ih _ (by simp) h_valid₀ (by rfl)
        simp only [List.map_take, ←h_same_update_keys, this, List.take_append_length]
      · apply ih _ (by simp) h_valid₁ (by rfl)
        simp only [List.map_drop, ←h_same_update_keys, this, List.drop_append_length]
    case Edge res' dir h_res h_valid =>
      replace h_same_update_keys : (res'.updates).map Prod.fst = (res₁.updates).map Prod.fst := by
        subst res₀
        try simp only [List.nil_append] at h_same_update_keys
        exact h_same_update_keys
      apply mk_edge dir
       (res₀ := { updates := res₁.updates, siblings := res'.siblings })
      · subst res₀
        ext <;> simp [←h_same_siblings]
      · exact ih _ (by simp) h_valid rfl h_same_update_keys
    case Descent res' length_m2 word h_res h_length h_valid h_empty =>
      replace h_same_update_keys : res'.updates.map Prod.fst = res₁.updates.map Prod.fst := by
        subst res₀
        try simp only [List.nil_append] at h_same_update_keys
        exact h_same_update_keys
      have h_res₁_eq : res₁ = (TraverseResult.descent (length_m2 + 2)).add
          { updates := res₁.updates, siblings := res'.siblings } := by
        subst res₀
        ext <;> simp [←h_same_siblings]
      rw [h_res₁_eq]
      apply mk_descent length_m2 word h_length (by rfl) _ h_empty
      exact ih _ (by omega) h_valid rfl h_same_update_keys

------

-- Uniqueness of valid siblings under prefix relation: two valid results at the same
-- (crypto, path, ref) with equal updates and one's siblings being a prefix of the other's
-- (in the append-equality sense) must have equal siblings.  (For the reverse prefix
-- direction, apply with swapped res₀ and res₁.)
theorem TraverseResult.valid.eq_of_prefix
    {crypto: Crypto} {height: ℕ} {path: ℕ} {res₀ res₁: TraverseResult}
    {ref: PatriciaTree height}
    (h_height_le: height ≤ crypto.max_height)
    (h_valid₀: res₀.valid crypto path ref)
    (h_valid₁: res₁.valid crypto path ref)
    (h_updates: res₀.updates = res₁.updates)
    (h_prefix: res₀.siblings <+: res₁.siblings) :
    res₀ = res₁ := by
  induction height using Nat.strong_induction_on generalizing path res₀ res₁
  rename_i height ih
  cases height
  case zero =>
    unfold valid at h_valid₀ h_valid₁
    obtain ⟨val₀, h₀⟩ := h_valid₀
    obtain ⟨val₁, h₁⟩ := h_valid₁
    subst res₀ res₁
    apply TraverseResult.ext h_updates (by rfl)

  case succ height_m1 =>
    -- Suffices to prove res₀.siblings = res₁.siblings.
    apply TraverseResult.ext h_updates

    cases h_valid₀ using TraverseResult.valid.elim_succ
    case Binary res₀₀ res₀₁ h_res₀ h_valid₀₀ h_valid₀₁ =>
      subst res₀
      -- res₁ is also binary.
      have ⟨res₁₀, res₁₁, h_res₁, h_valid₁₀, h_valid₁₁⟩ :=
        TraverseResult.valid.binary_elim h_valid₁ (by
          have ⟨update, h_update⟩ :=
            List.exists_mem_of_ne_nil _ (implies_updates h_valid₀₀).1
          exact ⟨update, by rw [←h_updates]; simp [h_update],
            (implies_updates h_valid₀₀).2 update h_update⟩
        ) (by
          have ⟨update, h_update⟩ :=
            List.exists_mem_of_ne_nil _ (implies_updates h_valid₀₁).1
          exact ⟨update, by rw [←h_updates]; simp [h_update],
            (implies_updates h_valid₀₁).2 update h_update⟩
        )
      subst res₁

      -- Updates split.
      have h_left_updates_eq : res₀₀.updates = res₁₀.updates :=
        is_in_subtree.append_eq h_updates
          (implies_updates h_valid₀₀).2 (implies_updates h_valid₀₁).2
          (implies_updates h_valid₁₀).2 (implies_updates h_valid₁₁).2
      have h_right_updates_eq : res₀₁.updates = res₁₁.updates := by
        apply List.append_cancel_left
        simp only [h_left_updates_eq] at h_updates
        exact h_updates

      -- Siblings split.
      obtain ⟨siblings', h_siblings_split⟩ := h_prefix
      simp only [List.append_assoc] at h_siblings_split
      rcases List.append_eq_append_iff.mp h_siblings_split with
        ⟨k', h_left_forward, h_right_forward⟩ |
        ⟨k', h_left_backward, h_right_backward⟩
      · -- Case: res₁₀.siblings = res₀₀.siblings ++ k'.
        have h_left_eq : res₀₀ = res₁₀ :=
          ih _ (by omega) (by omega) h_valid₀₀ h_valid₁₀ h_left_updates_eq
            ⟨k', h_left_forward.symm⟩
        have h_self : res₀₀.siblings ++ k' = res₀₀.siblings :=
          h_left_forward.symm.trans (congrArg _ h_left_eq).symm
        have h_k'_nil : k' = [] := by simpa using h_self
        subst k'
        simp only [List.nil_append] at h_right_forward
        have h_right_eq : res₀₁ = res₁₁ :=
          ih _ (by omega) (by omega) h_valid₀₁ h_valid₁₁ h_right_updates_eq
            ⟨siblings', h_right_forward⟩
        simp [h_left_eq, h_right_eq]
      · -- Case: res₀₀.siblings = res₁₀.siblings ++ k'.
        have h_left_eq : res₁₀ = res₀₀ :=
          ih _ (by omega) (by omega) h_valid₁₀ h_valid₀₀ h_left_updates_eq.symm
            ⟨k', h_left_backward.symm⟩
        have h_self : res₁₀.siblings ++ k' = res₁₀.siblings :=
          h_left_backward.symm.trans (congrArg _ h_left_eq).symm
        have h_k'_nil : k' = [] := by simpa using h_self
        subst k'
        simp only [List.nil_append] at h_right_backward
        have h_right_eq : res₀₁ = res₁₁ :=
          ih _ (by omega) (by omega) h_valid₀₁ h_valid₁₁ h_right_updates_eq
            ⟨siblings', h_right_backward.symm⟩
        simp [h_left_eq, h_right_eq]

    case Edge res₀' dir₀ h_res₀'_eq h_res₀'_valid =>
      subst res₀
      have ⟨s, h_s⟩ := h_prefix
      simp only [List.nil_append] at h_updates

      -- Show res₁ is also edge with the same direction.
      have ⟨res₁', h_res₁, h_res₁'_valid⟩ :=
        valid.edge_elim h_valid₁ dir₀ (by simp [←h_s])
          (h_updates ▸ (valid.implies_updates h_res₀'_valid).2)
      subst res₁

      simp only [List.cons_append, List.nil_append, List.cons.injEq, true_and] at h_s
      simp [ih _ (by omega) (by omega) h_res₀'_valid h_res₁'_valid h_updates ⟨s, h_s⟩]

    case Descent res₀₀ length_m2₀ word₀ h_res₀ h_length₀ h_valid₀₀ h_empty₀₀ =>
      subst res₀

      have ⟨s, h_s⟩ := h_prefix
      simp only [List.nil_append] at h_updates

      -- First show res₁ is also descent.
      have ⟨res₁₀, h_res₁, h_valid₁₀, h_empty₁₀⟩ :=
        valid.descent_elim' (by omega) (ref:=ref) h_valid₁ length_m2₀
          (by rw [←h_s, List.head?_append]; simp) (by omega) word₀
          (h_updates ▸ (valid.implies_updates h_valid₀₀).2)
      subst res₁

      simp only [List.cons_append, List.nil_append, List.cons.injEq, true_and] at h_s

      simp [ih _ (by omega) (by omega) h_valid₀₀ h_valid₁₀ h_updates ⟨s, h_s⟩]
