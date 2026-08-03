#!/usr/bin/env python3
"""Exact Fraction replay of the free-endpoint m=12,N=7 incumbent."""

from __future__ import annotations

from fractions import Fraction as F
from math import floor
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
SOLUTION_PATH = (
    HERE.parents[1]
    / "long_runs"
    / "m12_N7_length_order_depth2"
    / "m12_N7_lengthorder_1-5_solution.json"
)
REPORT_PATH = HERE / "unrestricted_incumbent_exact_report.json"

# Increasing positional order in the translated-missing-point model, matching
# solver indices 0,...,6.  Adding t/(m-2) to every start converts this to an
# ordinary representative whose missing point is zero.
TRANSLATED_MISSING_POINT = F(23, 28)
TRANSLATED_INTERVALS = [
    (F(0), F(5, 12096)),
    (F(5, 144), F(1, 1008)),
    (F(1, 24), F(1, 28)),
    (F(1, 8), F(1, 28)),
    (F(7, 8), F(1, 28)),
    (F(137, 144), F(1, 1008)),
    (F(23, 24), F(1, 28)),
]
INTERVALS = sorted(
    (
        ((x + TRANSLATED_MISSING_POINT / 10) % 1, alpha)
        for x, alpha in TRANSLATED_INTERVALS
    ),
    key=lambda interval: interval[0],
)


def main() -> None:
    solution = json.loads(SOLUTION_PATH.read_text(encoding="utf-8"))
    values = solution["values"]

    # Replay the final solver fixture exactly in its translated coordinates.
    maximum_saved_lift_integrality_error = 0.0
    saved_lift_count = 0
    for i, (x_i, alpha_i) in enumerate(TRANSLATED_INTERVALS):
        for j in range(i, len(TRANSLATED_INTERVALS)):
            x_j, alpha_j = TRANSLATED_INTERVALS[j]
            for ell, (x_ell, alpha_ell) in enumerate(TRANSLATED_INTERVALS):
                left = x_i + x_j - 12 * (x_ell + alpha_ell)
                right = x_i + alpha_i + x_j + alpha_j - 12 * x_ell
                lift = floor(left - TRANSLATED_MISSING_POINT)
                assert (
                    lift + TRANSLATED_MISSING_POINT
                    <= left
                    < right
                    <= lift + 1 + TRANSLATED_MISSING_POINT
                )
                saved_value = float(values[f"n_{i}-{j}-{ell}"])
                saved_lift = round(saved_value)
                maximum_saved_lift_integrality_error = max(
                    maximum_saved_lift_integrality_error,
                    abs(saved_value - saved_lift),
                )
                assert saved_lift == lift
                saved_lift_count += 1

    assert all(F(0) <= x < x + alpha <= F(1) for x, alpha in INTERVALS)
    assert all(
        x + alpha <= y
        for (x, alpha), (y, _) in zip(INTERVALS, INTERVALS[1:])
    )

    interaction_count = 0
    zero_endpoint_slacks = 0
    minimum_positive_slack: F | None = None
    for i, (x_i, alpha_i) in enumerate(INTERVALS):
        for j in range(i, len(INTERVALS)):
            x_j, alpha_j = INTERVALS[j]
            for ell, (x_ell, alpha_ell) in enumerate(INTERVALS):
                left = x_i + x_j - 12 * (x_ell + alpha_ell)
                right = x_i + alpha_i + x_j + alpha_j - 12 * x_ell
                lift = floor(left)
                assert lift <= left < right <= lift + 1
                for slack in (left - lift, F(lift + 1) - right):
                    if slack == 0:
                        zero_endpoint_slacks += 1
                    elif minimum_positive_slack is None or slack < minimum_positive_slack:
                        minimum_positive_slack = slack

                interaction_count += 1

    measure = sum(alpha for _, alpha in INTERVALS)
    assert measure == F(251, 1728)
    assert interaction_count == 196
    assert zero_endpoint_slacks == 14
    assert minimum_positive_slack == F(1, 144)

    maximum_start_error = max(
        abs(float(values[f"x_{i}"]) - float(x))
        for i, (x, _) in enumerate(TRANSLATED_INTERVALS)
    )
    maximum_length_error = max(
        abs(float(values[f"alpha_{i}"]) - float(alpha))
        for i, (_, alpha) in enumerate(TRANSLATED_INTERVALS)
    )
    translated_missing_point_error = abs(
        float(values["t"]) - float(TRANSLATED_MISSING_POINT)
    )
    objective_error = abs(float(solution["optimum"]) - float(measure))
    report = {
        "m": 12,
        "interval_count": len(INTERVALS),
        "interaction_count": interaction_count,
        "saved_integer_lifts_verified": saved_lift_count,
        "exact_measure": str(measure),
        "zero_endpoint_slacks": zero_endpoint_slacks,
        "minimum_positive_endpoint_slack": str(minimum_positive_slack),
        "exact_translated_missing_point": str(TRANSLATED_MISSING_POINT),
        "floating_translated_missing_point_error": translated_missing_point_error,
        "maximum_saved_lift_integrality_error": maximum_saved_lift_integrality_error,
        "maximum_floating_start_error": maximum_start_error,
        "maximum_floating_length_error": maximum_length_error,
        "floating_objective_error": objective_error,
        "intervals": [
            {"start": str(x), "end": str(x + alpha), "length": str(alpha)}
            for x, alpha in INTERVALS
        ],
        "solver_fixture": str(SOLUTION_PATH.relative_to(HERE.parents[2])),
        "claim": (
            "exact construction certificate and final solver-incumbent replay; "
            "the exhaustive upper bound remains conditional on numerical "
            "smaller-subunion bounds"
        ),
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "intervals"}, indent=2))


if __name__ == "__main__":
    main()
