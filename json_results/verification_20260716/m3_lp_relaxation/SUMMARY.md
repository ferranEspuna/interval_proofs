# Naive LP relaxation for `m=3`

## Scope

`run.py` rebuilt the standard ordered-interval model for every
`N=1,...,8`, both with and without the redundant interval-width cuts.  It
then changed every integer lift variable `n_i-j-ell` to a continuous variable
and solved the resulting LP.  Monotonicity cuts and the endpoint-length
symmetry cut retained their normal default settings.

This is the direct LP relaxation suggested as a first diagnostic in the
research roadmap.  It does not include the previously computed subunion
bounds, since the purpose is to test whether the formulation itself exposes
the desired `1/5` inequality.

## Result

All 16 LPs solved optimally.  With either width-cut setting, the objective was

```text
N = 1, 2, 3, 4, 5, 6, 7, 8
LP optimum = 0.2, 0.4, 0.6, 0.8, 1, 1, 1, 1.
```

Thus the naive relaxation gives `min(N/5, 1)` and is already too weak at
`N=2`.  The width cuts do not strengthen it.

`result_summary.json` indexes every serialized problem/solution pair.
Independent replay found maximum row violation
`8.89e-16`, maximum objective error `1.12e-16`, and no bound violation.
