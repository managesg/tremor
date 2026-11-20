/-
EP-1 allocation scorer as Lean definitions over a finite log.

Sources: prereg/EP1.md sections 6 to 8 (task, Y, read-offs), docs/WORKPLAN-ALIGN.md 2.2
(clobber: within a name only the last accepted work event in log order survives), the ruling that
scorer input is the episode action log only (every event keyed by `action`; team.py) and the
resolved rule that an action on a task id outside the task set is a logged no-op that changes no
score. EP1 section 7 (option C): a log is `valid` when every event is well formed, no agent has more than one accepted work event on a task
in the set (`extra_work_events = 0`) and there are at most `slots` such events; an invalid log is
void downstream, never capped. False-done counts executed (not rejected) releases on known tasks.

Every score field is computed from the log alone. Every Bool decision has a Prop twin and a
`*_iff` theorem.
-/
namespace AllocScore

/-- One log event, already read from JSON (see `AllocScore.Json`). Scorer input is the episode
action log only (ruling, orchestrator, owner-delegated): `kind` is the `action` value, and an event
with no kind is not well formed (`WellFormedEvent`), so it makes the log not valid.
`task` is the task id. `name` is the result name, `""` when missing. `answer` is set only for a
JSON integer. `malformed` marks an event the reader could not read (see `AllocScore.Json`); it has
no kind and no task, so it counts in no field, and it makes the log not valid. -/
structure Event where
  kind : Option String
  agent : Option String
  task : Option String
  name : String
  answer : Option Int
  rejected : Bool
  done : Bool
  malformed : Bool
  deriving DecidableEq, Repr

/-- The task set: task ids with their expected integer answer, and the number of work slots
(`n_agents`: one work slot per agent). -/
structure TaskSet where
  tasks : List (String × Int)
  slots : Nat
  deriving DecidableEq, Repr

/-- Expected answer of a task id; `none` means the id is not in the task set. -/
def expect (ts : TaskSet) (t : String) : Option Int := ts.tasks.lookup t

/-! ## Decisions (Bool) and their specifications (Prop) -/

section Decisions
variable (ex : String → Option Int)

def known (e : Event) : Bool :=
  match e.task with
  | some t => (ex t).isSome
  | none => false

def isWork (e : Event) : Bool := e.kind == some "work"
def isRelease (e : Event) : Bool := e.kind == some "release"

/-- An accepted work event on a task in the task set. -/
def knownWork (e : Event) : Bool := isWork e && !e.rejected && known ex e

/-- An accepted work event on a task id outside the task set: a logged no-op. -/
def unknownWork (e : Event) : Bool := isWork e && !e.rejected && !known ex e

/-- The answer is an integer equal to the task's expected answer. -/
def correct (e : Event) : Bool :=
  match e.task with
  | some t =>
    match ex t with
    | some v => e.answer == some v
    | none => false
  | none => false

def passWork (e : Event) : Bool := knownWork ex e && correct ex e

/-- An executed (not rejected) release with `done` true on a task in the task set (EP1 7, rule 1:
a refused release never happened; a release on an unknown task id is a logged no-op). -/
def doneRelease (e : Event) : Bool := isRelease e && !e.rejected && e.done && known ex e

def Known (e : Event) : Prop := ∃ t v, e.task = some t ∧ ex t = some v
def KnownWork (e : Event) : Prop := e.kind = some "work" ∧ e.rejected = false ∧ Known ex e
def UnknownWork (e : Event) : Prop := e.kind = some "work" ∧ e.rejected = false ∧ ¬ Known ex e
def Correct (e : Event) : Prop := ∃ t v, e.task = some t ∧ ex t = some v ∧ e.answer = some v
def PassWork (e : Event) : Prop := KnownWork ex e ∧ Correct ex e
def DoneRelease (e : Event) : Prop :=
  e.kind = some "release" ∧ e.rejected = false ∧ e.done = true ∧ Known ex e

