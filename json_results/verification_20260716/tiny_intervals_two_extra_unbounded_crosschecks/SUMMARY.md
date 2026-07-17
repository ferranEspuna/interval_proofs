# Two-extra numerical and unbounded cross-checks, 2026-07-17

This directory preserves every variant used to audit the complete two-extra
scan without overwriting a canonical stem.

## Unbounded checks above the cut threshold

The fully unbounded standard model was rerun at `m=44` (positive branch) and
`m=46` (zero-gain branch), with `--mip-rel-gap 0` and no per-extra length cut.
The commands and resource use are in `m44_larger_unbounded_extra2.log` and
`m46_larger_unbounded_extra2.log`.

- `m=44` returns two positive extras, each equal to `1/44528` up to
  `4e-12`, matching the cut-assisted result.  It closed after 63,764 nodes.
- `m=46` returns gain `6.67e-10`, below the `1e-9` reporting tolerance, and
  closed after 84,977 nodes.  This matches the reported zero-gain branch.

These runs confirm both a positive and a zero case immediately beyond the
point where the main campaign began using the inductive per-extra cut.

## Preserved numerical variants

The original canonical presolve-on artifacts for `m=34`, `m=40`, and `m=100`
are retained with names ending in `presolve_on_anomalous`.  Their clean
replacements are also retained here:

- The first no-presolve `m=40` run reduced the maximum row residual from
  `1.41e-9` to `5.39e-11`.
- A no-presolve `m=100` run with the inductive bound placed both extras exactly
  at `1/510000`, closed with gap zero in 46 nodes, and had maximum row residual
  `1.94e-14`.  The presolve-on variant had stopped one extra exactly `1e-6`
  short.
- A no-presolve-only `m=34` diagnostic was worse: HiGHS accepted an integer
  and row residual around `2.03e-7`.  This file is deliberately retained as a
  diagnostic, not promoted.

The final strict `m=34` and `m=40` variants use all of

```text
presolve = false
mip_rel_gap = 0
mip_abs_gap = 0
mip_feasibility_tolerance = 1e-10
```

Both close with stored gap zero and zero integrality violation.  Their maximum
row violations are respectively `1.33e-11` and `9.10e-12`.  These strict pairs
were promoted into the canonical 123-case scan only after the originals were
preserved here.

The failed strict-feasibility-only diagnostic log shows why the absolute gap
matters: with `mip_rel_gap=0` but the default absolute MIP gap, HiGHS stopped
the `m=34` model at relative gap `2.57e-7` because the remaining absolute
objective gap was below its separate threshold.

## Artifacts and replay

`run.sh`, `run_numerical_crosschecks.sh`, and `run_strict_crosschecks.sh`
retain the exact commands.  Problem JSONs are deterministically compressed and
solution metadata uses repository-relative paths.  `replay_crosschecks.py`
produces `replay_report.json` for all ten stored solution variants.  Across the
two promoted strict cases it records zero bound, integrality, and objective
error and maximum row violation `1.33e-11`.
