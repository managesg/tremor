# GPT consult (Codex worker via Orca), 2026-11-19

Source: a supervised Codex worker, launched in the `murmuration` workspace with a sanitized brief
(no names, data or secrets). Task task_ca5f70559a69, dispatch ctx_2343282c51a3, outcome succeeded.
Model: NOT stated in the reply; the launch used the session default (no model id was verified, the
owner's "Astra 6.2" could not be confirmed). Treat as advice from an unidentified OpenAI model, not
evidence. The worker ran in the owner's Codex YOLO mode (no sandbox); the brief told it to answer
from the brief only. Hooks were not trusted (option 3 chosen at the prompt).
Below: the worker's report, lightly reformatted, content unchanged.

## 1. Research question
Under a fixed task budget, does passing compact, provenance-linked, revocable state across agent
boundaries improve hidden-test task completion after context loss and stale advice, compared with
equally funded transcript retrieval and free-form notes?
Ship decision: make versioned handoffs a default if they improve paired pass rates by a prespecified
practical margin, reduce stale-advice failures on clean and perturbed tasks, and clear a cost
guardrail. If simple retrieval ties, ship retrieval. One GPU and a blocked sample of independent
maintenance tasks suffice to test a large effect; small effects are reported as inconclusive.

## 2. Three ways to fool yourselves
- Memory: more inference or leaked answers masquerading as better memory. Compare consolidation
  against equally funded task-time retrieval, charge both for total context and preprocessing, keep
  evaluation histories isolated. Start with source, scope and supersession. Cut ontology and weight
  editing from the first study.
- Efficiency: cheap inference masquerading as cheap completion. Charge router calls, warmup, idle
  attribution, retries and escalation to the same denominator. Compare a static cheapest-qualified
  policy and a fixed frontier policy before adding prediction. Cut green claims for hosted models
  without energy telemetry.
- Policy: a signed ceiling masquerading as safe delegation, and one transcript masquerading as a
  training corpus. Start with explicit task-scoped capability leases enforced at the tool boundary.
  Compare static leases with need-based grants against the same ceiling and tool surface. Cut learned
  rules and coupling heuristics until enough independent sessions exist.

## 3. Cross-model protocol
- Block by repository and task. Freeze commits, task text, hidden tests, tool schemas and mechanism
  configuration. Independently grounded maintenance tasks for conclusions, planted traps for
  diagnosis. Pilot on separate repositories, then 24 held-out tasks and three paired repetitions per
  model and arm. Serialize local GPU runs, rotate arm order, predeclare the minimum effect and the
  expansion rule.
- Example caps per task per arm: 20 minutes, 40 tool calls, 30,000 model input tokens including
  retrieved text, 8,000 generated tokens where observable. Calibrate on the pilot and freeze. Record
  native token counts and transferred bytes because tokenizers differ. Matched caps within a model;
  separate cost-quality comparison across models at overlapping dollar budgets. Charge offline
  consolidation over a preregistered reuse horizon and report the cold-start case too.
- Cross: memory off, equal-compute free-form retrieval, provenance-linked state with clean vs stale
  state. Hold tool rights fixed; test permission and routing changes in separate experiments. Score
  with hidden tests, build/lint checks and deterministic tool-audit predicates. Timeouts and rejected
  patches count as failures. Report paired repository-clustered intervals, cap hits, USD and measured
  whole-box joules per pass including failures. Mark hosted energy unavailable.
- Record checkpoint hash, quantization, runtime, sampling settings, provider version or fingerprint
  when exposed, timestamps. Pair seeds where supported, pair task and repetition everywhere.
  Interleave hosted arms, rerun sentinels, treat detected provider drift as a separate block.

## 4. One worker contract
Input: task id, parent id, immutable workspace revision, typed goal and acceptance checks, scoped
context handles, remaining budget, a verifiable capability lease. Output: patch or artifact
references, evidence, resource usage, explicit completion or failure status. Child dispatch uses the
same contract through the same scheduler. The hub receives a lease as a worker and uses the same
interface to dispatch a local model. Only the authority service can issue rights within the human
ceiling. Reserve child budgets before dispatch; isolated checkouts with explicit integration.
Failure cases: ambient hub privileges, capability laundering through child dispatch, nested fan-out
spending the same budget twice, conflicting patches, unverifiable completion claims. Validate tool
calls at execution, record results, make retries idempotent with task and attempt ids.

## 5. Confidentiality
Self-hosting and private tunnels can limit public tool exposure and keep local artifacts and execution
under owner-controlled infrastructure. Provider inference can still receive prompts, snippets,
retrieved context and tool results. The owner's host, connector, credentials, logs, backups and any
allowed egress remain trust boundaries. A tunnel authenticates a transport endpoint and does not
decide what data enters a prompt. Test synthetic canaries across model requests, subprocess egress,
connector output, logs and backups. Test tenant isolation, lease revocation and fail-closed behaviour
on tunnel loss.

## 6. Names (collision checks outside the brief; all unchecked)
Keelcast (top pick), Taskwake, Crewmark, Fleetpin, Helmrelay, Wakepost, Courselet, Oarlink.

## 7. Easy-to-miss engineering
Verify from a clean checkout with hidden tests inaccessible to workers. Treat generated repositories
as fault fixtures. Treat the 1,000-agent story as motivation and autoresearch as a controlled
mechanism test. Keep the expensive real-task generalization test small and separate. Instrument
cancellation, queue delay and human intervention alongside tokens. Include the single frontier worker
baseline before attributing any benefit to orchestration.
