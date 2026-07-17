# Two-interval scan for higher multipliers

This directory contains one standard-formulation run for every integer
`m=4,...,100`, with `N=2`.  Each invocation used the template

```bash
.venv/bin/python circle_intervals.py -N 2 --m <m> \
  --mip-rel-gap 0 --require-success \
  --output-dir json_results/verification_20260716/two_interval_scan \
  --run-name m<m>_N2_standard_gap0
```

Thus the runs used the original formulation, the default monotonicity and
endpoint-length cuts, no width cuts, `epsilon=0`, and an explicitly requested
zero relative MIP gap.  All 97 solves returned `success=true`, equal reported
primal and dual objectives, and `mip_gap=0`.

The objectives agree with

```text
2(m-2) / [m(m+2)]
```

throughout the scan.  The largest discrepancy in the original saved points
was `6.68e-11`, at `m=87`.  Independent replay found that point to violate one
integer lift and one row by about `6.11e-9`, within the solver's default
feasibility tolerances.  The supplemental run in `../two_interval_scan_strict`
used `1e-10` MIP, primal, and dual feasibility tolerances.  It again proved
zero-gap optimality, has maximum replay residual `2.71e-14`, and reconstructs
exactly as

```text
objective = 170/7743 = 2(87-2) / [87(87+2)].
```

Every stem here has a full `_problem.json` and `_solution.json`.  These are
floating-point MILP certificates; the strict rational reconstruction at
`m=87` verifies the most numerically marginal saved point.
