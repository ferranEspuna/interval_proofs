# Exact reconstruction of the positive two-extra scan

`verify_exact_two_extra_family.py` performs two exact checks with
`fractions.Fraction`:

1. it reconstructs all 48 positive larger-`q` saved solutions (`m=4,8,9`
   and the 45 values `12 <= m <= 100` congruent to `0` or `1` modulo `4`),
   discards zero-length MILP extras, and rechecks every lifted image
   `I_i + I_j - m I_ell`;
2. it verifies a solver-independent canonical family for the same 48 values.

All checks pass.  Each pass checked 161,000 lifted images, hence 322,000 exact
image containments (644,000 endpoint inequalities) across both passes.  The
largest errors between a reconstructed rational endpoint/length and its saved
floating-point value were respectively
`1.1950246348035876e-11` and `1.195024442357702e-11`.

## Uniform family

Let

```text
delta = (m - 2q + 2) / (m(m+2)),
a     = -m delta / (m-2) (mod 1),
b     = a + 1/m (mod 1).
```

Thus `b` is the start of the first base interval after wrapping around zero.
For every `m = 0 (mod 4)` with `12 <= m <= 100`, take

```text
q = m/4 + 1,
g = 2 / (m^2(m+2)),
x_1 = b - (m-4)/(4m^2),
x_2 = b - (m-8)/(4m^2).
```

For every `m = 1 (mod 4)` with `13 <= m <= 97`, take

```text
q = (m+3)/4,
g = 1 / (m^2(m+2)),
x_1 = b - (m-5)/(4m^2),
x_2 = b - (m-9)/(4m^2).
```

Adding `(x_1,x_1+g)` and `(x_2,x_2+g)` to the fixed equally spaced base is
exactly `m`-sum-free in every tested case.  The starts satisfy
`x_2-x_1=1/m^2`; each interval contributes exactly the one-extra gain `g`, so
the total two-extra gain is exactly `2g`.  This includes the clean `m=100`
case.

The same first-start formula gives one genuine extra at `m=8` and `m=9`; the
second start then equals `b` and overlaps the base.  The `m=4` certificate is
the separate interval with start `1/48` and length `1/192`.

Equivalently, the canonical starts lie on the grid observed in the saved
solutions.  If `m=0 (mod 4)`,

```text
x_i/g = J_i + (m-4)/(m-2),
J_1 = (m^2+6m-8)/8,
J_2 = m(m+10)/8.
```

If `m=1 (mod 4)`,

```text
x_i/g = J_i + (m-8)/(m-2),
J_1 = (m^2+5m-6)/4,
J_2 = (m^2+9m+2)/4.
```

The solver often chose different integer grid positions, but every positive
saved choice also reconstructs and verifies exactly.  Those choices, all base
and extra rational endpoints, exact measures, triple counts, and endpoint
slacks are recorded in `exact_verification_report.json`.

## Reproduction

```bash
python3 json_results/verification_20260716/tiny_intervals_two_extra_exact/verify_exact_two_extra_family.py
```

The canonical main-scan `m=100` artifact is the clean no-presolve rerun.  The
canonical exact check is solver-independent and does not otherwise depend on
that floating-point file.
