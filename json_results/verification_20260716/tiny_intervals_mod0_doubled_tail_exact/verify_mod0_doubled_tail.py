#!/usr/bin/env python3
"""Exact finite verification of the doubled-tail family for m=0 (mod 4)."""

from __future__ import annotations

from fractions import Fraction as F
from math import floor
import json
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
CAMPAIGN = HERE.parent
SATURATION_DIR = CAMPAIGN / "tiny_intervals_extra_count_saturation"
REPORT_PATH = HERE / "exact_verification_report.json"


SATURATION_RECONSTRUCTIONS = [
    {
        "m": 16,
        "solver_extra_count": 4,
        "starts": [F(433, 16128), F(185, 8064), F(689, 8064), F(1441, 16128)],
    },
    {
        "m": 20,
        "solver_extra_count": 6,
        "starts": [F(2861, 39600), F(1381, 19800), F(2371, 19800),
                   F(4841, 39600), F(391, 19800), F(881, 39600)],
    },
]


def base_parameters(m: int) -> tuple[int, F, F, F]:
    assert m >= 16 and m % 4 == 0
    q = m // 4 + 1
    delta = F(1, 2 * (m + 2))
    a = (-F(m) * delta / F(m - 2)) % 1
    b = (a + F(1, m)) % 1
    return q, delta, a, b


def base_intervals(m: int) -> list[tuple[F, F, str]]:
    q, delta, a, _ = base_parameters(m)
    return [((a + F(r, m)) % 1, delta, f"base_{r}") for r in range(q)]


def doubled_tail_family(m: int) -> tuple[list[tuple[F, F, str]], dict[str, Any]]:
    q, delta, a, b = base_parameters(m)
    last_index = (m - 4) // 4
    g = F(2, m * m * (m + 2))
    tail = [b - F(m - 4 * j, 4 * m * m) for j in range(2, last_index + 1)]
    starts = tail + [start + F(1, m) for start in tail]
    intervals = base_intervals(m) + [
        (start, g, f"extra_{index + 1}") for index, start in enumerate(starts)
    ]

    extra_count = (m - 8) // 2
    assert len(starts) == extra_count
    base_density = q * delta
    gain = extra_count * g
    density = F(m**3 + 4 * m * m + 8 * m - 64, 8 * m * m * (m + 2))
    assert base_density + gain == density
    return intervals, {
        "m": m,
        "q": q,
        "a": str(a),
        "b": str(b),
        "delta": str(delta),
        "extra_count": extra_count,
        "extra_length": str(g),
        "tail_starts": [str(start) for start in tail],
        "translated_tail_starts": [str(start + F(1, m)) for start in tail],
        "base_density": str(base_density),
        "gain": str(gain),
        "density": str(density),
    }


def verify_intervals(
    m: int, intervals: list[tuple[F, F, str]]
) -> dict[str, Any]:
    ordered = sorted(intervals)
    assert all(F(0) <= x < x + alpha <= F(1) for x, alpha, _ in ordered)
    assert all(
        x + alpha <= y
        for (x, alpha, _), (y, _, _) in zip(ordered, ordered[1:])
    )

    triple_count = 0
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
                triple_count += 1

    return {
        "interval_count": len(ordered),
        "triple_count": triple_count,
        "measure": str(sum(alpha for _, alpha, _ in ordered)),
        "zero_endpoint_slacks": zero_endpoint_slacks,
        "minimum_positive_endpoint_slack": str(minimum_positive_endpoint_slack),
        "intervals": [
            {
                "label": label,
                "start": str(x),
                "end": str(x + alpha),
                "length": str(alpha),
            }
            for x, alpha, label in ordered
        ],
    }


