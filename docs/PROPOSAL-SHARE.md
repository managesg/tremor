# Sortie: a small test program built on your talks

Draft for review, 2026-11-19; amended 2026-11-20 after two independent adversarial reviews (no
coverage table, prior art first, T7 and permission-log wording, citation rule). **Not sent to anyone.** Addressed to Lance Martin, Lydia Hallie,
CJ Avilla and Diogo Almeida. Drafted with an AI model (Claude Fable 5.2) from our notes and
machine-generated transcripts, so every quote needs a check against the recording first.

"Sortie" is a working name. We have **not** checked whether it is available (no registry, domain
or trademark search).

## Current program summary for publication review (2026-11-21)

Sortie tests when coding agents can coordinate through shared practices and when they need
enforcement in the harness. The first study compares a claim-before-work instruction,
the same rule enforced in code, and an arm without the rule. The arms share a task and
work budget, and three scorers check the logged outcomes. Pilot 3 completed 30 episodes
and selected shared task order. Its longest reply exceeded the preregistered clearance
ceiling, so the confirmatory experiment remains unfrozen and unrun.

The eight-line research program covers error correlation, memory transmission, monitor
selection, offline consolidation, norm carriers, permission decay, team size, and
activation readouts. Each line names a baseline and a measurable outcome. Current scripted
checks establish that the instruments behave on known fixtures. Scientific claims require
the matched, held-out comparisons specified for each line.

Sources for release review: [eight-line proposal](PROPOSAL-RESIDENCY-V3.md),
[EP-1 preregistration](../prereg/EP1.md), and
[Pilot 3 clearance](reports/workplan-ep/P3-clearance-criterion-2.md).
The owner still selects the exact publication copy, contact and destination.

## Earlier correspondence draft

The material below preserves the earlier handoff study and its attribution notes.

## 1. What Sortie is, and the one question

**Prior art first.** None of the mechanisms here is new: orchestrators, model cascades, signed
policy, governed memory with provenance and offline consolidation all exist, and published team
studies already compare soft practices with structural ones. What we might add is narrow: an
equal-budget test with deterministic scoring and open instruments, reported even if null.

Sortie is a small, open test bench for one problem: when work crosses an agent boundary (a
subagent returns, a session ends, a worker fails), state is lost or goes stale. We test one
mechanism for that, a **handoff record**: a short note passed across the boundary that is
*versioned* (each change gets a number), *provenance-linked* (each statement points to the log
line or file it came from) and *revocable* (a later record can withdraw an earlier one). Around it
is deliberately little: plain routing code, a human-held signing key, and models that all run
under the same contract. It is not a framework, not a product and not a model.

**The headline question.** At the same budget per task, do versioned, provenance-linked,
revocable handoffs lose less pass rate when things go wrong than equally funded search over the
raw log, and does the answer differ between a small local model (at most 9 billion parameters)
and a Claude tier?

"Things go wrong" means five seeded *perturbations* (disturbances the test harness injects, one
per run): **P1** the requirement changes mid-task; **P2** the requirement is noisy; **P3** a wrong
or stale memory is injected; **P4** a worker fails or is slow; **P5** a permission is denied while
a safe allowed route exists.

The score is **robustness**: clean pass rate minus perturbed pass rate, compared between arms on
the same task and seed, with a 95% interval. Passing is always a deterministic check, never a
model grader. Beside it we report a harm rate (runs that touched a protected file, leaked a
planted marker string, or acted outside their permission) and cost per passing task.

**Decision rule, set before any run.** If handoffs beat search by at least 10 points with an
interval that excludes zero, without losing clean pass rate or raising harm, we build the handoff
store. If they tie or search wins, we ship search and delete the store. The first pass is small
(240 runs per model), so only effects of about 15 points will be visible.

**We have no results.** Section 6 says exactly what exists.

## 2. Building on your work

Each section gives what we took (talk claims unless marked), the figures and whether we could
verify them, what we test because of it, the gaps we found, and one question.

