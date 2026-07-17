#!/usr/bin/env python3
"""Solve a two-extra case with a private strict HiGHS MIP tolerance."""

import argparse
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from equally_spaced_tiny_interval_lp import (
    build_variable_extra_interval_milp,
    save_json_outputs,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--m", type=int, required=True)
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    options = {
        "mip_rel_gap": 0.0,
        "mip_abs_gap": 0.0,
        "presolve": False,
        "mip_feasibility_tolerance": 1e-10,
    }
    problem = build_variable_extra_interval_milp(
        m=args.m,
        tie_choice="larger",
        anchor=0,
        extra_count=2,
    )
    problem.metadata["solver_options"] = dict(options)
    problem.metadata["tolerance"] = 1e-9
    solution = problem.solve(options=options)
    print(solution)
    if not solution.success or solution.status_name != "optimal":
        raise SystemExit(f"strict solve failed: {solution.status_name}: {solution.message}")
    if solution.solver_details.get("mip_gap") != 0:
        raise SystemExit(f"strict solve did not close the gap: {solution.solver_details}")

    problem_path, solution_path = save_json_outputs(
        problem,
        solution,
        output_dir=args.output_dir,
        run_name=args.run_name,
    )
    print(f"Saved problem JSON: {problem_path}")
    print(f"Saved solution JSON: {solution_path}")


if __name__ == "__main__":
    main()
