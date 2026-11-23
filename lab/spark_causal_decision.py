"""Standalone local SmolLM3 adapter for pre-rendered experiment prompts."""

from pathlib import Path

from lab.spark_decision import make_generator


class _RenderedPromptTokenizer:
    def __init__(self, tokenizer):
        self._tokenizer = tokenizer

    def __call__(self, prompt, **options):
        # The chat renderer already inserts special tokens.
        return self._tokenizer(prompt, add_special_tokens=False, **options)

    def decode(self, ids, **options):
        return self._tokenizer.decode(ids, **options)


def load_smollm3(model_dir, *, device="cpu"):
    """Load an exact local candidate selected and admitted by the caller."""
    directory = Path(model_dir).resolve(strict=True)
    if not directory.is_dir():
        raise ValueError("model mount must be a directory")

    import torch
    from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer

    target = torch.device(device)
    if target.type not in ("cpu", "cuda") or (target.type == "cuda" and target.index is None):
        raise ValueError("device must be CPU or an explicitly indexed CUDA device")

    local = {"local_files_only": True, "trust_remote_code": False}
    config = AutoConfig.from_pretrained(str(directory), **local)
    if config.model_type != "smollm3":
        raise ValueError("expected a local SmolLM3 checkpoint")
    tokenizer = AutoTokenizer.from_pretrained(str(directory), **local)
    model = AutoModelForCausalLM.from_pretrained(
        str(directory), config=config, use_safetensors=True,
        dtype=torch.float32 if target.type == "cpu" else torch.bfloat16, **local,
    ).to(target).eval()

    def synchronize():
        if target.type == "cuda":
            torch.cuda.synchronize(target)

    return make_generator(
        _RenderedPromptTokenizer(tokenizer), model, device=target,
        inference_mode=torch.inference_mode, synchronize=synchronize,
    )
