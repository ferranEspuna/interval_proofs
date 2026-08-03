#!/usr/bin/env python3
"""Generate exact project constructions and shareable visualizer links.

The interval formulas in the research status are evaluated with
``fractions.Fraction``.  Before a link is printed, every lifted interval

    I_i + I_j - m I_l

is checked exactly to lie in a unit gap around the requested missing point.
The conversion to floating point happens only when the website state is
created.

Examples
--------

Generate the optimized equally-spaced construction for ``m=20``::

    python3 construction_visualizer_links.py equally-spaced --m 20

Generate either of the two added-tail families from the status document::

    python3 construction_visualizer_links.py mod0-tail --m 20
    python3 construction_visualizer_links.py mod1-tail --m 21

Generate the competing mod-0 hybrid branch containing the exceptional
``m=12`` short interval::

    python3 construction_visualizer_links.py mod0-hybrid --m 12

Print a Markdown inventory of status-document links::

    python3 construction_visualizer_links.py status

Refresh the LaTeX package used to link construction mentions directly::

    python3 construction_visualizer_links.py latex-package \\
        --output latex/visualizer_links.sty
"""

from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass
from fractions import Fraction as F
from itertools import combinations_with_replacement
import json
from math import floor, gcd
from pathlib import Path
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


DEFAULT_VISUALIZER_URL = "https://ferranespuna.github.io/interval_proofs/"
VISUALIZER_BASE_COLORS = (
    "#ef4444",
    "#3b82f6",
    "#f59e0b",
    "#10b981",
    "#8b5cf6",
    "#ec4899",
    "#06b6d4",
)


@dataclass(frozen=True)
class Interval:
    start: F
    length: F
    label: str

    @property
    def end(self) -> F:
        return self.start + self.length


@dataclass(frozen=True)
class Construction:
    slug: str
    title: str
    description: str
    m: int
    intervals: tuple[Interval, ...]
    missing_point: F = F(0)

    @property
    def measure(self) -> F:
        return sum((interval.length for interval in self.intervals), F(0))


@dataclass(frozen=True)
class ExactCheck:
    interval_count: int
    lifted_interaction_count: int
    zero_endpoint_slacks: int
    minimum_positive_slack: F | None


def fraction_text(value: F) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def interval_from_endpoints(start: F, end: F, label: str) -> Interval:
    if end <= start:
        raise ValueError(f"invalid interval endpoints for {label}: {start}, {end}")
    return Interval(start=start, length=end - start, label=label)


def sorted_intervals(intervals: tuple[Interval, ...] | list[Interval]) -> tuple[Interval, ...]:
    return tuple(sorted(intervals, key=lambda interval: (interval.start, interval.end)))


def exact_check(construction: Construction) -> ExactCheck:
    """Verify geometry and the full lifted open-interval certificate exactly."""

    intervals = sorted_intervals(construction.intervals)
    if not intervals:
        raise ValueError("a construction must contain at least one interval")

    for interval in intervals:
        if not (F(0) <= interval.start < interval.end <= F(1)):
            raise ValueError(
                f"{construction.slug}: {interval.label} is not non-wrapping in [0,1]"
            )
    for left, right in zip(intervals, intervals[1:]):
        if left.end > right.start:
            raise ValueError(
                f"{construction.slug}: {left.label} overlaps {right.label}"
            )

    interaction_count = 0
    zero_slacks = 0
    minimum_positive_slack: F | None = None
    for first_index, second_index in combinations_with_replacement(
        range(len(intervals)), 2
    ):
        first = intervals[first_index]
        second = intervals[second_index]
        for third in intervals:
            lifted_left = (
                first.start
                + second.start
                - construction.m * third.end
                - construction.missing_point
            )
            lifted_right = (
                first.end
                + second.end
                - construction.m * third.start
                - construction.missing_point
            )
            integer_lift = floor(lifted_left)
            if not (
                F(integer_lift) <= lifted_left
                < lifted_right
                <= F(integer_lift + 1)
            ):
                raise ValueError(
                    f"{construction.slug}: failed interaction "
                    f"{first.label}+{second.label}-{construction.m}{third.label}; "
                    f"shifted image is ({lifted_left}, {lifted_right})"
                )
            for slack in (
                lifted_left - integer_lift,
                integer_lift + 1 - lifted_right,
            ):
                if slack == 0:
                    zero_slacks += 1
                elif minimum_positive_slack is None or slack < minimum_positive_slack:
                    minimum_positive_slack = slack
            interaction_count += 1

    return ExactCheck(
        interval_count=len(intervals),
        lifted_interaction_count=interaction_count,
        zero_endpoint_slacks=zero_slacks,
        minimum_positive_slack=minimum_positive_slack,
    )


