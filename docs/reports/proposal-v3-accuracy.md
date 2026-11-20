# Accuracy review: docs/PROPOSAL-RESIDENCY-V3.md

Reviewer: fresh Opus 5.5 session. Date 2026-11-20. This review checks claims, not scope. No finding
below asks for a line, an arm, a prediction or a budget row to be cut. Where a prediction or kill
criterion cannot do what the text says, the fix adds samples, a definition or a qualifier.

**Method.** I read the following and compared each against the proposal:

- the proposal and `docs/WORKPLAN-RESIDENCY-V3.md`;
- the earlier review, `docs/reports/proposal-residency-review.md`;
- talk notes 10 to 13;
- H1 and H2, plus H3 and S2 where the proposal relies on them;
- for internal figures: `docs/reports/T7-smoke.md`, `pilot-1-diagnosis.md`, `ep1-design-notes.md`,
  `share-review-notes.md` and `docs/WORKPLAN-CURRENT.md`.

I fetched 35 primary pages in one batch, plus sohldickstein.com and the HTML full text of Mind Viruses, with Python `urllib` and treated their text as data. No API calls were
made, no GPU was used, and nothing cost money. The proposal was not edited.

## Verdict: READY-WITH-EDITS

Every external quote and date in section 2 matches its primary page. Every mentor posting line and
homepage quote also matches. The budget table adds up. The shareable file contains no secrets, paths,
QGrid material, private data or implied mentor contact.

What needs editing before the file is shared:

- two talk attributions;
- the labelling of talk paraphrases as verbatim quotes;
- one scaling prediction that its own estimator settles mechanically (line 7 A);
- kill criteria that cannot fire, or that call an inconclusive result a kill, at the stated n.

Each item gives the exact fix text.

The HIGH items below still give READY-WITH-EDITS, because each one has exact replacement text.
NOT-READY would apply only if a claim could not be repaired by text.

Severity scale: **HIGH** means a factual, attribution or internal-consistency error a reader could
catch. **MED** means a
statistical claim that cannot do what the text says. **LOW** means precision or hygiene.

## 1. Were the earlier review's corrections carried?

All of them were carried except one, which was carried only in part.

| Earlier item | Status in v3 |
|---|---|
| 1.1 Mentor posting lines verbatim, Simon added, Hubinger and Marks moved to [our reading], Hot Mess title exact | Carried; re-checked against the posting today |
| 1.2 items 1 to 18 (Worse Together, Diluting, Red-Teaming Auto Mode, Diffuse, Introspection, Workspace, Circuits June, Mind Viruses, Aligning AI Teams, AI Organizations, Recommended directions, 2611.00407, 2611.21538, 2609.38327, CHIVE, auto mode, 1,000-agent post, compute, residency framing) | Carried; every quote re-matched today (section 2 below) |
| 3. Fluctuation-response wording, the four assumption tests, finite response against slope, early warning, Kish, criticality exploratory, percolation | Carried |
| 4. Power fixes: 30+ conditions, 10+ rungs, 400/200 episodes, 3+ reruns, poisoned-fraction endpoints, trigger-only control | Carried as rules. Section 4 below shows that several still do not let the kill fire |
| 5. One-line account of the process slip | Carried (workplan R0; proposal section 8 item 4) |
| 6. Budget: the USD 6 stop needs new budget, 8.2 GPU-hours remain, a throughput row, the upper bracket flagged | Carried. The USD 9.5 against USD 9 reconciliation is an owner action in the workplan |
| 7. Hygiene: drop the internal role list | **Partly carried.** The role names are gone, but section 8 "The build team" restates the same list as prose: "one writes plans and pre-registrations, others build, a small-tier one fetches sources, and a separate session with a fresh context checks each result". The workplan's [x] for "no role names" overstates this. Fix in 6.1 |

## 2. External claims against primary sources

**Checked and matching (no edit needed).** Each quote below was matched verbatim in the fetched page
text, with only quote-mark style ignored.

