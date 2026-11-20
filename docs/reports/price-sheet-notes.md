# Price sheet notes

Fetched 2026-11-19 (UTC) by plain HTTPS GET, no key, no login. OPENED: yes.

- Pricing page: https://platform.claude.com/docs/en/about-claude/pricing (docs.claude.com redirects here). OPENED: yes.
- Model IDs: https://platform.claude.com/docs/en/about-claude/models/overview (claude-fable-5-2, claude-opus-5-5, claude-sonnet-5-5, claude-haiku-5-5). OPENED: yes.
- claude.com/pricing was not opened; the docs page is the API price of record.

USD per million tokens, read from the "Model pricing" table:

| Model | Input | Output | Cache write 5m | Cache write 1h | Cache read |
|---|---|---|---|---|---|
| claude-fable-5-2 | 8 | 40 | 10 | 16 | 0.20 |
| claude-opus-5-5 | 4 | 20 | 5 | 8 | 0.20 |
| claude-sonnet-5-5 | 2 | 10 | 2.50 | 4 | 0.10 |
| claude-haiku-5-5, prompts up to 100,000 tokens | 0.10 | 0.50 | 0.125 | 0.20 | 0.01 |
| claude-haiku-5-5, prompts over 100,000 tokens | 0.50 | 2.50 | 0.625 | 1 | 0.05 |

Multipliers as the page states them: 5m write 1.25x input, 1h write 2x input, cache read 0.025x
(Fable 5.2), 0.05x (Opus 5.5, Sonnet 5.5), 0.1x (others, Haiku 5.5). The table matches these.

Caveats:
- Haiku 5.5 is tiered by prompt length; the sheet carries the `long_context` tier and the ledger picks it by
  total prompt tokens (input + cache read + cache write). The Haiku input figure ($0.10) is far below Haiku
  4.5 ($1); I read the page as printed and did not infer it. Re-check before any Haiku run.
- Fast mode, Batch API and data-residency modifiers are not in the sheet; the harness uses none of them.
- Thinking tokens are billed as output tokens and arrive inside `usage.output_tokens`.
- Claude 4.7+ models use a tokenizer producing about 30% more tokens for the same text: token counts are not
  comparable to older models or other families.
- No null prices. `aliases` is empty: a returned model ID that differs from the requested one voids the episode.
- The ledger refuses a sheet older than 3 days: refetch and bump `fetched` after reading the page again.
