# Qwen base checkpoint forward hooks on Spark

The exact staged Qwen3.5-4B base checkpoint loaded as
`Qwen3_5ForConditionalGeneration` in the pinned ARM64 CPU image. The
probe rehashed every file listed in the checkpoint manifest before
loading. Independent readback found no undeclared entries in the
snapshot directory. It used the public prompt `Return exactly [1].`, with five
native input tokens, one forward, and caching disabled.

| Source | Module | Observed CPU output |
| --- | --- | --- |
| Text layer 0, linear attention | `Qwen3_5DecoderLayer` | `[1, 5, 2560]` |
| Text layer 31, full attention | `Qwen3_5DecoderLayer` | `[1, 5, 2560]` |
| Layer 0 `linear_attn.in_proj_qkv` | `Linear` with weight shape `[8192, 2560]` | `[1, 5, 8192]` |
| Layer 31 `self_attn.q_proj` | `Linear` with weight shape `[8192, 2560]` | `[1, 5, 8192]` |

Each hook fired once and returned finite BF16 values. The receipt
records a digest after converting each observed tensor to float32.
The layer widths agree with the two prompts in the accepted CUDA
calibration, which had eight and seven tokens. The different prompts,
runtime settings and devices limit the comparison to shapes.

Live inspection recorded the `runc` runtime, no network, a read-only
root, a two-CPU quota, 12 GiB memory with no extra swap allowance, and
no GPU device request. The probe set PyTorch to one thread. Model file
verification took 13.30 seconds, loading 1.98 seconds, and tokenization,
hook setup, forward and capture together 7.26 seconds. The process reported peak RSS of
7,943,740 KiB. The named container was absent after exit and the same
vLLM engine process remained present.

## Evidence

- Local probe and receipt are in
  `runs/l4-l8-qwen-cpu-runtime.yLZUZZ`.
- Probe SHA-256
  `608727680929aa844896f4d230586e231829060979f139c66b18d06f0ae0bfc7`.
- Receipt SHA-256
  `c550de624a929f748486ecc649a4a1ef2c0bdce6ed1f784bf486f46ed3ac8eb9`.
- Checkpoint revision `851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a`,
  manifest SHA-256
  `9b70e85c464f8dddbe1c6094832f51043a85fa7dcdf281e0cb81aa0d2d4d6ea6`.
- Container image
  `sha256:c74c8710f2bc017b5de956853c50d896af4aa49b751bb87cbebf69e5206befb7`.

This run establishes CPU loading and hook execution on the base checkpoint
for two example targets. Milestone 5 still requires the independently
settled L4-E checkpoint pair and comparator evidence, followed by
actual loaded-state and hook receipts for the frozen L8-D probe.
[Adapter lineage](L4-L8-adapter-lineage.md) · [Accepted Spark calibration](Spark-readiness.md#calibration-result-and-settlement)

## Synthetic checkpoint switching on actual projections

A separate CPU probe captured the two projection inputs from the public
base forward. For each projection, it reused that same input with its
original BF16 weight and a synthetic checkpoint with the first output
channel's weight row negated. The strict Safetensors loader rehashed the
installed tensor for each stage.

Both projections produced `[1, 5, 8192]` hook outputs. The first channel
changed sign and the other channels retained equal values. Giving the
after file the before digest was refused before the module state changed.
Restoring the before state reproduced the installed weight digest and the
original numerical hook output. The receipt field
`restored_weight_and_hook_bytes` refers to those two checks. The probe
compared restored hook values rather than hashing the restored hook.

Each checkpoint occupied 41,943,128 bytes in a private temporary directory.
The receipt records the digests computed in the probe. The temporary
files were released with that directory, so the receipt supports a
runtime test and does not supply an independently retained checkpoint pair.
The read-only model snapshot was rehashed and independently checked
for a closed file inventory. The bounded CPU container exited, and the
existing vLLM engine continued running.

The source and receipt are in
`runs/l4-l8-qwen-projection-load.xfos3z`. Their SHA-256 digests are
`eb3c482413d0feb7c7e43f29d55ca516ca4c7daa1571609d33f33902ee2a54ba`
and `21f1184e904104066f15ef7ee7103bac159511272f9a1f1d7228f4ebb1b63af0`.
The trained adapter, independent checkpoint custody and held-out L8-D
comparison remain open.
