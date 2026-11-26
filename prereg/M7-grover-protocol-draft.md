# Pre-registration protocol draft: M7 Grover transfer (assignment by evidence access)

## 1. Status

**DRAFT. Not frozen. No run, spend or experiment authority.** Written offline on 2026-11-25. Nothing
here admits a batch, reserves GPU-hours, names a custodian or approves spend. M7 is blocked: no spend
figure, frozen protocol or custodian is in the repo (OD:7, OD:104-106; GP:41). A freeze needs the
items in section 12 closed and the record in section 13.

Source key. Every statement carries one of these citations or says OPEN. Where the repo gives no
number, the text says OPEN and section 12 names the missing source and the owner. Paths are relative
to the repo root; line numbers are as read at HEAD `c584674` in the working tree.

| Key | File | State when read |
|---|---|---|
| OD | `docs/reports/tremor/OWNER_DECISION_M2_M7_D8_Pilot4_EP1.md` | tracked |
| GP | `docs/reports/TREMOR_GOAL_AND_PLAN_20261123.md` | as read |
| GTD | `docs/reports/workplan-ep/Grover-transfer-protocol-draft.md` | **untracked** |
| GCC | `docs/reports/workplan-ep/Grover-holdout-custody-checklist.md` | **untracked** |
| GTS | `docs/reports/workplan-ep/Grover-topology-scripted.md` | tracked |
| SE | `runs/grover-statistical-envelope.6Cln7i/OWNER.md` | **untracked** (`git ls-files` empty) |
| EPL | `docs/reports/workplan-ep/Execution-plan-20261123.md` | as read |
| CB | `docs/reports/workplan-ep/Coordinator-blockers-20261122.md` | as read |
| ADMR | `docs/reports/tremor/ADMISSION_RECORD_20261125.md` | tracked |
| EP1 | `prereg/EP1.md` | tracked |
| P | `docs/PROPOSAL-RESIDENCY-V3.md` | working tree; contains no Grover line (grep, 2026-11-25) |
| FMT | `prereg/R2-L2-C-protocol.md` | format model only |
| code | `lab/topology.py`, `lab/quantum/topology_transfer.py`, `lab/quantum/topology_audit.py` | tracked; tree hash not recorded here (G-O16) |

## 2. Purpose

Test whether the coordination result seen on scripted Grover fixtures transfers to model workers,
after EP-1: the offline replay covers scripted fixtures only, and "the post-EP-1 model transfer still
needs its protected seeds, approved allocation, and frozen science protocol" (GTS:28-29). The offline
milestone is met when the coordinator reproduces the three regimes across the crossed conditions and
an independent reviewer reconstructs the matched comparisons from saved traces; the later model
milestone needs held-out input custody, a frozen protocol, explicit allocation and admission, and
scored matched blocks with complete resource receipts (GTD:3).

M7 depends on EP-1 (GTD:49; GP:41-42; OD:106). No part of M7 can be rescued by spending more (OD:145).

## 3. Estimand

- **Primary estimand: OPEN (G-O2).** The repo says to freeze the contrast and its meaningful gain
  before evaluating (GTD:13, GTD:48) and lists the primary contrast as unverified (SE:19-20); it names
  none. Candidate contrasts the repo defines, not chosen here:
  - assignment policy at the same shared access, baseline = independent self-assignment with shared
    evidence (GTD:12);
  - evidence access within each policy, own against shared (GTD:12);
  - aggregate emergence baseline = deduplicated stage union of independent work with own evidence
    (GTD:12; GTS:14-15).
- **Unit of utility.** Distinct verified solution stages counted once in the union; a verified no-hit
  is a solved stage; a missing, blocked or malformed answer stays distinct; shard transmissions are
  costs, not utility (GTD:13; GTS:14-16).
- **Reporting.** Paired tasks; stage counts or stage-completion rates by regime; absolute paired
  effects, uncertainty and realised resource differences by regime (GTD:13, GTD:28). The
  evidence-access interaction is exploratory and kept distinct from the primary contrast (GTD:28).
