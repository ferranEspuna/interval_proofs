#!/usr/bin/env python3
"""Reproduce the legal N=5, m=3 formulation/cut profiling matrix."""

from __future__ import annotations

import csv
import itertools
import json
import os
import platform
import shlex
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


ARTIFACT_DIR = Path(__file__).resolve().parent
ROOT = ARTIFACT_DIR.parents[2]
PYTHON = ROOT / ".venv" / "bin" / "python"
PROGRAM = ROOT / "circle_intervals.py"
LOG_DIR = ARTIFACT_DIR / "logs"
RELATIVE_ARTIFACT_DIR = ARTIFACT_DIR.relative_to(ROOT)


@dataclass(frozen=True)
class Configuration:
    translated: bool
    width: bool
    monotonicity: bool
    endpoint: bool
    first_shortest: bool
    second_at_most_last: bool

    @property
    def formulation(self) -> str:
        return "translated" if self.translated else "original"

    @property
    def run_name(self) -> str:
        bits = (
            f"t{int(self.translated)}",
            f"w{int(self.width)}",
            f"mono{int(self.monotonicity)}",
            f"ep{int(self.endpoint)}",
            f"min{int(self.first_shortest)}",
            f"sll{int(self.second_at_most_last)}",
        )
        return "profile_" + "_".join(bits)


def legal_configurations() -> list[Configuration]:
    configs: list[Configuration] = []

    # The translated-only cuts are unavailable in the original formulation.
    for width, monotonicity, endpoint in itertools.product((False, True), repeat=3):
        configs.append(
            Configuration(
                translated=False,
                width=width,
                monotonicity=monotonicity,
                endpoint=endpoint,
                first_shortest=False,
                second_at_most_last=False,
            )
        )

    # In translated mode, endpoint and first-shortest cannot both be enabled.
    for values in itertools.product((False, True), repeat=5):
        width, monotonicity, endpoint, first_shortest, second_at_most_last = values
        if endpoint and first_shortest:
            continue
        configs.append(
            Configuration(
                translated=True,
                width=width,
                monotonicity=monotonicity,
                endpoint=endpoint,
                first_shortest=first_shortest,
                second_at_most_last=second_at_most_last,
            )
        )

    assert len(configs) == 32
    assert sum(not config.translated for config in configs) == 8
    assert sum(config.translated for config in configs) == 24
    assert len({config.run_name for config in configs}) == 32
    return configs


def command_for(config: Configuration) -> list[str]:
    command = [str(PYTHON), str(PROGRAM), "-N", "5", "--m", "3"]
    if config.translated:
        command.append("--translated-missing-point")
    command.append("--width-cuts" if config.width else "--no-width-cuts")
    command.append(
        "--monotonicity-cuts"
        if config.monotonicity
        else "--no-monotonicity-cuts"
    )
    command.append(
        "--endpoint-length-cut" if config.endpoint else "--no-endpoint-length-cut"
    )
    if config.first_shortest:
        command.append("--first-interval-shortest")
    if config.second_at_most_last:
        command.append("--second-interval-at-most-last")
    command.extend(
        [
            "--mip-rel-gap",
            "0",
            "--require-success",
            "--output-dir",
            str(RELATIVE_ARTIFACT_DIR),
            "--run-name",
            config.run_name,
        ]
    )
    return command