### 2.1 Lance Martin, "Exploring Claude's Frontier"

**What we took (talk claims).** A team of one lead and 999 helpers formalised Fermat's Last
Theorem in Lean with only Git and a SQL database as shared tools. We do not read this as a
no-harness result: per the two written posts we opened, the agents were given lead and helper roles, the 60
target statements, a one-sentence route sketch, definitions and 47 already-proved lemmas, and
Lean checked every proof. The agents, not the prompt,
created the coordination tables; Lance: "We didn't tell them to these tables" (transcript as
recognised). On memory: agents write notes greedily inside a session, while memory needs to be
"globally coherent and not redundant"; an offline pass ("dreaming") can repair it: "a poison
memory was injected and it's stuck there. Dreaming can rescue that."

**Figures and status.**

| Figure | Status |
|---|---|
| 1,000 agents, 60 statements, five tables, no network in sandboxes, classifier plus offline monitor | Confirmed in the written post we opened. The post gives 28.7 hours (talk: about 30), lists 47 proved lemmas given as input, and calls the run a "toy experiment" |
| 12,929 writes and 147,425 reads at hour 5.3; 125 to 209 of 999 helpers idle | Read by us off slide screenshots; may contain reading errors |
| CL-Bench database task, score with a memory store against without, six models (for example Opus 5.5 0.838 against 0.655; Sonnet 4.6 0.364 against 0.330) | Slide-read. The benchmark repository and paper exist and were opened |
| Search alone 53%; wiki alone 13% after 2 dreaming sessions rising to 48% after 128; wiki plus search 54% rising to 61% | Slide-read. The written post puts sessions (2 to 128) on the axis; the slide labels it 2M to 128M with the note "budget of 1M tokens per session, not measured spend". Tokens actually spent are not given |

**What we test because of it.** Plain search over the raw log is our main baseline, because on
that slide it is the hardest thing to beat. Injected wrong memory is perturbation P3. Any offline
consolidation is charged inside the same budget as the arm it competes with.

**Gaps, offered respectfully.**
1. The memory gain looks like a *threshold*, not a gradient. From the slide values the gain is
   near zero for the weakest model, largest for the middle ones and smaller at the top, where the
   no-memory score is already high. As a share of remaining headroom it is roughly flat (0.44 to
   0.61) for five models and 0.05 for one. This is our arithmetic on six slide-read points.
2. The CL-Bench paper's abstract says "naive ICL outperforms systems dedicated to memory
   management" (ICL: in-context learning, putting the history in the prompt). That deserves a
   line next to the memory-store result.
3. Dreaming returns diminish. Wiki alone gains 35 points for 64 times the dreaming sessions (2
   to 128; a budget, not measured spend); wiki plus search gains 7, and beats search alone by 1
   point after 2 sessions and 8 after 128. With 25 questions, 8 points is two questions, and no
   interval is shown.
4. The poisoning rescue is one game. We could not tell how many runs or seeds it rests on.
5. The read-to-write ratio (about 11 to 1) could be coordination or polling.

**Our question.** For the wiki result, how many tokens did the dreaming sessions actually spend,
and what does search alone score if it is given the same amount?

### 2.2 Lydia Hallie, bounded autonomy in Claude Code

Our notes come from a machine transcript of a re-recording; we have no verified link.

**What we took (talk claims).** Wherever the human steps out of the loop, the model, the harness
or the environment has to take over. Guarantees come from the harness: deny rules are checked
before the auto-mode classifier. The test for what must be a rule (as in our notes): "if Claude
gets it wrong once, can I take it back?" Permissions decide whether a tool call runs, not what it
can reach once running, so the environment needs limits too; the sandbox covers shell commands
only.

**Figures and status.**

