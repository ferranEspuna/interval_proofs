"""Numerical and CLI regressions for arbitrary integer linear forms.

Run with: python -m unittest test_linear_form_intervals.py
"""

from __future__ import annotations

import base64
from itertools import product
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit

from circle_intervals import build_circle_interval_problem
from linear_form_intervals import (
    build_linear_form_interval_problem,
    interval_tuples,
    linear_form_visualizer_state,
)
from milp_problem import MILPProblem, MILPSolution


SCRIPT = Path(__file__).with_name("linear_form_intervals.py")


class LinearFormIntervalTests(unittest.TestCase):
    def solve(self, N, coefficients, epsilon=0.0, **options):
        problem = build_linear_form_interval_problem(N, coefficients, epsilon, **options)
        solution = problem.solve(options={"mip_rel_gap": 0})
        self.assertTrue(solution.success, solution.message)
        self.assertIsNotNone(solution.optimum)
        return solution

    def test_single_interval_known_densities(self):
        # If sum(c) != 0, the single-interval optimum is (1-2*eps)/sum(abs(c)).
        for coefficients in ([1], [-3], [2, 3], [1, 1, -3], [2, -1, 3, -2, 4]):
            for epsilon in (0.0, 0.01):
                with self.subTest(coefficients=coefficients, epsilon=epsilon):
                    solution = self.solve(1, coefficients, epsilon)
                    expected = (1 - 2 * epsilon) / sum(map(abs, coefficients))
                    self.assertAlmostEqual(solution.optimum, expected, places=7)

    def test_matches_existing_three_term_solver(self):
        for N in (1, 2, 3):
            for translated in (False, True):
                with self.subTest(N=N, translated=translated):
                    options = {"use_translated_missing_point": translated}
                    old = build_circle_interval_problem(N, m=3, **options).solve(
                        options={"mip_rel_gap": 0}
                    )
                    self.assertTrue(old.success, old.message)
                    new = self.solve(N, [1, 1, -3], **options)
                    self.assertAlmostEqual(new.optimum, old.optimum, places=7)

    def test_zero_coefficients_do_not_change_the_form(self):
        original = self.solve(2, [1, 1, -3])
        padded = self.solve(2, [0, 1, 0, 1, -3, 0])
        self.assertAlmostEqual(padded.optimum, original.optimum, places=7)
        self.assertEqual(padded.parameters["coefficients"], [0, 1, 0, 1, -3, 0])
        self.assertEqual(padded.parameters["active_coefficients"], [1, 1, -3])
        self.assertEqual(padded.parameters["lifted_tuple_count"], 6)

    def test_zero_sum_fixed_and_translated_modes_differ(self):
        fixed = self.solve(2, [1, -1])
        self.assertAlmostEqual(fixed.optimum, 0.0, places=7)
        strict = build_linear_form_interval_problem(2, [1, -1], 0.01).solve()
        self.assertEqual(strict.status_name, "infeasible")
        translated = self.solve(1, [1, -1], 0.01, use_translated_missing_point=True)
        self.assertAlmostEqual(translated.optimum, 0.49, places=7)
        state = linear_form_visualizer_state(
            translated, N=1, coefficients=[1, -1], translated_missing_point=True,
        )
        self.assertEqual(state["coefficients"], [1, -1])
        self.assertAlmostEqual(state["missingPoint"], translated["t"], places=10)
        self.assertAlmostEqual(state["intervals"][0]["start"], 0.0, places=10)

    def test_zero_form(self):
        self.assertAlmostEqual(self.solve(2, [0, 0]).optimum, 0.0, places=7)
        strict = build_linear_form_interval_problem(1, [0], 0.01).solve()
        self.assertEqual(strict.status_name, "infeasible")
        translated = self.solve(2, [0, 0], 0.01, use_translated_missing_point=True)
        self.assertAlmostEqual(translated.optimum, 1.0, places=7)

    def test_all_ordered_assignments_obey_endpoint_containment(self):
        # Check independently over the full Cartesian product, including tuples
        # omitted by the equal-coefficient symmetry reduction and zero slots.
        coefficients = [2, -1, 2, 0, -2]
        epsilon = 0.01
        for translated in (False, True):
            with self.subTest(translated=translated):
                solution = self.solve(
                    2, coefficients, epsilon,
                    use_translated_missing_point=translated,
                )
                missing = solution["t"] if translated else 0
                for indices in product(range(2), repeat=len(coefficients)):
                    endpoints = [
                        (c * solution[f"x_{i}"], c * (solution[f"x_{i}"] + solution[f"alpha_{i}"]))
                        for c, i in zip(coefficients, indices)
                    ]
                    left = sum(min(pair) for pair in endpoints)
                    right = sum(max(pair) for pair in endpoints)
                    smallest_lift = math.ceil(right - missing - 1 + epsilon - 1e-7)
                    largest_lift = math.floor(left - missing - epsilon + 1e-7)
                    self.assertLessEqual(smallest_lift, largest_lift, (indices, left, right))

    def test_repeated_coefficient_enumeration(self):
        tuples = list(interval_tuples(3, (2, -1, 2, -1)))
        self.assertEqual(len(tuples), 36)
        self.assertEqual(len(set(tuples)), 36)
        self.assertTrue(all(i <= k and j <= l for i, j, k, l in tuples))
        self.assertEqual(list(interval_tuples(3, ())), [()])

    def test_optional_cuts_preserve_optimum(self):
        coefficients = [2, -1, 2, -2]
        expected = self.solve(
            2, coefficients, add_width_cuts=False,
            add_monotonicity_cuts=False, add_endpoint_length_cut=False,
        ).optimum
        for width, monotonic in product((False, True), repeat=2):
            with self.subTest(width=width, monotonic=monotonic):
                solution = self.solve(
                    2, coefficients, add_width_cuts=width,
                    add_monotonicity_cuts=monotonic,
                )
                self.assertAlmostEqual(solution.optimum, expected, places=7)

    def test_invalid_input(self):
        cases = [
            (0, [1], 0.0, {}), (1.5, [1], 0.0, {}), (True, [1], 0.0, {}),
            (1, [], 0.0, {}), (1, [1.5], 0.0, {}), (1, [True], 0.0, {}),
            (1, [1], -0.01, {}), (1, [1], 0.6, {}),
            (1, [1], math.nan, {}), (1, [1], math.inf, {}),
            (2, [1], 0.0, {"add_first_interval_shortest_cut": True}),
            (2, [1], 0.0, {"subset_alpha_bounds": [(1.5, 0.2)]}),
            (2, [1], 0.0, {"subset_alpha_bounds": [(1, math.nan)]}),
            (2, [1], 0.0, {"total_length_lower_bound": -1}),
        ]
        for N, coefficients, epsilon, options in cases:
            with self.subTest(N=N, coefficients=coefficients, epsilon=epsilon, options=options):
                with self.assertRaises(ValueError):
                    build_linear_form_interval_problem(N, coefficients, epsilon, **options)


