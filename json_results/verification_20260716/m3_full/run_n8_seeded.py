#!/usr/bin/env python3
"""Reproduce the seeded zero-gap N=8, m=3 run retained in this directory.

SciPy's public ``milp`` wrapper does not expose a MIP start, so this fixed
campaign runner uses the private HiGHS binding bundled with the recorded SciPy
version.  The optimization model itself is still built by ``circle_intervals``.
"""

from __future__ import annotations

import math
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import numpy as np
from scipy.optimize._highspy import _core as highs_core
from scipy.sparse import coo_array

from circle_intervals import (
    build_circle_interval_problem,
    solution_visualizer_state,
    visualizer_state_url,
)
from milp_problem import INTEGER, MILPProblem, MILPSolution

OUTPUT_DIR = ROOT / "json_results/verification_20260716/m3_full"
MIP_REL_GAP = float(os.environ.get("N8_MIP_REL_GAP", "0"))
MIP_ABS_GAP = float(os.environ.get("N8_MIP_ABS_GAP", "0"))
ADD_WIDTH_CUTS = os.environ.get("N8_WIDTH_CUTS", "1") not in {
    "0",
    "false",
    "False",
}
ADD_TOTAL_LENGTH_CUTOFF = os.environ.get("N8_TOTAL_LENGTH_CUTOFF", "1") not in {
    "0",
    "false",
    "False",
}
USE_TRANSLATED_FORMULATION = os.environ.get("N8_TRANSLATED", "0") in {
    "1",
    "true",
    "True",
}
RANDOM_SEED = int(os.environ.get("N8_RANDOM_SEED", "0"))
GAP_STEM = "gap0" if MIP_REL_GAP == 0 else f"gap{MIP_REL_GAP:g}"
ABS_GAP_STEM = (
    "absgap0" if MIP_ABS_GAP == 0 else f"absgap{MIP_ABS_GAP:g}"
)
WIDTH_STEM = "width" if ADD_WIDTH_CUTS else "no_width"
CUTOFF_STEM = "cutoff" if ADD_TOTAL_LENGTH_CUTOFF else "no_cutoff"
FORMULATION_STEM = "translated" if USE_TRANSLATED_FORMULATION else "original"
RANDOM_STEM = "" if RANDOM_SEED == 0 else f"_rng{RANDOM_SEED}"
STEM = (
    f"m3_N8_full_seed_{FORMULATION_STEM}_{WIDTH_STEM}_"
    f"{CUTOFF_STEM}{RANDOM_STEM}_{GAP_STEM}_{ABS_GAP_STEM}"
)
PROBLEM_PATH = OUTPUT_DIR / f"{STEM}_problem.json"
SOLUTION_PATH = OUTPUT_DIR / f"{STEM}_solution.json"


def highs_lp(problem: MILPProblem) -> tuple[highs_core.HighsLp, dict[str, int]]:
    variable_index = {
        variable.name: index for index, variable in enumerate(problem.variables)
    }
    variable_count = len(problem.variables)
    row_count = len(problem.constraints)

    costs = np.zeros(variable_count)
    assert problem.objective is not None
    for name, coefficient in problem.objective.coefficients.items():
        costs[variable_index[name]] = -coefficient  # maximize via minimization

    lower_bounds = np.array(
        [
            -highs_core.kHighsInf
            if variable.lower_bound is None
            else variable.lower_bound
            for variable in problem.variables
        ],
        dtype=float,
    )
    upper_bounds = np.array(
        [
            highs_core.kHighsInf
            if variable.upper_bound is None
            else variable.upper_bound
            for variable in problem.variables
        ],
        dtype=float,
    )

    row_lower = np.full(row_count, -highs_core.kHighsInf)
    row_upper = np.full(row_count, highs_core.kHighsInf)
    rows: list[int] = []
    columns: list[int] = []
    coefficients: list[float] = []
    for row, constraint in enumerate(problem.constraints):
        for name, coefficient in constraint.coefficients.items():
            rows.append(row)
            columns.append(variable_index[name])
            coefficients.append(coefficient)
        if constraint.sense == "==":
            row_lower[row] = row_upper[row] = constraint.rhs
        elif constraint.sense == "<=":
            row_upper[row] = constraint.rhs
        else:
            row_lower[row] = constraint.rhs

    matrix = coo_array(
        (coefficients, (rows, columns)),
        shape=(row_count, variable_count),
    ).tocsc()

    lp = highs_core.HighsLp()
    lp.num_col_ = variable_count
    lp.num_row_ = row_count
    lp.col_cost_ = costs
    lp.col_lower_ = lower_bounds
    lp.col_upper_ = upper_bounds
    lp.row_lower_ = row_lower
    lp.row_upper_ = row_upper
    lp.a_matrix_.num_col_ = variable_count
    lp.a_matrix_.num_row_ = row_count
    lp.a_matrix_.format_ = highs_core.MatrixFormat.kColwise
    lp.a_matrix_.start_ = matrix.indptr.astype(np.int32)
    lp.a_matrix_.index_ = matrix.indices.astype(np.int32)
    lp.a_matrix_.value_ = matrix.data
    lp.integrality_ = [
        highs_core.HighsVarType(1 if variable.kind == INTEGER else 0)
        for variable in problem.variables
    ]
    return lp, variable_index


