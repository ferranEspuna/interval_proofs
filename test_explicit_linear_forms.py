"""Exact images, witnesses and grouped-preimage construction regressions."""

import base64
from fractions import Fraction as F
from itertools import product
import json
import unittest
from urllib.parse import parse_qs, urlsplit

from explicit_construction import (
    CircleOpenInterval as I,
    CircleOpenIntervalUnion as U,
    CirclePointSet,
    apply_linear_form,
    dilate_interval_union,
    minkowski_sum,
    optimal_preimage_widths,
    optimized_preimage_construction,
    preimage_construction,
    preimage_under_repeated_addition,
    ruzsa_optimized_construction,
    torus_preimage_partition,
)


class LinearFormImageTests(unittest.TestCase):
    def test_dilation_is_not_repeated_independent_addition(self):
        A = U([I(F(0), F(1, 10)), I(F(3, 10), F(2, 5))])
        dilation = A.apply_linear_form([2])
        repeated_sum = apply_linear_form(A, [1, 1])
        self.assertFalse(dilation.containsPoint(F(2, 5)))
        self.assertTrue(repeated_sum.containsPoint(F(2, 5)))
        self.assertEqual(dilation.length, F(2, 5))
        self.assertEqual(repeated_sum.length, F(3, 5))

    def test_signed_dilation_and_wrapping(self):
        result = dilate_interval_union(I(F(3, 4), F(5, 4)), -1)
        self.assertTrue(result.containsPoint(0))
        self.assertFalse(result.containsPoint(F(1, 4)))
        self.assertFalse(result.containsPoint(F(3, 4)))
        self.assertEqual(result.length, F(1, 2))
        self.assertTrue(dilate_interval_union(I(0, 1), -2).is_full)

    def test_unit_width_image_is_punctured_but_longer_image_is_full(self):
        punctured = apply_linear_form(I(F(0), F(1, 2)), [1, 1])
        self.assertEqual(punctured.length, 1)
        self.assertFalse(punctured.is_full)
        self.assertEqual(punctured.missing_point(), 0)
        self.assertFalse(punctured.containsPoint(0))
        full = apply_linear_form(I(F(0), F(3, 5)), [1, 1])
        self.assertTrue(full.is_full)
        self.assertIsNone(full.missing_point())

    def test_zero_form_is_a_singleton_only_when_domain_is_nonempty(self):
        point = apply_linear_form(I(F(1, 4), F(1, 2)), [0, 0])
        self.assertIsInstance(point, CirclePointSet)
        self.assertEqual(point.length, 0)
        self.assertTrue(point.containsPoint(0))
        self.assertFalse(point.containsPoint(point.missing_point()))
        empty = apply_linear_form(U([]), [0, 0])
        self.assertFalse(empty.containsPoint(0))
        self.assertEqual(empty.missing_point(), 0)
        mixed = apply_linear_form(I(F(1, 4), F(1, 2)), [0, -1, 0])
        self.assertEqual(mixed.intervals, [I(F(1, 2), F(3, 4))])

    def test_missing_point_handles_gaps_isolated_holes_and_empty_sets(self):
        cases = [
            U([]),
            U([I(F(3, 4), F(5, 4))]),
            U([I(0, F(1, 2)), I(F(1, 2), 1)]),
            U([I(F(1, 3), F(4, 3))]),
        ]
        for value in cases:
            with self.subTest(intervals=value.intervals):
                point = value.missing_point()
                self.assertIsInstance(point, F)
                self.assertFalse(value.containsPoint(point))
        self.assertIsNone(U.full_circle().missing_point())

    def test_empty_sum_and_full_sum(self):
        A = I(F(1, 4), F(1, 2))
        self.assertEqual(minkowski_sum(A, U([])).length, 0)
        self.assertTrue(minkowski_sum(A, U.full_circle()).is_full)
        self.assertTrue(minkowski_sum(U.full_circle(), A).is_full)
        self.assertEqual(apply_linear_form(U([]), [1, -3]).length, 0)

    def test_image_matches_exhaustive_interval_tuple_endpoints(self):
        A = U([I(F(1, 20), F(1, 10)), I(F(3, 10), F(7, 20)), I(F(9, 10), F(21, 20))])
        for coefficients in ([1], [-3], [1, 1, -2], [2, -3, 0, 1], [-1, -1], [0, 2]):
            expected_intervals = []
            full = False
            active = [c for c in coefficients if c]
            for selected in product(A.intervals, repeat=len(active)):
                lower = sum(min(c * arc.start, c * arc.end) for c, arc in zip(active, selected))
                upper = sum(max(c * arc.start, c * arc.end) for c, arc in zip(active, selected))
                if upper - lower > 1:
                    full = True
                    break
                expected_intervals.append(I(lower, upper))
            expected = U.full_circle() if full else U(expected_intervals)
            actual = apply_linear_form(A, coefficients)
            with self.subTest(coefficients=coefficients):
                self.assertEqual(actual.length, expected.length)
                self.assertEqual(actual.is_full, expected.is_full)
                points = {F(k, 120) for k in range(120)}
                points.update(arc.start for arc in expected.intervals)
                points.update(arc.end % 1 for arc in expected.intervals)
                for point in points:
                    self.assertEqual(actual.containsPoint(point), expected.containsPoint(point))
                witness = actual.missing_point()
                if witness is not None:
                    self.assertFalse(actual.containsPoint(witness))

    def test_coefficient_and_preimage_validation(self):
        A = I(0, F(1, 4))
        for coefficients in ([], [True], [1.5], ["2"]):
            with self.subTest(coefficients=coefficients):
                with self.assertRaises(ValueError):
                    apply_linear_form(A, coefficients)
        for n in (0, -1, 1.5, True):
            with self.assertRaises(ValueError):
                preimage_under_repeated_addition(A, n)
        with self.assertRaises(ValueError):
            list(torus_preimage_partition(0, 2))


