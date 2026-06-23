from collections import defaultdict
from milp_problem import MILPProblem


def build_circle_interval_problem(N: int, d: float, epsilon: float = 0.0) -> MILPProblem:
    problem = MILPProblem(f"{d}-sum-free set problem for {N} intervals")
    assert N >= 1
    assert d > 0
    assert epsilon >= 0

    for i in range(N):
        problem.add_continuous_variable(f"x_{i}", lower_bound=0, upper_bound=1)
        problem.add_continuous_variable(f"alpha_{i}", lower_bound=0, upper_bound=1)

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

    # Sum-free condition: the interval I_i + I_j - d*I_k must not contain 0.
    # Unwrapping modulo 1, such an interval must be contained in
    # (n_ijk, n_ijk + 1), where n_ijk is an integer. With epsilon=0 this is
    # the closed relaxation n_ijk <= left and right <= n_ijk + 1.
    for i in range(N):
        for j in range(i, N):
            for k in range(N):
                # The leftmost point of I_i + I_j - d*I_k is
                # x_i + x_j - d*x_k - d*alpha_k >= n_ijk + epsilon.
                problem.add_integer_variable(f"n_{i}-{j}-{k}", lower_bound=int(-d) - 1, upper_bound=3)
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
    problem.add_continuous_variable("total_length", lower_bound=0, upper_bound=1)
    problem.add_equality("total_length_definition", {"total_length": 1, ** {f"alpha_{i}": -1 for i in range(N)}}, 0)
    problem.set_objective_variable("total_length", sense="maximize")

    return problem


def main() -> None:
    problem = build_circle_interval_problem(N=7, d=3, epsilon=1e-10)
    print(problem)
    print()

    solution = problem.solve()

    print(solution)
    print()

    assert solution.success, solution.message

if __name__ == "__main__":
    main()
