#!/usr/bin/env python3
"""Exactly reconstruct and verify the positive K=3 scan artifacts."""

from __future__ import annotations

from fractions import Fraction as F
from math import floor
import json
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
SOLVER_DIR = HERE.parent / "tiny_intervals_three_extra"
REPORT_PATH = HERE / "exact_verification_report.json"


CASES = {
    12: {
        "solution": "m12_q4_extra3_per_extra_bound_1over1008_gap0_solution.json",
        "measure": F(251, 1728),
        "extras": {
            4: (F(139, 840), F(1, 1008)),
            5: (F(7103, 60480), F(5, 12096)),
            6: (F(23, 280), F(1, 1008)),
        },
    },
    13: {
        "solution": "m13_q4_extra3_per_extra_bound_1over2535_gap0_solution.json",
        "measure": F(122, 845),
        "extras": {
            # This zero-length variable is recorded for comparison with the
            # solver output, then omitted from the interval union.
            4: (F(797, 27885), F(0)),
            5: (F(632, 27885), F(1, 2535)),
            6: (F(797, 27885), F(1, 2535)),
        },
    },
    16: {
        "solution": "m16_q5_extra3_per_extra_bound_1over2304_gap0_solution.json",
        "measure": F(323, 2304),
        "extras": {
            5: (F(433, 16128), F(1, 2304)),
            6: (F(307, 16128), F(1, 2304)),
            7: (F(185, 8064), F(1, 2304)),
        },
    },
    17: {
        "solution": "m17_q5_extra3_per_extra_bound_1over5491_gap0_solution.json",
        "measure": F(768, 5491),
        "extras": {
            5: (F(2173, 27455), F(1, 5491)),
            6: (F(653, 27455), F(1, 5491)),
            7: (F(558, 27455), F(1, 5491)),
        },
    },
}


def rational_base_by_index(
    solution: dict[str, Any],
) -> dict[int, tuple[F, F, str]]:
    m = int(solution["parameters"]["m"])
    q = int(solution["parameters"]["q"])
    delta = F(m - 2 * q + 2, m * (m + 2))
    a = (-F(m) * delta / F(m - 2)) % 1
    result = {}
    for item in solution["parameters"]["intervals"]:
        if not item["fixed_base"]:
            continue
        index = int(item["index"])
        r = int(item["label"].removeprefix("base_"))
        result[index] = ((a + F(r, m)) % 1, delta, item["label"])
    assert len(result) == q
    return result


def verify_exact_union(
    m: int, intervals_by_index: dict[int, tuple[F, F, str]]
) -> dict[str, Any]:
    ordered = sorted(
        ((x, alpha, label, index) for index, (x, alpha, label) in intervals_by_index.items())
    )
    assert all(F(0) <= x < x + alpha <= F(1) for x, alpha, _, _ in ordered)
    assert all(
        x + alpha <= y
        for (x, alpha, _, _), (y, _, _, _) in zip(ordered, ordered[1:])
    )

    interactions = []
    zero_endpoint_slacks = 0
    minimum_positive_endpoint_slack: F | None = None
    for r, (x_i, alpha_i, label_i, index_i) in enumerate(ordered):
        for x_j, alpha_j, label_j, index_j in ordered[r:]:
            for x_ell, alpha_ell, label_ell, index_ell in ordered:
                left = x_i + x_j - m * (x_ell + alpha_ell)
                right = x_i + alpha_i + x_j + alpha_j - m * x_ell
                lift = floor(left)
                assert lift <= left < right <= lift + 1
                left_slack = left - lift
                right_slack = F(lift + 1) - right
                for slack in (left_slack, right_slack):
                    if slack == 0:
                        zero_endpoint_slacks += 1
                    elif (
                        minimum_positive_endpoint_slack is None
                        or slack < minimum_positive_endpoint_slack
                    ):
                        minimum_positive_endpoint_slack = slack
                interactions.append(
                    {
                        "indices": [index_i, index_j, index_ell],
                        "labels": [label_i, label_j, label_ell],
                        "lift": lift,
                        "left_endpoint": str(left),
                        "right_endpoint": str(right),
                        "left_slack": str(left_slack),
                        "right_slack": str(right_slack),
                    }
                )

    return {
        "interval_count": len(ordered),
        "triple_count": len(interactions),
        "measure": str(sum(alpha for _, alpha, _, _ in ordered)),
        "zero_endpoint_slacks": zero_endpoint_slacks,
        "minimum_positive_endpoint_slack": str(minimum_positive_endpoint_slack),
        "intervals": [
            {
                "solver_index": index,
                "label": label,
                "start": str(x),
                "end": str(x + alpha),
                "length": str(alpha),
            }
            for x, alpha, label, index in ordered
        ],
        "lifted_interactions": interactions,
    }