class PreimageConstructionTests(unittest.TestCase):
    def test_grouped_widths_count_both_signs_and_ignore_zero(self):
        self.assertEqual(optimal_preimage_widths([10, 10, -19]), {10: F(1, 4), 19: F(1, 2)})
        self.assertEqual(optimal_preimage_widths([2, -2, 2, 0]), {2: F(1, 3)})
        self.assertEqual(optimal_preimage_widths([0, 0]), {})

    def test_custom_wrapping_targets_and_negative_terms(self):
        targets = {2: I(F(7, 8), F(9, 8)), 3: I(F(3, 4), F(5, 4))}
        result = preimage_construction([2, -2, -3], targets)
        self.assertEqual(result.bounding_width, 1)
        self.assertEqual(result.guaranteed_density, F(1, 8))
        self.assertFalse(result.image.containsPoint(result.bounding_start))
        self.assertFalse(result.image.containsPoint(result.missing_point))
        for k in range(96):
            point = F(k, 96)
            expected = all(target.containsPoint(d * point) for d, target in targets.items())
            self.assertEqual(result.A.containsPoint(point), expected)

    def test_pigeonhole_guarantee_and_exact_witness(self):
        for coefficients in ([1], [1, -1], [1, 1, -3], [10, 10, -19], [2, -3, 1, 4], [0, 0], [0, 2, -3]):
            with self.subTest(coefficients=coefficients):
                result = optimized_preimage_construction(coefficients)
                self.assertGreaterEqual(result.A.length, result.guaranteed_density)
                self.assertIsNotNone(result.missing_point)
                self.assertFalse(result.image.containsPoint(result.missing_point))
                self.assertEqual(ruzsa_optimized_construction(coefficients).length, result.A.length)

    def test_sweep_finds_same_best_density_as_cartesian_search(self):
        coefficients = [1, 1, -3, 2]
        widths = optimal_preimage_widths(coefficients)
        best = F(0)
        for indices in product(*(range(width.denominator) for width in widths.values())):
            targets = {d: I(F(k, width.denominator), F(k + 1, width.denominator))
                       for (d, width), k in zip(widths.items(), indices)}
            best = max(best, preimage_construction(coefficients, targets).A.length)
        self.assertEqual(optimized_preimage_construction(coefficients).A.length, best)

    def test_wide_targets_may_cover_circle_without_false_witness(self):
        result = preimage_construction([1, 1], {1: I(0, F(3, 4))})
        self.assertTrue(result.image.is_full)
        self.assertIsNone(result.missing_point)
        self.assertIsNone(result.guaranteed_density)

    def test_all_zero_construction_has_full_A_and_singleton_image(self):
        result = optimized_preimage_construction([0, 0])
        self.assertTrue(result.A.is_full)
        self.assertEqual(result.targets, ())
        self.assertEqual(result.guaranteed_density, 1)
        self.assertTrue(result.image.containsPoint(0))
        self.assertFalse(result.image.containsPoint(result.missing_point))

    def test_invalid_target_keys_and_partition_budget(self):
        with self.assertRaises(ValueError):
            preimage_construction([2, -3], {2: I(0, F(1, 4))})
        with self.assertRaises(ValueError):
            optimized_preimage_construction([1000, 1001], max_partition_cells=10)

    def test_construction_url_retains_editable_targets(self):
        result = optimized_preimage_construction([10, 10, -19])
        url = result.visualize(base_url="https://example.test/?keep=yes#circle")
        parts = urlsplit(url)
        query = parse_qs(parts.query)
        encoded = query["state"][0]
        state = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        self.assertEqual(state["mode"], "preimage-construction")
        self.assertEqual(state["coefficients"], [10, 10, -19])
        self.assertEqual(query["keep"], ["yes"])
        self.assertEqual(parts.fragment, "circle")
        self.assertEqual([t["coefficient"] for t in state["targets"]], [10, 19])
        self.assertEqual([t["width"] for t in state["targets"]], [0.25, 0.5])


if __name__ == "__main__":
    unittest.main()
