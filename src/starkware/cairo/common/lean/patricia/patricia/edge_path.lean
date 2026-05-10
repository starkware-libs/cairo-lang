import patricia.is_in_subtree

structure EdgePath where
  (length_m1: ℕ)
  (path: Fin (2 ^ ((length_m1: ℕ) + 1)))
deriving Repr, DecidableEq

@[ext]
theorem EdgePath.ext (path₀ path₁: EdgePath)
    (h_length: path₀.length_m1 = path₁.length_m1)
    (h_path: (path₀.path: ℕ) = path₁.path) :
    path₀ = path₁ := by
  cases path₀
  cases path₁
  simp only at h_length h_path
  rename_i length_m1₀ path₀ length_m1₁ path₁
  subst length_m1₀
  simp only [mk.injEq, heq_eq_eq, true_and]
  ext
  exact h_path

abbrev EdgePath.length (path: EdgePath) : ℕ := path.length_m1 + 1

abbrev EdgePath.mk_len1 (dir: Fin 2) : EdgePath :=
  { length_m1 := 0, path := ⟨dir, by simp [dir.prop]⟩ }

abbrev EdgePath.extend (path: EdgePath) (dir: Fin 2) : EdgePath :=
  {
    length_m1 := path.length,
    path := ⟨path.path + dir * 2 ^ path.length, by
      unfold EdgePath.length
      exact calc (path.path: ℕ) + dir * 2 ^ (path.length)
        _ < 2 ^ (path.length) + dir * 2 ^ (path.length) := by simp
        _ = 2 ^ (path.length) * (1 + dir) := by ring
        _ ≤ 2 ^ (path.length) * 2 := by apply Nat.mul_le_mul_left; omega
        _ = _ := by simp [Nat.pow_succ]
    ⟩,
  }

-- Every path is either a length-1 path `mk_len1 dir`, or extends a shorter `path'` by `dir`.
theorem EdgePath.cases {path: EdgePath} :
    ∃ dir: Fin 2, (
      path = EdgePath.mk_len1 dir ∨
      ∃ path': EdgePath, path = path'.extend dir
    ) := by
  cases h_path_len: path.length_m1
  case zero =>
    use ⟨path.path, ?_⟩
    · apply Or.inl
      ext
      · simp [*]
      · rfl
    · have := path.path.2
      conv at this => rhs; rw [h_path_len]
      exact this
  case succ path_len_m2 =>
    by_cases h_path: (path.path: ℕ) < 2 ^ (path_len_m2 + 1)
    case pos =>
      use 0
      apply Or.inr
      use ⟨path_len_m2, ⟨path.path, h_path⟩⟩
      ext
      · conv => lhs; rw [h_path_len]
      · simp
    case neg =>
      use 1
      apply Or.inr
      use ⟨path_len_m2, ⟨path.path - 2 ^ (path_len_m2 + 1), by rw [←h_path_len]; omega⟩⟩
      ext
      · conv => lhs; rw [h_path_len]
      · simp only [EdgePath.length, Fin.isValue, Fin.coe_ofNat_eq_mod, Nat.mod_succ, one_mul]
        simp only [Nat.sub_add_cancel (Nat.not_lt.1 h_path)]

-- Variant of `cases` that fixes the first-step direction `dir`,
-- given that `path` lies in `dir`'s subtree.
theorem EdgePath.cases' (dir: Fin 2) {path: EdgePath}
    (h_in_subtree: is_in_subtree path.length_m1 dir path.path):
    (
      path = EdgePath.mk_len1 dir ∨
      ∃ path': EdgePath, path = path'.extend dir
    ) := by
  rcases path.cases with ⟨dir', h | ⟨path', h⟩⟩
  · apply Or.inl
    have : dir = dir' := by
      rw [h] at h_in_subtree
      exact Fin.ext (is_in_subtree.height0.mp h_in_subtree).symm
    exact this ▸ h
  · obtain ⟨path', -⟩ := h
    apply Or.inr
    use path'
    have : dir = dir' := by
      exact Fin.ext <| is_in_subtree.inj_path h_in_subtree (by apply is_in_subtree.mk)
    rw [this]