def replay(problem: MILPProblem, raw_values: list[float]) -> dict[str, object]:
    values = {
        variable.name: raw_values[index]
        for index, variable in enumerate(problem.variables)
    }
    max_bound = 0.0
    max_integrality = 0.0
    for index, variable in enumerate(problem.variables):
        value = raw_values[index]
        if variable.lower_bound is not None:
            max_bound = max(max_bound, variable.lower_bound - value)
        if variable.upper_bound is not None:
            max_bound = max(max_bound, value - variable.upper_bound)
        if variable.kind == INTEGER:
            max_integrality = max(max_integrality, abs(value - round(value)))

    max_row = 0.0
    worst_row: str | None = None
    for constraint in problem.constraints:
        lhs = sum(
            coefficient * values[name]
            for name, coefficient in constraint.coefficients.items()
        )
        if constraint.sense == "==":
            violation = abs(lhs - constraint.rhs)
        elif constraint.sense == "<=":
            violation = max(0.0, lhs - constraint.rhs)
        else:
            violation = max(0.0, constraint.rhs - lhs)
        if violation > max_row:
            max_row = violation
            worst_row = constraint.name

    return {
        "max_bound_violation": max(0.0, max_bound),
        "max_integrality_violation": max_integrality,
        "max_row_violation": max_row,
        "worst_row": worst_row,
    }


