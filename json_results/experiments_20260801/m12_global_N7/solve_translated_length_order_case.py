#!/usr/bin/env python3
"""Solve one length-order case of the all-endpoints-free m=12, N=7 MILP.

The translated formulation places a globally shortest interval at index 0.
``--length-order i,j`` additionally chooses indices ``i`` and ``j`` as a
second-shortest and then a third-shortest interval.  All 6*5 ordered pairs
cover the unrestricted length patterns (ties can occur in several cases).

This decomposition is intended to keep HiGHS branch-and-bound trees small
enough for machines on which the monolithic model exhausts memory.
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


def parse_length_order(value: str) -> tuple[int, ...]:
    try:
        indices = tuple(int(part.strip()) for part in value.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "length-order indices must be comma-separated integers"
        ) from exc
    if not indices or any(index not in range(1, N) for index in indices):
        raise argparse.ArgumentTypeError(
            f"length-order indices must be distinct values in 1,...,{N - 1}"
        )
    if len(indices) != len(set(indices)):
        raise argparse.ArgumentTypeError("length-order indices must be distinct")
    return indices


def add_length_order_prefix(problem, prefix: tuple[int, ...]) -> None:
    """Order the selected indices before every remaining positive index."""
    remaining = set(range(1, N))
    for rank, selected_index in enumerate(prefix, start=2):
        if selected_index not in remaining:
            raise ValueError(f"invalid repeated length-order index {selected_index}")
        for other_index in sorted(remaining - {selected_index}):
            problem.add_inequality(
                name=(
                    f"length_rank_{rank}_index_{selected_index}"
                    f"_at_most_{other_index}"
                ),
                coefficients={
                    f"alpha_{selected_index}": 1,
                    f"alpha_{other_index}": -1,
                },
                sense="<=",
                rhs=0,
            )
        remaining.remove(selected_index)


def default_run_name(
    prefix: tuple[int, ...],
    *,
    time_limit: float | None,
    node_limit: int | None,
) -> str:
    order_text = "-".join(str(index) for index in prefix)
    time_text = "unlimited" if time_limit is None else f"{int(time_limit)}s"
    node_text = "unlimited" if node_limit is None else str(node_limit)
    return f"m12_N7_translated_lengthorder_{order_text}_{time_text}_nodes{node_text}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Solve one memory-reducing m=12,N=7 length-order case."
    )
    parser.add_argument(
        "--length-order",
        type=parse_length_order,
        required=True,
        help="indices chosen successively as second-, third-, ... shortest",
    )
    parser.add_argument("--time-limit", type=float, default=7200.0)
    parser.add_argument("--node-limit", type=int, default=3_000_000)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
    )
    parser.add_argument("--run-name")
    parser.add_argument("--disp", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()

    if args.time_limit is not None and args.time_limit <= 0:
        parser.error("--time-limit must be positive")
    if args.node_limit is not None and args.node_limit <= 0:
        parser.error("--node-limit must be positive")
    if args.threads <= 0:
        parser.error("--threads must be positive")

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
    add_length_order_prefix(problem, args.length_order)

    options: dict[str, object] = {
        "mip_rel_gap": 0.0,
        "mip_abs_gap": 0.0,
        "disp": args.disp,
        "threads": args.threads,
    }
    if args.time_limit is not None:
        options["time_limit"] = args.time_limit
    if args.node_limit is not None:
        options["node_limit"] = args.node_limit

    problem.metadata["solver_options"] = dict(options)
    problem.metadata["output_dir"] = artifact_path(args.output_dir)
    problem.metadata["length_order_prefix"] = list(args.length_order)
    problem.metadata["length_order_partition_is_exhaustive_at_depth"] = len(
        args.length_order
    )

    integer_count = sum(variable.kind == "integer" for variable in problem.variables)
    print(
        f"{problem.name}: {len(problem.variables)} variables "
        f"({integer_count} integer), {len(problem.constraints)} constraints"
    )
    print(f"length-order prefix after shortest index 0: {args.length_order}")
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

    run_name = args.run_name or default_run_name(
        args.length_order,
        time_limit=args.time_limit,
        node_limit=args.node_limit,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    problem_path = args.output_dir / f"{run_name}_problem.json"
    solution_path = args.output_dir / f"{run_name}_solution.json"
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
