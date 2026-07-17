# Strict rerun of the `m=87`, `N=2` scan

The original saved run used SciPy 1.18.0 / HiGHS 1.12.0 with
`{"mip_rel_gap": 0.0}`.  Its raw HiGHS point had

- objective `0.021955314544418954`;
- `n_0-1-0 = -39.999999993891784`, an integrality residual of
  `6.108216155098489e-09`; and
- a maximum row violation of `6.108223260525847e-09` in
  `sum_free_right_1-1-0`.

The same problem JSON was loaded with `MILPProblem.from_json` and solved by
calling

```python
problem.solve(options={
    "mip_rel_gap": 0.0,
    "mip_feasibility_tolerance": 1e-10,
    "primal_feasibility_tolerance": 1e-10,
    "dual_feasibility_tolerance": 1e-10,
})
```

SciPy reports the three feasibility-tolerance keys as unrecognized SciPy
options and passes them verbatim to HiGHS.  The strict run proved optimality
with zero MIP gap in 104 nodes.  Its objective is
`0.021955314477593028`, every integer lift is exactly integral in the raw
result, and the maximum violation recomputed from the serialized point is
`2.708944180085382e-14`.

The following rational reconstruction satisfies every row of the saved MILP
exactly:

```text
alpha_0 = alpha_1 = 85/7743
x_0 = 1407/1513
x_1 = 123922/131631 = x_0 + 1/87
(n_000, n_001, n_010, n_011, n_110, n_111)
    = (-80, -81, -80, -81, -80, -81)
objective = 170/7743 = 0.021955314477592663
```

The strict floating-point optimum differs from this exact value by
`3.642919299551295e-16`.
