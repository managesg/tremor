# murmuration: hub and cells

Date: 2026-11-19. Status: **design only. Nothing here is built or run** (uncommitted `cell.py`
and `router.py` appeared in the working tree on 2026-11-19; not verified). `PRINCIPLES.md` wins
any conflict. Platform facts: `research/07`. Weight edits: `research/08`. Local models:
`research/09`. Hypothesis and gate IDs: `PLAN.md`. Plain-language summary: `VISION.md`.

## 1. The design in one paragraph

One hub, many cells, star topology. The **hub** is plain code plus the owner's signing key; it
is not a model (section 2 names its three parts apart). A **cell** is a directory the owner can
read and edit: a prompt, a signed policy, an append-only log, a memory file, a budget and a model
(none, a local model with an adapter, or a Claude model). **Every model is a cell, the strongest
included.** "Plan", "verify" and "judge" are task classes like any other: a hub-as-worker is a
Claude cell whose `cell.json` names a stronger model, and its tokens appear in its evidence
bundle like any cell's. They exchange four plain files. The routing table decides who executes:
send every task class to Claude cells and it is central; send classes to local cells and it is
decentral. It does not decide who reads: a Claude planner cell still reads every task it plans
(section 6a). The three worker kinds share a file format, not a security property (section 3).
Which classes may move is an empirical question (H6).

## 2. Hub: three parts, named apart (amended 2026-11-19, adversarial review 2, section 1)

| Part | What it is | What it does | What it never does |
|---|---|---|---|
| Owner key | The owner's signing key | Signs policy (section 4, file 1) | Sits where a model process can read it, if the owner protects it as below |
| Router code | Deterministic code, started by the owner, outside any Claude Code sandbox | Reads task specs, applies `routes.json`, launches worker cells, runs deterministic checks, lints digests, writes cost lines | Calls a model to make a routing decision |
| Models | Cells (section 3) | Planner cell: writes task specs. Verifier cell: judges where no check exists. Worker cells: do tasks | Sign anything; launch other cells |

1. **Signs the ceiling.** A planner cell may draft a policy; only the owner's key signs it. A
   model that could sign alone could be talked into it. Keeping the key from every model is an
   intention, not yet a property: on this box the owner's sessions run as the owner's user and
   file tools run outside the shell sandbox (`research/07`), so a key file under the owner's home
   is readable unless it is off the box, on a hardware token or passphrase-protected. The
   signature proves who approved a file; it does not enforce it. Enforcement is `cell.py` or
   Claude Code permission rules.
2. **Decomposes.** A planner cell splits work only when the coupling gate (H2) says the parts
   are nearly independent, and gives each task a class. Its output is task specs; the router
   launches the workers. Claude orchestrating local models is exactly this: a planner cell. It
   never launches a process, so no cell needs `docker.sock`.
3. **Verifies with independent context.** The verifier sees the task spec and the evidence
   bundle, never the worker's reasoning. Deterministic check first. **Rule:** a cell's result is
   never verified by a cell with the same model ID unless a deterministic check exists;
   otherwise it goes to a different tier or to the owner.
4. **Judges.** Accept, reject, or escalate to the owner; accept or reject memory digests.

Costs of this split, stated: a planner cell needs a wide read ceiling, so "narrow authority"
holds for workers only; planning has no deterministic check, so planner quality is judged only
downstream; a Claude cell is a subagent or headless session whose enforcement is permission
rules plus the shell-only sandbox.

Terminology: where this file or another says "the hub" plans, proposes, verifies, edits weights
or is a "hub model" (notably sections 6, 11 and 12, `VISION.md`, `PLAN.md` H7 and T7), read
"the strongest model cell". "The hub" as an entity is router code plus the owner's key.

Router code does not read a cell's raw log by default. A model never holds a cell's secrets by
design, but a Claude cell's whole context is session content sent to the model API (section
6a), and a digest lint that resolves source pointers reads the log: that lint is router code,
never a model.

## 3. Cell

```
cells/<id>/
  cell.json      worker kind, model id, adapter sha256, decoding config, task classes
  prompt.md      system prompt
  policy.json    + policy.json.sig
  inbox/ outbox/ task and result files
  log.jsonl      append-only; each line carries the sha256 of the previous line
  memory.jsonl   PLAN 5.2 record schema: source, confidence, valid_until, supersedes
  adapters/      optional; base weights live elsewhere, read-only and hashed
```

