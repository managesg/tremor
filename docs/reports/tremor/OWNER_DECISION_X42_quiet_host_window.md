# Owner decision packet: X42 quiet-host windows for candidate d918428

**One question for Alejandro and PC:** may the three quiet-machine windows that Gate R1 asks for ("full suite green three times on a quiet machine") be run on `seabridge-spark`, exactly as specified below, on the d918428 tree?

**This packet authorizes nothing.** It starts no window, host probe, run, spend or protected action until Alejandro and PC (the Local Coordinator Manager) each say yes in the current session. PC proposed running the windows after the integration freeze; no date is set here. Written 2026-11-23 by the TREMOR lane from repository files and read-only host observations. The bench verdict stays with the separate reviewer (`X42_BENCH_REREVIEW_PACKET_d918428.md`); a green window is evidence for the quiet-machine half of the gate and says nothing about the bench half.

## 1. Basis

- **Policy** (`docs/WORKPLAN-RESIDENCY-V3.md`, sha256 `71c1cb470a3c1438dc2348963360167a49455bf864f1310b507cb37b5cbfc9f1`): "Gate R1: verifier ACCEPT on the bench; full suite green three times on a quiet machine." The policy gives no CPU idle, load, I/O, duration or skip threshold. This packet invents none. Where one is needed, the **host reviewer decides, with written reasons**, and the reasons go in that window's disposition.
- **Rule:** the agreed three-part prospective host-evidence rule, `coordinator-outbox/pc-x42-prospective-host-rule-agreement-1406Z.md`: (1) bind source, roster and skip disposition, image/argv/cgroup identity and an allowed-workload list before a window; unrelated concurrent jobs on the relevant resources make a window ineligible, unknown activity or unverifiable separation make it insufficient; (2) record suite start/stop, same-clock snapshots at both boundaries, window-scoped suite CPU and I/O next to host counters and non-suite workload evidence, with cadence and gap handling declared in advance, mixed intervals excluded, and one-minute load and the launcher memory floor treated as context only; (3) one reasoned eligible / ineligible / insufficient disposition per window; nothing carries across a changed source. That rule is a joint reviewers' standard; it does not amend the policy.
- **The three archived windows** (784 passed, 1 skipped each) remain insufficient evidence for e972484a, and nothing from them carries to d918428.
- **Observation today, for context only:** at 07:44 local the host showed a one-minute load of 36.5 on 20 CPUs, many agent `node` and `python` processes at 90 to 150 percent CPU, and a TREMOR container suite running. The host is not quiet now. Windows need the freeze.

## 2. Exact source

- Commit `f62cfe1b98e690c6bb38e87306e2baa5bb00d100` (`f62cfe1`, the current nominated candidate), tree `cdaee7645ab06162e13040963a586342963d57a5`, 623 files. Replaces `83e4870`: the row 169 per-module round at the exact candidate bytes found defects in five R1 modules, closed over several rounds (`runs/r1-row169-module-verification.BBKCr0/RECEIPTS.md`); the bench re-check at f62cfe1 (`runs/x42-bench-recheck-f62cfe1.CgLSTo/VERDICT.md`, sha256 `6ada3cf4…`) rules rows 155, 157, 158, 159, 162, 165 and 169 ACCEPT and row 167 INCOMPLETE. Dry preflight on 2026-11-24 (`runs/x42-quiet-host-dry-preflight-f62cfe1.uHq3nV`, EVIDENCE.sha256 `3a16b006…`): every pin passes. Roster, collected in the pinned image without running tests: package 912 test IDs (sha256 `caf3dc4139410e7c5a92d50456d5ebddf56d453365c618359b7c73146386e76d`), lab 929 (sha256 `d5082bb142037412193a88a9f5428ab21f422c85729a7d8ba8b0e9441267b392`). Container suites at this commit: package 912 OK, lab 929 OK, exit 0 (`runs/container-suite-f62cfe1.z58nsD`, EVIDENCE.sha256 `bc905905…`). Superseded and never to be run: `83e4870`, `a673019`, `4cdbb35`, `874861e`, `c527f40`. If the candidate moves again, both values and the roster must be redone before W1.
- The runner builds the source by `git archive d918428` into the window's own run folder, then checks every extracted file against its committed blob id (`git hash-object --no-filters`) and the file count against `git ls-tree`. A second manifest after the window must equal the first. Nothing is run from the shared working tree, which has uncommitted lane edits.
- **Added to the bundle, not from git:** two empty mountpoint directories (`runs/ep1-live/pilot3`, `data/tools/lean/lean-4.35.0-linux_aarch64`; the `formal/alloc_score` directory is in git) and two read-only mounts of inputs that are outside the tree:
  - Lean toolchain `data/tools/lean/lean-4.35.0-linux_aarch64` (outside git; the runner records the sha256 of `bin/lean` and a hash of the sorted file-size list; PC pins both at admission; the runner also tests a content digest of all 17925 regular files, `find . -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum` run inside the toolchain directory, equal to `2ff2426a230b59f49ed2c30962850e795b12e78adfc8a7de556d2c3426ecff3e` before any container starts; observed 2026-11-23, stable across two runs; the 13 symlinks are not covered).
  - `runs/ep1-live/pilot3/`, git-ignored and outside the e972484a manifest. Pins (observed 2026-11-23): `episodes.jsonl` `04401ed5cf7d07e82e65bfa95d792234ac201cb591b12419434bbff6c2e4e0f6`; `final.json` `c104fedf6f277c61fb5c28140b2881afac67fdd6edf465b2685ca988a84ed8e4`; `pilot_trace.txt` `f7116becf94086692a1b182de849472343866eea1b16084d4aac5635fa52eb19`; `schedule.json` `2a0188449dff2b411c67b603473349325ad8148afbaa74ef2d109d84a55ce003`. The runner refuses to start on any mismatch.
