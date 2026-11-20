import AllocScore.Basic

/-!
Kernel-checked properties of `AllocScore.score`.

1. Unknown-task events change no score field except `unknown_task_events`.
2. `surviving_passing ≤ distinct_passing` always; `distinct_passing ≤ slots` and `Y ∈ [0, 1]`
   on every `valid` log (false for arbitrary logs: see `distinct_gt_slots_possible`, whose log is
   not valid). `validWith_iff`: `valid` decides `Valid` (every event read and keyed by `action`,
   one accepted work event per agent, at most `slots` of them).
3. Clobber: per name, the survivor is exactly the last accepted work event in log order.
4. Determinism, task-set extensionality, and swap invariance for adjacent events on different
   tasks with different names (with counterexamples for a shared name or a shared task).
5. `*_iff` theorems for every Bool decision live next to the decisions in `AllocScore.Basic`.
-/
namespace AllocScore

/-! ## Distinct counts -/

section Distinct
variable {α : Type} [DecidableEq α]

theorem mem_dedup {x : α} : ∀ {l : List α}, x ∈ dedup l ↔ x ∈ l
  | [] => by simp [dedup]
  | y :: ys => by
    unfold dedup
    by_cases h : y ∈ ys
    · rw [ite_eq_left h, mem_dedup, List.mem_cons]
      constructor
      · exact Or.inr
      · rintro (rfl | hx)
        · exact h
        · exact hx
    · rw [ite_eq_right h, List.mem_cons, List.mem_cons, mem_dedup]

theorem nodup_dedup : ∀ (l : List α), (dedup l).Nodup
  | [] => by simp [dedup]
  | y :: ys => by
    unfold dedup
    by_cases h : y ∈ ys
    · rw [ite_eq_left h]; exact nodup_dedup ys
    · rw [ite_eq_right h]
      exact List.nodup_cons.mpr ⟨fun hm => h (mem_dedup.mp hm), nodup_dedup ys⟩

theorem length_dedup_le : ∀ (l : List α), (dedup l).length ≤ l.length
  | [] => by simp [dedup]
  | y :: ys => by
    have := length_dedup_le ys
    unfold dedup
    split
    · simp; omega
    · simp; omega

theorem length_le_of_nodup_subset :
    ∀ {s t : List α}, s.Nodup → (∀ x ∈ s, x ∈ t) → s.length ≤ t.length
  | [], _, _, _ => by simp
  | x :: s, t, hn, hsub => by
    rw [List.nodup_cons] at hn
    have hx : x ∈ t := hsub x (List.mem_cons_self ..)
    have hs : ∀ y ∈ s, y ∈ t.erase x := by
      intro y hy
      have hne : y ≠ x := fun e => hn.1 (e ▸ hy)
      exact (List.mem_erase_of_ne hne).mpr (hsub y (List.mem_cons_of_mem _ hy))
    have h1 := length_le_of_nodup_subset hn.2 hs
    rw [List.length_erase_of_mem hx] at h1
    have h2 : 0 < t.length := List.length_pos_of_mem hx
    simp only [List.length_cons]
    omega

theorem distinctCount_le_of_subset {s t : List α} (h : ∀ x ∈ s, x ∈ t) :
    distinctCount s ≤ distinctCount t := by
  unfold distinctCount
  apply length_le_of_nodup_subset (nodup_dedup s)
  intro x hx
  exact mem_dedup.mpr (h x (mem_dedup.mp hx))

theorem distinctCount_congr {s t : List α} (h : ∀ x, x ∈ s ↔ x ∈ t) :
    distinctCount s = distinctCount t :=
  Nat.le_antisymm (distinctCount_le_of_subset fun x hx => (h x).mp hx)
    (distinctCount_le_of_subset fun x hx => (h x).mpr hx)

theorem distinctCount_le_length (l : List α) : distinctCount l ≤ l.length := length_dedup_le l

