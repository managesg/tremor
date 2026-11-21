"""Summarise runs/t7-smoke arm files: accuracy at 2k/8k/cap, finished share, timing, energy, projection inputs."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t7_arms  # noqa: E402

D = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "runs", "t7-smoke")
for arm in ("0", "A", "B"):
    r = t7_arms.read_results(os.path.join(D, "arm%s.jsonl" % arm))
    s = json.load(open(os.path.join(D, "arm%s.summary.json" % arm)))
    e, k = s["energy"], s["step_marks"]
    # Gross and net energy encode the idle baseline for this arm.
    idle_w = (e["joules_gpu"] - e["joules_gpu_net"]) / e["seconds"]
    toks = sorted(x["tokens"] for x in r)
    mid = [m for m in k if m[0] >= 64]
    print(json.dumps({
        "arm": arm, "n": len(r), "acc_2k": t7_arms.accuracy_at_cap(r, 2048), "acc_8k": t7_arms.accuracy_at_cap(r, 8192),
        "finished": sum(x["finished"] for x in r), "no_box": sum(x["pred"] is None for x in r),
        "tokens_median": toks[len(toks) // 2], "tokens_max": toks[-1], "tokens_total": s["tokens_generated"],
        "gen_s": round(s["gen_seconds"], 1), "tok_s": round(s["tokens_per_s"], 1), "steps": s["steps"],
        "s_per_step_first_1k": round((k[32][1] - k[2][1]) / (k[32][0] - k[2][0]), 3),
        "s_per_step_last_1k": round((k[-1][1] - k[-33][1]) / (k[-1][0] - k[-33][0]), 3),
        "J_gross": round(e["joules_gpu"]), "J_net": round(e["joules_gpu_net"]), "J_per_tok": round(s["joules_per_token"], 4),
        "mean_W": round(e["joules_gpu"] / e["seconds"], 2), "idle_fraction": e["idle_fraction"],
        "idle_W": round(idle_w, 2), "peak_cuda_gib": round(s["peak_cuda_mem_gib"], 2)}))