- **Nomination:** the candidate for the windows is the commit PC forwards for the bench re-review. The source must be exactly that nominated commit, and the runner pins (`commit`, `tree`) must be set to it; per the lane's nomination it is currently `1d333f7` or later (not verified here, and no hash or tree in this packet is bound to it until PC names it).
- A changed source (any new commit, any tree difference) voids this packet and needs a fresh nomination and a fresh yes.

## 3. Roster and skip disposition (to be pinned by PC before W1)

- **Suites in one window:** package (`discover -s tests`) and lab (`discover -s lab/tests -t .`), in that order, in two containers created before the window and run back to back.
- **Recorded at d918428 on the host** (clean `git archive`, no container, `runs/commit-suite-rebuild.gtQgQg/`): package 869 tests, OK, skipped 1, 755.6 s; lab 832 tests, errors 10, skipped 9, 62.3 s. The 10 lab errors are 4 numpy-dependent (`test_adapter_tensor_lineage`), 3 torch-dependent (`test_l8_loader_receipt`) and 3 that read `runs/ep1-live/pilot3/episodes.jsonl` (`test_pilot4_preflight_manifest`).
- **Container baseline (finished):** `runs/container-suite-d918428.Q1iSRQ/` (its `DONE` file and exit files exist; `OWNER.md` read). In the pinned image, with read-only mounts for the Lean toolchain, `runs/ep1-live/pilot3` and (lab only) `runs/spend/pilot3.jsonl`: package 869 tests, OK, skipped 1, exit 0 (`package.exit`); lab 832 tests, OK, skipped 2, exit 0 (`lab.exit`). The first lab run had 2 errors (`test_pilot4_preflight_manifest`) only because the spend ledger `runs/spend/pilot3.jsonl` was not mounted; that is a mount omission, not a code fault. The runner now binds `runs/spend/pilot3.jsonl` read-only into both containers, pinned at sha256 `142b7fef649bb0fe187ebf7fc5cb21e13a7bf4be17756cd9927c1eceae6117e1`, and checks five read-only mounts. The same setup ran green on candidate e11df9d (`runs/container-suite-e11df9d.hZjTis`: package 869 OK, lab 860 OK).
- **Open decision D2 (reviewer decides with reasons, before W1):** what "green" means for the lab suite. The policy has no allowance for errors. The container baseline settles the practical question: in the pinned image the lab suite is green, so D2 reduces to "green = both suites exit 0 in the pinned image with those read-only mounts". The host-only lab errors (numpy, torch, pilot3) do not occur in the container, so no named error allowance is needed. I recommend that rule. A window whose suite is not green under the pinned rule is not an eligible green window.
- **Pinning the roster:** the expected roster is the sorted list of test ids from discovery, produced without running a test, in a container with the section 6 flags, and its sha256 recorded by PC. Command (replace the final argument with `lab` for the lab suite, with `-t .` semantics built in):

```
python -B -c 'import sys,unittest
def ids(s):
    for t in s:
        if isinstance(t, unittest.TestSuite): yield from ids(t)
        else: yield t.id()
top = {"package": ("tests", None), "lab": ("lab/tests", ".")}[sys.argv[1]]
print("\n".join(sorted(ids(unittest.TestLoader().discover(top[0], top_level_dir=top[1])))))' package
```
  (with `PYTHONPATH=/repo/src:/repo/tests:/repo` for package and `/repo/src:/repo/lab:/repo/tests:/repo` for lab, the same as the suite). After each window, the reviewer compares the suite log's run count, skipped count and ERROR/FAIL ids with the pinned roster and skip list. A discovery import failure shows as a failed-test id in the roster and is counted.