theorem length_dedup_eq_iff : ∀ (l : List α), (dedup l).length = l.length ↔ l.Nodup
  | [] => by simp [dedup]
  | y :: ys => by
    have ih := length_dedup_eq_iff ys
    have hle := length_dedup_le ys
    unfold dedup
    by_cases h : y ∈ ys
    · rw [ite_eq_left h, List.nodup_cons]
      constructor
      · intro he; simp only [List.length_cons] at he; omega
      · rintro ⟨hn, _⟩; exact absurd h hn
    · rw [ite_eq_right h, List.nodup_cons, List.length_cons, List.length_cons, Nat.add_right_cancel_iff, ih]
      exact ⟨fun hn => ⟨h, hn⟩, fun hn => hn.2⟩

/-- A list minus its distinct count is zero exactly when it has no repeated value. -/
theorem sub_distinctCount_eq_zero_iff (l : List α) : l.length - distinctCount l = 0 ↔ l.Nodup := by
  have h1 := distinctCount_le_length l
  rw [← length_dedup_eq_iff]
  unfold distinctCount at h1 ⊢
  constructor <;> intro h <;> omega

end Distinct

/-! ## Validity (EP1 section 7, option C) -/

theorem extraWork_eq_zero_iff (ex : String → Option Int) (l : List Event) :
    extraWork ex l = 0 ↔ ((work ex l).map (·.agent)).Nodup := by
  unfold extraWork
  rw [← sub_distinctCount_eq_zero_iff, List.length_map]

theorem wellFormed_iff (l : List Event) : wellFormed l = true ↔ ∀ e ∈ l, WellFormedEvent e := by
  simp [wellFormed, wellFormedEvent_iff]

/-- `valid` decides its specification `Valid`. -/
theorem validWith_iff (ex : String → Option Int) (slots : Nat) (l : List Event) :
    validWith ex slots l = true ↔ Valid ex slots l := by
  simp only [validWith, Valid, Bool.and_eq_true, wellFormed_iff, beq_iff_eq, extraWork_eq_zero_iff,
    decide_eq_true_eq, and_assoc]

theorem score_valid_iff (ts : TaskSet) (l : List Event) :
    (score ts l).valid = true ↔ Valid (expect ts) ts.slots l :=
  validWith_iff _ _ _

/-! ## 1. Unknown-task events are no-ops -/

section Unknown
variable {ex : String → Option Int} {e : Event}

theorem knownWork_of_unknown (h : known ex e = false) : knownWork ex e = false := by
  simp [knownWork, h]

theorem correct_of_unknown (h : known ex e = false) : correct ex e = false := by
  cases hc : correct ex e
  · rfl
  · rw [correct_known ex e hc] at h; cases h

theorem passWork_of_unknown (h : known ex e = false) : passWork ex e = false := by
  simp [passWork, knownWork_of_unknown h]

theorem doneRelease_of_unknown (h : known ex e = false) : doneRelease ex e = false := by
  simp [doneRelease, h]

theorem filter_insert_false (p : Event → Bool) (l1 l2 : List Event) (h : p e = false) :
    (l1 ++ e :: l2).filter p = (l1 ++ l2).filter p := by
  simp [List.filter_append, h]

theorem falseDoneGo_insert_unknown (h : known ex e = false) (l2 : List Event) :
    ∀ (l1 : List Event) (b : List (Option String × Option String)),
      falseDoneGo ex b (l1 ++ e :: l2) = falseDoneGo ex b (l1 ++ l2)
  | [], b => by
    simp [falseDoneGo, passWork_of_unknown h, doneRelease_of_unknown h]
  | x :: xs, b => by
    simp only [List.cons_append, falseDoneGo, falseDoneGo_insert_unknown h l2 xs]

end Unknown

/-- **(1)** Inserting an event on a task id outside the task set, anywhere in the log, changes no
score field other than `unknown_task_events`. -/
theorem score_insert_unknown (ts : TaskSet) (l1 l2 : List Event) (e : Event)
    (h : known (expect ts) e = false) (hm : wellFormedEvent e = true) :
    { score ts (l1 ++ e :: l2) with unknown_task_events := 0 } =
      { score ts (l1 ++ l2) with unknown_task_events := 0 } := by
  simp only [score, scoreWith, survivors, extraWork, validWith, wellFormed, work,
    filter_insert_false _ l1 l2 (knownWork_of_unknown h),
    filter_insert_false _ l1 l2 (doneRelease_of_unknown h),
    falseDoneGo_insert_unknown h l2 l1, List.all_append, List.all_cons, hm, Bool.true_and]
  rfl

