# Interval Proofs MILP Tools

This repository contains a small named-variable MILP wrapper and a model for
searching interval configurations on the circle.

The main script is `circle_intervals.py`. It builds a mixed-integer linear
program for a set

```text
A = union_i [x_i, x_i + alpha_i] in T = R/Z
```

ordered in the representative interval `[0, 1]`, and maximizes
`sum_i alpha_i` subject to the condition that `0` is not contained in
`A + A - dA`. It also has an optional translated-missing-point formulation
that asks whether some point, not necessarily `0`, is outside `A + A - dA`.

The proof that the sharp bound is `1/5` for `N=2`, `d=3` is in:

```text
latex/2_interval_proof.tex
pdf/2_interval_proof.pdf
```

That proof shows that any union of two closed intervals in `T` of measure at
least `1/5` satisfies `A + A - 3A = T`. In the MILP's normalized missing-point
formulation, this corresponds to a supremum of `1/5` for `N=2`, `d=3`.

## Setup

Create and use the project virtual environment:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Run the small MILP wrapper test:

```bash
.venv/bin/python test_milp_problem.py
```

## Files

`milp_problem.py` defines:

- `MILPProblem`: dataclass-style named-variable MILP model.
- `NamedVariable`: continuous or integer variables with bounds.
- `LinearConstraintSpec`: named linear equalities and inequalities.
- `LinearObjective`: linear minimization or maximization objective.
- `MILPSolution`: solver result with named values, objective value, model
  parameters, and solver diagnostics.

`circle_intervals.py` defines:

- `build_circle_interval_problem(...)`: builds the interval MILP.
- `integer_lift_bounds(...)`: computes safe bounds for the integer lift
  variables.
- A command line interface for building, solving, and saving JSON artifacts.

`json_results/` is the default output directory for saved problem and solution
JSON files.

## MILP Model

For each interval `i`, the model has:

```text
x_i       start point, continuous in [0, 1]
alpha_i   interval length, continuous
```

The interval is represented as `[x_i, x_i + alpha_i]`. The model adds:

```text
x_i + alpha_i <= 1
x_{i-1} + alpha_{i-1} <= x_i
```

so intervals are non-wrapping, ordered, and non-overlapping in `[0, 1]`.

For every `i <= j` and every `k`, it introduces an integer lift variable
`n_{i-j-k}` so that the real interval

```text
I_i + I_j - d I_k
```

is contained between consecutive integers:

```text
n_{i-j-k} + epsilon <= left endpoint
right endpoint <= n_{i-j-k} + 1 - epsilon
```

With `epsilon=0`, this is the closed relaxation and computes a supremum. With
positive `epsilon`, it enforces a positive margin from integer endpoints.

With `--translated-missing-point`, the model adds a continuous variable
`t in [0, 1]` and instead uses:

```text
n_{i-j-k} + t + epsilon <= left endpoint
right endpoint <= n_{i-j-k} + 1 + t - epsilon
```

This asks whether any point `t mod 1` is missing from `A + A - dA`. In this
mode the integer lift lower bound is one smaller, because `t` can shift the
containing unit interval by up to one. The model also fixes `x_0 = 0`, using
translation invariance to start the first interval at the origin.

The objective is:

```text
maximize sum_i alpha_i
```

## Strengthening Cuts

The script has optional extra constraints. They are enabled by default where
noted.

### Width Cuts

Disabled by default. Enable with `--width-cuts`.

Every lifted interval must fit inside a unit gap, so:

```text
alpha_i + alpha_j + d alpha_k <= 1 - 2 epsilon
```

Leave disabled with the default behavior, or explicitly with:

```bash
--no-width-cuts
```

### Integer Monotonicity Cuts

Enabled by default with `--monotonicity-cuts`.

Since intervals are ordered, the lift variables are monotone:

```text
n_{i-1,j,k} <= n_{i,j,k}
n_{i,j-1,k} <= n_{i,j,k}
n_{i,j,k} <= n_{i,j,k-1}
```

Disable with:

```bash
--no-monotonicity-cuts
```

### Endpoint Length Cut

Enabled by default with `--endpoint-length-cut`.

This adds:

```text
alpha_{N-1} <= alpha_0
```

The intended justification is the reflection symmetry `A -> -A`, choosing the
orientation in which the last interval is no longer than the first. Because
this is a symmetry-breaking convention, keep `--no-endpoint-length-cut` handy
when auditing or comparing runs.

