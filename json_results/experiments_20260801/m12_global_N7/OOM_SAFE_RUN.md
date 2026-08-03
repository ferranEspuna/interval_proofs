# Completed memory-safe audit for `m=12`, `N=7`

## Result

The decomposition below has finished.  All 30 cases are closed: four are
zero-gap optimal at `251/1728`, and 26 are infeasible at or above that cutoff.
The final attempts used 42,749,286 nodes and 33.65 aggregate solver-hours; no
final case hit its time or node limit.  See the
[experiment summary](SUMMARY.md) for the mathematical interpretation and the
[artifact index](../../long_runs/m12_N7_length_order_depth2/README.md) for the
retained evidence.

The result is an all-endpoints-free numerical optimum conditional on the
smaller-component subset bounds.  It is not restricted to the fixed equally
spaced base, but it is also not an unconditional exact upper-bound theorem.

## Why the decomposition was needed

The monolithic seven-day run was killed by the Linux OOM killer after about
5.2 hours.  At the last logged point HiGHS had processed about 11.8 million
nodes and retained about 5.3 million queued nodes.  The kernel recorded
approximately 12.1 GiB resident memory for the Python process on a machine
with 15 GiB RAM and 4 GiB swap.

HiGHS through `scipy.optimize.milp` does not checkpoint or move the open MIP
tree to disk.  A restarted monolithic job therefore begins from the root and
eventually recreates the same memory pressure.

## Reproducing the decomposition

Use the translated formulation, put a shortest interval at index 0, and split
exhaustively on the positional indices of a second- and third-shortest
interval.  There are `6*5=30` cases.  Ties can put a configuration in more
than one case, but every configuration occurs in at least one case.

Run all cases sequentially:

```bash
cd /home/ferran/interval_proofs

CASE_SECONDS=7200 \
NODE_LIMIT=3000000 \
THREADS=1 \
bash json_results/experiments_20260801/m12_global_N7/run_m12_n7_memory_safe.sh
```

The limits shown above stop each case after two hours or three million
processed nodes, whichever comes first.  They were deliberately conservative
for a 16 GiB machine.  A few original attempts needed a higher time limit, but
the retained final attempts all closed below three million nodes.  Each solver
process exits and releases its tree before the next case begins.  Completed
`optimal` or `infeasible` cases are skipped when the batch script is rerun.

## Two simultaneous workers

The parallel-safe runner may be launched with the same command in two
terminals or tmux windows:

```bash
cd /home/ferran/interval_proofs

CASE_SECONDS=7200 \
NODE_LIMIT=3000000 \
THREADS=1 \
MAX_WORKERS=2 \
bash json_results/experiments_20260801/m12_global_N7/run_m12_n7_memory_safe_parallel.sh
```

Each worker claims a different case by creating its log while holding a
scheduler lock.  When multiple workers are active, they only claim cases that
have no log.  The final remaining worker may retry logged but unresolved cases
once; closed `optimal` and `infeasible` cases are always skipped.  Logs are
appended on a retry rather than overwritten.

The default `MAX_WORKERS=2` reflects the measured memory headroom on the
16 GiB machine.  A third launch warns and exits without claiming anything.
If one worker runs out of unlogged cases while another is still active, it
warns, unregisters, and exits.  This lets the last worker safely decide what
logged unresolved work remains.

Do not run the original sequential runner or a manually named case against
the same output directory at the same time.  They do not participate in this
worker registry.

Summarize the results with:

```bash
.venv/bin/python \
  json_results/experiments_20260801/m12_global_N7/summarize_length_order_cases.py
```

Rerunning an identical case does not resume its branch-and-bound tree.  During
an incomplete future audit, a persistent case can instead be split one rank
deeper, for example:

```bash
.venv/bin/python \
  json_results/experiments_20260801/m12_global_N7/solve_translated_length_order_case.py \
  --length-order 2,4,1 \
  --time-limit 7200 \
  --node-limit 3000000 \
  --threads 1 \
  --output-dir json_results/long_runs/m12_N7_length_order_depth3 \
  --run-name m12_N7_lengthorder_2-4-1 \
  --disp
```

For an unresolved depth-two prefix `i,j`, the four cases `i,j,k` over the
remaining indices `k` partition it exhaustively.  No such deeper split was
needed for the completed results retained here.

As in the main experiment, these computations are conditional on treating
the floating-point smaller-`N` rational reconstructions as upper bounds.
