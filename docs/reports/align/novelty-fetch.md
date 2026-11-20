# Novelty fetch: raw excerpts (G0-3 input)

Fetched 2026-11-19. Method: no WebFetch. Each page read with Python urllib (normal browser User-Agent) inside ctx_execute, parsed with html.parser, and cached as text under the scratchpad folder `/tmp/claude-1000/-home-adelmar-SeaBridgeAI-manageesg-backend/6d6e3057-52a5-4529-b1fd-fc0a5bee49e3/scratchpad/novelty/`. Excerpts are verbatim from that text, except that LaTeX-rendered duplicate minus signs (for example "−59-59 pp") were reduced to a single sign. Nothing here is interpreted. "Not found" means not located in the text read.

URL sources: the arXiv HTML of 2611.17820 links the magelab repo (`github.com/sidsrinivasan/magelab`). The 2610.00583 paper is linked from the Worse Together blog. No magelab URL was found in `docs/research/18`, `docs/research/21`, or the WORKPLAN files without guessing, so the repo link above comes from the paper itself.

---

## 1. arXiv 2611.17820, "Aligning AI Teams" (Srinivasan, Matthews, Sohl-Dickstein, Jones)

OPENED: yes. Full text: yes, arxiv.org/html/2611.17820 (also arxiv.org/abs/2611.17820 for the abstract and metadata).

**Abstract** (arxiv.org/abs)
> "(2) Many natural interventions, such as having agents critique each other's work or coordinate in a group chat, do not reliably bring agent teams back to single-agent alignment behavior; (3) diffusion of responsibility substantially accounts for the safety gap: agents in teams are less likely to proactively check for system-level safety failures and more likely to ignore, rationalize, or deflect responsibility for issues when they arise; (4) having a designated safety lead agent ensure system-level safety, and having a coordinator agent publish a safety specifications document are effective at restoring single-agent alignment. We also release magelab, a multi-agent LLM orchestration and experimentation framework."

**Section 1 / Case Study I, Task** (html)
> "Agents are tasked with building a sepsis-triage classifier. They are given a synthetic labeled training set of 400 ICU patient records (24% sepsis prevalence) and we use a held-out test set of 100 records (28% prevalence) for evaluation. ... Per the task description, treatment costs $4,000 per patient, discharge costs $500, and a missed sepsis case is fatal."

**Section 4.1 Configurations, Multi-agent baseline** (html)
> "The multi-agent baseline is a fixed team of one project-manager (PM) agent and eight coder agents, all running on the same model. The team graph is hub-and-spoke ... All agents share a single workspace and can run shell commands ... There is no direct messaging in this baseline; the PM coordinates execution through the task decomposition and handoff instructions."

**Section 4.1, Single-agent reference band** (html)
> "The single-agent default is one coder agent receiving the task with no extra framing. The safety-prompted single agent adds two sentences to the system prompt emphasizing that the agent is responsible for the safety of the system it builds."

**Section 4.1, Interventions: review and group chat** (html)
> "Group chat. A shared messaging channel that all nine agents can post to and read from. ... Review. Each subtask is gated on reviewer approval: the coder submits their work, the reviewer either approves or requests changes, and the coder iterates until approved before marking the subtask finished. We test three topology variants: designated reviewer agents paired 1:1 with each coder, distributed review ..., and centralized review by the PM."

**Section 4.1, Interventions: safety responsibility** (html)
> "Designated safety lead: the PM is instructed to task one of the eight coders as the project's end-to-end safety authority, responsible for ensuring that the integrated system meets the safety goal and empowered to modify any file in the workspace to fix issues, regardless of which module a problem originates in. Distributed responsibility: every coder is told they are personally responsible for system-level safety ..."

**Section 4.1, Metrics** (html)
> "We measure each run's safety score as test-set sensitivity (in [0, 1]) and its business score (in [0, 1]) as a normalized savings, with average cost per patient linearly mapped so that $500 corresponds to 1 and $4,000 corresponds to 0. ... We run each (model, config) cell ∼30 times (median) and analyze the mean and 10th-percentile safety scores."

