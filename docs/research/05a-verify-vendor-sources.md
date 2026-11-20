# 05a Verification of vendor sources (checked 2026-11-19)

Method note. WebFetch was blocked by a local hook, so each page was fetched in full through the context-mode indexer (ctx_index on the URL) and then read through targeted retrieval (ctx_search). "OPENED-IN-FULL: yes" means the whole page was fetched and indexed. It does not mean every chunk was read line by line. Quotes are verbatim from retrieved chunks (<=25 words). Nothing is filled from memory.

## 1. Claude Code auto mode

### 1a. Engineering post
- URL opened: https://www.anthropic.com/engineering/claude-code-auto-mode (the fetch resolved to https://www.anthropic.com/research/claude-code-auto-mode)
- Title: "How we built Claude Code auto mode: a safer way to skip permissions". Published Mar 25, 2026 (Engineering team).
- OPENED-IN-FULL: yes (17 chunks)

| Claim | Verdict | Evidence |
|---|---|---|
| Humans approve ~93% of manual prompts | CONFIRMED (in this post) | "Manual prompts sit in the middle, and in practice users accept 93% of them anyway." |
| Classifier FPR 8.5% -> 0.4% across two stages | CONFIRMED | "That reduces the 8.5% FPR down to 0.4%." Table: Stage 1 8.5% FPR; full pipeline 0.4% FPR (n=10,000 real traffic). |
| ~17% false-negative on overeager actions | CONFIRMED | "The 17% false-negative rate on real overeager actions is the honest number." The sample is n=52. Stage 1 alone is 6.6% FNR. |
| Escalate to human after 3 consecutive or 20 total denials | CONFIRMED | "If a session accumulates 3 consecutive denials or 20 total, we stop the model and escalate to the human." Headless `claude -p` terminates instead (post); the permission-modes doc says the action does not run and the run continues. |
| Humans caught ~14% vs auto mode ~89% | NOT FOUND in this post | The post contains no human-reviewer study. It is in the announcement below. |

### 1b. Announcement article that holds the human-vs-classifier study
- URL opened: https://claude.com/resources/articles/auto-mode-default-in-claude-code
- Dated August 7, 2026, with an "Update, October 22, 2026" banner. OPENED-IN-FULL: yes (18 chunks)

| Claim | Verdict | Evidence |
|---|---|---|
| Humans caught ~14% of dangerous commands vs auto ~89% | CONFIRMED (the exact figure is 13.6%) | "human review caught just 13.6% of dangerous commands, while auto mode caught 89%." n=1,053 paid testers. |
| Humans approve ~93% of prompts | CONTRADICTED here (different number) | "users approve 97% of permission prompts in Claude Code." The 93% is from the March engineering post and 97% from the August article. Cite them separately and do not merge them. |
| Study caveat | Context | Testers were in a staged test environment, knew they were being evaluated, and one prompt per session was swapped for a dangerous command. |

Other numbers in the announcement, in case the plan uses them: held-out synthetic attack miss rate fell from 12% to 7%, and the article says this "should not be taken as the miss rate on real traffic".

## 2. Claude Code docs: permissions, hooks, sandboxing, settings
URLs opened, all OPENED-IN-FULL yes. No page date or version stamp was shown. The pages mention versions up to v2.1.302.
- https://code.claude.com/docs/en/permissions
- https://code.claude.com/docs/en/permission-modes
- https://code.claude.com/docs/en/hooks
- https://code.claude.com/docs/en/sandboxing (fetched; not needed for any claim below)
- https://code.claude.com/docs/en/settings
- https://code.claude.com/docs/en/debug-your-config

| Claim | Verdict | Evidence |
|---|---|---|
| Deny rules evaluated before the classifier; a deny-matching call never reaches it | CONFIRMED (inferred from the decision order, no sentence says "never reaches") | permission-modes, decision order, "The first matching step wins": "Actions matching your allow, ask, or deny rules resolve immediately". Exceptions: writes to protected paths and `rm`/`rmdir` critical-path removals go to the classifier even when an allow rule matches. Deny is not listed as an exception. |
| Precedence deny > ask > allow | CONFIRMED | permissions: "Rules are evaluated in order: deny, then ask, then allow." Also "An allow rule can't carve an exception out of a deny rule." |
| Hook exit 2 blocks and returns feedback; exit 1 does not block | CONFIRMED | hooks: "Exit with code 2 to block the action." Exit 1: "is a non-blocking error unless the hook is one whose failure blocks the action". The stderr is the reason for a PreToolUse block. Caveat: for SessionStart, SubagentStart and PostModelSwitch, exit 2 is only shown in the transcript and "Claude doesn't see it". A hook `onFailure: "block"` makes any failure block. |
| Persistent allow rules have no built-in expiry/decay | CONFIRMED by absence, not by an explicit statement | permissions table: "Yes, and don't ask again" for Bash is "Permanently per repository and command", and for web fetch is "Permanently per repository and domain". File edits last "Until session end". No expiry setting was found in permissions or settings. The exceptions are the session-only file-edit grants and the permission-modes protections above. |
| A doctor prompt-audit command exists | PARTIAL / NOT FOUND as named | debug-your-config: "/doctor ... Setup checkup: installation health, invalid settings files, unused extensions, duplicate subagent names ..., and checked-in CLAUDE.md content Claude can derive". `claude doctor` is read-only diagnostics. No "prompt-audit" command or permission-prompt audit was found. |
| Auto-mode denial thresholds 3/20 | CONFIRMED (permission-modes) | "The thresholds of 3 blocks in a row and 20 blocks total are not configurable." |

