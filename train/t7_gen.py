"""T7 smoke generation, run INSIDE the container (torch + transformers). One batch = all given problems.
Sampling follows docs/reports/G9-repo-review.md (profiles think35 / nothink35); presence penalty is a custom
processor because transformers has none, and it also applies temperature/top-k/top-p so the order is the
vLLM one (penalty, temperature, top-k, top-p). Usage: t7_gen.py <arm 0|B> <model_dir> <out.jsonl> <cap> <smoke|main-timing-only>"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import t7_arms  # noqa: E402
import t7_samples  # noqa: E402
from vendor import mathqa_grade as G  # noqa: E402

PROFILES = {  # G9 section 4
    "0": dict(temperature=0.6, top_p=0.95, top_k=20, presence_penalty=1.5, thinking=True),
    "A": dict(temperature=0.6, top_p=0.95, top_k=20, presence_penalty=1.5, thinking=True),  # same as arm 0, edited weights
    "B": dict(temperature=0.7, top_p=0.8, top_k=20, presence_penalty=1.5, thinking=False),
}


def filtered_logits(logits, presence, seen, temperature, top_k, top_p):
    """logits [B,V] float; seen [B,V] bool of tokens already generated. Returns logits with -inf outside the nucleus."""
    import torch
    x = logits.float() - presence * seen
    x = x / temperature
    kth = torch.topk(x, top_k, dim=-1).values[:, -1:]
    x = x.masked_fill(x < kth, float("-inf"))
    sv, si = torch.sort(x, descending=True, dim=-1)
    cum = torch.softmax(sv, dim=-1).cumsum(-1)
    drop = (cum - torch.softmax(sv, dim=-1)) > top_p  # keep the first token that crosses top_p
    sv = sv.masked_fill(drop, float("-inf"))
    return torch.full_like(x, float("-inf")).scatter(-1, si, sv)


def main(arm, model_dir, out, cap, ids):
    import torch
    from transformers import (AutoModelForCausalLM, AutoTokenizer, LogitsProcessor, LogitsProcessorList, StoppingCriteria,
                              StoppingCriteriaList)
    prof = PROFILES[arm]
    rows = t7_samples.load_math500("/work/data/math500/test.jsonl")
    probs = [rows[i] for i in ids]
    tok = AutoTokenizer.from_pretrained(model_dir, padding_side="left")
    model = AutoModelForCausalLM.from_pretrained(model_dir, dtype=torch.bfloat16).cuda().eval()
    prompts = [tok.apply_chat_template([{"role": "user", "content": G.build_prompt(p["problem"])}], tokenize=False,
                                       add_generation_prompt=True, enable_thinking=prof["thinking"]) for p in probs]
    enc = tok(prompts, return_tensors="pt", padding=True).to("cuda")
    plen = enc["input_ids"].shape[1]

    class Sampler(LogitsProcessor):
        def __init__(self):
            self.seen = None

        def __call__(self, input_ids, scores):
            if self.seen is None:
                self.seen = torch.zeros(scores.shape, dtype=torch.bool, device=scores.device)
            if input_ids.shape[1] > plen:  # output tokens only, as vLLM's presence_penalty
                self.seen.scatter_(1, input_ids[:, -1:], True)
            return filtered_logits(scores, prof["presence_penalty"], self.seen, prof["temperature"], prof["top_k"],
                                   prof["top_p"])

    marks = []

    class Clock(StoppingCriteria):  # never stops; logs (output step, seconds) every 32 steps for step-time growth
        def __call__(self, input_ids, scores, **kw):
            k = input_ids.shape[1] - plen
            if k % 32 == 0:
                marks.append((k, time.time()))
                if k % 256 == 0:
                    print("MEM step", k, round(torch.cuda.memory_allocated() / 2**30, 2),
                          round(torch.cuda.memory_reserved() / 2**30, 2), flush=True)
            return torch.zeros(input_ids.shape[0], dtype=torch.bool, device=input_ids.device)

    torch.cuda.set_per_process_memory_fraction(0.2)  # unified memory: OOM here, not host starvation
    torch.manual_seed(0)
    torch.cuda.reset_peak_memory_stats()
    torch.cuda.synchronize()
    t0 = time.time()
    with torch.no_grad():
        gen = model.generate(**enc, do_sample=True, temperature=None, top_k=None, top_p=None, max_new_tokens=cap,
                             logits_processor=LogitsProcessorList([Sampler()]),
                             stopping_criteria=StoppingCriteriaList([Clock()]), pad_token_id=tok.pad_token_id)
    torch.cuda.synchronize()
    t1 = time.time()
    new = gen[:, plen:]
    eos = {tok.eos_token_id, tok.convert_tokens_to_ids("<|im_end|>")} - {None}
    total = 0
    if os.path.exists(out):
        os.remove(out)  # file is ours (runs/); a re-run overwrites
    for p, row in zip(probs, new.tolist()):
        n, finished = len(row), False
        for k, t in enumerate(row):
            if t in eos:
                n, finished = k + 1, True
                break
        total += n
        text = tok.decode(row[:n], skip_special_tokens=True)
        pred, nbox = G.extract(text)
        t7_arms.write_result(out, {"id": p["unique_id"], "arm": arm, "cap": cap, "seed": 0, "tokens": n,
                                   "finished": finished, "correct": G.is_correct(pred, p["answer"]), "pred": pred,
                                   "gold": p["answer"], "boxes": nbox, "text": text})
    meta = {"arm": arm, "n_problems": len(probs), "cap": cap, "prompt_tokens_padded": plen, "t_start": t0, "t_end": t1,
            "gen_seconds": t1 - t0, "tokens_generated": total, "steps": int(new.shape[1]),
            "tokens_per_s": total / (t1 - t0), "slot_tokens_per_s": new.numel() / (t1 - t0),
            "peak_cuda_mem_gib": torch.cuda.max_memory_allocated() / 2**30, "profile": prof, "step_marks": [(k, t - t0) for k, t in marks]}
    json.dump(meta, open(out + ".meta.json", "w"), indent=1)
    print(json.dumps(meta))


if __name__ == "__main__":
    arm, model_dir, out, cap, which = sys.argv[1:6]
    allrows = t7_samples.load_math500("/work/data/math500/test.jsonl")
    ids = t7_samples.main_ids(list(allrows)) if which == "main-timing-only" else t7_samples.smoke_ids(list(allrows))
    main(arm, model_dir, out, int(cap), ids)
