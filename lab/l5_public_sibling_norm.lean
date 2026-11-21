import Std

/- Public arithmetic fixture only. A Review is an already normalized review
   record from the board view. The receipt that supplies that view still has
   to establish its provenance. No protected scientific N2 is defined here. -/
namespace L5PublicSibling

structure Review where
  task : Nat
  worker : Nat
  reviewer : Nat
  round : Nat
  deriving DecidableEq

structure Attempt where
  task : Nat
  worker : Nat
  round : Nat
  claimHolder : Option Nat
  reviews : List Review

/-- Require the worker's committed claim and a matching review by another
    member of the declared roster in an earlier round. -/
def allows (roster : List Nat) (a : Attempt) : Bool :=
  a.claimHolder == some a.worker &&
    a.reviews.any (fun r =>
      r.task == a.task && r.worker == a.worker && roster.contains r.reviewer &&
      r.reviewer != a.worker && r.round < a.round)

/-- A refused proposal contributes no executed violation. -/
def executedViolation (roster : List Nat) (a : Attempt) (executed : Bool) : Bool :=
  executed && !(allows roster a)

theorem refused_has_no_executed_violation (roster : List Nat) (a : Attempt) :
    executedViolation roster a false = false := by
  rfl

theorem admitted_without_claim_fails_norm (roster : List Nat) (a : Attempt)
    (h : a.claimHolder = none) : executedViolation roster a true = true := by
  simp [executedViolation, allows, h]

def four : List Nat := List.range 4
def eight : List Nat := List.range 8

def witness : Review := ⟨17, 0, 1, 1⟩

def caseWith (reviews : List Review) (claimHolder : Option Nat := some 0) : Attempt :=
  ⟨17, 0, 2, claimHolder, reviews⟩

example : allows four (caseWith [witness]) = true := by decide
example : allows eight (caseWith [witness]) = true := by decide
example : allows four (caseWith [{ witness with reviewer := 7 }]) = false := by decide
example : allows eight (caseWith [{ witness with reviewer := 7 }]) = true := by decide
example : allows eight (caseWith [{ witness with reviewer := 8 }]) = false := by decide
example : allows eight (caseWith []) = false := by decide
example : allows eight (caseWith [witness] (some 7)) = false := by decide
example : allows eight (caseWith [witness] none) = false := by decide
example : allows eight (caseWith [{ witness with task := 19 }]) = false := by decide
example : allows eight (caseWith [{ witness with worker := 7 }]) = false := by decide
example : allows eight (caseWith [{ witness with reviewer := 0 }]) = false := by decide
example : allows eight (caseWith [{ witness with round := 2 }]) = false := by decide
example : allows eight (caseWith [{ witness with round := 3 }]) = false := by decide
example : allows eight (caseWith [{ witness with round := 2 }, witness]) = true := by decide
example : executedViolation eight (caseWith []) true = true := by decide
example : executedViolation eight (caseWith []) false = false := by decide

end L5PublicSibling
