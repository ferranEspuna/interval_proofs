#!/usr/bin/env python3
"""Verify the rational constructions recovered from the higher-m MILPs.

For open intervals I_r=(a_r,b_r), the real lift

    I_i + I_j - m I_l

is (L,R)=(a_i+a_j-m*b_l, b_i+b_j-m*a_l).  The circle set is
m-sum-free exactly when none of these open intervals contains an integer.
All arithmetic below is exact.
"""

from __future__ import annotations

from fractions import Fraction
from itertools import combinations_with_replacement

F = Fraction

CONSTRUCTIONS = {
    "m4_N5_solution": (
        4,
        ((F(1, 3), F(5, 12)), (F(91, 192), F(23, 48)), (F(7, 12), F(2, 3))),
        F(11, 64),
    ),
    "m5_N5_solution": (
        5,
        ((F(4, 21), F(29, 105)), (F(41, 105), F(10, 21))),
        F(6, 35),
    ),
    "m5_N6_solution": (
        5,
        (
            (F(2, 21), F(29, 210)),
            (F(41, 210), F(5, 21)),
            (F(25, 42), F(67, 105)),
            (F(73, 105), F(31, 42)),
        ),
        F(6, 35),
    ),
    "m8_N5_solution": (
        8,
        (
            (F(7, 120), F(13, 120)),
            (F(29, 240), F(119, 960)),
            (F(11, 60), F(7, 30)),
            (F(14, 15), F(59, 60)),
        ),
        F(49, 320),
    ),
    "m9_N5_solution": (
        9,
        (
            (F(39, 77), F(386, 693)),
            (F(428, 693), F(463, 693)),
            (F(4237, 6237), F(4244, 6237)),
            (F(505, 693), F(60, 77)),
        ),
        F(136, 891),
    ),
}


def verify(name: str, m: int, intervals: tuple[tuple[F, F], ...], expected: F) -> None:
    assert intervals
    for index, (left, right) in enumerate(intervals):
        assert F(0) <= left < right <= F(1), (name, index, left, right)
        if index:
            assert intervals[index - 1][1] <= left, (name, index, intervals)

    measure = sum((right - left for left, right in intervals), F(0))
    assert measure == expected, (name, measure, expected)

    checked = 0
    positive_slacks: list[F] = []
    tight_sides = 0
    for i, j in combinations_with_replacement(range(len(intervals)), 2):
        for ell in range(len(intervals)):
            ai, bi = intervals[i]
            aj, bj = intervals[j]
            ae, be = intervals[ell]
            lower = ai + aj - m * be
            upper = bi + bj - m * ae
            lift = lower.numerator // lower.denominator
            left_slack = lower - lift
            right_slack = lift + 1 - upper
            assert lower < upper, (name, i, j, ell, lower, upper)
            assert left_slack >= 0 and right_slack >= 0, (
                name,
                i,
                j,
                ell,
                lift,
                lower,
                upper,
            )
            for slack in (left_slack, right_slack):
                if slack == 0:
                    tight_sides += 1
                else:
                    positive_slacks.append(slack)
            checked += 1

    print(
        f"{name}: m={m}, intervals={len(intervals)}, triples={checked}, "
        f"measure={measure}, tight_sides={tight_sides}, "
        f"min_positive_slack={min(positive_slacks)}"
    )


def main() -> None:
    for name, (m, intervals, expected) in CONSTRUCTIONS.items():
        verify(name, m, intervals, expected)
    print("All rational constructions are exactly m-sum-free.")


if __name__ == "__main__":
    main()
