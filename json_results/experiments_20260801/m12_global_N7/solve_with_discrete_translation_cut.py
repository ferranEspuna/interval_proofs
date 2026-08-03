#!/usr/bin/env python3
"""Run the unrestricted m=12, N=7 MILP with certified smaller-N cuts.

The additional ``x_0 <= 1/(m-2)`` inequality is a symmetry cut.  Translation
by k/(m-2) preserves m-sum-freeness, since A+A-mA is translated by -k.  Given
an ordered representative with first start x_0, translating left by
floor((m-2)x_0)/(m-2) keeps every interval inside [0,1] and places the first
start in [0,1/(m-2)).
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from circle_intervals import (
    build_circle_interval_problem,
    has_visualizer_values,
    solution_visualizer_state,
    visualizer_state_url,
)


M = 12
N = 7
SUBSET_BOUNDS = [
    (2, 5 / 42),
    (3, 1 / 7),
    (4, 1 / 7),
    (5, 145 / 1008),
    (6, 73 / 504),
]
KNOWN_CONSTRUCTION = 251 / 1728


def artifact_path(path: Path) -> str:
    """Use portable repository-relative metadata for in-repository artifacts."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(resolved)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--time-limit", type=float, default=600.0)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument(
        "--run-name",
        default="m12_N7_standard_discrete_translation_cut_all_subset_bounds_cutoff_600s",
    )
    parser.add_argument("--disp", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()

    problem = build_circle_interval_problem(
        N=N,
        m=M,
        add_width_cuts=False,
        subset_alpha_bounds=SUBSET_BOUNDS,
        total_length_lower_bound=KNOWN_CONSTRUCTION,
    )
    problem.add_inequality(
        name="discrete_translation_first_start",
        coefficients={"x_0": 1},
        sense="<=",
        rhs=1 / (M - 2),
    )
    options = {
        "time_limit": args.time_limit,
        "mip_rel_gap": 0.0,
        "mip_abs_gap": 0.0,
        "disp": args.disp,
    }
    problem.metadata["solver_options"] = dict(options)
    problem.metadata["output_dir"] = artifact_path(args.output_dir)
    problem.metadata["discrete_translation_first_start_upper_bound"] = 1 / (M - 2)

    integer_count = sum(variable.kind == "integer" for variable in problem.variables)
    print(
        f"{problem.name}: {len(problem.variables)} variables "
        f"({integer_count} integer), {len(problem.constraints)} constraints"
    )
    solution = problem.solve(options=options)
    print(solution)

    if has_visualizer_values(solution, N):
        state = solution_visualizer_state(solution, N=N, m=M)
        solution.parameters["visualizer_state"] = state
        solution.parameters["visualizer_url"] = visualizer_state_url(state)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    problem_path = args.output_dir / f"{args.run_name}_problem.json"
    solution_path = args.output_dir / f"{args.run_name}_solution.json"
    problem_path.write_text(problem.to_json(), encoding="utf-8")
    solution.parameters["problem_json_path"] = artifact_path(problem_path)
    solution.parameters["solution_json_path"] = artifact_path(solution_path)
    solution_path.write_text(solution.to_json(), encoding="utf-8")
    print(f"Saved problem JSON: {problem_path}")
    print(f"Saved solution JSON: {solution_path}")
    if "visualizer_url" in solution.parameters:
        print(f"Visualizer state URL: {solution.parameters['visualizer_url']}")


if __name__ == "__main__":
    main()