## 4. Exact runner

Adapted from `runs/r1-n2-corrected-candidate.i5ACbL/run-suite.sh`. Differences from that script, in full: (a) source is `git archive d918428` verified against git, not a pre-made `source/` folder; (b) the image, limits, flags, three of four mounts and the 50 GiB `MemAvailable` launch floor (52428800 KiB) are unchanged; the fourth mount (pilot3, read-only) is new; (c) two containers (package, lab), created and inspected before the window, instead of one; (d) the suite timeout is 1500 s per container (the value in `runs/container-suite-d918428.Q1iSRQ/run.sh`; the old script used 480 s); it is an operational limit, not an acceptance threshold, and a timeout is a failed run; (e) inside the container the suite command is wrapped to print the container's own `cpu.stat`, `io.stat` and `memory.peak` immediately before and after the suite; (f) the collector writes one raw file per snapshot instead of one line per sample; (g) a go/no-go prompt after a preflight snapshot; (h) pins for source, pilot3 and Lean; (i) `PYTHONPATH` changed from `/repo/src` to the suite paths (`/repo/src:/repo/tests:/repo` and `/repo/src:/repo/lab:/repo/tests:/repo`); (j) the container shell changed from `-ec` with `exec timeout ...` to `-c` with `s=$?`, so the closing cgroup print runs and the exit status is passed on (`cp` failure exits 70); (k) the old script's `.Name` check in `jq -e` was dropped in the first draft and is restored here (`.Name == "/x42-<W>-<suite>-<pid>"`); (l) new: an EXIT trap that removes only this window's own created containers by exact id, and a bounded retry of the post-cleanup check. The suite command itself (`python -B -m unittest discover ...`) is unchanged. **The script has not been executed**; its syntax was checked with `bash -n` only. The untested point is whether the container can read its own `/sys/fs/cgroup/cpu.stat`; if it cannot, the in-container figures are lost and the host-side cgroup samples carry the window, with the last interval before exit treated as a mixed edge.

