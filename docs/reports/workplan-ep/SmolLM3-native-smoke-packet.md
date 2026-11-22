# SmolLM3 native smoke review packet

The smoke exercises one public prompt on the verified SmolLM3-3B
checkpoint. A successful run establishes that the pinned local CUDA
loader can load and generate inside the Spark serving constraints. The
separate L1–L3 experiment still needs a reviewed family choice, frozen
comparisons and protected data.

## Inputs and CPU rehearsal

Bundle `runs/replication-smollm3-staging.out5A0/smoke-worker/verified-retry`
contains both worker plans, the exact worker and adapter, and their input
manifest. The CUDA plan SHA-256 is
`514d0decfdf849432ad7893cb9b465af62d5fce8acdab4ee849a80d195326dc8`.
It binds the staged checkpoint manifest
`6ff79f0d818a19b9e36f64c7bae12558d099889eae5b368038133a4906df9d7f`,
CUDA device 0, and a 0.20 PyTorch allocator fraction.

The public prompt contains 73 canonical input tokens with thinking
disabled, has a two-token output cap, and uses deterministic generation.
The worker checks both actual prompt bytes and canonical token IDs before
loading the model. It records the load and generation times, output cap
status, and CUDA allocation and reservation peaks without storing
generated text.

The CPU plan passed against the actual checkpoint using one explicit
PyTorch thread. Its receipt SHA-256 is
`2355f8eb36ebbdd68691263a5fea5286b01b215ae52b2434954d445c78d7781f`.
The first CPU attempt timed out with the runtime's implicit thread
configuration. The isolated retry used explicit single-thread execution
and the final worker with peak-memory fields. The CPU receipt and
synthetic CUDA unit checks leave CUDA runtime compatibility unmeasured.

## Guard and settlement

- Use the existing pinned ARM64 image, read-only model and worker mounts,
  disabled networking, isolated worker logs and exact container identity.
  Verify the checkpoint bytes and container configuration before starting.
- Reuse the physical Spark guard lock and the 10 GiB host memory stop.
  Start checks must address pending attempts across both the calibration
  and smoke paths. A lock alone loses that protection when its process
  exits. The existing R2 admission and worker remain unchanged.
- Review the prior 70 GiB pre-start headroom, 300-second outer deadline
  and 0.1 GPU-hour reserve as one **proposed** envelope. The last leaves
  up to 60 seconds after the outer deadline before the reservation is
  exceeded. The reviewer can choose a different validated envelope.
- Assign the reservation to named replication capacity and account for
  elapsed time from start through confirmed cleanup. Record watchdog
  decisions, exact-ID removal and reaped attachment. Preserve the hold
  on uncertainty or an overrun. The R2/R3 balance and historical T7 hold
  have distinct purposes.

The worker plan does not open a GPU run. The run needs an independently
pinned admission and a separately placed replication reservation.

## Verified pre-start components

The offline preflight rehashed the staged model and four-file native
worker mount, then matched a synthetic admission to its exact replication
reserve. It refused the same reserve with a different admission ID.
The receipt is `offline-prestart-inputs.json` in the staging run root.
No live admission was written.

The pre-start container recipe pins the image, worker command, device,
read-only mounts, selected environment, and temporary filesystem. The
inspection format was exercised against an isolated CPU-only container.
CUDA device and mount refusals were tested with synthetic inspect output.
The actual CUDA create and attachment remain unverified.

## Connected launch review

The guarded launcher now performs the window and memory recheck under
the common lock, records pending intent before Docker creation, and acts on
the exact inspected ID. It keeps a separate pre-start inspection file and
clears the shared pending state only after confirmed removal, attachment
reaping and durable capture. The shared journal retains its existing
container-name format. The smoke uses its own admission and allocation.

The exact local review bundle is
`runs/replication-smollm3-staging.out5A0/native-launch-review`.
Its source manifest SHA-256 is
`145a26e2a49564c72bee37f7525079ae17ed565d462d037a261b07c3b27413be`.
Forty focused tests passed in that isolated tree. A mocked launch produced
receipts that passed both the semantic CUDA worker check and the replication
settlement check. The reservation stayed held until an exact synthetic
settlement was supplied. This exercises the launcher and receipt chain
without making a live CUDA result or changing the ledger.

The run operator needs the live admission and reservation pins to execute
this exact path. The worker check and the settlement check remain separate.
They establish technical CUDA behavior and accounting, respectively.

[Checkpoint and CPU evidence](Second-family-candidate-Smollm3.md) ·
[Spark guard and resource evidence](Spark-readiness.md)

## Cross-family tokenizer check

The pinned CPU container rendered `Return exactly [1].` with the staged
Qwen3.5-4B and SmolLM3-3B tokenizers. The native template's direct token IDs
matched rendering followed by encoding with `add_special_tokens=False`
in all four cases. The default encoder also matched on these fixtures.

| Model | Thinking disabled | Thinking enabled |
| --- | ---: | ---: |
| Qwen3.5-4B | 17 input tokens | 15 input tokens |
| SmolLM3-3B | 73 input tokens | 253 input tokens |

