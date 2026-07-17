"""Direct standard-formulation experiments around the equally spaced construction.

The equally spaced construction fixes

    q, delta, a
    I_r = (a + r/m, a + r/m + delta), 0 <= r < q,

with q chosen to maximize q * delta and delta = (m - 2q + 2)/(m(m + 2)).
This script fixes that base construction, adds a requested number of genuinely
variable extra intervals (x_i, alpha_i), and optimizes directly with the same
standard lifted constraints as circle_intervals.py.

This is the standard formulation only: the missing point is 0, not a translated
variable t.

Because the extra starts are not seeded, the lift certificates n_{i,j,ell} are
integer variables.  So this direct "just optimize" model is a MILP.

Example:

    python3 equally_spaced_tiny_interval_lp.py --m 4 --anchor -1 --extra-count 1
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
from fractions import Fraction
import math
from pathlib import Path

from milp_problem import MILPProblem, MILPSolution


TOLERANCE = 1e-10


@dataclass(frozen=True)
class IntervalSeed:
    start: float
    length: float
    fixed: bool
    label: str

    @property
    def end(self) -> float:
        return self.start + self.length


def parse_fraction_float(text: str) -> float:
    try:
        return float(Fraction(text))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"expected a decimal or fraction, got {text!r}"
        ) from exc


def nonnegative_int(text: str) -> int:
    try:
        value = int(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected a nonnegative integer") from exc
    if value < 0:
        raise argparse.ArgumentTypeError("expected a nonnegative integer")
    return value


def nonnegative_float(text: str) -> float:
    try:
        value = float(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected a nonnegative number") from exc
    if not math.isfinite(value) or value < 0:
        raise argparse.ArgumentTypeError("expected a finite nonnegative number")
    return value


def filename_float(value: float) -> str:
    return f"{value:g}".replace("-", "neg").replace(".", "p")


def normalize_mod_one(value: float) -> float:
    normalized = value % 1.0
    if math.isclose(normalized, 1.0, abs_tol=TOLERANCE):
        return 0.0
    return normalized


def optimized_q(m: int, *, tie_choice: str = "larger") -> int:
    if m < 3:
        raise ValueError("m must be at least 3")
    if tie_choice not in {"larger", "smaller"}:
        raise ValueError("tie_choice must be 'larger' or 'smaller'")

    allowed = [q for q in range(1, m + 1) if 2 * q < m + 2]
    if not allowed:
        raise ValueError("no admissible q values")

    def score(q: int) -> int:
        return q * (m - 2 * q + 2)

    best_score = max(score(q) for q in allowed)
    best_qs = [q for q in allowed if score(q) == best_score]
    return max(best_qs) if tie_choice == "larger" else min(best_qs)


def equally_spaced_delta(m: int, q: int) -> float:
    if 2 * q >= m + 2:
        raise ValueError("q must satisfy q < (m + 2)/2")
    return (m - 2 * q + 2) / (m * (m + 2))


def integer_lift_bounds(m: int, epsilon: float) -> tuple[int, int]:
    """Return safe standard-formulation bounds for n_{i,j,ell}."""
    lower_bound = math.ceil(-m - 1 + epsilon - TOLERANCE)
    upper_bound = math.floor(2 - epsilon + TOLERANCE)
    return lower_bound, upper_bound


def anchor_values(m: int, delta: float) -> list[tuple[int, float]]:
    """Return one representative a for each integer anchor class.

    The construction needs (2 - m) * a - m * delta to be an integer.  Changing
    that integer by m - 2 changes a by 1, so these are the distinct choices in
    T.
    """
    return [
        (anchor, normalize_mod_one((anchor + m * delta) / (2 - m)))
        for anchor in range(-(m - 3), 1)
    ]


def base_intervals(
    *,
    m: int,
    q: int,
    delta: float,
    anchor: int | None,
) -> tuple[int, list[IntervalSeed]]:
    anchors = anchor_values(m, delta)
    if anchor is None:
        selected_anchor, a = 0, normalize_mod_one(m * delta / (2 - m))
    else:
        period = m - 2
        matches = [
            (candidate_anchor, candidate_a)
            for candidate_anchor, candidate_a in anchors
            if (candidate_anchor - anchor) % period == 0
        ]
        if not matches:
            raise ValueError(f"invalid anchor {anchor}; expected an integer class")
        selected_anchor, a = matches[0]

    intervals = [
        IntervalSeed(
            start=normalize_mod_one(a + r / m),
            length=delta,
            fixed=True,
            label=f"base_{r}",
        )
        for r in range(q)
    ]
    intervals.sort(key=lambda interval: interval.start)

    for interval in intervals:
        if interval.end > 1 + TOLERANCE:
            raise ValueError(
                "chosen anchor makes a base interval wrap around 1; choose "
                "another anchor"
            )

    return selected_anchor, intervals


def build_variable_extra_interval_milp(
    *,
    m: int,
    q: int | None = None,
    tie_choice: str = "larger",
    anchor: int | None = None,
    extra_count: int = 0,
    epsilon: float = 0.0,
    extra_length_bound: float | None = None,
    free_base_start: bool = False,
    order_extra_intervals: bool = False,
) -> MILPProblem:
    """Build the direct standard MILP with unseeded extra intervals."""
    if m < 3:
        raise ValueError("m must be at least 3")
    if extra_count < 0:
        raise ValueError("extra count must be nonnegative")
    if epsilon < 0:
        raise ValueError("epsilon must be nonnegative")
    if extra_length_bound is not None and extra_length_bound < 0:
        raise ValueError("extra length bound must be nonnegative")

    selected_q = optimized_q(m, tie_choice=tie_choice) if q is None else q
    delta = equally_spaced_delta(m, selected_q)
    selected_anchor, base = base_intervals(
        m=m,
        q=selected_q,
        delta=delta,
        anchor=anchor,
    )

    intervals = [
        {
            "index": index,
            "label": interval.label,
            "seed_start": interval.start,
            "seed_length": interval.length,
            "fixed_base": True,
        }
        for index, interval in enumerate(base)
    ]
    for extra_index in range(extra_count):
        intervals.append(
            {
                "index": len(intervals),
                "label": f"extra_{extra_index}",
                "seed_start": None,
                "seed_length": None,
                "fixed_base": False,
            }
        )

    total = len(intervals)
    base_density = selected_q * delta
    default_extra_upper = max(0.0, (1 - 2 * epsilon) / (m + 2))
    extra_upper = (
        default_extra_upper
        if extra_length_bound is None
        else extra_length_bound
    )
    n_lower_bound, n_upper_bound = integer_lift_bounds(m, epsilon)

    problem = MILPProblem(
        f"direct MILP around optimized {m}-sum-free equally spaced construction"
    )
    problem.metadata = {
        "m": m,
        "q": selected_q,
        "delta": delta,
        "base_density": base_density,
        "anchor": selected_anchor,
        "epsilon": epsilon,
        "extra_count": extra_count,
        "extra_length_bound": extra_length_bound,
        "extra_alpha_upper_bound": extra_upper,
        "free_base_start": free_base_start,
        "order_extra_intervals": order_extra_intervals,
        "formulation": "standard_variable_extra_milp",
        "translated_missing_point": False,
        "integer_lift_lower_bound": n_lower_bound,
        "integer_lift_upper_bound": n_upper_bound,
        "intervals": intervals,
    }

    if free_base_start and base:
        shift_lower = -min(interval.start for interval in base)
        shift_upper = 1 - max(interval.end for interval in base)
        problem.add_continuous_variable(
            "base_shift",
            lower_bound=shift_lower,
            upper_bound=shift_upper,
        )
        problem.metadata["base_shift_bounds"] = {
            "lower": shift_lower,
            "upper": shift_upper,
        }

    for index, interval in enumerate(intervals):
        is_base = bool(interval["fixed_base"])
        alpha_upper = delta if is_base else extra_upper
        problem.add_continuous_variable(f"x_{index}", lower_bound=0, upper_bound=1)
        problem.add_continuous_variable(
            f"alpha_{index}",
            lower_bound=0,
            upper_bound=alpha_upper,
        )
        problem.add_inequality(
            name=f"inside_unit_{index}",
            coefficients={f"x_{index}": 1, f"alpha_{index}": 1},
            sense="<=",
            rhs=1,
        )

        if is_base:
            seed_start = float(interval["seed_start"])
            if free_base_start:
                problem.add_equality(
                    name=f"base_spacing_{index}",
                    coefficients={f"x_{index}": 1, "base_shift": -1},
                    rhs=seed_start,
                )
            else:
                problem.add_equality(
                    name=f"fixed_base_start_{index}",
                    coefficients={f"x_{index}": 1},
                    rhs=seed_start,
                )
            problem.add_equality(
                name=f"fixed_base_length_{index}",
                coefficients={f"alpha_{index}": 1},
                rhs=delta,
            )

    # By default the interval list is not ordered: extras may land in any gap.
    # Pairwise order binaries enforce non-overlap without choosing a slot in
    # advance.  Since the extra labels are interchangeable, an optional
    # symmetry convention orders them by start and removes their mutual
    # pairwise binaries.
    if order_extra_intervals:
        first_extra = len(base)
        for index in range(first_extra, total - 1):
            problem.add_inequality(
                name=f"ordered_extra_nonoverlap_{index}_{index + 1}",
                coefficients={
                    f"x_{index}": 1,
                    f"alpha_{index}": 1,
                    f"x_{index + 1}": -1,
                },
                sense="<=",
                rhs=0,
            )

    for i in range(total):
        for j in range(i + 1, total):
            if intervals[i]["fixed_base"] and intervals[j]["fixed_base"]:
                continue
            if (
                order_extra_intervals
                and not intervals[i]["fixed_base"]
                and not intervals[j]["fixed_base"]
            ):
                continue

            order_name = f"before_{i}-{j}"
            problem.add_integer_variable(order_name, lower_bound=0, upper_bound=1)
            problem.add_inequality(
                name=f"nonoverlap_{i}_before_{j}",
                coefficients={
                    f"x_{i}": 1,
                    f"alpha_{i}": 1,
                    f"x_{j}": -1,
                    order_name: 1,
                },
                sense="<=",
                rhs=1,
            )
            problem.add_inequality(
                name=f"nonoverlap_{j}_before_{i}",
                coefficients={
                    f"x_{j}": 1,
                    f"alpha_{j}": 1,
                    f"x_{i}": -1,
                    order_name: -1,
                },
                sense="<=",
                rhs=0,
            )

    for i in range(total):
        for j in range(i, total):
            for ell in range(total):
                n_name = f"n_{i}-{j}-{ell}"
                problem.add_integer_variable(
                    n_name,
                    lower_bound=n_lower_bound,
                    upper_bound=n_upper_bound,
                )

                left_coefficients: dict[str, float] = defaultdict(float)
                left_coefficients[f"x_{i}"] -= 1
                left_coefficients[f"x_{j}"] -= 1
                left_coefficients[f"x_{ell}"] += m
                left_coefficients[f"alpha_{ell}"] += m
                left_coefficients[n_name] += 1
                problem.add_inequality(
                    name=f"sum_free_left_{i}-{j}-{ell}",
                    coefficients=left_coefficients,
                    sense="<=",
                    rhs=-epsilon,
                )

                right_coefficients: dict[str, float] = defaultdict(float)
                right_coefficients[f"x_{i}"] += 1
                right_coefficients[f"x_{j}"] += 1
                right_coefficients[f"alpha_{i}"] += 1
                right_coefficients[f"alpha_{j}"] += 1
                right_coefficients[f"x_{ell}"] -= m
                right_coefficients[n_name] -= 1
                problem.add_inequality(
                    name=f"sum_free_right_{i}-{j}-{ell}",
                    coefficients=right_coefficients,
                    sense="<=",
                    rhs=1 - epsilon,
                )

    problem.set_objective(
        {f"alpha_{index}": 1 for index in range(total)},
        sense="maximize",
    )
    return problem


def solver_options_from_args(args: argparse.Namespace) -> dict[str, object]:
    options: dict[str, object] = {}
    if args.time_limit is not None:
        options["time_limit"] = args.time_limit
    if args.mip_rel_gap is not None:
        options["mip_rel_gap"] = args.mip_rel_gap
    if args.mip_abs_gap is not None:
        options["mip_abs_gap"] = args.mip_abs_gap
    if args.presolve is not None:
        options["presolve"] = args.presolve
    if args.disp:
        options["disp"] = True
    return options


def save_json_outputs(
    problem: MILPProblem,
    solution: MILPSolution,
    *,
    output_dir: Path,
    run_name: str,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    problem_path = output_dir / f"{run_name}_problem.json"
    solution_path = output_dir / f"{run_name}_solution.json"
    problem_path.write_text(problem.to_json(), encoding="utf-8")
    solution.parameters["problem_json_path"] = str(problem_path)
    solution.parameters["solution_json_path"] = str(solution_path)
    solution_path.write_text(solution.to_json(), encoding="utf-8")
    return problem_path, solution_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build and solve a standard-formulation MILP for adding variable "
            "extra intervals to the optimized equally spaced construction."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--m",
        type=int,
        required=True,
        help="integer sum-free multiplier",
    )
    parser.add_argument(
        "--q",
        type=int,
        default=None,
        help="override the optimized q",
    )
    parser.add_argument(
        "--tie-choice",
        choices=["larger", "smaller"],
        default="larger",
        help="which optimized q to use when two q values tie",
    )
    parser.add_argument(
        "--anchor",
        type=int,
        default=None,
        help=(
            "integer value of (2-m)a-m*delta, modulo m-2; omit for the "
            "a=m*delta/(2-m) representative from the construction"
        ),
    )
    parser.add_argument(
        "--extra-count",
        type=nonnegative_int,
        default=0,
        metavar="K",
        help="number of variable extra intervals to add",
    )
    parser.add_argument(
        "--epsilon",
        type=float,
        default=0.0,
        help="positive margin for strict lifted inequalities",
    )
    parser.add_argument(
        "--tolerance",
        type=nonnegative_float,
        default=1e-9,
        help="absolute tolerance for reporting improvement over the base density",
    )
    parser.add_argument(
        "--extra-length-bound",
        type=parse_fraction_float,
        default=None,
        metavar="L",
        help=(
            "optional upper bound for each extra interval length; by default "
            "uses the one-interval width bound 1/(m+2)"
        ),
    )
    parser.add_argument(
        "--free-base-start",
        action="store_true",
        help=(
            "preserve the equally spaced base block's lengths and spacings, "
            "but allow its common translate to vary inside the current "
            "[0,1] representative"
        ),
    )
    parser.add_argument(
        "--ordered-extras",
        action=argparse.BooleanOptionalAction,
        default=False,
        help=(
            "order interchangeable extra intervals by start, adding direct "
            "non-overlap constraints and removing their mutual order binaries"
        ),
    )
    parser.add_argument(
        "--time-limit",
        type=float,
        default=None,
        help="HiGHS time limit in seconds",
    )
    parser.add_argument(
        "--mip-rel-gap",
        type=nonnegative_float,
        default=None,
        help="relative MIP gap termination tolerance passed to HiGHS",
    )
    parser.add_argument(
        "--mip-abs-gap",
        type=nonnegative_float,
        default=None,
        help=(
            "absolute MIP gap termination tolerance passed to HiGHS; set this "
            "as well as --mip-rel-gap when both must be zero"
        ),
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
        "--print-problem",
        action="store_true",
        help="print the full MILP model before solving",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="do not save problem and solution JSON files",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("json_results_tmp"),
        help="directory for saved JSON artifacts",
    )
    parser.add_argument(
        "--run-name",
        default=None,
        help="base filename for saved JSON artifacts",
    )
    parser.add_argument(
        "--require-success",
        action="store_true",
        help="exit with an error if HiGHS does not prove optimality",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    solver_options = solver_options_from_args(args)

    try:
        problem = build_variable_extra_interval_milp(
            m=args.m,
            q=args.q,
            tie_choice=args.tie_choice,
            anchor=args.anchor,
            extra_count=args.extra_count,
            epsilon=args.epsilon,
            extra_length_bound=args.extra_length_bound,
            free_base_start=args.free_base_start,
            order_extra_intervals=args.ordered_extras,
        )
    except ValueError as exc:
        parser.error(str(exc))

    problem.metadata["solver_options"] = dict(solver_options)
    problem.metadata["tolerance"] = args.tolerance

    integer_variables = sum(
        variable.kind == "integer" for variable in problem.variables
    )
    print(
        f"{problem.name}: {len(problem.variables)} variables "
        f"({integer_variables} integer), {len(problem.constraints)} constraints"
    )
    print(
        "base: "
        f"m={problem.metadata['m']}, q={problem.metadata['q']}, "
        f"delta={problem.metadata['delta']:.12g}, "
        f"density={problem.metadata['base_density']:.12g}, "
        f"anchor={problem.metadata['anchor']}, "
        f"extra_count={problem.metadata['extra_count']}, "
        f"free_base_start={problem.metadata['free_base_start']}"
    )

    if args.print_problem:
        print()
        print(problem)

    solution = problem.solve(options=solver_options)
    print()
    print(solution)

    if solution.optimum is not None:
        base_density = float(problem.metadata["base_density"])
        gain = solution.optimum - base_density
        print()
        print(f"base density: {base_density:.12g}")
        print(f"MILP density: {solution.optimum:.12g}")
        print(f"gain:         {gain:.12g}")
        print(f"improved:     {gain > args.tolerance} (tolerance={args.tolerance:g})")
        print()
        print("Intervals:")
        if "base_shift" in solution.values:
            print(f"  base_shift = {float(solution['base_shift']):.12g}")
        for interval in problem.metadata["intervals"]:
            index = int(interval["index"])
            label = str(interval["label"])
            start = float(solution[f"x_{index}"])
            length = float(solution[f"alpha_{index}"])
            print(
                f"  {index}: {label:8s} "
                f"({start:.12g}, {start + length:.12g}) "
                f"length={length:.12g}"
            )

    if not args.no_save:
        epsilon_part = (
            "" if args.epsilon == 0 else f"_eps{filename_float(args.epsilon)}"
        )
        extra_bound_part = (
            ""
            if args.extra_length_bound is None
            else f"_extrabound{filename_float(args.extra_length_bound)}"
        )
        ordered_part = "_ordered1" if args.ordered_extras else ""
        run_name = args.run_name or (
            f"variable_extra_milp_m{args.m}_q{problem.metadata['q']}"
            f"_anchor{problem.metadata['anchor']}"
            f"_freebase{int(args.free_base_start)}"
            f"_extra{args.extra_count}"
            f"{ordered_part}"
            f"{epsilon_part}"
            f"{extra_bound_part}"
        )
        problem_path, solution_path = save_json_outputs(
            problem,
            solution,
            output_dir=args.output_dir,
            run_name=run_name,
        )
        print()
        print(f"Saved problem JSON: {problem_path}")
        print(f"Saved solution JSON: {solution_path}")

    if args.require_success and not solution.success:
        raise SystemExit(solution.message)


if __name__ == "__main__":
    main()