```bash
#!/usr/bin/env bash
# X42 quiet-window runner for d918428. Adapted from runs/r1-n2-corrected-candidate.i5ACbL/run-suite.sh.
# Not admitted until Alejandro and PC say yes. Usage: run-window.sh W1|W2|W3
set -euo pipefail
window="${1:?usage: run-window.sh W1|W2|W3}"
case "$window" in W1|W2|W3) ;; *) echo "bad window label" >&2; exit 64;; esac
repo=/home/adelmar/SeaBridgeAI/murmuration
commit=f62cfe1b98e690c6bb38e87306e2baa5bb00d100
tree=cdaee7645ab06162e13040963a586342963d57a5
image=sha256:c74c8710f2bc017b5de956853c50d896af4aa49b751bb87cbebf69e5206befb7
lean=$repo/data/tools/lean/lean-4.35.0-linux_aarch64
pilot3=$repo/runs/ep1-live/pilot3
spend=$repo/runs/spend/pilot3.jsonl
cadence=5
D=(docker --host unix:///var/run/docker.sock)
bundle=$(mktemp -d "$repo/runs/x42-quiet-$window.XXXXXX")
mkdir "$bundle/samples" "$bundle/source"

# Stop path: after any failure or signal, remove only this window's own containers, by exact id from the bundle.
runner=
cleanup() {
  local n id
  if [ -n "$runner" ]; then kill "$runner" 2>/dev/null || true; fi
  for n in package lab; do
    if [ -s "$bundle/$n.id" ]; then
      id=$(cat "$bundle/$n.id")
      "${D[@]}" rm -f "$id" >> "$bundle/trap-removed.txt" 2>/dev/null || true
    fi
  done
}
trap cleanup EXIT

manifest() { (cd "$bundle/source" && find . -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum); }

# Collector: one raw file per snapshot, bracketed by two readings of the same clocks (UTC realtime, uptime).
snap() {
  local f="$bundle/samples/$(date -u +%s%N)-$1.txt" g c
  {
    echo "t0=$(date -u +%FT%T.%NZ) up0=$(cut -d' ' -f1 /proc/uptime) label=$1"
    cat /proc/stat /proc/loadavg /proc/diskstats
    grep -E '^(MemTotal|MemAvailable|SwapFree|Dirty|Writeback):' /proc/meminfo
    for g in cpu io memory; do echo "== psi $g"; cat "/proc/pressure/$g"; done
    for g in /sys/fs/cgroup /sys/fs/cgroup/system.slice /sys/fs/cgroup/user.slice /sys/fs/cgroup/init.scope /sys/fs/cgroup/user.slice/user-*.slice; do
      echo "== cgroup $g"; cat "$g/cpu.stat" "$g/io.stat"
    done
    if [ -s "$bundle/current.id" ]; then
      c=/sys/fs/cgroup/system.slice/docker-$(cat "$bundle/current.id").scope
      echo "== container $(cat "$bundle/current.id")"
      cat "$c/cpu.stat" "$c/io.stat" "$c/memory.current" "$c/memory.peak" "$c/pids.current" "$c/cpu.pressure" "$c/io.pressure"
    fi
    echo "== proc (stat, cgroup per pid)"
    for g in /proc/[0-9]*; do cat "$g/stat" "$g/cgroup"; done
    case "$1" in preflight|*start|*stop|*end) echo "== ps"; ps -eww -o pid,ppid,uid,lstart,args;; esac
    echo "t1=$(date -u +%FT%T.%NZ) up1=$(cut -d' ' -f1 /proc/uptime)"
  } > "$f" 2>&1 || true
}

# Pins
test "$(git -C "$repo" rev-parse "$commit^{tree}")" = "$tree"
git -C "$repo" archive "$commit" | tar -xf - -C "$bundle/source"
git -C "$repo" ls-tree -r "$commit" | while read -r mode type blob path; do
  test "$(git -C "$repo" hash-object --no-filters -- "$bundle/source/$path")" = "$blob"
done
test "$(find "$bundle/source" -type f | wc -l)" = "$(git -C "$repo" ls-tree -r --name-only "$commit" | wc -l)"
mkdir -p "$bundle/source/runs/ep1-live/pilot3" "$bundle/source/runs/spend" "$bundle/source/data/tools/lean/lean-4.35.0-linux_aarch64"
: > "$bundle/source/runs/spend/pilot3.jsonl"  # mountpoint for the read-only spend ledger
test "$(sha256sum < "$spend" | cut -d" " -f1)" = 142b7fef649bb0fe187ebf7fc5cb21e13a7bf4be17756cd9927c1eceae6117e1  # spend ledger pin (observed 2026-11-23)
manifest > "$bundle/source.before.sha256"
(cd "$pilot3" && sha256sum -c --quiet - <<'PINS'
04401ed5cf7d07e82e65bfa95d792234ac201cb591b12419434bbff6c2e4e0f6  episodes.jsonl
c104fedf6f277c61fb5c28140b2881afac67fdd6edf465b2685ca988a84ed8e4  final.json
f7116becf94086692a1b182de849472343866eea1b16084d4aac5635fa52eb19  pilot_trace.txt
2a0188449dff2b411c67b603473349325ad8148afbaa74ef2d109d84a55ce003  schedule.json
PINS
)
test -x "$lean/bin/lean"
sha256sum "$lean/bin/lean" > "$bundle/lean-bin.sha256"
(cd "$lean" && find . -type f -printf '%s %p\n' | LC_ALL=C sort | sha256sum) > "$bundle/lean-tree.sha256"
test "$(cd "$lean" && find . -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum | cut -d" " -f1)" = 2ff2426a230b59f49ed2c30962850e795b12e78adfc8a7de556d2c3426ecff3e  # Lean toolchain content pin (observed 2026-11-23)
test "$(awk '/^MemAvailable:/ {print $2}' /proc/meminfo)" -ge 52428800
test "$("${D[@]}" image inspect --format '{{.Id}}' "$image")" = "$image"

# Containers are created and inspected before the window so no create/inspect work falls inside it.
mk() {  # $1 name, $2 PYTHONPATH, rest = unittest discover arguments
  local n=$1 pp=$2 id; shift 2
  id=$("${D[@]}" create --rm --name "x42-$window-$n-$$" --pull=never --network=none --read-only --runtime=runc \
    --memory=4g --cpus=2 --pids-limit=256 --user 1000:1000 \
    --tmpfs /tmp:rw,exec,nosuid,nodev,size=512m,mode=1777 \
    --tmpfs /repo/formal/alloc_score:rw,exec,nosuid,nodev,size=384m,mode=1777 \
    --mount "type=bind,source=$bundle/source,target=/repo,readonly" \
    --mount "type=bind,source=$bundle/source/formal/alloc_score,target=/lean-source,readonly" \
    --mount "type=bind,source=$lean,target=/repo/data/tools/lean/lean-4.35.0-linux_aarch64,readonly" \
    --mount "type=bind,source=$pilot3,target=/repo/runs/ep1-live/pilot3,readonly" \
    --mount "type=bind,source=$spend,target=/repo/runs/spend/pilot3.jsonl,readonly" \
    --workdir /repo -e HOME=/tmp -e CUDA_VISIBLE_DEVICES= -e PYTHONDONTWRITEBYTECODE=1 \
    -e PYTHONPATH="$pp" -e OMP_NUM_THREADS=2 --entrypoint /bin/sh "$image" \
    -c 'cp -R /lean-source/. /repo/formal/alloc_score/ || exit 70; cg() { echo "== CGROUP $1"; cat /sys/fs/cgroup/cpu.stat /sys/fs/cgroup/io.stat /sys/fs/cgroup/memory.peak 2>&1 || true; }; cg start; timeout 1500s python -B -m unittest discover "$@"; s=$?; cg end; exit $s' sh "$@")
  [[ "$id" =~ ^[0-9a-f]{64}$ ]]
  printf '%s\n' "$id" > "$bundle/$n.id"
  "${D[@]}" inspect "$id" | jq '.[0] | {Id, Name, Image, State: .State.Status, Host: (.HostConfig | {NetworkMode, Memory, NanoCpus, PidsLimit, ReadonlyRootfs, Runtime, DeviceRequests, Devices, PortBindings}), Mounts: [.Mounts[] | {Source, Destination, RW}]}' > "$bundle/$n.inspection.json"
  jq -e --arg id "$id" --arg name "/x42-$window-$n-$$" --arg image "$image" \
    '.Id == $id and .Name == $name and .Image == $image and .State == "created" and
     (.Host | .NetworkMode == "none" and .Memory == 4294967296 and .NanoCpus == 2000000000 and
       .PidsLimit == 256 and .ReadonlyRootfs and .Runtime == "runc" and
       (.Devices | length) == 0 and (.DeviceRequests | length) == 0 and (.PortBindings | length) == 0) and
     (.Mounts | length) == 5 and all(.Mounts[]; .RW == false)' "$bundle/$n.inspection.json" >/dev/null
}
mk package /repo/src:/repo/tests:/repo -s tests -v
mk lab /repo/src:/repo/lab:/repo/tests:/repo -s lab/tests -t . -v

snap preflight
read -r -p "Preflight snapshot written to $bundle/samples. Type $window to start the window: " answer
test "$answer" = "$window"

# The window: package container, then lab container, back to back; the collector ticks every $cadence s.
(
  for n in package lab; do
    cat "$bundle/$n.id" > "$bundle/current.id"
    snap "$n-start"
    date -u +%FT%T.%NZ > "$bundle/$n.started-utc.txt"
    st=0; "${D[@]}" start --attach "$(cat "$bundle/$n.id")" > "$bundle/$n.log" 2>&1 || st=$?
    printf '%s\n' "$st" > "$bundle/$n.exit"
    date -u +%FT%T.%NZ > "$bundle/$n.ended-utc.txt"
    snap "$n-end"
  done
  : > "$bundle/DONE"
) &
runner=$!
while kill -0 "$runner" 2>/dev/null; do snap tick; sleep "$cadence"; done
wait "$runner"
rm -f "$bundle/current.id"
snap post-window

# Cleanup evidence and source integrity
# --rm removal can lag the exit of "docker start --attach", so retry a few times before failing.
for n in package lab; do
  for i in 1 2 3 4 5; do
    "${D[@]}" ps -a --no-trunc --filter "id=$(cat "$bundle/$n.id")" --format '{{.ID}}' > "$bundle/$n.post-cleanup-ids.txt"
    [ -s "$bundle/$n.post-cleanup-ids.txt" ] || break
    sleep 1
  done
  test ! -s "$bundle/$n.post-cleanup-ids.txt"
done
manifest > "$bundle/source.after.sha256"
cmp "$bundle/source.before.sha256" "$bundle/source.after.sha256"
for n in package lab; do tail -n 7 "$bundle/$n.log"; done
test "$(cat "$bundle/package.exit")$(cat "$bundle/lab.exit")" = 00
```

