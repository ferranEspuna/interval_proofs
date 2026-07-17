# Extra-count saturation campaign, 2026-07-17

## Scope and formulation

This campaign follows the first positive third intervals and asks how many
extra intervals can coexist around the fixed optimized equally spaced base.
Every model uses anchor `0`, the exact saved one-extra optimum as a per-extra
length bound, and explicitly requests both

```text
mip_rel_gap = 0
mip_abs_gap = 0
```

The initial matrix is retained in `run_saturation.sh`.  The larger follow-ups
use the valid `--ordered-extras` symmetry break and are reproducible with
`run_ordered_followups.sh`.  Filenames encode `m`, `q`, extra count, the exact
per-extra bound, whether ordered extras were used, and both zero-gap settings.
At most two runs are scheduled concurrently by the retained runners.

The per-extra bound is inductively valid: deleting all other extras leaves a
feasible one-extra extension of the fixed base.  Ordering extras is also
without loss because the extra intervals are otherwise exchangeable; it fixes
their left-to-right labels and removes their mutual order binaries.

All 18 retained solutions report `success=true`, `status_name="optimal"`, and
stored `mip_gap=0`.  Problem JSONs are deterministically gzip-compressed and
solution metadata uses repository-relative paths.

## Results

The following table gives the number of positive extras above `1e-9`.  A range
such as `K=4,5` means both models were solved and gave the listed best pattern.

| `m` | tested extra counts | positive extras at the largest tested `K` | lengths at the optimum | total density |
|---:|:---|---:|:---|:---|
| 12 | 4, 5 | 3 | `1/1008, 1/1008, 5/12096` | `251/1728` |
| 13 | 4, 5 | 2 | two copies of `1/2535` | `122/845` |
| 16 | 4, 5 | 4 | four copies of `1/2304` | `9/64` |
| 17 | 4, 5, 6 | 4 | four copies of `1/5491` | `769/5491` |
| 20 | 4, 5, 6, 7 | 6 | six copies of `1/4400` | `303/2200` |
| 21 | 4, 5, 6, 7 | 6 | six copies of `1/10143` | `464/3381` |

For `m=20,21`, every requested extra through `K=6` reaches the individual
upper bound, while `K=7` adds only a zero-length interval.  For `m=16`, all
four extras in `K=4` are full and the fifth is zero.  At `m=12`, the third
extra is genuinely positive but shorter than the first two; at `m=13`, even
five available extras produce only two positive components.

`result_summary.json` and `result_summary.csv` retain all 18 objectives,
ordered/unordered flags, individual lengths, positive and full-bound counts,
node counts, and solver options.

## Symmetry comparison

The unordered `m=16, K=5` model closed in 9:05 at 238,840 nodes.  The otherwise
equivalent ordered-extra model closed in 11.14 seconds at 3,873 nodes and
returned the same four-full-plus-one-zero pattern.  The ordered formulation
also closed the previously long follow-ups at 12,129 nodes (`m=12,K=5`), 8,506
(`m=13,K=5`), 22,904 (`m=17,K=6`), 39,295 (`m=20,K=7`), and 9,664
(`m=21,K=7`).  Incomplete logs from the stopped unordered attempts were
removed; the completed unordered `m=16,K=5` artifact is retained for the
direct comparison.

## Exact and floating-point validation

The central exact checker
`../higher_m_general_m11-13/verify_exact_constructions.py` verifies rational
open-interval certificates for the material constructions:

- `m=12`, three positives, density `251/1728` (196 triples);
- `m=16`, four full extras, density `9/64` (405 triples);
- `m=17`, four full extras, density `769/5491` (405 triples);
- `m=20`, six full extras, density `303/2200` (936 triples); and
- `m=21`, six full extras, density `464/3381` (936 triples).

All exact checks pass.  The generic saved-model replay covers all 18 numerical
solutions in `replay_report.json`: zero integrality and objective error,
maximum bound violation `1.33e-14`, and maximum row violation `7.33e-11`.
