#!/usr/bin/env python3
"""Replay the preserved two-extra numerical cross-check artifacts."""

import importlib.util
import json
from pathlib import Path


ARTIFACT_DIR = Path(__file__).resolve().parent
REPO_ROOT = ARTIFACT_DIR.parents[2]
MAIN_CHECKER = ARTIFACT_DIR.parent / "tiny_intervals_two_extra" / "replay_saved_solutions.py"
REPORT_PATH = ARTIFACT_DIR / "replay_report.json"


def load_main_checker():
    spec = importlib.util.spec_from_file_location("two_extra_replay", MAIN_CHECKER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def main():
    checker = load_main_checker()
    results = [
        checker.replay(path.resolve())
        for path in sorted(ARTIFACT_DIR.glob("*_solution.json"))
    ]
    assert len(results) == 10, len(results)
    strict_results = [
        result for result in results if "mipabsgap0_mipfeastol1e-10" in result["solution"]
    ]
    assert len(strict_results) == 2, len(strict_results)
    report = {
        "solution_count": len(results),
        "all_success_optimal_zero_gap": all(
            result["success"]
            and result["status_name"] == "optimal"
            and result["mip_gap"] == 0
            for result in results
        ),
        "maxima": {
            key: max(float(result[key]) for result in results)
            for key in (
                "max_bound_violation",
                "max_integrality_violation",
                "max_row_violation",
                "objective_error",
            )
        },
        "strict_mip_tolerance_maxima": {
            key: max(float(result[key]) for result in strict_results)
            for key in (
                "max_bound_violation",
                "max_integrality_violation",
                "max_row_violation",
                "objective_error",
            )
        },
        "results": results,
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "results"}, indent=2))


if __name__ == "__main__":
    main()