The post-cleanup `ps -a` check retries up to five times one second apart, because `--rm` removal can race the check; the limit that remains is that a container still present after about five seconds fails the runner and is then removed by the trap. The final line makes the runner exit nonzero unless both suites exited 0. That is a convenience, not the disposition; the disposition follows the pinned green rule (section 3, D2) and the evidence rules below.

## 5. Image, argv, limits

- **Image:** `sha256:c74c8710f2bc017b5de956853c50d896af4aa49b751bb87cbebf69e5206befb7` (arm64, tag `murmuration-t7:1`), inspected and compared by id before the window; `--pull=never`.
- **Argv per container** (see `mk`): `docker --host unix:///var/run/docker.sock create --rm --name x42-<W>-<suite>-<pid> --pull=never --network=none --read-only --runtime=runc --memory=4g --cpus=2 --pids-limit=256 --user 1000:1000`, tmpfs `/tmp` 512m and `/repo/formal/alloc_score` 384m, four read-only bind mounts (bundle source, Lean project copy source, Lean toolchain, pilot3), workdir `/repo`, env `HOME=/tmp CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2` and the suite `PYTHONPATH`, entrypoint `/bin/sh`.
- **Limits and checks:** no network, read-only root, no devices, no GPU, no published ports, runc, 4 GiB, 2 CPUs, 256 processes; `jq -e` verifies each before the window. Suite timeout 1500 s per container.
- **Cgroup identity:** systemd driver, cgroup v2; the container's scope is `/sys/fs/cgroup/system.slice/docker-<id>.scope` (the `docker info` and slice layout were read on the host today).

