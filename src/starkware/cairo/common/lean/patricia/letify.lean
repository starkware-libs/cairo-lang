import Lean

/-! # `letify`

A tactic that converts a hypothesis `h : x = e` (where `x` is a free variable
in the local context) into a let-binding `x : T := e`, and clears `h`.

The goal expression is preserved — occurrences of `x` stay as `x`, but `x` is
now let-bound to `e`. Other hypotheses that mention `x` are also rewritten to
reference the new let-bound `x`.
-/

open Lean Meta Elab Tactic

elab "letify " hyp:ident : tactic => do
  let mvarId ← getMainGoal
  let (xName, xType) ← mvarId.withContext do
    let lctx ← getLCtx
    let some hDecl := lctx.findFromUserName? hyp.getId
      | throwError "letify: no such hypothesis '{hyp.getId}'"
    let some (_, lhs, _) := hDecl.type.eq?
      | throwError "letify: expected an equality"
    let some xFV := lhs.fvarId?
      | throwError "letify: lhs must be a free variable"
    pure ((← xFV.getDecl).userName, ← inferType lhs)
  liftMetaTactic1 fun mvarId => mvarId.withContext do
    let some hDecl := (← getLCtx).findFromUserName? hyp.getId | throwError "letify: lost h"
    let some (_, lhs, rhs) := hDecl.type.eq? | throwError "letify: expected equality"
    -- Introduce a fresh let-decl `_letify_tmp := rhs` at the end of the lctx.
    let m1 ← mvarId.define `_letify_tmp xType rhs
    let (xNew, m2) ← m1.intro1
    m2.withContext do
      -- Assert `xFV = xNew`, using `h` as the proof (defeq via zeta on xNew).
      let h'Type ← mkAppM ``Eq #[lhs, .fvar xNew]
      let m3 ← m2.assert `_letify_h h'Type hDecl.toExpr
      let (h'FV, m4) ← m3.intro1
      -- subst eliminates xFV, replacing it with xNew everywhere.
      let (_, m5) ← Lean.Meta.substCore m4 h'FV (symm := false)
      -- Clear the original `h` (its fvar may have changed; look up by name).
      let m6 ← m5.withContext do
        match (← getLCtx).findFromUserName? hyp.getId with
        | some d => m5.tryClear d.fvarId
        | none => pure m5
      -- Rename the let-decl to the original name `x`.
      m6.rename xNew xName

example (y x z: Nat) (h: x = y + 2) (hxz: z = x + 1) : z + x = y + 3 + x := by
  letify h
  rw [hxz]