def optimized_q(m: int, tie_choice: str = "larger") -> int:
    if m < 3:
        raise ValueError("m must be at least 3")
    if tie_choice not in {"larger", "smaller"}:
        raise ValueError("tie_choice must be 'larger' or 'smaller'")
    admissible = [q for q in range(1, m + 1) if 2 * q < m + 2]
    score = lambda q: q * (m - 2 * q + 2)
    best_score = max(score(q) for q in admissible)
    choices = [q for q in admissible if score(q) == best_score]
    return max(choices) if tie_choice == "larger" else min(choices)


def equally_spaced_parameters(m: int, q: int) -> tuple[F, F, F]:
    if m < 3:
        raise ValueError("m must be at least 3")
    if q < 1 or 2 * q >= m + 2:
        raise ValueError("q must satisfy 1 <= q < (m+2)/2")
    delta = F(m - 2 * q + 2, m * (m + 2))
    real_a = -F(m) * delta / F(m - 2)
    a = real_a % 1
    b = (a + F(1, m)) % 1
    return delta, a, b


def equally_spaced_construction(
    m: int,
    *,
    q: int | None = None,
    tie_choice: str = "larger",
) -> Construction:
    selected_q = optimized_q(m, tie_choice) if q is None else q
    delta, a, _ = equally_spaced_parameters(m, selected_q)
    selected_score = selected_q * (m - 2 * selected_q + 2)
    reference_q = optimized_q(m, "larger")
    optimized_score = reference_q * (m - 2 * reference_q + 2)
    title_prefix = (
        "Optimized equally spaced construction"
        if selected_score == optimized_score
        else "Equally spaced construction"
    )
    intervals = tuple(
        Interval((a + F(r, m)) % 1, delta, f"base_{r}")
        for r in range(selected_q)
    )
    construction = Construction(
        slug=f"equally-spaced-m{m}-q{selected_q}",
        title=f"{title_prefix}, m={m}, q={selected_q}",
        description=(
            "The exact q-interval family from the equally spaced construction "
            "in the status document; q may also be supplied explicitly."
        ),
        m=m,
        intervals=sorted_intervals(intervals),
    )
    exact_check(construction)
    return construction


def two_interval_construction(m: int) -> Construction:
    if m < 4:
        raise ValueError("the status document's two-interval formula is for m >= 4")
    base = equally_spaced_construction(m, q=2)
    construction = Construction(
        slug=f"two-interval-m{m}",
        title=f"Two-interval formula example, m={m}",
        description="The q=2 equally-spaced construction of density 2(m-2)/(m(m+2)).",
        m=m,
        intervals=base.intervals,
    )
    exact_check(construction)
    return construction


def fixed_base_extra_construction(m: int, extra_count: int) -> Construction:
    """Return the canonical one- or two-extra fixed-base reconstruction."""

    if extra_count not in {1, 2}:
        raise ValueError("extra_count must be 1 or 2")
    base = equally_spaced_construction(m, tie_choice="larger")
    _, _, b = equally_spaced_parameters(m, len(base.intervals))

    if m == 4:
        starts = [F(1, 48)]
        extra_length = F(1, 192)
    elif m % 4 == 0 and m >= 8:
        extra_length = F(2, m * m * (m + 2))
        starts = [
            b - F(m - 4, 4 * m * m),
            b - F(m - 8, 4 * m * m),
        ]
        if m == 8:
            starts = starts[:1]
    elif m % 4 == 1 and m >= 9:
        extra_length = F(1, m * m * (m + 2))
        starts = [
            b - F(m - 5, 4 * m * m),
            b - F(m - 9, 4 * m * m),
        ]
        if m == 9:
            starts = starts[:1]
    else:
        raise ValueError(
            "positive canonical fixed-base extras occur for m=4, for multiples "
            "of 4 from m=8, and for m=1 mod 4 from m=9"
        )

    selected_starts = starts[:extra_count]
    intervals = list(base.intervals)
    intervals.extend(
        Interval(start, extra_length, f"extra_{index + 1}")
        for index, start in enumerate(selected_starts)
    )
    actual_count = len(selected_starts)
    construction = Construction(
        slug=f"fixed-base-{actual_count}-extra-m{m}",
        title=f"Fixed equally-spaced base plus {actual_count} extra interval(s), m={m}",
        description=(
            "Canonical exact reconstruction of the one-/two-extra fixed-base scan. "
            "For m=4,8,9 a requested second extra is necessarily absent."
        ),
        m=m,
        intervals=sorted_intervals(intervals),
    )
    exact_check(construction)
    return construction


