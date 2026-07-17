# Removable-interaction verification

These runs use the translated-missing-point normalization, choose the first
interval to be shortest, impose the reflection cut comparing the second and
last intervals, and request an exact relative MIP gap (`--mip-rel-gap 0`).  No
`--n-minus-one-alpha-bound` was used.

| N | Singleton-removable triples | Maximal families found | Family sizes | Status |
|---:|---:|---:|:---|:---|
| 2 | 2 | 2 | 1, 1 | Exhaustive |
| 3 | 7 | 7 | 3, 3, 3, 3, 3, 4, 4 | Exhaustive |
| 4 | 16 | 5 | 7, 7, 7, 7, 8 | Partial: stopped at the five-family cap |
| 5 | 32 | 0 | — | Partial: family search timed out after 120 seconds |

The `N=4` families were checked for maximality against all singleton-removable
triples, but the family enumeration was not exhaustive.  For `N=5`, the run
completed the full model and every singleton exclusion, but found no maximal
family before the timed family-search phase ended.  Thus the unconditional
experiment supports maximal-family claims only for `N=2,3`; for `N=5` it
supports only the count of 32 singleton-removable triples.

## Exact commands

```bash
.venv/bin/python find_excludable_sum_free_triples.py \
  --n-values 2,3 \
  --m 3 \
  --target-bound 0.2 \
  --mip-rel-gap 0 \
  --output-txt json_results/verification_20260716/removable_interactions/maximal_excludable_triples_m3_N2-3.txt
```

```bash
.venv/bin/python find_excludable_sum_free_triples.py \
  --n-values 4,5 \
  --m 3 \
  --target-bound 0.2 \
  --width-cuts \
  --mip-rel-gap 0 \
  --max-families 5 \
  --search-time-limit 120 \
  --output-txt json_results/verification_20260716/removable_interactions/maximal_excludable_triples_m3_N4-5_partial.txt
```

The corresponding `.log` files contain complete stdout/stderr and GNU `time`
resource measurements.
