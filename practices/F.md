id: F
version: 1
enforcer: lint.source_required
measures: poison_adoption, stale_fact_reuse, sprawl
---
Every note links its source. When a fact changes, add a new note that supersedes the old one; never rewrite the old note. Give each fact an expiry date and treat expired facts as unconfirmed until re-checked.