def environment_record(configs: list[Configuration]) -> dict[str, Any]:
    import scipy
    from scipy.optimize._highspy._core import _Highs

    git_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    solver_processes = subprocess.run(
        ["ps", "-eo", "pid,etime,pcpu,pmem,cmd"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    solver_processes = [
        line.strip()
        for line in solver_processes
        if "circle_intervals.py" in line and "profile_" not in line
    ]
    return {
        "created_at": datetime.now().astimezone().isoformat(),
        "git_commit": git_commit,
        "platform": platform.platform(),
        "python": platform.python_version(),
        "scipy": scipy.__version__,
        "highs": _Highs().version(),
        "logical_cpu_count": os.cpu_count(),
        "load_average_at_start": list(os.getloadavg()),
        "other_circle_intervals_processes_at_start": solver_processes,
        "timing_method": "time.perf_counter around each complete subprocess",
        "execution_order": "sequential in the order listed in matrix.json",
        "configuration_count": len(configs),
    }


def validate_solution(config: Configuration, solution: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    parameters = solution.get("parameters", {})
    details = solution.get("solver_details", {})
    expected_parameters = {
        "N": 5,
        "m": 3.0,
        "epsilon": 0.0,
        "use_translated_missing_point": config.translated,
        "add_width_cuts": config.width,
        "add_monotonicity_cuts": config.monotonicity,
        "add_endpoint_length_cut": config.endpoint,
        "add_first_interval_shortest_cut": config.first_shortest,
        "add_second_interval_at_most_last_cut": config.second_at_most_last,
    }
    for key, expected in expected_parameters.items():
        if parameters.get(key) != expected:
            errors.append(f"parameter {key}: expected {expected!r}, got {parameters.get(key)!r}")
    if parameters.get("solver_options", {}).get("mip_rel_gap") != 0.0:
        errors.append("saved solver option mip_rel_gap is not 0")
    if solution.get("success") is not True:
        errors.append(f"success is {solution.get('success')!r}")
    if solution.get("status_name") != "optimal":
        errors.append(f"status_name is {solution.get('status_name')!r}")
    optimum = solution.get("optimum")
    dual = details.get("mip_dual_bound")
    gap = details.get("mip_gap")
    if not isinstance(optimum, (int, float)) or abs(optimum - 0.2) > 1e-8:
        errors.append(f"optimum {optimum!r} is not 0.2 within 1e-8")
    if not isinstance(dual, (int, float)) or abs(dual - 0.2) > 1e-8:
        errors.append(f"dual bound {dual!r} is not 0.2 within 1e-8")
    if not isinstance(gap, (int, float)) or abs(gap) > 1e-12:
        errors.append(f"MIP gap {gap!r} is not zero within 1e-12")
    if isinstance(optimum, (int, float)) and isinstance(dual, (int, float)):
        if abs(optimum - dual) > 1e-10:
            errors.append(f"optimum and dual differ by {abs(optimum - dual)}")
    return errors


CSV_FIELDS = [
    "run_name",
    "formulation",
    "translated",
    "width",
    "monotonicity",
    "endpoint",
    "first_shortest",
    "second_at_most_last",
    "wall_seconds",
    "exit_code",
    "success",
    "status_name",
    "optimum",
    "mip_dual_bound",
    "mip_gap",
    "mip_node_count",
    "validation_passed",
    "validation_errors",
    "command",
    "problem_json",
    "solution_json",
    "log",
]


def historical_comparison(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_name = {row["run_name"]: row for row in rows}
    original_historical_name = "profile_t0_w0_mono1_ep1_min0_sll0"
    translated_historical_name = "profile_t1_w1_mono1_ep0_min1_sll1"

    successful = [row for row in rows if row.get("validation_passed")]
    original_rows = [row for row in successful if row["formulation"] == "original"]
    translated_rows = [
        row for row in successful if row["formulation"] == "translated"
    ]

    return {
        "historical_original": {
            "run_name": original_historical_name,
            "wall_seconds": 4.82,
            "mip_node_count": 4329,
            "current": by_name.get(original_historical_name),
        },
        "historical_translated": {
            "run_name": translated_historical_name,
            "wall_seconds": 8.34,
            "mip_node_count": 9475,
            "current": by_name.get(translated_historical_name),
        },
        "current_fastest_original": min(
            original_rows, key=lambda row: row["wall_seconds"], default=None
        ),
        "current_fastest_translated": min(
            translated_rows, key=lambda row: row["wall_seconds"], default=None
        ),
    }


def compact_comparison_row(row: dict[str, Any] | None) -> str:
    if row is None:
        return "not yet available"
    return (
        f"`{row['run_name']}`: {row['wall_seconds']:.3f}s and "
        f"{row['mip_node_count']:,} nodes"
    )


def write_summaries(
    configs: list[Configuration],
    environment: dict[str, Any],
    rows: list[dict[str, Any]],
) -> None:
    with (ARTIFACT_DIR / "summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            csv_row = dict(row)
            csv_row["validation_errors"] = " | ".join(row["validation_errors"])
            writer.writerow({key: csv_row.get(key) for key in CSV_FIELDS})

    comparison = historical_comparison(rows)
    summary = {
        "matrix_definition": {
            "N": 5,
            "m": 3,
            "epsilon": 0.0,
            "mip_rel_gap": 0.0,
            "require_success": True,
            "legal_configuration_count": 32,
            "original_configuration_count": 8,
            "translated_configuration_count": 24,
            "rule": (
                "original fixes first_shortest=second_at_most_last=false; "
                "translated permits all five cut flags except endpoint=true "
                "with first_shortest=true"
            ),
        },
        "environment": environment,
        "completed_runs": len(rows),
        "all_valid": len(rows) == len(configs)
        and all(row["validation_passed"] for row in rows),
        "historical_comparison": comparison,
        "runs": rows,
    }
    (ARTIFACT_DIR / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )

    matrix_lines = [
        "# Reproduced 32-configuration profile: `N=5`, `m=3`",
        "",
        "## Matrix definition",
        "",
        "Every run used `--mip-rel-gap 0 --require-success`, `epsilon=0`, and",
        "was executed sequentially. The binary columns are:",
        "",
        "- `t`: translated-missing-point formulation;",
        "- `w`: width cuts;",
        "- `mono`: lift monotonicity cuts;",
        "- `ep`: endpoint-length cut;",
        "- `min`: first interval shortest;",
        "- `sll`: second interval at most the last.",
        "",
        "The original formulation has `min=sll=0`, giving all `2^3=8` choices",
        "of `w`, `mono`, and `ep`. In translated mode all five cut flags vary,",
        "except `ep=min=1` is illegal. This gives `4 * (4+2)=24` translated",
        "choices and 32 configurations in total.",
        "",
        f"Completed: **{len(rows)}/32**. All completed rows valid: ",
        f"**{all(row['validation_passed'] for row in rows)}**.",
        "",
        "## Results",
        "",
        "| run | t | w | mono | ep | min | sll | wall (s) | optimum | dual | gap | nodes | valid |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|",
    ]
    for row in rows:
        matrix_lines.append(
            "| {run_name} | {translated:d} | {width:d} | {monotonicity:d} | "
            "{endpoint:d} | {first_shortest:d} | {second_at_most_last:d} | "
            "{wall_seconds:.3f} | {optimum:.15g} | {mip_dual_bound:.15g} | "
            "{mip_gap:.3g} | {mip_node_count:,} | {valid} |".format(
                **row, valid="yes" if row["validation_passed"] else "NO"
            )
        )

    historical_original = comparison["historical_original"]
    historical_translated = comparison["historical_translated"]
    matrix_lines.extend(
        [
            "",
            "## Timing comparison",
            "",
            (
                "The historical original winner was "
                f"`{historical_original['run_name']}` at 4.82s and 4,329 nodes. "
                "This reproduction of that configuration is "
                + compact_comparison_row(historical_original["current"])
                + "."
            ),
            "",
            (
                "The historical translated winner was "
                f"`{historical_translated['run_name']}` at 8.34s and 9,475 nodes. "
                "This reproduction of that configuration is "
                + compact_comparison_row(historical_translated["current"])
                + "."
            ),
            "",
            "The fastest configurations by current measured wall time are:",
            "",
            "- original: "
            + compact_comparison_row(comparison["current_fastest_original"])
            + ";",
            "- translated: "
            + compact_comparison_row(comparison["current_fastest_translated"])
            + ".",
            "",
        "Wall time is machine- and load-dependent. See `environment.json` for",
        "the software versions, processor information, initial load, and other",
            "solver jobs that were active at the beginning of this reproduction.",
            "",
            "## Artifacts",
            "",
            "For each run, the directory contains `_problem.json`, `_solution.json`,",
            "and `logs/<run>.log`. Each log records the exact command, timestamps,",
            "wall time, exit code, stdout, and stderr. `summary.csv` and",
            "`summary.json` are the machine-readable summaries; `matrix.json` lists",
            "all configurations and commands in execution order.",
            "",
            "A zero floating-point MIP gap is a solver result, not an independently",
            "checkable exact rational certificate.",
            "",
        ]
    )
    (ARTIFACT_DIR / "SUMMARY.md").write_text(
        "\n".join(matrix_lines), encoding="utf-8"
    )


def run_configuration(config: Configuration, index: int) -> dict[str, Any]:
    command = command_for(config)
    command_text = shlex.join(command)
    problem_path = ARTIFACT_DIR / f"{config.run_name}_problem.json"
    solution_path = ARTIFACT_DIR / f"{config.run_name}_solution.json"
    log_path = LOG_DIR / f"{config.run_name}.log"

    started_at = datetime.now().astimezone().isoformat()
    started = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    wall_seconds = time.perf_counter() - started
    finished_at = datetime.now().astimezone().isoformat()

    log_text = "\n".join(
        [
            f"run_index: {index}/32",
            f"run_name: {config.run_name}",
            f"command: {command_text}",
            f"started_at: {started_at}",
            f"finished_at: {finished_at}",
            f"wall_seconds: {wall_seconds:.9f}",
            f"exit_code: {completed.returncode}",
            "",
            "--- stdout ---",
            completed.stdout,
            "--- stderr ---",
            completed.stderr,
        ]
    )
    log_path.write_text(log_text, encoding="utf-8")

    solution: dict[str, Any] = {}
    read_error: str | None = None
    if solution_path.exists():
        try:
            solution = json.loads(solution_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            read_error = f"could not read solution JSON: {exc}"
    else:
        read_error = "solution JSON was not created"

    validation_errors = validate_solution(config, solution) if solution else []
    if completed.returncode != 0:
        validation_errors.insert(0, f"process exit code was {completed.returncode}")
    if read_error:
        validation_errors.insert(0, read_error)
    if not problem_path.exists():
        validation_errors.insert(0, "problem JSON was not created")

    details = solution.get("solver_details", {})
    row = {
        "run_name": config.run_name,
        "formulation": config.formulation,
        "translated": int(config.translated),
        "width": int(config.width),
        "monotonicity": int(config.monotonicity),
        "endpoint": int(config.endpoint),
        "first_shortest": int(config.first_shortest),
        "second_at_most_last": int(config.second_at_most_last),
        "wall_seconds": wall_seconds,
        "exit_code": completed.returncode,
        "success": solution.get("success"),
        "status_name": solution.get("status_name"),
        "optimum": solution.get("optimum"),
        "mip_dual_bound": details.get("mip_dual_bound"),
        "mip_gap": details.get("mip_gap"),
        "mip_node_count": details.get("mip_node_count"),
        "validation_passed": not validation_errors,
        "validation_errors": validation_errors,
        "command": command_text,
        "problem_json": str(problem_path.relative_to(ROOT)),
        "solution_json": str(solution_path.relative_to(ROOT)),
        "log": str(log_path.relative_to(ROOT)),
    }
    return row


def main() -> int:
    if not PYTHON.is_file() or not PROGRAM.is_file():
        raise SystemExit("run this script from the interval_proofs checkout")
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    configs = legal_configurations()
    matrix = [
        {
            "index": index,
            **asdict(config),
            "formulation": config.formulation,
            "run_name": config.run_name,
            "command": shlex.join(command_for(config)),
        }
        for index, config in enumerate(configs, start=1)
    ]
    (ARTIFACT_DIR / "matrix.json").write_text(
        json.dumps(matrix, indent=2) + "\n", encoding="utf-8"
    )

    environment = environment_record(configs)
    (ARTIFACT_DIR / "environment.json").write_text(
        json.dumps(environment, indent=2) + "\n", encoding="utf-8"
    )

    rows: list[dict[str, Any]] = []
    write_summaries(configs, environment, rows)
    for index, config in enumerate(configs, start=1):
        print(f"[{index:02d}/32] {config.run_name}", flush=True)
        row = run_configuration(config, index)
        rows.append(row)
        result = "PASS" if row["validation_passed"] else "FAIL"
        print(
            f"  {result}: {row['wall_seconds']:.3f}s, "
            f"objective={row['optimum']}, nodes={row['mip_node_count']}",
            flush=True,
        )
        if row["validation_errors"]:
            for error in row["validation_errors"]:
                print(f"  validation error: {error}", flush=True)
        write_summaries(configs, environment, rows)

    all_valid = all(row["validation_passed"] for row in rows)
    print(f"Completed {len(rows)} runs; all_valid={all_valid}", flush=True)
    return 0 if all_valid else 1


if __name__ == "__main__":
    sys.exit(main())