| Figure | Status |
|---|---|
| People caught about 14% of dangerous commands; auto mode caught 89% | Confirmed in the 7 August 2026 announcement. The exact figure is **13.6%**, with 1,053 paid testers in a staged test who knew they were being evaluated |
| Hook exit code 2 blocks and returns feedback; exit 1 does not | Confirmed in the docs, with exceptions for some events |
| Deny rules are evaluated before the classifier | Confirmed from the documented decision order; no page states it as a sentence |
| A "doctor prompt audit" command | **Not found** in the docs. We found `/doctor` and `claude doctor`, neither named that |

**What we test because of it.** Her rule of thumb is our harm definition: actions that cannot be
taken back (protected-file change, secret reaching a transcript) count as harm whether or not the
task passed. Her observation that the same prompt yields different small decisions is why we score
robustness under P1 to P5, not a single pass rate. P5 tests denial with a safe route.

**Gaps, offered respectfully.**
1. Deny rules are not an absolute guarantee for shell commands. The docs say Bash deny rules
   match the command string, so `Bash(rm *)` does not stop `/bin/rm` or `bash -c 'rm ...'`, and
   they recommend a hook or the sandbox for a hard guarantee.
2. The March 2026 engineering post reports a 17% false-negative rate on real overeager actions
   (52 cases). It is worth saying beside the 89%.
3. Allow rules are documented as lasting "Permanently per repository and command". We found no
   expiry setting, so there is no evidence either way on whether old allow rules should lapse.
   We wanted to test that and cannot: our own permission log is far too small.

**Our question.** Is there data on how often a permanently allowed rule is used again after a
long idle period, and would an expiry on allow rules be considered?

### 2.3 CJ Avilla: the trust talk, and the multi-agent talk with Harrison Stall

**What we took from "Building Trustworthy AI Agent Systems" (talk claims).** Trust is being
willing to be vulnerable when you cannot fully monitor; supervision does not scale, so the aim is
to shrink the space where trust is needed: "design for appropriate trust, not greater trust"
(attributed in the talk to Lee and See, 2004). Four layers: model, bound, watch, respond. The key
idea: a base policy, a ceiling policy "signed by a human", and per-session policies that "grow or
shrink based on evidence"; the example shrink is an agent that "hasn't actually used GitHub for
two weeks". Also: credentials kept out of the agent loop; offline audit of sessions against a
written policy; the ability to interrupt everything, revoke keys and sign a narrower ceiling.

**"Why One AI Agent Isn't Enough (And How to Run 1,000)".** We have no transcript, only a topic
list: Flows, budgets, interrupts, credentials outside the agent. We would rather read it than
guess.

**Figures and status.**

| Item | Status |
|---|---|
| Policy files covering domains, paths, HTTP methods and executables; request, human approval, reload | Confirmed in the NVIDIA OpenShell docs. The policy advisor is off by default, and automatic approval is an opt-in |
| Shrinking unused grants | Not found as a documented feature in the three OpenShell pages we read; "two weeks" is the talk's example, not a measured window |
| Per-session budgets and per-tool policies on Managed Agents | Found on pages we read only in part |
| "Flows" | The page we tried returned 404; we do not know the current name |

**What we test because of it.** Our permission design is his, reduced: a human-signed ceiling, a
deny list, an expiry, and a task-scoped **lease** (a short-lived list of allowed actions, checked
at the moment a tool runs). "Respond" becomes a test: revocation must take effect on the next
action.

**Gaps, offered respectfully.**
1. Grow and shrink has no stated stopping rule. An audience question asked what stops an agent
   requesting more than it needs, or blocking itself and stalling. The answer was that a human
   decides whether to promote a repeated request. That leaves both failure modes unmeasured.
2. We found no evidence, in the talk or the docs, for any particular shrink window.
3. A signature shows who approved a policy. It enforces nothing by itself, and a key that a
   model process can read is not held by a human in any useful sense.

**Our question.** What would you measure to tell an agent that over-requests from one that
under-requests and stalls, and is there data from the reference implementation?