Extra facts found that bear on the plan:
- "A hook that exits with code 2 stops the tool call before permission rules are evaluated", so a hook can block even when an allow rule exists.
- A deny rule cannot be overridden by a PreToolUse hook that returns "allow".
- Bash deny rules match the literal command string only: `Bash(rm *)` does not stop `/bin/rm` or `bash -c 'rm ...'`. The docs say to use a hook or the sandbox for a hard guarantee.
- Boundaries stated in conversation are re-read from the transcript each check and can be lost on compaction. For a hard guarantee the docs say to add a deny rule.

## 3. NVIDIA OpenShell docs
URLs opened, all OPENED-IN-FULL yes. No page version or date was shown.
- https://docs.nvidia.com/openshell/about/overview (the index.html URL redirected here)
- https://docs.nvidia.com/openshell/how-it-works/policies/overview
- https://docs.nvidia.com/openshell/how-it-works/policies/schema
- https://docs.nvidia.com/openshell/how-it-works/policies/advisor

| Claim | Verdict | Evidence |
|---|---|---|
| Policy YAML covers domains | CONFIRMED | schema: `endpoints: - host: api.github.com port: 443`. Overview: "OpenShell denies every outbound connection from a sandbox unless a rule in network_policies allows it." |
| ... paths | CONFIRMED | schema REST rules have a path glob; WebSocket "path: Path glob of the upgrade request". Filesystem policy has `read_only` and `read_write` path lists. |
| ... HTTP methods | CONFIRMED | WebSocket rules use `method: GET`. Overview: "allow reading from an API but not writing to it". Presets such as `access: read-only` appear in the schema. |
| ... executables | CONFIRMED | "Binary Object ... path: Executable path or glob, such as /usr/bin/curl". Also: "OpenShell records a hash of each executable the first time it takes part in a connection, and denies later connections if the file changes." |
| Policy Advisor: denial -> proposal -> human approval -> hot reload | CONFIRMED | "A proposal never changes the policy on its own. By default, every proposal waits for your review." "an approved rule takes effect without a restart." The log sequence is `CONFIG:PROPOSED`, `APPROVED` or `REJECTED`, `LOADED`. A rejection reason goes back to the agent so it can submit a narrower proposal. |
| Policy Advisor is off by default; auto-approval is opt-in | Extra finding | "The policy advisor is off by default." "You can opt in to automatic approval, which approves a proposal when OpenShell's risk checks find nothing to flag." |
| Only network rules hot-reload | Extra finding | Schema: `network_policies` Live; `filesystem_policy`, `landlock` and `process` take effect at Startup. |
| No documented decay/shrink of grants | CONFIRMED by absence | Searches for expire, TTL, decay, shrink and revoke in the overview, schema and advisor pages found no such feature. Approved rules persist until removed manually ("approve, remove, or undo a rule"). Limit: I did not open the manage-policies, network-rules, prover or default-policy pages, so absence is for the three pages above only. |

## 4. Managed Agents, memory, prompt caching, pricing

### 4a. Dreams (Managed Agents)
- URL opened: https://platform.claude.com/docs/en/managed-agents/dreams. OPENED-IN-FULL: yes. No date shown. Beta header `dreaming-2026-04-21`.

| Claim | Verdict | Evidence |
|---|---|---|
| Dreaming feature exists | CONFIRMED | "A dream reads an existing memory store alongside past session transcripts, then produces a new, reorganized memory store". |
| Properties relevant to the plan | Extra | Status "Research preview". Takes 1 to 100 sessions. "The input store is never modified". Not ZDR eligible and not HIPAA eligible. |

### 4b. "The components of agent memory" (Lance Martin)
- URL opened: https://www.anthropic.com/research/components-of-agent-memory. OPENED-IN-FULL: yes (14 chunks). The post says "Written by Lance Martin". The publication date was not shown in the retrieved chunks. A search result gives Nov 6, 2026 (secondary, unverified).