Disabling this cut does not let intervals wrap around the endpoint of
`[0, 1]`; it only removes the inequality above. The non-wrapping constraints
`x_i + alpha_i <= 1` remain in force.

Disable with:

```bash
--no-endpoint-length-cut
```

### Translated-Only Symmetry Cuts

These require `--translated-missing-point`, because they use the extra
translation freedom from the variable missing point.

Use `--first-interval-shortest` to add:

```text
alpha_0 <= alpha_i for every i
```

This chooses the origin at a shortest interval. It cannot be combined with
`--endpoint-length-cut`; pass `--no-endpoint-length-cut` when using it.

Use `--second-interval-at-most-last` to add:

```text
alpha_1 <= alpha_{N-1}
```

Here the indices are the zero-based variable names used in the JSON and code:
`alpha_0` is the first interval from the origin, `alpha_1` the second, and
`alpha_{N-1}` the last.

### Excluding Head or Tail Sum-Free Conditions

Use `--exclude-sum-free-triple I,J,K` to skip one exact lifted d-sum-free
condition:

```text
I_i + I_j - d I_k
```

The first two indices must satisfy `I <= J`, matching the modeled triples
`i <= j`. The option can be repeated:

```bash
--exclude-sum-free-triple 0,0,0
--exclude-sum-free-triple 0,1,0
```

This skips exactly `I_0 + I_0 - d I_0` and `I_0 + I_1 - d I_0`, and does not
skip other triples involving intervals `0` or `1`.

Use `--exclude-sum-free-intervals I,J,...` to choose a zero-based set of
intervals. This is coarser: the model skips all lifted d-sum-free conditions
whose three interval indices all lie inside that chosen set. The option can be
repeated to exclude several chosen sets.

The shortcut flags `--exclude-sum-free-head-size COUNT` and
`--exclude-sum-free-tail-size COUNT` do the same thing for the first or last
`COUNT` intervals, respectively.

For head `COUNT=1`, this skips only:

```text
I_0 + I_0 - d I_0
```

For tail `COUNT=1`, this skips only:

```text
I_{N-1} + I_{N-1} - d I_{N-1}
```

For `COUNT=2`, this skips the lifted conditions using only the first two or
last two intervals. This is useful for testing how much chosen small intervals
contribute to the tightness of a bound.

In the translated-missing-point formulation with `--first-interval-shortest`,
the first interval `alpha_0` is the known shortest interval, so the natural
small-interval experiment is usually:

```bash
--exclude-sum-free-head-size 1
```

or, when also treating the second interval from the origin as part of the
small block:

```bash
--exclude-sum-free-head-size 2
```

The tail option remains useful for experiments in the original ordering, or
when you specifically want to test the last interval or last few intervals.

Direct examples:

```bash
--exclude-sum-free-triple 0,0,0
--exclude-sum-free-triple 0,0,0 --exclude-sum-free-triple 0,1,0
--exclude-sum-free-intervals 0
--exclude-sum-free-intervals 0,1
--exclude-sum-free-intervals 0,2
--exclude-sum-free-intervals 0,1 --exclude-sum-free-intervals 3,4
```

Skipped triples do not get an integer lift variable `n_{i-j-k}`, the two
left/right containment inequalities, width cuts, or monotonicity links
involving that missing lift variable. Also, if a self triple `(i, i, i)` is
skipped, the derived variable upper bound `alpha_i <= 1/(d+2)` is not imposed
on that interval; the interval is still bounded by `x_i + alpha_i <= 1`.

Important: excluding d-sum-free triples relaxes the MILP. If the relaxed model
proves a larger optimum than the full model, that is not a theorem about the
original problem; it only shows that the omitted triples may be doing real
work. The useful case is when the relaxed model proves the same bound as the
full model. Then the run suggests those omitted triples are not needed for
that numerical bound, which can guide a shorter proof or help build intuition
about which interval interactions are essential.

The script warns when triples are excluded without any symmetry condition
identifying a globally shortest interval. For small-interval experiments, the
usual way to provide that information is:

```bash
--translated-missing-point --first-interval-shortest
```

Examples:

```bash
--exclude-sum-free-intervals 0,1
--exclude-sum-free-head-size 1
--exclude-sum-free-head-size 2
--exclude-sum-free-tail-size 1
--exclude-sum-free-tail-size 2
```

### Subset Alpha Bounds

