# Unrestricted higher-multiplier verification

This directory contains standard-formulation runs of `circle_intervals.py` for
`m = 4,...,10` with `N = 5`, together with the additional `m = 5`, `N = 6`
run.  Each run used the command template

```bash
.venv/bin/python circle_intervals.py -N <N> --m <m> \
  --mip-rel-gap 0 --require-success \
  --output-dir json_results/verification_20260716/higher_m_general \
  --run-name m<m>_N<N>_standard_gap0
```

Thus all runs used the original (non-translated) formulation, no width cuts,
the default monotonicity cuts, the default endpoint-length cut, and
`epsilon = 0`.  The saved solution JSON confirms those settings.  Every run
returned `success = true`, equal primal and dual values at the precision
reported by HiGHS, and zero MIP gap.

| m | N | optimum (rational reconstruction) | reported optimum = dual bound | MIP gap | nodes | positive intervals |
|---:|---:|---:|---:|---:|---:|---:|
| 4 | 5 | `11/64` | `0.17187500000010916` | 0 | 28,570 | 3 |
| 5 | 5 | `6/35` | `0.17142857142860901` | 0 | 58,931 | 2 |
| 6 | 5 | `1/6` | `0.16666666666668328` | 0 | 47,116 | 3 |
| 7 | 5 | `10/63` | `0.15873015873023799` | 0 | 63,915 | 2 |
| 8 | 5 | `49/320` | `0.15312500000000850` | 0 | 79,823 | 4 |
| 9 | 5 | `136/891` | `0.15263748597082175` | 0 | 87,978 | 4 |
| 10 | 5 | `3/20` | `0.15000000000007588` | 0 | 103,362 | 3 |
| 5 | 6 | `6/35` | `0.17142857142868084` | 0 | 398,263 | 4 |

## Supplementary lower-N cross-checks

The directory also retains lower-`N` runs made while identifying the smallest
component count at which the structures above appear.  They used the same
standard formulation and zero-gap command template.

| m | N | reported objective | MIP gap | nodes |
|---:|---:|---:|---:|---:|
| 4 | 2 | `0.16666666666666696` | 0 | 17 |
| 4 | 3 | `0.17187500000000092` | 0 | 165 |
| 5 | 2 | `0.17142857142857648` | 0 | 11 |
| 5 | 3 | `0.17142857142857243` | 0 | 194 |
| 6 | 2 | `0.16666666666667437` | 0 | 8 |
| 6 | 3 | `0.16666666666667174` | 0 | 330 |
| 7 | 2 | `0.15873015873015883` | 0 | 10 |
| 7 | 3 | `0.15873015873015930` | 0 | 320 |
| 8 | 2 | `0.15000000000000030` | 0 | 13 |
| 8 | 4 | `0.15312500000000010` | 0 | 7,008 |
| 9 | 2 | `0.14141414141414300` | 0 | 9 |
| 9 | 4 | `0.15263748597081970` | 0 | 6,972 |
| 10 | 2 | `0.13333333333333697` | 0 | 11 |
| 10 | 4 | `0.15000000000000710` | 0 | 9,544 |

In particular, the gain is already present with three allowed intervals for
`m=4`, and with four allowed intervals for `m=8,9`.  The `N=5` runs remain the
uniform comparison across all seven multipliers.

The positive intervals, after rational reconstruction of the numerical
endpoints, are:

- `m=4, N=5`: `(1/3,5/12)`, `(91/192,23/48)`,
  `(7/12,2/3)`.  This is the two-component equally spaced base plus the
  interval of width `1/192`, with total measure `11/64`.
- `m=5, N=5`: `(4/21,29/105)`, `(41/105,10/21)`, both of width `3/35`.
- `m=6, N=5`: `(1/24,1/8)`, `(7/8,67/72)`,
  `(67/72,23/24)`.  The last two pieces have widths `1/18` and `1/36` and
  split one width-`1/12` base component at a common endpoint.
- `m=7, N=5`: `(13/45,116/315)`, `(136/315,23/45)`, both of width `5/63`.
- `m=8, N=5`: `(7/120,13/120)`, `(29/240,119/960)`,
  `(11/60,7/30)`, `(14/15,59/60)`.  Three intervals have width `1/20`
  and form the equally spaced base; the fourth has width `1/320`.
- `m=9, N=5`: `(39/77,386/693)`, `(428/693,463/693)`,
  `(4237/6237,4244/6237)`, `(505/693,60/77)`.  Three intervals have
  width `5/99` and form the equally spaced base; the fourth has width
  `1/891`.
- `m=10, N=5`: `(5/16,29/80)`, `(33/80,37/80)`, `(41/80,9/16)`, all
  of width `1/20` and spaced by `1/10`.
- `m=5, N=6`: `(2/21,29/210)`, `(41/210,5/21)`,
  `(25/42,67/105)`, `(73/105,31/42)`, all of width `3/70`.  This is the
  reported four-positive-interval split of density `6/35`; the starting
  points have alternating gaps `1/10` and `2/5`.  The other two allowed
  intervals have zero width.

For each stem, `_problem.json` contains the full MILP and `_solution.json`
contains the solution, solver diagnostics, and visualizer state.  The
rational values above are reconstructions of the floating-point solutions;
zero numerical MIP gap is strong computational evidence, not by itself an
exact rational certificate.

## Exact construction replay

The companion script `verify_rational_constructions.py` checks the recovered
positive intervals for `m=4`, both `m=5` forms, `m=8`, and `m=9` using exact
`fractions.Fraction` arithmetic.  For every pair `i <= j` and every `ell`, it
verifies that the open real interval

```text
(a_i + a_j - m b_ell, b_i + b_j - m a_ell)
```

contains no integer.  It also checks ordering, disjointness, endpoints, and
the exact total measure.  The checks cover respectively 18, 6, 40, 40, and 40
interaction triples and all pass.  In particular, the reconstructed `m=8`
and `m=9` points are exact constructions proving

```text
d_8(T) >= 49/320,     d_9(T) >= 136/891.
```

This upgrades the lower bounds supplied by those two points; it does not
upgrade the numerical claim that the saved `N=5` MILPs are optimal.
