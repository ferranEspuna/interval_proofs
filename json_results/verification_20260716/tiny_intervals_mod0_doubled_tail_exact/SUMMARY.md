# Exact doubled-tail family for `m = 0 (mod 4)`

`verify_mod0_doubled_tail.py` verifies an exact analogue of the residue-1
doubled-tail construction.  It checks interval geometry and every lifted image
with `fractions.Fraction`; it makes no optimality claim.

For the larger optimizing block, write

```text
q = m/4+1,
delta = 1/(2(m+2)),
a = -m delta/(m-2) (mod 1),
b = a+1/m (mod 1),
g = 2/(m^2(m+2)).
```

Define

```text
s_j = b-(m-4j)/(4m^2),    1 <= j <= (m-4)/4.
```

Retain the tail `j=2,...,(m-4)/4` and add an interval of length `g` at both
`s_j` and `s_j+1/m`.  The resulting construction has

```text
extra count = (m-8)/2,
total interval count = 3(m-4)/4,
gain = (m-8)/(m^2(m+2)),
density = (m^3+4m^2+8m-64)/(8m^2(m+2)).
```

The family passes exactly for every `m=16,20,...,100`: 22 cases and 1,236,906
lifted images.  If `m=4k`, the verifier also confirms

```text
total interval count = 3(k-1),
zero endpoint slacks = k(k+1),
minimum positive endpoint slack = 1/(2m).
```

The tested range is finite.  These are exact lower-bound constructions, not a
claim that `(m-8)/2` is the maximum possible extra count.

## Per-value exact results

Here `K` is the extra count and `N` is the total interval count.

| `m` | `K` | `N` | lifted images | exact density |
|---:|---:|---:|---:|---:|
| 16 | 4 | 9 | 405 | `9/64` |
| 20 | 6 | 12 | 936 | `303/2200` |
| 24 | 8 | 15 | 1800 | `127/936` |
| 28 | 10 | 18 | 3078 | `263/1960` |
| 32 | 12 | 21 | 4851 | `579/4352` |
| 36 | 14 | 24 | 7200 | `1627/12312` |
| 40 | 16 | 27 | 10206 | `23/175` |
| 44 | 18 | 30 | 13950 | `2913/22264` |
| 48 | 20 | 33 | 18513 | `1877/14400` |
| 52 | 22 | 36 | 23976 | `527/4056` |
| 56 | 24 | 39 | 30420 | `1473/11368` |
| 60 | 26 | 42 | 37926 | `7213/55800` |
| 64 | 28 | 45 | 46575 | `1453/11264` |
| 68 | 30 | 48 | 56448 | `10419/80920` |
| 72 | 32 | 51 | 67626 | `1541/11988` |
| 76 | 34 | 54 | 80190 | `4819/37544` |
| 80 | 36 | 57 | 94221 | `8409/65600` |
| 84 | 38 | 60 | 109800 | `19423/151704` |
| 88 | 40 | 63 | 127008 | `619/4840` |
| 92 | 42 | 66 | 145926 | `25413/198904` |
| 96 | 44 | 69 | 166635 | `14411/112896` |
| 100 | 46 | 72 | 189216 | `10841/85000` |

## Saturation comparisons and the `m=12` exception

The zero-gap `m=16`, `K=4` artifact has four full-`g` extras and exact measure
`9/64`; its `K=5` successor has no fifth positive interval.  The zero-gap
`m=20`, `K=6` artifact has six full-`g` extras and exact measure `303/2200`.
Exact rational reconstructions of both solver constructions are included in
the report, along with repository-relative paths to the `K=4,5,6` artifacts.

The pattern deliberately starts at `m=16`.  At `m=12`, the same doubled-tail
recipe gives only the two full extras, whereas the exact `K=3` construction has
two intervals of length `1/1008` and a third of length `5/12096`.  Thus `m=12`
is an explicit exception to the equal-length count formula.

`exact_verification_report.json` records every rational interval endpoint,
per-case slack statistics, exact saturation reconstructions, and only
repository-relative artifact paths.

## Reproduction

```bash
python3 json_results/verification_20260716/tiny_intervals_mod0_doubled_tail_exact/verify_mod0_doubled_tail.py
```
