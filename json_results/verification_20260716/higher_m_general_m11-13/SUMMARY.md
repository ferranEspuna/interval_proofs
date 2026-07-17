# Unrestricted higher-m continuation, 2026-07-17

## Scope and commands

This directory extends the standard unrestricted finite-union MILP through
`m=11,12,13`.  The completed matrix contains the `N=5` checks and lower-`N`
checkpoints needed to identify the first component count at which the general
model improves on the equally spaced base:

```sh
.venv/bin/python circle_intervals.py \
    -N N \
    --m M \
    --mip-rel-gap 0 \
    --require-success \
    --output-dir json_results/verification_20260716/higher_m_general_m11-13 \
    --run-name mM_NN_standard_gap0
```

No translated formulation, width cuts, subset bound, total-length lower bound,
or fixed base construction is used.  The standard defaults retain monotonicity
and endpoint-length cuts.  `run_all.sh` contains the six completed commands and
each run has its full problem, solution, and `/usr/bin/time -v` log.

## Completed unrestricted results

All six saved runs report `success=true`, `status_name="optimal"`, and stored
`mip_gap=0`.

| `m` | `N` | optimum | positive components | nodes | wall time |
|---:|---:|:---|---:|---:|:---|
| 11 | 3 | `21/143` numerically | 3 | 274 | 0.99 s |
| 11 | 5 | `21/143` numerically | 3 | 104,167 | 3:08.81 |
| 12 | 4 | `1/7` numerically | 3 | 15,031 | 15.82 s |
| 12 | 5 | `145/1008` numerically | 5 | 103,007 | 3:05.77 |
| 13 | 4 | `28/195` numerically | 4 | 7,028 | 10.66 s |
| 13 | 5 | `73/507` numerically | 5 | 78,142 | 1:57.70 |

For `m=11`, monotonicity in the allowed number of components squeezes the
intermediate `N=4` value between the equal `N=3` and `N=5` results.  For
`m=12,13`, `N=4` remains at the equally spaced base and `N=5` is the first
tested component count with a strict gain: respectively `1/1008` and
`1/2535`.  The unrestricted optimizers reproduce the one-extra construction
without fixing the base in advance.

## Direct N=6 handoff

The immediate unrestricted `N=6` checks for `m=12,13` were launched with the
same standard zero-relative-gap command and no subset bound.  They were still
branching when this artifact set was handed back to the parent campaign, so
they are not counted as completed here and no claim of a direct general-model
upper bound is made yet.  The exact commands are retained in `run_n6.sh` and
`run_m13_n6_only.sh`; completed results should be added here only after their
solution JSONs exist and replay successfully.

Independently of those pending upper-bound computations, the fixed-base
specialized campaign supplies exact six-interval lower bounds `73/504` for
`m=12` and `122/845` for `m=13`.

## Exact construction certificates

`verify_exact_constructions.py` checks rational open-interval constructions
without floating point.  For every interaction it verifies that

```text
[a_r + a_s - m b_t, b_r + b_s - m a_t]
```

lies in one unit interval between consecutive integers; because the actual
image is open, equality at the displayed endpoints is allowed.  The retained
`exact_certificate_check.log` covers:

- the unrestricted `m=12,13`, `N=5` constructions;
- the exact `m=12,13` two-extra constructions;
- the first positive third interval at `m=12`; and
- the later `m=16,17,20,21` saturation constructions.

All checks pass.  In particular, the `m=12,13`, `N=5` lower bounds check all
75 interactions exactly, and the six-interval constructions check all 126.

## Replay validation

The six completed unrestricted assignments were replayed against their stored
problems with `../replay_artifact_directory.py`.  `replay_report.json` records
zero bound, integrality, and objective error and maximum row violation
`7.17e-12`.  Solution artifact links are repository-relative.