- **Claim scope.** The complementary own-access cell excludes the information the join needs, so a
  scripted gain there only checks the information path (GTD:15). An authority-only claim needs matching
  worker order or a registered contrast; otherwise label the result for the implemented policy bundle
  (GTD:10). Rotation supplies no comparison of lead-specific decision quality when leads share one
  deterministic planner (GTS:30-32).
- **Cross-regime normalisation and the meaningful gain: OPEN (G-O2).** GTD:13 says to freeze them; no
  value is in the repo.

## 4. Arms

Four assignment policies crossed with two evidence-access settings, giving eight cells per block
(GTD:10-11; GTS:3-5).

| Factor | Levels | Source |
|---|---|---|
| Assignment | independent self-assignment; fixed lead; rotating lead/helper; peer coordination | GTD:10 |
| Evidence access | own verified evidence; shared verified evidence | GTD:11 |
| Regime | complementary; redundant; sequential | GTD:9; GTS:3 |

Held fixed across arms: task definitions, solver eligibility, scorer, resource envelope, receipt
visibility and release rules within each access arm, worker traversal order in the scripted replay
(GTD:10-11; GTS:5-6). Rotation costs two handoff units per cell in the scripted replay (GTS:31).
Whether worker order is held fixed or varied in the model run is OPEN (G-O14): GTD:10 says to record
it and label results accordingly, not which to choose.

State reset between arms and counterbalancing or randomisation of order within matched blocks, without
changing which worker receives each source (GTD:28). The randomisation scheme itself is OPEN (G-O14).

Model, snapshot, temperature and thinking setting for the workers: OPEN (G-O6). GTD:51 leaves model
choice open and no Grover figure exists (OD:106).

## 5. Endpoints

1. **Primary endpoint:** OPEN with G-O2 (the contrast). Its measurement is the distinct verified stage
   union per cell (GTD:13).
2. **Diagnostic counts, kept even when the verifier rejects them:** false guesses, no-hit guesses,
   redundant work, dependency delays (GTD:28); verified no-hit receipts and fallback uses (GTS:155-168).
3. **Charges:** reads, plans, blocked attempts, claims or dispatch, handoffs, work, shard publication,
   verification and deduplication, charged identically under the same ceilings, with actual costs shown
   separately (GTD:36). Scripted ceiling is 32 abstract cost units (GTS:4-5); its mapping to model
   calls and tokens is OPEN (G-O10).
4. **Scoring.** Receipt check first, then mathematical correctness; independent exact rational scoring
   with gate replay over a fixed iteration interval; solver output acceptance, score verdict and
   terminal verified union recorded separately (GTD:20, GTD:22). Exact rational equality scorer covers
   one to ten qubits and iterations zero to 128 (GTS:208-214, GTS:183-188).
5. Descriptive: stage counts by regime and by cap (SE:15-18; GTS:177-179).

## 6. Denominators

- **Stage denominator:** derived from the frozen public case for each stage (SE:5-7). For the protected
  blocks the per-block stage inventory is a custodian input (GCC:10); no number is stated here.
- **Aborted, stopped or budget-cut arms:** a budget-stopped prefix leaves the complete roster total
  unavailable (GTS:200-201); completion bounds are arithmetic sensitivity bounds for hypothetical
  completion (SE:15-18). The stopped-pair policy for the primary analysis is OPEN (G-O4; CB:35). Aborted
  blocks must be defined prospectively (GTD:28).
- **Missing is not zero:** a withheld result or parser failure never becomes a no-hit (GTD:21).
- **Number of blocks per regime, per cell and per branch (hit, no-hit, boundary):** OPEN (G-O3, G-O9).

## 7. Held-out construction, custody and blinding

- **Protected manifest.** Envelope and per-block fields as listed in GCC:7-11. A holdout custodian
  stages it independently, with an auditable split rule; holds out structural combinations and
  outcome branches as well as index positions; balances viable hit, no-hit and boundary cases without
  using model results (GTD:26). Marked-index relabelling at fixed marked count leaves the probability
  trace unchanged, so index position alone is not novelty (GTD:26).
- **Commitment.** Possible form: SHA-256 over a schema-specific domain prefix, a private 32-byte nonce
  and canonical manifest bytes; nonce and seed excluded from the receipt; receipt obtained separately
  from the run writer (GCC:13). The synthetic rehearsal binds canonical bytes under a Grover-specific
  domain and a 32-byte opening (GTS:129-131).
