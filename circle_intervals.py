import argparse
from collections import defaultdict
from itertools import combinations
import math
from pathlib import Path

from milp_problem import MILPProblem


def integer_lift_bounds(d: float, epsilon: float = 0.0) -> tuple[int, int]:
    """Return safe bounds for the integer lift variable n_ijk.

    Since all intervals are represented inside [0, 1],
        -d <= right endpoint <= 2 and -d <= left endpoint <= 2.
    The lift n must satisfy n + epsilon <= left and
    right <= n + 1 - epsilon.
    """
    tolerance = 1e-12
    lower_bound = math.ceil(-d - 1 + epsilon - tolerance)
    upper_bound = math.floor(2 - epsilon + tolerance)
    return lower_bound, upper_bound


def build_circle_interval_problem(
    N: int,
    d: float,
    epsilon: float = 0.0,
    *,
    add_width_cuts: bool = True,
    add_monotonicity_cuts: bool = True,
    add_endpoint_length_cut: bool = True,
    subset_alpha_bounds: list[tuple[int, float]] | None = None,
) -> MILPProblem:
    problem = MILPProblem(f"{d}-sum-free set problem for {N} intervals")
    if N < 1:
        raise ValueError("N must be at least 1")
    if d <= 0:
        raise ValueError("d must be positive")
    if epsilon < 0:
        raise ValueError("epsilon must be nonnegative")

    subset_alpha_bounds = list(subset_alpha_bounds or [])
    for subset_size, bound in subset_alpha_bounds:
        if not 1 <= subset_size <= N:
            raise ValueError("subset alpha bound size must be between 1 and N")
        if not math.isfinite(bound) or bound < 0:
            raise ValueError("subset alpha bound must be a finite nonnegative number")

    n_lower_bound, n_upper_bound = integer_lift_bounds(d, epsilon)
    alpha_upper_bound = max(0.0, (1 - 2 * epsilon) / (d + 2))
    problem.metadata = {
        "N": N,
        "d": d,
        "epsilon": epsilon,
        "add_width_cuts": add_width_cuts,
        "add_monotonicity_cuts": add_monotonicity_cuts,
        "add_endpoint_length_cut": add_endpoint_length_cut,
        "subset_alpha_bounds": [
            {"subset_size": subset_size, "bound": bound}
            for subset_size, bound in subset_alpha_bounds
        ],
        "integer_lift_lower_bound": n_lower_bound,
        "integer_lift_upper_bound": n_upper_bound,
        "alpha_upper_bound": alpha_upper_bound,
    }

    for i in range(N):
        problem.add_continuous_variable(f"x_{i}", lower_bound=0, upper_bound=1)
        problem.add_continuous_variable(
            f"alpha_{i}",
            lower_bound=0,
            upper_bound=alpha_upper_bound,
        )

        # Keep each interval in the chosen [0, 1] representative.
        problem.add_inequality(
            name=f"inside_unit_{i}",
            coefficients={f"x_{i}": 1, f"alpha_{i}": 1},
            sense="<=",
            rhs=1,
        )

        # Ordering and non-overlapping.
        if i > 0:
            problem.add_inequality(
                name=f"order_{i}",
                coefficients={f"x_{i-1}": 1, f"alpha_{i-1}": 1, f"x_{i}": -1},
                sense="<=",
                rhs=0,
            )

    if add_endpoint_length_cut and N > 1:
        # Reflection lets us choose the orientation in which the last interval
        # is no longer than the first one.
        problem.add_inequality(
            name="last_interval_at_most_first",
            coefficients={f"alpha_{N - 1}": 1, "alpha_0": -1},
            sense="<=",
            rhs=0,
        )

    for bound_index, (subset_size, bound) in enumerate(subset_alpha_bounds):
        for subset in combinations(range(N), subset_size):
            subset_name = "_".join(str(index) for index in subset)
            problem.add_inequality(
                name=f"subset_alpha_bound_{bound_index}_{subset_size}_{subset_name}",
                coefficients={f"alpha_{index}": 1 for index in subset},
                sense="<=",
                rhs=bound,
            )

    # Sum-free condition: the interval I_i + I_j - d*I_k must not contain 0.
    # Unwrapping modulo 1, such an interval must be contained in
    # (n_ijk, n_ijk + 1), where n_ijk is an integer. With epsilon=0 this is
    # the closed relaxation n_ijk <= left and right <= n_ijk + 1.
    for i in range(N):
        for j in range(i, N):
            for k in range(N):
                if add_width_cuts:
                    width_coefs = defaultdict(float)
                    width_coefs[f"alpha_{i}"] += 1
                    width_coefs[f"alpha_{j}"] += 1
                    width_coefs[f"alpha_{k}"] += d
                    problem.add_inequality(
                        name=f"sum_free_width_{i}-{j}-{k}",
                        coefficients=width_coefs,
                        sense="<=",
                        rhs=1 - 2 * epsilon,
                    )

                # The leftmost point of I_i + I_j - d*I_k is
                # x_i + x_j - d*x_k - d*alpha_k >= n_ijk + epsilon.
                problem.add_integer_variable(
                    f"n_{i}-{j}-{k}",
                    lower_bound=n_lower_bound,
                    upper_bound=n_upper_bound,
                )

                if add_monotonicity_cuts:
                    # The lifted interval moves right as i or j increases.
                    if i > 0:
                        problem.add_inequality(
                            name=f"n_monotone_i_{i}-{j}-{k}",
                            coefficients={
                                f"n_{i - 1}-{j}-{k}": 1,
                                f"n_{i}-{j}-{k}": -1,
                            },
                            sense="<=",
                            rhs=0,
                        )
                    if j > i:
                        problem.add_inequality(
                            name=f"n_monotone_j_{i}-{j}-{k}",
                            coefficients={
                                f"n_{i}-{j - 1}-{k}": 1,
                                f"n_{i}-{j}-{k}": -1,
                            },
                            sense="<=",
                            rhs=0,
                        )

                    # The lifted interval moves left as k increases because
                    # the expression subtracts d*I_k.
                    if k > 0:
                        problem.add_inequality(
                            name=f"n_monotone_k_{i}-{j}-{k}",
                            coefficients={
                                f"n_{i}-{j}-{k}": 1,
                                f"n_{i}-{j}-{k - 1}": -1,
                            },
                            sense="<=",
                            rhs=0,
                        )

                coefs_left = defaultdict(float)
                coefs_left[f"x_{i}"] -= 1
                coefs_left[f"x_{j}"] -= 1
                coefs_left[f"x_{k}"] += d
                coefs_left[f"alpha_{k}"] += d
                coefs_left[f"n_{i}-{j}-{k}"] += 1

                problem.add_inequality(
                    name=f"sum_free_left_{i}-{j}-{k}",
                    coefficients=coefs_left,
                    sense="<=",
                    rhs=-epsilon,
                )

                # The rightmost point of I_i + I_j - d*I_k is
                # x_i + x_j + alpha_i + alpha_j - d*x_k <= n_ijk + 1 - epsilon.
                coefs_right = defaultdict(float)
                coefs_right[f"x_{i}"] += 1
                coefs_right[f"x_{j}"] += 1
                coefs_right[f"alpha_{i}"] += 1
                coefs_right[f"alpha_{j}"] += 1
                coefs_right[f"x_{k}"] -= d
                coefs_right[f"n_{i}-{j}-{k}"] -= 1

                problem.add_inequality(
                    name=f"sum_free_right_{i}-{j}-{k}",
                    coefficients=coefs_right,
                    sense="<=",
                    rhs=1 - epsilon,
                )

    # Objective: maximize the sum of the lengths of the intervals.
    problem.set_objective({f"alpha_{i}": 1 for i in range(N)}, sense="maximize")

    return problem