def main() -> None:
    problem = build_circle_interval_problem(
        N=8,
        m=3,
        use_translated_missing_point=USE_TRANSLATED_FORMULATION,
        add_width_cuts=ADD_WIDTH_CUTS,
        add_monotonicity_cuts=True,
        add_endpoint_length_cut=not USE_TRANSLATED_FORMULATION,
        add_first_interval_shortest_cut=USE_TRANSLATED_FORMULATION,
        add_second_interval_at_most_last_cut=USE_TRANSLATED_FORMULATION,
        subset_alpha_bounds=[(7, 0.2)],
        total_length_lower_bound=0.2 if ADD_TOTAL_LENGTH_CUTOFF else None,
    )
    if USE_TRANSLATED_FORMULATION:
        # Translate [0.4,0.6] to [0,0.2], split it into eight equal adjacent
        # open intervals, and use the translated missing point t=0.4.  Splitting
        # only removes endpoints, so the construction remains feasible and now
        # satisfies the first-interval-shortest normalization without padding.
        seed = {"t": 0.4}
        for index in range(8):
            seed[f"x_{index}"] = index / 40
            seed[f"alpha_{index}"] = 1 / 40
        for variable in problem.variables:
            if variable.name.startswith("n_"):
                i, j, ell = (int(part) for part in variable.name[2:].split("-"))
                seed[variable.name] = (i + j - 3 * ell - 19) // 40
        seed_justification = (
            "the translated one-interval construction [0,0.2], split into "
            "eight equal adjacent open intervals, with missing point t=0.4"
        )
    else:
        seed = {"x_0": 0.4, "alpha_0": 0.2}
        for index in range(1, 8):
            seed[f"x_{index}"] = 0.6
            seed[f"alpha_{index}"] = 0.0
        # For this padded one-interval construction every lifted interaction
        # lies in [-1,0], so n=-1 completes the geometric seed exactly.
        for variable in problem.variables:
            if variable.name.startswith("n_"):
                seed[variable.name] = -1.0
        seed_justification = (
            "the explicit one-interval 3-sum-free construction [0.4,0.6]; "
            "all corresponding integer lifts equal -1"
        )

    problem.metadata.update(
        {
            "output_dir": str(OUTPUT_DIR.relative_to(ROOT)),
            "solver_options": {
                "mip_rel_gap": MIP_REL_GAP,
                "mip_abs_gap": MIP_ABS_GAP,
                "random_seed": RANDOM_SEED,
            },
            "solver_interface": "scipy.optimize._highspy._core._Highs",
            "mip_start": seed,
            "mip_start_justification": seed_justification,
        }
    )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PROBLEM_PATH.write_text(problem.to_json(), encoding="utf-8")

    lp, variable_index = highs_lp(problem)
    highs = highs_core._Highs()
    assert highs.passModel(lp) == highs_core.HighsStatus.kOk
    assert highs.setOptionValue("output_flag", False) == highs_core.HighsStatus.kOk
    assert (
        highs.setOptionValue("mip_rel_gap", MIP_REL_GAP)
        == highs_core.HighsStatus.kOk
    )
    assert (
        highs.setOptionValue("mip_abs_gap", MIP_ABS_GAP)
        == highs_core.HighsStatus.kOk
    )
    assert (
        highs.setOptionValue("random_seed", RANDOM_SEED)
        == highs_core.HighsStatus.kOk
    )
    seed_indices = np.array(
        [variable_index[name] for name in seed],
        dtype=np.int32,
    )
    seed_values = np.array(list(seed.values()), dtype=float)
    seed_status = highs.setSolution(len(seed), seed_indices, seed_values)
    if seed_status != highs_core.HighsStatus.kOk:
        raise RuntimeError(f"HiGHS rejected the partial MIP start: {seed_status}")

    started = time.monotonic()
    run_status = highs.run()
    wall_seconds = time.monotonic() - started
    model_status = highs.getModelStatus()
    success = (
        run_status == highs_core.HighsStatus.kOk
        and model_status == highs_core.HighsModelStatus.kOptimal
    )
    status_text = highs.modelStatusToString(model_status)
    raw_values = list(highs.getSolution().col_value)
    info = highs.getInfo()
    optimum = -float(highs.getObjectiveValue()) if raw_values else None

    named_values: dict[str, float | int] = {}
    for variable, value in zip(problem.variables, raw_values):
        value = float(value)
        if variable.kind == INTEGER and math.isclose(
            value, round(value), abs_tol=1e-8
        ):
            named_values[variable.name] = int(round(value))
        else:
            named_values[variable.name] = value

    solution = MILPSolution(
        problem_name=problem.name,
        status=0 if success else 1,
        status_name="optimal" if success else status_text.lower().replace(" ", "_"),
        success=success,
        message=f"HiGHS model status: {status_text}",
        objective_sense="maximize",
        optimum=optimum,
        values=named_values,
        parameters={
            **problem.metadata,
            "problem_json_path": str(PROBLEM_PATH.relative_to(ROOT)),
            "solution_json_path": str(SOLUTION_PATH.relative_to(ROOT)),
            "mip_start_status": str(seed_status),
            "wall_seconds": wall_seconds,
            "independent_replay": replay(problem, raw_values),
        },
        solver_details={
            "mip_dual_bound": -float(info.mip_dual_bound),
            "mip_gap": float(info.mip_gap),
            "mip_node_count": int(info.mip_node_count),
        },
    )
    if raw_values:
        state = solution_visualizer_state(solution, N=8, m=3)
        solution.parameters["visualizer_state"] = state
        solution.parameters["visualizer_url"] = visualizer_state_url(state)
    SOLUTION_PATH.write_text(solution.to_json(), encoding="utf-8")

    print(
        f"status={solution.status_name} optimum={solution.optimum} "
        f"dual={solution.solver_details['mip_dual_bound']} "
        f"gap={solution.solver_details['mip_gap']} "
        f"nodes={solution.solver_details['mip_node_count']} "
        f"wall={wall_seconds:.3f}s"
    )
    print(f"replay={solution.parameters['independent_replay']}")
    print(f"saved={PROBLEM_PATH.relative_to(ROOT)}, {SOLUTION_PATH.relative_to(ROOT)}")
    if not success:
        raise SystemExit(f"HiGHS did not prove optimality: {status_text}")


if __name__ == "__main__":
    main()
