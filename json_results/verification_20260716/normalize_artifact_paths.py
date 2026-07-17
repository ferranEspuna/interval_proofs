#!/usr/bin/env python3
"""Normalize saved solution artifact links to repository-relative paths."""

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
VERIFICATION_DIR = Path(__file__).resolve().parent
ARTIFACT_DIRS = [
    VERIFICATION_DIR / "higher_m_general_m11-13",
    VERIFICATION_DIR / "tiny_intervals_two_extra",
    VERIFICATION_DIR / "tiny_intervals_two_extra_unbounded_crosschecks",
    VERIFICATION_DIR / "tiny_intervals_three_extra",
    VERIFICATION_DIR / "tiny_intervals_extra_count_saturation",
]


def relative(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def normalize_solution(solution_path: Path) -> bool:
    stem = solution_path.name.removesuffix("_solution.json")
    candidates = [
        solution_path.with_name(f"{stem}_problem.json.gz"),
        solution_path.with_name(f"{stem}_problem.json"),
    ]
    existing = [path for path in candidates if path.exists()]
    if len(existing) != 1:
        raise RuntimeError(f"expected one problem for {solution_path}: {existing}")

    solution = json.loads(solution_path.read_text(encoding="utf-8"))
    parameters = solution["parameters"]
    normalized_problem = relative(existing[0])
    normalized_solution = relative(solution_path)
    changed = (
        parameters.get("problem_json_path") != normalized_problem
        or parameters.get("solution_json_path") != normalized_solution
    )
    parameters["problem_json_path"] = normalized_problem
    parameters["solution_json_path"] = normalized_solution
    if changed:
        solution_path.write_text(
            json.dumps(solution, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return changed


def main():
    paths = [
        path
        for artifact_dir in ARTIFACT_DIRS
        for path in sorted(artifact_dir.glob("*_solution.json"))
    ]
    changed = sum(normalize_solution(path) for path in paths)
    print(f"normalized {changed} of {len(paths)} solution files")


if __name__ == "__main__":
    main()
