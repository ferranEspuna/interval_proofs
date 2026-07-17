#!/usr/bin/env python3
"""Replay the retained m=3 finite-union solutions against their MILPs."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
ARTIFACT_DIR = Path(__file__).resolve().parent
REPORT_PATH = ARTIFACT_DIR / "replay_report.json"
RETAINED_SOLUTIONS = [
    *(f"m3_N{N}_standard_gap0_solution.json" for N in range(1, 7)),
    "m3_N7_with_N6_bound_gap0_solution.json",
]


def replay(solution_name: str) -> dict[str, object]:
    solution_path = ARTIFACT_DIR / solution_name
    solution = json.loads(solution_path.read_text(encoding="utf-8"))
    problem_path = Path(solution["parameters"]["problem_json_path"])
    if not problem_path.is_absolute():
        problem_path = ROOT / problem_path
    problem = json.loads(problem_path.read_text(encoding="utf-8"))
    values = {name: float(value) for name, value in solution["values"].items()}

    max_bound = 0.0
    max_integrality = 0.0
    for variable in problem["variables"]:
        value = values[variable["name"]]
        lower = variable["lower_bound"]
        upper = variable["upper_bound"]
        if lower is not None:
            max_bound = max(max_bound, float(lower) - value)
        if upper is not None:
            max_bound = max(max_bound, value - float(upper))
        if variable["kind"] == "integer":
            max_integrality = max(max_integrality, abs(value - round(value)))

    max_row = 0.0
    worst_row = None
    for constraint in problem["constraints"]:
        lhs = sum(
            float(coefficient) * values[name]
            for name, coefficient in constraint["coefficients"].items()
        )
        rhs = float(constraint["rhs"])
        if constraint["sense"] == "==":
            violation = abs(lhs - rhs)
        elif constraint["sense"] == "<=":
            violation = max(0.0, lhs - rhs)
        else:
            violation = max(0.0, rhs - lhs)
        if violation > max_row:
            max_row = violation
            worst_row = constraint["name"]

    objective = sum(
        float(coefficient) * values[name]
        for name, coefficient in problem["objective"]["coefficients"].items()
    )
    return {
        "solution": str(solution_path.relative_to(ROOT)),
        "problem": str(problem_path.relative_to(ROOT)),
        "success": solution["success"],
        "status_name": solution["status_name"],
        "mip_gap": solution["solver_details"]["mip_gap"],
        "max_bound_violation": max(0.0, max_bound),
        "max_integrality_violation": max_integrality,
        "max_row_violation": max_row,
        "worst_row": worst_row,
        "objective_error": abs(objective - float(solution["optimum"])),
    }


def main() -> None:
    results = [replay(name) for name in RETAINED_SOLUTIONS]
    assert all(result["success"] for result in results)
    assert all(result["status_name"] == "optimal" for result in results)
    assert all(result["mip_gap"] == 0 for result in results)
    maxima = {
        key: max(float(result[key]) for result in results)
        for key in (
            "max_bound_violation",
            "max_integrality_violation",
            "max_row_violation",
            "objective_error",
        )
    }
    report = {
        "solution_count": len(results),
        "all_success_optimal_zero_gap": True,
        "all_problem_paths_exist": True,
        "maxima": maxima,
        "results": results,
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"solution_count": len(results), "maxima": maxima}, indent=2))


if __name__ == "__main__":
    main()
