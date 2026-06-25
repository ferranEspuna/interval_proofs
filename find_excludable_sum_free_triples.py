"""Find maximal d-sum-free triples that can be omitted without changing a bound.

The default experiment is the translated-missing-point setup used for
small-interval investigations:

    N = 2, 3, 4, 5
    d = 3
    target bound = 1/5
    x_0 = 0 via --translated-missing-point
    alpha_0 <= alpha_i via --first-interval-shortest
    alpha_1 <= alpha_{N-1} via --second-interval-at-most-last
    no endpoint-length cut

The output is a text report listing maximal families of exact triples
(i, j, k), i <= j, whose lifted conditions can be excluded while the MILP
still proves the requested bound.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import math
from pathlib import Path
from time import perf_counter
from typing import Iterable

from circle_intervals import build_circle_interval_problem, parse_subset_alpha_bound

Triple = tuple[int, int, int]
TripleSet = frozenset[Triple]


@dataclass
class SearchStats:
    solves: int = 0
    cache_hits: int = 0
    invalid_sets: int = 0
    valid_sets: int = 0
    union_prunes: int = 0
    stopped_by_max_families: bool = False
    timed_out: bool = False
    started_at: float = field(default_factory=perf_counter)

    @property
    def elapsed_seconds(self) -> float:
        return perf_counter() - self.started_at


def all_sum_free_triples(N: int) -> list[Triple]:
    return [(i, j, k) for i in range(N) for j in range(i, N) for k in range(N)]


def format_triple(triple: Triple, d: float) -> str:
    i, j, k = triple
    return f"({i},{j},{k}) = I_{i} + I_{j} - {d:g} I_{k}"


def format_family(family: Iterable[Triple], d: float) -> str:
    triples = sorted(family)
    if not triples:
        return "  <empty family>"
    return "\n".join(f"  - {format_triple(triple, d)}" for triple in triples)


class BoundOracle:
    def __init__(
        self,
        *,
        N: int,
        d: float,
        epsilon: float,
        target_bound: float,
        tolerance: float,
        add_width_cuts: bool,
        add_monotonicity_cuts: bool,
        subset_alpha_bounds: list[tuple[int, float]],
        solver_options: dict[str, object],
    ) -> None:
        self.N = N
        self.d = d
        self.epsilon = epsilon
        self.target_bound = target_bound
        self.tolerance = tolerance
        self.add_width_cuts = add_width_cuts
        self.add_monotonicity_cuts = add_monotonicity_cuts
        self.subset_alpha_bounds = list(subset_alpha_bounds)
        self.solver_options = dict(solver_options)
        self.cache: dict[TripleSet, tuple[bool, float | None, str]] = {}
        self.stats = SearchStats()

    def proves_bound(self, excluded: Iterable[Triple]) -> tuple[bool, float | None, str]:
        key = frozenset(excluded)
        cached = self.cache.get(key)
        if cached is not None:
            self.stats.cache_hits += 1
            return cached

        problem = build_circle_interval_problem(
            N=self.N,
            d=self.d,
            epsilon=self.epsilon,
            use_translated_missing_point=True,
            add_width_cuts=self.add_width_cuts,
            add_monotonicity_cuts=self.add_monotonicity_cuts,
            add_endpoint_length_cut=False,
            add_first_interval_shortest_cut=True,
            add_second_interval_at_most_last_cut=True,
            exclude_sum_free_exact_triples=sorted(key),
            subset_alpha_bounds=self.subset_alpha_bounds,
        )
        solution = problem.solve(options=self.solver_options)
        self.stats.solves += 1

        optimum = solution.optimum
        proves = (
            solution.success
            and optimum is not None
            and optimum <= self.target_bound + self.tolerance
        )
        if proves:
            self.stats.valid_sets += 1
        else:
            self.stats.invalid_sets += 1

        result = (proves, optimum, solution.message)
        self.cache[key] = result
        return result


def keep_maximal(families: list[TripleSet]) -> list[TripleSet]:
    maximal: list[TripleSet] = []
    for family in sorted(set(families), key=lambda item: (-len(item), sorted(item))):
        if any(family < other for other in maximal):
            continue
        maximal = [other for other in maximal if not other < family]
        maximal.append(family)
    return sorted(maximal, key=lambda item: (len(item), sorted(item)))


def find_maximal_families(
    *,
    oracle: BoundOracle,
    candidates: list[Triple],
    max_families: int | None,
    search_time_limit: float | None,
) -> tuple[list[TripleSet], bool]:
    discovered: list[TripleSet] = []
    stop_search = False
    deadline = (
        None
        if search_time_limit is None
        else perf_counter() + search_time_limit
    )

    def should_stop() -> bool:
        nonlocal stop_search
        if stop_search:
            return True
        if deadline is not None and perf_counter() >= deadline:
            oracle.stats.timed_out = True
            stop_search = True
            return True
        return False

    def record(family: TripleSet) -> None:
        nonlocal discovered, stop_search
        if any(family <= other for other in discovered):
            return
        for triple in candidates:
            if triple in family:
                continue
            if should_stop():
                return
            extension = frozenset(set(family).union({triple}))
            proves, _, _ = oracle.proves_bound(extension)
            if proves:
                return
        discovered = [other for other in discovered if not other < family]
        discovered.append(family)
        if max_families is not None and len(discovered) >= max_families:
            oracle.stats.stopped_by_max_families = True
            stop_search = True

    def seed_greedy_family() -> None:
        family: TripleSet = frozenset()
        for triple in candidates:
            if should_stop():
                return
            extension = frozenset(set(family).union({triple}))
            proves, _, _ = oracle.proves_bound(extension)
            if proves:
                family = extension
        record(family)

    def search(prefix: TripleSet, tail: tuple[Triple, ...]) -> None:
        if should_stop():
            return
        if not tail:
            record(prefix)
            return

        union_candidate = frozenset(set(prefix).union(tail))
        proves, _, _ = oracle.proves_bound(union_candidate)
        if proves:
            oracle.stats.union_prunes += 1
            record(union_candidate)
            return

        extended = False
        for index, triple in enumerate(tail):
            if should_stop():
                return
            new_prefix = frozenset(set(prefix).union({triple}))
            proves, _, _ = oracle.proves_bound(new_prefix)
            if not proves:
                continue
            extended = True
            search(new_prefix, tail[index + 1 :])

        if not extended:
            record(prefix)

    seed_greedy_family()
    search(frozenset(), tuple(candidates))
    complete = not oracle.stats.stopped_by_max_families and not oracle.stats.timed_out
    return keep_maximal(discovered), complete


def parse_n_values(text: str) -> list[int]:
    values: list[int] = []
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        value = int(part)
        if value < 1:
            raise argparse.ArgumentTypeError("N values must be positive")
        values.append(value)
    if not values:
        raise argparse.ArgumentTypeError("at least one N value is required")
    return values


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Find maximal exact d-sum-free triples that can be excluded while "
            "preserving a target bound."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--n-values",
        type=parse_n_values,
        default=[2, 3, 4, 5],
        help="comma-separated interval counts to test",
    )
    parser.add_argument("--d", type=float, default=3.0, help="sum-free multiplier")
    parser.add_argument(
        "--target-bound",
        type=float,
        default=0.2,
        help="bound that the relaxed model must still prove",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=1e-9,
        help="absolute tolerance for comparing the optimum to the target bound",
    )
    parser.add_argument(
        "--epsilon",
        type=float,
        default=0.0,
        help="positive margin for strict sum-free inequalities",
    )
    parser.add_argument(
        "--width-cuts",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="include redundant width cuts",
    )
    parser.add_argument(
        "--monotonicity-cuts",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="include integer lift monotonicity cuts",
    )
    parser.add_argument(
        "--subset-alpha-bound",
        dest="subset_alpha_bounds",
        action="append",
        type=parse_subset_alpha_bound,
        default=[],
        metavar="N_PRIME:BOUND",
        help="add subset alpha bounds to every tested model; can be repeated",
    )
    parser.add_argument(
        "--mip-rel-gap",
        type=float,
        default=0.0,
        help="relative MIP gap passed to HiGHS",
    )
    parser.add_argument(
        "--time-limit",
        type=float,
        default=None,
        help="optional per-solve HiGHS time limit in seconds",
    )
    parser.add_argument(
        "--node-limit",
        type=int,
        default=None,
        help="optional per-solve HiGHS node limit",
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=None,
        help="optional HiGHS thread count",
    )
    parser.add_argument(
        "--max-families",
        type=int,
        default=None,
        help="stop after this many maximal families per N; omit for exhaustive search",
    )
    parser.add_argument(
        "--search-time-limit",
        type=float,
        default=None,
        help="optional maximal-family search time limit per N, after singleton tests",
    )
    parser.add_argument(
        "--output-txt",
        type=Path,
        default=Path("json_results/maximal_excludable_triples_d3_N2-5.txt"),
        help="text report path",
    )
    return parser


def solver_options_from_args(args: argparse.Namespace) -> dict[str, object]:
    options: dict[str, object] = {"mip_rel_gap": args.mip_rel_gap}
    if args.time_limit is not None:
        options["time_limit"] = args.time_limit
    if args.node_limit is not None:
        options["node_limit"] = args.node_limit
    if args.threads is not None:
        options["threads"] = args.threads
    return options


def main() -> None:
    args = build_parser().parse_args()
    args.output_txt.parent.mkdir(parents=True, exist_ok=True)
    solver_options = solver_options_from_args(args)

    lines: list[str] = [
        "Maximal excludable d-sum-free triples",
        "======================================",
        "",
        "A family is listed when excluding exactly those triples, and no larger",
        "family found by the search, still lets the translated MILP prove the",
        f"target bound {args.target_bound:g}.",
        "",
        "Fixed model settings:",
        f"  d = {args.d:g}",
        f"  epsilon = {args.epsilon:g}",
        "  translated_missing_point = True",
        "  first_interval_shortest = True",
        "  second_interval_at_most_last = True",
        "  endpoint_length_cut = False",
        f"  width_cuts = {args.width_cuts}",
        f"  monotonicity_cuts = {args.monotonicity_cuts}",
        f"  subset_alpha_bounds = {args.subset_alpha_bounds}",
        f"  solver_options = {solver_options}",
        f"  max_families = {args.max_families}",
        f"  search_time_limit = {args.search_time_limit}",
        "",
    ]

    for N in args.n_values:
        print(f"N={N}: computing full-model bound")
        oracle = BoundOracle(
            N=N,
            d=args.d,
            epsilon=args.epsilon,
            target_bound=args.target_bound,
            tolerance=args.tolerance,
            add_width_cuts=args.width_cuts,
            add_monotonicity_cuts=args.monotonicity_cuts,
            subset_alpha_bounds=args.subset_alpha_bounds,
            solver_options=solver_options,
        )
        full_proves, full_bound, full_message = oracle.proves_bound(())
        if not full_proves:
            lines.extend(
                [
                    f"N = {N}",
                    "-" * (4 + len(str(N))),
                    (
                        "Full model did not prove the requested bound; "
                        "skipping maximal-family search."
                    ),
                    f"  full optimum = {full_bound}",
                    f"  solver message = {full_message}",
                    "",
                ]
            )
            continue

        all_triples = all_sum_free_triples(N)
        removable: list[Triple] = []
        print(f"N={N}: testing {len(all_triples)} singleton exclusions")
        for triple in all_triples:
            proves, _, _ = oracle.proves_bound((triple,))
            if proves:
                removable.append(triple)

        print(
            f"N={N}: {len(removable)} singleton-removable triples; "
            "searching maximal families"
        )
        families, search_complete = find_maximal_families(
            oracle=oracle,
            candidates=removable,
            max_families=args.max_families,
            search_time_limit=args.search_time_limit,
        )

        lines.extend(
            [
                f"N = {N}",
                "-" * (4 + len(str(N))),
                f"Full-model optimum: {full_bound}",
                f"All triples: {len(all_triples)}",
                f"Singleton-removable triples: {len(removable)}",
                f"Maximal families found: {len(families)}",
                f"Search complete: {search_complete}",
                f"Stopped by max families: {oracle.stats.stopped_by_max_families}",
                f"Timed out: {oracle.stats.timed_out}",
                f"Search solves: {oracle.stats.solves}",
                f"Cache hits: {oracle.stats.cache_hits}",
                f"Union-prune successes: {oracle.stats.union_prunes}",
                f"Elapsed seconds: {oracle.stats.elapsed_seconds:.3f}",
                "",
            ]
        )
        if not search_complete:
            lines.extend(
                [
                    "WARNING: this N block is partial. The families below are",
                    "maximality-checked against the singleton-removable triples,",
                    "but the search did not prove that all maximal families",
                    "have been enumerated.",
                    "",
                ]
            )

        for family_index, family in enumerate(families, start=1):
            lines.extend(
                [
                    f"Family {family_index} ({len(family)} triples):",
                    format_family(family, args.d),
                    "",
                ]
            )

        args.output_txt.write_text("\n".join(lines), encoding="utf-8")
        print(
            f"N={N}: wrote {len(families)} families to {args.output_txt} "
            f"after {oracle.stats.elapsed_seconds:.1f}s"
        )

    args.output_txt.write_text("\n".join(lines), encoding="utf-8")
    print(f"Final report written to {args.output_txt}")


if __name__ == "__main__":
    main()