## 6. Allowed-workload list

Under rule part (1) every standing service is named and either allowed with a reason or excluded. Allowed workload has its CPU and I/O recorded, not hidden; "allowed" never means "ignored". Anything not on this list that uses the relevant resources makes the window ineligible; activity the evidence cannot attribute makes it insufficient.

| Workload | Status | Justification |
| --- | --- | --- |
| The two suite containers and their `containerd-shim`/`runc` processes | Allowed | The subject of the window. |
| `run-window.sh`, `docker` CLI, `jq`, `sha256sum`, `git archive` | Allowed | The runner. Source building and pin checks happen before `snap preflight`; only `docker start --attach`, the collector and `sleep` run inside the window. |
| The collector (`snap`: `cat`, `date`, `ps`, `sleep`) | Allowed | Required by the rule; its own CPU is attributable by pid and recorded as non-suite workload. |
| `dockerd` and `containerd` | Allowed | Required to run the containers; their cgroups are sampled. |
| Kernel threads, `systemd` (pid 1), `systemd-journald`, `systemd-udevd`, `systemd-logind`, `dbus`, `rsyslog`, `systemd-timesyncd`, `systemd-resolved`, `systemd-networkd`, `NetworkManager`, `cron`, `polkit` | Allowed | Necessary OS and runtime services on the live host. Not stopped, because stopping them is a host change outside this packet. |
| `ssh.service`/`sshd` and the operator's one idle shell | Allowed | The operator needs access; the operator session must not run a command during the window except the runner. |
| `tailscaled`, `nvidia-persistenced`, `nvidia-dgx-telemetry`, `dgx-dashboard*`, `rasdaemon`, `smartmontools`, `multipathd`, `lldpd` | Allowed as background | Standing platform and hardware services; recorded, not stopped. The reviewer decides with reasons whether any shows material activity. |
| Desktop and convenience services (`gdm`, `gnome-remote-desktop`, `cups*`, `avahi-daemon`, `bluetooth`, `ModemManager`, `colord`, `udisks2`, `upower`, `accounts-daemon`, `fwupd`, `snapd`, `switcheroo-control`) | Allowed as background | Standing services present in the unit list today; stopping them is a host change. Recorded; the reviewer decides if any is material. |
| The four standing MongoDB containers (`ii-spark-mongo-20261121`, `seabridge-mongo`, `seabridge-mongo-t2`, `seabridge-mongo-test`) | Allowed only if idle, else excluded | They run for other lanes and are not to be stopped by this lane. Their cgroup CPU and I/O are sampled; any activity makes the window ineligible unless the reviewer rules it immaterial with reasons. |
| Any agent session executing a turn (Claude, Codex, Kimi, Orca workers, `node` and `python` agent processes), any build, test, download, training, inference or data job, any other Docker container, any Spark vLLM serving request | **Excluded** | Unrelated concurrent jobs on the CPU, memory or disk the suite uses. These must be quiesced (idle, not killed) for the whole freeze. |
| GPU | Excluded | The suite has no GPU (`CUDA_VISIBLE_DEVICES=` empty, no devices); the suite never touches it. A GPU job elsewhere is not a CPU or I/O competitor, but any GPU job's host-side CPU is still counted under the rows above. |

The freeze: PC, not this lane, confirms that other lanes' sessions are quiesced. This lane kills nothing and stops no one else's process.

## 7. Host-evidence capture

