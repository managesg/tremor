"""Load pinned standalone checkpoints on CPU and record an actual fixture hook."""

import argparse
import hashlib
import json
from pathlib import Path

from lab import adapter_lineage


def _fingerprints(state):
    import torch

    tensors = {}
    for name, tensor in state.items():
        if not isinstance(tensor, torch.Tensor) or tensor.device.type != "cpu" or tensor.layout != torch.strided:
            raise ValueError("checkpoint witness requires dense CPU tensors")
        raw = tensor.detach().contiguous().reshape(-1).view(torch.uint8)
        tensors[name] = {"dtype": str(tensor.dtype), "shape": list(tensor.shape),
                         "sha256": hashlib.sha256(memoryview(raw.numpy())).hexdigest()}
    return tensors


def _load_verified_cpu(module, bundle, reference, *, max_bytes):
    """Load a fresh fixture module. The caller must discard it if verification fails."""
    import torch
    from safetensors import SafetensorError
    from safetensors.torch import load

    path = adapter_lineage._path(Path(bundle).resolve(strict=True), reference)
    digest = reference["sha256"]
    content = adapter_lineage._checked_safetensors_bytes(path, expected=digest, max_bytes=max_bytes)
    try:
        state = load(content)
    except SafetensorError as error:
        raise ValueError(f"checkpoint decoder refused {path.name}") from error
    expected = _fingerprints(state)
    target = module.state_dict()
    if (not expected or set(expected) != set(target)
            or any(not isinstance(tensor, torch.Tensor) or tensor.device.type != "cpu"
                   or tensor.layout != torch.strided
                   or (str(tensor.dtype), list(tensor.shape)) != (expected[name]["dtype"], expected[name]["shape"])
                   for name, tensor in target.items())):
        raise ValueError("checkpoint and target module tensor inventory, dtype or shape differ")
    module.load_state_dict(state, strict=True, assign=False)
    installed = _fingerprints(module.state_dict())
    if installed != expected:
        raise ValueError("installed module state differs from the verified checkpoint")
    return {"checkpoint_sha256": digest, "checkpoint_bytes": len(content), "installed_tensors": installed}


def replay_fixture(bundle, plan, *, plan_sha256, max_bytes):
    """Load the frozen synthetic pair and observe its real linear-module hook."""
    import torch

    manifest = adapter_lineage._json(plan, plan_sha256)
    lineage = adapter_lineage.verify_tensor_change(bundle, manifest, max_bytes=max_bytes)
    input_tensor = torch.tensor([[2.0, 1.0]], dtype=torch.float32, device="cpu")
    rows = []
    for stage in ("before", "after"):
        model = torch.nn.Linear(2, 1, bias=False, dtype=torch.float32, device="cpu").eval()
        loaded = _load_verified_cpu(model, bundle, manifest["checkpoints"][stage], max_bytes=max_bytes)
        hook = []

        def observe(_module, _args, output):
            hook.append((output.detach().tolist(), _fingerprints({"hook": output})["hook"]))

        handle = model.register_forward_hook(observe)
        try:
            with torch.inference_mode():
                result = model(input_tensor).tolist()
        finally:
            handle.remove()
        if len(hook) != 1 or hook[0][0] != result:
            raise ValueError("fixture hook did not observe the loaded module output")
        rows.append({"stage": stage, **loaded, "hook_output": hook[0][0], "hook_tensor": hook[0][1]})
    return {"evidence": "scripted_cpu_loader", "plan_sha256": plan_sha256, "lineage": lineage,
            "loader": {"device": "cpu", "torch_version": str(torch.__version__), "strict": True},
            "hook": "linear.forward", "fixture_input": input_tensor.tolist(),
            "fixture_input_tensor": _fingerprints({"input": input_tensor})["input"], "stages": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--max-bytes", type=int, required=True)
    args = parser.parse_args()
    try:
        result = replay_fixture(args.bundle, args.plan, plan_sha256=args.plan_sha256, max_bytes=args.max_bytes)
    except (ImportError, KeyError, OSError, RuntimeError, TypeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
