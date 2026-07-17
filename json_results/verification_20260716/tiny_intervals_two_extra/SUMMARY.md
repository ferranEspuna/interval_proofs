# Two-extra verification, 2026-07-16--17

## Scope and acceleration

This directory contains the complete two-extra analogue of the one-extra scan:
the larger optimizing `q` branch for every `m=3,...,100`, plus the smaller
optimizing branch for every tied value `m=4,8,...,100`.  There are 123 runs.
All use anchor `0`, two arbitrary extra intervals, and a requested zero
relative MIP gap.

The first 44 models are unbounded apart from the model's generic interval
width bound: all larger branches through `m=43`, together with the tied smaller
branches at `m=4,8,12`.  Their command template is

```sh
.venv/bin/python equally_spaced_tiny_interval_lp.py \
    --m M \
    --tie-choice BRANCH \
    --anchor 0 \
    --extra-count 2 \
    --mip-rel-gap 0 \
    --require-success \
    --output-dir json_results/verification_20260716/tiny_intervals_two_extra
```

Unbounded solve time began growing sharply near `m=40`.  The remaining 79
models use an inductive per-extra upper bound equal to the corresponding saved
one-extra optimum: larger branches `m=44,...,100` and tied smaller branches
`m=16,20,...,100`.  This is a valid redundant cut within the saved one-extra
campaign, because deleting the other extra leaves a feasible one-extra
extension.  The continuation adds

```sh
--extra-length-bound G_M
```

where `G_M` is `2/[m^2(m+2)]` for larger `m=0 (mod 4)`,
`1/[m^2(m+2)]` for larger `m=1 (mod 4)`, and `0` on the tested
zero-gain branches.  `run_scan_m14-100.sh` retains the exact matrix and uses at
most two concurrent solvers.  The unbounded `m=44` and `m=46` cross-checks are
in the sibling `../tiny_intervals_two_extra_unbounded_crosschecks` directory.

All deterministic problem JSONs are gzip-compressed.  Saved solution metadata
uses repository-relative paths to the compressed problems.

## Results

All 123 canonical solutions report `success=true`,
`status_name="optimal"`, and stored `mip_gap=0`.  A positive gain above the
reporting tolerance `1e-9` occurs on the larger branch exactly for

```text
m = 4, 8, 9, 12, 13, 16, 17, ..., 96, 97, 100,
```

and on no tied smaller branch.  The total two-extra gains agree to within
`1.74e-11` with

```text
m = 4:                   1/192,
m = 8:                   1/320,
m = 9:                   1/891,
m = 0 (mod 4), m >= 12:  4/[m^2(m+2)],
m = 1 (mod 4), m >= 13:  2/[m^2(m+2)],
all other tested cases:   0.
```

For `m=4,8,9`, only one of the two extras is positive.  Beginning at `m=12`
on the positive congruence classes, both extras attain the one-extra optimum,
so the gain doubles.  `result_summary.json` and `result_summary.csv` contain
all per-case objectives, lengths, node counts, branch labels, formula errors,
and whether the inductive cut was used.

The first new constructions were rationalized exactly.  At `m=12`, the two
extras both have length `1/1008` and the total density is `73/504`; at `m=13`,
they both have length `1/2535` and the total density is `122/845`.  The central
checker `../higher_m_general_m11-13/verify_exact_constructions.py` verifies all
126 interactions in each construction with exact fractions.

## Numerical validation and preserved exceptions

`replay_saved_solutions.py` replays every canonical assignment against its
stored bounds and constraints.  The regenerated `replay_report.json` records
zero bound, integrality, and objective error; its maximum row violation is
`7.45e-10` (the zero-gain `m=43` run), below the reporting tolerance.

Three numerically noisy canonical cases were replaced only after preserving
their originals in `../tiny_intervals_two_extra_unbounded_crosschecks`:

- `m=34` and `m=40` were rerun without presolve, with
  `mip_abs_gap=0` and `mip_feasibility_tolerance=1e-10`.  Their strict replay
  has zero integrality violation and maximum row violation `1.33e-11`.
- At `m=100`, presolve stopped one extra exactly `1e-6` short.  A no-presolve
  rerun reaches both per-extra bounds with stored gap zero and row residual
  `1.94e-14`.  Both the presolve-on anomaly and the promoted no-presolve result
  are retained in the sibling directory.

The `m=100` behavior and a strict `m=34` diagnostic also exposed the relevance
of HiGHS' separate absolute MIP-gap tolerance.  Later saturation experiments
therefore request both relative and absolute MIP gaps equal to zero.