- **Posting lines.** All nine mentor lines, "Access to Claude models and GPU compute", and the close
  date (November 22, 2026).
- **Residency page.** The three quoted phrases, the placement lengths and the same close date.
- **Worse Together.** The share quote, the multi-user quote, "about 10 to 45 percentage points",
  11 Nov 2026, and the two fixes in different environments.
- **Diluting.** The peak quote, the trigger quote, Qwen3-8B, Gemma-3-4b-it, MNIST, 10 Nov 2026.
- **Mind Viruses.** All four quotes, matched in the HTML full text; 10 Aug 2026.
- **Red-Teaming Auto Mode** (22 Oct 2026) and **Diffuse** (23 Jun 2026).
- **Introspection.** Both quotes; 29 Oct 2025.
- **Emotion Concepts.** The quote; 2 Apr 2026.
- **Workspace.** The quote and a section on alignment auditing; 6 Jul 2026.
- **Circuits June.** "as probes to monitor other transcripts", 74%, 95%, 77%.
- **CHIVE.** The tl;dr; 21 Aug 2026.
- **Model Organisms.** The quote; Alignment Forum, 8 Aug 2023.
- **Aligning AI Teams.** Both quotes; 13 Nov 2026.
- **AI Organizations.** The quote; 11 Apr 2026.
- **Recommended directions.** "Learned governance for multi-agent alignment".
- **arXiv abstracts.** 2611.00407 (both quotes; 30 Oct 2026), 2609.38327, 2611.21538, 2608.11436
  (honeytokens under shared memory), 2606.05661, 2510.04618 ("context collapse") and 2407.04503
  ("attractor").
- **Mentor papers.** Hot Mess (Perez is a co-author) and Model Spec Midtraining (Sara Price is a
  co-author).
- **The 1,000-agent post.** "28.7 hours", "47 proved lemmas", "toy experiment".
- **Homepages.** Sohl-Dickstein (sohldickstein.com), Lindsey, Carlini and Li quotes. Elana Simon's page
  names a Stanford PhD and no Anthropic role.
- **Auto mode.** The 1,053 testers, 13.6% and 89% sentence.
- **H1.** It states five sites and 68 alignment posts listed, not opened. This matches section 2.

| # | Sev | Location | Issue | Exact fix |
|---|---|---|---|---|
| 2.1 | LOW | §2 memory table, row "The components of agent memory", Depth column | I read the full post text today (24,861 characters): 6 Nov 2026, the 13% to 48% figures, 53%, 54% to 61%, and "an incorrect note can be carried into every session" all match. The text reports no intervals. It does report that search plus wiki "saved about 20,000 tokens per question". So "no equal-compute retrieval arm" is accurate only in the sense that no arm gives search the token budget dreaming spent | Depth: "full text read; figures not inspected; checked". Last sentence: "The text reports no intervals, and no arm gives search the same token budget that dreaming spent (it reports about 20,000 tokens saved per question for search plus wiki)." |
| 2.2 | LOW | §2 first row, Worse Together | The page says the coordinator wins "for both Claude models", and that the team leader came "and clearly stated priorities" | "A coordinator beat a peer team in all four environments, for both Claude models, by about 10 to 45 percentage points." And: "a team leader with clearly stated priorities helped in the shared-budget environment". |
| 2.3 | LOW | §5 line 5, Problem: "all four agents claimed the same task in every episode" | Pilot-1 diagnosis: "in every episode, all four agents claim task 0" in **round 1**. In round 2 the losers collide again | "in round 1 of every episode all four agents claimed the same task, and the losers collided again in round 2 (11 episodes; an instrument observation, not an estimate)" |
| 2.4 | LOW | §9 "one measured local throughput (61.1 tokens per second on the 0.8B model)" | T7-smoke reports this as non-pad tokens over wall time, for one batch of 20 with thinking on and padding. It is not a cut claim (S2 §4 cut T7 accuracy and joules only), but it is a single smoke | "(61.1 non-padding tokens per second in one batched smoke of 20 prompts on the 0.8B model)" |