Three worker kinds, one file format (not one security property). A planner or verifier cell is
the Claude-subagent kind with its own `cell.json`, policy, budget and log:

| Worker | Where authority is enforced | Honest limit |
|---|---|---|
| Stub (no model, plain code) | `cell.py` is the only code that acts; it checks every capability key against the policy | Narrow by construction, not an OS boundary |
| Claude subagent | Restricted tool list, permission rules, Claude Code's shell sandbox | The sandbox covers shell only. Read/Edit/Write/WebFetch, MCP servers and hooks run outside it. Bash deny rules can be bypassed (SCIENCE 7.2a). |
| Local model (after GPU gates) | `cell.py` runs the model's tool requests after the same key check; optionally a container with only the cell directory mounted, no network | Cannot be a Claude Code session (file 07). It is a custom worker process. |

The log is tamper-evident, not tamper-proof. Memory records are superseded or expire, never
deleted.

## 4. Contract: four files

Plain JSON, checked by hand-written code.

**1. Policy** (hub to cell, signed).
```json
{"version": 3, "cell_id": "extract", "issued_at": "...", "expires_at": "...",
 "prev_sha256": "...",
 "base":    ["Read:cells/extract/**"],
 "ceiling": ["Bash:python3", "Write:cells/extract/outbox/**"],
 "deny":    ["Bash:curl", "Read:**/.env"],
 "decay":   {"tau_days": 14},
 "budget":  {"tokens": 200000, "wall_s": 900, "usd": 0.50}}
```
- `base`: always allowed. `ceiling`: the most a session may grow into without asking. `deny`
  wins over both.
- **Session grants are not in the signed file.** A key inside the ceiling is granted on first
  observed need and dropped after `tau_days` idle, by the existing `grow_decay` logic in
  `ledger.py`, recorded in the log. A key outside the ceiling returns `status: escalate`; only
  a new signed version widens the ceiling. Tau is a placeholder until H1 picks one; path-glob
  keys extend the ledger's current `Bash:<first token>` key.
- Signature: `ssh-keygen -Y sign` with a dedicated owner key; cells hold only the public key
  and call `ssh-keygen -Y verify`. OpenSSH is on this box: no new dependency. Untested here.
- An expired policy, a bad signature or a broken `prev_sha256` chain is refused.

**2. Task spec** (hub to cell): `task_id, class, goal, inputs [{path, sha256}], check {cmd,
expect}, budget, policy_sha256, route_reason, coupling_score`.

**3. Result and evidence bundle** (cell to hub): `task_id, status (pass | fail | blocked |
escalate), outputs [{path, sha256}], check_output, cost {tokens_in, tokens_out,
tokens_cache_read, tokens_cache_write, wall_s, joules_gpu or null, usd}, model_id, adapter_sha256, policy_sha256, log_range {first, last line
hash}, requested_keys`. A missing cost field is recorded as null, never as zero.

**4. Memory digest** (both ways): `digest.jsonl`, one candidate record per line, plus the
sha256 of the cell's store. The hub lints each record (source pointer resolves, no secret
pattern, scope allowed), then accepts it into the shared store or rejects it with a reason.
Records sent down arrive as `confidence: imported`. A local cell's raw log is not sent to any
model: the router code resolves pointers. A Claude cell has no such property: everything in its
context already went to the model API when the cell ran (section 6a).

## 5. Transport

| Option | Cost | Verdict |
|---|---|---|
| Files in the cell directory, atomic rename, git for history | Zero; stdlib; no port, no daemon | **Chosen.** The hub starts a cell as a subprocess (`python -m murmuration cell run cells/<id> <task>`). Git history waits for gate G0. |
| MCP server wrapping the same files | A process and a config entry | Later, only if a Claude Code session must call a cell as a tool |
| HTTP on loopback | A port, which needs owner approval (G4) | Only for serving a local model. Never for the contract. |

## 6. What exists on the Claude platform, and what is new

| Part | Exists today (file 07) | New here |
|---|---|---|
| Planner and verifier cells | Claude Code session with subagents; hosted Managed Agents coordinator (full self-host: only a coordinator with 1 to 20 listed subagents) | A verifier bound to a signed policy and an evidence bundle |
| Narrow cell sandbox | Claude Code `sandbox.filesystem.*`, `sandbox.network.allowedDomains`, permission rules | Deriving each cell's allowlist from one signed file |
| Signed policy | No. Managed and server settings are config, not signed; agent identity signs tokens, not policy | Signer and cell-side verifier |
| Grants that decay | No documented expiry of allow rules (7.2a) | Session grants under a ceiling (H1) |
| Cell-local memory with digest sync | No. Memory stores are hosted by Anthropic, or by your server in full self-host | `memory.jsonl` plus digest lint |
| Local small model per cell | Not a documented use: gateway model IDs must name the same model | Custom worker process |

