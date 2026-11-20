# Anthropic alignment link inventory (research note 18)

Read on 2026-11-19 with a Python urllib fetch (normal browser User-Agent) plus html.parser; WebFetch was not used. Links kept: http(s) anchors pointing to papers, posts, repos or team/person pages; site chrome (nav, search, news, engineering, science, social, Claude console), job postings and mailto/fragment links are dropped. Duplicates are merged across pages (fragments removed). Papers and PDFs linked from the pages were NOT opened; only their URLs were taken from the page HTML.

Page codes: IDX = alignment.anthropic.com index, RES = residency, FEL = Fellows 2026, REC = recommended directions, FRT = frontier red team page.

## 1. Pages

| Page | URL | OPENED | Title | Date shown in page text | Links kept | How read |
|---|---|---|---|---|---|---|
| IDX | https://alignment.anthropic.com/ | yes | Alignment Science Blog | none shown | 95 raw / see T4 | urllib + html.parser |
| RES | https://alignment.anthropic.com/2026/anthropic-residency/ | yes | Anthropic Residency: applications open for established technical leaders | October 30, 2026; November 22, 2026 (role unlabeled) | 34 raw | urllib + html.parser |
| FEL | https://alignment.anthropic.com/2025/anthropic-fellows-program-2026/ | yes | Anthropic Fellows Program for AI safety research: applications open for our next cohorts | September 28, 2026 (role unlabeled) | 14 raw | urllib + html.parser |
| REC | https://alignment.anthropic.com/2025/recommended-directions/ | yes | Recommendations for Technical AI Safety Research Directions | January 10, 2025 | 67 raw | urllib + html.parser |
| FRT | https://www.anthropic.com/research/team/frontier-red-team | yes | Frontier Red Team \ Anthropic | 2026-02-24; 2026-10-17; May 22, 2026 (role unlabeled) | 41 raw | urllib + html.parser |

The alignment.anthropic.com index is the archive: it lists about 90 posts, and each post's own page was not opened (not in the requested set).

## 2. Representative Fellows papers named on the residency page

| Paper (as named on residency page) | Resolved URL seen on a page | Opened | Link text on residency page |
|---|---|---|---|
| Automated Weak-to-Strong Researcher | https://alignment.anthropic.com/2026/automated-w2s-researcher/ | no (URL from residency HTML only) | Automated Weak-to-Strong Researcher |
| Removing Sandbagging in LLMs by Training with Weak Supervision | https://arxiv.org/abs/2604.22082 | no (URL from residency HTML only) | Removing Sandbagging in LLMs by Training with Weak Supervision |
| SHADE-Arena | https://www.anthropic.com/research/shade-arena-sabotage-monitoring | no (URL from residency HTML only) | SHADE-Arena: Evaluating Sabotage and Monitoring in LLM Agents |
| SLEIGHT-Bench | https://alignment.anthropic.com/2026/sleight-bench/ | no (URL from residency HTML only) | SLEIGHT-Bench: Finding Blind Spots in AI Monitors |
| AuditBench | https://alignment.anthropic.com/2026/auditbench/ | no (URL from residency HTML only) | AuditBench: Evaluating Alignment Auditing Techniques on Models with Hi... |
| Subliminal Learning | https://alignment.anthropic.com/2025/subliminal-learning/ (also https://arxiv.org/abs/2507.14805 linked as 'subliminal learning') | no (URL from residency HTML only) | Subliminal Learning: Language Models Transmit Behavioral Traits via Hi... |
| Natural Language Autoencoders | https://transformer-circuits.pub/2026/nla/ | no (URL from residency HTML only) | Natural Language Autoencoders Produce Unsupervised Explanations of LLM... |
| Mechanisms of Introspective Awareness | https://arxiv.org/abs/2603.21396 | no (URL from residency HTML only) | Mechanisms of Introspective Awareness |
| Poisoning Fine-tuning Datasets of Constitutional Classifiers | https://alignment.anthropic.com/2026/backdooring-classifiers/ | no (URL from residency HTML only) | Poisoning Fine-tuning Datasets of Constitutional Classifiers |
| Detecting Adversarial Fine-tuning with Auditing Agents | https://arxiv.org/abs/2510.16255 | no (URL from residency HTML only) | Detecting Adversarial Fine-tuning with Auditing Agents |
| The LLM Has Left The Chat (bail preferences) | https://arxiv.org/abs/2509.04781 | no (URL from residency HTML only) | The LLM Has Left The Chat: Evidence of Bail Preferences in Large Langu... |
| Gemma Needs Help | https://arxiv.org/abs/2603.10011 | no (URL from residency HTML only) | Gemma Needs Help: Investigating and Mitigating Emotional Instability i... |
| AI Agents Find $4.6M in Blockchain Smart Contract Exploits | https://red.anthropic.com/2025/smart-contracts/ | no (URL from residency HTML only) | AI Agents Find $4.6M in Blockchain Smart Contract Exploits |
| How Claude Performs on Robotics Tasks | https://www.anthropic.com/research/claude-plays-robotics | no (URL from residency HTML only) | How Claude Performs on Robotics Tasks |