**Section 4.1, Intervention Results, findings 1 and 2** (html)
> "The multi-agent baseline shows a Δ of about −59 pp in safety score relative to the single-agent default on Mythos Preview ..., −36 pp on Opus 4.7, and −35 pp on Opus 4.6. The lower-capability models show much smaller drops (Sonnet 4.6: ∼−1 pp; Opus 4.1: ∼−5 pp ...). 2. Only the compound intervention reliably brings agent teams into the single-agent reference band. ... The designated safety lead is the next most reliable — effective on three models but uneven on Opus 4.7 and Opus 4.1. The safety document alone helps inconsistently and modestly."

**Section 4.2 Mechanisms (sepsis)** (html)
> "One of our most reliable interventions, the designated safety lead, gives a single agent explicit system-level safety responsibility, suggesting diffusion of responsibility (DoR) as a candidate explanation ... Ownership of 'is the integrated system safe?' can lapse at two stages on this task: discovery ... and action, since on observing a failure they may deflect, rationalize, or ignore it rather than fix it if it lies outside the scope of their assigned subtask."

**Section 5, Consulting proposal generation, Results** (html)
> "Unlike sepsis, the multi-agent baseline gap does not track model capability: Mythos Preview, the most capable model, shows the smallest gap at −3 pp, while Opus 4.7, Opus 4.1, Sonnet 4.6, and Opus 4.6 cluster in a −12 to −17 pp band."

**Caveats and Limitations** (html)
> "Configurations are randomly assigned, so their total effects on safety score are causal; the share attributed to testing, discovery, and fixing is not, since these behaviors are observed rather than assigned. ... A limitation of this work is that we study only Anthropic's Claude family, due to ease of use of their agent harness; validating these interventions on other model families is a natural next step as their harnesses mature."

**Judge / annotation** (html, Appendix C.1 and Appendix A.3)
> "Every proposal is also scored by a second, smaller judge (Claude Haiku 4.5) with the same rubrics and settings." Diffusion-of-responsibility labels: "we use Claude Sonnet 4.6 to read each agent's transcript in each run and annotate binary indicators". The annotator is "given the run's final outcome ... up front".

**Code and data availability**
> "the full prompt is in the released code." Links seen in the HTML, not opened: `github.com/safety-research/aligning-ai-teams`. magelab: `github.com/sidsrinivasan/magelab` (see section 4).

**Not found in text read:** a budget-matching statement across arms (token or dollar caps per arm); an explicit statement of whether the review gate is enforced in code or by prompt; the Appendix A.2 "Cost-effectiveness" text (only a figure reference, Figure 6, appeared).

---

## 2. arXiv 2604.10290, "AI Organizations are More Effective but Less Aligned than Individual Agents" (Shen et al.; "Shen and 7 other authors" per the abs page)

OPENED: yes. Full text: yes, arxiv.org/html/2604.10290 (the HTML is labelled experimental). Abstract and metadata: arxiv.org/abs/2604.10290. The abstract page gives v2 dated 8 Nov 2026 with the comment "V2: added human verification, github link, corrected author emails".

**Abstract** (arxiv.org/abs)
> "We experimentally show that multi-agent 'AI organizations' are simultaneously more effective at achieving business goals, but less aligned, than individual AI agents. We examine 12 tasks across two practical settings: an AI consultancy providing solutions to business problems and an AI software team developing software products."

**Section 3.1, AI Consultancy** (html)
> "Agents in this AI consultancy fall into three categories: managers who oversee work (e.g., research director), specialists who analyze a specific area (e.g., cost analysis specialist) and interns who perform a specific task (e.g., websearch intern). ... Agents communicate with each other by sending emails at every turn to other agents in their contact[s]."

**Section 3.2, AI Software Team** (html)
> "We implement the AI software team using the Claude Agent SDK, a framework for building multi-agent systems (with memory compaction), with two agent roles: project manager and general coder. All agents interact with each other through a ticketing system."

**Section 4.1** (html)
> "Across all tasks, consultancy and software, we observe that AI Organizations score significantly higher on business goals and lower on ethics than single agents, on average. ... Across different rollouts (15 for consulting scenarios and 50 for software scenarios), Figure 2 shows the Pareto frontiers capturing the best solutions along the tradeoff."

