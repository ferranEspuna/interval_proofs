# Bound-assisted unrestricted N=6 follow-up

These two standard-formulation runs add the independently computed unrestricted
`N=5` bound to every five-component subunion and use the known exact
six-component construction as a total-length cutoff:

```bash
.venv/bin/python circle_intervals.py -N 6 --m 12 \
  --subset-alpha-bound 5:0.14384920634920634 \
  --total-length-lower-bound 0.14484126984126985 \
  --mip-rel-gap 0 --require-success

.venv/bin/python circle_intervals.py -N 6 --m 13 \
  --subset-alpha-bound 5:0.14398422090729784 \
  --total-length-lower-bound 0.14437869822485207 \
  --mip-rel-gap 0 --require-success
```

Both runs completed with `status_name="optimal"` and stored `mip_gap=0`.

| `m` | rational reconstruction | solver objective | nodes |
|---:|:---|---:|---:|
| 12 | `73/504` | `0.14484128521475476` | 2,984,522 |
| 13 | `122/845` | `0.1443787115567082` | 3,090,399 |

The bounds are floating-point computational inputs, not exact theorems.  The
small objective excesses over the rational constructions are numerical
feasibility noise.  `replay_report.json` covers both saved assignments and
records zero bound, integrality, and objective error, with maximum row
violation `9.54e-7`.
