#!/usr/bin/env python3
"""Reconstruct and exactly verify the positive fixed-base two-extra runs.

The floating-point MILP solutions lie on a simple rational grid.  This script
does two independent finite checks:

* reconstruct every positive larger-q saved solution for ``m <= 100`` and
  replay every lifted sum-free interval containment over ``Fraction``;
* verify a uniform, solver-independent choice of the extra interval starts.

Zero-length MILP extras are discarded, since they do not define intervals.
The canonical main-scan m=100 artifact is the clean no-presolve rerun.
"""

from __future__ import annotations

import csv
from fractions import Fraction as F
from math import floor
import json
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
CAMPAIGN = HERE.parent
SCAN = CAMPAIGN / "tiny_intervals_two_extra"
REPORT_PATH = HERE / "exact_verification_report.json"


def optimized_q(m: int) -> int:
    """Return the larger maximizing q used by the scan."""
    candidates = [q for q in range(1, m + 1) if 2 * q < m + 2]
    score = lambda q: q * (m - 2 * q + 2)
    optimum = max(map(score, candidates))
    return max(q for q in candidates if score(q) == optimum)


def base_data(m: int) -> tuple[int, F, F, list[tuple[F, F, str]]]:
    q = optimized_q(m)
    delta = F(m - 2 * q + 2, m * (m + 2))
    a = (-F(m) * delta / F(m - 2)) % 1
    intervals = [
        ((a + F(r, m)) % 1, delta, f"base_{r}") for r in range(q)
    ]
    return q, delta, a, intervals


def extra_length(m: int) -> F:
    if m == 4:
        return F(1, 192)
    if m % 4 == 0:
        return F(2, m * m * (m + 2))
    if m % 4 == 1:
        return F(1, m * m * (m + 2))
    raise ValueError(f"m={m} has no positive larger-q extra in this scan")


def grid_offset(m: int) -> F:
    if m % 4 == 0:
        return F(m - 4, m - 2)
    if m % 4 == 1:
        return F(m - 8, m - 2)
    raise ValueError(f"m={m} has no positive larger-q extra in this scan")


def verify_intervals(
    m: int, intervals: list[tuple[F, F, str]]
) -> dict[str, Any]:
    """Check geometry and every open lifted image exactly."""
    ordered = sorted(intervals)
    assert all(F(0) <= x < x + alpha <= F(1) for x, alpha, _ in ordered)
    assert all(
        x + alpha <= y
        for (x, alpha, _), (y, _, _) in zip(ordered, ordered[1:])
    )

    zero_endpoint_slacks = 0
    minimum_positive_endpoint_slack: F | None = None
    triple_count = 0
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
                triple_count += 1

    return {
        "interval_count": len(ordered),
        "triple_count": triple_count,
        "measure": str(sum(alpha for _, alpha, _ in ordered)),
        "zero_endpoint_slacks": zero_endpoint_slacks,
        "minimum_positive_endpoint_slack": (
            str(minimum_positive_endpoint_slack)
            if minimum_positive_endpoint_slack is not None
            else None
        ),
        "intervals": [
            {"label": label, "start": str(x), "length": str(alpha)}
            for x, alpha, label in ordered
        ],
    }


def selected_scan_rows() -> list[dict[str, str]]:
    rows = list(csv.DictReader((SCAN / "result_summary.csv").open()))
    wanted = []
    for row in rows:
        m = int(row["m"])
        if row["branch"] != "larger":
            continue
        if m in (4, 8, 9) or (12 <= m <= 100 and m % 4 in (0, 1)):
            wanted.append(row)
    return wanted