- **Worker input.** Workers see only the projected question and approved, previously released evidence.
  Full marks, expected answers, exact traces, family state and held-out seed material stay in the
  controller and verifier boundary; the audit trace stays out of the worker read path (GTD:19). The
  planner receives only ordered task IDs and per-worker ready task IDs (GTS:61-68).
- **Receipts.** Shard receipts and solved-stage receipts have distinct types and unique identities;
  citations resolve against an immutable verifier-side store; wrong-block, stale, wrong-source,
  same-round and invented receipts are rejected (GTD:20). Missing predecessor, verified no-hit and hit
  are distinct states; only the last two unlock a dependency (GTD:21).
- **Roles.** Protocol author defines split and eligibility; custodian builds and retains the private
  inventory and issues an authenticated receipt before execution; evaluator gets only authorised
  projections; reviewer checks the opening independently (GCC:27). Development examples stay outside
  the protected inventory (GCC:27).
- **Custodian and scorer: OPEN (G-O7).** No appointment exists (OD:7, OD:106; GP:41).
- **Split, generator revision and configuration digest: OPEN (G-O1).** The documented seeds are public
  development controls (GTD:26, GTD:48).

## 8. Sample size, power and stopping

- **Sample size: OPEN (G-O3).** The repo requires a defensible sample plan from authorised variance
  evidence (GTD:28; CB:35) and says independent inferential sample size and uncertainty remain
  unverified (SE:19-20). The 1,024 public arm-by-cap views and four deterministic public cases (SE:18)
  are scripted fixtures, not a variance estimate. FMT:144-162 gives the proposal's sizing rule for the
  R2 line; whether it applies to M7 is not stated in any M7 source (G-O3).
- **Statistical stopping rule: OPEN (G-O5).** SE:19-20 lists the stop rule as unverified; none is
  written.
- **Economic stop: OPEN (G-O10).** No M7 figure exists (OD:106).
- **Hard stop in code that already applies:** USD 10 across every ledger in the pinned directory
  (EP1:1202-1204; OD:114). Not an M7 allocation.

## 9. Analysis plan

Fixed in the repo:

1. Independently verified, deduplicated stage union from the traces; same-stratum baselines as in
   section 3 (GTD:12, GTD:35).
2. An independent replay reconstructs stage-level union and baseline from trace events (GTD:35); a
   reviewer reconstructs the matched comparisons from saved traces (GTD:3).
3. Paired contrasts by regime with uncertainty (GTD:13, GTD:28).

OPEN: the interval or test form, multiplicity handling across contrasts and regimes, and the
treatment of ties and floor or ceiling cells (G-O2, G-O3). No source gives them. A decision rule
(supported, killed, inconclusive) and kill criteria are not written in any M7 source: OPEN (G-O2).

## 10. What can run offline now

All of the following need no model call, no network, no key and no spend. They check the instrument
only, not model coordination (GTS:119-120; GTD:41).