### 2.4 Diogo Almeida, "Beyond Better Assistants"

**What we took (talk claims).** Reliability matters more than occasional brilliance. Agent
design is constrained by the *KV cache* (the stored intermediate computation that lets a model
skip re-processing a prompt it has seen; providers bill it as cache writes and reads): "they're
so inflexible in their design because of the tyranny of the KV cache". He asks why memory grows
with history length, why parallel agents "need to rediscover the same patterns of the codebase
over and over", and why "even naive routing doesn't work". He presents these as open
questions. The cache material is about 90 seconds of the talk; the cost argument is in his blog.

**Figures and status.**

| Figure | Status |
|---|---|
| Cost shares from a slide: cache read about 67%, output 18%, input 12%, cache write 3% | **Unconfirmed.** The blog chart is an image; its text says only that output is "just 9-18% of the total bill" |
| Price basis | The blog assumes an older price sheet with cache reads at 0.1 times input. Current prices are 0.025 to 0.05 times, so the shares would shift toward output and writes |
| "Memory is O(N), why not log N" | The transcript reads "o of nan" and "login"; the mathematical reading is our inference. No paper we opened establishes logarithmic memory for agents; the one formal log-growth result concerns attention state inside a model |

**What we test because of it.** Every result carries tokens by class (input, output, cache write,
cache read) for planner, verifier and worker separately, so a design cannot look cheap because
another role paid. We price the cold-start cache write of a fresh subagent, which sets a minimum
task size worth delegating. Handoffs are our small version of his call to do state management instead of
assuming global state.

**Gaps, offered respectfully.** The chart's numbers are not recoverable from the page, and it is
drawn at cache-read prices that have since fallen two- to fourfold. That routing "fights the
cache" is argued, not measured, in what we read.

**Our question.** Could you share the numbers behind the cost-share chart, and would you redraw
it at current prices?

## 3. First principles and complex systems, as testable claims

A complex-systems concept enters only if it gives a number that can come out wrong, and is tested
first on *scripted backends* (small deterministic programs standing in for a model: no GPU, no API
cost), which check the instrument and show nothing about models.

**What we test, and what we do not claim.** We test one thing at a time against a baseline that
ignores it: here, handoffs against equally funded search under seeded perturbations; in the
companion programme, one coordination rule given as a written card against the same rule enforced
in code. We do not claim coverage of any research area, any result about models, or that agents
self-organise; stigmergy, near-decomposability, Ostrom's local rules, requisite variety, lock-in
and consolidation are framings for single tests, not findings. We keep a private gap list of what
we cannot test and why; it is not a coverage claim and is not part of this draft. Criticality and
scaling laws stay parked until they yield a prediction that can fail.

**The first-principles rules.**
- **Five-step filter**, in order: question the requirement, delete, simplify, accelerate,
  automate. We use it as a discipline, not as authority.
- **Units.** Every quantity has a unit; ratios show numerator and denominator; missing is
  recorded as unknown, never zero.
- **Matched budgets.** Every comparison holds one budget fixed and varies one thing. Memory
  reads, note-writing and offline passes are charged inside the cap.
- **Run gate.** Run something only if the chance it changes a decision, times the value of that
  decision, exceeds its cost. A result that cannot change what we do next is not run.

**Each cut is itself an ablation.** No decay rule: static expiry is the baseline decay must beat.
No model-based dreaming: search is the baseline dreaming must beat. No board: assignment by the
router is the baseline a board must beat. No learned rules, no predictive routing: the static
cheapest-qualified tier is the baseline. If the simple version ties, the concept stays out.

## 4. Architecture

- **Key.** A human-held key signs each policy. It shows who approved; it enforces nothing. It
  stays out of every model's reach only if it lives off the machine or behind a passphrase.
- **Router code.** Deterministic code started by a person. It reads task specs, launches workers,
  runs checks and writes cost lines. It never calls a model to decide a route.