def mod0_tail_construction(m: int) -> Construction:
    if m < 16 or m % 4 != 0:
        raise ValueError("the mod-0 doubled-tail family requires m >= 16 and m = 0 mod 4")
    q = m // 4 + 1
    base = equally_spaced_construction(m, q=q)
    _, _, b = equally_spaced_parameters(m, q)
    extra_length = F(2, m * m * (m + 2))
    tail = [
        b - F(m - 4 * j, 4 * m * m)
        for j in range(2, (m - 4) // 4 + 1)
    ]
    starts = tail + [start + F(1, m) for start in tail]
    intervals = list(base.intervals)
    intervals.extend(
        Interval(start, extra_length, f"extra_{index + 1}")
        for index, start in enumerate(starts)
    )
    construction = Construction(
        slug=f"mod0-doubled-tail-m{m}",
        title=f"Doubled-tail family for m=0 mod 4, m={m}",
        description=(
            "The fixed-base family with (m-8)/2 short components and density "
            "(m^3+4m^2+8m-64)/(8m^2(m+2))."
        ),
        m=m,
        intervals=sorted_intervals(intervals),
    )
    exact_check(construction)
    return construction


def mod0_hybrid_construction(m: int) -> Construction:
    """Return the hybrid full-extra/short-bridge branch for m=0 mod 4."""

    if m < 12 or m % 4 != 0:
        raise ValueError("the mod-0 hybrid family requires m >= 12 and m = 0 mod 4")
    q = m // 4 + 1
    k = m // 4
    base = equally_spaced_construction(m, q=q)
    _, _, b = equally_spaced_parameters(m, q)
    full_length = F(2, m * m * (m + 2))
    short_length = F(m - 2, m**3 * (m + 2))

    def tail_start(j: int) -> F:
        return b - F(m - 4 * j, 4 * m * m)

    first_full = b + F(1, 2 * m)
    second_full = first_full + F(1, m)
    short_end = tail_start(2) + F(1, m) + full_length
    starts_and_lengths = [
        (first_full, full_length),
        (second_full, full_length),
        (short_end - short_length, short_length),
    ]
    starts_and_lengths.extend(
        (tail_start(j) + F(1, m), full_length)
        for j in range(3, k)
    )
    intervals = list(base.intervals)
    intervals.extend(
        Interval(start, length, f"extra_{index + 1}")
        for index, (start, length) in enumerate(starts_and_lengths)
    )
    construction = Construction(
        slug=f"mod0-hybrid-m{m}",
        title=f"Short-bridge hybrid family for m=0 mod 4, m={m}",
        description=(
            "The competing branch containing the m=12 length "
            "h=(m-2)/(m^3(m+2)); it beats the regular doubled tail at m=12 "
            "but loses to it from m=16 onward."
        ),
        m=m,
        intervals=sorted_intervals(intervals),
    )
    exact_check(construction)
    return construction


def mod1_tail_construction(m: int) -> Construction:
    if m < 13 or m % 4 != 1:
        raise ValueError("the mod-1 doubled-tail family requires m >= 13 and m = 1 mod 4")
    q = (m + 3) // 4
    base = equally_spaced_construction(m, q=q)
    _, _, b = equally_spaced_parameters(m, q)
    extra_length = F(1, m * m * (m + 2))
    tail = [
        b - F(m - (4 * j + 1), 4 * m * m)
        for j in range(2, (m - 5) // 4 + 1)
    ]
    starts = tail + [start + F(1, m) for start in tail]
    intervals = list(base.intervals)
    intervals.extend(
        Interval(start, extra_length, f"extra_{index + 1}")
        for index, start in enumerate(starts)
    )
    construction = Construction(
        slug=f"mod1-doubled-tail-m{m}",
        title=f"Doubled-tail family for m=1 mod 4, m={m}",
        description=(
            "The fixed-base family with (m-9)/2 short components and density "
            "(m^3+4m^2+7m-36)/(8m^2(m+2))."
        ),
        m=m,
        intervals=sorted_intervals(intervals),
    )
    exact_check(construction)
    return construction


def _explicit(
    slug: str,
    title: str,
    description: str,
    m: int,
    endpoint_pairs: list[tuple[F, F]],
    *,
    missing_point: F = F(0),
) -> Construction:
    construction = Construction(
        slug=slug,
        title=title,
        description=description,
        m=m,
        intervals=sorted_intervals(
            [
                interval_from_endpoints(start, end, f"A{index + 1}")
                for index, (start, end) in enumerate(endpoint_pairs)
            ]
        ),
        missing_point=missing_point,
    )
    exact_check(construction)
    return construction


def named_construction(name: str) -> Construction:
    key = name.lower()
    if key == "m3-endpoint":
        return _explicit(
            "m3-open-endpoint-configuration",
            "Exceptional m=3 open two-interval endpoint configuration",
            (
                "The representative printed in the status document.  It is a "
                "translated-missing-point construction (missing point 1/5), not "
                "a representative with missing point 0."
            ),
            3,
            [(F(0), F(1, 10)), (F(1, 2), F(3, 5))],
            missing_point=F(1, 5),
        )
    if key == "m3-sum-free":
        return _explicit(
            "m3-open-endpoint-sum-free-translate",
            "Sum-free translate of the exceptional m=3 endpoint configuration",
            "Translate the displayed endpoint configuration by its missing point 1/5.",
            3,
            [(F(1, 5), F(3, 10)), (F(7, 10), F(4, 5))],
        )
    if key == "a4":
        return _explicit(
            "a4",
            "Explicit A_4 construction",
            "Three intervals, measure 11/64.",
            4,
            [
                (F(1, 3), F(5, 12)),
                (F(25, 48), F(101, 192)),
                (F(7, 12), F(2, 3)),
            ],
        )
    if key == "a5":
        return _explicit(
            "a5",
            "Explicit A_5 construction",
            "Two intervals, measure 6/35.",
            5,
            [(F(2, 35), F(1, 7)), (F(6, 7), F(33, 35))],
        )
    if key == "a5-split":
        return _explicit(
            "a5-twofold-preimage",
            "Four-component twofold preimage of A_5",
            "The four positive intervals from the six-variable m=5 run, each of length 3/70.",
            5,
            [
                (F(1, 35), F(1, 14)),
                (F(3, 7), F(33, 70)),
                (F(37, 70), F(4, 7)),
                (F(13, 14), F(34, 35)),
            ],
        )
    if key == "a8":
        return _explicit(
            "a8",
            "Explicit A_8 construction",
            "Four intervals, measure 49/320.",
            8,
            [
                (F(7, 120), F(13, 120)),
                (F(29, 240), F(119, 960)),
                (F(11, 60), F(7, 30)),
                (F(14, 15), F(59, 60)),
            ],
        )
    if key == "a9":
        return _explicit(
            "a9",
            "Explicit A_9 construction",
            "Four intervals, measure 136/891.",
            9,
            [
                (F(39, 77), F(386, 693)),
                (F(428, 693), F(463, 693)),
                (F(4237, 6237), F(4244, 6237)),
                (F(505, 693), F(60, 77)),
            ],
        )
    if key == "m12-six":
        construction = fixed_base_extra_construction(12, 2)
        return Construction(
            slug="m12-earlier-six-interval",
            title="Earlier six-interval m=12 construction",
            description="Equally-spaced base plus two intervals of length 1/1008; measure 73/504.",
            m=12,
            intervals=construction.intervals,
        )
    if key == "a12":
        return _explicit(
            "a12",
            "Exceptional seven-interval A_12 construction",
            "Four base intervals plus lengths 1/1008, 5/12096, 1/1008; measure 251/1728.",
            12,
            [
                (F(17, 420), F(8, 105)),
                (F(23, 280), F(419, 5040)),
                (F(7103, 60480), F(33, 280)),
                (F(13, 105), F(67, 420)),
                (F(139, 840), F(839, 5040)),
                (F(29, 140), F(17, 70)),
                (F(67, 70), F(139, 140)),
            ],
        )
    if key == "a13":
        return _explicit(
            "a13",
            "Explicit six-interval A_13 construction",
            "Four base intervals plus two intervals of length 1/2535; measure 122/845.",
            13,
            [
                (F(632, 27885), F(643, 27885)),
                (F(797, 27885), F(808, 27885)),
                (F(74, 2145), F(151, 2145)),
                (F(239, 2145), F(316, 2145)),
                (F(404, 2145), F(481, 2145)),
                (F(2054, 2145), F(2131, 2145)),
            ],
        )
    if key == "m16-three":
        base = equally_spaced_construction(16, q=5)
        extra_length = F(1, 2304)
        construction = Construction(
            slug="m16-three-extra-incumbent",
            title="Three-extra m=16 incumbent",
            description=(
                "The optimized five-interval base plus three intervals of length "
                "1/2304; measure 323/2304."
            ),
            m=16,
            intervals=sorted_intervals(
                list(base.intervals)
                + [
                    Interval(start, extra_length, f"extra_{index + 1}")
                    for index, start in enumerate(
                        (F(307, 16128), F(185, 8064), F(433, 16128))
                    )
                ]
            ),
        )
        exact_check(construction)
        return construction
    if key == "m17-three":
        base = equally_spaced_construction(17, q=5)
        extra_length = F(1, 5491)
        construction = Construction(
            slug="m17-three-extra-incumbent",
            title="Three-extra m=17 incumbent",
            description=(
                "The optimized five-interval base plus three intervals of length "
                "1/5491; measure 768/5491."
            ),
            m=17,
            intervals=sorted_intervals(
                list(base.intervals)
                + [
                    Interval(start, extra_length, f"extra_{index + 1}")
                    for index, start in enumerate(
                        (F(558, 27455), F(653, 27455), F(2173, 27455))
                    )
                ]
            ),
        )
        exact_check(construction)
        return construction
    choices = ", ".join(NAMED_CHOICES)
    raise ValueError(f"unknown named construction {name!r}; choose one of: {choices}")


NAMED_CHOICES = (
    "m3-endpoint",
    "m3-sum-free",
    "a4",
    "a5",
    "a5-split",
    "a8",
    "a9",
    "m12-six",
    "a12",
    "a13",
    "m16-three",
    "m17-three",
)


def interval_visualizer_state(construction: Construction) -> dict[str, object]:
    intervals = sorted_intervals(construction.intervals)
    return {
        "v": 1,
        "mode": "interval",
        "intervals": [
            {
                "id": index + 1,
                "start": float(interval.start),
                "width": float(interval.length),
                "color": VISUALIZER_BASE_COLORS[index % len(VISUALIZER_BASE_COLORS)],
            }
            for index, interval in enumerate(intervals)
        ],
        "m": construction.m,
        "fixTotalLength": False,
        "targetTotalLength": float(construction.measure),
        "hiddenMixedComboKeys": [],
    }


def encode_visualizer_state(state: dict[str, object]) -> str:
    state_json = json.dumps(state, ensure_ascii=False, separators=(",", ":"))
    return base64.urlsafe_b64encode(state_json.encode("utf-8")).decode("ascii").rstrip("=")


def visualizer_state_url(
    state: dict[str, object],
    *,
    base_url: str = DEFAULT_VISUALIZER_URL,
) -> str:
    split_url = urlsplit(base_url)
    query = dict(parse_qsl(split_url.query, keep_blank_values=True))
    query["state"] = encode_visualizer_state(state)
    return urlunsplit(
        (
            split_url.scheme,
            split_url.netloc,
            split_url.path,
            urlencode(query),
            split_url.fragment,
        )
    )


def construction_visualizer_url(
    construction: Construction,
    *,
    base_url: str = DEFAULT_VISUALIZER_URL,
) -> str:
    return visualizer_state_url(interval_visualizer_state(construction), base_url=base_url)


def is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value in {2, 3}:
        return True
    if value % 2 == 0 or value % 3 == 0:
        return False
    divisor = 5
    while divisor * divisor <= value:
        if value % divisor == 0 or value % (divisor + 2) == 0:
            return False
        divisor += 6
    return True


def candela_setup(m: int, n: int | None = None) -> tuple[dict[str, object], dict[str, object]]:
    """Build and exactly check the paper's finite-group lemma preset."""

    if not (3 <= m <= 54):
        raise ValueError("the deployed visualizer supports 3 <= m <= 54")
    max_n = (12000 - 1) // (4 * m * m)
    if n is None:
        n = next(
            (candidate for candidate in range(1, max_n + 1) if is_prime(4 * m * m * candidate + 1)),
            None,
        )
        if n is None:
            raise ValueError(f"no displayed prime p=4m^2n+1 is available for m={m}")
    if not (1 <= n <= max_n):
        raise ValueError(f"n must lie in [1,{max_n}] for the deployed visualizer")
    p = 4 * m * m * n + 1
    if not is_prime(p):
        raise ValueError(f"p=4m^2n+1={p} is not prime")

    residue = m % 4
    if residue == 0:
        lambda_value, mu, extra = m, m // 4, "none"
    elif residue == 1:
        lambda_value, mu, extra = m, (m - 1) // 4, "none"
    elif residue == 2:
        lambda_value, mu, extra = m - 1, (m - 2) // 4, "tail-2"
    else:
        lambda_value, mu, extra = m, (m - 3) // 4, "tail-3"

    values = {
        x % p
        for x in range(4 * m * n + 1, 2 * lambda_value * m * n + 1)
        if x % m <= mu
    }
    if extra == "tail-2":
        extra_residue = (m + 2) // 4
        values.update(
            (t * m + extra_residue) % p
            for t in range(m * n, 2 * (m - 1) * n)
        )
    if extra == "tail-3":
        extra_residue = (m + 1) // 4
        values.update(
            (t * m + extra_residue) % p
            for t in range(m * n, 2 * m * n)
        )

    dilation = 4 * m * n
    dilated = {(dilation * value) % p for value in values}
    m_values = {(m * value) % p for value in dilated}
    sum_values = {(left + right) % p for left in dilated for right in dilated}
    overlap = sum_values & m_values
    if overlap:
        raise ValueError(f"finite-group exact check failed with {len(overlap)} overlaps")

    state: dict[str, object] = {
        "v": 2,
        "mode": "candela",
        "m": m,
        "n": n,
        "p": p,
        "recipe": "lemma",
        "lambda": lambda_value,
        "mu": mu,
        "manualLambda": lambda_value,
        "manualMu": mu,
        "dilation": dilation,
    }
    metadata: dict[str, object] = {
        "m": m,
        "n": n,
        "p": p,
        "size": len(dilated),
        "density": F(len(dilated), p),
        "paper_density": F(len(dilated), p - 1),
        "dilation": dilation,
        "gcd_dilation_p": gcd(dilation, p),
    }
    return state, metadata


def print_construction(construction: Construction, base_url: str) -> None:
    check = exact_check(construction)
    print(construction.title)
    print(construction.description)
    print(f"m: {construction.m}")
    print(f"measure: {fraction_text(construction.measure)} ({float(construction.measure):.12g})")
    print(f"missing point: {fraction_text(construction.missing_point)}")
    print("intervals (open):")
    for interval in sorted_intervals(construction.intervals):
        print(
            f"  {interval.label}: ({fraction_text(interval.start)}, "
            f"{fraction_text(interval.end)}) length={fraction_text(interval.length)}"
        )
    print(
        "exact certificate: "
        f"{check.lifted_interaction_count} lifted interactions, "
        f"{check.zero_endpoint_slacks} tight endpoint sides"
    )
    print("state JSON:")
    print(json.dumps(interval_visualizer_state(construction), indent=2))
    print("visualizer:")
    print(construction_visualizer_url(construction, base_url=base_url))


def markdown_link(construction: Construction, base_url: str) -> str:
    check = exact_check(construction)
    url = construction_visualizer_url(construction, base_url=base_url)
    missing = (
        "sum-free (missing 0)"
        if construction.missing_point == 0
        else f"missing {fraction_text(construction.missing_point)}"
    )
    return (
        f"- [{construction.title}]({url}) — density "
        f"{fraction_text(construction.measure)}, {len(construction.intervals)} intervals, "
        f"{missing}; exact replay: {check.lifted_interaction_count} interactions."
    )


def status_interval_constructions() -> list[Construction]:
    """Return every exact interval state cited by the project documentation."""

    constructions = [named_construction(name) for name in NAMED_CHOICES]
    constructions.extend(equally_spaced_construction(m) for m in range(3, 16))
    constructions.extend(
        [
            equally_spaced_construction(12, tie_choice="smaller"),
            equally_spaced_construction(12, q=2),
            equally_spaced_construction(20),
            two_interval_construction(20),
            two_interval_construction(87),
            fixed_base_extra_construction(4, 1),
            fixed_base_extra_construction(8, 1),
            fixed_base_extra_construction(9, 1),
            fixed_base_extra_construction(12, 1),
            fixed_base_extra_construction(12, 2),
            fixed_base_extra_construction(13, 1),
            fixed_base_extra_construction(13, 2),
            mod0_hybrid_construction(12),
            mod0_hybrid_construction(16),
            mod0_tail_construction(16),
            mod1_tail_construction(13),
            mod1_tail_construction(17),
            mod0_tail_construction(20),
            mod1_tail_construction(21),
        ]
    )
    slugs = [construction.slug for construction in constructions]
    if len(slugs) != len(set(slugs)):
        raise ValueError("the documented construction inventory contains duplicate slugs")
    return constructions


def latex_link_inventory(base_url: str) -> list[tuple[str, str]]:
    """Return semantic LaTeX keys and their exactly checked visualizer URLs."""

    entries: list[tuple[str, str]] = []
    for construction in status_interval_constructions():
        exact_check(construction)
        entries.append(
            (
                construction.slug,
                construction_visualizer_url(construction, base_url=base_url),
            )
        )
    candela_state, candela_metadata = candela_setup(7, 1)
    entries.append(
        (
            f"candela-m7-p{candela_metadata['p']}",
            visualizer_state_url(candela_state, base_url=base_url),
        )
    )
    for slug, _ in entries:
        if re.fullmatch(r"[a-z0-9-]+", slug) is None:
            raise ValueError(f"LaTeX visualizer slug is not csname-safe: {slug!r}")
    return entries


def latex_package_text(base_url: str) -> str:
    """Generate the shared package that makes construction names direct links."""

    lines = [
        r"\NeedsTeXFormat{LaTeX2e}",
        r"\ProvidesPackage{visualizer_links}[2026/08/03 generated construction links]",
        r"\RequirePackage{xcolor}",
        r"\RequirePackage{hyperref}",
        r"\definecolor{VisualizerLinkColor}{RGB}{0,82,155}",
        r"\newcommand{\DeclareVisualizerLink}[2]{%",
        r"  \expandafter\def\csname intervalproofs@visualizer@#1\endcsname{#2}%",
        r"}",
        r"\DeclareRobustCommand{\Visualizer}[2]{%",
        r"  \begingroup",
        r"  \ifcsname intervalproofs@visualizer@#1\endcsname",
        r"    \edef\VisualizerTarget{\csname intervalproofs@visualizer@#1\endcsname}%",
        r"    \href{\VisualizerTarget}{{\color{VisualizerLinkColor}#2}}%",
        r"  \else",
        r"    \PackageError{visualizer_links}{Unknown visualizer construction `#1'}%",
        r"      {Regenerate visualizer_links.sty from construction_visualizer_links.py.}%",
        r"    #2%",
        r"  \fi",
        r"  \endgroup",
        r"}",
        "",
    ]
    for slug, url in latex_link_inventory(base_url):
        lines.append(
            rf"\DeclareVisualizerLink{{{slug}}}{{\detokenize{{{url}}}}}"
        )
    lines.extend(["", r"\endinput", ""])
    return "\n".join(lines)


def status_links_text(base_url: str) -> str:
    """Generate the checked Markdown catalog without relying on shell redirection."""

    lines = [
        "# Project construction visualizer links",
        "",
        "This catalog is generated by `python3 construction_visualizer_links.py status`.",
        (
            "Every interval construction is checked with exact rational arithmetic before "
            "its link is emitted. General families can be generated for other admissible "
            "values of `m` with the commands documented in [README.md](README.md)."
        ),
        "",
        "### Explicit and exceptional constructions",
        "",
    ]
    for name in NAMED_CHOICES:
        if name == "m16-three":
            lines.append("")
        lines.append(markdown_link(named_construction(name), base_url))

    lines.extend(
        ["", "### Optimized equally-spaced family (the table in the status document)", ""]
    )
    for m in range(3, 16):
        lines.append(markdown_link(equally_spaced_construction(m), base_url))
    lines.extend(["", "### Additional equally-spaced examples used in the report", ""])
    lines.append(markdown_link(equally_spaced_construction(12, tie_choice="smaller"), base_url))
    lines.append(markdown_link(equally_spaced_construction(12, q=2), base_url))
    lines.append(markdown_link(equally_spaced_construction(20), base_url))

    lines.extend(["", "### Other general-family examples", ""])
    examples = [
        two_interval_construction(20),
        two_interval_construction(87),
        fixed_base_extra_construction(4, 1),
        fixed_base_extra_construction(8, 1),
        fixed_base_extra_construction(9, 1),
        fixed_base_extra_construction(12, 1),
        fixed_base_extra_construction(12, 2),
        fixed_base_extra_construction(13, 1),
        fixed_base_extra_construction(13, 2),
        mod0_hybrid_construction(12),
        mod0_hybrid_construction(16),
        mod0_tail_construction(16),
        mod1_tail_construction(13),
        mod1_tail_construction(17),
        mod0_tail_construction(20),
        mod1_tail_construction(21),
    ]
    for construction in examples:
        lines.append(markdown_link(construction, base_url))

    lines.extend(["", "### Finite-group comparison construction", ""])
    state, metadata = candela_setup(7, 1)
    url = visualizer_state_url(state, base_url=base_url)
    lines.append(
        f"- [Candela--Gonzalez-Sanchez--Grynkiewicz example, "
        f"m=7, p={metadata['p']}]({url}) — |A|={metadata['size']}, "
        f"density {fraction_text(metadata['density'])}; exact finite-group replay passed."
    )
    return "\n".join(lines) + "\n"


def print_status_links(base_url: str) -> None:
    print(status_links_text(base_url), end="")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--visualizer-url",
        default=DEFAULT_VISUALIZER_URL,
        help="base URL for generated state links",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    equal_parser = subparsers.add_parser("equally-spaced", help="general q-interval family")
    equal_parser.add_argument("--m", type=int, required=True)
    equal_parser.add_argument("--q", type=int)
    equal_parser.add_argument("--tie-choice", choices=("larger", "smaller"), default="larger")

    two_parser = subparsers.add_parser("two-interval", help="q=2 observed formula")
    two_parser.add_argument("--m", type=int, required=True)

    fixed_parser = subparsers.add_parser("fixed-base", help="canonical one-/two-extra family")
    fixed_parser.add_argument("--m", type=int, required=True)
    fixed_parser.add_argument("--extra-count", type=int, choices=(1, 2), required=True)

    mod0_parser = subparsers.add_parser("mod0-tail", help="m=0 mod 4 doubled-tail family")
    mod0_parser.add_argument("--m", type=int, required=True)

    hybrid_parser = subparsers.add_parser(
        "mod0-hybrid", help="m=0 mod 4 short-bridge hybrid family"
    )
    hybrid_parser.add_argument("--m", type=int, required=True)

    mod1_parser = subparsers.add_parser("mod1-tail", help="m=1 mod 4 doubled-tail family")
    mod1_parser.add_argument("--m", type=int, required=True)

    named_parser = subparsers.add_parser("named", help="explicit construction from the status")
    named_parser.add_argument("name", choices=NAMED_CHOICES)

    candela_parser = subparsers.add_parser("candela", help="finite-group lemma construction")
    candela_parser.add_argument("--m", type=int, required=True)
    candela_parser.add_argument("--n", type=int)

    status_parser = subparsers.add_parser(
        "status", help="print a Markdown inventory of status-document links"
    )
    status_parser.add_argument(
        "--output",
        help="write the catalog to this path instead of standard output",
    )
    latex_parser = subparsers.add_parser(
        "latex-package", help="generate the shared LaTeX visualizer-link package"
    )
    latex_parser.add_argument(
        "--output",
        help="write the package to this path instead of standard output",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        if args.command == "status":
            catalog = status_links_text(args.visualizer_url)
            if args.output:
                output_path = Path(args.output)
                output_path.write_text(catalog, encoding="utf-8")
                print(f"Wrote {output_path}")
            else:
                print(catalog, end="")
            return
        if args.command == "latex-package":
            package = latex_package_text(args.visualizer_url)
            if args.output:
                output_path = Path(args.output)
                output_path.write_text(package, encoding="utf-8")
                print(f"Wrote {output_path}")
            else:
                print(package, end="")
            return
        if args.command == "equally-spaced":
            construction = equally_spaced_construction(
                args.m, q=args.q, tie_choice=args.tie_choice
            )
        elif args.command == "two-interval":
            construction = two_interval_construction(args.m)
        elif args.command == "fixed-base":
            construction = fixed_base_extra_construction(args.m, args.extra_count)
        elif args.command == "mod0-tail":
            construction = mod0_tail_construction(args.m)
        elif args.command == "mod0-hybrid":
            construction = mod0_hybrid_construction(args.m)
        elif args.command == "mod1-tail":
            construction = mod1_tail_construction(args.m)
        elif args.command == "named":
            construction = named_construction(args.name)
        elif args.command == "candela":
            state, metadata = candela_setup(args.m, args.n)
            print("Candela--Gonzalez-Sanchez--Grynkiewicz finite-group construction")
            for key, value in metadata.items():
                print(f"{key}: {fraction_text(value) if isinstance(value, F) else value}")
            print("state JSON:")
            print(json.dumps(state, indent=2))
            print("visualizer:")
            print(visualizer_state_url(state, base_url=args.visualizer_url))
            return
        else:  # pragma: no cover - argparse makes this unreachable.
            raise ValueError(f"unsupported command {args.command}")
        print_construction(construction, args.visualizer_url)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
