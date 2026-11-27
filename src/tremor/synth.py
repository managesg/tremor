"""Seeded synthetic transcript generator. ILLUSTRATION ONLY: its usage pattern is invented,
so results on it demonstrate the tool, not the world."""
import json
import random
from datetime import datetime, timedelta, timezone

TOOLS = [("Read", None), ("Edit", None), ("Grep", None), ("Bash", "git"), ("Bash", "pytest"),
         ("Bash", "npm"), ("Bash", "docker"), ("Bash", "curl"), ("Bash", "rm")]


def generate(seed=1, days=60, per_day=25):
    rng = random.Random(seed)
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    # each capability is active in a window (bursty use), curl and rm are sometimes denied
    window = {i: (rng.randrange(0, days - 5), rng.randrange(5, days)) for i in range(len(TOOLS))}
    lines, n = [], 0
    for d in range(days):
        for _ in range(per_day):
            live = [i for i in range(len(TOOLS)) if window[i][0] <= d <= window[i][0] + window[i][1] or i < 3]
            i = rng.choice(live)
            name, cmd = TOOLS[i]
            ts = (t0 + timedelta(days=d, seconds=rng.randrange(86000))).isoformat().replace("+00:00", "Z")
            n += 1
            tid = f"t{n}"
            inp = {"command": f"{cmd} x"} if name == "Bash" else {"file_path": "/x"}
            denied = cmd in ("curl", "rm") and rng.random() < 0.4
            lines.append({"sessionId": f"s{d // 3}", "timestamp": ts,
                          "message": {"content": [{"type": "tool_use", "id": tid, "name": name, "input": inp}]}})
            res = ("Permission to use Bash with command x has been denied." if denied else "ok")
            lines.append({"sessionId": f"s{d // 3}", "timestamp": ts,
                          "message": {"content": [{"type": "tool_result", "tool_use_id": tid,
                                                   "content": res, "is_error": denied}]}})
    return "\n".join(json.dumps(x, sort_keys=True) for x in lines) + "\n"