def exact_saturation_comparisons() -> list[dict[str, Any]]:
    results = []
    for reconstruction in SATURATION_RECONSTRUCTIONS:
        m = reconstruction["m"]
        solver_extra_count = reconstruction["solver_extra_count"]
        starts = reconstruction["starts"]
        q, delta, _, _ = base_parameters(m)
        g = F(2, m * m * (m + 2))
        intervals = base_intervals(m) + [
            (start, g, f"extra_{index}") for index, start in enumerate(starts)
        ]
        exact = verify_intervals(m, intervals)
        matches = sorted(
            SATURATION_DIR.glob(f"m{m}_q{q}_extra{solver_extra_count}_*_solution.json")
        )
        assert len(matches) == 1
        solution = json.loads(matches[0].read_text())
        objective_error = float(solution["optimum"]) - float(F(exact["measure"]))
        assert abs(objective_error) < 1e-9
        results.append(
            {
                "m": m,
                "solver_extra_count": solver_extra_count,
                "solver_path": str(matches[0].relative_to(REPO_ROOT)),
                "solver_status": solution["status_name"],
                "solver_mip_gap": solution["solver_details"]["mip_gap"],
                "solver_objective_error": objective_error,
                "extra_starts": [str(start) for start in starts],
                "exact_replay": exact,
            }
        )
    return results


def numeric_saturation_artifacts() -> list[dict[str, Any]]:
    results = []
    for m in (16, 20):
        q, delta, _, _ = base_parameters(m)
        g = F(2, m * m * (m + 2))
        for path in sorted(SATURATION_DIR.glob(f"m{m}_q{q}_extra*_solution.json")):
            solution = json.loads(path.read_text())
            extra_count = int(solution["parameters"]["extra_count"])
            lengths = [
                float(solution["values"][f"alpha_{q + i}"])
                for i in range(extra_count)
            ]
            positive_count = sum(length > float(g) / 2 for length in lengths)
            reconstructed_density = q * delta + positive_count * g
            results.append(
                {
                    "m": m,
                    "solver_extra_count": extra_count,
                    "positive_extra_count_at_half_g": positive_count,
                    "path": str(path.relative_to(REPO_ROOT)),
                    "status": solution["status_name"],
                    "mip_gap": solution["solver_details"]["mip_gap"],
                    "solver_optimum": solution["optimum"],
                    "base_plus_positive_count_g": str(reconstructed_density),
                    "objective_error": float(solution["optimum"])
                    - float(reconstructed_density),
                }
            )
    return results


def main() -> None:
    cases = []
    for m in range(16, 101, 4):
        intervals, metadata = doubled_tail_family(m)
        exact = verify_intervals(m, intervals)
        assert exact["measure"] == metadata["density"]
        k = m // 4
        interval_count = 3 * (k - 1)
        assert exact["interval_count"] == interval_count
        assert exact["triple_count"] == interval_count**2 * (interval_count + 1) // 2
        assert exact["zero_endpoint_slacks"] == k * (k + 1)
        assert F(exact["minimum_positive_endpoint_slack"]) == F(1, 2 * m)
        metadata["exact_replay"] = exact
        cases.append(metadata)

    saturation = exact_saturation_comparisons()
    numeric_saturation = numeric_saturation_artifacts()
    assert len(cases) == 22
    report = {
        "summary": {
            "cases_verified": len(cases),
            "lifted_images_verified": sum(
                case["exact_replay"]["triple_count"] for case in cases
            ),
            "exact_saturation_constructions_compared": len(saturation),
            "numeric_saturation_artifacts_compared": len(numeric_saturation),
        },
        "formula": {
            "congruence": "m = 0 (mod 4), 16 <= m <= 100",
            "q": "m/4+1",
            "delta": "1/(2(m+2))",
            "base_start_sequence": "s_j=b-(m-4j)/(4m^2)",
            "tail_indices": "2 <= j <= (m-4)/4",
            "extra_starts": "s_j and s_j+1/m for every tail index j",
            "extra_count": "(m-8)/2",
            "total_interval_count": "3(m-4)/4",
            "extra_length": "2/(m^2(m+2))",
            "gain": "(m-8)/(m^2(m+2))",
            "density": "(m^3+4m^2+8m-64)/(8m^2(m+2))",
            "optimality_claim": "none; exact construction only in the tested finite range",
        },
        "exception": {
            "m": 12,
            "reason": (
                "the doubled tail has only two full-g extras, whereas the saved K=3 "
                "construction has two full-g extras plus a third of length 5/12096"
            ),
        },
        "cases": cases,
        "exact_saturation_comparisons": saturation,
        "numeric_saturation_artifacts": numeric_saturation,
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
