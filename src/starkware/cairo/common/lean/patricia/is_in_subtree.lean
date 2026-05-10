import Mathlib.Data.Nat.Basic
import Mathlib.Tactic

def is_in_subtree (height path leaf: ℕ) : Prop :=
  leaf ≥ path * 2 ^ height ∧ leaf < (path + 1) * 2 ^ height

instance (height path: ℕ) : DecidablePred (is_in_subtree height path) := λ n ↦ by
  unfold is_in_subtree
  infer_instance

theorem is_in_subtree.mk {height: ℕ} (path: ℕ) (i: Fin (2 ^ height)) :
    is_in_subtree height path (i + path * 2^height) := by
  simp [is_in_subtree, add_mul]
  omega

theorem is_in_subtree.sub_offset_lt {height path leaf: ℕ}
    (h: is_in_subtree height path leaf) :
    leaf - path * 2 ^ height < 2 ^ height := by
  have ⟨h₀, h₁⟩ := h
  apply (Nat.sub_lt_iff_lt_add' h₀).2
  rw [add_mul, one_mul] at h₁
  exact h₁

def is_in_subtree.relative {height path leaf: ℕ}
    (h: is_in_subtree height path leaf) : Fin (2 ^ height) :=
  ⟨leaf - path * 2 ^ height, h.sub_offset_lt⟩

theorem is_in_subtree.height0 {path leaf: ℕ} :
    is_in_subtree 0 path leaf ↔ leaf = path := by
  simp [is_in_subtree]
  omega

theorem is_in_subtree.height_add1 {height_m1 path leaf: ℕ} {dir: Fin 2}
    (h: is_in_subtree height_m1 (path * 2 + dir) leaf) :
    is_in_subtree (height_m1 + 1) path leaf := by
  simp only [is_in_subtree] at *
  constructor
  · calc leaf
      _ ≥ (path * 2 + dir) * 2 ^ height_m1 := h.1
      _ ≥ (path * 2) * 2 ^ height_m1 := Nat.mul_le_mul_right _ (by simp)
      _ = path * 2 ^ (height_m1 + 1) := by rw [Nat.pow_succ']; ring
  · calc leaf
      _ < (path * 2 + dir + 1) * 2 ^ height_m1 := h.2
      _ ≤ (path * 2 + 1 + 1) * 2 ^ height_m1 := Nat.mul_le_mul_right _ (by omega)
      _ = (path + 1) * 2 ^ (height_m1 + 1) := by ring

theorem is_in_subtree.height_add1' {height_m1 path leaf: ℕ} :
    is_in_subtree (height_m1 + 1) path leaf ↔
    (
      is_in_subtree height_m1 (path * 2) leaf ∨
      is_in_subtree height_m1 (path * 2 + 1) leaf
    ) := by
  constructor
  · intro h
    simp only [is_in_subtree] at *
    by_cases h' : leaf < (2 * path + 1) * 2 ^ height_m1
    case pos =>
      apply Or.inl
      rw [Nat.pow_succ] at h
      ring_nf at h h' ⊢
      exact ⟨h.1, h'⟩
    case neg =>
      apply Or.inr
      ring_nf at h h' ⊢
      exact ⟨by omega, h.2⟩
  · intro h
    cases h
    case inl h =>
      apply height_add1 (dir:=0)
      simp [h]
    case inr h =>
      apply height_add1 (dir:=1)
      simp [h]

theorem is_in_subtree.height_add {height path leaf length: ℕ} {word: Fin (2 ^ length)}
    (length_le_height: length ≤ height)
    (h: is_in_subtree (height - length) (path * 2 ^ length + word) leaf) :
    is_in_subtree height path leaf := by
  induction length
  case zero => simp at h; exact h
  case succ length_m1 ih =>
    cases height
    case zero => contradiction
    case succ height_m1 =>
      simp only [add_le_add_iff_right] at length_le_height
      apply ih (word := ⟨word / 2, by omega⟩) (by omega)
      rw [Nat.sub_add_comm length_le_height]
      apply is_in_subtree.height_add1 (dir := ⟨word % 2, by omega⟩)
      rw [←Nat.mod_add_div (m := word) (k := 2)] at h
      ring_nf at h ⊢
      rw [(by omega: 1 + height_m1 - (1 + length_m1) = height_m1 - length_m1)] at h
      exact h

-- Transitivity for `is_in_subtree`: if `leaf` lies in `p₁`'s subtree at depth `height₀`, and
-- `p₁` itself lies in `p₂`'s subtree at the relative depth `height₁ - height₀`,
-- then `leaf` lies in `p₂`'s subtree at depth `height₁`.
theorem is_in_subtree.trans {height₀ height₁ p₁ p₂ leaf : ℕ}
    (h_le: height₀ ≤ height₁)
    (h₀ : is_in_subtree height₀ p₁ leaf)
    (h₁ : is_in_subtree (height₁ - height₀) p₂ p₁) :
    is_in_subtree height₁ p₂ leaf := by
  apply is_in_subtree.height_add (length_le_height := by omega) (word := h₁.relative)
  rw [show height₁ - (height₁ - height₀) = height₀ from by omega]
  show is_in_subtree height₀ (p₂ * 2 ^ (height₁ - height₀) + (p₁ - p₂ * 2 ^ (height₁ - height₀))) leaf
  rw [Nat.add_sub_cancel' h₁.1]
  exact h₀

theorem is_in_subtree.height_add' {height path leaf: ℕ} (length: ℕ)
    (length_le_height: length ≤ height)
    (h: is_in_subtree height path leaf) :
    ∃ word: Fin (2 ^ length),
      is_in_subtree (height - length) (path * 2 ^ length + word) leaf := by
  induction length
  case zero => use ⟨0, by simp⟩; simp [h]
  case succ length_m1 ih =>
    replace ⟨word', ih⟩ := ih (by omega)
    have : height - length_m1 = height - (length_m1 + 1) + 1 := by omega
    rw [this] at ih
    cases is_in_subtree.height_add1'.1 ih
    case inl h_left =>
      use ⟨word' * 2, by simp [Nat.pow_succ]⟩
      ring_nf at h_left ⊢
      exact h_left
    case inr h_right =>
      use ⟨word' * 2 + 1, by simp [Nat.pow_succ]; omega⟩
      ring_nf at h_right ⊢
      exact h_right

theorem is_in_subtree.height_add_left {height_m1 path leaf length_m1: ℕ} {word: Fin (2 ^ length_m1)}
    (length_le_height: length_m1 ≤ height_m1)
    (h: is_in_subtree (height_m1 - length_m1) (path * 2 ^ (length_m1 + 1) + word) leaf) :
    is_in_subtree height_m1 (path * 2) leaf := by
  apply is_in_subtree.height_add (word:=word) (by omega)
  rw [Nat.pow_succ'] at h
  ring_nf at h ⊢
  exact h

theorem is_in_subtree.height_add_right {height_m1 path leaf length_m1 word: ℕ}
    (length_le_height: length_m1 ≤ height_m1)
    (h_word_ge: 2 ^ length_m1 ≤ word)
    (h_word_lt: word < 2 ^ (length_m1 + 1))
    (h: is_in_subtree (height_m1 - length_m1) (path * 2 ^ (length_m1 + 1) + word) leaf) :
    is_in_subtree height_m1 (path * 2 + 1) leaf := by
  have : 2 ^ length_m1 < 2 ^ (length_m1 + 1) := by omega
  have h_bound : word - 2 ^ length_m1 < 2 ^ length_m1 := by omega
  apply is_in_subtree.height_add (word:=⟨word - 2 ^ length_m1, h_bound⟩) (by omega)
  simp only [add_mul, one_mul, mul_comm 2, mul_assoc _ 2, ←pow_succ, add_assoc,
    Nat.add_sub_cancel' h_word_ge]
  exact h

theorem is_in_subtree.inj_path {height path₀ path₁ leaf: ℕ}
    (h₀: is_in_subtree height path₀ leaf)
    (h₁: is_in_subtree height path₁ leaf) :
    path₀ = path₁ := by
  simp only [is_in_subtree] at *
  by_contra
  wlog h: path₀ ≤ path₁ -- generalizing path₀ path₁
  · exact this (path₀:=path₁) (path₁:=path₀) (h₀:=h₁) (h₁:=h₀) (by omega) (by omega)
  have := calc leaf
    _ < (path₀ + 1) * 2 ^ height := h₀.2
    _ ≤ path₁ * 2 ^ height := Nat.mul_le_mul_right _ (by omega)
    _ ≤ leaf := h₁.1
  simp at this

-- Given two appends that are equal, with each side's elements living in a specific subtree
-- (path*2 for the left pieces, path*2+1 for the right pieces), the left pieces are equal.
theorem is_in_subtree.append_eq
    {xs ys as bs: List (ℕ × ℕ)} {height path: ℕ}
    (h_append: xs ++ ys = as ++ bs)
    (h_xs: ∀ u ∈ xs, is_in_subtree height (path * 2) u.1)
    (h_ys: ∀ u ∈ ys, is_in_subtree height (path * 2 + 1) u.1)
    (h_as: ∀ u ∈ as, is_in_subtree height (path * 2) u.1)
    (h_bs: ∀ u ∈ bs, is_in_subtree height (path * 2 + 1) u.1) :
    xs = as := by
  replace h_xs : ∀ u ∈ xs, decide (is_in_subtree height (path * 2) u.1) = true := by simpa only [decide_eq_true_eq]
  replace h_as : ∀ u ∈ as, decide (is_in_subtree height (path * 2) u.1) = true := by simpa only [decide_eq_true_eq]
  replace h_ys : ∀ u ∈ ys, ¬decide (is_in_subtree height (path * 2) u.1) = true := by
    simp only [decide_eq_true_eq]
    intro u h h_contra
    exact absurd (is_in_subtree.inj_path h_contra (h_ys u h)) (by omega)
  replace h_bs : ∀ u ∈ bs, ¬decide (is_in_subtree height (path * 2) u.1) = true := by
    simp only [decide_eq_true_eq]
    intro u h h_contra
    exact absurd (is_in_subtree.inj_path h_contra (h_bs u h)) (by omega)

  have h_filtered := congrArg
    (List.filter (λ u: ℕ × ℕ ↦ is_in_subtree height (path * 2) u.1)) h_append
  simp only [
    List.filter_append, List.filter_eq_self.2 h_xs, List.filter_eq_self.2 h_as,
    List.filter_eq_nil_iff.2 h_ys, List.filter_eq_nil_iff.2 h_bs,
    List.append_nil] at h_filtered
  exact h_filtered
