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
