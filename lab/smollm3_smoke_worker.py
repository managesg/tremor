"""Bounded local public-prompt worker. The caller owns admission and settlement."""

import argparse
import hashlib
import json
from pathlib import Path
import re
from time import monotonic_ns

from lab.spark_causal_decision import load_smollm3


SCHEMA = "tremor.smollm3_smoke.v1"
MODEL = "HuggingFaceTB/SmolLM3-3B"
REVISION = "a07cc9a04f16550a088caea529712d1d335b0ac1"
PROMPT_SHA256 = "df98aea726ee4667af1040eb778401ec3aeef67130a3c42f54599d4ab3899411"
INPUT_IDS_SHA256 = "53883937f025778218df4c2c7f2e5b786aa6f16c514a1004605e098a920d77f9"
INPUT_TOKENS = 73
MAX_OUTPUT_TOKENS = 2
PLAN_FIELDS = {
    "schema", "manifest_sha256", "device", "prompt_sha256", "input_ids_sha256",
    "input_tokens", "max_output_tokens", "cuda_allocator_fraction",
}
RUNTIME_METADATA = {
    "chat_template.jinja", "config.json", "generation_config.json", "model.safetensors.index.json",
    "special_tokens_map.json", "tokenizer.json", "tokenizer_config.json",
}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _object(pairs):
    value = dict(pairs)
    _require(len(value) == len(pairs), "duplicate JSON field")
    return value


def _sha256(value):
    _require(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None,
             "expected lowercase SHA-256")
    return value


def _pinned_object(path, digest):
    with path.open("rb") as stream:
        raw = stream.read(65537)
    _require(len(raw) <= 65536 and hashlib.sha256(raw).hexdigest() == _sha256(digest),
             f"digest mismatch or oversized JSON: {path.name}")
    result = json.loads(raw, object_pairs_hook=_object)
    _require(type(result) is dict, f"expected JSON object: {path.name}")
    return result


def _verify_metadata(snapshot, manifest_sha):
    manifest = _pinned_object(snapshot / "MANIFEST.sha256.json", manifest_sha)
    _require((manifest.get("model"), manifest.get("revision")) == (MODEL, REVISION),
             "snapshot identity differs from the public smoke checkpoint")
    pending = RUNTIME_METADATA.copy()
    for row in manifest["files"]:
        name = row["path"]
        if name not in RUNTIME_METADATA:
            continue
        _require(name in pending, f"duplicate manifest file: {name}")
        path = snapshot / name
        _require(not path.is_symlink() and path.is_file() and path.stat().st_size == row["bytes"],
                 f"metadata is missing, linked, or has changed size: {name}")
        with path.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        _require(actual == _sha256(row["sha256"]), f"metadata digest mismatch: {name}")
        pending.remove(name)
    _require(not pending, "manifest omits required runtime metadata")


def _render(snapshot):
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(
        snapshot, local_files_only=True, trust_remote_code=False,
    )
    prompt = tokenizer.apply_chat_template(
        [{"role": "user", "content": "Return exactly [1]."}], tokenize=False,
        enable_thinking=False, add_generation_prompt=True,
    )
    return prompt, tokenizer(prompt, add_special_tokens=False, truncation=False).input_ids


def _configure_device(fraction):
    import torch

    torch.cuda.set_per_process_memory_fraction(fraction, device=0)
    torch.cuda.reset_peak_memory_stats(device=0)


def _device_peaks():
    import torch

    return torch.cuda.max_memory_allocated(device=0), torch.cuda.max_memory_reserved(device=0)


def run(snapshot, plan, *, plan_sha256):
    """Execute one prompt on a pinned mount under caller-owned GPU controls.

    The launcher must verify full shard hashes and prevent mount changes. It
    also owns CUDA authorization, the host watchdog, and the resource ledger.
    """
    spec = _pinned_object(Path(plan), plan_sha256)
    _require(set(spec) == PLAN_FIELDS and spec["schema"] == SCHEMA, "unexpected smoke plan schema")
    _require(spec["prompt_sha256"] == PROMPT_SHA256 and type(spec["input_tokens"]) is int
             and spec["input_tokens"] == INPUT_TOKENS and type(spec["max_output_tokens"]) is int
             and spec["max_output_tokens"] == MAX_OUTPUT_TOKENS, "unexpected public prompt or token limits")
    _require(spec["input_ids_sha256"] == INPUT_IDS_SHA256, "expected canonical public prompt token pin")
    device, fraction = spec["device"], spec["cuda_allocator_fraction"]
    _require(
        (device == "cpu" and fraction is None)
        or (device == "cuda:0" and type(fraction) in (int, float) and 0 < fraction <= 0.2),
        "expected CPU with no allocator fraction or cuda:0 with a bounded fraction",
    )
    snapshot = Path(snapshot).resolve(strict=True)
    _verify_metadata(snapshot, spec["manifest_sha256"])
    prompt, ids = _render(snapshot)
    _require(hashlib.sha256(prompt.encode("utf-8")).hexdigest() == PROMPT_SHA256,
             "public prompt rendering differs from the pinned bytes")
    _require(type(ids) is list and len(ids) == INPUT_TOKENS
             and all(type(token) is int and token >= 0 for token in ids), "unexpected public prompt token IDs")
    ids_sha = hashlib.sha256(json.dumps(ids, separators=(",", ":")).encode("ascii")).hexdigest()
    _require(ids_sha == INPUT_IDS_SHA256, "public prompt token IDs differ from the pinned sequence")
    if device == "cuda:0":
        _configure_device(fraction)
    started = monotonic_ns()
    generate = load_smollm3(snapshot, device=device)
    load_ns = monotonic_ns() - started
    result = generate(prompt, max_input_tokens=INPUT_TOKENS, max_output_tokens=MAX_OUTPUT_TOKENS)
    _require(result.input_tokens == INPUT_TOKENS and type(result.output_tokens) is int
             and 0 < result.output_tokens <= MAX_OUTPUT_TOKENS
             and type(result.generation_ns) is int and result.generation_ns >= 0
             and result.reached_output_limit is (result.output_tokens == MAX_OUTPUT_TOKENS),
             "generation receipt differs from the bounded token contract")
    allocated = reserved = None
    if device == "cuda:0":
        allocated, reserved = _device_peaks()
        _require(type(allocated) is int and type(reserved) is int and 0 <= allocated <= reserved,
                 "invalid worker CUDA peak memory counters")
    return {
        "evidence": "local_public_prompt_smoke_worker",
        "plan_sha256": plan_sha256,
        "manifest_sha256": spec["manifest_sha256"],
        "prompt_sha256": PROMPT_SHA256,
        "input_ids_sha256": ids_sha,
        "device": device,
        "cuda_allocator_fraction": fraction,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "cap_reached": result.reached_output_limit,
        "load_ns": load_ns,
        "generation_ns": result.generation_ns,
        "peak_cuda_allocated_bytes": allocated,
        "peak_cuda_reserved_bytes": reserved,
        "authorizes_execution": False,
        "scientific_acceptance": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--plan-sha256", required=True)
    args = parser.parse_args()
    print(json.dumps(run(**vars(args)), sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