The SmolLM3 disabled-mode token digest matched the frozen smoke worker.
The paired replication should pin thinking mode alongside the renderer
and account for actual tokens in each family's tokenizer. These counts
describe one public prompt. The replication cohort, effective scoring and
GPU performance remain unmeasured.

The rerunnable check and receipt are in
`runs/replication-smollm3-staging.out5A0/render-parity.Ehwtrv`. The
receipt binds the two sets of tokenizer files and all four rendered
prompt and token-ID digests. Its SHA-256 is
`345845705557b0f454b1fd8fab321bda3a7ecce1d2c999405523f09cfef9eeb9`.

## Adversarial verification and current operator bundle

Two synthetic reproducers found preflight-to-start input drift and an
unverified Docker inspection sidecar. The launcher now revalidates the
exact admission, reservation, worker and snapshot after Docker inspection
and before attachment. The host capture binds the inspection bytes to
the exact created container. Independent metric verification replays
the image, device, worker command and read-only mount checks against the
expected paths. The staging owner retains custody of those paths during
execution because Docker's read-only mount does not prevent host writes.

Use `runs/replication-smollm3-staging.out5A0/native-launch-reviewed.tl0ZlD`
for operator review. Its source manifest SHA-256 is
`a923295dd72b0ea195ba09da505495437955bd38890354cce87a081dab1a652b`.
Run `sha256sum -c source.sha256` before using the bundle. Sixty focused
tests passed in that isolated tree. `python3 -B replay.py` exercised fake
Docker creation, attachment, inspection, metric verification and settlement.
The resulting `mocked-chain.json` SHA-256 is
`593af8ad31622cdee3a2d9d12bc6ad453db96682828eced66274ffb2da6e9b7b`.
The replay preserves the full reserve until a separate synthetic settlement.
It contains simulated CUDA measurements.

The metric verifier takes `guard.jsonl`, the reviewed snapshot path and
the reviewed worker mount path as positional arguments. It requires
`--host-capture-sha256`, `--worker-log-sha256` and `--admission-id`.

The paired L1–L3 design has a separate prospective metadata check. It
compares pinned task and replicate IDs, block and scoring context across
unchanged transfer, local recalibration and the common reference holdout.
It rejects group overlap across splits and exact trial relabeling. Without
a matched reference schedule it withholds the cross-family comparison.
The pairing and inventory suite passed all 20 tests in the model checkout.
The isolated pairing bundle
`runs/replication-smollm3-staging.out5A0/prospective-pairing-reviewed.ZxUw9g`
has manifest SHA-256
`3932da8d2ea4bf50ba1f7a708f70daa572134940c120540b8f77174360c27f93`.
Its 20-test suite skipped the check that needs the staged Qwen fixture.
Actual held-out manifests and outcomes still need independent custody.

## Unused reservation after a verified pre-attachment stop

An input change after Docker create can stop the launcher before attach.
The host receipt must show the exact inspected container in created state,
confirmed removal, zero elapsed attachment time, and empty worker output.
The verifier checks the inspection bytes against the host capture and
requires an independent worker-output pin. Incomplete inspection or
uncertain attachment or cleanup keeps the full reservation held.

With that evidence, a separately pinned `cancel` receipt can return the
unused reservation with a zero charge. It names the same admission,
reserve and host capture as a settlement. The verifier returns
`verified_unused_reservation_return`, which records a cancellation and
carries no CUDA result. The tool leaves the ledger unchanged.

The finalized verification bundle is
`runs/replication-smollm3-staging.out5A0/native-launch-cancellation-final.v022iV`.
Its source manifest SHA-256 is
`c8164f59f8b637fa56efcdca02c9bdc26cce92e58676e796f914d66bf450a05c`.
Sixty-four tests passed in the isolated closure. The successful mocked
launch and settlement replay was byte-identical. The new
`python3 -B replay_cancellation.py` drove a synthetic input-drift stop
through the launcher. The 0.1 GPU-hour hold survived the stopped attempt
and cleared only when an exact synthetic cancellation was supplied.
Its SHA-256 is
`923ea122e151dc96ac0cd1c29bf74e12e189cf9331961871c87e2baf9eb114ad`.

## Candidate for binding the launch to the ledger opening

The current detached review patch uses the independent opening verifier
both before Docker creation and after exact container inspection, before
attachment. It matches the placement to the actual R2 ledger and guard
capture, the admission and the reserve. The verification retains the
0.023123 GPU-hour R2 settlement and the provisional 4.0 GPU-hour T7 hold.
The launch command adds
`--opening-balance LEDGER R2_GUARD PLACEMENT PLACEMENT_SHA256`.
The placement pin must come from the resource owner, who also checks the
current ledger head. This patch specifically supports the first smoke
against a reviewed R2-only cut.

The detached candidate passed 75 tests. With the R3 typed-settlement
patch it passed 78. The prior mocked launch and cancellation outputs
and exact archived R2 digest all reproduce. Native GPU admission,
source adoption and actual technical results remain open.
[Source and verification](../../../runs/m8-smoke-bound-opening.xlu84i/OWNER.md)