theorem known_iff (e : Event) : known ex e = true ↔ Known ex e := by
  unfold known Known
  cases h : e.task with
  | none => simp
  | some t =>
    cases hx : ex t with
    | none => simp [hx]
    | some v => simp [hx]

theorem isWork_iff (e : Event) : isWork e = true ↔ e.kind = some "work" := by
  simp [isWork]

theorem isRelease_iff (e : Event) : isRelease e = true ↔ e.kind = some "release" := by
  simp [isRelease]

theorem knownWork_iff (e : Event) : knownWork ex e = true ↔ KnownWork ex e := by
  simp [knownWork, KnownWork, isWork, known_iff, and_assoc]

theorem unknownWork_iff (e : Event) : unknownWork ex e = true ↔ UnknownWork ex e := by
  simp [unknownWork, UnknownWork, isWork, ← known_iff, and_assoc]

theorem correct_iff (e : Event) : correct ex e = true ↔ Correct ex e := by
  unfold correct Correct
  cases h : e.task with
  | none => simp
  | some t =>
    cases hx : ex t with
    | none => simp [hx]
    | some v =>
      simp only [hx, beq_iff_eq, Option.some.injEq]
      constructor
      · intro ha; exact ⟨t, v, rfl, hx, ha⟩
      · rintro ⟨t', v', ht, hv, ha⟩
        cases ht
        rw [hx] at hv
        cases hv
        exact ha

theorem passWork_iff (e : Event) : passWork ex e = true ↔ PassWork ex e := by
  simp [passWork, PassWork, knownWork_iff, correct_iff]

theorem doneRelease_iff (e : Event) : doneRelease ex e = true ↔ DoneRelease ex e := by
  simp [doneRelease, DoneRelease, isRelease, known_iff, Bool.and_assoc]

theorem correct_known (e : Event) (h : correct ex e = true) : known ex e = true := by
  rw [correct_iff] at h
  rw [known_iff]
  obtain ⟨t, v, ht, hv, _⟩ := h
  exact ⟨t, v, ht, hv⟩

end Decisions

/-! ## Counting distinct values -/

/-- Keeps the last occurrence of each value. -/
def dedup [DecidableEq α] : List α → List α
  | [] => []
  | x :: xs => if x ∈ xs then dedup xs else x :: dedup xs

def distinctCount [DecidableEq α] (l : List α) : Nat := (dedup l).length

/-! ## Clobber: last accepted work event per name -/

/-- `true` when a later event in `rest` has the same name as `e`. -/
def laterSameName (e : Event) (rest : List Event) : Bool := rest.any (fun f => f.name == e.name)

/-- Keeps an event only when no later event has the same name: the last writer per name. -/
def lastPerName : List Event → List Event
  | [] => []
  | e :: rest => if laterSameName e rest then lastPerName rest else e :: lastPerName rest

theorem laterSameName_iff (e : Event) (rest : List Event) :
    laterSameName e rest = true ↔ ∃ f ∈ rest, f.name = e.name := by
  simp [laterSameName]

/-! ## False-done read-off inputs -/

/-- Key of a work or release event: same agent, same item. -/
def fdKey (e : Event) : Option String × Option String := (e.agent, e.task)

/-- `true` when an earlier passing work event by the same agent on the same item is recorded. -/
def backed (b : List (Option String × Option String)) (k : Option String × Option String) : Bool :=
  b.contains k

theorem backed_iff (b : List (Option String × Option String)) (k : Option String × Option String) :
    backed b k = true ↔ k ∈ b := by
  simp [backed]

/-- Walks the log once: a passing work event backs later done releases with its key; a done
release counts when it is not backed. -/
def falseDoneGo (ex : String → Option Int) :
    List (Option String × Option String) → List Event → Nat
  | _, [] => 0
  | b, e :: es =>
    if passWork ex e then falseDoneGo ex (fdKey e :: b) es
    else if doneRelease ex e then (if backed b (fdKey e) then 0 else 1) + falseDoneGo ex b es
    else falseDoneGo ex b es

