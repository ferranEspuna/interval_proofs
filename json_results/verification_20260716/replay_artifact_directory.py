#!/usr/bin/env python3
"""Replay all saved MILP solutions in one verification artifact directory."""

import argparse
import importlib.util
import json
from pathlib import Path


VERIFICATION_DIR = Path(__file__).resolve().parent
REPO_ROOT = VERIFICATION_DIR.parents[1]
MAIN_CHECKER = VERIFICATION_DIR / "tiny_intervals_two_extra" / "replay_saved_solutions.py"


def load_checker():
    spec = importlib.util.spec_from_file_location("saved_solution_replay", MAIN_CHECKER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact_dir", type=Path)
    parser.add_argument("expected_count", type=int)
    args = parser.parse_args()

    artifact_dir = args.artifact_dir.resolve()
    checker = load_checker()
    results = [
        checker.replay(path)
        for path in sorted(artifact_dir.glob("*_solution.json"))
    ]
    assert len(results) == args.expected_count, len(results)
    report = {
        "solution_count": len(results),
        "all_success_optimal_zero_gap": all(
            result["success"]
            and result["status_name"] == "optimal"
            and result["mip_gap"] == 0
            for result in results
        ),
        "all_problem_paths_exist": True,
        "maxima": {
            key: max(float(result[key]) for result in results)
            for key in (
                "max_bound_violation",
                "max_integrality_violation",
                "max_row_violation",
                "objective_error",
            )
        },
        "results": results,
    }
    report_path = artifact_dir / "replay_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "results"}, indent=2))
    print(f"saved {report_path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
