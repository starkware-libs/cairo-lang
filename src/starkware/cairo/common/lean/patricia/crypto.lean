import Mathlib.Data.Nat.Basic
import Mathlib.Tactic

structure Crypto where
  hash: ℕ → ℕ → ℕ
  max_height: ℕ
  h_max_height: max_height > 1
  h_hash: a ≤ max_height → b ≤ max_height → hash x y + a = hash z w + b → x = z ∧ y = w ∧ a = b
  hash_ne_zero: ∀ x y a b, a ≤ max_height → b ≤ max_height → hash x y + a ≠ b

theorem Crypto.h_hash' {crypto: Crypto} {x y z w: ℕ}
    (h: crypto.hash x y = crypto.hash z w) :
    x = z ∧ y = w := by
  have : crypto.hash x y + 0 = crypto.hash z w + 0 := h
  simp [crypto.h_hash (by omega) (by omega) this]

theorem Crypto.hash_ne_zero' {crypto: Crypto} (x y: ℕ) :
    crypto.hash x y ≠ 0 :=
  crypto.hash_ne_zero x y 0 0 (by omega) (by omega)

theorem Crypto.hash_gt {crypto: Crypto} (x y a: ℕ) :
    crypto.hash x y + a > crypto.max_height := by
  by_contra h
  have := crypto.hash_ne_zero x y a (crypto.hash x y + a) (by omega) (Nat.not_lt.1 h)
  simp at this
