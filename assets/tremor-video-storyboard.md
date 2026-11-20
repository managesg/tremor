# TREMOR Video Storyboard

**Concept:** 60–90 second animated explainer, built from the SVG hero. Every frame is already defined in the
SVG; the video is a walkthrough of the same visual grammar.

---

## Visual language (from Lance Martin's designs)

- **Agent team** = diamond of 4 core nodes, expandable to rings of 16/32. Nodes pulse when they act.
- **Shared state** = ripple rings around the team. Ring radius = rerun variance (susceptibility).
- **Memory** = two ellipses (daily/hippocampus, long-term/neocortex). Area ∝ characters stored (Lance's
  Pokemon slide).
- **Dreaming** = arrows hippocampus → neocortex (offline replay) and back (consolidation).
- **Poison memory** = glowing trap node; a spiral of dreaming arrows corrects it.
- **Eight research lines** = orbiting satellites, rotating slowly.

---

## Scene sequence (each beat ≈ 5–8 s)

| Time | Visual | Narration (script) | Lance reference |
|------|--------|-------------------|-----------------|
| 0–6 s | Fade in: dark field. Title "TREMOR" at bottom. Four agent nodes appear in diamond, pulsing. | "AI agents don't work alone. They form teams that share a board, notes, memory." | Story 1: teams of agents |
| 6–12 s | Ripple rings grow around the team, breathing. | "The team is a medium. It has properties no single agent has: how much it wobbles, how far errors spread, how correlated its mistakes are." | First principles: a collective is a physical medium |
| 12–20 s | Memory ellipses appear above team. Daily (left) small, long-term (right) larger. Arrows flow left→right (dreaming), then right→left (consolidation). | "Lance showed that agents write memory greedily inside a session. Dreaming is the offline process that replays daily memory into long-term knowledge — and corrects it." | Story 2: memory and dreaming; hippocampus → neocortex |
| 20–28 s | A red "POISON TRAP" node appears in daily memory. Dreaming arrows spiral around it and it fades. | "He also showed a wrong memory can trap an agent in a loop. Dreaming rescued it." | Wrong-memory trap; Pokemon memory directories |
| 28–36 s | Eight satellites appear in orbit: susceptibility, immune system, decorrelated monitors, dreaming, stigmergic coordination, trust, renormalization, activation readouts. | "Each of these is a measurable property. TREMOR turns it into a technique: spend verification where the team wobbles most; quarantine suspect memories; pick monitors whose failures don't overlap; and so on." | Eight lines; Lance's "tyranny of agent design" |
| 36–44 s | The central team expands from 4 to 16 nodes. The renormalization satellite highlights. | "Does a hierarchy beat a flat team? Renormalization tells us when." | Story 3: large teams |
| 44–52 s | Probe rays from the activation-readout satellite enter agent nodes. | "Probes inside local models flag a team failing together, before any single agent does." | Anthropic's features-as-monitors |
| 52–60 s | All satellites pulse together. The bottom timeline bar fills: Week 1 → Week 3 → Week 6 → 6 months → Public release. | "Six weeks: the shared instrument, three core techniques, first results. Six months: a second model family, external benchmarks, one open release." | Six-week deliverable |
| 60–65 s | Fade to: `github.com/managesg/tremor` · `README.md` · `WORKPLAN.md` | "Everything is open. The instrument, the logs, the negative results. github.com/managesg/tremor" | — |

---

## Production notes

- **Source of truth:** all shapes, colours, animations and timings are in `assets/tremor-hero-v2.svg`.
  The video is a camera move through that SVG, pausing at each satellite.
- **Tooling:** can be recorded from a browser with `ffmpeg` or rendered with `cairosvg` + `ffmpeg` frame by frame.
- **Music/SFX:** subtle ambient (Lance's talk has a calm, deliberate rhythm).
- **Accessibility:** full caption track; alt text in SVG covers every frame.

---

## Short version (30 s, for social)

Cut to beats: diamond + ripples (6 s) → memory + dreaming (6 s) → poison trap corrected (6 s) → 8 satellites (6 s) → expand to 16 + timeline (6 s) → link (4 s).

---

## Files in the repo

- `assets/tremor-hero-v2.svg` — the complete animated diagram, every element ID'd for programmatic control.
- `assets/tremor-video-storyboard.md` — this file.
- `README.md` — embeds the SVG.
- `WORKPLAN.md` — the public work plan.