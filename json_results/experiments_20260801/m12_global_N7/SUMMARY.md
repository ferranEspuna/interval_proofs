# Unrestricted `m=12`, `N=7` investigation, 2026-08-01

## Conclusion

The completed all-endpoints-free audit has a zero-gap numerical optimum

```text
M_7(12) = 251/1728 = 0.1452546296296296...
```

among unions of at most seven intervals.  This is not merely optimal relative
to the fixed equally spaced base: all seven starts and lengths were variables.
An exhaustive 30-case length-order partition closed with four optimal cases at
this value and 26 cases infeasible above the known-construction cutoff.

The upper-bound conclusion is **conditional** on treating the numerical
smaller-component results below as valid subset bounds, and on the usual
floating-point MILP computation.  Those bounds have matching exact
constructions and zero reported MIP gaps, but no checkable exact branch
certificates.  Therefore the audit is strong numerical evidence for the full
seven-interval statement, not an unconditional exact theorem.  The exact
`251/1728` construction and its lower bound do not depend on this caveat.

## Completed exhaustive length-order audit

The memory-safe formulation uses a variable missing point, puts a globally
shortest interval at positional index 0, and applies the reflection convention
`alpha_1 <= alpha_6`.  It then chooses, in order, the indices of a shortest
remaining interval and a shortest interval after that.  The `6*5=30` ordered
prefixes cover every length ordering.  Equal lengths make cases overlap, but
cannot leave a gap in the partition.

Every case used free endpoints and lengths, the exact lower-bound cutoff
`sum(alpha) >= 251/1728`, and the subset bounds for sizes 2 through 6.  The
final result is:

| outcome | prefixes | count |
|:---|:---|---:|
| zero-gap optimal at `251/1728` | `(1,3)`, `(1,5)`, `(3,1)`, `(5,1)` | 4 |
| infeasible at or above the cutoff | every other ordered prefix | 26 |

Here `infeasible` is a successful upper-bound result: it means that ordering
class contains no construction of length at least `251/1728` under the stated
subset bounds, not that the class contains no sum-free construction at all.
The four optimal prefixes are overlapping representations caused by equal
component lengths and reflection.  Each has length multiset

```text
4 copies of 1/28, 2 copies of 1/1008, and 1 copy of 5/12096.
```

The final attempts processed 42,749,286 branch-and-bound nodes in 121,154.13
aggregate solver-seconds (33.65 hours).  No final case hit its time or node
limit.  The 30 log/problem/solution triples and a directory-level result index
are under `json_results/long_runs/m12_N7_length_order_depth2/`.  Recheck their
status with:

```sh
.venv/bin/python \
  json_results/experiments_20260801/m12_global_N7/summarize_length_order_cases.py
```

## Smaller-component constraints

The unrestricted saved computations used to strengthen `N=7` are:

| allowed components | numerical optimum | archived status |
|---:|:---|:---|
| 2 | `5/42` | zero gap, 13 nodes |
| 3 | `1/7` | squeezed between the explicit three-interval base and the `N=4` upper bound |
| 4 | `1/7` | zero gap, 15,031 nodes |
| 5 | `145/1008` | zero gap, 103,007 nodes |
| 6 | `73/504` | zero gap, 1,892,013 nodes in the unrestricted run |

The `N=4,5,6` artifacts are under
`json_results/verification_20260716/higher_m_general_m11-13/`; the `N=2`
artifact is under `two_interval_scan/`.  A second `N=6` run with the `N=5`
subset bound and the known-construction cutoff also closed at `73/504`
numerically (2,984,522 nodes).

Every subset-strengthened `N=7` run used candidate subset inequalities for
sizes 2 through 6, obtained by treating the displayed numerical
reconstructions as upper bounds, and the known-construction cutoff
`sum(alpha_i) >= 251/1728`.  At that cutoff, the three strongest complement
inequalities say

```text
every one interval  >= 251/1728 - 73/504  =  5/12096,
every two intervals >= 251/1728 - 145/1008 = 17/12096,
every three intervals >= 251/1728 - 1/7    = 29/12096.
```

The candidate saturates all three with short lengths `5/12096`, `1/1008`,
and `1/1008`, since these have numerators `5,12,12` over `12096`.

These smaller-`N` upper bounds are floating-point zero-gap MILP results, not
formal exact upper-bound certificates.  Their rational values are supported
by exact matching constructions, but the distinction matters even for the
interpretation of the `N=7` experiment.  In particular, the saved direct
`N=6` assignment has objective `0.14484130121147112`, about `3.14e-8` above
`73/504`, together with a `5.65e-7` row residual.  This is consistent with
solver feasibility noise, but imposing the slightly smaller rational value
`73/504` is still a numerical hypothesis rather than a certified-valid cut.

## Candidate validation

The optimal `(1,5)` final case reconstructs in ordinary, zero-missing-point
coordinates to

```text
(169/5040, 29/840)       length 1/1008
(17/420,   8/105)        length 1/28
(23/280,   4993/60480)   length 5/12096
(589/5040, 33/280)       length 1/1008
(13/105,   67/420)       length 1/28
(29/140,   17/70)        length 1/28
(67/70,    139/140)      length 1/28
```

The solver used translated coordinates with exact missing point `t=23/28`;
adding `t/(12-2)=23/280` to every start gives the representative above.  The
exact checker `verify_unrestricted_incumbent_exact.py` verifies all 196 lifted
interactions of the ordinary construction and all 196 saved integer lifts in
the final solver fixture with `fractions.Fraction`.  It finds 14 tight endpoint
inequalities and minimum positive endpoint slack `1/144`.  Its output is
`unrestricted_incumbent_exact_report.json`.  A checked shareable state is the
[exceptional seven-interval construction in the visualizer catalog](../../../VISUALIZER_LINKS.md).

```sh
.venv/bin/python \
  json_results/experiments_20260801/m12_global_N7/verify_unrestricted_incumbent_exact.py
```

## Why the fractional extra is selected only at `m=12`

For `m = 0 (mod 4)`, there are two exact competing fixed-base patterns:

```text
regular doubled-tail gain = (m-8)/(m^2(m+2)),
hybrid gain               = (m^2-2m-4)/(2m^3(m+2)).
```

The hybrid has a short interval

```text
h = (m-2)/(m^3(m+2)),       h/g = (m-2)/(2m),
```

where `g=2/(m^2(m+2))` is a full-extra length.  Two tight lifted images fix
the two endpoints of this short suffix.  The exact advantage of the hybrid
over the regular doubled tail is

```text
(-m^2 + 14m - 4)/(2m^3(m+2)).
```

This is positive at `m=12`, where it equals `5/12096`, and negative for every
`m >= 16`; its positive real range ends at `7+3 sqrt(5)`.  At `m=16`, for
example, the hybrid trades one full interval for the shorter suffix and loses
`1/4096`, so the regular all-full pattern wins.

`analyze_m12_hybrid.py` checks the hybrid exactly for all 23 values
`m=12,16,...,100` (468,257 lifted interactions).  Hence the fractional short
interval does not literally cease to be feasible after `m=12`; rather,
`m=12` is the only tested multiple of four where selecting that hybrid branch
beats the regular family.  This explains the observed anomaly inside these
families, but it is not a proof that no unrelated construction can do better.