- **Every model is a cell,** the strongest included. A *cell* is a folder: a prompt, a policy, a
  budget and an append-only, hash-chained log. Scripted, local and Claude cells share a file
  format, not a security property.
- **Planner cell.** A strong model orchestrating weaker ones only writes task specs. It never
  launches a process, and its tokens are counted like any worker's.
- **Leases** (design, not built: today the code checks a per-cell allow and deny list and token
  and time caps). Task-scoped, expiring, checked when the tool executes; default deny, deny wins.
- **Evidence bundle.** Result, check output, cost by token class, seconds, joules or unknown, USD
  or unknown, model ID, lease hash, log range.
- **Independence.** A result is not verified by a cell with the same model ID unless a
  deterministic check exists.

**Confidentiality, stated accurately.** No arrangement that uses a hosted model keeps session
content from the model provider: every prompt, every file the model reads and every tool result is
sent. Self-hosted environments keep execution and files on your machine, not the transcript. The Claude Code sandbox limits shell commands only; file tools, hooks and MCP servers
run outside it. MCP tunnels reach a private server without an open inbound port, but each tool
result still becomes session content and a third party is on the path. Only a local model's raw
log, and inputs it receives by path and hash that no hosted model reads, stay local. We plan to
check this with planted marker strings; that test is not built.

## 5. One protocol for any model, and the cost columns

1. One agent loop, task spec and tool schema for every model, with one adapter per backend. A
   shipped product is a separate, labelled arm.
2. Frozen code, task text, hidden tests and settings; conclusions only from held-out tasks.
3. The same cap for every arm: turns, input and output bytes, and seconds. Bytes, because
   tokenisers differ. Timeouts count as failures.
4. Each batch includes a scripted floor that must fail and a scripted oracle that must pass,
   or the batch is void.
5. Models interleaved, arm order rotated, a fixed sentinel set around each batch to detect drift.
6. The model ID returned in each response is compared with the one requested; a mismatch voids
   the run.

**Costs, never added across kinds:**

| Column | Unit | Note |
|---|---|---|
| Tokens per passing task | tokens, by class and by role | From usage fields or local counts |
| Energy per passing task | joules | Local runs only, a raw log field, never a headline: sampled GPU board power times time on a shared engine, not CPU, memory or cooling. **Hosted energy is "n/a"**; we make no efficiency or "green" claim |
| Money per passing task | USD | At a dated price sheet. Local USD is "n/a" until an electricity tariff is set |
| Seconds | wall clock | Reported, not a headline |

## 6. What exists today, and what failed

**Built and independently verified** (three verification passes by a separate model with fresh
context, accepted with notes): run manifest, statistics, permission ledger, reuse-hazard
estimate, token and cost accounting, memory lint, co-change coupling, trap benchmark, runner and
command line. 85 tests passed 20 times in a row. In the same breath: the harness has needed
several verification rounds because it was wrong each time before; the model-facing layer was
rejected once (it accepted unknown task ids and broke its round rules) and its fix is not yet
re-verified; the instrument pilot with a real model has not run; no batch has been run.

**Built, not yet verified:** the cell and router modules and the perturbation harness. The tree
holds 110 test functions; the newer ones were counted, not re-run, for this draft.

**Failed or blocked.**
- The permission log is too small: 1,079 events and 11 denials, but from one session; 30
  sessions is our recruitment target, not a validated sample size. The decay question is parked.
- The local GPU smoke test was stopped repeatedly by a memory watchdog. Host memory leaks at
  roughly 22 MB per step and the cause is not isolated. Three 20-problem smokes later completed
  (0/20, 8/20, 1/20 at an 8,192-token cap, most generations cut at the cap, different decoding
  per arm): configuration results, not an effect of the weight edit.
- **Nothing has been hypothesis-tested. No pre-registration is frozen.**
- One exploratory measurement: in 42 local sessions, cache reads were 93.7% of tokens (tokens,
  not cost; one user, one machine).