class LinearFormCLITests(unittest.TestCase):
    def run_cli(self, directory, *arguments):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *map(str, arguments)],
            cwd=directory, capture_output=True, text=True, timeout=60,
        )

    def test_save_and_visualizer_link(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "results"
            result = self.run_cli(
                directory, "-N", 1, "--coefficients", 1, 1, -3,
                "--translated-missing-point", "--mip-rel-gap", 0,
                "--output-dir", output, "--run-name", "smoke", "--require-success",
                "--visualizer-url", "https://example.test/view?theme=dark#plot",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            problem = MILPProblem.from_json((output / "smoke_problem.json").read_text())
            solution = MILPSolution.from_json((output / "smoke_solution.json").read_text())
            self.assertEqual(problem.metadata["coefficients"], [1, 1, -3])
            self.assertTrue(solution.success)
            self.assertAlmostEqual(solution.optimum, 0.2, places=7)
            url = solution.parameters["visualizer_url"]
            self.assertIn(url, result.stdout)
            parsed = urlsplit(url)
            self.assertEqual(parsed.fragment, "plot")
            query = parse_qs(parsed.query)
            self.assertEqual(query["theme"], ["dark"])
            encoded = query["state"][0]
            state = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
            self.assertEqual(state["mode"], "linear-form")
            self.assertEqual(state["coefficients"], [1, 1, -3])
            self.assertAlmostEqual(state["missingPoint"], solution["t"], places=10)
            self.assertEqual(state, solution.parameters["visualizer_state"])

    def test_infeasible_result_saved_before_require_success_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "results"
            result = self.run_cli(
                directory, "-N", 1, "--coefficients", 1, -1, "--epsilon", 0.01,
                "--output-dir", output, "--run-name", "infeasible", "--require-success",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue((output / "infeasible_problem.json").exists())
            solution = MILPSolution.from_json((output / "infeasible_solution.json").read_text())
            self.assertEqual(solution.status_name, "infeasible")
            self.assertNotIn("visualizer_url", solution.parameters)
            self.assertNotIn("Visualizer state URL:", result.stdout)

    def test_no_save_still_prints_link(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_cli(directory, "-N", 1, "-c", 1, "--no-save", "--require-success")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Visualizer state URL:", result.stdout)
            self.assertEqual(list(Path(directory).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