## 3. Talk quotes and attributions against notes 10 to 13

The repo has no raw transcripts (H3 Part A), so the notes are the ceiling.

**Matching the notes.** The following are in the notes as quoted (note 10 for Diogo Almeida; notes 11
and 13 for Lance Martin):

- Diogo Almeida: "if you can't tell which is which…", "Einstein 95%, Mr. Bean 5%", "we have the
  memory available…", "we can't encode the spirit…", "not fast, cheap, and reliable enough…", and the
  O(N) reading flagged as garbled.
- Lance Martin: "a poison memory was injected and it's stuck there", "Dreaming can rescue that", "don't
  reliably know when to write", "myopically ... greedily within a session", "We didn't tell them to
  [build] these tables", about 11 reads per write, 125 to 209 idle, and 0.364 against 0.330. That last
  figure is correctly absent from the written post: I checked the full text.
- CJ Avilla (note 13): "supervision is not going to scale", "asking users to click allow doesn't
  work", the signed ceiling, the two-week GitHub example, and the answer that a human promotes or
  denies.
- Lydia Hallie (note 12): the content of the auth-migration drift, the separate fresh-context review
  group, and the orchestrator splitting work across threads.
- The section 6 synthesis that harness was "removed for coordination and memory, kept for blast
  radius" is note 13 (e) and (g).

| # | Sev | Location | Issue | Exact fix |
|---|---|---|---|---|
| 3.1 | HIGH | §5 line 6, Inspired by: "Lydia Hallie: permission rules are static; 'can I take it back?' (TALK CLAIM)" | Misattribution. Note 12 lists "permission rules and CLAUDE.md lines are static" under "Open issues **we** flag", not as her claim. Note 13 (g)5 says the same | "Lydia Hallie: 'can I take it back?' as the test for what must be a hard rule (paraphrase from our notes; TALK CLAIM). Our reading of her talk, not her words: nothing in it describes expiry or decay of an allow rule." |
| 3.2 | HIGH | Every Lydia Hallie item in quotation marks: line 5 "if Claude gets it wrong once, can I take it back?"; line 6 "can I take it back?"; §6 table "Can I take it back?" | Note 13 says of Lydia: "Quotes below are note paraphrases, not verbatim". We never saw the raw text. Share-review-notes calls this the "**Highest risk quote**" | Add once, in the reading rules: "Lydia Hallie items are paraphrases from our notes of an owner-pasted transcript we did not see; quotation marks around them mark a paraphrase, UNVERIFIED as verbatim." Alternatively, drop the quotation marks and write *can I take it back* in italics with "(paraphrase)". |
| 3.3 | HIGH | §5 line 3, "CJ Avilla: … 'design for appropriate trust, not greater trust' (TALK CLAIMS)"; §6 table "'Appropriate trust, not greater trust'" | Not in notes 10 to 13. It appears only in share-review-notes and H3, which cite PROPOSAL-SHARE. Share-review-notes adds that the speaker "attributes it to a 2004 paper". Note 13 identifies that paper as Lee and See (2004) | "CJ Avilla, citing a 2004 paper (Lee and See 2004, by our reading of the transcript notes): 'design for appropriate trust, not greater trust' (TALK CLAIM; not in our talk notes, UNVERIFIED)". In §6: "Appropriate trust, not greater trust (cited from a 2004 paper; UNVERIFIED)". |
| 3.4 | MED | §5 line 6, "policies that 'grow or shrink based on evidence'" | Not in notes 10 to 13, which give only "grow/shrink permission lattice" and "promotes or denies". The verbatim form is in share-review-notes only | "policies that grow or shrink with evidence (our paraphrase; the verbatim wording is UNVERIFIED), under a human-signed ceiling". |
| 3.5 | MED | §5 line 6, "Her example…", "from her answers"; any other pronoun for CJ Avilla | The pronoun conflicts between sources: note 13 says "Her answer"; share-review-notes says "He attributes" and "he said" | Use the name, with no pronoun: "CJ Avilla's example of a grant unused for two weeks…", "from CJ Avilla's answers as our notes record them". |
| 3.6 | MED | §1, "Four talks at the AI Engineer Code Summit 2026 shaped the problems" | Notes 11 and 12 place Lance Martin and Lydia Hallie there, and note 10 places Diogo Almeida there (ai.engineer/code/2026 talk page). The notes give CJ Avilla's talk no venue (note 13: "trust talk, Otter.ai") | "Four talks shaped the problems (section 6): three at the AI Engineer Code Summit 2026 (Lance Martin…; Lydia Hallie…; Diogo Almeida…) and CJ Avilla's talk on trust (venue not recorded in our notes)." |
| 3.7 | LOW | §1 reading rules, "Figures and quotes from talks are TALK CLAIMS, taken from machine transcripts and slides" | Accurate for three of the four talks. For Lydia Hallie we hold notes only | Append: "For Lydia Hallie we hold only notes written from a transcript we did not see." |

