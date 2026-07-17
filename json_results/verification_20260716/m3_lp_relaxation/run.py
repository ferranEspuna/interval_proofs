#!/usr/bin/env python3
"""Solve and archive the naive LP relaxation of the m=3 interval model."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from circle_intervals import build_circle_interval_problem
from milp_problem import CONTINUOUS, INTEGER


OUTPUT_DIR = Path(__file__).resolve().parent


def replay(problem, solution) -> dict[str, float | str | None]:
    values = {name: float(value) for name, value in solution.values.items()}
    max_bound = 0.0
    for variable in problem.variables:
        value = values[variable.name]
        if variable.lower_bound is not None:
            max_bound = max(max_bound, variable.lower_bound - value)
        if variable.upper_bound is not None:
            max_bound = max(max_bound, value - variable.upper_bound)

    max_row = 0.0
    worst_row = None
    for constraint in problem.constraints:
        lhs = sum(
            coefficient * values[name]
            for name, coefficient in constraint.coefficients.items()
        )
        if constraint.sense == "==":
            violation = abs(lhs - constraint.rhs)
        elif constraint.sense == "<=":
            violation = max(0.0, lhs - constraint.rhs)
        else:
            violation = max(0.0, constraint.rhs - lhs)
        if violation > max_row:
            max_row = violation
            worst_row = constraint.name

    return {
        "max_bound_violation": max(0.0, max_bound),
        "max_row_violation": max_row,
        "worst_row": worst_row,
    }


def main() -> None:
    rows = []
    for add_width_cuts in (False, True):
        for interval_count in range(1, 9):
            problem = build_circle_interval_problem(
                N=interval_count,
                m=3,
                add_width_cuts=add_width_cuts,
                add_monotonicity_cuts=True,
                add_endpoint_length_cut=True,
            )
            relaxed_count = 0
            for variable in problem.variables:
                if variable.kind == INTEGER:
                    variable.kind = CONTINUOUS
                    relaxed_count += 1
            problem.metadata.update(
                {
                    "experiment": "naive_lp_relaxation",
                    "relaxed_integer_variable_count": relaxed_count,
                    "solver_options": {},
                }
            )

            solution = problem.solve()
            stem = (
                f"m3_N{interval_count}_lp_relaxation_"
                f"width{int(add_width_cuts)}"
            )
            problem_path = OUTPUT_DIR / f"{stem}_problem.json"
            solution_path = OUTPUT_DIR / f"{stem}_solution.json"
            solution.parameters.update(
                {
                    "problem_json_path": str(problem_path.relative_to(ROOT)),
                    "solution_json_path": str(solution_path.relative_to(ROOT)),
                    "independent_replay": replay(problem, solution),
                }
            )
            problem_path.write_text(problem.to_json(), encoding="utf-8")
            solution_path.write_text(solution.to_json(), encoding="utf-8")
            rows.append(
                {
                    "N": interval_count,
                    "add_width_cuts": add_width_cuts,
                    "success": solution.success,
                    "status_name": solution.status_name,
                    "optimum": solution.optimum,
                    "expected_optimum": min(interval_count / 5, 1),
                    "problem": str(problem_path.relative_to(ROOT)),
                    "solution": str(solution_path.relative_to(ROOT)),
                    "independent_replay": solution.parameters[
                        "independent_replay"
                    ],
                }
            )

    assert all(row["success"] for row in rows)
    assert all(row["status_name"] == "optimal" for row in rows)
    assert all(
        abs(float(row["optimum"]) - float(row["expected_optimum"])) <= 1e-12
        for row in rows
    )
    result = {
        "run_count": len(rows),
        "all_success_optimal": True,
        "max_objective_error": max(
            abs(float(row["optimum"]) - float(row["expected_optimum"]))
            for row in rows
        ),
        "max_row_violation": max(
            float(row["independent_replay"]["max_row_violation"])
            for row in rows
        ),
        "rows": rows,
    }
    (OUTPUT_DIR / "result_summary.json").write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "run_count": result["run_count"],
                "max_objective_error": result["max_objective_error"],
                "max_row_violation": result["max_row_violation"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
