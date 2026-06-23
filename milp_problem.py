"""Small named-variable MILP wrapper backed by SciPy/HiGHS."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from typing import Any, Mapping

try:
    import numpy as np
    from scipy.optimize import Bounds, LinearConstraint, milp
except ImportError as exc:
    raise RuntimeError(
        "MILPProblem.solve() requires SciPy, whose milp() function uses "
        "the optimized HiGHS solver. Install it with: "
        "python3 -m pip install scipy"
    ) from exc

VariableKind = str
ConstraintSense = str
ObjectiveSense = str


CONTINUOUS = "continuous"
INTEGER = "integer"

LE = "<="
GE = ">="
EQ = "=="

MINIMIZE = "minimize"
MAXIMIZE = "maximize"


def _require_name(name: str, what: str) -> str:
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"{what} name must be a non-empty string")
    return name


def _normalize_bound(value: float | None, *, lower: bool) -> float | None:
    if value is None:
        return None

    value = float(value)
    if math.isfinite(value):
        return value

    if lower and value == -math.inf:
        return None
    if not lower and value == math.inf:
        return None

    side = "lower" if lower else "upper"
    raise ValueError(f"{side} bound must be finite or unbounded")


def _normalize_coefficients(coefficients: Mapping[str, float]) -> dict[str, float]:
    normalized: dict[str, float] = {}
    for variable_name, coefficient in coefficients.items():
        _require_name(variable_name, "variable")
        coefficient = float(coefficient)
        if coefficient != 0.0:
            normalized[variable_name] = coefficient

    if not normalized:
        raise ValueError("linear expression must contain at least one non-zero coefficient")

    return normalized


def _format_number(value: float) -> str:
    if math.isfinite(value) and math.isclose(value, round(value), abs_tol=1e-12):
        return str(int(round(value)))
    return f"{value:g}"


def _format_bound(value: float | None, *, lower: bool) -> str:
    if value is None:
        return "-inf" if lower else "inf"
    return _format_number(value)


def _format_expression(coefficients: Mapping[str, float]) -> str:
    parts: list[str] = []
    for variable_name, coefficient in coefficients.items():
        sign = "-" if coefficient < 0 else "+"
        magnitude = abs(coefficient)

        if math.isclose(magnitude, 1.0, abs_tol=1e-12):
            term = variable_name
        else:
            term = f"{_format_number(magnitude)}*{variable_name}"

        if not parts:
            parts.append(term if sign == "+" else f"-{term}")
        else:
            parts.append(f" {sign} {term}")

    return "".join(parts) if parts else "0"


@dataclass
class NamedVariable:
    """A named MILP variable."""

    name: str
    kind: VariableKind = CONTINUOUS
    lower_bound: float | None = None
    upper_bound: float | None = None

    def __post_init__(self) -> None:
        self.name = _require_name(self.name, "variable")

        if self.kind not in {CONTINUOUS, INTEGER}:
            raise ValueError(f"variable kind must be {CONTINUOUS!r} or {INTEGER!r}")

        self.lower_bound = _normalize_bound(self.lower_bound, lower=True)
        self.upper_bound = _normalize_bound(self.upper_bound, lower=False)

        if (
            self.lower_bound is not None
            and self.upper_bound is not None
            and self.lower_bound > self.upper_bound
        ):
            raise ValueError("lower bound cannot be greater than upper bound")

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "lower_bound": self.lower_bound,
            "upper_bound": self.upper_bound,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "NamedVariable":
        return cls(
            name=str(data["name"]),
            kind=str(data.get("kind", CONTINUOUS)),
            lower_bound=data.get("lower_bound"),
            upper_bound=data.get("upper_bound"),
        )

    def __str__(self) -> str:
        return (
            f"{self.name}: {self.kind} "
            f"[{_format_bound(self.lower_bound, lower=True)}, "
            f"{_format_bound(self.upper_bound, lower=False)}]"
        )


@dataclass
class LinearConstraintSpec:
    """A named linear equality or inequality."""

    name: str
    coefficients: dict[str, float]
    sense: ConstraintSense
    rhs: float

    def __post_init__(self) -> None:
        self.name = _require_name(self.name, "constraint")
        self.coefficients = _normalize_coefficients(self.coefficients)

        if self.sense not in {LE, GE, EQ}:
            raise ValueError(f"constraint sense must be one of {LE!r}, {GE!r}, {EQ!r}")

        self.rhs = float(self.rhs)
        if not math.isfinite(self.rhs):
            raise ValueError("constraint right-hand side must be finite")

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "coefficients": dict(self.coefficients),
            "sense": self.sense,
            "rhs": self.rhs,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "LinearConstraintSpec":
        return cls(
            name=str(data["name"]),
            coefficients=dict(data["coefficients"]),
            sense=str(data["sense"]),
            rhs=float(data["rhs"]),
        )

    def __str__(self) -> str:
        return (
            f"{self.name}: {_format_expression(self.coefficients)} "
            f"{self.sense} {_format_number(self.rhs)}"
        )


@dataclass
class LinearObjective:
    """A linear objective for a MILP problem."""

    coefficients: dict[str, float]
    sense: ObjectiveSense = MINIMIZE

    def __post_init__(self) -> None:
        self.coefficients = _normalize_coefficients(self.coefficients)

        if self.sense not in {MINIMIZE, MAXIMIZE}:
            raise ValueError(f"objective sense must be {MINIMIZE!r} or {MAXIMIZE!r}")

    def to_dict(self) -> dict[str, Any]:
        return {"coefficients": dict(self.coefficients), "sense": self.sense}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "LinearObjective":
        return cls(
            coefficients=dict(data["coefficients"]),
            sense=str(data.get("sense", MINIMIZE)),
        )

    def __str__(self) -> str:
        return f"{self.sense} {_format_expression(self.coefficients)}"


@dataclass
class MILPSolution:
    """Solution returned by MILPProblem.solve()."""

    problem_name: str
    status: int
    status_name: str
    success: bool
    message: str
    objective_sense: ObjectiveSense
    optimum: float | None
    values: dict[str, float | int] = field(default_factory=dict)

    def value(self, variable_name: str) -> float | int:
        return self.values[variable_name]

    def __getitem__(self, variable_name: str) -> float | int:
        return self.value(variable_name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "problem_name": self.problem_name,
            "status": self.status,
            "status_name": self.status_name,
            "success": self.success,
            "message": self.message,
            "objective_sense": self.objective_sense,
            "optimum": self.optimum,
            "values": dict(self.values),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MILPSolution":
        return cls(
            problem_name=str(data["problem_name"]),
            status=int(data["status"]),
            status_name=str(data["status_name"]),
            success=bool(data["success"]),
            message=str(data["message"]),
            objective_sense=str(data["objective_sense"]),
            optimum=data.get("optimum"),
            values=dict(data.get("values", {})),
        )

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    @classmethod
    def from_json(cls, text: str) -> "MILPSolution":
        return cls.from_dict(json.loads(text))

    def __str__(self) -> str:
        optimum = "unknown" if self.optimum is None else _format_number(self.optimum)
        lines = [
            f"MILPSolution({self.problem_name!r})",
            f"  status: {self.status_name} ({self.message})",
            f"  objective: {self.objective_sense}, optimum = {optimum}",
            "  values:",
        ]

        if self.values:
            for variable_name in sorted(self.values):
                value = self.values[variable_name]
                if isinstance(value, int):
                    formatted = str(value)
                else:
                    formatted = _format_number(value)
                lines.append(f"    {variable_name} = {formatted}")
        else:
            lines.append("    <none>")

        return "\n".join(lines)


@dataclass
class MILPProblem:
    """Mixed-integer linear program with named variables and constraints.

    The solver backend is scipy.optimize.milp, which delegates to the optimized
    HiGHS solver. Install the dependency with:

        python3 -m pip install scipy
    """

    name: str = "MILPProblem"
    variables: list[NamedVariable] = field(default_factory=list)
    constraints: list[LinearConstraintSpec] = field(default_factory=list)
    objective: LinearObjective | None = None

    def __post_init__(self) -> None:
        self.name = _require_name(self.name, "problem")

        seen_variables: set[str] = set()
        for index, variable in enumerate(self.variables):
            if not isinstance(variable, NamedVariable):
                variable = NamedVariable.from_dict(variable)  # type: ignore[arg-type]
                self.variables[index] = variable
            if variable.name in seen_variables:
                raise ValueError(f"duplicate variable name {variable.name!r}")
            seen_variables.add(variable.name)

        seen_constraints: set[str] = set()
        for index, constraint in enumerate(self.constraints):
            if not isinstance(constraint, LinearConstraintSpec):
                constraint = LinearConstraintSpec.from_dict(constraint)  # type: ignore[arg-type]
                self.constraints[index] = constraint
            if constraint.name in seen_constraints:
                raise ValueError(f"duplicate constraint name {constraint.name!r}")
            seen_constraints.add(constraint.name)

        if self.objective is not None and not isinstance(self.objective, LinearObjective):
            self.objective = LinearObjective.from_dict(self.objective)  # type: ignore[arg-type]

        self._validate_references()

    @property
    def variable_names(self) -> list[str]:
        return [variable.name for variable in self.variables]

    def _variable_index(self) -> dict[str, int]:
        return {variable.name: index for index, variable in enumerate(self.variables)}

    def _check_variable_references(self, coefficients: Mapping[str, float]) -> None:
        available = set(self.variable_names)
        missing = sorted(set(coefficients) - available)
        if missing:
            joined = ", ".join(repr(name) for name in missing)
            raise KeyError(f"unknown variable name(s): {joined}")

    def _validate_references(self) -> None:
        for constraint in self.constraints:
            self._check_variable_references(constraint.coefficients)
        if self.objective is not None:
            self._check_variable_references(self.objective.coefficients)

    def add_variable(
        self,
        name: str,
        *,
        kind: VariableKind = CONTINUOUS,
        lower_bound: float | None = None,
        upper_bound: float | None = None,
    ) -> NamedVariable:
        if name in self._variable_index():
            raise ValueError(f"duplicate variable name {name!r}")

        variable = NamedVariable(
            name=name,
            kind=kind,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
        )
        self.variables.append(variable)
        return variable

    def add_continuous_variable(
        self,
        name: str,
        *,
        lower_bound: float | None = None,
        upper_bound: float | None = None,
    ) -> NamedVariable:
        return self.add_variable(
            name,
            kind=CONTINUOUS,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
        )

    def add_integer_variable(
        self,
        name: str,
        *,
        lower_bound: float | None = None,
        upper_bound: float | None = None,
    ) -> NamedVariable:
        return self.add_variable(
            name,
            kind=INTEGER,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
        )

    def add_constraint(
        self,
        name: str,
        coefficients: Mapping[str, float],
        sense: ConstraintSense,
        rhs: float,
    ) -> LinearConstraintSpec:
        if name in {constraint.name for constraint in self.constraints}:
            raise ValueError(f"duplicate constraint name {name!r}")

        constraint = LinearConstraintSpec(
            name=name,
            coefficients=dict(coefficients),
            sense=sense,
            rhs=rhs,
        )
        self._check_variable_references(constraint.coefficients)
        self.constraints.append(constraint)
        return constraint

    def add_equality(
        self,
        name: str,
        coefficients: Mapping[str, float],
        rhs: float,
    ) -> LinearConstraintSpec:
        return self.add_constraint(name, coefficients, EQ, rhs)

    def add_inequality(
        self,
        name: str,
        coefficients: Mapping[str, float],
        sense: ConstraintSense,
        rhs: float,
    ) -> LinearConstraintSpec:
        if sense not in {LE, GE}:
            raise ValueError(f"inequality sense must be {LE!r} or {GE!r}")
        return self.add_constraint(name, coefficients, sense, rhs)

    def add_less_equal(
        self,
        name: str,
        coefficients: Mapping[str, float],
        rhs: float,
    ) -> LinearConstraintSpec:
        return self.add_constraint(name, coefficients, LE, rhs)

    def add_greater_equal(
        self,
        name: str,
        coefficients: Mapping[str, float],
        rhs: float,
    ) -> LinearConstraintSpec:
        return self.add_constraint(name, coefficients, GE, rhs)

    def set_objective(
        self,
        coefficients: Mapping[str, float],
        *,
        sense: ObjectiveSense = MINIMIZE,
    ) -> LinearObjective:
        objective = LinearObjective(coefficients=dict(coefficients), sense=sense)
        self._check_variable_references(objective.coefficients)
        self.objective = objective
        return objective

    def set_objective_variable(
        self,
        variable_name: str,
        *,
        sense: ObjectiveSense = MINIMIZE,
    ) -> LinearObjective:
        self._check_variable_references({variable_name: 1.0})
        return self.set_objective({variable_name: 1.0}, sense=sense)

    def solve(self, *, options: Mapping[str, Any] | None = None) -> MILPSolution:
        if not self.variables:
            raise ValueError("cannot solve a MILP with no variables")
        if self.objective is None:
            raise ValueError("cannot solve a MILP without an objective")

        variable_index = self._variable_index()
        variable_count = len(self.variables)

        c = np.zeros(variable_count)
        for variable_name, coefficient in self.objective.coefficients.items():
            c[variable_index[variable_name]] = coefficient
        if self.objective.sense == MAXIMIZE:
            c = -c

        lower_bounds = np.array(
            [
                -np.inf if variable.lower_bound is None else variable.lower_bound
                for variable in self.variables
            ],
            dtype=float,
        )
        upper_bounds = np.array(
            [
                np.inf if variable.upper_bound is None else variable.upper_bound
                for variable in self.variables
            ],
            dtype=float,
        )
        integrality = np.array(
            [1 if variable.kind == INTEGER else 0 for variable in self.variables],
            dtype=int,
        )

        solver_constraints = None
        if self.constraints:
            lhs = np.zeros((len(self.constraints), variable_count), dtype=float)
            constraint_lower = np.full(len(self.constraints), -np.inf, dtype=float)
            constraint_upper = np.full(len(self.constraints), np.inf, dtype=float)

            for row, constraint in enumerate(self.constraints):
                for variable_name, coefficient in constraint.coefficients.items():
                    lhs[row, variable_index[variable_name]] = coefficient

                if constraint.sense == EQ:
                    constraint_lower[row] = constraint.rhs
                    constraint_upper[row] = constraint.rhs
                elif constraint.sense == LE:
                    constraint_upper[row] = constraint.rhs
                elif constraint.sense == GE:
                    constraint_lower[row] = constraint.rhs
                else:
                    raise ValueError(f"unknown constraint sense {constraint.sense!r}")

            solver_constraints = LinearConstraint(
                lhs,
                lb=constraint_lower,
                ub=constraint_upper,
            )

        kwargs: dict[str, Any] = {
            "c": c,
            "integrality": integrality,
            "bounds": Bounds(lower_bounds, upper_bounds),
            "options": dict(options or {}),
        }
        if solver_constraints is not None:
            kwargs["constraints"] = solver_constraints

        result = milp(**kwargs)

        values: dict[str, float | int] = {}
        if result.x is not None:
            for variable, value in zip(self.variables, result.x):
                value = float(value)
                if variable.kind == INTEGER and math.isclose(value, round(value), abs_tol=1e-8):
                    values[variable.name] = int(round(value))
                else:
                    values[variable.name] = value

        optimum = None
        if result.fun is not None:
            optimum = float(result.fun)
            if self.objective.sense == MAXIMIZE:
                optimum = -optimum

        status_name = {
            0: "optimal",
            1: "limit_reached",
            2: "infeasible",
            3: "unbounded",
            4: "solver_error",
        }.get(int(result.status), "unknown")

        return MILPSolution(
            problem_name=self.name,
            status=int(result.status),
            status_name=status_name,
            success=bool(result.success),
            message=str(result.message),
            objective_sense=self.objective.sense,
            optimum=optimum,
            values=values,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "variables": [variable.to_dict() for variable in self.variables],
            "constraints": [constraint.to_dict() for constraint in self.constraints],
            "objective": None if self.objective is None else self.objective.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MILPProblem":
        return cls(
            name=str(data.get("name", "MILPProblem")),
            variables=[
                NamedVariable.from_dict(variable)
                for variable in data.get("variables", [])
            ],
            constraints=[
                LinearConstraintSpec.from_dict(constraint)
                for constraint in data.get("constraints", [])
            ],
            objective=(
                None
                if data.get("objective") is None
                else LinearObjective.from_dict(data["objective"])
            ),
        )

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    @classmethod
    def from_json(cls, text: str) -> "MILPProblem":
        return cls.from_dict(json.loads(text))

    def __str__(self) -> str:
        lines = [f"MILPProblem({self.name!r})"]

        if self.objective is None:
            lines.append("  objective: <unset>")
        else:
            lines.append(f"  objective: {self.objective}")

        lines.append("  variables:")
        if self.variables:
            for variable in self.variables:
                lines.append(f"    {variable}")
        else:
            lines.append("    <none>")

        lines.append("  constraints:")
        if self.constraints:
            for constraint in self.constraints:
                lines.append(f"    {constraint}")
        else:
            lines.append("    <none>")

        return "\n".join(lines)