- About 59,000 words of documents against under 2,000 lines of code. Our rule now: no new
  hypothesis until one pre-registration is frozen and run.

**Prior art.** Orchestrators, model cascades, signed policy, governed memory with provenance,
and consolidation all exist. Our possible contribution is narrow: an equal-budget test of
handoffs against search under seeded perturbations, and open instruments.

## 7. What we would like from you

Small asks. Any one would help; none is expected.

- **Lance:** the measured token spend behind the 2-to-128-session axis of the wiki evaluation,
  and the search score at that same spend; how many runs the
  poisoning rescue rests on; whether per-table read counts can be split into useful reads and
  polls.
- **Lydia:** the correct name of the prompt-audit command; any data on reuse of old allow rules;
  whether a task-scoped, expiring permission checked at tool execution fits the harness.
- **CJ:** links to the two reference implementations shown as QR codes; slides or a recording of
  the multi-agent talk; your view on measuring over-request and self-block.
- **Diogo:** the numbers and assumptions behind the cost-share chart; which sub-linear memory
  design you find most promising.

**What we offer.** The instruments are standard-library Python and can run on logs we never see.
We will share the pre-registrations before any run, and the results either way.

**What we are and are not asking.** We are not asking for endorsement, funding, access or
non-public data. Nothing here is published; the repository has no licence yet and is not public.
Model runs and publication each still need the project owner's separate decision. Three internal
cuts (a shared board, a coupling gate, a scripted re-verify arm) are proposed for reinstatement and
are not decided.

## 8. Sources and verification status

**Citation rule.** Before any public claim we cite the primary paper, post or official artifact,
with its denominator, policy and operating point, and we never import a reported rate (13.6%, 89%,
17%, the CL-Bench scores, the wiki curve) as our expected effect size or power assumption. Our
tests cannot establish any of those figures; they can only be set beside our own measured ones.

| Source | How we read it | Status |
|---|---|---|
| Talks by Lance Martin (12 Nov 2026), CJ Avilla (trust talk) and Diogo Almeida (11 Nov 2026) | Machine transcripts; Lance's slides from screenshots | Quotes unchecked against recordings; slide figures may have reading errors |
| Lydia Hallie talk | Machine transcript of a re-recording, via our notes | No verified recording link |
| CJ Avilla and Harrison Stall, "Why One AI Agent Isn't Enough" | Not read | Topic list only |
| "Safely scaling multi-agent teams with Claude Fable 5.2" (9 Nov 2026) | Opened | Confirms the run's setup; the hosting domain was not confirmed as official |
| "The components of agent memory" (Lance Martin) | About half read in the first pass; read in full in a later pass (our note 14) | Wiki axis is sessions (2 to 128); percentages match the slide; figures (images) not read |
| CL-Bench repository and paper (arXiv 2606.05661) | README and abstract | Apache-2.0 |
| Auto mode announcement (7 Aug 2026) and engineering post (25 Mar 2026) | Fetched in full, searched | 13.6%, 89%, n=1,053; 17%, n=52 |
| Claude Code docs; Claude pricing page | Fetched 19 Nov 2026 | Undated pages |
| NVIDIA OpenShell docs | Four pages opened | Absence claims cover three of them |
| "(KV) Cache Rules Everything Around Me" (9 Sep 2026) | Full text | Chart image not read |
| Mayer, Davis and Schoorman; Lee and See; Simon; Ostrom; Ashby; Arthur | Not opened by us | Cited second-hand |
| A "72% cost saving from cache fixes" figure in our notes | Not found in any written source | Not used |
| An outside consult with an OpenAI model whose identity we could not verify | Advice only | Not evidence |
| Two further adversarial reviews (an OpenAI model and a Cursor agent, identities unverified), 2026-11-20 | Advice only, from a brief | Not evidence; verdicts in our internal notes |

verified (2026-11-20 amendments): 36bab4b (plus working tree) 2026-11-20
