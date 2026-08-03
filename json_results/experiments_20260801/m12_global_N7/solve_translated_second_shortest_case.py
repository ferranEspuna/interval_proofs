#!/usr/bin/env python3
"""Solve one exhaustive length-order case of the unrestricted m=12,N=7 MILP.

The translated formulation places a globally shortest interval at index 0.
The six values of ``--second-index`` partition the remaining possibilities for
a second-shortest interval (ties may occur in more than one case).  Solving all
six cases therefore gives the unrestricted optimum; one case alone is only a
conditional result.
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
    parser.add_argument("--second-index", type=int, choices=range(1, N), required=True)
    parser.add_argument("--time-limit", type=float, default=180.0)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--disp", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()

    problem = build_circle_interval_problem(
        N=N,
        m=M,
        use_translated_missing_point=True,
        add_width_cuts=False,
        add_endpoint_length_cut=False,
        add_first_interval_shortest_cut=True,
        add_second_interval_at_most_last_cut=True,
        subset_alpha_bounds=SUBSET_BOUNDS,
        total_length_lower_bound=KNOWN_CONSTRUCTION,
    )
    for index in range(1, N):
        if index == args.second_index:
            continue
        problem.add_inequality(
            name=f"second_shortest_{args.second_index}_at_most_{index}",
            coefficients={f"alpha_{args.second_index}": 1, f"alpha_{index}": -1},
            sense="<=",
            rhs=0,
        )

    options = {
        "time_limit": args.time_limit,
        "mip_rel_gap": 0.0,
        "mip_abs_gap": 0.0,
        "disp": args.disp,
    }
    problem.metadata["solver_options"] = dict(options)
    problem.metadata["output_dir"] = artifact_path(args.output_dir)
    problem.metadata["second_shortest_interval_index"] = args.second_index

    integer_count = sum(variable.kind == "integer" for variable in problem.variables)
    print(
        f"{problem.name}: {len(problem.variables)} variables "
        f"({integer_count} integer), {len(problem.constraints)} constraints"
    )
    solution = problem.solve(options=options)
    print(solution)

    if has_visualizer_values(solution, N):
        state = solution_visualizer_state(
            solution,
            N=N,
            m=M,
            translated_missing_point=True,
        )
        solution.parameters["visualizer_state"] = state
        solution.parameters["visualizer_url"] = visualizer_state_url(state)

    stem = f"m12_N7_translated_secondshortest{args.second_index}_{int(args.time_limit)}s"
    args.output_dir.mkdir(parents=True, exist_ok=True)
    problem_path = args.output_dir / f"{stem}_problem.json"
    solution_path = args.output_dir / f"{stem}_solution.json"
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
