# G2a: NVIDIA PyTorch container (2026-11-19)

- Image: `nvcr.io/nvidia/pytorch:25.11-py3`, pulled once. Size 19.5 GB, arm64/linux, local image id
  eea3fe49e8a5, repo digest `sha256:417cbf33f87b5378849df37983552cd1f8bc8b62fe1ceabe004de816a55dff21`.
- Preflight (before pull): manifest lists amd64 and arm64; host aarch64; disk 2.7 TB free; MemAvailable
  about 77 GiB.
- Smoke (single `docker run --rm --gpus all --network none --memory 16g`, no model, no weights):
  torch 2.10.0a0 (nv25.11), `torch.cuda.is_available()` True, device NVIDIA GB10.
- Not installed in the image: `transformers`, `accelerate`, `peft`. Approved derived-image step adds
  ONLY a pinned `transformers` (version to be chosen from the Qwen3.5 model card requirement; nothing
  else, no vLLM, no Unsloth, no math-verify without an owner ask).
- Notice from the container: SHMEM limit is 64 MB by default; use `--ipc=host` only if a job needs it
  (not needed for the smoke). Governing terms: NVIDIA Software License Agreement (not reviewed in full).
- Rollback: `docker rmi nvcr.io/nvidia/pytorch:25.11-py3` (owner runs; nothing else depends on it).
