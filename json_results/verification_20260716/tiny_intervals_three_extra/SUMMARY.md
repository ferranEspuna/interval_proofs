# Three-extra threshold check, 2026-07-17

## Scope

This bounded follow-up tests when a third extra interval can improve the fixed
optimized equally spaced base.  It covers the larger optimizing branch for
`m=8,9,12,13,16,17` and the tied smaller branch for `m=12,16`.  Every run used
anchor `0`, three arbitrary extra intervals, zero relative MIP gap, and an
explicit per-extra length bound equal to the independently saved one-extra
optimum.  For example,

```sh
.venv/bin/python equally_spaced_tiny_interval_lp.py \
    --m 16 \
    --tie-choice larger \
    --anchor 0 \
    --extra-count 3 \
    --extra-length-bound 0.0004340277777777778 \
    --mip-rel-gap 0 \
    --require-success \
    --output-dir json_results/verification_20260716/tiny_intervals_three_extra \
    --run-name m16_q5_extra3_per_extra_bound_1over2304_gap0
```

The bound is inductively valid: after deleting the other extras, each retained
extra is a feasible one-extra extension of the same base.  The exact commands
and resource use are retained in the per-run logs.  `run_bounded.sh` contains
the complete matrix.  Problem JSONs are deterministically gzip-compressed, and
the solution metadata points to the compressed files.

## Results

All eight runs report `success=true`, `status_name="optimal"`, and stored
`mip_gap=0`.

| `m` | `q` branch | positive extras | extra lengths above `1e-9` | total gain |
|---:|:---|---:|:---|:---|
| 8 | 3, larger | 1 | `1/320` | `1/320` |
| 9 | 3, larger | 1 | `1/891` | `1/891` |
| 12 | 3, smaller | 0 | none | `0` |
| 12 | 4, larger | 3 | `1/1008, 5/12096, 1/1008` | `29/12096` |
| 13 | 4, larger | 2 | `1/2535, 1/2535` | `2/2535` |
| 16 | 4, smaller | 0 | none | `0` |
| 16 | 5, larger | 3 | three copies of `1/2304` | `1/768` |
| 17 | 5, larger | 3 | three copies of `1/5491` | `3/5491` |

Thus the first genuinely positive third interval occurs at `m=12`, although
it is shorter than the first two.  At `m=16,17`, all three extras attain the
one-extra upper bound.  At `m=13`, a third extra still does not help.

The `m=12` construction was rationalized to total density `251/1728`.  The
central checker `../higher_m_general_m11-13/verify_exact_constructions.py`
verifies all 196 open-interval interactions with exact fractions; 14 endpoint
slacks are zero and the least positive endpoint slack is `1/144`.

## Replay validation

`../replay_artifact_directory.py` replayed all eight stored assignments against
their stored problems.  The retained `replay_report.json` records zero
integrality and objective error, maximum bound violation
`2.86e-15`, and maximum row violation `6.31e-14`.
