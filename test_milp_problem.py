"""Basic executable test/demo for milp_problem.py.

Run with:

    python3 test_milp_problem.py
"""

from __future__ import annotations

import math

from milp_problem import MILPProblem, MILPSolution


def build_demo_problem() -> MILPProblem:
    problem = MILPProblem("small_named_milp")

    problem.add_integer_variable("x", lower_bound=0)
    problem.add_integer_variable("y", lower_bound=0)
    problem.add_continuous_variable("profit")

    problem.add_inequality("capacity_a", {"x": 2, "y": 1}, "<=", 7)
    problem.add_inequality("capacity_b", {"x": 1, "y": 2}, "<=", 7)
    problem.add_equality("profit_definition", {"profit": 1, "x": -3, "y": -2}, 0)
    problem.set_objective_variable("profit", sense="maximize")

    return problem


def main() -> None:
    problem = build_demo_problem()
    print(problem)
    print()

    restored_problem = MILPProblem.from_json(problem.to_json())
    assert restored_problem.to_dict() == problem.to_dict()

    try:
        solution = restored_problem.solve()
    except RuntimeError as exc:
        raise SystemExit(
            "The solver test requires SciPy. Install dependencies with:\n"
            "    python3 -m pip install -r requirements.txt\n\n"
            f"{exc}"
        ) from exc

    print(solution)
    print()

    assert solution.success, solution.message
    assert math.isclose(solution.optimum or math.nan, 11.0)
    assert solution["x"] == 3
    assert solution["y"] == 1
    assert math.isclose(float(solution["profit"]), 11.0)

    restored_solution = MILPSolution.from_json(solution.to_json())
    assert restored_solution.to_dict() == solution.to_dict()

    print("All MILP tests passed.")


if __name__ == "__main__":
    main()

