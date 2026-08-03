#!/usr/bin/env python3
"""Exact analysis of the short-extra branch containing the m=12 example.

For ``m = 0 (mod 4)``, the fixed-base experiments exhibit two competing
patterns.  The regular doubled tail uses only full extras of length ``g``.
The hybrid below uses several full extras and a right-hand suffix ``T`` of a
regular tail interval.  Two tight lifted images determine the suffix length

    h = (m - 2) / (m^3 (m + 2)).

At m=12 this is 5/12096.  This program constructs the hybrid and checks every
lifted image with ``fractions.Fraction`` for m=12,16,...,100.  It also checks
the exact gain comparison that explains why the hybrid beats the regular
doubled tail only at m=12 in that range.

The finite checks are exact construction certificates.  They do not prove
that either pattern is optimal, that the two patterns exhaust all possible
constructions, or that the hybrid is feasible for untested m.
"""

from __future__ import annotations

from fractions import Fraction as F
from math import floor
import json
from typing import Any


def base_parameters(m: int) -> tuple[int, F, F, F]:
    """Return q, delta, a, b for the larger mod-0 equally spaced base."""
    assert m >= 12 and m % 4 == 0
    q = m // 4 + 1
    delta = F(1, 2 * (m + 2))
    a = (-F(m) * delta / F(m - 2)) % 1
    b = (a + F(1, m)) % 1
    return q, delta, a, b


def base_intervals(m: int) -> list[tuple[F, F, str]]:
    q, delta, a, _ = base_parameters(m)
    return [
        ((a + F(r, m)) % 1, delta, f"base_{r}")
        for r in range(q)
    ]


def hybrid_construction(
    m: int,
) -> tuple[list[tuple[F, F, str]], dict[str, Any]]:
    """Build the hybrid branch and its exact algebraic metadata."""
    q, delta, _, b = base_parameters(m)
    k = m // 4
    g = F(2, m * m * (m + 2))
    h = F(m - 2, m**3 * (m + 2))

    def s(j: int) -> F:
        return b - F(m - 4 * j, 4 * m * m)

    # U and V replace the unshifted half of the regular doubled tail.  T is
    # the rightmost h-long suffix of the translated j=2 interval.  The later
    # translated-tail intervals remain full.
    u = b + F(1, 2 * m)
    v = u + F(1, m)
    translated_tail_2 = s(2) + F(1, m)
    t_end = translated_tail_2 + g
    t_start = t_end - h

    extras = [
        (u, g, "hybrid_U"),
        (v, g, "hybrid_V"),
        (t_start, h, "hybrid_T"),
    ]
    extras.extend(
        (s(j) + F(1, m), g, f"translated_tail_{j}")
        for j in range(3, k)
    )

    # The two endpoint equalities seen in the m=12 exact certificate persist
    # symbolically.  They place two lifted images on opposite sides of -1.
    x_3 = b + F(2, m)
    x_k = b + F(k - 1, m)
    assert x_3 + x_k - m * t_end == -1
    assert (v + g) + (x_k + delta) - m * t_start == -1
    assert m * h == F(1, 2 * m) - delta - g

    full_extra_count = k - 1
    assert len(extras) == k
    assert sum(length == g for _, length, _ in extras) == full_extra_count
    hybrid_gain = full_extra_count * g + h
    regular_gain = F(m - 8, m * m * (m + 2))
    advantage = hybrid_gain - regular_gain

    assert hybrid_gain == F(m * m - 2 * m - 4, 2 * m**3 * (m + 2))
    assert advantage == F(-m * m + 14 * m - 4, 2 * m**3 * (m + 2))
    assert h / g == F(m - 2, 2 * m)

    return base_intervals(m) + extras, {
        "m": m,
        "q": q,
        "g": str(g),
        "h": str(h),
        "h_over_g": str(h / g),
        "full_extra_count": full_extra_count,
        "positive_extra_count": len(extras),
        "hybrid_gain": str(hybrid_gain),
        "regular_doubled_tail_gain": str(regular_gain),
        "hybrid_minus_regular": str(advantage),
        "comparison": "greater" if advantage > 0 else "less",
        "tight_T_left_endpoint": str(t_start),
        "tight_T_right_endpoint": str(t_end),
    }


def verify_lifted_images(
    m: int, intervals: list[tuple[F, F, str]]
) -> dict[str, Any]:
    """Check geometry and every I_i+I_j-m I_l image exactly."""
    ordered = sorted(intervals)
    assert all(F(0) <= x < x + alpha <= F(1) for x, alpha, _ in ordered)
    assert all(
        x + alpha <= y
        for (x, alpha, _), (y, _, _) in zip(ordered, ordered[1:])
    )

    interaction_count = 0
    zero_endpoint_slacks = 0
    minimum_positive_endpoint_slack: F | None = None
    for i, (x_i, alpha_i, _) in enumerate(ordered):
        for x_j, alpha_j, _ in ordered[i:]:
            for x_ell, alpha_ell, _ in ordered:
                left = x_i + x_j - m * (x_ell + alpha_ell)
                right = x_i + alpha_i + x_j + alpha_j - m * x_ell
                lift = floor(left)
                assert lift <= left < right <= lift + 1
                for slack in (left - lift, F(lift + 1) - right):
                    if slack == 0:
                        zero_endpoint_slacks += 1
                    elif (
                        minimum_positive_endpoint_slack is None
                        or slack < minimum_positive_endpoint_slack
                    ):
                        minimum_positive_endpoint_slack = slack
                interaction_count += 1

    interval_count = len(ordered)
    assert interaction_count == interval_count**2 * (interval_count + 1) // 2
    return {
        "interval_count": interval_count,
        "interaction_count": interaction_count,
        "measure": str(sum(alpha for _, alpha, _ in ordered)),
        "zero_endpoint_slacks": zero_endpoint_slacks,
        "minimum_positive_endpoint_slack": str(minimum_positive_endpoint_slack),
    }


def main() -> None:
    cases = []
    total_interactions = 0
    for m in range(12, 101, 4):
        intervals, metadata = hybrid_construction(m)
        exact = verify_lifted_images(m, intervals)
        assert exact["interval_count"] == m // 2 + 1
        metadata["exact_replay"] = exact
        cases.append(metadata)
        total_interactions += exact["interaction_count"]

    assert len(cases) == 23
    assert total_interactions == 468_257
    assert F(cases[0]["h"]) == F(5, 12096)
    assert F(cases[0]["hybrid_minus_regular"]) == F(5, 12096)
    assert all(case["comparison"] == "less" for case in cases[1:])

    report = {
        "summary": {
            "cases_verified": len(cases),
            "lifted_images_verified": total_interactions,
            "tested_m": "12,16,...,100",
            "short_length_formula": "h=(m-2)/(m^3(m+2))",
            "hybrid_gain_formula": "(m^2-2m-4)/(2m^3(m+2))",
            "regular_gain_formula": "(m-8)/(m^2(m+2))",
            "difference_formula": "(-m^2+14m-4)/(2m^3(m+2))",
            "sign_switch": (
                "positive at m=12; negative for every tested m>=16; "
                "the positive real interval ends at 7+3*sqrt(5)"
            ),
            "optimality_claim": "none; exact finite construction checks only",
        },
        "cases": cases,
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
