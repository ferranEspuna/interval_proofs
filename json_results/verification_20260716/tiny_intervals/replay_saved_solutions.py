#!/usr/bin/env python3
"""Replay every saved tiny-interval solution against its compressed model."""

from __future__ import annotations

import gzip
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ARTIFACT_DIR = Path(__file__).resolve().parent
REPORT_PATH = ARTIFACT_DIR / "replay_report.json"


def read_problem(path: Path) -> dict[str, object]:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            return json.load(handle)
    return json.loads(path.read_text(encoding="utf-8"))


def replay(solution_path: Path) -> dict[str, object]:
    solution = json.loads(solution_path.read_text(encoding="utf-8"))
    problem_path = ROOT / solution["parameters"]["problem_json_path"]
    problem = read_problem(problem_path)
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
    objective_error = abs(objective - float(solution["optimum"]))
    return {
        "solution": str(solution_path.relative_to(ROOT)),
        "problem": str(problem_path.relative_to(ROOT)),
        "max_bound_violation": max(0.0, max_bound),
        "max_integrality_violation": max_integrality,
        "max_row_violation": max_row,
        "worst_row": worst_row,
        "objective_error": objective_error,
    }


def main() -> None:
    results = [replay(path) for path in sorted(ARTIFACT_DIR.glob("*_solution.json"))]
    assert len(results) == 123, len(results)
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
        "all_problem_paths_exist": True,
        "maxima": maxima,
        "results": results,
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"solution_count": len(results), "maxima": maxima}, indent=2))
    print(f"saved {REPORT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
