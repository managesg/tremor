# SmolLM3 candidate for second-family replication

The staged Spark checkpoints are both Qwen3.5. SmolLM3-3B is a concrete
candidate for the second family. The publisher documents an Apache 2.0
text-only decoder with a distinct architecture and a separate pretraining and
post-training recipe. The prospective family reviewer still has to accept the
definition and checkpoint for the comparison. [Model card](https://huggingface.co/HuggingFaceTB/SmolLM3-3B) ·
[Training report](https://huggingface.co/blog/smollm3)

## Metadata preflight on Spark

Pulled public metadata and tokenizer files only from revision
`a07cc9a04f16550a088caea529712d1d335b0ac1` and retained them under
`runs/replication-smollm3-metadata.8eLSUV`. The publisher's shard index
declares 6,150,197,248 bytes of tensor data in two Safetensors shards.
That total describes the serialized tensors. Spark memory and elapsed
time for inference still need measurement. [Pinned publisher tree](https://huggingface.co/HuggingFaceTB/SmolLM3-3B/tree/a07cc9a04f16550a088caea529712d1d335b0ac1)

The existing ARM64 CPU image with Transformers 5.2.0 resolved
`AutoModelForCausalLM` to `SmolLM3ForCausalLM`, loaded the exact local
tokenizer and rendered a public test prompt with networking disabled and
CUDA unavailable. No weight shard was present or loaded. The same sample
rendered to 73 input tokens with thinking disabled and 253 with thinking
enabled. Even a flag change affects the input meter. The publisher's
system-message flags can override the renderer argument, so the real
L1–L3 system templates have to be checked and pinned. [Publisher renderer instructions](https://huggingface.co/HuggingFaceTB/SmolLM3-3B#enabling-and-disabling-extended-thinking-mode)

| Receipt | SHA-256 |
| --- | --- |
| `metadata.sha256` | `7321f61c070ab76b128a9740f3e9aeb45fc030d75ce57e54b449b9c36889eaed` |
| `receipt.json` | `6c09d6fb0e72d9f27cf39c7c358e9f29ff6a0b38767c2327a65ca031cfb61fcd` |

## Staged checkpoint and CPU generation

The immutable publisher pointers identify two shards with exact sizes
4,966,315,264 and 1,183,919,744 bytes. Both staged files matched the
publisher's SHA-256 and size. The snapshot in
`runs/replication-smollm3-staging.out5A0/SmolLM3-3B` has ten data files,
6,167,546,549 bytes, and manifest SHA-256
`6ff79f0d818a19b9e36f64c7bae12558d099889eae5b368038133a4906df9d7f`.
[Pinned publisher tree](https://huggingface.co/HuggingFaceTB/SmolLM3-3B/tree/a07cc9a04f16550a088caea529712d1d335b0ac1)

The same CPU image then loaded the full verified checkpoint and ran the
local deterministic causal adapter on the public 73-token prompt. It
returned two output tokens at the selected cap. The test used one CPU,
a 16 GiB container memory limit, read-only mounts, a 120-second timeout,
disabled networking and no GPU. Its receipt SHA-256 is
`480c9e0fa557865e44efe48eb4422cae84038cccdd90163b108661450be55129`.
This checks the actual CPU load and token accounting only. It provides
no measured CUDA fit and no evidence on protected L1–L3 tasks.

The separate adapter and shared generator are pinned in the run bundle.
The shared generator remains untracked in the main checkout and needs an
assigned owner for Git packaging.

## What the replication lane needs next

1. The family reviewer records the exact candidate and comparison scope before
   any holdout work. The two Qwen sizes remain within the reference family.
2. The loader owner binds the pinned separate causal loader and verified
   shard bytes to the native recipe. Preserve the existing Qwen path.
   Match actual encoded IDs to the pinned template and account for special
   tokens, thinking flags, cache configuration, stop IDs and output limits.
   The published generation configuration enables sampling, so set
   deterministic generation explicitly for the matched smoke.
3. Run the admitted smoke on CUDA to measure bounded generation, host memory
   and cleanup timings under the Spark serving constraints.
4. Run the already registered paired L1–L3 replication after eligible
   allocation and protected-split custody, keeping unchanged transfer and
   separate recalibration visible in the analysis.

[Replication design](Second-model-replication-design.md) ·
[Shared Spark allocation envelope](Spark-allocation-rephase.md)