## 3. Category totals (all unique links in T4)

| Category | Links |
|---|---|
| other | 70 |
| AI security and frontier red-teaming | 31 |
| model organisms | 29 |
| interpretability | 25 |
| AI control and adversarial robustness | 23 |
| safeguards | 11 |
| ML systems and RL | 9 |
| scalable oversight | 9 |
| agents and multi-agent | 4 |
| AI welfare | 3 |
| memory | 0 |
| **total unique links** | **214** |

## 4. All outbound paper, post, repo and team links (de-duplicated)

| # | URL | Link text | Found on | Category |
|---|---|---|---|---|
| 1 | https://alignment.anthropic.com/2024/rogue-eval/index.html | A Toy Evaluation of Inference Code Tampering We describe how highly ca | IDX | AI control and adversarial robustness |
| 2 | https://alignment.anthropic.com/2024/safety-cases/index.html | Three Sketches of ASL-4 Safety Case Components We sketch out three hyp | IDX | AI control and adversarial robustness |
| 3 | https://alignment.anthropic.com/2025/automated-researchers-sandbag/ | Automated Researchers Can Subtly Sandbag Current models can sandbag ML | IDX | AI control and adversarial robustness |
| 4 | https://alignment.anthropic.com/2025/sabotage-risk-report/ | Anthropic's Pilot Sabotage Risk Report We release a report on the leve | IDX | AI control and adversarial robustness |
| 5 | https://alignment.anthropic.com/2025/strengthening-red-teams/ | Strengthening Red Teams: A Modular Scaffold for Control Evaluations We | IDX | AI control and adversarial robustness |
| 6 | https://alignment.anthropic.com/2025/subtle-reasoning/ | Training fails to elicit subtle reasoning in current language models W | IDX | AI control and adversarial robustness |
| 7 | https://alignment.anthropic.com/2026/abstractive-red-teaming/ | Abstractive Red-Teaming of Language Model Character How can we surface | IDX | AI control and adversarial robustness |
| 8 | https://alignment.anthropic.com/2026/agentic-misalignment-summer-2026/ | Agentic Misalignment in Summer 2026 We present four case studies of fr | IDX | AI control and adversarial robustness |
| 9 | https://alignment.anthropic.com/2026/auditing-overt-saboteur/ | Pre-deployment auditing can catch an overt saboteur We test whether ou | IDX | AI control and adversarial robustness |
| 10 | https://alignment.anthropic.com/2026/automated-em-search/ | Automated Subtle Emergent Misalignment Research We instructed a Claude | IDX | AI control and adversarial robustness |
| 11 | https://alignment.anthropic.com/2026/backdooring-classifiers/ | Poisoning Fine-tuning Datasets of Constitutional Classifiers We study  | IDX,RES | AI control and adversarial robustness |
| 12 | https://alignment.anthropic.com/2026/diffuse-ai-control/ | Diffuse AI Control on Fuzzy Tasks We introduce a red-teaming framework | IDX | AI control and adversarial robustness |
| 13 | https://alignment.anthropic.com/2026/homeopathic-learning/ | Diluting Poisoned Fine-Tuning Data Can Strengthen Its Effect We find t | IDX | AI control and adversarial robustness |
| 14 | https://alignment.anthropic.com/2026/modular-pretraining/ | Modular Pretraining Enables Access Control We study a method for isola | IDX | AI control and adversarial robustness |
| 15 | https://alignment.anthropic.com/2026/red-teaming-auto-mode/ | Red-Teaming Auto Mode: Improving Blocking Classifiers Against Malign C | IDX | AI control and adversarial robustness |
| 16 | https://arxiv.org/abs/2312.06942 | AI control | REC | AI control and adversarial robustness |
| 17 | https://arxiv.org/abs/2406.13352 | hiding malicious content in websites to hijack AI agents | REC | AI control and adversarial robustness |
| 18 | https://arxiv.org/abs/2410.13722 | poisoning pretraining corpora | REC | AI control and adversarial robustness |
| 19 | https://arxiv.org/abs/2510.16255 | Detecting Adversarial Fine-tuning with Auditing Agents | RES | AI control and adversarial robustness |
| 20 | https://www.anthropic.com/research/constitutional-classifiers | Constitutional Classifiers: Defending against Universal Jailbreaks acr | IDX | AI control and adversarial robustness |
| 21 | https://www.anthropic.com/research/sabotage-evaluations | Sabotage Evaluations for Frontier Models Benton et al., 2024 How well  | IDX | AI control and adversarial robustness |
| 22 | https://www.anthropic.com/research/shade-arena-sabotage-monitoring | SHADE-Arena: Evaluating Sabotage and Monitoring in LLM Agents | RES | AI control and adversarial robustness |
| 23 | https://www.anthropic.com/research/sleeper-agents-training-deceptive-llms-that-persist-through-safety-training | Sleeper Agents: Training Deceptive LLMs that Persist Through Safety Tr | IDX | AI control and adversarial robustness |
| 24 | https://alignment.anthropic.com/2026/reward-seeker/ | Training a Misaligned Reward Seeker Qi,* Wright, MacDiarmid, Hubinger, | IDX | AI security and frontier red-teaming |
| 25 | https://alignment.anthropic.com/2026/sleight-bench/ | SLEIGHT-Bench: Finding Blind Spots in AI Monitors We build a benchmark | FEL,IDX,RES | AI security and frontier red-teaming |
| 26 | https://arxiv.org/abs/2403.03218 | biological or cyber attacks | REC | AI security and frontier red-teaming |
| 27 | https://arxiv.org/abs/2409.12822 | learn to exploit | REC | AI security and frontier red-teaming |
| 28 | https://red.anthropic.com/ | Frontier Red | RES | AI security and frontier red-teaming |
| 29 | https://red.anthropic.com/2025/smart-contracts/ | AI Agents Find $4.6M in Blockchain Smart Contract Exploits | FEL,RES | AI security and frontier red-teaming |
| 30 | https://red.anthropic.com/2026/cvd/ | Visit | FRT | AI security and frontier red-teaming |
| 31 | https://red.anthropic.com/oss-scanner/ | Visit | FRT | AI security and frontier red-teaming |
| 32 | https://www.anthropic.com/research/attack-navigator | Mapping AI-enabled cyber threats: Insights from the LLM ATT&CK Navigat | FRT | AI security and frontier red-teaming |
| 33 | https://www.anthropic.com/research/attack-surface-reduction | Using Claude to reduce the attack surface of code | FRT | AI security and frontier red-teaming |
| 34 | https://www.anthropic.com/research/claude-plays-robotics | How Claude Performs on Robotics Tasks | FRT,RES | AI security and frontier red-teaming |
| 35 | https://www.anthropic.com/research/coordinated-vulnerability-disclosure-timelines | Updating our coordinated vulnerability disclosure policy timelines | FRT | AI security and frontier red-teaming |
| 36 | https://www.anthropic.com/research/cyber-toolkits-update | AI models are showing a greater ability to find and exploit vulnerabil | FRT | AI security and frontier red-teaming |
| 37 | https://www.anthropic.com/research/discovering-cryptographic-weaknesses | Discovering cryptographic weaknesses with Claude | FRT | AI security and frontier red-teaming |
| 38 | https://www.anthropic.com/research/discovering-vulnerabilities-with-claude | Discovering and exploiting vulnerabilities in critical, real-world sof | FRT | AI security and frontier red-teaming |
| 39 | https://www.anthropic.com/research/ecdsa-curve-origins | (no text) | FRT | AI security and frontier red-teaming |
| 40 | https://www.anthropic.com/research/exploit | Reverse engineering Claude's CVE-2026-2796 exploit | FRT | AI security and frontier red-teaming |
| 41 | https://www.anthropic.com/research/exploit-evals | Measuring LLMs’ ability to develop exploits | FRT | AI security and frontier red-teaming |
| 42 | https://www.anthropic.com/research/formal-verification | (no text) | FRT | AI security and frontier red-teaming |
| 43 | https://www.anthropic.com/research/glm-5-3-and-the-spread-of-advanced-cyber-capabilities | (no text) | FRT | AI security and frontier red-teaming |
| 44 | https://www.anthropic.com/research/intelligence-targeting-conventional-weapons-capabilities | Measuring tactical intelligence targeting and conventional weapons cap | FRT | AI security and frontier red-teaming |
| 45 | https://www.anthropic.com/research/launching-opt-in-vuln-finding-service-for-open-source | (no text) | FRT | AI security and frontier red-teaming |
| 46 | https://www.anthropic.com/research/mythos-preview | Assessing Claude Mythos Preview’s cybersecurity capabilities | FRT | AI security and frontier red-teaming |
| 47 | https://www.anthropic.com/research/n-days | Measuring LLMs’ impact on N-day exploits | FRT | AI security and frontier red-teaming |
| 48 | https://www.anthropic.com/research/project-eve-claude-plays-mmorpgs | Project EVE: Claude plays MMORPGs | FRT | AI security and frontier red-teaming |
| 49 | https://www.anthropic.com/research/project-fetch-phase-two | Project Fetch: Phase two | FRT | AI security and frontier red-teaming |
| 50 | https://www.anthropic.com/research/project-pilot | Project Pilot: Can AI control a drone? | FRT | AI security and frontier red-teaming |
| 51 | https://www.anthropic.com/research/provable-inference | (no text) | FRT | AI security and frontier red-teaming |
| 52 | https://www.anthropic.com/research/self-replicating-ai | AI models may be capable of self-replicating without access to a datac | FRT | AI security and frontier red-teaming |
| 53 | https://www.anthropic.com/research/team/frontier-red-team | Frontier Red Team | FRT | AI security and frontier red-teaming |
| 54 | https://www.anthropic.com/research/zero-days | Evaluating and mitigating the growing risk of LLM-discovered 0-days | FRT | AI security and frontier red-teaming |
| 55 | https://alignment.anthropic.com/2026/welfare-regard/ | Welfare Regard in Multi-Agent Systems Anthropic Fellows Blog: We measu | IDX | AI welfare |
| 56 | https://arxiv.org/abs/2509.04781 | The LLM Has Left The Chat: Evidence of Bail Preferences in Large Langu | RES | AI welfare |
| 57 | https://arxiv.org/abs/2603.10011 | Gemma Needs Help: Investigating and Mitigating Emotional Instability i | RES | AI welfare |
| 58 | https://alignment.anthropic.com/2025/inverse-scaling/ | Inverse Scaling in Test-Time Compute We investigate inverse scaling wh | IDX | ML systems and RL |
| 59 | https://alignment.anthropic.com/2025/stress-testing-model-specs/ | Stress-testing model specs reveals character differences among languag | IDX | ML systems and RL |
| 60 | https://alignment.anthropic.com/2026/automated-alignment-agent/ | A3: An Automated Alignment Agent for Safety Finetuning We introduce ou | IDX | ML systems and RL |
| 61 | https://alignment.anthropic.com/2026/automated-alignment-researchers/ | Automated Researchers Can Mitigate Well-Characterized Alignment Failur | IDX | ML systems and RL |
| 62 | https://alignment.anthropic.com/2026/conceptual-reasoning-index/ | Introducing the Conceptual Reasoning Index We design benchmarks to mea | IDX | ML systems and RL |
| 63 | https://alignment.anthropic.com/2026/msm/ | Model Spec Midtraining: Improving How Alignment Training Generalizes W | FEL,IDX | ML systems and RL |
| 64 | https://deepmind.google/discover/blog/specification-gaming-the-flip-side-of-ai-ingenuity/ | systematically | REC | ML systems and RL |
| 65 | https://www.anthropic.com/research/discovering-language-model-behaviors-with-model-written-evaluations | Discovering Language Model Behaviors with Model-Written Evaluations Pe | IDX | ML systems and RL |
| 66 | https://www.anthropic.com/research/forecasting-rare-behaviors | Forecasting Rare Language Model Behaviors Jones*, Tong* et al., 2025 W | IDX | ML systems and RL |
| 67 | https://alignment.anthropic.com/2026/ai-organizations/ | AI Organizations Can Be More Effective but Less Aligned than Individua | IDX | agents and multi-agent |
| 68 | https://alignment.anthropic.com/2026/worse-together/ | Worse Together: How Performance Breaks Down in Multi-User Multi-Agent  | IDX | agents and multi-agent |
| 69 | https://www.anthropic.com/research/multiagent-systems | Patterns and problems in emerging multiagent systems | FRT | agents and multi-agent |
| 70 | https://www.anthropic.com/research/trustworthy-agents | Trustworthy agents in practice | FRT | agents and multi-agent |
| 71 | https://alignment.anthropic.com/2025/activation-oracles/ | Activation Oracles: Training and Evaluating LLMs as General-Purpose Ac | IDX | interpretability |
| 72 | https://alignment.anthropic.com/2025/cheap-monitors/ | Model-Internals Classifiers We benchmark approaches to re-using LLM in | IDX | interpretability |
| 73 | https://alignment.anthropic.com/2025/distill-paraphrases/ | Do reasoning models use their scratchpad like we do? Evidence from dis | IDX | interpretability |
| 74 | https://alignment.anthropic.com/2025/honesty-elicitation/ | Evaluating honesty and lie detection techniques on a diverse suite dis | IDX | interpretability |
| 75 | https://alignment.anthropic.com/2026/chive/ | Would This Change Your Answer? Evaluating Explanations of LLM Behavior | IDX | interpretability |
| 76 | https://alignment.anthropic.com/2026/introspection-adapters/ | Introspection Adapters: Training LLMs to Report Their Learned Behavior | IDX | interpretability |
| 77 | https://alignment.anthropic.com/2026/lie-detectors/ | Fine-Tuned Lie Detectors Failed to Generalize We trained lie detectors | IDX | interpretability |
| 78 | https://arxiv.org/abs/2201.11903 | chain-of-thought | REC | interpretability |
| 79 | https://arxiv.org/abs/2603.21396 | Mechanisms of Introspective Awareness | RES | interpretability |
| 80 | https://proceedings.neurips.cc/paper_files/paper/2023/file/ed3fea9033a80fea1376299fa7863f4a-Paper-Conference.pdf | say what they think | REC | interpretability |
| 81 | https://transformer-circuits.pub/ | Transformer Circuits thread | IDX,REC,RES | interpretability |
| 82 | https://transformer-circuits.pub/2026/nla/ | Natural Language Autoencoders Produce Unsupervised Explanations of LLM | RES | interpretability |
| 83 | https://transluce.org/observability-interface | know information that they do not report when asked | REC | interpretability |
| 84 | https://www.alignment.org/blog/mechanistic-anomaly-detection-and-elk/ | anomaly detection | REC | interpretability |
| 85 | https://www.anthropic.com/research/influence-functions | Tracing Model Outputs to the Training Data We present a summary of Stu | IDX | interpretability |
| 86 | https://www.anthropic.com/research/language-models-mostly-know-what-they-know | Language Models (Mostly) Know What They Know Kadavath et al., 2022 We  | IDX | interpretability |
| 87 | https://www.anthropic.com/research/measuring-faithfulness-in-chain-of-thought-reasoning | Measuring Faithfulness in Chain-of-Thought Reasoning Lanham et al., 20 | IDX | interpretability |
| 88 | https://www.anthropic.com/research/open-source-circuit-tracing | open-source circuits | FEL | interpretability |
| 89 | https://www.anthropic.com/research/persona-vectors | persona vectors | RES | interpretability |
| 90 | https://www.anthropic.com/research/probes-catch-sleeper-agents | Simple Probes can Catch Sleeper Agents We find that probing, a simple  | IDX | interpretability |
| 91 | https://www.anthropic.com/research/question-decomposition-improves-the-faithfulness-of-model-generated-reasoning | Question Decomposition Improves the Faithfulness of Model-Generated Re | IDX | interpretability |
| 92 | https://www.anthropic.com/research/reasoning-models-dont-say-think | Reasoning Models Don't Always Say What They Think Chen et al., 2025 We | IDX | interpretability |
| 93 | https://www.anthropic.com/research/studying-large-language-model-generalization-with-influence-functions | Studying Large Language Model Generalization with Influence Functions  | IDX | interpretability |
| 94 | https://www.anthropic.com/research/team/interpretability | Interpretability | FRT | interpretability |
| 95 | https://www.lesswrong.com/posts/WCj7WgFSLmyKaMwPR/coup-probes-catching-catastrophes-with-probes-trained-off | shift from fixed datasets of synthetic data to data generated by the m | REC | interpretability |
| 96 | https://alignment.anthropic.com/2024/how-to-alignment-faking/index.html | How to Replicate and Extend our Alignment Faking Demo We describe how  | IDX | model organisms |
| 97 | https://alignment.anthropic.com/2025/alignment-faking-mitigations/ | Towards training-time mitigations for alignment faking in RL We constr | IDX | model organisms |
| 98 | https://alignment.anthropic.com/2025/auditing-mo-replication/ | Open Source Replication of the Auditing Game Model Organism We release | IDX | model organisms |
| 99 | https://alignment.anthropic.com/2025/automated-auditing/ | Building and evaluating alignment auditing agents In testing, our agen | IDX | model organisms |
| 100 | https://alignment.anthropic.com/2025/believe-it-or-not/ | Believe It or Not: How Deeply do LLMs Believe Implanted Facts? We intr | IDX | model organisms |
| 101 | https://alignment.anthropic.com/2025/bloom-auto-evals/ | Bloom: an open source tool for automated behavioral evaluations Bloom  | IDX | model organisms |
| 102 | https://alignment.anthropic.com/2025/inoculation-prompting/ | Inoculation Prompting: Instructing LLMs to misbehave at train-time imp | IDX | model organisms |
| 103 | https://alignment.anthropic.com/2025/modifying-beliefs-via-sdf/ | Modifying LLM Beliefs with Synthetic Document Finetuning We study whet | IDX | model organisms |
| 104 | https://alignment.anthropic.com/2025/petri/ | Petri: An open-source auditing tool to accelerate AI safety research A | FEL,IDX | model organisms |
| 105 | https://alignment.anthropic.com/2025/reward-hacking-ooc/index.html | Training on Documents about Reward Hacking Induces Reward Hacking Does | IDX | model organisms |
| 106 | https://alignment.anthropic.com/2025/subliminal-learning/ | Subliminal Learning: Language Models Transmit Behavioral Traits via Hi | IDX,RES | model organisms |
| 107 | https://alignment.anthropic.com/2025/wont-vs-cant/ | Won't vs. Can't: Sandbagging-like Behavior from Claude Models We find  | IDX | model organisms |
| 108 | https://alignment.anthropic.com/2026/auditbench/ | AuditBench: Evaluating Alignment Auditing Techniques on Models with Hi | IDX,RES | model organisms |
| 109 | https://alignment.anthropic.com/2026/coding-audit-realism/ | Measuring and improving coding audit realism with deployment resources | IDX | model organisms |
| 110 | https://alignment.anthropic.com/2026/hot-mess-of-ai/ | The Hot Mess of AI: How Does Misalignment Scale with Model Intelligenc | IDX | model organisms |
| 111 | https://alignment.anthropic.com/2026/petri-v2/ | Petri 2.0: New Scenarios, New Model Comparisons, and Improved Eval-Awa | IDX | model organisms |
| 112 | https://alignment.anthropic.com/2026/psm/ | The Persona Selection Model: Why AI Assistants might Behave like Human | IDX | model organisms |
| 113 | https://alignment.anthropic.com/2026/teaching-claude-why/ | Teaching Claude Why We use agentic misalignment as a case study to stu | IDX | model organisms |
| 114 | https://alignment.anthropic.com/2026/training-alignment-auditors/ | Training Alignment Auditors via Reinforcement Learning We train LLMs t | IDX | model organisms |
| 115 | https://arxiv.org/abs/2507.14805 | subliminal learning | FEL,RES | model organisms |
| 116 | https://www.anthropic.com/research/agentic-misalignment | agentic misalignment | FEL | model organisms |
| 117 | https://www.anthropic.com/research/alignment-faking | Alignment Faking in Large Language Models Greenblatt et al., 2024 We p | IDX | model organisms |
| 118 | https://www.anthropic.com/research/auditing-hidden-objectives | Auditing Language Models for Hidden Objectives Marks,* Treutlein,* et  | IDX | model organisms |
| 119 | https://www.anthropic.com/research/petri-open-source-auditing | Petri auditing tool | RES | model organisms |
| 120 | https://www.anthropic.com/research/reward-tampering | Sycophancy to Subterfuge: Investigating Reward-Tampering in Large Lang | IDX | model organisms |
| 121 | https://www.lesswrong.com/posts/ChDH335ckdvpxXaXX/model-organisms-of-misalignment-the-case-for-a-new-pillar-of-1 | model organisms of misalignment | RES | model organisms |
| 122 | https://alignment.anthropic.com/2024/anthropic-fellows-program/ | Introducing the Anthropic Fellows Program for AI Safety Research | FEL | other |
| 123 | https://alignment.anthropic.com/2024/anthropic-fellows-program/index.html | Introducing the Anthropic Fellows Program for AI Safety Research We're | IDX | other |
| 124 | https://alignment.anthropic.com/2025/anthropic-fellows-program-2026/ | Anthropic Fellows Program 2026 Apply now for our AI safety research fe | IDX | other |
| 125 | https://alignment.anthropic.com/2025/openai-findings/ | Findings from a Pilot Anthropic–OpenAI Alignment Evaluation Exercise A | IDX | other |
| 126 | https://alignment.anthropic.com/2025/recommended-directions/ | Recommendations for Technical AI Safety Research Directions | FEL,RES | other |
| 127 | https://alignment.anthropic.com/2025/recommended-directions/index.html | Recommendations for Technical AI Safety Research Directions A collecti | IDX | other |
| 128 | https://alignment.anthropic.com/2026/anthropic-residency/ | Anthropic Residency: applications open for established technical leade | IDX | other |
| 129 | https://arxiv.org/abs/1805.00899 | Irving et al., 2018 | REC | other (citation only; title not read) |
| 130 | https://arxiv.org/abs/1810.08575 | Christiano et al., 2018 | REC | other (citation only; title not read) |
| 131 | https://arxiv.org/abs/2109.10862 | Wu et al., 2021 | REC | other (citation only; title not read) |
| 132 | https://arxiv.org/abs/2206.05802 | incorporate AI assistance | REC | other (citation only; title not read) |
| 133 | https://arxiv.org/abs/2210.10760 | models of varying scales | REC | other (citation only; title not read) |
| 134 | https://arxiv.org/abs/2212.03827 | Burns et al., 2022 | REC | other (citation only; title not read) |
| 135 | https://arxiv.org/abs/2304.13734 | Azaria & Mitchell, 2023 | REC | other (citation only; title not read) |
| 136 | https://arxiv.org/abs/2306.03341 | Li et al., 2023 | REC | other (citation only; title not read) |
| 137 | https://arxiv.org/abs/2306.09983 | Furi et al., 2023 | REC | other (citation only; title not read) |
| 138 | https://arxiv.org/abs/2307.11768 | Radhakrishnan et al., 2023 | REC | other (citation only; title not read) |
| 139 | https://arxiv.org/abs/2307.13702 | Lanham et al., 2023 | REC | other (citation only; title not read) |
| 140 | https://arxiv.org/abs/2307.15043 | universal | REC | other (citation only; title not read) |
| 141 | https://arxiv.org/abs/2310.01405 | Zou et al., 2023 | REC | other (citation only; title not read) |
| 142 | https://arxiv.org/abs/2310.06824 | Marks & Tegmark, 2023 | REC | other (citation only; title not read) |
| 143 | https://arxiv.org/abs/2310.13548 | please the user | REC | other (citation only; title not read) |
| 144 | https://arxiv.org/abs/2311.08702 | Michael et al., 2023 | REC | other (citation only; title not read) |
| 145 | https://arxiv.org/abs/2311.10538 | Naihin et al., 2023 | REC | other (citation only; title not read) |
| 146 | https://arxiv.org/abs/2311.12022 | difficult ones that target PhD-level knowledge | REC | other (citation only; title not read) |
| 147 | https://arxiv.org/abs/2312.01037 | here | REC | other (citation only; title not read) |
| 148 | https://arxiv.org/abs/2312.03729 | circumstances under which | REC | other (citation only; title not read) |
| 149 | https://arxiv.org/abs/2312.06681 | Panickssery et al., 2024 | REC | other (citation only; title not read) |
| 150 | https://arxiv.org/abs/2312.09390 | Burns et al., 2023 | REC | other (citation only; title not read) |
| 151 | https://arxiv.org/abs/2312.12747 | Mills et al., 2024 | REC | other (citation only; title not read) |
| 152 | https://arxiv.org/abs/2401.06102 | Ghandeharioun et al., 2024 | REC | other (citation only; title not read) |
| 153 | https://arxiv.org/abs/2401.06751 | Hase et al., 2024 | REC | other (citation only; title not read) |
| 154 | https://arxiv.org/abs/2401.13138 | Chan et al., 2024 | REC | other (citation only; title not read) |
| 155 | https://arxiv.org/abs/2401.13986 | Chen et al., 2024 | REC | other (citation only; title not read) |
| 156 | https://arxiv.org/abs/2402.06782 | Khan et al., 2024 | REC | other (citation only; title not read) |
| 157 | https://arxiv.org/abs/2402.10260 | Souly et al. (2024) | REC | other (citation only; title not read) |
| 158 | https://arxiv.org/abs/2403.05518 | Chua et al., 2024 | REC | other (citation only; title not read) |
| 159 | https://arxiv.org/abs/2403.07918 | differential impact | REC | other (citation only; title not read) |
| 160 | https://arxiv.org/abs/2403.09472 | Sun et al., 2024 | REC | other (citation only; title not read) |
| 161 | https://arxiv.org/abs/2403.10949 | Chen et al., 2024 | REC | other (citation only; title not read) |
| 162 | https://arxiv.org/abs/2406.04313 | life | REC | other (citation only; title not read) |
| 163 | https://arxiv.org/abs/2406.04341 | expediting searches | REC | other (citation only; title not read) |
| 164 | https://arxiv.org/abs/2406.07358v2 | strategically choose not to reveal | REC | other (citation only; title not read) |
| 165 | https://arxiv.org/abs/2407.04622 | Kenton et al., 2024 | REC | other (citation only; title not read) |
| 166 | https://arxiv.org/abs/2407.04694 | situations | REC | other (citation only; title not read) |
| 167 | https://arxiv.org/abs/2407.13647 | Yang et al., 2024 | REC | other (citation only; title not read) |
| 168 | https://arxiv.org/abs/2407.13692 | Kirchner et al., 2024 | REC | other (citation only; title not read) |
| 169 | https://arxiv.org/abs/2409.18433 | Ding et al., 2024 | REC | other (citation only; title not read) |
| 170 | https://arxiv.org/abs/2410.03768 | pass messages | REC | other (citation only; title not read) |
| 171 | https://arxiv.org/abs/2410.05629v1 | Zhuang et al., 2024 | REC | other (citation only; title not read) |
| 172 | https://arxiv.org/abs/2410.09024 | Andriushchenko et al. (2024) | REC | other (citation only; title not read) |
| 173 | https://arxiv.org/abs/2410.13215 | trade off against | REC | other (citation only; title not read) |
| 174 | https://arxiv.org/abs/2410.13787 | Binder et al., 2024 | REC | other (citation only; title not read) |
| 175 | https://arxiv.org/abs/2412.08686 | Pan et al., 2024 | REC | other (citation only; title not read) |
| 176 | https://arxiv.org/abs/2412.14093 | fake being more aligned | REC | other (citation only; title not read) |
| 177 | https://arxiv.org/abs/2506.18032 | Why Do Some Language Models Fake Alignment While Others Don't? We inve | IDX | model organisms |
| 178 | https://belindal.github.io/ | Belinda Li | RES | other (person or team page) |
| 179 | https://elanapearl.github.io/ | Elana Simon | RES | other (person or team page) |
| 180 | https://evhub.github.io/ | Evan Hubinger | RES | other (person or team page) |
| 181 | https://jan.leike.name/ | Jan Leike | FEL | other (person or team page) |
| 182 | https://jlindsey15.github.io/ | Jack Lindsey | RES | other (person or team page) |
| 183 | https://nicholas.carlini.com/ | Nicholas Carlini | RES | other (person or team page) |
| 184 | https://scholar.google.com/citations?user=fW7yK10AAAAJ&hl=en | Samuel Marks | RES | other (person or team page) |
| 185 | https://scholar.google.com/citations?user=za0-taQAAAAJ&hl=en | Ethan Perez | RES | other (person or team page) |
| 186 | https://sohldickstein.com/ | Jascha Sohl-Dickstein | RES | other (person or team page) |
| 187 | https://www.anthropic.com/news/a-new-initiative-for-developing-third-party-model-evaluations | here | REC | other (citation only; title not read) |
| 188 | https://www.anthropic.com/research | Alignment Science team | IDX | other |
| 189 | https://www.anthropic.com/research/team/alignment | Alignment | FRT | other (person or team page) |
| 190 | https://www.anthropic.com/research/team/economics | Economics | FRT | other (person or team page) |
| 191 | https://www.anthropic.com/research/team/societal-impacts | Societal Impacts | FRT | other (person or team page) |
| 192 | https://www.linkedin.com/in/sara-price-310757b2/ | Sara Price | RES | other (person or team page) |
| 193 | https://alignment.anthropic.com/2025/alignment-faking-revisited/ | Alignment Faking Revisited: Improved Classifiers and Open Source Exten | IDX | model organisms |
| 194 | https://alignment.anthropic.com/2025/bumpers/ | Putting up Bumpers Even if we can't solve alignment, we can solve the  | IDX | safeguards |
| 195 | https://alignment.anthropic.com/2025/introducing-safeguards-research-team/index.html | Introducing Anthropic's Safeguards Research Team We're launching a new | IDX | safeguards |
| 196 | https://alignment.anthropic.com/2025/pretraining-data-filtering/ | Enhancing Model Safety through Pretraining Data Filtering We experimen | IDX | safeguards |
| 197 | https://alignment.anthropic.com/2025/selective-gradient-masking | Beyond Data Filtering: Knowledge Localization for Capability Removal i | IDX | safeguards |
| 198 | https://alignment.anthropic.com/2025/summarization-for-monitoring/index.html | Monitoring Computer Use via Hierarchical Summarization We introduce hi | IDX | safeguards |
| 199 | https://alignment.anthropic.com/2026/graft/ | Reducing Reward Hacking by Localizing Bad Behavior Instead of Penalizi | IDX | safeguards |
| 200 | https://arxiv.org/abs/2409.18025 | machine unlearning | REC | safeguards |
| 201 | https://arxiv.org/abs/2410.08827 | further fine-tuning to elicit the unlearned knowledge | REC | safeguards |
| 202 | https://arxiv.org/abs/2411.07494 | Rapid Response: Mitigating LLM Jailbreaks with a Few Examples Peng et  | FEL,IDX | safeguards |
| 203 | https://arxiv.org/abs/2411.07494v1 | Rapid response | REC | safeguards |
| 204 | https://www.anthropic.com/research/many-shot-jailbreaking | Many-shot Jailbreaking Anil et al., 2024 We study a long-context jailb | IDX | safeguards |
| 205 | https://alignment.anthropic.com/2025/unsupervised-elicitation/ | Unsupervised Elicitation We introduce a new unsupervised algorithm for | IDX | scalable oversight |
| 206 | https://alignment.anthropic.com/2026/automated-w2s-researcher/ | Automated Weak-to-Strong Researcher We built autonomous AI agents that | IDX,RES | scalable oversight |
| 207 | https://alignment.anthropic.com/2026/challenges-hopes/ | 3 Challenges and 2 Hopes for the Safety of Unsupervised Elicitation We | IDX | scalable oversight |
| 208 | https://alignment.anthropic.com/2026/taste/ | TASTE: Can AI Models Judge AI Safety Research Proposals? We introduce  | FEL,IDX | scalable oversight |
| 209 | https://arxiv.org/abs/2604.22082 | Removing Sandbagging in LLMs by Training with Weak Supervision | RES | scalable oversight |
| 210 | https://www.anthropic.com/research/constitutional-ai-harmlessness-from-ai-feedback | Constitutional AI: Harmlessness from AI Feedback Bai et al., 2022 We i | IDX | scalable oversight |
| 211 | https://www.anthropic.com/research/measuring-progress-on-scalable-oversight-for-large-language-models | Measuring Progress on Scalable Oversight for Large Language Models Bow | IDX | scalable oversight |
| 212 | https://www.anthropic.com/research/specific-versus-general-principles-for-constitutional-ai | Specific versus General Principles for Constitutional AI Kundu et al., | IDX | scalable oversight |
| 213 | https://www.anthropic.com/research/towards-understanding-sycophancy-in-language-models | Towards Understanding Sycophancy in Language Models Sharma et al., 202 | IDX,REC | model organisms |
| 214 | https://www.anthropic.com/research/training-a-helpful-and-harmless-assistant-with-reinforcement-learning-from-human-feedback | Training a Helpful and Harmless Assistant with Reinforcement Learning  | IDX | scalable oversight |

## 5. What could not be opened

- No linked paper, PDF or arXiv abstract was opened; their URLs come only from page HTML (T2 and T4).
- Linked posts on alignment.anthropic.com other than the five requested pages, and the anthropic.com research posts, were not opened.
- transformer-circuits.pub/2026/nla/, red.anthropic.com pages and the lesswrong, alignment.org and transluce.org links were not opened.
- Rows marked 'citation only' show only an author-year or bare phrase; their titles and topics were not read, so their category is a placeholder.
- Excluded from T4 as not paper/post/repo/team pages: job postings (greenhouse), Google Drive/Docs links, claude.ai, platform.claude.com, social profiles, site nav and search.