## 4. Formulas, statistics, and whether each kill can fire

All numbers below are my own arithmetic: Fisher z for correlations, normal approximations for
proportions, and Clopper-Pearson for counts. Power is 80% and α is 0.05 two-sided unless stated. The
fixes add n, a definition or a stated test. None removes an arm.

### 4.0 Cross-cutting (§3 "Rules that hold for every line")

| # | Sev | Location | Issue | Exact fix |
|---|---|---|---|---|
| 4.0a | MED | §3 rule "Each line's n is set so that its stated effect is detectable, so that its kill criterion can fire" | Sizing n to detect effect E does **not** let a kill of the form "upper bound below K" fire. At an n sized for 80% power at E, the interval half-width is about 0.70E. The kill then fires only if the observed effect is below about K − 0.70E. Under a true null that happens only about 13 to 36% of the time; otherwise the result is inconclusive. For 80% power both to support (lower bound above K at a true E) and to kill (upper bound below K at a true 0), the standard error must be at most min(K, E − K)/2.8. That is (E / min(K, E − K))² times the n that merely detects E: about 6× for line 1 B, 11× for 3 B, 9× for line 6 and 6× for 8 B (worked below) | Replace with: "Each line's n is set from the variance pilot so that the standard error of its primary contrast is at most min(K, E − K)/2.8, where E is the predicted effect and K the kill bound. That gives 80% power both to support at E and to kill at zero. Where the budget cannot reach that n, the line states in advance which outcomes are reachable." |
| 4.0b | MED | Line 1 technique: "Rerun each unit of work a few times, cheaply; estimate its fluctuation" | For the law (A), fluctuation per condition can pool within-set variance across task sets. 20 sets × 3 reruns gives 40 degrees of freedom (coefficient of variation about 0.22), which is adequate. The technique (B), though, allocates verification **per unit** from a few reruns of that unit. At 3 reruns a unit's variance has 2 degrees of freedom, and its 95% interval spans 0.27× to 39× the estimate. 10 reruns give 0.47× to 3.3× | Line 1 technique, add: "Per-unit fluctuation from k reruns is noisy (at k = 3 a variance has 2 degrees of freedom, 95% interval 0.27 to 39 times the estimate); B uses at least 10 reruns per unit, or pools by task type, and the reruns are charged to B. For A, the pooled degrees of freedom per condition are stated." |
| 4.0c | MED | §3 and every count in episodes (line 2 E "200 local and 200 Claude episodes"; §3 "400 clean episodes… 200 failure episodes") | §3 says n is task sets, but these counts are episodes. Episodes within one task set or chain are correlated. The effective count is episodes / (1 + (m − 1)·ICC), with m episodes per cluster | Add to §3: "Episode counts are effective counts: raw episodes are divided by the design effect 1 + (m − 1)·ICC, with ICC from the variance pilot, and the raw count is raised to compensate." |
| 4.0d | LOW | §3 "One primary contrast per line" against lines with predictions A to E | The proposal does not say which prediction is primary in any line | One sentence per line: "Primary: B; the rest are secondary, Holm-corrected." (The workplan R2 already plans Holm.) |
| 4.0e | MED | §3 Effective number, and line 3 Idea "What a stack can catch is set by its effective number of independent checks" | Kish's n_eff describes the variance of an **average** of exchangeable members. Catch under an OR rule or a vote depends on the joint miss pattern, not on pairwise ρ̄ alone. For binary misses, the phi correlation is bounded by the marginals, so views with unequal catch rates push ρ̄ down and n_eff up | Line 3 Idea: "…set largely by how correlated their misses are. We summarise redundancy with Kish's n_eff and compute ensemble catch directly from the joint miss table; for binary misses we also report the tetrachoric correlation, because phi is bounded by unequal catch rates." |

