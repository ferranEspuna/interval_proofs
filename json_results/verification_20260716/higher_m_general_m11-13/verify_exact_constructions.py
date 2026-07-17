#!/usr/bin/env python3
"""Verify exact open-interval certificates extracted from the m=12,13 runs."""

from fractions import Fraction as F
from math import floor


CASES = {
    "m12_N5": (
        12,
        F(145, 1008),
        [
            (F(1, 140), F(1, 28)),
            (F(53, 70), F(1, 28)),
            (F(4201, 5040), F(1, 1008)),
            (F(353, 420), F(1, 28)),
            (F(97, 105), F(1, 28)),
        ],
    ),
    "m13_N5": (
        13,
        F(73, 507),
        [
            (F(8, 165), F(7, 195)),
            (F(269, 2145), F(7, 195)),
            (F(5477, 27885), F(1, 2535)),
            (F(434, 2145), F(7, 195)),
            (F(599, 2145), F(7, 195)),
        ],
    ),
    "m12_two_extra": (
        12,
        F(73, 504),
        [
            (F(17, 420), F(1, 28)),
            (F(13, 105), F(1, 28)),
            (F(29, 140), F(1, 28)),
            (F(67, 70), F(1, 28)),
            (F(67, 2520), F(1, 1008)),
            (F(169, 5040), F(1, 1008)),
        ],
    ),
    "m13_two_extra": (
        13,
        F(122, 845),
        [
            (F(74, 2145), F(7, 195)),
            (F(239, 2145), F(7, 195)),
            (F(404, 2145), F(7, 195)),
            (F(158, 165), F(7, 195)),
            (F(797, 27885), F(1, 2535)),
            (F(632, 27885), F(1, 2535)),
        ],
    ),
    "m12_three_extra": (
        12,
        F(251, 1728),
        [
            (F(17, 420), F(1, 28)),
            (F(13, 105), F(1, 28)),
            (F(29, 140), F(1, 28)),
            (F(67, 70), F(1, 28)),
            (F(139, 840), F(1, 1008)),
            (F(7103, 60480), F(5, 12096)),
            (F(23, 280), F(1, 1008)),
        ],
    ),
    "m16_four_extra": (
        16,
        F(9, 64),
        [
            (F(31, 1008), F(1, 36)),
            (F(47, 504), F(1, 36)),
            (F(157, 1008), F(1, 36)),
            (F(55, 252), F(1, 36)),
            (F(61, 63), F(1, 36)),
            (F(433, 16128), F(1, 2304)),
            (F(185, 8064), F(1, 2304)),
            (F(689, 8064), F(1, 2304)),
            (F(1441, 16128), F(1, 2304)),
        ],
    ),
    "m17_four_extra": (
        17,
        F(769, 5491),
        [
            (F(44, 1615), F(9, 323)),
            (F(139, 1615), F(9, 323)),
            (F(234, 1615), F(9, 323)),
            (F(329, 1615), F(9, 323)),
            (F(92, 95), F(9, 323)),
            (F(2268, 27455), F(1, 5491)),
            (F(3218, 27455), F(1, 5491)),
            (F(3883, 27455), F(1, 5491)),
            (F(1603, 27455), F(1, 5491)),
        ],
    ),
    "m20_six_extra": (
        20,
        F(303, 2200),
        [
            (F(49, 1980), F(1, 44)),
            (F(37, 495), F(1, 44)),
            (F(247, 1980), F(1, 44)),
            (F(173, 990), F(1, 44)),
            (F(89, 396), F(1, 44)),
            (F(193, 198), F(1, 44)),
            (F(2861, 39600), F(1, 4400)),
            (F(1381, 19800), F(1, 4400)),
            (F(2371, 19800), F(1, 4400)),
            (F(4841, 39600), F(1, 4400)),
            (F(391, 19800), F(1, 4400)),
            (F(881, 39600), F(1, 4400)),
        ],
    ),
    "m21_six_extra": (
        21,
        F(464, 3381),
        [
            (F(206, 9177), F(11, 483)),
            (F(643, 9177), F(11, 483)),
            (F(360, 3059), F(11, 483)),
            (F(1517, 9177), F(11, 483)),
            (F(1954, 9177), F(11, 483)),
            (F(426, 437), F(11, 483)),
            (F(335, 21413), F(1, 10143)),
            (F(3452, 192717), F(1, 10143)),
            (F(3889, 192717), F(1, 10143)),
            (F(13066, 192717), F(1, 10143)),
            (F(12629, 192717), F(1, 10143)),
            (F(4064, 64239), F(1, 10143)),
        ],
    ),
}


def verify_case(label, m, expected_measure, start_lengths):
    intervals = [(start, start + length) for start, length in start_lengths]
    assert sum(right - left for left, right in intervals) == expected_measure
    assert all(F(0) <= left < right <= F(1) for left, right in intervals)

    ordered = sorted(intervals)
    assert all(right <= next_left for (_, right), (next_left, _) in zip(ordered, ordered[1:]))

    endpoint_slacks = []
    triple_count = 0
    for r in range(len(intervals)):
        for s in range(r, len(intervals)):
            for t in range(len(intervals)):
                a_r, b_r = intervals[r]
                a_s, b_s = intervals[s]
                a_t, b_t = intervals[t]
                left = a_r + a_s - m * b_t
                right = b_r + b_s - m * a_t
                integer_lift = floor(left)

                # The image is the open interval (left, right).  Containment in
                # [n, n+1] therefore excludes every integer even when equality
                # occurs at an endpoint.
                assert integer_lift <= left < right <= integer_lift + 1
                endpoint_slacks.extend(
                    (left - integer_lift, F(integer_lift + 1) - right)
                )
                triple_count += 1

    positive_slacks = [slack for slack in endpoint_slacks if slack > 0]
    print(
        f"{label}: measure={expected_measure}, intervals={len(intervals)}, "
        f"triples={triple_count}, zero_endpoint_slacks="
        f"{sum(slack == 0 for slack in endpoint_slacks)}, "
        f"minimum_positive_endpoint_slack={min(positive_slacks)}"
    )


if __name__ == "__main__":
    for case_label, case_data in CASES.items():
        verify_case(case_label, *case_data)