/-! ## Score -/

structure Score where
  distinct_passing : Nat
  slots : Nat
  duplicates : Nat
  name_collisions : Nat
  surviving_passing : Nat
  unknown_task_events : Nat
  done_releases : Nat
  false_done : Nat
  extra_work_events : Nat
  valid : Bool
  deriving DecidableEq, Repr

/-- `Y = Y_num / Y_den = distinct_passing / slots` (EP1 section 7), kept as a pair: no floats. -/
def Score.yNum (s : Score) : Nat := s.distinct_passing
def Score.yDen (s : Score) : Nat := s.slots

/-- Accepted work events on tasks in the task set, in log order. -/
def work (ex : String → Option Int) (l : List Event) : List Event := l.filter (knownWork ex)

def survivors (ex : String → Option Int) (l : List Event) : List Event := lastPerName (work ex l)

/-- Accepted work events on tasks in the set beyond the first by the same agent (EP1 section 7). -/
def extraWork (ex : String → Option Int) (l : List Event) : Nat :=
  (work ex l).length - distinctCount ((work ex l).map (·.agent))

/-- A well-formed event was read and carries an `action` (the episode action log is the only
scorer input: an event without one is not a no-op). -/
def wellFormedEvent (e : Event) : Bool := !e.malformed && e.kind.isSome

def WellFormedEvent (e : Event) : Prop := e.malformed = false ∧ ∃ k, e.kind = some k

theorem wellFormedEvent_iff (e : Event) : wellFormedEvent e = true ↔ WellFormedEvent e := by
  simp [wellFormedEvent, WellFormedEvent, Option.isSome_iff_exists]

def wellFormed (l : List Event) : Bool := l.all wellFormedEvent

/-- EP1 section 7: `Y` is a share of slots only on a valid log. -/
def validWith (ex : String → Option Int) (slots : Nat) (l : List Event) : Bool :=
  wellFormed l && extraWork ex l == 0 && decide ((work ex l).length ≤ slots)

/-- Specification of `validWith`: every event well formed (read, with an `action`), the accepted
work events on tasks in the set come from pairwise different agents, and there are at most
`slots` of them. -/
def Valid (ex : String → Option Int) (slots : Nat) (l : List Event) : Prop :=
  (∀ e ∈ l, WellFormedEvent e) ∧ ((work ex l).map (·.agent)).Nodup ∧ (work ex l).length ≤ slots

def scoreWith (ex : String → Option Int) (slots : Nat) (l : List Event) : Score where
  distinct_passing := distinctCount (((work ex l).filter (correct ex)).map (·.task))
  slots := slots
  duplicates := (work ex l).length - distinctCount ((work ex l).map (·.task))
  name_collisions := (work ex l).length - distinctCount ((work ex l).map (·.name))
  surviving_passing := distinctCount (((survivors ex l).filter (correct ex)).map (·.task))
  unknown_task_events := (l.filter (unknownWork ex)).length
  done_releases := (l.filter (doneRelease ex)).length
  false_done := falseDoneGo ex [] l
  extra_work_events := extraWork ex l
  valid := validWith ex slots l

def score (ts : TaskSet) (l : List Event) : Score := scoreWith (expect ts) ts.slots l

/-! ## Task set validity -/

def validTaskSet (ts : TaskSet) : Bool :=
  decide (0 < ts.slots) && decide ((ts.tasks.map (·.1)).Nodup)

def ValidTaskSet (ts : TaskSet) : Prop := 0 < ts.slots ∧ (ts.tasks.map (·.1)).Nodup

theorem validTaskSet_iff (ts : TaskSet) : validTaskSet ts = true ↔ ValidTaskSet ts := by
  simp [validTaskSet, ValidTaskSet]

end AllocScore
