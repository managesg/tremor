"""Download a pinned HF repo revision (stdlib only) and verify LFS sha256 against the HF API. Usage: fetch.py <repo> <rev> <outdir>"""
import hashlib, json, os, sys, urllib.request

def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "murmuration-fetch"}))

def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def main(repo, rev, out):
    info = json.load(get("https://huggingface.co/api/models/%s/revision/%s?blobs=true" % (repo, rev)))
    assert info["sha"] == rev, info["sha"]
    man = {}
    for s in info["siblings"]:
        n, dst = s["rfilename"], os.path.join(out, s["rfilename"])
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with get("https://huggingface.co/%s/resolve/%s/%s" % (repo, rev, n)) as r, open(dst, "wb") as f:
            while b := r.read(1 << 20):
                f.write(b)
        assert os.path.getsize(dst) == s["size"], n
        got, lfs = sha256(dst), (s.get("lfs") or {}).get("sha256")
        man[n] = {"size": s["size"], "sha256": got, "hf_lfs_sha256": lfs, "lfs_match": None if lfs is None else got == lfs}
        print(n, s["size"], man[n]["lfs_match"], flush=True)
    json.dump({"repo": repo, "revision": rev, "files": man}, open(os.path.join(out, "MANIFEST.sha256.json"), "w"), indent=1, sort_keys=True)

if __name__ == "__main__":
    main(*sys.argv[1:4])
