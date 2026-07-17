# Full finite-union checks for `m=3`

This directory contains the fresh finite-union checks used in the central
LaTeX document.  The runs through `N=6` are direct; the larger rows use the
preceding finite-model result as a bound on each smaller subunion.  All
completed rows below requested a zero relative MIP gap and returned equal
primal and dual objectives.

## Completed `N=1,...,7` runs

For `N=1,...,6` the command template was

```sh
.venv/bin/python circle_intervals.py -N N --m 3 \
  --mip-rel-gap 0 --require-success \
  --output-dir json_results/verification_20260716/m3_full \
  --run-name m3_NN_standard_gap0
```

These runs used the original formulation, no width cuts, the default lift
monotonicity cuts, and the endpoint-length reflection cut.  The `N=7` run
used the already completed `N=6` finite-model bound on every six-component
subunion:

```sh
.venv/bin/python circle_intervals.py -N 7 --m 3 \
  --width-cuts --monotonicity-cuts --endpoint-length-cut \
  --subset-alpha-bound 6:0.2 --mip-rel-gap 0 --require-success \
  --output-dir json_results/verification_20260716/m3_full \
  --run-name m3_N7_with_N6_bound_gap0
```

| `N` | reported objective | dual bound | MIP gap | nodes |
|---:|---:|---:|---:|---:|
| 1 | `0.2` | `0.2` | 0 | 1 |
| 2 | `0.20000000000000018` | `0.20000000000000018` | 0 | 5 |
| 3 | `0.19999999999999996` | `0.19999999999999996` | 0 | 27 |
| 4 | `0.2000000000000036` | `0.2000000000000036` | 0 | 401 |
| 5 | `0.20000000000113327` | `0.20000000000113327` | 0 | 4,329 |
| 6 | `0.20000000000000526` | `0.20000000000000526` | 0 | 59,958 |
| 7 | `0.20000000000002408` | `0.20000000000002408` | 0 | 759,172 |

Every serialized `N=1,...,7` assignment was independently replayed against
the corresponding variable bounds and constraint rows.  The largest row
residual was `1.181e-12`; the maximum bound violation was `5.25e-15`, and
the maximum integrality violation was zero.  The reproducible checker and
per-solution report are `replay_saved_solutions.py` and `replay_report.json`.

## `N=8`

The fresh `N=8` certification is still running.  It uses the numerical
`N=7` bound `1/5` on every seven-component subunion, together with the
independently known one-interval construction as a safe optimization cutoff
and feasible MIP start.  This section will be replaced by the retained final
command and solver diagnostics when the run completes.

The subset bounds make these finite-model checks inductive numerical
certificates: they are valid relative to the preceding saved finite-model
result.  As throughout this campaign, a zero floating-point MIP gap is not an
exact rational branch certificate.
