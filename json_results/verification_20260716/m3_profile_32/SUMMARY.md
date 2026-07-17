# Reproduced 32-configuration profile: `N=5`, `m=3`

## Matrix definition

Every run used `--mip-rel-gap 0 --require-success`, `epsilon=0`, and
was executed sequentially. The binary columns are:

- `t`: translated-missing-point formulation;
- `w`: width cuts;
- `mono`: lift monotonicity cuts;
- `ep`: endpoint-length cut;
- `min`: first interval shortest;
- `sll`: second interval at most the last.

The original formulation has `min=sll=0`, giving all `2^3=8` choices
of `w`, `mono`, and `ep`. In translated mode all five cut flags vary,
except `ep=min=1` is illegal. This gives `4 * (4+2)=24` translated
choices and 32 configurations in total.

Completed: **32/32**. All completed rows valid:
**True**.

## Mid-run metadata-only change

While the sequential profile was running, `circle_intervals.py` gained the
optional `--total-length-lower-bound` flag. No profiling command supplied that
flag, and its default is `None`. Consequently, runs 1--20 lack the metadata
key, whereas runs 21--32 serialize `total_length_lower_bound: null`.

This did not change a matrix model. Rebuilding representative configurations
with the post-change code and the default `None` value produced byte-identical
canonical model cores (name, variables, objective, and constraints) to saved
problems from both sides of the transition. The hashes and counts are recorded
in `model_equivalence_audit.json`; no run was repeated.

## Results