/-- **(1')** `unknown_task_events` grows by one exactly when the inserted event is an accepted
`work` event. -/
theorem unknown_insert_count (ts : TaskSet) (l1 l2 : List Event) (e : Event)
    (h : known (expect ts) e = false) :
    (score ts (l1 ++ e :: l2)).unknown_task_events =
      (score ts (l1 ++ l2)).unknown_task_events + (if isWork e && !e.rejected then 1 else 0) := by
  simp only [score, scoreWith, List.filter_append, List.filter_cons, List.length_append]
  cases hw : isWork e && !e.rejected
  · have : unknownWork (expect ts) e = false := by
      simp only [unknownWork, hw, Bool.false_and]
    simp [this]
  · have : unknownWork (expect ts) e = true := by
      simp only [unknownWork, hw, h, Bool.not_false, Bool.and_true]
    simp [this]
    omega

/-! ## 2. Bounds -/

theorem distinct_le_work (ts : TaskSet) (l : List Event) :
    (score ts l).distinct_passing ≤ (work (expect ts) l).length := by
  simp only [score, scoreWith]
  refine Nat.le_trans (distinctCount_le_length _) ?_
  rw [List.length_map]
  exact List.length_filter_le _ _

/-- **(2a)** `distinct_passing ≤ slots` when there are at most `slots` accepted work events on
tasks of the task set. -/
theorem distinct_le_slots (ts : TaskSet) (l : List Event)
    (h : (work (expect ts) l).length ≤ ts.slots) :
    (score ts l).distinct_passing ≤ (score ts l).slots :=
  Nat.le_trans (distinct_le_work ts l) h

/-- **(2a')** EP1 section 6: one work slot per agent. If the accepted work events come from
pairwise different agents, all drawn from a list of at most `slots` agents, then
`distinct_passing ≤ slots`. -/
theorem distinct_le_slots_one_work_per_agent (ts : TaskSet) (l : List Event)
    (agents : List (Option String))
    (hnodup : ((work (expect ts) l).map (·.agent)).Nodup)
    (hin : ∀ e ∈ work (expect ts) l, e.agent ∈ agents)
    (hlen : agents.length ≤ ts.slots) :
    (score ts l).distinct_passing ≤ (score ts l).slots := by
  apply distinct_le_slots
  have h := length_le_of_nodup_subset hnodup (by
    intro x hx
    rw [List.mem_map] at hx
    obtain ⟨e, he, rfl⟩ := hx
    exact hin e he)
  rw [List.length_map] at h
  omega

/-- **(2b)** `Y = Y_num / Y_den` lies in `[0, 1]` (and `Y_den > 0`) for a valid task set with at
most `slots` accepted work events. `Y_num ≥ 0` holds because it is a natural number. -/
theorem Y_in_unit (ts : TaskSet) (l : List Event) (hv : ValidTaskSet ts)
    (h : (work (expect ts) l).length ≤ ts.slots) :
    0 < (score ts l).yDen ∧ (score ts l).yNum ≤ (score ts l).yDen :=
  ⟨hv.1, distinct_le_slots ts l h⟩

/-- **(2a'')** EP1 section 7: on every valid log, `distinct_passing ≤ slots`. -/
theorem distinct_le_slots_of_valid (ts : TaskSet) (l : List Event) (h : (score ts l).valid = true) :
    (score ts l).distinct_passing ≤ (score ts l).slots :=
  distinct_le_slots ts l ((score_valid_iff ts l).mp h).2.2

/-- **(2b')** On every valid log of a valid task set, `Y_den > 0` and `Y_num ≤ Y_den`, so
`Y ∈ [0, 1]`. -/
theorem Y_in_unit_of_valid (ts : TaskSet) (l : List Event) (hv : ValidTaskSet ts)
    (h : (score ts l).valid = true) :
    0 < (score ts l).yDen ∧ (score ts l).yNum ≤ (score ts l).yDen :=
  Y_in_unit ts l hv ((score_valid_iff ts l).mp h).2.2

theorem lastPerName_sublist : ∀ (l : List Event), (lastPerName l).Sublist l
  | [] => by simp [lastPerName]
  | e :: rest => by
    unfold lastPerName
    split
    · exact (lastPerName_sublist rest).cons e
    · exact (lastPerName_sublist rest).cons_cons e

/-- **(2c)** `surviving_passing ≤ distinct_passing`, for every log. -/
theorem surviving_le_distinct (ts : TaskSet) (l : List Event) :
    (score ts l).surviving_passing ≤ (score ts l).distinct_passing := by
  simp only [score, scoreWith, survivors]
  apply distinctCount_le_of_subset
  intro x hx
  simp only [List.mem_map, List.mem_filter] at hx ⊢
  obtain ⟨e, ⟨he, hc⟩, rfl⟩ := hx
  exact ⟨e, ⟨(lastPerName_sublist _).subset he, hc⟩, rfl⟩

/-- **(2d)** The three bounds together on a valid log of a valid task set:
`surviving_passing ≤ distinct_passing ≤ slots` and `Y ∈ [0, 1]`. -/
theorem valid_bounds (ts : TaskSet) (l : List Event) (hv : ValidTaskSet ts)
    (h : (score ts l).valid = true) :
    (score ts l).surviving_passing ≤ (score ts l).distinct_passing ∧
      (score ts l).distinct_passing ≤ (score ts l).slots ∧
      0 < (score ts l).yDen ∧ (score ts l).yNum ≤ (score ts l).yDen :=
  ⟨surviving_le_distinct ts l, distinct_le_slots_of_valid ts l h, Y_in_unit_of_valid ts l hv h⟩

/-- Example data for the counterexamples below. -/
def cxTasks : TaskSet := ⟨[("t0", 1), ("t1", 2)], 1⟩

def cxWork (agent task : String) (answer : Int) (name : String) : Event :=
  ⟨some "work", some agent, some task, name, some answer, false, false, false⟩

def cxDone (agent task : String) : Event :=
  ⟨some "release", some agent, some task, "", none, false, true, false⟩

/-- Without the one-work-per-slot hypothesis, `distinct_passing ≤ slots` is false: two passing
work events with one slot. -/
theorem distinct_gt_slots_possible :
    ∃ ts l, (score ts l).slots < (score ts l).distinct_passing :=
  ⟨cxTasks, [cxWork "a0" "t0" 1 "x", cxWork "a1" "t1" 2 "y"], by decide⟩

/-- The counterexample log of `distinct_gt_slots_possible` is not valid: it is void, not scored. -/
theorem distinct_gt_slots_log_not_valid :
    (score cxTasks [cxWork "a0" "t0" 1 "x", cxWork "a1" "t1" 2 "y"]).valid = false := by decide

/-- Two accepted work events by one agent make a log not valid, even within the slot count. -/
theorem two_work_one_agent_not_valid :
    (score ⟨[("t0", 1), ("t1", 2)], 4⟩ [cxWork "a0" "t0" 1 "x", cxWork "a0" "t1" 2 "y"]).valid = false ∧
    (score ⟨[("t0", 1), ("t1", 2)], 4⟩
      [cxWork "a0" "t0" 1 "x", cxWork "a0" "t1" 2 "y"]).extra_work_events = 1 := by decide

/-- One malformed event makes a log not valid. -/
theorem malformed_not_valid (ts : TaskSet) (l : List Event) (e : Event) (h : e ∈ l)
    (hm : e.malformed = true) : (score ts l).valid = false := by
  cases hv : (score ts l).valid
  · rfl
  · have := (((score_valid_iff ts l).mp hv).1 e h).1
    rw [hm] at this
    cases this

/-- An event without an `action` (no kind: a board `type` line, a board release, any other shape)
makes a log not valid: the scorer reads the episode action log only. -/
theorem no_action_not_valid (ts : TaskSet) (l : List Event) (e : Event) (h : e ∈ l)
    (hk : e.kind = none) : (score ts l).valid = false := by
  cases hv : (score ts l).valid
  · rfl
  · obtain ⟨_, k, hk'⟩ := ((score_valid_iff ts l).mp hv).1 e h
    rw [hk] at hk'
    cases hk'

/-! ## 3. Clobber -/

theorem lastPerName_filter_name (n : String) : ∀ (l : List Event),
    (lastPerName l).filter (fun f => f.name == n) =
      ((l.filter (fun f => f.name == n)).getLast?).toList
  | [] => by simp [lastPerName]
  | e :: rest => by
    have ih := lastPerName_filter_name n rest
    unfold lastPerName
    by_cases hl : laterSameName e rest = true
    · rw [ite_eq_left hl, ih]
      obtain ⟨f, hf, hfn⟩ := (laterSameName_iff e rest).mp hl
      by_cases hen : e.name = n
      · have hne : rest.filter (fun f => f.name == n) ≠ [] := by
          intro h0
          have hm : f ∈ rest.filter (fun f => f.name == n) :=
            List.mem_filter.mpr ⟨hf, by simp [hfn, hen]⟩
          rw [h0] at hm
          cases hm
        rw [List.filter_cons_of_pos (by simp [hen]), List.getLast?_cons]
        cases hg : (rest.filter (fun f => f.name == n)).getLast? with
        | none => exact absurd (List.getLast?_eq_none_iff.mp hg) hne
        | some g => rfl
      · rw [List.filter_cons_of_neg (by simp [hen])]
    · rw [ite_eq_right hl]
      by_cases hen : e.name = n
      · have h0 : rest.filter (fun f => f.name == n) = [] := by
          rw [List.filter_eq_nil_iff]
          intro f hf hfn
          exact hl ((laterSameName_iff e rest).mpr ⟨f, hf, by simpa [hen] using hfn⟩)
        rw [List.filter_cons_of_pos (by simp [hen]), List.filter_cons_of_pos (by simp [hen]),
          ih, h0]
        rfl
      · rw [List.filter_cons_of_neg (by simp [hen]), List.filter_cons_of_neg (by simp [hen]), ih]

/-- **(3)** For every name `n`, the surviving work events named `n` are exactly the last accepted
work event named `n` in log order (none when there is none). -/
theorem clobber_last_writer (ts : TaskSet) (l : List Event) (n : String) :
    (survivors (expect ts) l).filter (fun f => f.name == n) =
      ((work (expect ts) l).filter (fun f => f.name == n)).getLast?.toList :=
  lastPerName_filter_name n _

/-- **(3')** At most one work event survives per name. -/
theorem clobber_at_most_one (ts : TaskSet) (l : List Event) (n : String) :
    ((survivors (expect ts) l).filter (fun f => f.name == n)).length ≤ 1 := by
  rw [clobber_last_writer]
  cases ((work (expect ts) l).filter (fun f => f.name == n)).getLast? <;> simp

/-- **(3'')** Per name, the surviving passing work events are the last accepted work event of that
name if it is passing, and nothing otherwise: at most one, and it is the last in log order. -/
theorem clobber_passing (ts : TaskSet) (l : List Event) (n : String) :
    (survivors (expect ts) l).filter (fun f => f.name == n && correct (expect ts) f) =
      (((work (expect ts) l).filter (fun f => f.name == n)).getLast?.toList).filter
        (correct (expect ts)) := by
  rw [← clobber_last_writer, List.filter_filter]
  congr 1
  funext f
  exact Bool.and_comm _ _

/-! ## 4. Determinism, extensionality, reordering -/

/-- **(4a)** Equal inputs give equal scores. -/
theorem score_deterministic {ts₁ ts₂ : TaskSet} {l₁ l₂ : List Event}
    (ht : ts₁ = ts₂) (hl : l₁ = l₂) : score ts₁ l₁ = score ts₂ l₂ := by
  subst ht; subst hl; rfl

/-- **(4b)** The score depends on the task set only through each id's expected answer and the
slot count (so the order of the task list does not matter). -/
theorem score_ext_taskset (ts₁ ts₂ : TaskSet) (l : List Event)
    (h : ∀ t, expect ts₁ t = expect ts₂ t) (hs : ts₁.slots = ts₂.slots) :
    score ts₁ l = score ts₂ l := by
  unfold score
  rw [show expect ts₁ = expect ts₂ from funext h, hs]

theorem perm_swap_mid {α : Type} (l1 l2 : List α) (a b : α) :
    (l1 ++ a :: b :: l2).Perm (l1 ++ b :: a :: l2) :=
  List.Perm.append_left l1 (List.Perm.swap b a l2)

theorem laterSameName_append_swap (e a b : Event) (P Q : List Event) :
    laterSameName e (P ++ a :: b :: Q) = laterSameName e (P ++ b :: a :: Q) := by
  simp only [laterSameName, List.any_append, List.any_cons, Bool.or_left_comm]

theorem lastPerName_swap_mem (a b : Event) (hab : a.name ≠ b.name) (Q : List Event) :
    ∀ (P : List Event) (x : Event),
      x ∈ lastPerName (P ++ a :: b :: Q) ↔ x ∈ lastPerName (P ++ b :: a :: Q)
  | [], x => by
    have h1 : laterSameName a (b :: Q) = laterSameName a Q := by
      simp [laterSameName, Ne.symm hab]
    have h2 : laterSameName b (a :: Q) = laterSameName b Q := by
      simp [laterSameName, hab]
    simp only [List.nil_append, lastPerName, h1, h2]
    cases laterSameName a Q <;> cases laterSameName b Q <;>
      simp [List.mem_cons, or_left_comm]
  | z :: P, x => by
    simp only [List.cons_append, lastPerName, laterSameName_append_swap z a b P Q]
    split
    · exact lastPerName_swap_mem a b hab Q P x
    · simp only [List.mem_cons, lastPerName_swap_mem a b hab Q P x]

theorem survivors_swap_mem (ex : String → Option Int) (l1 l2 : List Event) (a b : Event)
    (hab : a.name ≠ b.name) (x : Event) :
    x ∈ survivors ex (l1 ++ a :: b :: l2) ↔ x ∈ survivors ex (l1 ++ b :: a :: l2) := by
  simp only [survivors, work, List.filter_append, List.filter_cons]
  cases ha : knownWork ex a <;> cases hb : knownWork ex b <;> simp only [ite_true, ite_false,
    Bool.false_eq_true]
  exact lastPerName_swap_mem a b hab _ _ x

theorem backed_cons_ne {k k' : Option String × Option String} (h : k' ≠ k)
    (b : List (Option String × Option String)) : backed (k' :: b) k = backed b k := by
  apply Bool.eq_iff_iff.mpr
  rw [backed_iff, backed_iff, List.mem_cons]
  constructor
  · rintro (h' | h')
    · exact absurd h'.symm h
    · exact h'
  · exact Or.inr

theorem falseDoneGo_congr (ex : String → Option Int) :
    ∀ (l : List Event) (b₁ b₂ : List (Option String × Option String)),
      (∀ k, k ∈ b₁ ↔ k ∈ b₂) → falseDoneGo ex b₁ l = falseDoneGo ex b₂ l
  | [], _, _, _ => rfl
  | e :: es, b₁, b₂, h => by
    have hb : backed b₁ (fdKey e) = backed b₂ (fdKey e) := by
      apply Bool.eq_iff_iff.mpr
      rw [backed_iff, backed_iff]
      exact h _
    have hc : ∀ k, k ∈ fdKey e :: b₁ ↔ k ∈ fdKey e :: b₂ := by
      intro k
      rw [List.mem_cons, List.mem_cons, h k]
    simp only [falseDoneGo, hb, falseDoneGo_congr ex es b₁ b₂ h,
      falseDoneGo_congr ex es _ _ hc]

theorem falseDoneGo_swap (ex : String → Option Int) (a c : Event) (hk : fdKey a ≠ fdKey c)
    (l2 : List Event) :
    ∀ (l1 : List Event) (b : List (Option String × Option String)),
      falseDoneGo ex b (l1 ++ a :: c :: l2) = falseDoneGo ex b (l1 ++ c :: a :: l2)
  | [], b => by
    have hac := backed_cons_ne hk
    have hca := backed_cons_ne (Ne.symm hk)
    have hsw : falseDoneGo ex (fdKey c :: fdKey a :: b) l2 =
        falseDoneGo ex (fdKey a :: fdKey c :: b) l2 :=
      falseDoneGo_congr ex l2 _ _ (by intro k; simp only [List.mem_cons]; exact or_left_comm)
    simp only [List.nil_append, falseDoneGo]
    cases passWork ex a <;> cases doneRelease ex a <;> cases passWork ex c <;>
      cases doneRelease ex c <;> simp [hac, hca, hsw] <;> omega
  | z :: P, b => by
    simp only [List.cons_append, falseDoneGo, falseDoneGo_swap ex a c hk l2 P]

/-- **(4c)** Swapping two adjacent events that touch different tasks and carry different names
does not change any score field. Any reordering made of such swaps therefore keeps the score. -/
theorem score_swap (ts : TaskSet) (l1 l2 : List Event) (a b : Event)
    (ht : a.task ≠ b.task) (hn : a.name ≠ b.name) :
    score ts (l1 ++ a :: b :: l2) = score ts (l1 ++ b :: a :: l2) := by
  have hp := perm_swap_mid l1 l2 a b
  have hw : (work (expect ts) (l1 ++ a :: b :: l2)).Perm (work (expect ts) (l1 ++ b :: a :: l2)) :=
    hp.filter _
  have hk : fdKey a ≠ fdKey b := fun h => ht (congrArg Prod.snd h)
  have hwf : wellFormed (l1 ++ a :: b :: l2) = wellFormed (l1 ++ b :: a :: l2) := by
    simp only [wellFormed, List.all_append, List.all_cons, Bool.and_left_comm]
  have hx : extraWork (expect ts) (l1 ++ a :: b :: l2) = extraWork (expect ts) (l1 ++ b :: a :: l2) := by
    unfold extraWork
    rw [hw.length_eq, distinctCount_congr fun x => (hw.map _).mem_iff]
  simp only [score, scoreWith, Score.mk.injEq]
  refine ⟨?_, trivial, ?_, ?_, ?_, ?_, ?_, ?_, hx, ?_⟩
  · exact distinctCount_congr fun x => ((hw.filter _).map _).mem_iff
  · rw [hw.length_eq, distinctCount_congr fun x => (hw.map _).mem_iff]
  · rw [hw.length_eq, distinctCount_congr fun x => (hw.map _).mem_iff]
  · apply distinctCount_congr
    intro x
    simp only [List.mem_map, List.mem_filter, survivors_swap_mem _ l1 l2 a b hn]
  · exact (hp.filter _).length_eq
  · exact (hp.filter _).length_eq
  · exact falseDoneGo_swap _ a b hk l2 l1 []
  · simp only [validWith, hwf, hx, hw.length_eq]

/-- **(4d)** The different-name condition is needed: two work events on different tasks under one
name change `surviving_passing` when swapped (last writer wins). -/
theorem swap_same_name_can_change :
    ∃ ts a b, a.task ≠ b.task ∧ a.name = b.name ∧ score ts [a, b] ≠ score ts [b, a] :=
  ⟨cxTasks, cxWork "a0" "t0" 1 "n", cxWork "a1" "t1" 0 "n", by decide⟩

/-- **(4e)** The different-task condition is needed: a done release before or after the same
agent's passing work on that task changes `false_done`. -/
theorem swap_same_task_can_change :
    ∃ ts a b, a.task = b.task ∧ a.name ≠ b.name ∧ score ts [a, b] ≠ score ts [b, a] :=
  ⟨cxTasks, cxWork "a0" "t0" 1 "w", cxDone "a0" "t0", by decide⟩

end AllocScore
