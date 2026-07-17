# Computational verification campaign started 2026-07-16

This directory is the retained artifact set for the computational statements
in `latex/project_status.tex`.  The campaign started from Git commit
`07986a4b6c3ab83aa7de6c5da25fdf1842090dda` and used Python 3.12.3, NumPy
2.5.1, SciPy 1.18.0, and HiGHS 1.12.0.  Unless a run is explicitly identified
as a historical-tolerance comparison, optimization runs requested
`mip_rel_gap=0`; the later saturation and strict numerical checks also request
`mip_abs_gap=0`.  Bounded or inductively accelerated searches are identified
in their summaries.

| Directory | Scope | Completion status |
|:---|:---|:---|
| `m3_full/` | full `m=3` finite-union checks | direct zero-gap runs complete for `N=1,...,6`; the zero-gap `N=7` run uses the saved six-subunion bound; see its summary for `N=8` |
| `m3_lp_relaxation/` | continuous-lift relaxation for `m=3,N=1,...,8`, with and without width cuts | complete, 16 LPs; optimum `min(N/5,1)` |
| `m3_profile_32/` | all 32 legal cut/formulation configurations for `m=3,N=5` | full zero-gap reproduction of the historical profiling matrix |
| `removable_interactions/` | translated-model redundant-interaction search | exhaustive for `N=2,3`; capped/timeout-bounded for `N=4,5` |
| `removable_interactions_subset_bound/` | historical redundant-interaction variant with the `(N-1)`-subset bound | exhaustive for `N=2,3`; historically capped/timeout-bounded for `N=4,5` |
| `higher_m_general/` | unrestricted `N=5`, `m=4,...,10`, plus `m=5,N=6` | complete, all zero reported gap |
| `higher_m_general_m11-13/` | unrestricted lower-`N` checkpoints and `N=5` for `m=11,12,13` | six runs complete and replayed; direct unrestricted `m=12,13,N=6` jobs handed off while still running |
| `higher_m_general_m11-13_subset_bound/` | `m=12,13,N=6` with saved five-subunion bounds and known-construction cutoffs | runs in progress; no result is claimed yet |
| `two_interval_scan/` | unrestricted `N=2`, `m=4,...,100` | complete, all zero reported gap |
| `two_interval_scan_strict/` | strict-tolerance replay of the marginal `m=87,N=2` point | complete, exact rational reconstruction feasible |
| `tiny_intervals/` | equally spaced base plus one variable interval, `m=3,...,100` and both tied branches | complete, 123 zero-gap runs |
| `tiny_intervals_two_extra/` | fixed equally spaced base plus two arbitrary extras, `m=3,...,100` and both tied branches | complete, 123 canonical zero-gap runs; exact new constructions begin at `m=12` |
| `tiny_intervals_two_extra_unbounded_crosschecks/` | unbounded, no-presolve, and strict numerical variants for selected two-extra cases | complete, ten preserved variants and replay report |
| `tiny_intervals_two_extra_exact/` | exact reconstruction of every positive one- and two-extra output | complete, all 48 positive two-extra cases pass |
| `tiny_intervals_three_extra/` | bounded third-extra threshold checks at `m=8,9,12,13,16,17` | complete, eight zero-gap runs; first positive third extra at `m=12` |
| `tiny_intervals_three_extra_exact/` | exact reconstruction of the positive three-extra checks | complete, 898 lifted images and saved lifts pass |
| `tiny_intervals_extra_count_saturation/` | bound-assisted extra-count checks through `K=5,6,7` at `m=12,13,16,17,20,21` | complete, 18 runs with both relative and absolute gaps requested zero |
| `tiny_intervals_mod0_doubled_tail_exact/` | exact doubled-tail family for `m=0 mod 4`, `m=16,...,100` | complete, 22 cases and 1,236,906 lifted images pass |
| `tiny_intervals_mod1_full_family_exact/` | exact requested and doubled-tail families for `m=1 mod 4` through `m=97` | complete, including 1,047,816 lifted images for the stronger family |

Each subdirectory contains or is accompanied by a `SUMMARY.md` describing its
commands, settings, results, and limitations.  Standard MILP directories keep
serialized problem and solution pairs.  The much larger deterministic problem
JSON files in the tiny-interval campaigns are gzip-compressed; their solution
JSON and console logs remain plain text.  Saved problem/solution links in the
new campaign directories are repository-relative.

“Zero reported gap” means that HiGHS returned equal floating-point primal and
dual objectives.  It is strong reproducible numerical evidence, not an exact
rational branch certificate.  The LaTeX text retains that distinction.  Exact
open-interval lower-bound certificates extracted from the material
`m=12,13,16,17,20,21` constructions are checked by
`higher_m_general_m11-13/verify_exact_constructions.py`.