- **Clock:** UTC realtime plus `/proc/uptime`, read twice per snapshot (`t0`, `t1`). The bracket width is the stated timing uncertainty of that snapshot. Container start and end times come from the same `date -u` call family and are recorded with the snapshots taken immediately before `docker start` and immediately after it returns.
- **Boundary snapshots:** `preflight`; `package-start`, `package-end`, `lab-start`, `lab-end`; `post-window`. Window start = `package.started-utc.txt`, stop = `lab.ended-utc.txt`.
- **Per snapshot (raw, unreduced):** `/proc/stat`, `/proc/loadavg`, `/proc/diskstats`, selected `/proc/meminfo`, pressure (`cpu`, `io`, `memory`), `cpu.stat` and `io.stat` for the root cgroup, `system.slice`, `user.slice`, `init.scope` and each `user-*.slice`, the current container scope's `cpu.stat`, `io.stat`, `memory.current`, `memory.peak`, `pids.current` and pressure files, and every process's `/proc/<pid>/stat` and `cgroup`. Boundary snapshots add `ps -eww -o pid,ppid,uid,lstart,args`. Inside each container the wrapper prints the container's own `cpu.stat`, `io.stat` and `memory.peak` at suite start and end (untested, see section 4).
- **Cadence:** every 5 seconds (the cadence of the existing runner), declared before the window. Snapshot cost is recorded, not hidden.
- **Window-scoped suite CPU and I/O:** the difference of the container scope's `cpu.stat` (`usage_usec`, `user_usec`, `system_usec`, `nr_throttled`) and `io.stat` between the start and end snapshots of each suite, and the in-container before/after figures. Beside it: host `/proc/stat` deltas, the slice-level `cpu.stat`/`io.stat` deltas, per-pid `utime`+`stime` deltas grouped by cgroup path, and `/proc/diskstats` deltas for the devices holding the bundle, `/tmp`, and Docker's root. Non-suite workload evidence is host total minus the suite scope, broken down by slice and by process against the section 6 list.
- **One-minute load and the 50 GiB memory floor** are recorded as context only and never decide a window.
- **Gaps:** a gap is a pair of consecutive snapshots more than twice the cadence apart (declared parameter, not a quietness threshold), or a snapshot whose `t1 - t0` bracket exceeds the cadence. A gap interval's activity is unknown; it is marked insufficient evidence for that interval, and the window is insufficient unless the reviewer can show with other evidence (cumulative counters bracketing the gap) that nothing outside the allowed list ran in it.
- **Mixed edges:** an interval that contains a window boundary or the package-to-lab handover mixes in-window and out-of-window activity. It is excluded from window-specific calculations (suite CPU, non-suite share), and cumulative counters are used only across whole intervals. If material concurrent activity in an excluded interval stays unresolved, the window is insufficient evidence.
- **Retention (same receipt, in the window's run folder):** raw samples, both suite logs, both exit files, inspection JSONs, container ids, start and end times, source manifests before and after, pins, Lean identity, post-cleanup ids. Nothing is summarized away; reductions are separate files with the raw files kept.

## 8. Three-run schedule

W1, W2 and W3 run back to back inside one freeze, each from a fresh `run-window.sh` call with its own run folder, source copy, containers and snapshots. Between windows the freeze holds and the host reviewer may read W(n) while W(n+1) waits; the operator starts W(n+1) only after the runner for W(n) exits and its `DONE` file exists. No earlier start than PC's integration-freeze announcement and Alejandro's yes. Duration is not measured for the container at d918428: the host package suite took 755.6 s and the lab suite 62.3 s, the container timeouts are 1500 s each, so a window is bounded at about 50 minutes of suite time plus snapshot overhead, and three windows at about 2.5 hours, not counting preflight and review. If a window is not eligible, the gate is not met and a replacement window needs a fresh yes; this packet covers exactly three attempts.

## 9. Per-window disposition template

One file per window, `DISPOSITION_<W>.md`, written by the host reviewer (the Assistant's designated role, not the operator and not the bench reviewer):

```
Window: W<n>      Source: f62cfe1b98e690c6bb38e87306e2baa5bb00d100 / tree cdaee764...
Run folder: runs/x42-quiet-W<n>.<suffix>      Operator: <name>      Reviewer: <name>      Date:
Pins verified (source before/after equal; pilot3; Lean; image id; inspection checks):  yes/no, notes
Roster (pinned sha256 <...>): package ran/skipped/ERROR/FAIL = ... ; lab = ... ; differences from the pinned roster: ...
Suite result under the pinned green rule (D2): green / not green, reason
Start/stop (UTC): <package.started> -> <lab.ended>      Snapshots: <list>, gaps: <list>, mixed intervals: <list>
Suite CPU/IO (cgroup, in-container): ...      Host CPU/IO over whole intervals: ...      Non-suite workload by slice/process: ...
Allowed-list conformance: only-allowed / unlisted activity found: <what, when, how much>
Unknown or unattributable activity: none / <where>
Disposition: ELIGIBLE / INELIGIBLE / INSUFFICIENT
Reasons (written, evidence-cited; any judgement on "material" is explained here, no number from the policy):
Carries to other windows or sources: no.
```
ELIGIBLE means a green suite under the pinned roster with attributable evidence that only allowed workload used the relevant resources throughout. Three ELIGIBLE windows on d918428 are the evidence for the quiet-machine half of the gate. The bench verdict is separate.

## 10. Stop conditions

Stop (no further window, report to PC and Alejandro) on: any pin or manifest mismatch; the runner's own `test`/`jq -e` checks failing; `MemAvailable` below the launch floor; the preflight snapshot showing excluded activity (the operator does not type the label); an OOM kill, pid-limit hit, container timeout or Docker daemon error; the collector failing or gaps that cannot be resolved; a disk or capacity problem in the run folder's filesystem; any request from Alejandro or PC to stop. The only process the operator may stop is this window's own named containers (`docker stop x42-<W>-...`); on any stop path the runner's EXIT trap itself removes this window's own containers by exact id (`docker rm -f` of the ids in `package.id` and `lab.id`, logged in `trap-removed.txt`), and nothing else; no other process or service is touched, and nothing is retried silently. Any spend, network or GPU use is out of scope and would be a stop; none is planned or needed.

## 11. Rollback

Nothing to roll back. The runner changes no service, setting, repository file or git state; its only writes are the new `runs/x42-quiet-<W>.*` folders and the containers' `--rm` cleanup (on a stop path, the EXIT trap removes only this window's own containers by exact id). The owner removes the run folders if they want them gone (this lane never deletes). The runner and this packet are not installed anywhere.

## 12. Risk

- **Other lanes' work stops** for the freeze (about 2.5 hours of suites plus review), which is the main cost.
- **Disk:** raw snapshots hold every process's `stat` line and a cgroup line per cadence tick; one snapshot is likely hundreds of kilobytes, not measured. `runs/` is 11 GiB on a volume with 2.1 TiB free, so capacity is not the concern, but PC should have the `preflight` snapshot size read before W1.
- **Collector load:** reading about a thousand `/proc` entries every 5 s is itself CPU on a 20-CPU host. It is on the allowed list and attributable, and the reviewer may judge it material; if so, the cadence changes before the window, not during.
- **Untested script and untested in-container cgroup read** (section 4). A failure appears as a stop before any suite runs or as missing in-container figures, not as a wrong green.
- **Green in a window is not proven here.** The container baseline is green (at f62cfe1: package 912 and lab 929, both exit 0), but the host lab run has 10 environmental errors; D2 must still be recorded by the reviewer as the container rule above.
- **A window can come out ineligible or insufficient** even if every test passes; that is the rule working.

## 13. Recommendation

Yes, on these conditions, and not before them: (1) the integration freeze is announced by PC and other lanes are confirmed quiesced; (2) PC pins the roster and skip list (section 3), the Lean identity and the pilot3 pins; (3) the host reviewer rules D2 (my recommendation: green = both suites exit 0 in the pinned image with the read-only mounts for Lean, `runs/ep1-live/pilot3` and `runs/spend/pilot3.jsonl`; the finished baseline `runs/container-suite-d918428.Q1iSRQ/` shows package 869 OK exit 0 and lab 832 OK exit 0 in that setup); (4) the script gets one syntax and dry check by someone other than its author, without running a window; (5) the host reviewer and the operator are different people, and neither is the bench reviewer. Any change to the source, image, runner, roster or allowed list after the yes voids the yes.

## 14. Where the reviewer decides, with reasons (no invented threshold)

What counts as material concurrent activity; whether a given allowed background service is material in a window; whether a gap or mixed edge is resolved by other evidence; the meaning of green for the lab suite (D2); whether the collector's own load is acceptable; whether a window with a recorded in-container cgroup failure is still sufficient; the disposition itself. No CPU idle, load, I/O or duration number is set by this packet or by the policy.

## 15. What a yes means

Alejandro and PC both say yes in the current session: the runner may be called for W1, W2 and W3 on the d918428 tree under the conditions above, by the named operator, once each. It authorizes no push, no spend, no D8 or Pilot 4 action, no N2 access and no bench verdict.
