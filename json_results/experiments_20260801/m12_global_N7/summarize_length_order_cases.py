#!/usr/bin/env python3
"""Summarize the 30 memory-safe m=12,N=7 length-order cases."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("json_results/long_runs/m12_N7_length_order_depth2"),
    )
    args = parser.parse_args()

    closed = 0
    unresolved = 0
    missing = 0
    status_counts: Counter[str] = Counter()
    print("case  status          primal          dual            gap       nodes")
    print("----  --------------  --------------  --------------  --------  --------")
    for second_index in range(1, 7):
        for third_index in range(1, 7):
            if second_index == third_index:
                continue
            case = f"{second_index},{third_index}"
            path = args.output_dir / (
                f"m12_N7_lengthorder_{second_index}-{third_index}_solution.json"
            )
            if not path.exists():
                print(f"{case:<4}  missing")
                missing += 1
                continue

            solution = json.loads(path.read_text(encoding="utf-8"))
            status = str(solution.get("status_name", "unknown"))
            status_counts[status] += 1
            details = solution.get("solver_details", {})
            primal = solution.get("optimum")
            dual = details.get("mip_dual_bound")
            gap = details.get("mip_gap")
            nodes = details.get("mip_node_count")
            print(
                f"{case:<4}  {status:<14}  {str(primal):<14}  "
                f"{str(dual):<14}  {str(gap):<8}  {str(nodes):<8}"
            )
            if status in {"optimal", "infeasible"}:
                closed += 1
            else:
                unresolved += 1

    print()
    print(f"closed: {closed}/30; unresolved: {unresolved}; missing: {missing}")
    print(
        f"optimal: {status_counts['optimal']}; "
        f"infeasible above cutoff: {status_counts['infeasible']}"
    )
    if closed == 30:
        print(
            "All length-order cases are closed. Subject to the numerical "
            "smaller-subunion bounds, their union covers the all-endpoints-free model."
        )
    else:
        print(
            "The global length-order audit is not closed. Split or extend the "
            "unresolved cases rather than rerunning completed cases."
        )


if __name__ == "__main__":
    main()