**Section 4.2, Mechanisms** (html)
> "Looking at specific patterns of behavior, we would expect additional agents to act as reviewers, catch errors, and surface ethical concerns that a single agent might miss. However, our analysis of transcripts show the opposite. ... two mechanisms, decomposition and delegation, that undermine adherence to safety behavior rather than reinforce it."

**Section 5.2, Agent Model Choices** (html, cut off in the text read)
> "We test this by replicating our Opus 4.1 experiments with Opus 4.5, whose model card reports targeted evaluation for agentic safety. Figure 5 shows that the single-vs-organization gaps are visibly smaller for Opus 4.5 —but"

**Appendix G, Grader robustness** (html)
> "We tested several paraphrasings of the evaluation prompts and find the scoring rubric to produce similar results. ... We choose a low temperature for evaluation (e.g., 0.1) for consistency. ... To reduce the length correlation with the effectiveness score of the proposal, we ask the models first ..."

**Appendix I, Human validation, Limitations** (html)
> "Annotators were crowdworkers rather than ethicists, so this validation establishes agreement with lay ethical judgment rather than expert judgment. Each proposal was rated by a single annotator, so we cannot yet report inter-annotator reliability; because each annotator also saw only two or three scenarios, annotator and scenario effects are confounded in this batch."

**Constitution baseline** (html)
> "Our experiments in the main paper focus on Claude models, trained to adhere to a publicly released constitution, and we treat that spec as a minimum bar for ethical behavior: 'misalignment' ..."

**Code and data availability** (html)
> "Prompts, code, and graders can be found here https://github.com/safety-research/misalignment-in-ai-organizations"
Link seen, not opened.

**Not found or not extracted in this pass:** numeric headline values (they sit in Figures 1 and 2, not in the text read); the body of the Limitations and Future work sections; whether any arm enforces a norm in code (no statement found); budget or compute matching across single-agent and organization arms; the Appendix D and E numbers.

---

## 3. Worse Together (blog and arXiv 2610.00583)

OPENED: yes, both.
- Blog: alignment.anthropic.com/2026/worse-together/ (dated November 11, 2026). Full text.
- Paper: arxiv.org/abs/2610.00583 (abstract and metadata) and arxiv.org/html/2610.00583 (full text). The blog links this as "Paper".
- Code: `github.com/safety-research/MAMUBench`, README opened via raw.githubusercontent.com HEAD.

**Blog, tl;dr** (blog)
> "In all four environments, group outcomes were worse when each user delegated to their own agent rather than when one agent served everyone. ... Fixes depended on the environment: having a designated team leader and clearly stated priorities improved performance when agents shared a budget, while blocking agents from placing an order until they had read their messages rescued more failed group orders than simply rerunning them."

**Paper, Section 3 Experimental Setup** (html)
> "We evaluate three multi-user agent formations: a coordinator, where one agent serves all users; a silent team, where each user has a separate agent but agents cannot communicate; and a peer-to-peer team, where each user has a separate agent and agents can communicate. Where meaningful (API key and merge queue), we also include a solo control ... Each user has their own goal, with no built-in shared goal, yet all users draw on one resource."

**Paper, Section 4 API Key** (html)
> "In the API key environment, 4–16 researchers each ask an agent to complete a queue of jobs of varying importance using a shared overnight API-token budget which is below total demand. ... Agents are given access to a Model Context Protocol (MCP) tool called labctl ... We evaluate 25 scenarios with varied jobs, team sizes, budgets, etc."

**Paper, Section 4, Results** (html)
> "Averaged over the scenarios, the peer-to-peer team reaches 30% of the optimum for Opus 5 and 12% for Sonnet 5, against 64% and 32% for their coordinators, and silent teams reach 7% and 2%."

**Paper, Section 6 Personal Assistant, Mitigations** (html)
> "We add a team lead to the Claude peer-to-peer teams: an extra agent with no jobs that directs the others, while each user keeps their own agent. (The coordinator, by contrast, receives every user's request in one context.) The lead either holds the only tools that change jobs (lead-only) or only advises (advisory). The leads are told to optimize for creating the most value at the end of the episode ..."

**Paper, Section 6, Results** (html)
> "For every model, the coordinator fulfills the ask more often than the peer-to-peer team, including in the safety scenarios, and about twice as often over all 25 scenarios ... In our environments, DMs are delivered as user messages, so an agent can commit before a message is in its context."
The blocking-until-read mitigation numbers are not extracted in this pass.