def filename_float(value: float) -> str:
    return f"{value:g}".replace("-", "neg").replace(".", "p")


def parse_subset_alpha_bound(value: str) -> tuple[int, float]:
    if ":" in value:
        size_text, bound_text = value.split(":", 1)
    elif "=" in value:
        size_text, bound_text = value.split("=", 1)
    else:
        raise argparse.ArgumentTypeError("expected N_PRIME:BOUND, for example 6:0.2")

    try:
        subset_size = int(size_text)
        bound = float(bound_text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected N_PRIME:BOUND with numeric values") from exc

    if subset_size < 1:
        raise argparse.ArgumentTypeError("N_PRIME must be at least 1")
    if not math.isfinite(bound) or bound < 0:
        raise argparse.ArgumentTypeError("BOUND must be a finite nonnegative number")

    return subset_size, bound


def default_file_stem(args: argparse.Namespace) -> str:
    subset_bound_part = "".join(
        f"_subset{subset_size}le{filename_float(bound)}"
        for subset_size, bound in args.subset_alpha_bounds
    )
    return (
        f"circle_intervals_N{args.N}_d{filename_float(args.d)}"
        f"_eps{filename_float(args.epsilon)}"
        f"_width{int(args.width_cuts)}"
        f"_monotone{int(args.monotonicity_cuts)}"
        f"_endpoint{int(args.endpoint_length_cut)}"
        f"{subset_bound_part}"
    )


def solver_options_from_args(args: argparse.Namespace) -> dict[str, object]:
    options: dict[str, object] = {}
    if args.time_limit is not None:
        options["time_limit"] = args.time_limit
    if args.node_limit is not None:
        options["node_limit"] = args.node_limit
    if args.mip_rel_gap is not None:
        options["mip_rel_gap"] = args.mip_rel_gap
    if args.presolve is not None:
        options["presolve"] = args.presolve
    if args.disp:
        options["disp"] = True
    if args.threads is not None:
        options["threads"] = args.threads
    return options


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build and solve a circle interval MILP.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-N", type=int, default=2, help="number of intervals")
    parser.add_argument("--d", type=float, default=3.0, help="sum-free multiplier")
    parser.add_argument(
        "--epsilon",
        type=float,
        default=0.0,
        help="positive margin for strict sum-free inequalities",
    )
    parser.add_argument(
        "--width-cuts",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="add redundant interval-width cuts",
    )
    parser.add_argument(
        "--monotonicity-cuts",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="add monotonicity cuts between integer lift variables",
    )
    parser.add_argument(
        "--endpoint-length-cut",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="add the symmetry cut alpha_{N-1} <= alpha_0",
    )
    parser.add_argument(
        "--subset-alpha-bound",
        dest="subset_alpha_bounds",
        action="append",
        type=parse_subset_alpha_bound,
        default=[],
        metavar="N_PRIME:BOUND",
        help=(
            "add constraints that every N_PRIME-subset of alphas has sum "
            "at most BOUND; can be repeated"
        ),
    )
    parser.add_argument(
        "--time-limit",
        type=float,
        default=None,
        help="HiGHS time limit in seconds",
    )
    parser.add_argument(
        "--node-limit",
        type=int,
        default=None,
        help="HiGHS branch-and-bound node limit",
    )
    parser.add_argument(
        "--mip-rel-gap",
        type=float,
        default=None,
        help="relative MIP gap termination tolerance",
    )
    parser.add_argument(
        "--presolve",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="enable or disable HiGHS presolve",
    )
    parser.add_argument(
        "--disp",
        action="store_true",
        help="show HiGHS solver log",
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=None,
        help="thread count passed through to HiGHS",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("json_results"),
        help="directory for saved problem and solution JSON files",
    )
    parser.add_argument(
        "--run-name",
        default=None,
        help="base filename for saved JSON files",
    )
    parser.add_argument(
        "--problem-json",
        type=Path,
        default=None,
        help="explicit path for the problem JSON",
    )
    parser.add_argument(
        "--solution-json",
        type=Path,
        default=None,
        help="explicit path for the solution JSON",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="do not save problem and solution JSON files",
    )
    parser.add_argument(
        "--print-problem",
        action="store_true",
        help="print the full MILP model before solving",
    )
    parser.add_argument(
        "--require-success",
        action="store_true",
        help="exit with an error if HiGHS does not prove optimality",
    )
    return parser


def save_json_outputs(
    problem: MILPProblem,
    solution,
    args: argparse.Namespace,
) -> tuple[Path, Path]:
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = args.run_name or default_file_stem(args)

    problem_path = args.problem_json or output_dir / f"{stem}_problem.json"
    solution_path = args.solution_json or output_dir / f"{stem}_solution.json"
    problem_path.parent.mkdir(parents=True, exist_ok=True)
    solution_path.parent.mkdir(parents=True, exist_ok=True)

    problem_path.write_text(problem.to_json(), encoding="utf-8")
    solution.parameters["problem_json_path"] = str(problem_path)
    solution.parameters["solution_json_path"] = str(solution_path)
    solution_path.write_text(solution.to_json(), encoding="utf-8")
    return problem_path, solution_path


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    problem = build_circle_interval_problem(
        N=args.N,
        d=args.d,
        epsilon=args.epsilon,
        add_width_cuts=args.width_cuts,
        add_monotonicity_cuts=args.monotonicity_cuts,
        add_endpoint_length_cut=args.endpoint_length_cut,
        subset_alpha_bounds=args.subset_alpha_bounds,
    )
    solver_options = solver_options_from_args(args)
    problem.metadata["solver_options"] = dict(solver_options)
    problem.metadata["output_dir"] = str(args.output_dir)

    integer_variables = sum(variable.kind == "integer" for variable in problem.variables)
    print(
        f"{problem.name}: {len(problem.variables)} variables "
        f"({integer_variables} integer), {len(problem.constraints)} constraints"
    )

    if args.print_problem:
        print()
        print(problem)

    solution = problem.solve(options=solver_options)

    print(solution)
    print()

    if not args.no_save:
        problem_path, solution_path = save_json_outputs(problem, solution, args)
        print(f"Saved problem JSON: {problem_path}")
        print(f"Saved solution JSON: {solution_path}")
        print()

    if args.require_success and not solution.success:
        raise SystemExit(solution.message)

if __name__ == "__main__":
    main()
