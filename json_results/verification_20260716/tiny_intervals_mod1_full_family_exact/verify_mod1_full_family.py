#!/usr/bin/env python3
"""Exact finite verification of the full m=1 (mod 4) extra family."""

from __future__ import annotations

from fractions import Fraction as F
from math import floor
import json
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
CAMPAIGN = HERE.parent
ONE_DIR = CAMPAIGN / "tiny_intervals"
TWO_DIR = CAMPAIGN / "tiny_intervals_two_extra"
THREE_DIR = CAMPAIGN / "tiny_intervals_three_extra"
SATURATION_DIR = CAMPAIGN / "tiny_intervals_extra_count_saturation"
REPORT_PATH = HERE / "exact_verification_report.json"


# These rational reconstructions are separate constructions extracted from the
# emerging saturation runs.  They are not needed to verify the requested
# family, but make its comparison with the larger-K artifacts exact.
SATURATION_RECONSTRUCTIONS = [
    {
        "m": 13,
        "solver_extra_count": 4,
        "starts": [F(4427, 27885), F(4262, 27885)],
        "note": "two full-g extras; the other saved lengths are zero/numerical dust",
    },
    {
        "m": 17,
        "solver_extra_count": 4,
        "starts": [F(2268, 27455), F(3218, 27455), F(3883, 27455), F(1603, 27455)],
        "note": "four full-g extras",
    },
    {
        "m": 21,
        "solver_extra_count": 4,
        "starts": [F(335, 21413), F(3889, 192717), F(3452, 192717), F(2578, 192717)],
        "note": "the requested four-extra family",
    },
    {
        "m": 21,
        "solver_extra_count": 5,
        "starts": [F(12629, 192717), F(4064, 64239), F(3889, 192717),
                   F(3452, 192717), F(335, 21413)],
        "note": "five full-g extras",
    },
    {
        "m": 21,
        "solver_extra_count": 6,
        "starts": [F(335, 21413), F(3452, 192717), F(3889, 192717),
                   F(13066, 192717), F(12629, 192717), F(4064, 64239)],
        "note": "six full-g extras; exactly the doubled-tail family",
    },
]


def base_parameters(m: int) -> tuple[int, F, F, F]:
    assert m >= 9 and m % 4 == 1
    q = (m + 3) // 4
    delta = F(m + 1, 2 * m * (m + 2))
    a = (-F(m) * delta / F(m - 2)) % 1
    b = (a + F(1, m)) % 1
    return q, delta, a, b


def base_intervals(m: int) -> list[tuple[F, F, str]]:
    q, delta, a, _ = base_parameters(m)
    return [((a + F(r, m)) % 1, delta, f"base_{r}") for r in range(q)]


def requested_family(m: int) -> tuple[list[tuple[F, F, str]], dict[str, Any]]:
    q, delta, a, b = base_parameters(m)
    extra_count = (m - 5) // 4
    g = F(1, m * m * (m + 2))
    intervals = base_intervals(m)
    starts = []
    for j in range(1, extra_count + 1):
        start = b - F(m - (4 * j + 1), 4 * m * m)
        starts.append(start)
        intervals.append((start, g, f"extra_{j}"))

    base_density = q * delta
    gain = extra_count * g
    density = F((m - 1) * (m * m + 5 * m + 10), 8 * m * m * (m + 2))
    assert base_density + gain == density
    return intervals, {
        "m": m,
        "q": q,
        "a": str(a),
        "b": str(b),
        "delta": str(delta),
        "extra_count": extra_count,
        "extra_length": str(g),
        "extra_starts": [str(start) for start in starts],
        "base_density": str(base_density),
        "gain": str(gain),
        "density": str(density),
    }


