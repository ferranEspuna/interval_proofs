# Final `m=12`, `N=7` length-order audit

This directory contains the completed all-endpoints-free, depth-two audit.
All `6*5=30` ordered length prefixes are closed:

- `optimal`: `(1,3)`, `(1,5)`, `(3,1)`, `(5,1)`, each at floating-point
  objective and dual bound `251/1728` up to solver tolerance, with zero gap;
- `infeasible`: the other 26 prefixes, after imposing the known-construction
  cutoff `sum(alpha) >= 251/1728`.

The four optimal cases overlap because two component lengths are tied and the
formulation has reflection symmetry.  They all have four lengths `1/28`, two
lengths `1/1008`, and one length `5/12096`.  Together, the 30 final
attempts used 42,749,286 nodes and 121,154.13 solver-seconds.  None ended at a
time or node limit.

Each prefix `i-j` has three retained artifacts:

- `m12_N7_lengthorder_i-j_problem.json`: complete named MILP;
- `m12_N7_lengthorder_i-j_solution.json`: final status and solver data;
- `m12_N7_lengthorder_i-j.log`: final HiGHS log.

Re-audit the directory from the repository root with:

```bash
.venv/bin/python \
  json_results/experiments_20260801/m12_global_N7/summarize_length_order_cases.py
```

The exact construction is available in the
[visualizer inventory](../../../VISUALIZER_LINKS.md), and its rational replay
is produced by
`json_results/experiments_20260801/m12_global_N7/verify_unrestricted_incumbent_exact.py`.

## Scope of the result

The split is exhaustive because index 0 is chosen globally shortest, then the
prefix chooses a shortest of the remaining six and a shortest of the remaining
five.  Ties may duplicate a configuration but cannot omit one.  Starts and
lengths remain free, so this goes beyond the fixed equally spaced-base model
and includes unions of fewer than seven intervals through zero lengths.

The numerical upper bound is conditional on the imported `N=2,...,6` subset
bounds `5/42`, `1/7`, `1/7`, `145/1008`, and `73/504`.  Those are zero-gap
floating-point MILP reconstructions, not exact branch certificates.  Hence the
directory establishes a zero-gap numerical optimum for the conditional model,
not an unconditional formal theorem.  The exact `251/1728` lower-bound
construction is independently certified.