def reconstruct_saved_solution(row: dict[str, str]) -> dict[str, Any]:
    m = int(row["m"])
    q = int(row["q"])
    assert q == optimized_q(m)

    solution_path = SCAN / row["solution"]
    solution_source = "main scan artifact"

    solution = json.loads(solution_path.read_text())
    values = solution["values"]
    g = extra_length(m)
    _, _, _, intervals = base_data(m)

    reconstructed_extras = []
    maximum_start_error = 0.0
    maximum_length_error = 0.0
    for extra_index in range(2):
        alpha_float = float(values[f"alpha_{q + extra_index}"])
        if alpha_float < float(g) / 2:
            continue

        if m == 4:
            # The sole positive m=4 interval is the special endpoint 1/48.
            x = F(1, 48)
            grid_integer = None
        else:
            offset = grid_offset(m)
            raw_integer = float(values[f"x_{q + extra_index}"]) / float(g)
            raw_integer -= float(offset)
            grid_integer = round(raw_integer)
            assert abs(raw_integer - grid_integer) < 1e-5
            x = (F(grid_integer) + offset) * g

        start_error = abs(float(values[f"x_{q + extra_index}"]) - float(x))
        length_error = abs(alpha_float - float(g))
        maximum_start_error = max(maximum_start_error, start_error)
        maximum_length_error = max(maximum_length_error, length_error)
        label = f"extra_{extra_index}"
        intervals.append((x, g, label))
        reconstructed_extras.append(
            {
                "label": label,
                "grid_integer": grid_integer,
                "start": str(x),
                "length": str(g),
                "floating_start_error": start_error,
                "floating_length_error": length_error,
            }
        )

    expected_extra_count = 1 if m in (4, 8, 9) else 2
    assert len(reconstructed_extras) == expected_extra_count
    exact = verify_intervals(m, intervals)
    expected_measure = sum(alpha for _, alpha, _ in intervals)
    assert abs(float(solution["optimum"]) - float(expected_measure)) < 2e-9

    return {
        "m": m,
        "q": q,
        "solution_source": solution_source,
        "solution_path": str(solution_path.relative_to(REPO_ROOT)),
        "solver_status": solution["status_name"],
        "solver_mip_gap": solution["solver_details"]["mip_gap"],
        "reconstructed_extras": reconstructed_extras,
        "maximum_floating_start_error": maximum_start_error,
        "maximum_floating_length_error": maximum_length_error,
        "exact_replay": exact,
    }


def canonical_intervals(m: int) -> tuple[list[tuple[F, F, str]], dict[str, Any]]:
    q, delta, a, intervals = base_data(m)
    b = (a + F(1, m)) % 1
    g = extra_length(m)

    if m == 4:
        starts = [F(1, 48)]
        formula = "special: x=1/48, alpha=1/192"
    elif m % 4 == 0:
        starts = [
            b - F(m - 4, 4 * m * m),
            b - F(m - 8, 4 * m * m),
        ]
        if m == 8:
            # The second start equals b, so retain only the genuine extra.
            starts = starts[:1]
        formula = (
            "alpha=2/[m^2(m+2)]; starts "
            "b-(m-4)/(4m^2), b-(m-8)/(4m^2)"
        )
    elif m % 4 == 1:
        starts = [
            b - F(m - 5, 4 * m * m),
            b - F(m - 9, 4 * m * m),
        ]
        if m == 9:
            # The second start equals b, so retain only the genuine extra.
            starts = starts[:1]
        formula = (
            "alpha=1/[m^2(m+2)]; starts "
            "b-(m-5)/(4m^2), b-(m-9)/(4m^2)"
        )
    else:
        raise ValueError(m)

    for index, x in enumerate(starts):
        intervals.append((x, g, f"extra_{index}"))
    metadata = {
        "m": m,
        "q": q,
        "a": str(a),
        "b": str(b),
        "delta": str(delta),
        "extra_length": str(g),
        "extra_starts": [str(x) for x in starts],
        "formula": formula,
    }
    return intervals, metadata


def main() -> None:
    rows = selected_scan_rows()
    saved = [reconstruct_saved_solution(row) for row in rows]

    canonical = []
    for m in [4, 8, 9, *range(12, 101)]:
        if m not in (4, 8, 9) and m % 4 not in (0, 1):
            continue
        intervals, metadata = canonical_intervals(m)
        metadata["exact_replay"] = verify_intervals(m, intervals)
        canonical.append(metadata)

    assert len(saved) == 48
    assert len(canonical) == 48
    assert sum(item["m"] >= 12 for item in canonical) == 45

    report = {
        "summary": {
            "saved_solutions_reconstructed": len(saved),
            "canonical_cases_verified": len(canonical),
            "two_positive_extra_cases_m_at_least_12": 45,
            "maximum_floating_start_error": max(
                item["maximum_floating_start_error"] for item in saved
            ),
            "maximum_floating_length_error": max(
                item["maximum_floating_length_error"] for item in saved
            ),
            "m100_source": next(
                item["solution_source"] for item in saved if item["m"] == 100
            ),
        },
        "saved_solution_reconstructions": saved,
        "canonical_family": canonical,
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