| Claim | Verdict | Evidence |
|---|---|---|
| Authored by Lance Martin | CONFIRMED | "Written by Lance Martin with editorial guidance from ..." |
| Dreaming corrects/consolidates memory | CONFIRMED | "Claude can use dreaming to organize memory. This can correct mistakes, create notes, build new memory representations, or shape what's preemptively loaded". |
| 72% cost reduction from cache fixes | NOT FOUND in this post | The only "72%" is a quality figure, unrelated to cost or caching: "100% of the criteria could be met, up from 72%." |

### 4c. Memory tool
- URL opened: https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool. OPENED-IN-FULL: yes. No date shown.
- CONFIRMED: "The memory tool operates client-side: Claude requests file operations, and your application runs them." It has a "Memory expiration" section: "Periodically delete memory files that haven't been accessed in a long time." This is a suggestion for your own handler, not a built-in feature.

### 4d. Prompt caching and pricing
- URLs opened: https://platform.claude.com/docs/en/build-with-claude/prompt-caching and https://platform.claude.com/docs/en/about-claude/pricing. OPENED-IN-FULL: yes for both. No version or date shown.

| Claim | Verdict | Evidence |
|---|---|---|
| Prefix ordering | CONFIRMED | "Cache prefixes are created in the following order: tools, system, then messages." Also: "Place static content ... at the beginning of your prompt." |
| Cache TTL | CONFIRMED | "By default, the cache has a 5-minute lifetime." A 1-hour TTL is available at additional cost. |
| Read-token price ratio as stated on the pricing page | CONFIRMED with per-model exceptions | Pricing: "Cache read (hit) 0.1x base input price on most models". Exceptions in the same page: Fable 5.2 and 5.1 0.025x; Opus 5.5 0.05x; Sonnet 5.5 0.05x; all other models 0.1x. The caching page says "0.1 times ... (see the table footnote for per-model exceptions)". Cache writes are 1.25x (5 minute) and 2x (1 hour). |
| 72% cost reduction from cache fixes | NOT FOUND in any written source opened | Searched the caching page and the components post. It appears to be a talk-only claim. |

## Corrections the plan needs
1. "Humans caught ~14% / auto mode ~89%" is not in the engineering post. It is in the Aug 7, 2026 announcement (https://claude.com/resources/articles/auto-mode-default-in-claude-code), and the exact figure is 13.6% (n=1,053 staged testers, not real work). Cite the announcement.
2. The ~93% approval figure is from the Mar 25 engineering post. The Aug 7 announcement says 97%. Do not present 93% as current, and do not mix the two sources.
3. The 17% false-negative rate is n=52 real overeager actions, and the 0.4% false-positive rate is n=10,000 real traffic. State the sample sizes. The 8.5% -> 0.4% drop comes at the cost of recall (stage 1 alone is 6.6% FNR).
4. 3 consecutive / 20 total denials is confirmed but not configurable. In `-p` mode the engineering post says the process terminates, while the permission-modes doc says the action does not run and Claude keeps working. These two sources disagree, so pick the docs for current behaviour.
5. "Deny never reaches the classifier" holds only through the decision-order list. No page says this sentence. Protected-path writes and `rm`/`rmdir` critical-path removals go to the classifier even with an allow rule. Bash deny rules are string matches and are bypassable (`/bin/rm`, `bash -c`), so pair them with a hook or the sandbox.
6. "No allow-rule expiry" is supported by absence plus the "Permanently per repository and command" wording. Say "no documented expiry". File-edit approvals do expire at session end.
7. The "doctor prompt-audit command" was NOT FOUND. Only `/doctor` (a setup checkup that includes derivable CLAUDE.md content, with proposed fixes) and `claude doctor` (read-only diagnostics) exist. Do not call it a prompt audit.
8. The "72% cost reduction from cache fixes" is NOT in any written source. The only 72% in the components post is a wiki-grading quality score (72% -> 100%). Mark it as a talk-only claim, or drop it.
9. The cache-read price ratio is not a flat 0.1x. Current models differ: Sonnet 5.5 0.05x, Opus 5.5 0.05x, Fable 0.025x. Use the per-model table.
10. The OpenShell "no decay" claim is by absence across three pages (overview, schema, advisor). The manage-policies, network-rules, prover and default-policy pages were not opened. Also, Policy Advisor is off by default, only network rules hot-reload, and automatic approval exists as an opt-in. The plan must not imply that every proposal needs a human.
11. Hooks: exit 2 gives feedback to the agent only for events that can block (for example PreToolUse). For SessionStart, SubagentStart and PostModelSwitch, "Claude doesn't see it". Exit 1 is non-blocking unless `onFailure: "block"` is set.
12. Dreams is a research preview, not ZDR or HIPAA eligible, so do not recommend it for tenant data without caveats.
