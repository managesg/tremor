"""WSP-R1: blind cross-model replication of "Sparks of Weight-Space Programming" Experiment 1.

build: write the 4 released prompts and 4 shuffled controls (values permuted within each tensor,
fixed seed) under neutral names, plus a sealed key. score: grade answers by a fixed keyword map.
Pure stdlib; no network, model or GPU. Preregistration: prereg/WSP-R1-exp1-blind-read.md.
"""
import argparse, hashlib, json, random, re, sys
from pathlib import Path

LOGS = Path("data/lm_understand-logs/exp1_which_game")
GAMES = {"breakout": "a9f535cc", "pong": "dfc6cb65", "pacman": "bdf99279", "freeway": "0bbcc3ea"}
MARK = "THE NETWORK'S WEIGHTS\n"
SEED = 20261124
# First matching game wins in this order; a Game: line matching two games scores as ambiguous (wrong).
KEYWORDS = {
    "breakout": ("breakout", "arkanoid", "brick"),
    "pong": ("pong",),
    "pacman": ("pac-man", "pacman", "pac man", "ms. pac"),
    "freeway": ("freeway", "frogger", "road-crossing", "road crossing", "traffic-crossing", "traffic crossing",
                "crossing the road", "cross the road", "chicken"),
}
NUM = re.compile(r"-?\d+\.\d+")


def shuffle_block(block, rng):
    """Permute values within each tensor section; keep headers, line shapes and formatting."""
    out, section = [], []

    def flush():
        values = [v for line in section for v in NUM.findall(line)]
        rng.shuffle(values)
        it = iter(values)
        for line in section:
            out.append(NUM.sub(lambda _: next(it), line))
        section.clear()

    for line in block.split("\n"):
        if line and (line[0] == "-" or line[0].isdigit()):
            section.append(line)
        else:
            flush()
            out.append(line)
    flush()
    return "\n".join(out)


def build(out):
    rng = random.Random(SEED)
    out.mkdir(parents=True, exist_ok=False)
    arms = []
    for game, net in GAMES.items():
        prompt = (LOGS / "runs" / game / "prompt.txt").read_text()
        head, block = prompt.split(MARK, 1)
        assert block == (LOGS / "networks" / f"{net}_actor.txt").read_text(), game
        control = shuffle_block(block, rng)
        assert sorted(NUM.findall(control)) == sorted(NUM.findall(block)) and control != block, game
        arms += [(game, "real", head + MARK + block), (game, "shuffled", head + MARK + control)]
    rng.shuffle(arms)
    key = {}
    for i, (game, arm, text) in enumerate(arms, 1):
        name = f"item{i}"
        (out / f"{name}.txt").write_text(text)
        key[name] = {"game": game, "arm": arm, "sha256": hashlib.sha256(text.encode()).hexdigest()}
    (out / "sealed-key.json").write_text(json.dumps(key, indent=1, sort_keys=True))
    print(json.dumps({k: v["sha256"] for k, v in key.items()}, indent=1))


def game_of(answer):
    lines = [l for l in answer.splitlines() if l.strip().lower().lstrip("*# ").startswith("game")]
    if not lines:
        return None
    text = lines[0].lower()
    hits = [g for g, words in KEYWORDS.items() if any(w in text for w in words)]
    return hits[0] if len(hits) == 1 else ("ambiguous" if hits else "other")


def score(out):
    key = json.loads((out / "sealed-key.json").read_text())
    rows = []
    for name, k in sorted(key.items()):
        path = out / f"{name}.answer.md"
        guess = game_of(path.read_text()) if path.exists() else "missing"
        rows.append({"item": name, **{x: k[x] for x in ("game", "arm")}, "guess": guess, "correct": guess == k["game"]})
    for arm in ("real", "shuffled"):
        sel = [r for r in rows if r["arm"] == arm]
        print(f"{arm}: {sum(r['correct'] for r in sel)}/{len(sel)} correct")
    (out / "scores.json").write_text(json.dumps(rows, indent=1))
    return rows


def _self_check():
    assert game_of("Game: Breakout (Atari)") == "breakout"
    assert game_of("**Game:** Frogger-style road crossing") == "freeway"
    assert game_of("Game: Pac-Man like maze") == "pacman"
    assert game_of("Game: Pong or Breakout") == "ambiguous"
    assert game_of("Game: Snake") == "other" and game_of("no answer") is None
    rng = random.Random(1)
    b = "W1 x\n0.100 -0.200\n0.300 0.400\nb1 y\n1.000"
    s = shuffle_block(b, rng)
    assert s.split("\n")[0] == "W1 x" and s.split("\n")[3] == "b1 y" and s.split("\n")[4] == "1.000"
    assert sorted(NUM.findall(s)) == sorted(NUM.findall(b))


if __name__ == "__main__":
    _self_check()
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=("build", "score", "check"))
    p.add_argument("--out", type=Path)
    a = p.parse_args()
    if a.action == "build":
        build(a.out)
    elif a.action == "score":
        score(a.out)
    else:
        print("self-check OK")
