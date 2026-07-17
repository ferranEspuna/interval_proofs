# Removable-interaction search with the \(N-1\) subset bound

This directory reproduces the historical translated-symmetry experiment in
which every \((N-1)\)-subset of interval lengths is additionally constrained
to have total length at most \(1/5\).

## Historical provenance

The removed artifact was recovered from commit `883d32b` as
`json_results/maximal_excludable_triples_d3_N2-5_subsetNminus1le0p2.txt`.
Its companion exhaustive \(N=2,3\) report was
`json_results/maximal_excludable_triples_d3_N2-3_complete_subsetNminus1le0p2.txt`.
Commit `3a67946` subsequently removed both files. In the parts relevant to
this search, the current search driver changes the `d` terminology to `m` and
adds clearer partial-search warnings.

## Fixed settings

- \(m=3\), target bound \(1/5\), and zero epsilon;
- translated missing-point formulation;
- first interval shortest and second interval no longer than the last;
- width and lift-monotonicity cuts enabled, endpoint-length cut disabled;
- the \((N-1)\)-subset alpha bound set to \(1/5\);
- HiGHS relative MIP gap set to zero.

## Fresh results

| \(N\) | all triples | singleton-removable | maximal families retained | family sizes | exhaustive? |
|---:|---:|---:|---:|:---|:---|
| 2 | 6 | 2 | 2 | 1, 1 | yes |
| 3 | 18 | 7 | 7 | 3, 3, 3, 3, 3, 4, 4 | yes |
| 4 | 40 | 16 | 5 | 7, 7, 7, 7, 8 | no: stopped at five families |
| 5 | 75 | 32 | 0 | none found before timeout | no: timed out |

The full-model optima for \(N=2,3,4,5\) were respectively
`0.20000000000000004`, `0.20000000000000118`, `0.2000000000000049`, and
`0.2000000000000054`, with the requested zero relative MIP gap.

The \(N=2,3\) family lists exactly match the old exhaustive report. The five
fresh \(N=4\) families also exactly match the old capped report. The \(N=5\)
run reproduced the old counts of 32 singleton-removable triples and zero
families before timeout. It completed 81 solves in 1919.739 seconds, versus 85
solves in 1086.383 seconds historically; that difference is expected from a
wall-clock cutoff checked between solves and does not change any reported
family or singleton count. Every family listed by a partial run is checked to
be maximal relative to the complete set of singleton-removable candidates;
the cap only prevents a claim that all maximal families were enumerated.

Exhaustive \(N=4,5\) family enumeration was not attempted after the singleton
phase: there are respectively 16 and 32 singleton-removable candidates in the
historical run, hence up to \(2^{16}\) and \(2^{32}\) candidate subsets, and the
old campaign itself retained only a five-family / 120-second bounded search.
The `--search-time-limit` begins only after all singleton exclusions have been
solved. A single MILP already in progress is allowed to finish, so wall time
may exceed 120 seconds.

## Exact commands

```sh
.venv/bin/python find_excludable_sum_free_triples.py \
  --n-values 2,3 --m 3 --target-bound 0.2 \
  --n-minus-one-alpha-bound 0.2 \
  --width-cuts --monotonicity-cuts --mip-rel-gap 0 \
  --output-txt json_results/verification_20260716/removable_interactions_subset_bound/maximal_excludable_triples_m3_N2-3_exhaustive.txt
```

```sh
.venv/bin/python find_excludable_sum_free_triples.py \
  --n-values 4 --m 3 --target-bound 0.2 \
  --n-minus-one-alpha-bound 0.2 \
  --width-cuts --monotonicity-cuts --mip-rel-gap 0 \
  --max-families 5 --search-time-limit 120 \
  --output-txt json_results/verification_20260716/removable_interactions_subset_bound/maximal_excludable_triples_m3_N4_capped.txt
```

```sh
.venv/bin/python find_excludable_sum_free_triples.py \
  --n-values 5 --m 3 --target-bound 0.2 \
  --n-minus-one-alpha-bound 0.2 \
  --width-cuts --monotonicity-cuts --mip-rel-gap 0 \
  --max-families 5 --search-time-limit 120 \
  --output-txt json_results/verification_20260716/removable_interactions_subset_bound/maximal_excludable_triples_m3_N5_capped.txt
```

The corresponding `.log` files contain the programs' complete standard
output. The `.txt` files contain solver settings, optima, solve/cache counts,
termination flags, and the explicit interaction families.
