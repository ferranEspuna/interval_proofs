#!/usr/bin/env python3
"""Compare the complete two-extra scan with the saved one-extra scan."""

from __future__ import annotations

import csv
from fractions import Fraction as F
import json
from pathlib import Path


ARTIFACT_DIR = Path(__file__).resolve().parent
ONE_EXTRA_DIR = ARTIFACT_DIR.parent / "tiny_intervals"
JSON_PATH = ARTIFACT_DIR / "result_summary.json"
CSV_PATH = ARTIFACT_DIR / "result_summary.csv"
REPORTING_TOLERANCE = 1e-9


def branch_name(m: int, q: int) -> str:
    if m % 4 == 0 and q == m // 4:
        return "smaller"
    return "larger"


def expected_two_extra_gain(m: int, branch: str) -> F:
    if branch == "smaller":
        return F(0)
    if m == 4:
        return F(1, 192)
    if m == 8:
        return F(1, 320)
    if m == 9:
        return F(1, 891)
    if m >= 12 and m % 4 == 0:
        return F(4, m * m * (m + 2))
    if m >= 13 and m % 4 == 1:
        return F(2, m * m * (m + 2))
    return F(0)


def main() -> None:
    rows = []
    for path in ARTIFACT_DIR.glob("*_solution.json"):
        solution = json.loads(path.read_text(encoding="utf-8"))
        parameters = solution["parameters"]
        m = int(parameters["m"])
        q = int(parameters["q"])
        branch = branch_name(m, q)
        one_paths = list(
            ONE_EXTRA_DIR.glob(
                f"variable_extra_milp_m{m}_q{q}_anchor0_freebase0_extra1_solution.json"
            )
        )
        assert len(one_paths) == 1, (m, q, one_paths)
        one_solution = json.loads(one_paths[0].read_text(encoding="utf-8"))

        base = float(parameters["base_density"])
        one_gain = float(one_solution["optimum"]) - base
        two_gain = float(solution["optimum"]) - base
        extras = [float(solution["values"][f"alpha_{q + index}"]) for index in range(2)]
        expected = float(expected_two_extra_gain(m, branch))
        rows.append(
            {
                "m": m,
                "q": q,
                "branch": branch,
                "base_density": base,
                "one_extra_gain": one_gain,
                "two_extra_gain": two_gain,
                "expected_two_extra_gain": expected,
                "formula_error": two_gain - expected,
                "excess_over_twice_one_gain": two_gain - 2 * one_gain,
                "positive_extra_count": sum(value > REPORTING_TOLERANCE for value in extras),
                "extra_0_length": extras[0],
                "extra_1_length": extras[1],
                "extra_length_bound": parameters["extra_length_bound"],
                "success": solution["success"],
                "status_name": solution["status_name"],
                "mip_gap": solution["solver_details"]["mip_gap"],
                "mip_node_count": solution["solver_details"]["mip_node_count"],
                "solution": path.name,
            }
        )

    rows.sort(key=lambda row: (row["m"], row["q"]))
    assert len(rows) == 123, len(rows)
    assert all(row["success"] for row in rows)
    assert all(row["status_name"] == "optimal" for row in rows)
    assert all(row["mip_gap"] == 0 for row in rows)

    positive_larger = [
        row["m"]
        for row in rows
        if row["branch"] == "larger" and row["two_extra_gain"] > REPORTING_TOLERANCE
    ]
    positive_smaller = [
        row["m"]
        for row in rows
        if row["branch"] == "smaller" and row["two_extra_gain"] > REPORTING_TOLERANCE
    ]
    report = {
        "solution_count": len(rows),
        "unbounded_run_count": sum(row["extra_length_bound"] is None for row in rows),
        "inductively_bounded_run_count": sum(
            row["extra_length_bound"] is not None for row in rows
        ),
        "all_success_optimal_zero_gap": True,
        "reporting_tolerance": REPORTING_TOLERANCE,
        "positive_larger_m": positive_larger,
        "positive_smaller_m": positive_smaller,
        "max_absolute_formula_error": max(abs(row["formula_error"]) for row in rows),
        "max_excess_over_twice_one_gain": max(
            row["excess_over_twice_one_gain"] for row in rows
        ),
        "rows": rows,
    }
    JSON_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    with CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(
        json.dumps(
            {key: value for key, value in report.items() if key != "rows"},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
