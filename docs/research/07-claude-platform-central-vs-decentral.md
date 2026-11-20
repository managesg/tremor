# 07 - Claude platform: what is central vs decentral

Date read: 2026-11-19. Public web only. Pages were loaded with Python urllib (User-Agent header, Accept: text/markdown) inside ctx_execute and parsed locally; WebFetch was not used. Quotes are verbatim and 25 words or fewer. Nothing is filled from memory; gaps are listed in section (f).

## Sources and OPENED status

| # | URL | OPENED | How / extent |
|---|---|---|---|
| 1 | https://claude.com/resources/articles/claude-managed-agents-updates | yes, in full | HTML, tags stripped. Dated May 19, 2026. |
| 2 | https://code.claude.com/docs/en/self-hosted-environments | yes, in full | Served as markdown. |
| 3 | https://code.claude.com/docs/en/sandboxing | yes, in full | Served as markdown (about 97k chars). |
| 4 | https://claude.com/resources/articles/self-hosted-claude-managed-agents | yes, in full | Linked from 1. Dated Nov 12, 2026. |
| 5 | https://platform.claude.com/docs/en/managed-agents/self-hosted | yes, in full | |
| 6-9 | .../managed-agents/{self-hosted/differences, self-hosted/inference-provider, self-hosted-sandboxes-security, overview, sessions, session-operations, permission-policies, tools, memory, vaults, dreams, multiagent, observability, environments, self-hosted-sandboxes, self-hosted-data-and-access}; mcp-tunnels/overview; self-hosted-environments-{configuration,deploy,reference} | partial | Headings plus targeted passages (hooks, MCP, permissions, network, OTel, budgets, policies). |
| 10 | .../managed-agents/flows | no | HTTP 404. No page called "Flows" found; the nearest feature is "Dynamic workflows" in `multiagent`. |
| 11 | OpenTelemetry tracing page; /events-and-streaming; /self-hosted/configure; /self-hosted/agent-identity; /self-hosted-sandboxes-workers | no | Linked or fetched, not read. |

## (a) Central vs decentral

