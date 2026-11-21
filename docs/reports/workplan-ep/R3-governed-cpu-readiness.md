# R3 governed CPU readiness

## L2 plan and treatment binding

Governed verification now requires the independent per-arm reference
digest, input and output token caps, and output-limit rule. These terms
must cover the exact schedule and agree within each matched block. The
reference digest binds the Board verification post. The verifier also
checks the actual facilitator instruction, source and decoy content,
and named reads against the scheduled condition before checking replayed
prompts and host replies.

Repinning a worker archive previously allowed changed reference text,
changed caps, or a changed output-limit rule to pass under the same
schedule. Astra independently reproduced a second case in which a
warning-labeled arm delivered neutral instructions. The governed path
refuses these cases and an otherwise correctly labeled decoy read.
Historical scripted replay retains its original evidence label.

Two isolated CPU jobs completed from the same pinned source closure.
The clean arm recorded `no_planted_roots` and the trigger-only arm
recorded `trigger_only`. Both retained six attempts and 48 synthetic
output tokens. Their plant readouts were null. Each job was reaped and
removed, and its plan, host tape and export passed bound replay. The
historical planted export's bound replay stayed byte-identical.

| Artifact | SHA-256 |
| --- | --- |
| L2 source manifest | `9244a389abe770aaa0d1dffa5c94c42f58e2c8d35cfae636eb37492bf5330c0f` |
| Clean CPU bound replay | `7d96b7fd2b72a84b52b62dc17d05eb67efa05ce4688ff76c82ebd7616f807a05` |
| Trigger-only CPU bound replay | `e87c721863b2563a9e327a39597d5e2591cdf182ab6283d122650836d5bde355` |
| Historical planted bound replay | `21682ad8f2534d89e203b80fcd0721d81060d22ca39c5db0c42f2841bfe5b697` |

The L2 closure and 58 passing tests are in
`runs/r3-l2-governed-controls.GgS4JI`. The first isolated test attempt
omitted two test modules. The final closure includes both and ran all
12 selected modules.

## L5 interrupted delivery

The public scripted delivery harness persists each attempt before
container creation, then retains the exact created ID, validated
acknowledgment and confirmed cleanup as separate records. The prefix
auditor checks a pinned tape and round plan against the actual main
and delivery Board prefixes through each witnessed event. Independent
review reproduced an earlier flaw where editing a guide post while
keeping the named-read bytes intact escaped verification. The final
auditor rejects that change. It can still verify intact records before
a torn unwitnessed tail.

| Mocked interruption | First attempt | Second attempt |
| --- | --- | --- |
| Worker exchange timeout | Acknowledgment and cleanup verified | Cleanup verified, acknowledgment unavailable |
| Cleanup error | Acknowledgment and cleanup verified | Acknowledgment retained, cleanup and wall time unknown |

Twenty isolated tests passed, and the previously archived completed
delivery audit remained byte-identical at
`41b9545ca69e459265418244e0d8fd559abbf3efe94a2520ca118db7bc640470`.
The final source and mock receipts are in
`runs/r3-l5-delivery-prefix.0rmydK`, manifest SHA-256
`02e4bffbd3e739da9004f1a1d7f1579151c0143cabc39b7f4402726753d72274`.
The prefix report preserves unknowns and emits no paired effect.

These closures exercise the public CPU instruments. Native R3 still
requires frozen cohorts, separate custody and review, exact native
runner and resource admission, and measured scoring and cleanup.
[First slices protocol and admission](R3-first-slices-admission.md)

## Paired runner rehearsal

The public rehearsal CLI ran both a warning/neutral pair and a pair stopped
during the second arm. The completed case used independently prepared
fixture terms and verified both arms and the captured responses. The stopped
case retained both arm records, including the failed second-arm attempt,
and omitted the paired score and completed index.

Both ran in real isolated CPU containers using the same executable and
read-only source mount. Runtime inspection confirmed no network or GPU
device requests, one CPU, and a 128 MiB memory limit. Both full container
IDs were absent after cleanup. The captured responses in this public
rehearsal are scripted and retained within the same process. Native
host/worker custody, protected inputs, and launch admission remain open.

The exact source manifest SHA-256 is
`20038a4f914ab2f2593db5fb56da0f88fdd304c2dc0f04e7152735bfba0ef731`.
Eighteen focused tests passed. The CLI receipts and rerunnable wrapper
are under `runs/r3-l2-runner-rehearsal.7ZhUDP`.

The rehearsal now writes the archive ID and schedule digest before
generation. In the interrupted case it checks those values and the
planned block and arm position, and requires the actual recorded
condition to match the scheduled treatment. A valid neutral arm
substituted for warning and an arm with another archive ID both passed
the previous rehearsal and are now refused.

The replacement source and runtime receipts are in
`runs/r3-l2-rehearsal-identity.p8VTTs`. The source manifest SHA-256 is
`b8bbe09ff19e3dd74d4468c24ac4137ea30e010a46f9eeb2ede872f84dd7a1a0`.
Twenty-six tests passed. Both actual isolated CPU containers were
removed. The interrupted receipt keeps the paired score unset. The
plan and scripted responses are still generated within the same
public rehearsal process.
