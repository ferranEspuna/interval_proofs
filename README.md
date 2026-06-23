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
`A + A - dA`.

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

The objective is:

```text
maximize sum_i alpha_i
```

## Strengthening Cuts

The script has optional extra constraints. They are enabled by default where
noted.

### Width Cuts

Enabled by default with `--width-cuts`.

Every lifted interval must fit inside a unit gap, so:

```text
alpha_i + alpha_j + d alpha_k <= 1 - 2 epsilon
```

Disable with:

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

Disable with:

```bash
--no-endpoint-length-cut
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

Basic `N=2`, `d=3` run:

```bash
.venv/bin/python circle_intervals.py -N 2 --d 3 --mip-rel-gap 0 --require-success
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

Avoid saving JSON:

```bash
.venv/bin/python circle_intervals.py -N 7 --d 3 --no-save
```

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
- `parameters`, including `N`, `d`, `epsilon`, cut toggles, subset bounds, and
  solver options
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