Three deployment shapes exist. From the doc (https://platform.claude.com/docs/en/managed-agents/self-hosted), "Cloud sandboxes (default)": Anthropic runs sandbox, service and model. "Self-hosted sandboxes": you run the sandbox only. "Self-hosted Managed Agents": you run sandbox and service, model is Anthropic or a provider you choose. A fourth, separate shape is Claude Code self-hosted environments (runner on your host, control plane at Anthropic).

| Component | Central (Anthropic) | Decentral (you) | Quote and URL |
|---|---|---|---|
| Harness / agent loop | Hosted and self-hosted-sandbox modes; Claude Code self-hosted env control plane | Only in full self-hosted Managed Agents (`cma-server`) | "The agent loop that handles orchestration, context management, and error recovery stays on Anthropic's infrastructure" - https://claude.com/resources/articles/claude-managed-agents-updates. "Serves the API, runs the agent loop, and stores agents, sessions" - https://platform.claude.com/docs/en/managed-agents/self-hosted |
| Sandbox / environment | Default cloud environment | Self-hosted sandbox (Cloudflare, Daytona, Modal, Vercel or your infra); Claude Code runner; local bubblewrap/Seatbelt Bash sandbox | "Both the sandbox where an agent executes tools and the services it reaches run within the established boundaries of your enterprise" - article 1. "A runner ... Runners execute the sessions; the idea is the same as a self-hosted CI runner." - https://code.claude.com/docs/en/self-hosted-environments |
| Credentials / vault | Hosted vaults; proxy outside the sandbox injects secrets | Own secret manager (full self-host only); Vercel/Cloudflare injection at network edge; `sandbox.credentials` locally | "Vaults are designed to keep credentials out of the sandbox." - article 4, https://claude.com/resources/articles/self-hosted-claude-managed-agents. Self-host: "store the secret of each new vault credential in your secret manager" - https://platform.claude.com/docs/en/managed-agents/self-hosted/differences |
| Session log / transcript | Hosted service, and for Claude Code self-hosted env | Full self-host: your PostgreSQL | "Anthropic stores the session transcript so you can resume the session from another supported surface" - https://code.claude.com/docs/en/self-hosted-environments. "Session history is stored in your own database." - article 4 |
| Memory | Memory stores hosted by Anthropic (hosted and self-hosted-sandbox modes) | Self-hosted server hosts stores; worker copies to `/mnt/memory` | "Anthropic hosts memory stores, including their version history." - https://platform.claude.com/docs/en/managed-agents/self-hosted-sandboxes-security (paraphrase of: "Anthropic hosts [memory stores], including their version history"). Self-host: "`memory_store` resources work." - differences |
| Policies | claude.ai server-managed settings and org policies; hosted permission policies | Managed settings file in runner image; `permission_policy` on agent; server `mcp.allowed_hostnames`, `git.allowed_*` | "server-managed settings and organization policies from claude.ai don't reach sessions" (Bedrock/Agent Platform runner) - https://code.claude.com/docs/en/self-hosted-environments |
| Network egress | Cloud env `networking: limited` allowlist | Your firewall/VPC; Claude Code `sandbox.network.allowedDomains`; custom proxy | "When you host the sandbox yourself, you set the same limits in your own firewall." - article 4 |
| MCP | Hosted MCP connector; MCP tunnels (research preview, Cloudflare-based) | Private MCP hosts via allowlist; local stdio MCP in runner image | "A lightweight gateway you deploy makes a single outbound connection, no inbound firewall rules" - article 1 |
| Orchestration / Flows | Multiagent (coordinator, dynamic workflows, advisor) hosted | Full self-host: only `coordinator` with 1 to 20 listed subagents | "Dynamic workflows, the advisor, and subagents that the agent defines itself aren't available." - differences |
| Observability / OTel | Console session viewer; usage/cost pages | Own collector | "The record exports over OpenTelemetry" - article 4. "The server records no traces or metrics until you turn them on with the standard OpenTelemetry environment variables." - https://platform.claude.com/docs/en/managed-agents/self-hosted-data-and-access |
| Model inference | Anthropic API by default | Bedrock, Vertex, Foundry or your own gateway (full self-host); Bedrock/Agent Platform (Claude Code runner) | "Model requests go where you choose" - article 4 |

Central regardless of mode in the Claude Code self-hosted environment: "The control plane remains Anthropic-hosted: session orchestration, queueing, and the claude.ai interface" (article 2). Not available there: Zero Data Retention and HIPAA orgs (article 2). Self-hosted Managed Agents is the exception: ZDR applies to requests to Claude (article 4).

## (b) Configurable per agent or session

Managed Agents (https://platform.claude.com/docs/en/managed-agents/...):
- Model: agent `model` string or object with `speed`, `effort`, `inference_geo` (`agent-setup`). Per-session override: `agent: {type: "agent_with_overrides", id, model, system, tools, mcp_servers, skills}` (`sessions`). A model override "replaces the agent's `model` object in full", so effort must be re-set.
- Budget: session `budget: {type: "limit", max_list_cost: {amount: "125", currency: "USD"}}` (cents, string). "A hard ceiling on the session's list cost". Enforced between model requests, stop reason `budget_reached`; attach only at creation, change later via session update (`sessions`, `session-operations`).
- Permissions: per-tool `permission_policy` types `always_allow`, `always_ask`, `auto`; `default_config.permission_policy` on `agent_toolset_20260401`; agent toolset defaults `always_allow`, MCP toolsets `always_ask`. Custom tools are not covered (`permission-policies`). Confirm via `user.tool_confirmation`.
- Tools: `configs: [{name, enabled}]` and web `allowed_domains` / `blocked_domains`; tools and `mcp_servers` can be updated mid-session (`tools`, `session-operations`).
- Interrupt: `user.interrupt` event stops the agent; it "ends no workflow run" (`reference`).
- Full self-host server settings file: `inference.provider`, `mcp.allowed_hostnames`, `mcp.private_hostnames`, `mcp.max_result_bytes`, `git.allowed_hostnames`, `git.allowed_push_refs`, `web_tools.*` (differences, inference-provider).

Claude Code local (https://code.claude.com/docs/en/sandboxing): `sandbox.enabled`, `sandbox.failIfUnavailable`, `sandbox.allowUnsandboxedCommands`, `sandbox.excludedCommands`, `sandbox.filesystem.{allowWrite,denyWrite,denyRead,allowRead,disabled}`, `sandbox.network.{allowedDomains,deniedDomains,strictAllowlist,httpProxyPort,socksProxyPort,tlsTerminate,allowManagedDomainsOnly}`, `sandbox.credentials.{files,envVars}` with `mode: deny|mask`, `permissions.blockReadsOutsideWorkingDirectories`, `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB`. Locks come from managed settings.

Claude Code runner (https://code.claude.com/docs/en/self-hosted-environments-configuration): `--hooks-dir` / `SELF_HOSTED_RUNNER_HOOKS_DIR` with lifecycle hooks `checkout`, `post-session`, `command`; spawn-runner hook for on-demand runners; wrapper script appending `--permission-mode`, `--allowed-tools`, `--disallowed-tools` after `"$@"`; `SELF_HOSTED_RUNNER_HOST_CONFIG_DIR`; managed-settings.json in the image. Model per session is chosen by the control plane: "You can't choose the model with `ANTHROPIC_MODEL`".

## (c) Extension points that need no fork of Claude Code

1. Claude Code hooks: `~/.claude/settings.json` hooks (e.g. Stop hook reference in the configuration page). Run "with your full access", outside the sandbox (sandboxing page).
2. MCP servers: `claude mcp add --scope user` baked into the runner image; `.mcp.json`; `/etc/claude-code/managed-mcp.json`. Managed Agents `mcp_servers` plus vault `static_bearer` credentials. A third-party tool exposed as an MCP server is the lowest-friction plug-in point.
3. Skills, agents, commands, CLAUDE.md in the host `~/.claude/` snapshot, seeded into each session by the runner.
4. Settings and permission rules: managed settings, `--allowed-tools`, `permission_policy`, `auto` policy (server evaluates each call), custom tools (your code runs the operation, so any open-source tool can run behind it).
5. Telemetry: `CLAUDE_CODE_ENABLE_TELEMETRY` plus standard OTel env vars to your own collector; runner Prometheus `/metrics`, `OTEL_METRICS_EXPORTER=prometheus`; `GET /healthz`; server-side OTel in self-hosted Managed Agents.
7. Custom sandbox clients: "Bring any sandbox client you want" (article 1); your own worker calls the Environments Work endpoints (`self-hosted-sandboxes`).
9. Open-source sandbox: Claude Code "builds the sandbox on the open source `@anthropic-ai/sandbox-runtime` package" and it can wrap the whole process.
10. Model gateway: `inference.provider: gateway` with `format: anthropic-messages`, `bedrock-invoke` or `vertex-raw-predict` (full self-host only).

## (d) Limits and risks stated in the docs

- "Sandboxing reduces risk but is not a complete isolation boundary." (sandboxing)
- Sandbox covers shell commands only; Read/Edit/Write/WebFetch, MCP servers, hooks, LSP, status line, `apiKeyHelper` run outside it (sandboxing).
- Network filtering is by client-supplied hostname, no TLS inspection by default; domain fronting is named as possible. Broad hosts like github.com are exfiltration paths.
- `allowUnixSockets` (docker.sock), broad `allowWrite`, `enableWeakerNestedSandbox`, `allowNestedUserNamespaces` can break the boundary. Unsandboxed retry via `dangerouslyDisableSandbox` unless `allowUnsandboxedCommands: false`.
- Custom proxy port: your proxy then filters everything; built-in lists stop applying.
- Self-hosted Managed Agents: "The agent's `bash` tool is a real shell with the worker process's permissions and network access." Isolation comes from the container you run it in. Force pushes are not refused by the server.
- Environment key leakage: Anthropic "cannot know your key was compromised". Read-only memory is protected from upload, not local modification via bash.
- Claude Code self-hosted: session content still goes to `api.anthropic.com` even with Bedrock; runner locks to one owner; GitHub / GHES checkout only (other hosts via `--environment` dispatch); public beta, Team/Enterprise only.
- Full self-host is private beta, request via account team; no scheduled deployments, dreams, webhooks, Files API, `mcp_oauth` vault credentials; no console parity.
- MCP tunnels: research preview, "provided 'as-is' without any uptime, support, or continuity commitment"; depends on Cloudflare.
- Dreams (memory consolidation job) is research preview and unavailable on a self-hosted server.

## (e) Hub-and-cells sketch

Hub (central): a strong model as planner, verifier and policy signer, with the policy as signed, versioned config.
Cells: many small self-hosted agents, each with narrow sandbox, local small model, local memory.

| Part | Supported today | Would be new |
|---|---|---|
| Hub model plans and verifies | Yes: coordinator multiagent, advisor (hosted only), outcomes via `user.define_outcome`; or a plain Messages API loop | A verifier contract that checks cell output against a signed policy |
| Cells with narrow sandboxes | Yes: one environment per trust boundary, `sandbox.filesystem.*`, `network.allowedDomains`, egress firewall, container per session (Compose, `cma-sandboxes` Helm) | Fleet-level template that derives each cell's allowlist from the signed policy |
| Cell credentials not held by agent | Yes: vault proxy, `sandbox.credentials` mask, egress gateway, secret manager | None |
| Cell local memory | Partly: memory stores copied to `/mnt/memory`; self-hosted server keeps its own store | Memory that never leaves the cell and syncs only signed digests to hub |
| Local small model per cell | Unclear. Gateway provider exists, but doc says model IDs "must name the same model", so a non-Claude local model is not a documented use | Anthropic-Messages-compatible shim in front of a local model, tested for tool use; or run the cell loop outside Claude Code entirely |
| Hub-to-cell dispatch | Yes: work queue per environment, runner polls, agent identity tokens | Hub-side scheduler that routes tasks by cell capability |
| Policy signing | Partial: managed settings file and server settings are config, not signed; agent identity signs tokens, not policy | Policy signer and cell-side verifier (e.g. a PreToolUse hook that checks a signature) |

Boundary: a cell on a local model cannot also be a Claude Code session, because Claude Code sessions use "an Anthropic-issued OAuth token that other providers don't accept" (article 2). A local-model cell is therefore either a custom worker/custom-tool process, or a Claude-model cell with local tools.

## (f) Corrections and uncertainties

- The three named sources are partly overlapping: article 1 is dated May 19, 2026 and covers only self-hosted sandboxes and MCP tunnels. The newer Nov 12 article (4) adds full self-hosted Managed Agents; article 1 alone would understate decentralisation.
- No "Flows" page exists at the tried URL (404). I treated "dynamic workflows" in `multiagent` as the equivalent; this is an assumption.
- Article 1 says self-hosted sandboxes are public beta; the self-hosted Claude Code environments page says public beta for Team and Enterprise; full self-host is private beta. Status labels differ by product and I did not reconcile them.
- Article 4 and article 1 differ on where the "record" exports over OTel; the dedicated OTel tracing page for hosted mode was not opened, so hosted-side OTel details are unverified.
- Hooks as a concept exist in Claude Code sessions (including seeded into self-hosted runner sessions) but I found no hook mechanism on Managed Agents agent definitions; absence in pages I read is not proof.
- Local-small-model cells: the doc's gateway section states IDs must name the same model; running a different model is my inference, untested and probably unsupported.