Not used: self-hosted Managed
Agents (private beta; no dreams, scheduled deployments or Files API), Claude Code self-hosted
environments (control plane and transcript stay at Anthropic), MCP tunnels (research preview).
If the owner wants self-hosted environments or MCP tunnels, this line and `PLAN.md` 4.5 change,
and their limits (Team or Enterprise only, GitHub checkout only, no Zero Data Retention,
research preview) become project constraints. That is an owner decision; nothing here assumes
it. The Claude Code sandbox filters network by client-supplied hostname and the docs name domain
fronting as possible, so a no-network cell needs a container or firewall. File 07's mapping of
"dynamic workflows" to "Flows" is an assumption; nothing here depends on it.

## 6a. Confidentiality: what stays local and what reaches the model provider

Source: `research/07` via `docs/reports/adversarial-review-2.md` section 2. File 07 read the
MCP-tunnel and several self-hosted pages only in part; gaps are marked unknown.

"Claude on localhost" is a misnomer. In every Claude shape in file 07 the model runs at
Anthropic or at a cloud provider. What can be local is tool execution, files and, in one
private-beta shape, the session store. **No Claude shape keeps session content from the model
provider.** Every file a Claude cell reads, every tool result and every prompt is session content.

| Shape | What it does keep local | What still reaches the provider | Fits | Does not fit |
|---|---|---|---|---|
| Claude Code self-hosted environments | Session execution, checkout, files at rest, tool side effects | Session transcript (Anthropic stores it); control plane; session content goes to `api.anthropic.com` even with Bedrock. No ZDR or HIPAA organisations; Team and Enterprise; GitHub or GHES checkout only | Keeping repositories and credentials off a vendor's execution host | Confidentiality of anything the model reads; choosing it also rules out ZDR |
| Claude Code sandbox | Limits what shell commands can touch | All session content. Read, Edit, Write, WebFetch, MCP servers, hooks run outside it; network filtered by client-supplied hostname | An injected or mistaken shell command | Exfiltration through a file tool, hook or MCP server; confidentiality from the provider |
| MCP tunnels | A private MCP server reached by one outbound connection | Every tool result returned through the tunnel becomes session content. A third party (Cloudflare) is on the path. Unknown: end-to-end encryption through the tunnel provider and what it can log | Not opening an inbound port | Confidentiality from the provider or the tunnel operator |
| Self-hosted Managed Agents (private beta) | Session history in your own database; model requests go where you choose | The model still sees the content | Owning the session store | Hiding content from whichever model serves it |
| Local open-weight cell | Its raw log and the inputs the router passed by path and hash without any model reading them | Its result, check output and digest, if a Claude planner or verifier cell reads them | Content no Claude cell ever reads | Any task a Claude planner wrote or read |

The owner's sessions on this box go through a local proxy whose fallback chain can answer a
"Claude" request with another provider's model, and those providers' retention terms were not
reviewed (backend `AGENTS_SYSTEM.md`). Experiment runs therefore use a direct key and check the
model ID returned in each response (`PLAN.md` 4.4, 4.6).

## 7. What the owner can edit

A new concept is tapped in by adding a cell directory, a memory record or a route row. No code
change.

| What | File | How a change takes effect |
|---|---|---|
| Policy | `policy.json` | Edit, bump `version`, sign. Unsigned edits are refused. |
| Memory | `memory.jsonl` | Append a record that supersedes the old one, `author: owner` |
| Prompt | `prompt.md` | Edit. The cell's config hash changes, so its route measurement is void until re-measured. |
| Adapter, weights, decoding | `cell.json`, `adapters/` | Point at another adapter hash or decoding config. Base weights are never modified; an edited model is a hashed copy. Same invalidation. |
| Routing | `routes.json` | Edit the floor or the tier order per class |

## 8. Routing: the cascade and the run gate

`routes.json` holds, per task class, a quality floor and tiers ordered by measured cost per
passing task (stub, local model, Claude cell, stronger Claude cell), each with held-out n, pass
rate, CI lower bound and the config hash it was measured on.

