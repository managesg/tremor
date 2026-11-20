"""Host-side T7 runner: idle power record, or one arm in the container with 1 Hz nvidia-smi sampling, a MemAvailable
watchdog (kills the container below 10 GiB) and energy via power.py.
  t7_host.py idle <seconds>
  t7_host.py run <arm> <cap> <smoke|N> [tag]"""
import json
import os
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import power  # noqa: E402

ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "runs", "t7-smoke")
SMI = ["nvidia-smi", "--query-gpu=timestamp,power.draw,utilization.gpu", "--format=csv,noheader,nounits", "-lms", "1000"]
MIN_AVAIL_KIB = 10 * 2**20


def mem_available_kib():
    with open("/proc/meminfo") as f:
        return next(int(l.split()[1]) for l in f if l.startswith("MemAvailable"))


class Smi:
    def __enter__(self, path=None):
        self.f = open(self.path, "w")
        self.p = subprocess.Popen(SMI, stdout=self.f)
        return self

    def __exit__(self, *a):
        self.p.terminate()
        self.p.wait()
        self.f.close()

    def __init__(self, path):
        self.path = path


def summarize(csv_path, t0=None, t1=None, baseline_w=None):
    s = power.parse_csv(open(csv_path).read())
    if t0 is not None:
        s = [x for x in s if t0 <= x[0] <= t1]
    return power.sample(s, baseline_w)


def idle(seconds):
    os.makedirs(OUT, exist_ok=True)
    with Smi(os.path.join(OUT, "idle.csv")):
        time.sleep(seconds)
    r = summarize(os.path.join(OUT, "idle.csv"))
    r["mean_w"] = power.baseline_watts(power.parse_csv(open(os.path.join(OUT, "idle.csv")).read()))
    json.dump(r, open(os.path.join(OUT, "idle.json"), "w"), indent=1)
    print(json.dumps(r))


def run(arm, cap, which, tag=None):
    tag = tag or "arm" + arm
    name = "murm-t7-" + tag
    os.makedirs(OUT, exist_ok=True)
    out_in = "/work/runs/t7-smoke/%s.jsonl" % tag
    cmd = ["docker", "run", "--rm", "--name", name, "--gpus", "all", "--memory", "60g", "--network", "none",
           "--user", "%d:%d" % (os.getuid(), os.getgid()), "-e", "HOME=/tmp", "-e", "HF_HUB_OFFLINE=1",
           "-e", "PYTHONDONTWRITEBYTECODE=1",
           "-e", "PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True", "-w", "/work",
           "-v", ROOT + "/train:/work/train:ro", "-v", ROOT + "/src:/work/src:ro", "-v", ROOT + "/tests:/work/tests:ro",
           "-v", ROOT + "/data:/work/data", "-v", ROOT + "/data/hf:/work/data/hf:ro", "-v", ROOT + "/runs:/work/runs",
           "murmuration-t7:1", "python", "-B", "train/t7_gen.py", arm, "/work/runs/t7-smoke/armA" if arm == "A" else "/work/data/hf/Qwen3.5-0.8B", out_in, str(cap),
           str(which)]
    killed = []
    stop = threading.Event()

    def watch():
        while not stop.wait(5):
            if mem_available_kib() < MIN_AVAIL_KIB:
                killed.append(mem_available_kib())
                subprocess.run(["docker", "kill", name])
                return

    if mem_available_kib() < MIN_AVAIL_KIB:
        sys.exit("MemAvailable below 10 GiB: not starting")
    th = threading.Thread(target=watch, daemon=True)
    th.start()
    csv = os.path.join(OUT, tag + ".power.csv")
    with Smi(csv):
        rc = subprocess.run(cmd, stdout=open(os.path.join(OUT, tag + ".log"), "w"), stderr=subprocess.STDOUT).returncode
    stop.set()
    if killed or rc:
        sys.exit("run failed rc=%s watchdog_kill_MemAvailable_kib=%s (see %s.log)" % (rc, killed, tag))
    meta = json.load(open(os.path.join(OUT, tag + ".jsonl.meta.json")))
    idle_w = json.load(open(os.path.join(OUT, "idle.json")))["mean_w"] if os.path.exists(os.path.join(OUT, "idle.json")) else None
    e = summarize(csv, meta["t_start"], meta["t_end"], idle_w)
    meta["energy"] = e
    meta["joules_per_token"] = e["joules_gpu"] / meta["tokens_generated"]
    json.dump(meta, open(os.path.join(OUT, tag + ".summary.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in meta.items() if k not in ("profile", "step_marks", "energy")}))


if __name__ == "__main__":
    a = sys.argv[1:]
    idle(float(a[1])) if a[0] == "idle" else run(a[1], int(a[2]), a[3], a[4] if len(a) > 4 else None)
