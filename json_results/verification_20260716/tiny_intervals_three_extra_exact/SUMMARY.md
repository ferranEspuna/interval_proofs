# Exact reconstruction of the positive three-extra runs

`verify_exact_three_extra.py` reconstructs the larger-`q`, `K=3` solutions for
`m=12,13,16,17` over `fractions.Fraction`.  It checks both the rational union
and every integer lift stored in the corresponding solver solution.

All 898 lifted images pass exactly, and all 898 saved integer lifts contain the
reconstructed open images in an interval `[n,n+1]`.  The largest discrepancies
between saved floating-point and reconstructed rational starts and lengths are
`5.245803791353865e-15` and `4.600811918942238e-16`, respectively.

| `m` | positive extras | exact measure | lifted images | zero endpoint slacks | minimum positive slack |
|---:|---:|---:|---:|---:|---:|
| 12 | 3 | `251/1728` | 196 | 14 | `1/144` |
| 13 | 2 | `122/845` | 126 | 13 | `7/169` |
| 16 | 3 | `323/2304` | 288 | 19 | `1/32` |
| 17 | 3 | `768/5491` | 288 | 18 | `10/289` |

Thus the third interval is genuinely positive for `m=12,16,17`.  At `m=12`
its length is `5/12096`, while the other two lengths are `1/1008`.  All three
have length `1/2304` at `m=16` and `1/5491` at `m=17`.  At `m=13`, the third
MILP variable has length zero, so the exact union is the previously verified
two-extra construction.

## Exact endpoint lists

The intervals are open.  In increasing circular order, the reconstructed
`m=12` union is

```text
(17/420, 8/105)
(23/280, 419/5040)
(7103/60480, 33/280)
(13/105, 67/420)
(139/840, 839/5040)
(29/140, 17/70)
(67/70, 139/140)
```

The `m=13` union is

```text
(632/27885, 643/27885)
(797/27885, 808/27885)
(74/2145, 151/2145)
(239/2145, 316/2145)
(404/2145, 37/165)
(158/165, 2131/2145)
```

The `m=16` union is

```text
(307/16128, 157/8064)
(185/8064, 377/16128)
(433/16128, 55/2016)
(31/1008, 59/1008)
(47/504, 61/504)
(157/1008, 185/1008)
(55/252, 31/126)
(61/63, 251/252)
```

The `m=17` union is

```text
(558/27455, 563/27455)
(653/27455, 658/27455)
(44/1615, 89/1615)
(2173/27455, 2178/27455)
(139/1615, 184/1615)
(234/1615, 279/1615)
(329/1615, 22/95)
(92/95, 1609/1615)
```

`exact_verification_report.json` records every interval start, end, and length,
as well as the exact lift, image endpoints, and both endpoint slacks for every
one of the 898 interactions.

## Reproduction

```bash
python3 json_results/verification_20260716/tiny_intervals_three_extra_exact/verify_exact_three_extra.py
```

While this check was running, the separate saturation campaign produced an
optimal zero-gap `m=12`, `K=4` artifact with the same objective up to solver
tolerance and a fourth length of about `1.6e-13`.  That artifact is not used in
this `K=3` exact verification.