1. Choose the cheapest tier whose **held-out CI lower bound clears the floor** and whose config
   hash still matches. An unmeasured class goes to the Claude tier.
2. Run it and apply the task's deterministic check.
3. On failure escalate one tier, up to the strongest model cell, then the owner. No unchanged
   retries. A planner cell does not assign a task to its own model ID when no deterministic
   check exists (section 2, rule 3).

Planner and verifier tokens are cell cost too: they are logged in the same evidence-bundle
schema, so the share of tokens spent planning and verifying per passing task is reported and
"decentral" cannot look cheap while the planner spends most of the tokens.

**Run gate (value of computation).** With cell cost `c_s`, check cost `c_k`, hub cost `c_h` (the
cost of the strongest-cell route, including its planning and verifying) and
cell pass probability `p`, cell-first costs `c_s + c_k + (1 - p) * c_h` against `c_h`. Route to
the cell only if `p > (c_s + c_k) / c_h`. A model verifier runs only when there is no
deterministic check and `P(error) x cost of a wrong accept > verifier cost`. Fan-out, retries
and dream passes obey the same inequality. A tier that only ties the stub is removed. For a
Claude worker `c_s` includes its cold start (the cache write of a fresh context); its size is
not yet measured (PLAN E8.1) and may set a minimum task size worth sending to a worker.

Model API or strongest cell unreachable: cells finish only tasks with a deterministic check, inside their unexpired
policy. Results stay `unverified`; nothing is granted.

## 9. Failure modes and blast radius

| Failure | Blast radius | Guard | Tested by |
|---|---|---|---|
| Cell compromised (injected input, bad model) | Its ceiling and its directory. It cannot sign. It cannot reach another cell only if it is a containerised local cell; a stub cell is not an OS boundary, and a Claude cell is held back from other cells' directories by permission rules alone, with file tools outside the shell sandbox. | Signed ceiling, deny list, star topology, check and verifier | E5.3; unit test that a tampered policy is refused; H1 |
| Memory poisoning | The cell's own memory; the shared store only through the digest lint | Provenance, supersede, re-verify-on-use | H4 / E3.4; E3.5 |
| Policy drift (ceiling creep, stale policy, grants that never shrink) | Grows silently with each version | Version chain, expiry, decay, a diff the owner reads before signing | H1; unit tests for expired and unchained policies |
| Planner cell wrong, or router or model API down | Work stops, closed. A wrong split wastes tokens. Planner, verifier and Claude worker cells share a model family: correlated errors (hence the same-model-ID verification rule, section 2). | Deterministic checks first; coupling gate | H2; H5 (exploratory) |
| Stale route | One task class served below the floor | Config-hash invalidation | H6 |
| Bad weight patch or adapter | One cell's model | Base hash read-only; rollback is one line in `cell.json` | H7 off-target criterion |

## 10. Minimum viable hub-and-cells on this box (no GPU, no install, no network)

1. `cell.py`, one stdlib file: verify signature and chain, enforce keys, run the worker, append
   the log, write the result.
2. Two stub cells: `extract` (log lines to memory records by pattern, the non-learned baseline
   of PLAN 3.5) and `memlint`.
3. A scripted router (fixed plan, no model) so tests are deterministic: tampered policy refused;
   key outside the ceiling returns `escalate`; deny wins; broken log chain detected; digest
   record without a source rejected; failed check escalates one tier. Two hub-as-cell contract
   tests (adversarial review 2, section 1): (a) the same task spec runs unchanged on a stub cell
   and on a scripted stand-in for a strong cell; (b) a "plan" task is executed by a cell and its
   cost appears in its bundle. If both pass with no new file type, "every model is a cell"
   holds on paper and in code.
   Status: `WORKPLAN.md` 9 cut steps 1-3 ("no reachable decision"); the review recommends
   reinstating them (its rank 2, zero cost). Uncommitted `cell.py` and `router.py` exist in the
   working tree on 2026-11-19 and were not verified here. Owner ruling on reinstatement: open.
4. Then, under gate G7 batch C0 (USD 5; the owner must state a call limit, since the 9-call
   default is too few): a Claude Code session as planner cell, one Claude subagent as a worker
   cell, one fresh-context subagent as verifier, three trapbench tasks (their deterministic
   checks satisfy the section 2 verification rule). This is the labelled "Claude Code as shipped" product arm, not a cross-model
   comparison (`PLAN.md` 4.6).

