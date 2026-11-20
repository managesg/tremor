import Lean.Data.Json
import AllocScore.Basic

/-!
JSON input and output for the `allocscore` executable.

Input: `{"taskset": {"tasks": [{"id": str, "expect": int}, ...], "n_agents": int > 0}, "log": [event]}`,
or a JSON array of such objects (batch). Output: one score object, or an array in the same order.
A malformed task set, a log that is not an array, or input that is not JSON rejects the whole input;
no default score is produced. A malformed event does not reject: it is read as an event with
`malformed = true`, which counts in no field and makes the score `valid = false` (EP1 section 7).

Event reading. Input is the episode action log only (ruling, orchestrator, owner-delegated; team.py
writes every episode-log entry with an `action` key). An event is malformed when it is not an object,
`action` is missing or not a string (so a board-shaped `type` event, a board release included, is
malformed, not a release), `agent`, `task` or `name` is present and neither a string nor null, or
`rejected` is present and neither a bool nor null.
- `kind`: `action`.
- `task`: `task` (string or null). `agent`: string or null. `name`: string or null (missing or null
  reads as `""`).
- `answer`: set only for a JSON integer (no fraction, no exponent below zero); anything else is a
  wrong answer, not malformed input.
- `rejected`: bool or null (missing or null reads as false).
- `done`: true only for JSON `true` at top-level `done`.
-/
namespace AllocScore
open Lean

/-- Value at key `k` (`none` when absent); an error when `j` is not an object. -/
def field? (j : Json) (k : String) : Except String (Option Json) :=
  match j with
  | .obj _ =>
    match j.getObjVal? k with
    | .ok v => .ok (some v)
    | .error _ => .ok none
  | _ => .error s!"expected a JSON object around key '{k}'"

/-- An integer literal. Lean's parser keeps `30.0` as mantissa 300, exponent 1, so it is not one.
shortcut: `3e2` is folded by the parser into the integer 300; no producer of these logs writes
exponents, revisit if one does. -/
def intOf? : Json → Option Int
  | .num n => if n.exponent == 0 then some n.mantissa else none
  | _ => none

theorem intOf?_iff (j : Json) (i : Int) :
    intOf? j = some i ↔ ∃ n : JsonNumber, j = .num n ∧ n.exponent = 0 ∧ n.mantissa = i := by
  cases j with
  | num n =>
    simp only [intOf?, Json.num.injEq, exists_eq_left']
    by_cases h : n.exponent = 0 <;> simp [h]
  | _ => simp [intOf?]

def optStr (what : String) : Option Json → Except String (Option String)
  | none => .ok none
  | some .null => .ok none
  | some (.str s) => .ok (some s)
  | some _ => .error s!"{what}: expected a string or null"

def isTrue : Option Json → Bool
  | some (.bool true) => true
  | _ => false

theorem isTrue_iff (v : Option Json) : isTrue v = true ↔ v = some (.bool true) := by
  unfold isTrue
  split <;> simp_all

def parseEventStrict (j : Json) : Except String Event := do
  let some (.str k) ← field? j "action" | throw "action: expected a string"
  let task ← optStr "task" (← field? j "task")
  let agent ← optStr "agent" (← field? j "agent")
  let name ← optStr "name" (← field? j "name")
  let rejected ← match ← field? j "rejected" with
    | none => pure false
    | some .null => pure false
    | some (.bool b) => pure b
    | some _ => throw "rejected: expected a bool or null"
  let done := isTrue (← field? j "done")
  let answer := match (← field? j "answer") with
    | some v => intOf? v
    | none => none
  pure { kind := some k, agent, task, name := name.getD "", answer, rejected, done, malformed := false }

/-- The event read for an unreadable log entry: no kind, no task, `malformed`. -/
def malformedEvent : Event :=
  { kind := none, agent := none, task := none, name := "", answer := none, rejected := false,
    done := false, malformed := true }

def parseEvent (j : Json) : Event :=
  match parseEventStrict j with
  | .ok e => e
  | .error _ => malformedEvent

def parseTask (j : Json) : Except String (String × Int) := do
  let some (.str id) ← field? j "id" | throw "task id: expected a string"
  let some ev ← field? j "expect" | throw s!"task {id}: expect missing"
  let some v := intOf? ev | throw s!"task {id}: expect must be an integer"
  pure (id, v)

def parseTaskSet (j : Json) : Except String TaskSet := do
  let some tj ← field? j "tasks" | throw "taskset.tasks missing"
  let tasks ← (← tj.getArr?).toList.mapM parseTask
  let some nj ← field? j "n_agents" | throw "taskset.n_agents missing"
  let some n := intOf? nj | throw "taskset.n_agents must be an integer"
  if n ≤ 0 then throw "taskset.n_agents must be positive"
  let ts : TaskSet := ⟨tasks, n.toNat⟩
  if !validTaskSet ts then throw "taskset: duplicate task ids"
  pure ts

def scoreJson (s : Score) : Json :=
  Json.mkObj [
    ("distinct_passing", toJson s.distinct_passing),
    ("slots", toJson s.slots),
    ("duplicates", toJson s.duplicates),
    ("name_collisions", toJson s.name_collisions),
    ("surviving_passing", toJson s.surviving_passing),
    ("unknown_task_events", toJson s.unknown_task_events),
    ("Y_num", toJson s.yNum),
    ("Y_den", toJson s.yDen),
    ("done_releases", toJson s.done_releases),
    ("false_done", toJson s.false_done),
    ("extra_work_events", toJson s.extra_work_events),
    ("valid", toJson s.valid)]

def runCase (j : Json) : Except String Json := do
  let some tsj ← field? j "taskset" | throw "taskset missing"
  let some lj ← field? j "log" | throw "log missing"
  let ts ← parseTaskSet tsj
  let log := (← lj.getArr?).toList.map parseEvent
  pure (scoreJson (score ts log))

def run (input : String) : Except String String := do
  match ← Json.parse input with
  | .arr cases => pure (Json.arr (← cases.mapM runCase)).compress
  | j => pure (← runCase j).compress

end AllocScore
