"""Dry rebuild of arm A from the repo edit diff (vendored MIT apply_edit) into a temp copy under runs/.
Checks: base file sha256 vs the download manifest before AND after; edited tensor hashes vs the Hugging Face model card
hashes; every other tensor byte-identical to the base. Usage: t7_rebuild.py <base_dir> <edit_dir> <out.safetensors>"""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import numpy as np  # noqa: E402
import apply_edit  # noqa: E402
import st_numpy as S  # noqa: E402

CARD = {  # RikiyaT/Qwen3.5-0.8B-weight-space-programming model card, quoted in docs/reports/G3i-evidence.md
    "model.language_model.layers.15.mlp.down_proj.weight": "82e2d733ea64feaeb4af93a1e065641d3df98b494a8b7576ef2f52e90fe2ee53",
    "model.language_model.layers.19.mlp.down_proj.weight": "8ef3c61bc36af113ad58e89dbb0a4a14dcba5a45cb750c15ab515c82ddd12eb2",
}
BASE = "model.safetensors-00001-of-00001.safetensors"


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main(base_dir, edit_dir, out):
    with open(os.path.join(base_dir, "MANIFEST.sha256.json")) as f:
        want = json.load(f)["files"][BASE]["sha256"]
    bp = os.path.join(base_dir, BASE)
    assert sha(bp) == want, "base file differs from download manifest"
    apply_edit.main(bp, edit_dir, out)  # asserts per-tensor base_sha256 before and edited_sha256 after
    assert sha(bp) == want, "base file changed"
    a, b = S.load(bp), S.load(out)
    assert set(a) == set(b)
    diff = sorted(n for n in a if a[n][0] != b[n][0] or not np.array_equal(a[n][1], b[n][1]))
    assert diff == sorted(CARD), diff
    for n, h in CARD.items():
        assert hashlib.sha256(np.ascontiguousarray(b[n][1]).tobytes()).hexdigest() == h, n
    print(json.dumps({"base_sha256_unchanged": True, "tensors": len(a), "differing": diff, "card_hashes_match": True,
                      "edited_file_sha256": sha(out)}))


if __name__ == "__main__":
    main(*sys.argv[1:4])