This replaces the old T6 demonstrator. Later gates add: G2, a local-model runtime; G3 + G9, the
T7 pre-test (does "weights" in section 7 mean more than adapters and decoding config); G3 + G5,
a local-model cell that must beat the stub and clear the floor (H6); G6, a per-cell LoRA
adapter trained with Unsloth.

## 11. What we deliberately do not build

- A framework, SDK, plugin system, config language or user interface.
- A message bus, daemon, scheduler or service discovery.
- Cell-to-cell messaging, voting or consensus.
- A vector database. Memory stays a JSONL file until retrieval measurably fails.
- An Anthropic-Messages shim in front of a local model (undocumented, probably unsupported).
- A hub that edits cell weights in the loop. T7 tests the idea once; it is not a feature.
- A policy that rewrites itself, or a model that holds the signing key.
- A shared board that cells read and write. Lance Martin's 1,000-agent run used one (a database
  behind a gateway; talk claim). PLAN E8.2 tests a hub-hosted board against plain hub assignment
  with eight local agents. It is an experiment harness; it enters this design only if it beats
  the star by the margin stated in H9's decision rule. A board held by the hub keeps the star:
  cells still have no channel to each other.

## 12. One strong hub, many people's cells (direction; mostly untested)

The owner's question: if the hub model becomes much stronger than anything a person can run
locally, how do many people's local cells benefit while each person keeps control? Nothing in
this section is built. The design above is for one owner on one box; this section says what
would have to change and what could go wrong. "Strong hub" means a frontier model available
today. We have no superintelligent system and no test that says anything about one.

| Mechanism | How it would use the existing contract | Status | Testable now, single owner | Not testable now |
|---|---|---|---|---|
| Verified skills distilled into local adapters | Hub results that passed a deterministic check become training pairs; the adapter is a hashed file a person chooses to point `cell.json` at; base weights untouched | Speculative. H7's source says its edit removed an obstacle and added no ability | Whether a small adapter keeps a measured gain on one task class (T4, conditional; RECOMMENDED CUT awaiting owner ruling, `PLAN.md` 6.4); rollback by one line | Whether skills of a much stronger model transfer at all; adapter quality across people's different work |
| Shared memory digests with provenance lint | Contract file 4. Records only, each with a source pointer; arrive as `confidence: imported`; a local cell's raw log is read only by router code (a Claude cell's context already reached the provider, 6a) | Design, not built | Lint rejects records without a source; lock-in with and without governance (H4, E3.4); leak sentinels (E3.5) | Sharing between people: a pointer into someone else's private log cannot be resolved by the receiver, so cross-user lint can check form, not truth |
| A policy signed by each person | Contract file 1 with one key per person. The hub proposes a diff; only that person's key signs | Design; ordinary practice | Tampered, expired or unchained policy refused (contract tests) | Whether people read the diffs they sign |
| Cost routing so most work stays local | `routes.json`, per person and per task class | Hypothesis H6 | The cascade on this box | Other people's hardware and task mixes |

Risks that grow with the number of people, with the guard we have and its limit:

| Risk | Why it grows | Guard in this design | Limit of the guard |
|---|---|---|---|
| Concentration | Every cell depends on one hub and one vendor: correlated errors, one point of failure, pricing power, and a hub that sees every digest | The contract is plain files and the hub is a role, so another strong model could fill it; cells finish checked tasks when the hub is down (section 8) | Untested with a second model family. A plain-file contract does not create a second vendor |
| Memory poisoning across users | One accepted wrong record reaches everyone, and early records gain share (H4) | Provenance, supersede-not-delete, re-verify-on-use, imports marked `imported`; cross-user sharing off by default | The lint checks that a source exists, not that the claim is true. A patient attacker can supply a real-looking source |
| Privacy leakage | Digests and adapters can carry private detail from the work they came from | Local cells' raw logs are read only by router code; secret-pattern lint; scope filter (E3.5). Claude cells: none beyond the provider's own terms (6a) | Pattern lint misses what it has no pattern for. Nothing here measures what an adapter memorised from its training pairs |
| Policy drift | Ceilings creep version by version; one hub proposing policy to everyone makes all policies alike, so one flaw is everyone's flaw | Version chain, expiry, decay of unused grants (H1), a human-read diff | Depends on a person reading each diff. Sameness across people is not measured by anything here |

What changes in the design if this is ever pursued: a key per person, a digest scope per person,
and sharing between people only by explicit opt-in per record. Until a single-owner result
(H4, H6) exists, none of it is built.
