# Tiny-interval verification, 2026-07-16

## Scope and commands

The one-extra-interval scan used the fixed anchor representative `0`, one
variable extra interval, and an explicit zero relative MIP gap.  For every
`M` from 3 through 100, the command was

```sh
.venv/bin/python equally_spaced_tiny_interval_lp.py \
    --m M \
    --tie-choice larger \
    --anchor 0 \
    --extra-count 1 \
    --mip-rel-gap 0 \
    --output-dir json_results/verification_20260716/tiny_intervals \
    --require-success
```

Standard output and error from each invocation were redirected to
`scan_m${M}_tie_larger_anchor0_extra1.log`; the independent invocations were
scheduled two at a time with `xargs -P2`.  This does not change their solver
options.  The environment was Python 3.12.3, NumPy 2.5.1, SciPy 1.18.0, and
the bundled HiGHS 1.12.0.

When `M` is one of `4, 8, ..., 100`, the density-maximizing value of `q` is
not unique.  The second branch was run by replacing `--tie-choice larger`
with `--tie-choice smaller`.  Thus there are 98 larger-choice runs and 25
additional smaller-choice runs.

The anchor classes are not separate cases: changing the anchor translates
the set by an integer multiple of `1/(m-2)`, under which
`A+A-mA` is translated by an integer.  The classes therefore have the same
one-extra-interval optimum, and anchor `0` is a complete representative.

Each run saved its full problem JSON, solution JSON, and console log in this
directory.  The deterministic problem files were subsequently gzip-compressed
and the `problem_json_path` entries in all 123 solutions were updated to the
resulting `.json.gz` paths.  Filenames encode `m`, the actual `q`, anchor, and
extra count.

## Results

All 123 runs returned `status_name = "optimal"`, `success = true`, and an
actual HiGHS `mip_gap` of exactly zero.

For the larger optimizing choice of `q`, a positive gain greater than the
reporting tolerance `1e-9` occurs exactly for

```text
m = 4, 8, 9, 12, 13, 16, 17, ..., 96, 97, 100,
```

equivalently `m = 0 or 1 (mod 4)`, with `m=5` excluded.  There are no
discrepancies from that congruence claim.  Numerically, the gains agree to
within `2e-11` with

```text
m = 4:                  1/192,
m = 0 (mod 4), m >= 8: 2/[m^2(m+2)],
m = 1 (mod 4), m >= 9: 1/[m^2(m+2)],
all other tested m:     0.
```

There is one qualification at the tied values `m = 0 (mod 4)`: the smaller
maximizing branch `q=m/4` has zero gain in every run, while the larger branch
`q=m/4+1` has the positive gain above.  Consequently, the congruence claim
describes the larger/default optimized base, not every equally dense choice
of `q`.

An independent replay of every stored variable assignment against its
stored bounds and constraints found zero bound and integrality violation.
The largest floating-point constraint residual was
`2.43e-11`; the stored objective values matched exactly.  The reproducible
checker is `replay_saved_solutions.py`, and its per-file machine-readable
output is retained as `replay_report.json`.

## Two- and three-extra follow-ups

The complete two-extra analogue now appears in the sibling directory
`../tiny_intervals_two_extra`: 98 larger-choice runs for `m=3,...,100` and 25
tied smaller-choice runs.  Its `SUMMARY.md`, machine-readable result tables,
and replay report supersede the earlier `m<=10` pilot.

The pilot's conclusion holds only through `m=9`.  Beginning at `m=12` on the
positive congruence classes, two extra intervals can both attain the one-extra
gain.  The bounded three-extra threshold check is retained in
`../tiny_intervals_three_extra`, and the larger extra-count saturation campaign
is in `../tiny_intervals_extra_count_saturation`.