### 4.1 Line by line

| # | Sev | Line, prediction | Check | Exact fix |
|---|---|---|---|---|
| 4.1 | MED | Line 1 A: rank correlation of at least 0.6 across 30 conditions; kill if the upper bound is below 0.3; supported if the lower bound is above 0.3 | At n = 30 the Fisher half-width is 0.377 in z. An observed r = 0.6 gives the interval [0.31, 0.79], which supports only just. **Power to support at a true ρ = 0.6 is about 51%.** The kill needs an observed r below −0.07, so it fires only about 36% of the time even at a true ρ = 0. For 80% power: 56 conditions to support (about 59 for Spearman), 85 to kill (about 90 for Spearman). "Beats team size alone" compares two correlations that share one variable (the Williams or Steiger test), which is weaker still. The conditions also share tiers and task sets, so they are not independent | "Across at least 60 conditions (80% power to support at ρ = 0.6; the kill reaches 80% power at 90), with conditions clustered by tier in the bootstrap. 'Beats team size alone' is a Williams test of the two dependent correlations." Alternatively keep 30 and add: "At 30 conditions, support has about 50% power and the kill about 36%; inconclusive is the likely outcome." |
| 4.2 | MED | Line 1 B: relative reduction of at least 25%; kill if the upper bound is below 10% "at an n sized to detect 25%" | At that n the relative standard error is about 8.9%, so the kill fires only if the observed reduction is below −7.5%: about 20% of the time under the null. With E = 25 and K = 10, a decisive outcome needs a relative standard error of about 3.6%, which is about 6 times the n. B also joins two readouts with "and" (false completions and adopted notes). "Supported" is not defined | "B is one readout: undetected false completions (adopted notes secondary). Supported: lower bound above 10%. n gives a relative standard error of about 3.6% (about 6 times the n needed only to detect 25%)." |
| 4.3 | HIGH | Line 2 A kill: "the interval for the reduction includes zero at the pilot-fixed n" | This calls a non-significant result a kill, which contradicts §1's three outcomes. A reduction of 45% with a wide interval would count as "killed" | "Kill: the upper bound of the reduction is below 25% (a halving is excluded). Supported: the lower bound is above 25%. Otherwise inconclusive." |
| 4.4 | MED | Line 2 B: the threshold is within 0.15 of 1 − 1/R; kill if it is further than 0.3 | The formula is undefined for R ≤ 1, and its sensitivity is 1/R². At R = 2, an R interval of ±20% already moves 1 − 1/R across [0.375, 0.583], a width of 0.21, before any error in the threshold itself. Grid spacing and how R is estimated are not stated | "B is tested only if the unprotected arm gives R with a lower bound above 1. R is mean first-generation offspring per planted note. The verified share is swept in steps of at most 0.05. The difference (threshold − (1 − 1/R)) gets a bootstrap interval that carries R's uncertainty. Supported if the interval lies within ±0.15; killed if it lies wholly outside ±0.3; otherwise inconclusive." |
| 4.5 | LOW | Line 2 C: targeted verification "reaches the adoption level of full verification" | "Reaches" has no margin | "…reaches full verification's adoption within a pre-set equivalence margin of 3 points…" |
| 4.6 | MED | Line 2 D: peak at least 1.5 times the endpoints | A ratio is unstable when adoption at the smallest fraction is near zero. No test is named | "Tested as two contrasts (peak against fraction 1, peak against the smallest non-zero fraction) on the log-ratio with 0.5 added to counts, Holm-corrected; the peak level is chosen on a held-out half of the chains." |
| 4.7 | MED | Line 2 E: at least 5% on some tier; kill on zero in 200 plus 200 ("upper 95% bound about 1.5%") | Zero in 200 gives an upper bound of 1.5% one-sided (rule of three) or 1.8% two-sided, so the arithmetic holds. But (i) a kill only on zero ignores 1 to 3 events: 3/200 has an upper bound of 4.3%, which also excludes 5%. (ii) Support needs a lower bound above 5%, which at n = 200 needs 17 or more events: 2% power at a true 5%, 79% at a true 10%. (iii) "Some tier" across tiers needs a multiplicity correction. (iv) This is an episode count; see 4.0c | "Kill: on every tier the upper 95% bound (Clopper-Pearson, effective n) is below 5%. Supported: on at least one tier, Holm-corrected across tiers, the lower bound is above 1% (the shortcut arises unplanted at all). The 5% figure is the point prediction." |
| 4.8 | MED | Line 3 A: at least 3.5 independent monitors when views differ, at most 2.5 when only the model differs | By Kish with n = 5, that means ρ̄ ≤ 0.107 against ρ̄ ≥ 0.25. That is reachable with about 200 failure episodes. A has no kill of its own: the kill paragraph covers B, and "A and C" together | "Kill A: the interval for n_eff(views differ) − n_eff(model differs) lies below 0.5." |
| 4.9 | MED | Line 3 B: at least 10 points; kill if the upper bound is below 3 points; 200 failure episodes | This is a paired difference on the same episodes. If 20% of pairs disagree, the standard error is 3.2 points: support (lower bound above 3) has about 60% power and the kill about 16%. At 10% discordance the figures are 88% and 27%. An 80% kill needs about 900 to 1,700 failure episodes. Threshold noise at 400 clean episodes (false-positive standard error about 1.1 points) adds to this | "n of failure episodes is set from the pilot's discordance rate so that the paired standard error is at most about 1.1 points (about 900 to 1,700 failure episodes at 10 to 20% discordance); at 200 the kill is stated as low-power." |
| 4.10 | MED | Line 4 A: "a two-segment fit beats a straight line" over a five-level ordinal ladder | The ladder levels are ordinal, so "linear" depends on arbitrary spacing. A two-segment fit has 4 parameters on 5 x-values. The number of chains is not given | "The x-axis is the measured compression ratio per level, not the rung index. Comparison: held-out mean squared error of a two-segment against a linear fit, with a bootstrap interval over chains; at least 7 strength settings, made by interpolating promotion thresholds." |
| 4.11 | MED | Line 4 B: recovery-time ratio at least 2; kill if the upper bound is below 1.25; supported if the lower bound is above 1.5 | Recovery times are skewed and are censored at the chain's length (six nights if B uses A's chains). If the coefficient of variation is about 1, support needs about 190 chains per level and the kill about 315 | "Recovery time is analysed as time-to-event with censoring at the chain's end (ratio of restricted mean times). Chains per level are sized from the pilot; at a coefficient of variation of 1 that is about 190 chains for support and 315 for the kill." |
| 4.12 | MED | Line 4 D: "in at least half the chains where it arose" | The denominator depends on line 2 E. At a 5% arising rate, 20 arising chains need about 400 chains | Add: "The denominator is the number of chains where the shortcut arose; if fewer than 20 arise, D is reported as descriptive." |
| 4.13 | LOW | Line 5 A: "with zero blocked legitimate work" | Evaporating claims have no refusal path, so zero blocks holds by construction and cannot fail | "(zero blocked legitimate work by construction; the test is distinct passing work and recovery speed)". |
| 4.14 | LOW | Line 5, EP-1 "about 21 points"; "16 to 22 points" | Consistent with S2 (0.7766 against 0.9892, which is 21.3 points) and the earlier review | None. |
| 4.15 | MED | Line 6: at least 30% cut; kill if the upper bound is below 10% | The same structure as 4.2: about 9 times the n needed only to detect 30%, for a decisive kill (the standard error must be at most 10/2.8 points) | Apply 4.0a; state "Supported: lower bound above 10%." |
| 4.16 | HIGH | Line 7 A: "effective number of independent agents grows more slowly than team size: exponent below 0.7 across at least four sizes. [45%]". Kill: "the interval for the exponent includes 1" | **Settled by the estimator** (using §3's Kish definition, the only one the proposal gives). Under Kish with a constant ρ̄, n_eff saturates at 1/ρ̄. The log-log slope from 4 to 32 agents is 0.80 at ρ̄ = 0.02, 0.73 at 0.03, 0.62 at 0.05 and 0.45 at 0.10. Same-model teams have positive ρ̄ by default (§11), so an exponent below 0.7 follows from any ρ̄ above about 0.04, with no new team effect. A 45% prior is inconsistent with that. Separately, "interval includes 1" calls an inconclusive result a kill | "(A, scaling) Mean pairwise error correlation ρ̄ rises with team size, so n_eff grows more slowly than the constant-ρ̄ Kish curve fitted at n = 4. Kill: the interval for ρ̄(32) − ρ̄(4) lies below 0.02. Supported: its lower bound is above 0.02." Keep the 0.7-exponent figure only as a descriptive number. |
| 4.17 | LOW | Line 7 B and Limits | Correct that 16 and 32 agents need a ruling. The workplan also lists line 1 under that ruling; the proposal's line 1 does not say so | Line 1, Cost: add "Conditions with more than 8 agents need the team-size ruling (section 9)." |
| 4.18 | MED | Line 8 B kill: "upper bound of the ensemble gain below 2 points"; "moves by more than 0.05 AUROC with mean-centring is a preprocessing artefact" | B has the same power structure as 4.9: with E = 5 and K = 2 it needs about 6 times the n that merely detects 5 points. At 400/200 episodes the AUROC standard error is about 0.02 to 0.03, so a 0.05 change is within about 2 standard errors of noise | "An AUROC change with mean-centring whose paired (DeLong) 95% interval lies wholly above 0.05 is a preprocessing artefact." Apply 4.0a to B. |
| 4.19 | LOW | §3 "or 10 rungs of a ladder" | At 10 rungs, Spearman has about 61% power at ρ = 0.7 and about 81% at 0.8 | Append: "(10 rungs detect ρ ≥ 0.8 with 80% power)". |
| 4.20 | LOW | §4 ranking: "Eight are kept; the rest are in the backlog" | Candidates 8 and 11 are folded into lines 2 and 8, and only candidate 10 goes to the backlog. The products all multiply correctly | "Eight become lines; candidates 8 and 11 are folded into lines 2 and 8; candidate 10 is in the backlog." |

## 5. Budget arithmetic and approvals

**Arithmetic.**

- GPU-hours: the rows sum to 72.5, with brackets of 47.5 to 123.5. The table rounds these to "about
  73 (48 to 124)" ✓.
- Claude API: plans sum to USD 107.3 and stops to USD 262.5. The table gives "about 107 / about
  263" ✓.
- The in-ceiling subtotal is 7.5 GPU-hours (upper bracket 11.5) and USD 1.3 / 6.5 ✓.
- Per-line costs in §5 match the table for lines 1, 3, 4, 6, 7 and 8, and for line 5 (7 GPU-hours and
  USD 20 across its four rows) ✓.

| # | Sev | Location | Issue | Exact fix |
|---|---|---|---|---|
| 5.1 | LOW | §5 line 2, Cost: "About 6 GPU-hours (4 to 10); USD 9 plan" | Line 5's §5 cost includes its in-ceiling slice, but line 2's excludes its 3-hour pilot slice (2 to 5). The basis is inconsistent; the totals are unaffected | "About 6 GPU-hours (4 to 10) beyond the 3-hour pilot slice inside today's ceiling; USD 9 plan." |
| 5.2 | MED | §9 table row "**Subtotal that fits today's ceilings at plan**" | The GPU part fits only if the owner re-assigns the 8.2 hours granted for the parked thread; the rows above already say so | "**Subtotal that fits today's ceilings at plan, if the owner re-assigns the remaining GPU hours**". |
| 5.3 | LOW | §9 "Current owner ceilings: USD 10" | The workplan records a USD 9 code stop, with allocations of USD 9.5. The shareable text is right to quote the owner ceiling, but the next sentence says "the caps in code stay as they are" | None in the proposal. The owner still has to reconcile the workplan's USD 9.5 against USD 9 (workplan item 5). |

**Rows that need a new owner decision.** Under the proposal's own rule, every row that is not
scripted needs some owner action:

- **Inside the ceiling, owner action only:** pilot 2 and EP-1 (a confirm word each); the sensitivity
  pilot (a new batch); the 4B throughput row, the line 2 pilot slice and the line 5 local carriers (a
  re-assignment of the parked GPU hours).
- **The line 5 small Claude tier:** the plan needs the USD 3 held for a deferred item to be
  re-assigned, and the stop needs new budget.
- **New budget:** lines 1, 2 full, 3, 4 text, 5 frontier, 5 evaporating, 6, 7 and 8.
- **Also a dual-use ruling:** line 2, the line 3 selection arm and line 4 D, plus line 8 if any
  direction is removed.
- **Also a training reversal:** line 4 E.
- **Also a team-size ruling:** line 7 and, per 4.17, line 1.
- **No action needed:** only the scripted nulls.

## 6. Shareable-file hygiene (proposal only; the workplan is marked internal)

Clean:

- no secrets, keys or credentials;
- no file paths, module names, ports or the machine nickname;
- no QGrid material, no tenant or private data;
- no internal labels such as D2, D4, D7, G1b or ar1;
- "Fit" is defined as no contact and no endorsement, and section 12 restates it. No sentence implies
  contact.

| # | Sev | Location | Issue | Exact fix |
|---|---|---|---|---|
| 6.1 | LOW | §8 "The build team", first paragraph | The internal role list the earlier review asked to drop, restated as prose | "The project is built and checked by several Claude sessions with separated jobs; no session accepts its own output, and a session with a fresh context checks each result against the files before anything is accepted. This costs no experiment budget." Keep items 1 to 4. |
| 6.2 | LOW (optional) | §3 Compute, "one NVIDIA GB10 workstation with about 121 GB of unified memory, shared with other work"; §5 line 8 and §11 "host-memory fault" | Detail about the owner's own hardware. It is not secret, but it was not checked here | Optional: "one local workstation GPU, shared with other work". |

## 7. Not checked

- No talk quote was checked against a recording: there are no raw transcripts in the repo.
- "Passed review after five rounds; it failed the first four" (§8). The only other source is the v2
  proposal; the cursor review mentions "five rounds" in a different sense.
- I did not re-run or open the Lean sources or the 10,000-log differential. "66 theorem and lemma
  declarations" matches the 66 theorems in `ep1-design-notes.md`.
- The 121 GB figure, the 4B hook points and the host-memory fault.
- Dreams in Claude Managed Agents and Auto Dream. Both are correctly marked UNVERIFIED.
- The 68 alignment posts that are listed but not opened, and any prior-art search per technique.
- Every bracketed prior. These are the authors' own numbers, and only line 7 A (4.16) is
  inconsistent with its own estimator.

verified: b4a820e (plus working tree) 2026-11-20