Use `--subset-alpha-bound N_PRIME:BOUND` to add:

```text
sum_{i in S} alpha_i <= BOUND
```

for every subset `S` of size `N_PRIME`.

This is useful when a proven bound is known for fewer intervals. For example,
if for the same `d` you know any six intervals have total length at most
`1/5`, then in a seven-interval run add:

```bash
--subset-alpha-bound 6:0.2
```

The option can be repeated:

```bash
--subset-alpha-bound 6:0.2 --subset-alpha-bound 5:0.2
```

## Command Line Usage

Show all options:

```bash
.venv/bin/python circle_intervals.py --help
```

Every CLI flag has an example below. The examples are intentionally small; mix
the flags as needed for longer experiments.

Basic `N=2`, `d=3` run:

```bash
.venv/bin/python circle_intervals.py -N 2 --d 3 --mip-rel-gap 0 --require-success
```

Use a positive endpoint margin:

```bash
.venv/bin/python circle_intervals.py -N 2 --d 3 --epsilon 1e-6
```

Print the generated MILP without saving JSON:

```bash
.venv/bin/python circle_intervals.py -N 2 --d 3 --print-problem --no-save
```

Translated-missing-point run with both translated-only symmetry cuts:

```bash
.venv/bin/python circle_intervals.py -N 5 --d 3 \
  --translated-missing-point \
  --width-cuts \
  --first-interval-shortest \
  --second-interval-at-most-last \
  --no-endpoint-length-cut \
  --mip-rel-gap 0 \
  --require-success
```

Width and monotonicity cut examples:

```bash
.venv/bin/python circle_intervals.py -N 5 --d 3 --width-cuts
.venv/bin/python circle_intervals.py -N 5 --d 3 --no-width-cuts
.venv/bin/python circle_intervals.py -N 5 --d 3 --monotonicity-cuts
.venv/bin/python circle_intervals.py -N 5 --d 3 --no-monotonicity-cuts
```

Endpoint symmetry examples:

```bash
.venv/bin/python circle_intervals.py -N 5 --d 3 --endpoint-length-cut
.venv/bin/python circle_intervals.py -N 5 --d 3 --no-endpoint-length-cut
```

Relax the model by ignoring lifted d-sum-free conditions supported only on the
first interval:

```bash
.venv/bin/python circle_intervals.py -N 5 --d 3 \
  --exclude-sum-free-head-size 1 \
  --mip-rel-gap 0 \
  --require-success
```

In translated-missing-point experiments with the first interval normalized as
shortest, ignore the lifted conditions supported only on the first two
intervals:

```bash
.venv/bin/python circle_intervals.py -N 5 --d 3 \
  --translated-missing-point \
  --first-interval-shortest \
  --second-interval-at-most-last \
  --no-endpoint-length-cut \
  --exclude-sum-free-intervals 0,1 \
  --mip-rel-gap 0 \
  --require-success
```

Ignore only two exact triples involving the first two intervals:

```bash
.venv/bin/python circle_intervals.py -N 5 --d 3 \
  --translated-missing-point \
  --first-interval-shortest \
  --second-interval-at-most-last \
  --no-endpoint-length-cut \
  --exclude-sum-free-triple 0,0,0 \
  --exclude-sum-free-triple 0,1,0 \
  --mip-rel-gap 0 \
  --require-success
```

Relax the model by ignoring lifted d-sum-free conditions supported only on the
last interval:

```bash
.venv/bin/python circle_intervals.py -N 5 --d 3 \
  --exclude-sum-free-tail-size 1 \
  --mip-rel-gap 0 \
  --require-success
```

Relax the model by ignoring lifted d-sum-free conditions supported only on the
last two intervals:

```bash
.venv/bin/python circle_intervals.py -N 5 --d 3 \
  --exclude-sum-free-tail-size 2 \
  --mip-rel-gap 0 \
  --require-success
```

Run `N=7`, `d=3` with the known six-alpha bound `1/5`:

```bash
.venv/bin/python circle_intervals.py -N 7 --d 3 \
  --subset-alpha-bound 6:0.2 \
  --time-limit 300 \
  --mip-rel-gap 1e-3 \
  --run-name N7_d3_with_6_bound
```

Run the same experiment without the endpoint symmetry cut:

```bash
.venv/bin/python circle_intervals.py -N 7 --d 3 \
  --subset-alpha-bound 6:0.2 \
  --no-endpoint-length-cut \
  --time-limit 300 \
  --mip-rel-gap 1e-3 \
  --run-name N7_d3_with_6_bound_no_endpoint_cut
```

Run with solver logging:

```bash
.venv/bin/python circle_intervals.py -N 7 --d 3 \
  --subset-alpha-bound 6:0.2 \
  --disp
```

Limit solver effort:

```bash
.venv/bin/python circle_intervals.py -N 7 --d 3 \
  --time-limit 300 \
  --node-limit 100000 \
  --mip-rel-gap 1e-3
```

Control HiGHS presolve and thread count:

```bash
.venv/bin/python circle_intervals.py -N 5 --d 3 --presolve --threads 4
.venv/bin/python circle_intervals.py -N 5 --d 3 --no-presolve --threads 1
```

Save to a different output directory:

```bash
.venv/bin/python circle_intervals.py -N 7 --d 3 \
  --subset-alpha-bound 6:0.2 \
  --output-dir experiments/json
```

Save to explicit files:

```bash
.venv/bin/python circle_intervals.py -N 7 --d 3 \
  --subset-alpha-bound 6:0.2 \
  --problem-json experiments/N7_problem.json \
  --solution-json experiments/N7_solution.json
```

Use a run name for the default JSON filenames:

```bash
.venv/bin/python circle_intervals.py -N 7 --d 3 \
  --run-name N7_d3_named_experiment
```

Avoid saving JSON:

```bash
.venv/bin/python circle_intervals.py -N 7 --d 3 --no-save
```

## Profiling Notes

The `N=5`, `d=3` profiling runs from 2026-06-24 are saved in:

```text
json_results/k5_translated_profile_20260624/
```

The summary files are:

```text
json_results/k5_translated_profile_20260624/profile_summary.csv
json_results/k5_translated_profile_20260624/profile_summary.json
```

All 32 legal runs in that matrix used `--mip-rel-gap 0 --require-success`,
proved the same bound `0.2`, and ended with zero MIP gap.

Fastest original formulation:

```bash
.venv/bin/python circle_intervals.py -N 5 --d 3 \
  --no-width-cuts \
  --monotonicity-cuts \
  --endpoint-length-cut \
  --mip-rel-gap 0 \
  --require-success
```

This took about `4.82s` and `4,329` branch-and-bound nodes.

Fastest translated-missing-point formulation:

```bash
.venv/bin/python circle_intervals.py -N 5 --d 3 \
  --translated-missing-point \
  --width-cuts \
  --monotonicity-cuts \
  --no-endpoint-length-cut \
  --first-interval-shortest \
  --second-interval-at-most-last \
  --mip-rel-gap 0 \
  --require-success
```

This took about `8.34s` and `9,475` branch-and-bound nodes. In this benchmark,
the translated formulation did not improve solve time, but it produces
normalized solutions with `t` and `x_0 = 0`, which are useful for locating
small intervals in later experiments. Width cuts were neutral or slightly
slower in the original formulation, but helpful in the best translated runs.

## Solver Options

The script uses `scipy.optimize.milp`, backed by HiGHS.

Common options:

```bash
--time-limit SECONDS
--node-limit NODES
--mip-rel-gap GAP
--presolve / --no-presolve
--disp
--threads THREADS
```

If no solver options are passed, SciPy/HiGHS uses its defaults. In particular,
the default relative MIP gap is typically `1e-4`, so a reported optimum is a
numerical MIP optimum to solver tolerance, not an exact rational proof.

Use this for a stronger numerical proof:

```bash
--mip-rel-gap 0 --require-success
```

It may be much slower.

## JSON Output

By default, every run writes:

```text
json_results/<run>_problem.json
json_results/<run>_solution.json
```

The problem JSON includes variables, constraints, objective, and metadata.

The solution JSON includes:

- `optimum`
- named variable `values`
- `parameters`, including `N`, `d`, `epsilon`, formulation and cut toggles,
  subset bounds, and solver options
- `solver_details`, including node count, dual bound, and MIP gap when HiGHS
  provides them

Load saved files in Python:

```python
from pathlib import Path
from milp_problem import MILPProblem, MILPSolution

problem = MILPProblem.from_json(Path("json_results/run_problem.json").read_text())
solution = MILPSolution.from_json(Path("json_results/run_solution.json").read_text())
print(solution.optimum)
print(solution.parameters)
```

