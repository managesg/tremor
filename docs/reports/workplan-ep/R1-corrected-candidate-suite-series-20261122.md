# R1 corrected-candidate suite series

All three isolated CPU suites exited zero on the same 351-file candidate
`e972484a4db7c24f75058bf904c273545a4a4684a6dcc370caed2de44b1726de`.
Each ran the same 785 ordered test cases and recorded one Torch-dependent
skip. The unchanged skipped test separately passed in an environment
without Torch on the same candidate. Seven focused custody tests and
the independent six-case public replay also passed.

| Run | Test time (seconds) | Host samples | Minimum CPU idle | Median CPU idle | Maximum one-minute load |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 225.815 | 48 | 81.545% | 89.704% | 2.82 |
| 2 | 244.068 | 52 | 69.398% | 88.746% | 5.20 |
| 3 | 251.855 | 53 | 74.537% | 86.133% | 4.36 |

The attachment windows were serial and had distinct Docker identities.
Each container used the same pinned ARM64 image, two CPUs, 4 GiB of RAM,
read-only source and toolchain mounts, and no GPU attachment, network,
or published ports. Exact-ID queries confirmed each container was
absent after its attachment finished. The host samples bracketed each
window, with a maximum gap no greater than 5.051 seconds. Host
contention differed across the three windows.

The stricter replay uses only CPU counter intervals wholly inside each
attachment. They cover 97.83%, 98.00%, and 98.04% of the respective
windows. The in-window CPU tick-weighted idle shares are 90.15%, 87.62%,
and 86.82%. The second run's observed maximum I/O wait drops from 2.151%
to 0.185% when its boundary intervals are excluded. The third drops from
1.389% to 0.216%. The counters cannot attribute part of a straddling
interval to the attachment. The sampled one-minute load still includes
work from earlier in the minute. [Replay and scope](../../../runs/r1-window-counter-scope.QjV54l/OWNER.md)

The Coordinator and independent reviewer still need to qualify
quiet-host conditions and nominate this candidate. Only the windows
they qualify can count toward the three-run gate. The protected N2
predicate, examples and separation review remain with the author and
independent custodian. The fresh per-module checks and separate
adversarial bench verdict remain pending.

The independent technical pre-review found that `pairwise_miss`
silently truncates mismatched monitor rows and reports zero correlation
when no pair has defined phi. A detached patch rejects misaligned
observations and distinguishes unavailable correlation from measured
zero. Its 41 focused tests passed and the existing public control
report reproduced byte for byte. The source owner still needs to adopt
the patch and rerun the applicable suite on the nominated cut.
[Review packet](../../../runs/r1-exact-module-review.sdzwWw/OWNER.md)

Verify the three exact archived receipts and the unchanged Torch-absence
check from the Murmuration root.

```bash
bash runs/r1-n2-three-receipts.BeDGMH/verify.sh
(cd runs/r1-n2-corrected-candidate.i5ACbL/source && \
  PYTHONPATH="$PWD/tests:$PWD/src" PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest -v \
  test_runner.RunnerTests.test_local_hf_fails_cleanly)
```

See the [earlier R1 review](R1-evidence-review-20261121.md) for the
public verdict substitution and the exact source correction. The CPU
series provides evidence toward the R1 gate. Protected R3 runs remain
a separate part of milestone 3.
