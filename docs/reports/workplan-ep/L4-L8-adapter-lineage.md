# L4-E to L8-D checkpoint handoff

The L8-D preflight checks a local evidence bundle before held-out activation collection. It binds
the L8-D plan to the digest of a settled L4-E receipt. The receipt's settlement time must precede
the L8-D freeze time, and both records must name the same base model revision and checkpoint
artifacts. The preflight reads bytes and checks SHA-256 for the files each record references.

| Record | Fields |
| --- | --- |
| L4-E receipt | `line` is `L4-E`, `status` is `settled`, `settled_utc`, `base_revision`, `model_manifest`, `adapter_config`, `resource_receipt`, `context_control`, `training`, and `checkpoints.before` and `checkpoints.after` |
| L8-D plan | `prediction` is `L8-D`, `frozen_utc`, `base_revision`, `l4_receipt`, `activation_protocol`, `calibration`, `heldout`, and the same checkpoint references |
| Artifact reference | `path` relative to the bundle and `sha256` of the complete file. Use a standalone checkpoint file or frozen archive for a multi-file checkpoint. |
| Split manifest | JSON object with `samples`, an array of entries with `sample_id`, `family_id`, and `content`, an artifact reference to the prompt bytes |

Use a fixed evidence bundle and pass the independently recorded L8-D plan digest. The check
rejects a future freeze timestamp and reads each sample's actual bytes to verify its digest.
Each split must be nonempty. Across training, calibration and held-out sets the check rejects a
reused sample ID, family ID or verified content digest. It checks the declared memberships. The dataset
builder must derive those identifiers consistently, including across paraphrases in a family.
The activation protocol file must carry the exact layer/token selection, normalization and
random-direction control for the experiment. A reviewer still checks those contents, the real
training and settlement receipts, and which bytes the model loader used. A positive L8-D
comparison requires independently established adapter consolidation. If the underlying checkpoint
bytes are identical, record the L4-E outcome and hold L8-D because the pair supplies no change
to measure. Passing the preflight alone gives no authority to run a job.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m lab.adapter_lineage /path/to/bundle /path/to/l8d-plan.json --plan-sha256 "$L8_D_FROZEN_PLAN_SHA256"
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v lab.tests.test_adapter_lineage
```

The CPU tests use synthetic files and exercise checkpoint tampering, mismatched references,
unchanged artifacts, unfinished or late L4-E settlement, model revision mismatch, false prompt
digests, split aliases, unsafe paths, and external plan pinning through the CLI.
They establish the file and chronology checks. No L4-E checkpoint or L8-D activation was produced.

[Portfolio dependency](R2-R4-protocol-readiness.md#l4-e-checkpoint-dependency-and-coordination-extension) · [Preflight](../../../lab/adapter_lineage.py)

## Unambiguous records and tensor-content preflight

The plan, L4 receipt and split inventories now reject duplicate JSON members
at any depth and reject nonstandard numeric constants. A digest pin protects
bytes. Requiring unambiguous JSON prevents different readers from treating
the same pinned file as different split inventories or settlement states.

For bounded standalone Safetensors checkpoints, add
`--safetensors-max-bytes "$REVIEWED_CHECKPOINT_LIMIT"`. In the existing offline
CPU image, the verifier reads each file within that bound and checks the same
bytes against the lineage digest before decoding. Both stages must have the
same named tensor inventory, types and shapes. It full-hashes the bytes of each
tensor, independent of package metadata. The synthetic CLI accepted one changed
tensor and refused a repack with identical weights and different metadata.
The archived result is `runs/l4-l8-tensors-scripted.ZaXisb/tensor-lineage-result.json`,
SHA-256 `194e27bc17046effd23565bf4f7f018eb2853e862ffe4670a3ac4fb308a1293f`.
The focused suite passed 19 tests in the pinned CPU image. The decoder accepted a deliberately ambiguous fixture with two tensor declarations before the strict header check was added. The CLI now refuses the duplicate header even when the artifact digest is pinned.

A changed tensor payload establishes a file-level difference. The L4-E
settled training run, measurable improvement against the context control,
the loader's byte receipts and the frozen L8-D assessment still require
independent evidence. Standalone Safetensors is a supported development
format. A different final checkpoint layout needs a reviewed comparison.

## CPU loader and hook receipt

The offline [loader witness](../../../lab/l8_loader_receipt.py) uses the
standalone Safetensors development format. It verifies the frozen plan,
reads and pins each checkpoint, and passes those exact bytes to the CPU
decoder. Before loading, it compares the expected state names, dtypes and
shapes to the fresh target module. After strict load, it rehashes installed
tensor bytes. It rejects an unexpected dtype conversion and a test loader
that mutates the weights after loading.

For the synthetic fixture, the same float32 input produced forward-hook
outputs of 4 and 8 before and after loading. The saved receipt includes both
checkpoint digests, both installed-state tensor digests, the input and hook
tensor digests, and the CPU Torch version. Two direct CLI replays emitted
byte-identical output. The receipt is
`runs/l8-loader-scripted.cDdneC/loader-receipt.json`, SHA-256
`56f3f97be5ff3f28764c6022a779d5c53323816d680d75b178ccbf6790e1db12`.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m lab.l8_loader_receipt \
  runs/l8-loader-scripted.cDdneC runs/l8-loader-scripted.cDdneC/l8.json \
  --plan-sha256 2154e775c5e0e9e06ccccc53b9ffe3f6aa3b0628b8782fe4ac81b7d476dabf0f \
  --max-bytes 2048
```

Use the pinned offline CPU image for this command. The receipt is for a
linear fixture. Native L8-D still needs an admitted training result, a
run-bound base and selected-adapter receipt from the actual model loader,
independent evidence that the base remains unchanged, and matching
tokenization, layer and token selection, normalization, and random-control
records. The independent L8-B text and activation comparison still depends on
frozen causal labels and a reviewed hook procedure.

The independent review reproduced this receipt byte for byte. It also showed
that PyTorch can modify a module with tied parameters before a subsequent
state check rejects the load. The fixture loader is private and each stage
owns a fresh instance. Failure aborts that stage before recording an activation
or returning a module. A future loader that reuses instances needs an explicit
rollback or discard path.
