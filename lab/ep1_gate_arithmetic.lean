import Std

/-!
Offline arithmetic and decision-table specifications for EP-1.

The HDI inputs represent comparisons already made by Python. These proofs cover
branch priority and publication, leaving floating-point arithmetic, bootstrap
sampling, and correspondence to Python for separate verification. The ledger
statements use the local 2026-11-20 price snapshot and exact natural arithmetic.
They do not establish runtime enforcement, live pricing, or billing.
-/

namespace EP1Gate

inductive HDIStatus where
  | noRows
  | codeWorse
  | unresolved
  | interpretable
  deriving DecidableEq

structure HDIChecks where
  hasRows : Bool
  upperNegative : Bool
  lowerPositive : Bool
  belowAdjustedMargin : Bool
  denominatorNearZero : Bool
  hasRatios : Bool

def hdiStatus (checks : HDIChecks) : HDIStatus :=
  if !checks.hasRows then .noRows
  else if checks.upperNegative then .codeWorse
  else if !checks.lowerPositive || checks.belowAdjustedMargin ||
      checks.denominatorNearZero || !checks.hasRatios then .unresolved
  else .interpretable

theorem hdiDecisionTable (checks : HDIChecks) :
    (hdiStatus checks = .noRows ↔ checks.hasRows = false) ∧
    (hdiStatus checks = .codeWorse ↔
      checks.hasRows = true ∧ checks.upperNegative = true) ∧
    (hdiStatus checks = .unresolved ↔
      checks.hasRows = true ∧ checks.upperNegative = false ∧
      (checks.lowerPositive = false ∨ checks.belowAdjustedMargin = true ∨
        checks.denominatorNearZero = true ∨ checks.hasRatios = false)) ∧
    (hdiStatus checks = .interpretable ↔
      checks.hasRows = true ∧ checks.upperNegative = false ∧
      checks.lowerPositive = true ∧ checks.belowAdjustedMargin = false ∧
      checks.denominatorNearZero = false ∧ checks.hasRatios = true) := by
  rcases checks with ⟨rows, upper, lower, margin, near, ratios⟩
  cases rows <;> cases upper <;> cases lower <;>
    cases margin <;> cases near <;> cases ratios <;> decide

def publishHDI (checks : HDIChecks) (completeSets : Nat) : Bool :=
  decide (12 ≤ completeSets) && decide (hdiStatus checks = .interpretable)

theorem publishHDI_iff (checks : HDIChecks) (completeSets : Nat) :
    publishHDI checks completeSets = true ↔
      12 ≤ completeSets ∧ hdiStatus checks = .interpretable := by
  simp [publishHDI]

-- Costs are in picodollars. The short-context input, 5-minute cache write,
-- 1-hour cache write, and output rates are 100000, 125000, 200000, and 500000
-- picodollars per token. Reservation uses the largest applicable input rate.
def reservedCost (input output : Nat) : Nat :=
  input * max 100000 (max 125000 200000) + output * 500000

def reservedTokens (regularCalls : Nat) : Nat :=
  90000 + 300 + regularCalls * (2000 + 300)

def batchCost (regularCalls : Nat) : Nat :=
  reservedCost 90000 300 + regularCalls * reservedCost 2000 300

theorem canaryReservation :
    reservedCost 90000 300 = 18150000000 ∧
    reservedCost 90000 300 ≤ 50000000000 := by
  decide

theorem regularReservation : reservedCost 2000 300 = 550000000 := by
  decide

theorem scheduleWithReruns :
    1 + (3 * 20 * 8 + 16 : Nat) = 497 ∧
    reservedTokens (3 * 20 * 8 + 16) = 1231100 ∧
    batchCost (3 * 20 * 8 + 16) = 290950000000 := by
  decide

theorem maximumCallBudget :
    1 + (499 : Nat) = 500 ∧
    reservedTokens 499 = 1238000 ∧
    1238000 ≤ (1250000 : Nat) ∧
    batchCost 499 = 292600000000 ∧
    292600000000 ≤ (5000000000000 : Nat) := by
  decide

#print axioms hdiDecisionTable
#print axioms publishHDI_iff
#print axioms canaryReservation
#print axioms regularReservation
#print axioms scheduleWithReruns
#print axioms maximumCallBudget

end EP1Gate