def reconstruct_case(m: int, case: dict[str, Any]) -> dict[str, Any]:
    solution_path = SOLVER_DIR / case["solution"]
    solution = json.loads(solution_path.read_text())
    assert solution["success"] and solution["status_name"] == "optimal"
    assert solution["solver_details"]["mip_gap"] == 0

    intervals_by_index = rational_base_by_index(solution)
    values = solution["values"]
    extra_comparison = []
    maximum_start_error = 0.0
    maximum_length_error = 0.0
    for index, (x, alpha) in case["extras"].items():
        start_error = abs(float(values[f"x_{index}"]) - float(x))
        length_error = abs(float(values[f"alpha_{index}"]) - float(alpha))
        maximum_start_error = max(maximum_start_error, start_error)
        maximum_length_error = max(maximum_length_error, length_error)
        label = f"extra_{index - int(solution['parameters']['q'])}"
        extra_comparison.append(
            {
                "solver_index": index,
                "label": label,
                "start": str(x),
                "end": str(x + alpha),
                "length": str(alpha),
                "floating_start_error": start_error,
                "floating_length_error": length_error,
                "included_in_union": alpha > 0,
            }
        )
        if alpha > 0:
            intervals_by_index[index] = (x, alpha, label)

    exact = verify_exact_union(m, intervals_by_index)
    assert F(exact["measure"]) == case["measure"]
    assert abs(float(solution["optimum"]) - float(case["measure"])) < 1e-12

    # Check the exact intervals against the actual integer lifts in the saved
    # solver certificate, retaining original solver indices.
    saved_lift_count = 0
    for i in sorted(intervals_by_index):
        x_i, alpha_i, _ = intervals_by_index[i]
        for j in sorted(index for index in intervals_by_index if index >= i):
            x_j, alpha_j, _ = intervals_by_index[j]
            for ell in sorted(intervals_by_index):
                x_ell, alpha_ell, _ = intervals_by_index[ell]
                lift_value = values[f"n_{i}-{j}-{ell}"]
                lift = round(lift_value)
                assert abs(lift_value - lift) < 1e-9
                left = x_i + x_j - m * (x_ell + alpha_ell)
                right = x_i + alpha_i + x_j + alpha_j - m * x_ell
                assert lift <= left < right <= lift + 1
                saved_lift_count += 1
    assert saved_lift_count == exact["triple_count"]

    return {
        "m": m,
        "q": solution["parameters"]["q"],
        "solution_path": str(solution_path.relative_to(REPO_ROOT)),
        "solver_optimum": solution["optimum"],
        "solver_mip_gap": solution["solver_details"]["mip_gap"],
        "exact_measure": str(case["measure"]),
        "positive_extra_count": sum(alpha > 0 for _, alpha in case["extras"].values()),
        "maximum_floating_start_error": maximum_start_error,
        "maximum_floating_length_error": maximum_length_error,
        "extras": extra_comparison,
        "saved_integer_lifts_verified": saved_lift_count,
        "exact_replay": exact,
    }


def main() -> None:
    cases = [reconstruct_case(m, case) for m, case in CASES.items()]
    report = {
        "summary": {
            "cases_verified": len(cases),
            "lifted_images_verified": sum(
                case["exact_replay"]["triple_count"] for case in cases
            ),
            "saved_integer_lifts_verified": sum(
                case["saved_integer_lifts_verified"] for case in cases
            ),
            "maximum_floating_start_error": max(
                case["maximum_floating_start_error"] for case in cases
            ),
            "maximum_floating_length_error": max(
                case["maximum_floating_length_error"] for case in cases
            ),
        },
        "cases": cases,
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