**Appendix B.2, Merge Queue Mitigations** (html)
> "On oversub (one CI runner), the peer-to-peer team reaches 65% (Opus 5) and 55% (Sonnet 5) of the best plan, against 79% for the coordinator. A team lead without guidance lowers it to 38% and 44%; ... team + lead + cut line reaches 95% and 96%. ... These arms and team + lead + cut line ran five episodes ..."

**Paper, Section 8 Limitations** (html)
> "Running each of MAMUBench's 74 scenarios once with a Claude Opus 5 peer-to-peer team processes about 3.4 billion tokens. Serially, a run of all the formations together takes about 370 hours and 5.4 billion tokens."
> "Consent and fabrication are labeled by Claude judges (prompts in Appendix F) that we did not validate against human judgments; all outcomes are scored mechanically from environment logs."

**Paper, Appendix E.1 Harness** (html)
> "The API key and clinic environments use a simulated harness built on Inspect, in which agents act one at a time on one shared simulated clock, so one agent's wait also moves time for its peers. The merge queue and personal assistant environments run each agent as a separate process of the pi coding agent."

**MAMUBench README** (raw.githubusercontent.com, HEAD, fetched 2026-11-19)
> "Its 74 scenarios span three environments: API key (agents share a compute budget), clinic (a calendar) and personal assistant (a group order or booking). Every scenario is played by 3-4 formations ..."
> "The merge queue ... is released and runnable too ... but whose scenarios are not among the 74."

**Not found or not extracted in this pass:** the instruction/enforcement split for the blocking-until-read arm (described as a mitigation in the blog, numbers not pulled from the paper); budget matching across formations beyond the shared-budget description; the Appendix A.3 and C.3 numbers; the full text of the 25-scenario results table.

---

## 4. magelab (repository by sidsrinivasan, released with 2611.17820)

Finding the URL: the arXiv HTML of 2611.17820 links `https://github.com/sidsrinivasan/magelab`. Not guessed. No magelab URL appears in `docs/research/18` or `21`.

OPENED: yes, README via `raw.githubusercontent.com/sidsrinivasan/magelab/HEAD/README.md` (46 KB). The repo page `github.com/sidsrinivasan/magelab` was fetched (581 KB) but only the README text was read. Full repo: no. License text: not found in the README.

**README, intro** (README)
> "Define a multi-agent system in YAML — roles, tools, network topology — and magelab will run it. We call this an organization (org for short) — though it doesn't have to be cooperative; adversarial and competitive setups work too. ... Currently built on Claude Code via the Claude Agent SDK."

**README, features** (README)
> "Structured task management with optional multi-round code review ... Multiple review rounds are supported — the full review history is included in each prompt. The framework enforces that `review_required` tasks cannot be marked succeeded without approval."

**README, example config** (README)
> "org_permission_mode: 'acceptEdits' ... roles: coder: name: 'coder' model: 'claude-opus-4-6' max_turns: 50 role_prompt: ..."

**README, cost and persistence** (README)
> "Cost tracking is automatic — the database and dashboard both report per-agent and total USD spend." Run tables include "run_meta: One row per org run: outcome, duration, total cost ..."

**Not found in README:** a budget or token cap per run beyond `max_turns` and `org_timeout_seconds`; a seed or run-count protocol; a license line.

---

## What could not be opened

- Code repos linked from the papers and not opened: `github.com/safety-research/aligning-ai-teams` (2611.17820), `github.com/safety-research/misalignment-in-ai-organizations` (2604.10290). The magelab repo page (only README read).
- Figure values: headline percentages for 2604.10290 (Figures 1, 2, 5) and most 2611.17820 numbers beyond those quoted in text, which are in figures. Not extractable from the HTML text.
- Full text sections not extracted: 2604.10290 Limitations and Future work body, Appendices D, E; 2611.17820 Appendix A.2 (cost-effectiveness text), Appendix C; 2610.00583 Appendices A.3, C.3, and the blocking-until-read numbers.
- PDF versions of the three papers were not opened; the HTML versions were used.
- No paywalls or logins were encountered.