| run | t | w | mono | ep | min | sll | wall (s) | optimum | dual | gap | nodes | valid |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| profile_t0_w0_mono0_ep0_min0_sll0 | 0 | 0 | 0 | 0 | 0 | 0 | 17.913 | 0.2 | 0.2 | 0 | 30,126 | yes |
| profile_t0_w0_mono0_ep1_min0_sll0 | 0 | 0 | 0 | 1 | 0 | 0 | 9.214 | 0.2 | 0.2 | 0 | 13,573 | yes |
| profile_t0_w0_mono1_ep0_min0_sll0 | 0 | 0 | 1 | 0 | 0 | 0 | 11.298 | 0.200000000000002 | 0.200000000000002 | 0 | 10,368 | yes |
| profile_t0_w0_mono1_ep1_min0_sll0 | 0 | 0 | 1 | 1 | 0 | 0 | 6.581 | 0.200000000001133 | 0.200000000001133 | 0 | 4,329 | yes |
| profile_t0_w1_mono0_ep0_min0_sll0 | 0 | 1 | 0 | 0 | 0 | 0 | 18.130 | 0.2 | 0.2 | 0 | 30,126 | yes |
| profile_t0_w1_mono0_ep1_min0_sll0 | 0 | 1 | 0 | 1 | 0 | 0 | 9.213 | 0.2 | 0.2 | 0 | 13,573 | yes |
| profile_t0_w1_mono1_ep0_min0_sll0 | 0 | 1 | 1 | 0 | 0 | 0 | 11.815 | 0.200000000000002 | 0.200000000000002 | 0 | 10,368 | yes |
| profile_t0_w1_mono1_ep1_min0_sll0 | 0 | 1 | 1 | 1 | 0 | 0 | 6.652 | 0.200000000001133 | 0.200000000001133 | 0 | 4,329 | yes |
| profile_t1_w0_mono0_ep0_min0_sll0 | 1 | 0 | 0 | 0 | 0 | 0 | 89.260 | 0.200000000000002 | 0.200000000000002 | 0 | 163,989 | yes |
| profile_t1_w0_mono0_ep0_min0_sll1 | 1 | 0 | 0 | 0 | 0 | 1 | 51.398 | 0.200000000000001 | 0.200000000000001 | 0 | 85,710 | yes |
| profile_t1_w0_mono0_ep0_min1_sll0 | 1 | 0 | 0 | 0 | 1 | 0 | 23.603 | 0.200000000000001 | 0.200000000000001 | 0 | 34,759 | yes |
| profile_t1_w0_mono0_ep0_min1_sll1 | 1 | 0 | 0 | 0 | 1 | 1 | 19.135 | 0.2 | 0.2 | 0 | 26,685 | yes |
| profile_t1_w0_mono0_ep1_min0_sll0 | 1 | 0 | 0 | 1 | 0 | 0 | 41.282 | 0.200000000000001 | 0.200000000000001 | 0 | 71,864 | yes |
| profile_t1_w0_mono0_ep1_min0_sll1 | 1 | 0 | 0 | 1 | 0 | 1 | 22.259 | 0.2 | 0.2 | 0 | 38,219 | yes |
| profile_t1_w0_mono1_ep0_min0_sll0 | 1 | 0 | 1 | 0 | 0 | 0 | 64.319 | 0.200000000000024 | 0.200000000000024 | 0 | 68,995 | yes |
| profile_t1_w0_mono1_ep0_min0_sll1 | 1 | 0 | 1 | 0 | 0 | 1 | 27.081 | 0.200000000000005 | 0.200000000000005 | 0 | 28,208 | yes |
| profile_t1_w0_mono1_ep0_min1_sll0 | 1 | 0 | 1 | 0 | 1 | 0 | 34.858 | 0.200000000000035 | 0.200000000000035 | 0 | 35,220 | yes |
| profile_t1_w0_mono1_ep0_min1_sll1 | 1 | 0 | 1 | 0 | 1 | 1 | 11.334 | 0.200000000000006 | 0.200000000000006 | 0 | 9,475 | yes |
| profile_t1_w0_mono1_ep1_min0_sll0 | 1 | 0 | 1 | 1 | 0 | 0 | 28.499 | 0.200000000000024 | 0.200000000000024 | 0 | 29,118 | yes |
| profile_t1_w0_mono1_ep1_min0_sll1 | 1 | 0 | 1 | 1 | 0 | 1 | 16.367 | 0.200000000000004 | 0.200000000000004 | 0 | 15,931 | yes |
| profile_t1_w1_mono0_ep0_min0_sll0 | 1 | 1 | 0 | 0 | 0 | 0 | 104.978 | 0.200000000000002 | 0.200000000000002 | 0 | 163,989 | yes |
| profile_t1_w1_mono0_ep0_min0_sll1 | 1 | 1 | 0 | 0 | 0 | 1 | 55.549 | 0.200000000000001 | 0.200000000000001 | 0 | 85,710 | yes |
| profile_t1_w1_mono0_ep0_min1_sll0 | 1 | 1 | 0 | 0 | 1 | 0 | 26.519 | 0.200000000000001 | 0.200000000000001 | 0 | 34,759 | yes |
| profile_t1_w1_mono0_ep0_min1_sll1 | 1 | 1 | 0 | 0 | 1 | 1 | 21.406 | 0.2 | 0.2 | 0 | 26,685 | yes |
| profile_t1_w1_mono0_ep1_min0_sll0 | 1 | 1 | 0 | 1 | 0 | 0 | 48.160 | 0.200000000000001 | 0.200000000000001 | 0 | 71,864 | yes |
| profile_t1_w1_mono0_ep1_min0_sll1 | 1 | 1 | 0 | 1 | 0 | 1 | 27.225 | 0.2 | 0.2 | 0 | 38,219 | yes |
| profile_t1_w1_mono1_ep0_min0_sll0 | 1 | 1 | 1 | 0 | 0 | 0 | 78.827 | 0.200000000000024 | 0.200000000000024 | 0 | 68,995 | yes |
| profile_t1_w1_mono1_ep0_min0_sll1 | 1 | 1 | 1 | 0 | 0 | 1 | 33.669 | 0.200000000000005 | 0.200000000000005 | 0 | 28,208 | yes |
| profile_t1_w1_mono1_ep0_min1_sll0 | 1 | 1 | 1 | 0 | 1 | 0 | 46.355 | 0.200000000000035 | 0.200000000000035 | 0 | 35,220 | yes |
| profile_t1_w1_mono1_ep0_min1_sll1 | 1 | 1 | 1 | 0 | 1 | 1 | 13.545 | 0.200000000000006 | 0.200000000000006 | 0 | 9,475 | yes |
| profile_t1_w1_mono1_ep1_min0_sll0 | 1 | 1 | 1 | 1 | 0 | 0 | 39.341 | 0.200000000000024 | 0.200000000000024 | 0 | 29,118 | yes |
| profile_t1_w1_mono1_ep1_min0_sll1 | 1 | 1 | 1 | 1 | 0 | 1 | 19.693 | 0.200000000000004 | 0.200000000000004 | 0 | 15,931 | yes |

## Timing comparison

The historical original winner was `profile_t0_w0_mono1_ep1_min0_sll0` at 4.82s and 4,329 nodes. This reproduction of that configuration is `profile_t0_w0_mono1_ep1_min0_sll0`: 6.581s and 4,329 nodes.

The historical translated winner was `profile_t1_w1_mono1_ep0_min1_sll1` at 8.34s and 9,475 nodes. This reproduction of that configuration is `profile_t1_w1_mono1_ep0_min1_sll1`: 13.545s and 9,475 nodes.

The fastest configurations by current measured wall time are:

- original: `profile_t0_w0_mono1_ep1_min0_sll0`: 6.581s and 4,329 nodes;
- translated: `profile_t1_w0_mono1_ep0_min1_sll1`: 11.334s and 9,475 nodes.

Wall time is machine- and load-dependent. See `environment.json` for
the software versions, processor information, initial load, and other
solver jobs that were active at the beginning of this reproduction.

## Artifacts

For each run, the directory contains `_problem.json`, `_solution.json`,
and `logs/<run>.log`. Each log records the exact command, timestamps,
wall time, exit code, stdout, and stderr. `summary.csv` and
`summary.json` are the machine-readable summaries; `matrix.json` lists
all configurations and commands in execution order.

A zero floating-point MIP gap is a solver result, not an independently
checkable exact rational certificate.
