# Exact multi-extra families for `m = 1 (mod 4)`

`verify_mod1_full_family.py` performs exact `fractions.Fraction` checks for two
explicit families based on the larger optimizing equally spaced block.  It
checks interval geometry and every lifted image `I_i+I_j-mI_ell`; it makes no
optimality claim.

Write

```text
q = (m+3)/4,
delta = (m+1)/(2m(m+2)),
a = -m delta/(m-2) (mod 1),
b = a+1/m (mod 1),
g = 1/(m^2(m+2)).
```

## Requested family

For `j=1,...,(m-5)/4`, add an interval of length `g` at

```text
s_j = b - (m-(4j+1))/(4m^2).
```

This gives

```text
extra count = (m-5)/4,
total interval count = (m-1)/2,
gain = (m-5)/(4m^2(m+2)),
density = (m-1)(m^2+5m+10)/(8m^2(m+2)).
```

The family passes exactly for all 23 values `m=9,13,...,97`, covering 369,794
lifted images.  For `m=4k+1`, the verifier also confirms

```text
triple count = 2k^2(2k+1),
zero endpoint slacks = (k^2+5k+2)/2,
minimum positive endpoint slack = (m+1)/(2m^2).
```

This family is not saturating once `m>=17`: the exact constructions below add
more intervals of the same length.

## Stronger doubled-tail family

For `m>=13`, discard `s_1`, retain the tail `s_2,...,s_(m-5)/4`, and add both
the tail and its translate by `1/m`.  This gives

```text
extra count = (m-9)/2,
total interval count = 3(m-5)/4,
gain = (m-9)/(2m^2(m+2)),
density = (m^3+4m^2+7m-36)/(8m^2(m+2)).
```

This stronger family passes exactly for all 22 values `m=13,17,...,97`,
covering 1,047,816 lifted images.  If `m=4k+1`, its total interval count is
`3(k-1)`, its zero-slack count is `k(k+1)`, and its minimum positive endpoint
slack is again `(m+1)/(2m^2)`.

The tested range is finite and the construction is only a lower bound.  In
particular, these checks do not assert that `(m-9)/2` is the maximum possible
number of useful extras for any later `m`.

## Per-value exact results

Here `K` is the extra count and `N` the total interval count.

| `m` | requested `K / N / triples` | requested density | doubled `K / N / triples` | doubled density |
|---:|---:|---:|---:|---:|
| 9 | 1 / 4 / 40 | `136/891` | -- | -- |
| 13 | 2 / 6 / 126 | `122/845` | 2 / 6 / 126 | `122/845` |
| 17 | 3 / 8 / 288 | `768/5491` | 4 / 9 / 405 | `769/5491` |
| 21 | 4 / 10 / 550 | `1390/10143` | 6 / 12 / 936 | `464/3381` |
| 25 | 5 / 12 / 936 | `152/1125` | 8 / 15 / 1800 | `761/5625` |
| 29 | 6 / 14 / 1470 | `3486/26071` | 10 / 18 / 3078 | `3490/26071` |
| 33 | 7 / 16 / 2176 | `5056/38115` | 12 / 21 / 4851 | `241/1815` |
| 37 | 8 / 18 / 3078 | `2346/17797` | 14 / 24 / 7200 | `2348/17797` |
| 41 | 9 / 20 / 4200 | `9480/72283` | 16 / 27 / 10206 | `9487/72283` |
| 45 | 10 / 22 / 5566 | `2486/19035` | 18 / 30 / 13950 | `1382/10575` |
| 49 | 11 / 24 / 7200 | `5312/40817` | 20 / 33 / 18513 | `5315/40817` |
| 53 | 12 / 26 / 9126 | `20046/154495` | 22 / 36 / 23976 | `20056/154495` |
| 57 | 13 / 28 / 11368 | `24808/191691` | 24 / 39 / 30420 | `8273/63897` |
| 61 | 14 / 30 / 13950 | `10090/78141` | 26 / 42 / 37926 | `1442/11163` |
| 65 | 15 / 32 / 16896 | `7296/56615` | 28 / 45 / 46575 | `36493/283075` |
| 69 | 16 / 34 / 20230 | `43486/338031` | 30 / 48 / 56448 | `14500/112677` |
| 73 | 17 / 36 / 23976 | `17112/133225` | 32 / 51 / 67626 | `17117/133225` |
| 77 | 18 / 38 / 28158 | `60078/468391` | 34 / 54 / 80190 | `60094/468391` |
| 81 | 19 / 40 / 32800 | `69760/544563` | 36 / 57 / 94221 | `7753/60507` |
| 85 | 20 / 42 / 37926 | `5362/41905` | 38 / 60 / 109800 | `26816/209525` |
| 89 | 21 / 44 / 43560 | `92136/720811` | 40 / 63 / 127008 | `13165/102973` |
| 93 | 22 / 46 / 49726 | `104926/821655` | 42 / 66 / 145926 | `34982/273885` |
| 97 | 23 / 48 / 56448 | `39616/310497` | 44 / 69 / 166635 | `39623/310497` |

## Comparison with saved optimization artifacts

The verifier compares 49 zero-gap prefix artifacts: all saved `K=1` and `K=2`
runs for `m=9,13,...,97`, plus the available `K=3` runs for `m=9,13,17`.
Their objectives agree with the appropriate exact prefix density to within
`6.61e-12`.

The emerging saturation artifacts are also linked and reconstructed in the
JSON report.  In particular:

- `m13_q4_extra4_per_extra_bound_1over2535_relgap0_absgap0_solution.json` has
  two full-`g` extras, zero/dust in the other variables, and exact density
  `122/845` after rational reconstruction.  The ordered `K=5` successor still
  has only two positive extras.
- `m17_q5_extra4_per_extra_bound_1over5491_relgap0_absgap0_solution.json` has
  four full-`g` extras and exact density `769/5491`, matching the doubled-tail
  count and density.  The corresponding `K=5` artifact adds no fifth positive
  interval.
- `m21_q6_extra6_per_extra_bound_1over10143_relgap0_absgap0_solution.json` is
  exactly the six-extra doubled-tail family and has density `464/3381`; its
  ordered `K=7` successor has no seventh positive extra.

All paths in `exact_verification_report.json` are repository-relative.  The
report also records every exact interval endpoint, per-case slack statistics,
all saved-prefix comparisons, and exact reconstructions of the `m=13,17,21`
saturation constructions.

## Reproduction

```bash
python3 json_results/verification_20260716/tiny_intervals_mod1_full_family_exact/verify_mod1_full_family.py
```
