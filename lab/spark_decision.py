"""Local model generation adapter for a separately admitted Spark runner."""

from dataclasses import dataclass
from pathlib import Path
from time import monotonic_ns


@dataclass(frozen=True)
class Generation:
    text: str
    input_tokens: int
    output_tokens: int
    generation_ns: int
    reached_output_limit: bool


def _token_ids(row):
    ids = row.tolist()
    if any(type(value) is not int or value < 0 for value in ids):
        raise ValueError("token IDs must be nonnegative integers")
    return ids


def make_generator(tokenizer, model, *, device, inference_mode, synchronize):
    """Renderings and limits are supplied by the protocol that calls the adapter."""
    def generate(prompt, *, max_input_tokens, max_output_tokens):
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must be nonempty rendered text")
        if any(type(limit) is not int or limit < 1 for limit in (max_input_tokens, max_output_tokens)):
            raise ValueError("input and output token limits must be positive integers")

        encoded = tokenizer(prompt, return_tensors="pt", truncation=False)
        batch, input_count = encoded.input_ids.shape
        if batch != 1 or not 0 < input_count <= max_input_tokens:
            raise ValueError("encoded prompt exceeds the single-input token contract")
        prompt_ids = _token_ids(encoded.input_ids[0])
        encoded = encoded.to(device)
        synchronize()
        begin = monotonic_ns()
        with inference_mode():
            output = model.generate(**encoded, do_sample=False, num_beams=1, num_return_sequences=1,
                                    return_dict_in_generate=False, max_new_tokens=max_output_tokens)
        synchronize()
        elapsed = monotonic_ns() - begin

        if len(output.shape) != 2 or output.shape[0] != 1:
            raise ValueError("expected one generated sequence")
        output_count = output.shape[1] - input_count
        if not 0 < output_count <= max_output_tokens:
            raise ValueError("generated sequence exceeds the output token contract")
        observed_ids = _token_ids(output[0])
        if observed_ids[:input_count] != prompt_ids:
            raise ValueError("generated sequence lost its prompt prefix")
        text = tokenizer.decode(observed_ids[input_count:], skip_special_tokens=True,
                                clean_up_tokenization_spaces=False)
        if not isinstance(text, str):
            raise ValueError("decoder must return text")
        return Generation(text, input_count, output_count, elapsed, output_count == max_output_tokens)

    return generate


def load_qwen(model_dir):
    """Load the mounted Qwen checkpoint inside an admitted local container."""
    directory = Path(model_dir).resolve(strict=True)
    if not directory.is_dir():
        raise ValueError("model mount must be a directory")

    import torch
    from transformers import AutoModelForImageTextToText, AutoTokenizer

    device = "cuda:0"
    torch.cuda.set_per_process_memory_fraction(0.2, device=0)
    tokenizer = AutoTokenizer.from_pretrained(str(directory), local_files_only=True, trust_remote_code=False)
    model = AutoModelForImageTextToText.from_pretrained(
        str(directory), local_files_only=True, trust_remote_code=False, use_safetensors=True, dtype=torch.bfloat16,
    ).to(device).eval()
    return make_generator(tokenizer, model, device=device, inference_mode=torch.inference_mode,
                          synchronize=torch.cuda.synchronize)
