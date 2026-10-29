#!/usr/bin/env python3
"""Maximize circle interval density for an integer linear form.

Example: python linear_form_intervals.py -N 3 --coefficients 1 1 -3
The variables in L(a_1, ..., a_k) = sum c_r*a_r range independently over A.
At epsilon=0 this solves the closed endpoint relaxation, as circle_intervals.py
does; positive epsilon enforces a margin from the chosen missing point.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
from itertools import combinations_with_replacement, product
import json
import math
from numbers import Integral
from pathlib import Path
from typing import Iterable, Iterator

from circle_intervals import (
    DEFAULT_VISUALIZER_URL,
    add_interval_layout,
    has_visualizer_values,
    parse_subset_alpha_bound,
    save_json_outputs,
    solution_visualizer_state,
    solver_options_from_args,
    visualizer_number,
    visualizer_state_url,
)
from milp_problem import MILPProblem, MILPSolution


def normalize_coefficients(coefficients: Iterable[int]) -> tuple[int, ...]:
    coefficients = tuple(coefficients)
    if not coefficients:
        raise ValueError("provide at least one integer coefficient")
    if any(isinstance(c, bool) or not isinstance(c, Integral) for c in coefficients):
        raise ValueError("coefficients must be integers")
    return tuple(int(c) for c in coefficients)


def coefficient_groups(coefficients: tuple[int, ...]) -> list[list[int]]:
    groups: dict[int, list[int]] = {}
    for slot, coefficient in enumerate(coefficients):
        groups.setdefault(coefficient, []).append(slot)
    return list(groups.values())


def interval_tuples(N: int, coefficients: tuple[int, ...]) -> Iterator[tuple[int, ...]]:
    """Enumerate one assignment per permutation of equal-coefficient slots.

    Call with the nonzero coefficients. For the zero form, yield the empty
    tuple once. No recursion or fixed arity is used.
    """
    groups = coefficient_groups(coefficients)
    choices = [combinations_with_replacement(range(N), len(group)) for group in groups]
    for assignments in product(*choices):
        indices = [0] * len(coefficients)
        for group, assignment in zip(groups, assignments):
            for slot, index in zip(group, assignment):
                indices[slot] = index
        yield tuple(indices)


def integer_lift_bounds(
    coefficients: Iterable[int],
    epsilon: float = 0.0,
    *,
    translated_missing_point: bool = False,
) -> tuple[int, int]:
    coefficients = normalize_coefficients(coefficients)
    negative_sum = sum(c for c in coefficients if c < 0)
    positive_sum = sum(c for c in coefficients if c > 0)
    if not negative_sum and not positive_sum and not translated_missing_point:
        # For positive epsilon no lift works; leave a nonempty domain so the
        # containment constraints report infeasibility through the solver.
        return -1, 0
    # Every endpoint lies between negative_sum and positive_sum. Since
    # n+t+epsilon <= left <= right <= n+1+t-epsilon, these bounds are safe.
    shift = int(translated_missing_point)
    return (
        math.ceil(negative_sum - 1 - shift + epsilon - 1e-12),
        math.floor(positive_sum - epsilon + 1e-12),
    )


def build_linear_form_interval_problem(
    N: int,
    coefficients: Iterable[int],
    epsilon: float = 0.0,
    *,
    use_translated_missing_point: bool = False,
    add_width_cuts: bool = False,
    add_monotonicity_cuts: bool = True,
    add_endpoint_length_cut: bool = True,
    add_first_interval_shortest_cut: bool = False,
    add_second_interval_at_most_last_cut: bool = False,
    subset_alpha_bounds: list[tuple[int, float]] | None = None,
    total_length_lower_bound: float | None = None,
) -> MILPProblem:
    """Build the MILP for 0 outside L(A), or a variable missing point t.

    Zero-length intervals are allowed, so N means at most N intervals.
    A coefficient c means dilation of one independently chosen element of A,
    not a sum of |c| independent copies of A.
    """
    if isinstance(N, bool) or not isinstance(N, Integral) or N < 1:
        raise ValueError("N must be a positive integer")
    N = int(N)
    coefficients = normalize_coefficients(coefficients)
    active = tuple(c for c in coefficients if c)
    if not math.isfinite(epsilon) or not 0 <= epsilon <= 0.5:
        raise ValueError("epsilon must be finite and between 0 and 0.5")
    if add_first_interval_shortest_cut and not use_translated_missing_point:
        raise ValueError("the first-interval-shortest cut requires --translated-missing-point")
    if add_second_interval_at_most_last_cut and not use_translated_missing_point:
        raise ValueError("the second-interval-at-most-last cut requires --translated-missing-point")
    if add_first_interval_shortest_cut and add_endpoint_length_cut:
        raise ValueError("use --no-endpoint-length-cut with --first-interval-shortest")
    subset_alpha_bounds = list(subset_alpha_bounds or [])
    for size, bound in subset_alpha_bounds:
        if isinstance(size, bool) or not isinstance(size, Integral) or not 1 <= size <= N:
            raise ValueError("subset alpha bound size must be between 1 and N")
        if not math.isfinite(bound) or bound < 0:
            raise ValueError("subset alpha bound must be a finite nonnegative number")
    if total_length_lower_bound is not None:
        if not math.isfinite(total_length_lower_bound) or total_length_lower_bound < 0:
            raise ValueError("total length lower bound must be a finite nonnegative number")

    norm = sum(abs(c) for c in active)
    alpha_upper_bound = (1 - 2 * epsilon) / norm if norm else 1.0
    if not active and not use_translated_missing_point:
        # L(A)={0} for every nonempty A: even the limiting density is zero.
        # The bare epsilon=0 endpoint relaxation would incorrectly allow 1.
        alpha_upper_bound = 0.0
    lower, upper = integer_lift_bounds(
        coefficients, epsilon, translated_missing_point=use_translated_missing_point
    )
    tuple_count = math.prod(
        math.comb(N + len(group) - 1, len(group)) for group in coefficient_groups(active)
    )
    problem = MILPProblem(f"Linear form {list(coefficients)} for {N} intervals")
    problem.metadata = {
        "N": N,
        "coefficients": list(coefficients),
        "active_coefficients": list(active),
        "coefficient_sum": sum(coefficients),
        "epsilon": epsilon,
        "use_translated_missing_point": use_translated_missing_point,
        "add_width_cuts": add_width_cuts,
        "add_monotonicity_cuts": add_monotonicity_cuts,
        "add_endpoint_length_cut": add_endpoint_length_cut,
        "add_first_interval_shortest_cut": add_first_interval_shortest_cut,
        "add_second_interval_at_most_last_cut": add_second_interval_at_most_last_cut,
        "subset_alpha_bounds": [
            {"subset_size": size, "bound": bound} for size, bound in subset_alpha_bounds
        ],
        "total_length_lower_bound": total_length_lower_bound,
        "integer_lift_lower_bound": lower,
        "integer_lift_upper_bound": upper,
        "alpha_upper_bound": alpha_upper_bound,
        "lifted_tuple_count": tuple_count,
        "endpoint_relaxation": epsilon == 0,
    }
    add_interval_layout(
        problem, N,
        alpha_upper_bounds=[alpha_upper_bound] * N,
        use_translated_missing_point=use_translated_missing_point,
        add_endpoint_length_cut=add_endpoint_length_cut,
        add_first_interval_shortest_cut=add_first_interval_shortest_cut,
        add_second_interval_at_most_last_cut=add_second_interval_at_most_last_cut,
        subset_alpha_bounds=subset_alpha_bounds,
        total_length_lower_bound=total_length_lower_bound,
    )

    lifts = {
        indices: "n_" + ("-".join(map(str, indices)) or "empty")
        for indices in interval_tuples(N, active)
    }
    for name in lifts.values():
        problem.add_integer_variable(name, lower_bound=lower, upper_bound=upper)
    for indices, name in lifts.items():
        left: dict[str, float] = defaultdict(float, {name: 1})
        right: dict[str, float] = defaultdict(float, {name: -1})
        width: dict[str, float] = defaultdict(float)
        if use_translated_missing_point:
            left["t"] = 1
            right["t"] = -1
        for slot, (coefficient, index) in enumerate(zip(active, indices)):
            left[f"x_{index}"] -= coefficient
            right[f"x_{index}"] += coefficient
            if coefficient < 0:
                left[f"alpha_{index}"] -= coefficient
            else:
                right[f"alpha_{index}"] += coefficient
            width[f"alpha_{index}"] += abs(coefficient)
            if add_monotonicity_cuts and index > 0:
                previous = list(indices)
                previous[slot] -= 1
                previous_name = lifts.get(tuple(previous))
                if previous_name is not None:
                    sign = 1 if coefficient > 0 else -1
                    problem.add_less_equal(
                        f"n_monotone_{slot}_{name}",
                        {previous_name: sign, name: -sign}, 0,
                    )
        problem.add_less_equal(f"linear_form_left_{name}", left, -epsilon)
        problem.add_less_equal(f"linear_form_right_{name}", right, 1 - epsilon)
        if add_width_cuts and width:
            problem.add_less_equal(f"linear_form_width_{name}", width, 1 - 2 * epsilon)
    problem.set_objective({f"alpha_{i}": 1 for i in range(N)}, sense="maximize")
    return problem


def linear_form_visualizer_state(
    solution: MILPSolution,
    *,
    N: int,
    coefficients: Iterable[int],
    translated_missing_point: bool = False,
) -> dict[str, object]:
    """Export actual coordinates, retaining t for translation-invariant forms."""
    coefficients = normalize_coefficients(coefficients)
    # Reuse the existing interval/color/rounding export without its special
    # A+A-mA coordinate normalization. The general view can display t directly.
    state = solution_visualizer_state(solution, N=N, m=3)
    state.pop("m")
    for interval in state["intervals"]:
        # HiGHS may return a tiny negative width within feasibility tolerance.
        interval["width"] = min(1.0, max(0.0, interval["width"]))
    state.update({
        "mode": "linear-form",
        "coefficients": list(coefficients),
        "missingPoint": visualizer_number(float(solution["t"])) if translated_missing_point else 0.0,
        "epsilon": solution.parameters.get("epsilon", 0.0),
        "solverStatus": solution.status_name,
    })
    return state


def default_file_stem(args: argparse.Namespace) -> str:
    # A digest keeps names short for long forms and distinguishes every model
    # option. Full coefficients and parameters remain in both JSON artifacts.
    configuration = {
        key: value for key, value in vars(args).items()
        if key not in {"run_name", "problem_json", "solution_json", "output_dir",
                       "visualizer_url", "no_save", "print_problem", "require_success"}
    }
    digest = hashlib.sha256(json.dumps(configuration, sort_keys=True).encode()).hexdigest()[:12]
    coefficient_text = "_".join(str(c).replace("-", "neg") for c in args.coefficients)
    if len(coefficient_text) > 64:
        coefficient_text = coefficient_text[:64]
    return f"linear_form_N{args.N}_c{coefficient_text}_{digest}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Maximize interval density for L(a_1,...,a_k)=sum c_r*a_r on R/Z.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog="Example: python linear_form_intervals.py -N 3 --coefficients 1 1 -3 --mip-rel-gap 0",
    )
    parser.add_argument("-N", type=int, default=2, help="maximum number of intervals")
    parser.add_argument("--coefficients", "-c", nargs="+", type=int, required=True,
                        metavar="C", help="space-separated integer coefficients, e.g. 1 1 -3")
    parser.add_argument("--epsilon", type=float, default=0.0, help="endpoint margin; zero gives the closed relaxation")
    parser.add_argument("--translated-missing-point", action="store_true", help="find any missing point t instead of fixing it to zero")
    parser.add_argument("--width-cuts", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--monotonicity-cuts", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--endpoint-length-cut", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--first-interval-shortest", action="store_true", help="requires translated mode and --no-endpoint-length-cut")
    parser.add_argument("--second-interval-at-most-last", action="store_true", help="requires translated mode")
    parser.add_argument("--subset-alpha-bound", dest="subset_alpha_bounds", action="append",
                        type=parse_subset_alpha_bound, default=[], metavar="N_PRIME:BOUND")
    parser.add_argument("--total-length-lower-bound", type=float)
    parser.add_argument("--time-limit", type=float, help="HiGHS time limit in seconds")
    parser.add_argument("--node-limit", type=int)
    parser.add_argument("--mip-rel-gap", type=float)
    parser.add_argument("--mip-abs-gap", type=float)
    parser.add_argument("--presolve", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--disp", action="store_true", help="show solver log")
    parser.add_argument("--threads", type=int)
    parser.add_argument("--output-dir", type=Path, default=Path("json_results_tmp"))
    parser.add_argument("--run-name", help="base filename for saved JSON files")
    parser.add_argument("--problem-json", type=Path)
    parser.add_argument("--solution-json", type=Path)
    parser.add_argument("--no-save", action="store_true")
    parser.add_argument("--visualizer-url", default=DEFAULT_VISUALIZER_URL)
    parser.add_argument("--print-problem", action="store_true")
    parser.add_argument("--require-success", action="store_true", help="exit with an error unless optimality was reported")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        problem = build_linear_form_interval_problem(
            args.N, args.coefficients, args.epsilon,
            use_translated_missing_point=args.translated_missing_point,
            add_width_cuts=args.width_cuts,
            add_monotonicity_cuts=args.monotonicity_cuts,
            add_endpoint_length_cut=args.endpoint_length_cut,
            add_first_interval_shortest_cut=args.first_interval_shortest,
            add_second_interval_at_most_last_cut=args.second_interval_at_most_last,
            subset_alpha_bounds=args.subset_alpha_bounds,
            total_length_lower_bound=args.total_length_lower_bound,
        )
    except ValueError as exc:
        parser.error(str(exc))
    solver_options = solver_options_from_args(args)
    problem.metadata.update(solver_options=solver_options, output_dir=str(args.output_dir))
    print(f"{problem.name}: {len(problem.variables)} variables, "
          f"{problem.metadata['lifted_tuple_count']} integer lifts, {len(problem.constraints)} constraints", flush=True)
    if args.print_problem:
        print(problem)
    solution = problem.solve(options=solver_options)
    if has_visualizer_values(solution, args.N):
        state = linear_form_visualizer_state(
            solution, N=args.N, coefficients=args.coefficients,
            translated_missing_point=args.translated_missing_point,
        )
        solution.parameters["visualizer_state"] = state
        solution.parameters["visualizer_url"] = visualizer_state_url(state, base_url=args.visualizer_url)
    print(solution)
    if args.epsilon == 0:
        print("epsilon=0: density is for the closed endpoint relaxation (a limiting bound).")
    if not args.translated_missing_point and sum(args.coefficients) == 0:
        print("The coefficients sum to zero: every nonempty A has 0 in L(A), so no positive density avoids 0.")
    if not solution.success:
        print("Optimality was not established; any returned density is an incumbent, not a proved maximum.")
    if not args.no_save:
        args.run_name = args.run_name or default_file_stem(args)
        problem_path, solution_path = save_json_outputs(problem, solution, args)
        print(f"Saved problem JSON: {problem_path}")
        print(f"Saved solution JSON: {solution_path}")
    if "visualizer_url" in solution.parameters:
        print("Visualizer state JSON:")
        print(json.dumps(solution.parameters["visualizer_state"], indent=2))
        print("Visualizer state URL:")
        print(solution.parameters["visualizer_url"])
    else:
        print("No visualizer link: the solver returned no interval coordinates.")
    if args.require_success and not solution.success:
        raise SystemExit(solution.message)


if __name__ == "__main__":
    main()