def doubled_tail_family(m: int) -> tuple[list[tuple[F, F, str]], dict[str, Any]]:
    """Return the stronger two-translated-copy family for m >= 13."""
    assert m >= 13 and m % 4 == 1
    q, delta, a, b = base_parameters(m)
    requested_count = (m - 5) // 4
    g = F(1, m * m * (m + 2))
    tail = [
        b - F(m - (4 * j + 1), 4 * m * m)
        for j in range(2, requested_count + 1)
    ]
    starts = tail + [start + F(1, m) for start in tail]
    intervals = base_intervals(m) + [
        (start, g, f"extra_{index + 1}") for index, start in enumerate(starts)
    ]

    extra_count = F(m - 9, 2)
    assert extra_count.denominator == 1 and len(starts) == extra_count
    base_density = q * delta
    gain = int(extra_count) * g
    density = F(m**3 + 4 * m * m + 7 * m - 36, 8 * m * m * (m + 2))
    assert base_density + gain == density
    return intervals, {
        "m": m,
        "q": q,
        "a": str(a),
        "b": str(b),
        "delta": str(delta),
        "extra_count": int(extra_count),
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


def read_comparison(
    path: Path, *, m: int, extra_count: int, expected_gain_count: int
) -> dict[str, Any]:
    solution = json.loads(path.read_text())
    q, delta, _, _ = base_parameters(m)
    g = F(1, m * m * (m + 2))
    expected = q * delta + expected_gain_count * g
    lengths = [float(solution["values"][f"alpha_{q + i}"]) for i in range(extra_count)]
    return {
        "m": m,
        "extra_count": extra_count,
        "path": str(path.relative_to(REPO_ROOT)),
        "status": solution["status_name"],
        "mip_gap": solution["solver_details"]["mip_gap"],
        "solver_optimum": solution["optimum"],
        "expected_exact_density": str(expected),
        "objective_error": float(solution["optimum"]) - float(expected),
        "positive_extra_count_at_half_g": sum(length > float(g) / 2 for length in lengths),
    }


def saved_prefix_comparisons() -> list[dict[str, Any]]:
    comparisons = []
    for m in range(9, 98, 4):
        q = (m + 3) // 4
        full_count = (m - 5) // 4
        candidates = [
            (
                ONE_DIR
                / f"variable_extra_milp_m{m}_q{q}_anchor0_freebase0_extra1_solution.json",
                1,
            ),
            (
                TWO_DIR
                / f"variable_extra_milp_m{m}_q{q}_anchor0_freebase0_extra2_solution.json",
                2,
            ),
        ]
        g_denominator = m * m * (m + 2)
        candidates.append(
            (
                THREE_DIR
                / f"m{m}_q{q}_extra3_per_extra_bound_1over{g_denominator}_gap0_solution.json",
                3,
            )
        )
        for path, extra_count in candidates:
            if path.exists():
                comparisons.append(
                    read_comparison(
                        path,
                        m=m,
                        extra_count=extra_count,
                        expected_gain_count=min(extra_count, full_count),
                    )
                )
    return comparisons


def exact_saturation_comparisons() -> list[dict[str, Any]]:
    results = []
    for reconstruction in SATURATION_RECONSTRUCTIONS:
        m = reconstruction["m"]
        solver_extra_count = reconstruction["solver_extra_count"]
        starts = reconstruction["starts"]
        q, delta, _, _ = base_parameters(m)
        g = F(1, m * m * (m + 2))
        intervals = base_intervals(m) + [
            (start, g, f"extra_{index}") for index, start in enumerate(starts)
        ]
        exact = verify_intervals(m, intervals)
        family_density = F(
            (m - 1) * (m * m + 5 * m + 10), 8 * m * m * (m + 2)
        )

        matches = sorted(
            SATURATION_DIR.glob(
                f"m{m}_q{q}_extra{solver_extra_count}_*_solution.json"
            )
        )
        assert len(matches) == 1
        solver = json.loads(matches[0].read_text())
        exact_measure = F(exact["measure"])
        objective_error = float(solver["optimum"]) - float(exact_measure)
        assert abs(objective_error) < 1e-9
        results.append(
            {
                "m": m,
                "solver_extra_count": solver_extra_count,
                "reconstructed_positive_extra_count": len(starts),
                "note": reconstruction["note"],
                "solver_path": str(matches[0].relative_to(REPO_ROOT)),
                "solver_status": solver["status_name"],
                "solver_mip_gap": solver["solver_details"]["mip_gap"],
                "solver_objective_error": objective_error,
                "exact_measure": str(exact_measure),
                "requested_family_measure": str(family_density),
                "excess_over_requested_family": str(exact_measure - family_density),
                "extra_starts": [str(start) for start in starts],
                "exact_replay": exact,
            }
        )
    return results


def numeric_saturation_artifacts() -> list[dict[str, Any]]:
    results = []
    for m in (13, 17, 21):
        q, delta, _, _ = base_parameters(m)
        g = F(1, m * m * (m + 2))
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
    for m in range(9, 98, 4):
        intervals, metadata = requested_family(m)
        exact = verify_intervals(m, intervals)
        assert exact["measure"] == metadata["density"]

        k = (m - 1) // 4
        assert exact["interval_count"] == (m - 1) // 2
        assert exact["triple_count"] == 2 * k * k * (2 * k + 1)
        assert exact["zero_endpoint_slacks"] == (k * k + 5 * k + 2) // 2
        assert F(exact["minimum_positive_endpoint_slack"]) == F(m + 1, 2 * m * m)
        metadata["exact_replay"] = exact
        cases.append(metadata)

    doubled_tail_cases = []
    for m in range(13, 98, 4):
        intervals, metadata = doubled_tail_family(m)
        exact = verify_intervals(m, intervals)
        assert exact["measure"] == metadata["density"]
        assert exact["interval_count"] == 3 * (m - 5) // 4
        k = (m - 1) // 4
        interval_count = 3 * (k - 1)
        assert exact["triple_count"] == interval_count**2 * (interval_count + 1) // 2
        assert exact["zero_endpoint_slacks"] == k * (k + 1)
        assert F(exact["minimum_positive_endpoint_slack"]) == F(m + 1, 2 * m * m)
        metadata["exact_replay"] = exact
        doubled_tail_cases.append(metadata)

    saved = saved_prefix_comparisons()
    saturation = exact_saturation_comparisons()
    numeric_saturation = numeric_saturation_artifacts()
    assert len(cases) == 23
    assert len(doubled_tail_cases) == 22
    assert len(saved) == 49
    assert all(item["status"] == "optimal" and item["mip_gap"] == 0 for item in saved)
    assert max(abs(item["objective_error"]) for item in saved) < 1e-9

    report = {
        "summary": {
            "family_cases_verified": len(cases),
            "family_lifted_images_verified": sum(
                case["exact_replay"]["triple_count"] for case in cases
            ),
            "doubled_tail_cases_verified": len(doubled_tail_cases),
            "doubled_tail_lifted_images_verified": sum(
                case["exact_replay"]["triple_count"]
                for case in doubled_tail_cases
            ),
            "saved_prefix_artifacts_compared": len(saved),
            "maximum_saved_prefix_objective_error": max(
                abs(item["objective_error"]) for item in saved
            ),
            "exact_saturation_constructions_compared": len(saturation),
            "numeric_saturation_artifacts_compared": len(numeric_saturation),
        },
        "formula": {
            "congruence": "m = 1 (mod 4), 9 <= m <= 97",
            "q": "(m+3)/4",
            "delta": "(m+1)/(2m(m+2))",
            "extra_count": "(m-5)/4",
            "extra_length": "1/(m^2(m+2))",
            "extra_start_j": "b-(m-(4j+1))/(4m^2), 1 <= j <= (m-5)/4",
            "gain": "(m-5)/(4m^2(m+2))",
            "density": "(m-1)(m^2+5m+10)/(8m^2(m+2))",
        },
        "doubled_tail_formula": {
            "congruence": "m = 1 (mod 4), 13 <= m <= 97",
            "tail_indices": "2 <= j <= (m-5)/4",
            "extra_starts": "s_j and s_j+1/m for every tail index j",
            "extra_count": "(m-9)/2",
            "total_interval_count": "3(m-5)/4",
            "extra_length": "1/(m^2(m+2))",
            "gain": "(m-9)/(2m^2(m+2))",
            "density": "(m^3+4m^2+7m-36)/(8m^2(m+2))",
            "optimality_claim": "none; exact construction only in the tested finite range",
        },
        "family_cases": cases,
        "doubled_tail_cases": doubled_tail_cases,
        "saved_prefix_comparisons": saved,
        "exact_saturation_comparisons": saturation,
        "numeric_saturation_artifacts": numeric_saturation,
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