| Item | Command or artifact | Source |
|---|---|---|
| Scripted 32-cell replay and digest check | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m lab.quantum.topology_transfer`; expected SHA-256 `6ce893d3c05d06df563dde15086bc3764e1e1b0efdcceebb650b303210115bdc` | GTS:36-45 |
| Focused test suites | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:lab:tests python3 -m unittest -v lab.tests.test_topology_transfer lab.tests.test_topology lab.tests.test_advisor_controls` (GTS:40-41 wraps it over two lines) | GTS:40-41 |
| Serialized trace audit with independent digest | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m lab.quantum.topology_audit /path/to/grover-topology-scripted-trace.json --expected-sha256 6ce893d3c05d06df563dde15086bc3764e1e1b0efdcceebb650b303210115bdc` | GTS:55-59 |
| Cap sweep (1,024 cells) | no command in GTS; only the pinned source closure `runs/grover-planner-projection.XwHcCX/source` (untracked) and sweep receipt `ab5dd8a1f6b371ca1994b3f3411bb0b1e44d883bdd34ca74a918aa8ddf2f59d1` | GTS:76-81 |
| Synthetic custody opening and refusals | `bash runs/grover-custody-current.JX6TFI/rehearse.sh` | GTS:124-127 |
| Observed release rehearsal (no-hit fallback, hit, own-access) | `bash runs/grover-release-current.AYSM67/rehearse.sh` | GTS:148-168 |
| Scheduled public release roster | `bash runs/grover-release-roster.Uc5aBs/verify.sh` (12 tests) | GTS:203-205 |
| Exact equality and gate arithmetic | `runs/grover-exact-boundary.s0ClQc`; `runs/m7-all-cardinality-exact.XrwDrI/OWNER.md` | GTS:183-191, GTS:208-222 |
| Public statistical envelope | `bash runs/grover-statistical-envelope.6Cln7i/verify.sh` | SE:3-8 |
| Custody checklist offline validation on synthetic fixtures | recompute commitment; apply split to both inventories; rebuild worker projections | GCC:15-23 |
| Offline acceptance table | receipt and visibility, distinct outputs, charges and boundaries, reproducibility | GTD:32-37 |

Every `runs/` item in this table (`grover-planner-projection.XwHcCX`, `grover-custody-current.JX6TFI`,
`grover-release-current.AYSM67`, `grover-release-roster.Uc5aBs`, `grover-exact-boundary.s0ClQc`,
`m7-all-cardinality-exact.XrwDrI`, `grover-statistical-envelope.6Cln7i`) is untracked: `git ls-files` returns
nothing for each (checked 2026-11-25).

Offline allowance covers documentation, CPU fixtures and review only (GTD:39). Re-running these is not
required to read this draft; the digests above are quoted from the cited files and were not recomputed
for this draft (G-O16).

Offline items still missing: a protected-fixture run needs the custodian's inventory, which does not
exist (G-O7, G-O8). The integrated Grover grid replay was listed as still needed in GTD:41; GTS
reports later integration passes (GTS:113-118), so whether that item is closed is for the independent
reviewer (G-O15).

## 11. Spend

- **Cap.** Paid calls up to USD 10 total across M2, M7 and D8, running total USD 0.00, no call made
  (ADMR:3). Hosted cost for M7 stays under that shared cap and under the code hard cap (EP1:1202-1204).
  The code hard cap covers every ledger in the pinned directory (EP1:1203), and that directory already
  holds spend such as Pilot 1's USD 0.0115 (EP1:1196). ADMR's "USD 0.00" therefore counts Tremor
  calls only, not the whole directory.
- **The EP-1 share is not assumed.** EP1:1189-1200 allocates the USD 10 across EP-1 (USD 5), `ar1`
  (USD 3), the instrument pilot and pilot 2, with USD 1.25 unallocated, and names no M7 line. ADMR:3
  separately says the USD 10 is shared with M2 and D8. The two do not reconcile on the repo's text, so
  no M7 sub-cap is taken from either.
- **M7 hosted figure: OPEN (G-O10).** "No Claude API figure or live allocation exists for Grover"
  (OD:106; GTD:49). Missing source: a named allocation and cost estimate from the Grover author,
  checked by the spend reviewer.
- **Price sheet.** The pinned sheet lapsed 2026-11-24 00:00 UTC; M2 and M7 need a named refetch, new
  digest, continuity review, exact window and a pricing-coverage re-ruling before any window (OD:33-43,
  section 2, P4). OPEN (G-O13); the refetch is a network step this draft does not
  perform.
- **GPU-hours.** The only recorded figure is a share of 9.4 GPU-hours pooled with the adapter,
  replication and controller (EPL:489; OD:106), inside the funded 70 GPU-hours (P:937). The M7 share is
  OPEN (G-O11); measured resource admission is required (OD:106; CB:35).
- **Cap is soft.** A direct API key has no provider-enforced cap; a Console workspace limit of USD 10
  or less is recommended and is an owner action (EP1:1218-1221). Unknown cost is not counted as zero.
- **Owner words, verbatim.** "Paid calls for up to $10 for Tremor" (ADMR:3). This is not a one-use
  admission bound to a batch and UTC window (ADMR:5).

## 12. OPEN items blocking a freeze

| ID | Decision or input still needed; exact missing source | Owner |
|---|---|---|
| G-O1 | Split rule, generator revision and configuration digest, development inventory digest. No such record in the repo (GCC:3, GCC:9; GTD:48) | Protocol author proposes; independent reviewer audits |
| G-O2 | Primary estimand and contrast, meaningful gain, cross-regime normalisation, interval or test, multiplicity, decision rule and kill criteria. GTD:13 says freeze them; no value exists (SE:19-20) | Protocol author and independent reviewer freeze (GTD:48); proposed owner: owner approves at freeze |
| G-O3 | Defensible sample size, from authorised variance evidence; blocks per regime and cell. Source needed: an approved variance pilot for M7; none exists (GTD:28, GTD:51; SE:19-20) | Protocol author computes; reviewer checks |
| G-O4 | Stopped-pair and aborted-block policy (CB:35; GTD:28) | Protocol author; reviewer |
| G-O5 | Statistical stopping rule (SE:19-20) | Protocol author; owner approves |
| G-O6 | Worker model, snapshot, temperature, thinking setting, team size. GTD:51 leaves them open; no Grover figure (OD:106) | Owner (model and spend); protocol author |
| G-O7 | Appointment of an independent custodian and scorer (OD:7, OD:106; GCC:27; GP:41) | Proposed owner: owner appoints (no source names who appoints; CB:35 names only an independent custodian/scorer) |
| G-O8 | Authenticated pre-execution custody receipt, and reviewed offline validation of the real manifest (GCC:11, GCC:13, GCC:29; OD:106) | Custodian issues; reviewer checks |
| G-O9 | Hit, no-hit and boundary quotas and branch balance targets (GTD:26; GCC:20). No numbers in the repo | Protocol author; custodian |
| G-O10 | M7 hosted spend figure and per-call, token and call-count caps; mapping of the 32 abstract cost units to model calls (OD:106; GTD:49; GTS:178-179) | Grover author proposes; spend reviewer; owner approves |
| G-O11 | M7 share of GPU-hours inside the 70-hour programme; measured resource admission (EPL:489; OD:106; GTD:49) | Resource reviewer; owner |
| G-O12 | EP-1 completion and Pilot 4 clearance, the stated prerequisite. Pilot 3 criterion 2 failed (263 output tokens against 150) (GP:18; GTD:49; OD:145) | EP-1 author; owner |
| G-O13 | Price-window refetch, new digest, continuity review, window instants, pricing-coverage re-ruling (OD section 2, P4) | Owner (refetch is a network step); spend reviewer |
| G-O14 | Worker-order policy in the model run (fixed or varied) and the counterbalancing or randomisation scheme (GTD:10, GTD:28) | Protocol author |
| G-O15 | Whether the integrated Grover grid replay named in GTD:41 is closed by the later GTS passes; independent event-level review (GTS:113-118; EPL:2122) | Independent reviewer |
| G-O16 | Pin a committed or archived tree: GTD, GCC, SE and the `runs/` items in section 10 are untracked; code tree hash and config hash not recorded; quoted digests not recomputed here | Integration owner; owner approves the commit. Also untracked: SE and every `runs/` item in section 10 |
| G-O17 | No native launch entry point for a model-run batch is cited in any M7 source; a one-use admission bound to batch and UTC window does not exist (ADMR:5) | Line author builds; owner admits |
| G-O18 | Independent review of this protocol | Independent reviewer |

## 13. What the freeze record must contain

Following FMT section 15 and the custody and admission lines of GCC:25-29:

1. Protocol SHA-256 of this file at the frozen commit.
2. Code tree hash and configuration hash at the candidate (G-O16).
3. Protected inputs, each with path, SHA-256 and custodian: manifest envelope, private blocks, split
   audit, opening location, custody receipt (GCC:7-11).
4. Model snapshot, scorer IDs, primary and secondary contrasts, economic and statistical stopping
   rules, expected and maximum resources (G-O2, G-O5, G-O6, G-O10, G-O11).
5. The admission: a one-use approval by the owner bound to the exact batch and UTC window, with
   resource limits (ADMR:5; GTD:49).
6. Approval and review evidence quoted exactly, including the independent review (G-O18).
7. The EP-1 clearance record (G-O12).

A freeze is a pre-registration, not a run authorisation; each batch needs its own admission.
