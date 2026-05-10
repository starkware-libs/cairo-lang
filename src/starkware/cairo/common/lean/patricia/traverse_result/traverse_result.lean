import Mathlib.Data.Nat.Basic
import Mathlib.Tactic

structure TraverseResult where
  (updates: List (ℕ × ℕ))
  (siblings: List (ℕ × ℕ))
deriving Repr, DecidableEq

def TraverseResult.Empty : TraverseResult := ⟨[], []⟩

abbrev TraverseResult.sibling (sibling: ℕ) : TraverseResult :=
  { updates := [], siblings := [(0, sibling)] }

abbrev TraverseResult.descent (length: ℕ) : TraverseResult :=
  { updates := [], siblings := [(1, length)] }

abbrev TraverseResult.update (update: ℕ × ℕ) : TraverseResult :=
  { updates := [update], siblings := [] }

abbrev TraverseResult.add (res res': TraverseResult) : TraverseResult :=
  {
    updates := res.updates ++ res'.updates,
    siblings := res.siblings ++ res'.siblings,
  }

theorem TraverseResult.empty_add (res: TraverseResult) :
    (TraverseResult.Empty).add res = res := by rfl

theorem TraverseResult.add_empty (res: TraverseResult) :
    res.add .Empty = res := by simp [TraverseResult.add, TraverseResult.Empty]

@[ext]
theorem TraverseResult.ext {res res': TraverseResult}
    (h_updates: res.updates = res'.updates)
    (h_siblings: res.siblings = res'.siblings) :
    res = res' := by
  cases res
  cases res'
  simp only at *
  simp [h_updates, h_siblings]
