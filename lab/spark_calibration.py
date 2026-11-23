"""Small Qwen3.5-4B calibration workload for Spark's separately gated R2 smoke."""

import json
import time

PROMPTS = ("Return only the JSON array [1].", "Name one property of a square.")
TOKENS = 32
LAYERS = (0, 31)


def main():
    import torch
    from transformers import AutoModelForImageTextToText, AutoTokenizer

    started = time.monotonic()
    torch.cuda.set_per_process_memory_fraction(0.2, device=0)
    tokenizer = AutoTokenizer.from_pretrained("/model", local_files_only=True)
    model = AutoModelForImageTextToText.from_pretrained(
        "/model", local_files_only=True, dtype=torch.bfloat16
    ).to("cuda:0").eval()
    torch.cuda.synchronize()
    load_seconds = time.monotonic() - started
    layers = model.model.language_model.layers
    results = []
    for prompt in PROMPTS:
        inputs = tokenizer(prompt, return_tensors="pt").to("cuda:0")
        hook_shapes = {}

        def shape_hook(index):
            def capture(_module, _args, output):
                if index not in hook_shapes:
                    hidden = output[0] if isinstance(output, tuple) else output
                    hook_shapes[index] = list(hidden.shape)
            return capture

        handles = [layers[index].register_forward_hook(shape_hook(index)) for index in LAYERS]
        try:
            begin = time.monotonic()
            with torch.inference_mode():
                output = model.generate(**inputs, do_sample=False, max_new_tokens=TOKENS)
            torch.cuda.synchronize()
            elapsed = time.monotonic() - begin
        finally:
            for handle in handles:
                handle.remove()
        count = output.shape[-1] - inputs.input_ids.shape[-1]
        if not 0 < count <= TOKENS or set(hook_shapes) != set(LAYERS):
            raise RuntimeError("generation or activation hook outside the calibration contract")
        results.append({
            "input_tokens": inputs.input_ids.shape[-1],
            "generated_tokens": count,
            "seconds": elapsed,
            "tokens_per_second": count / elapsed,
            "first_hook_shapes": hook_shapes,
        })
    print(json.dumps({
        "load_seconds": load_seconds,
        "peak_cuda_reserved_bytes": torch.cuda.max_memory_reserved(),
        "results": results,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
