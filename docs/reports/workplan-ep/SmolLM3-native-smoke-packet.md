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

The worker plan does not open a GPU run. The launcher and resource owner
need to bind the reviewed envelope, shared pending-attempt check, exact
container and reservation before execution.

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

The offline settlement verifier keeps replication and program balances
separate and requires independently pinned worker and host receipts before
release. Launcher integration still needs fresh window and memory checks
under the common lock immediately before start, durable registration of the
pending attempt before Docker creation, and exact cleanup and reaping. A
separate worker-metric check must confirm the CUDA result before it counts
as a successful technical smoke.

[Checkpoint and CPU evidence](Second-family-candidate-Smollm3.md) ·
[Spark guard and resource evidence](Spark-readiness.md)
