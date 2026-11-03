"""Exact set-operation regressions for circular open intervals.

Run with ``python -m unittest test_explicit_construction.py``.
"""

from fractions import Fraction as F
from itertools import combinations_with_replacement, permutations, product
import operator
import unittest

from explicit_construction import CircleOpenInterval as Interval
from explicit_construction import CircleOpenIntervalUnion as Union


class CircleOpenIntervalTests(unittest.TestCase):
    def test_normalization_preserves_lifted_length(self):
        interval = Interval(F(-1, 4), F(1, 4))
        self.assertEqual(interval.start, F(3, 4))
        self.assertEqual(interval.end, F(5, 4))
        self.assertEqual(interval.length, F(1, 2))
        for point in (F(0), F(1), F(-1), F(7, 8)):
            self.assertTrue(interval.containsPoint(point))
        for point in (F(-1, 4), F(1, 4), F(1, 2)):
            self.assertFalse(interval.containsPoint(point))

    def test_invalid_lengths_are_rejected(self):
        for start, end in ((F(1), F(0)), (F(0), F(5, 4))):
            with self.subTest(start=start, end=end):
                with self.assertRaises(ValueError):
                    Interval(start, end)

    def test_empty_and_punctured_circle_are_distinct(self):
        empty = Interval(F(1, 3), F(1, 3))
        punctured = Interval(F(1, 3), F(4, 3))
        self.assertEqual(empty.length, 0)
        self.assertEqual(punctured.length, 1)
        self.assertFalse(empty.containsPoint(F(1, 2)))
        self.assertFalse(punctured.containsPoint(F(1, 3)))
        self.assertTrue(punctured.containsPoint(F(0)))

    def test_interval_contains_itself_and_shared_boundary_subintervals(self):
        interval = Interval(F(1, 4), F(3, 4))
        self.assertTrue(interval.containsInterval(interval))
        self.assertTrue(interval.containsInterval(Interval(F(1, 4), F(1, 2))))
        self.assertTrue(interval.containsInterval(Interval(F(1, 2), F(3, 4))))
        self.assertFalse(interval.containsInterval(Interval(F(1, 2), F(1))))

    def test_empty_interval_is_contained_everywhere(self):
        empty = Interval(F(1, 2), F(1, 2))
        self.assertTrue(Interval(F(0), F(1, 4)).containsInterval(empty))
        self.assertTrue(empty.containsInterval(empty))
        self.assertTrue(Union([]).containsInterval(empty))
        self.assertFalse(empty.containsInterval(Interval(F(0), F(1, 4))))

    def test_wrapping_containment(self):
        interval = Interval(F(3, 4), F(5, 4))
        self.assertTrue(interval.containsInterval(Interval(F(0), F(1, 4))))
        self.assertTrue(interval.containsInterval(Interval(F(7, 8), F(9, 8))))
        self.assertFalse(interval.containsInterval(Interval(F(0), F(1, 2))))

    def test_intersection_with_itself_preserves_interval(self):
        interval = Interval(F(1, 4), F(3, 4))
        result = interval & interval
        self.assertEqual(result.length, interval.length)
        self.assertTrue(result.containsPoint(F(1, 2)))
        self.assertFalse(result.containsPoint(F(1, 4)))
        self.assertFalse(result.containsPoint(F(3, 4)))

    def test_intersection_with_shared_start_preserves_shorter_interval(self):
        result = Interval(F(0), F(1, 4)) & Interval(F(0), F(3, 4))
        self.assertEqual(result.length, F(1, 4))
        self.assertTrue(result.containsPoint(F(1, 8)))

    def test_wrapping_intersection_uses_compatible_lifts(self):
        result = Interval(F(3, 4), F(5, 4)) & Interval(F(1, 8), F(7, 8))
        self.assertEqual(result.length, F(1, 4))
        self.assertEqual(len(result.intervals), 2)
        self.assertTrue(result.containsPoint(F(3, 16)))
        self.assertTrue(result.containsPoint(F(13, 16)))
        self.assertFalse(result.containsPoint(F(0)))

    def test_touching_intersection_is_empty(self):
        result = Interval(F(0), F(1, 2)) & Interval(F(1, 2), F(1))
        self.assertEqual(result.length, 0)
        self.assertFalse(result.containsPoint(F(1, 2)))


class CircleOpenIntervalUnionTests(unittest.TestCase):
    def test_duplicate_intervals_are_counted_once(self):
        interval = Interval(F(0), F(1, 2))
        result = interval | interval
        self.assertEqual(result.length, F(1, 2))
        self.assertEqual(len(result.intervals), 1)

    def test_overlapping_intervals_merge(self):
        result = Interval(F(0), F(1, 2)) | Interval(F(1, 4), F(3, 4))
        self.assertEqual(result.length, F(3, 4))
        self.assertEqual(len(result.intervals), 1)
        self.assertTrue(result.containsPoint(F(1, 2)))
        self.assertFalse(result.containsPoint(F(0)))
        self.assertFalse(result.containsPoint(F(3, 4)))

    def test_touching_open_intervals_keep_the_missing_point(self):
        result = Interval(F(0), F(1, 2)) | Interval(F(1, 2), F(1))
        self.assertEqual(result.length, 1)
        self.assertEqual(len(result.intervals), 2)
        self.assertFalse(result.containsPoint(F(0)))
        self.assertFalse(result.containsPoint(F(1, 2)))
        self.assertFalse(result.containsInterval(Interval(F(1, 4), F(3, 4))))

    def test_wrapping_union_preserves_origin_as_interior(self):
        result = Interval(F(3, 4), F(9, 8)) | Interval(F(0), F(1, 4))
        self.assertEqual(result.length, F(1, 2))
        self.assertTrue(result.containsPoint(F(0)))
        self.assertTrue(result.containsInterval(Interval(F(7, 8), F(9, 8))))
        self.assertFalse(result.containsPoint(F(1, 4)))

    def test_bridge_merging_is_independent_of_insertion_order(self):
        intervals = [
            Interval(F(0), F(1, 4)),
            Interval(F(1, 2), F(3, 4)),
            Interval(F(1, 8), F(5, 8)),
        ]
        for order in permutations(intervals):
            with self.subTest(order=order):
                result = Union(list(order))
                self.assertEqual(result.length, F(3, 4))
                self.assertEqual(len(result.intervals), 1)
                self.assertTrue(result.containsInterval(Interval(F(0), F(3, 4))))

    def test_full_circle_union_preserves_all_points(self):
        result = Interval(F(0), F(3, 4)) | Interval(F(1, 2), F(5, 4))
        self.assertEqual(result.length, 1)
        for i in range(16):
            self.assertTrue(result.containsPoint(F(i, 16)))
        self.assertTrue(result.containsInterval(Interval(F(0), F(1))))
        self.assertTrue(result.containsInterval(Interval(F(3, 4), F(7, 4))))

    def test_two_distinct_punctured_circles_have_full_union(self):
        result = Interval(F(0), F(1)) | Interval(F(1, 2), F(3, 2))
        self.assertEqual(result.length, 1)
        self.assertTrue(result.containsPoint(F(0)))
        self.assertTrue(result.containsPoint(F(1, 2)))

    def test_full_circle_intersection_returns_other_set(self):
        full = Interval(F(0), F(3, 4)) | Interval(F(1, 2), F(5, 4))
        other = Interval(F(3, 4), F(5, 4))
        for result in (full & other, other & full):
            self.assertEqual(result.length, F(1, 2))
            self.assertTrue(result.containsPoint(F(0)))
            self.assertFalse(result.containsPoint(F(3, 4)))

    def test_interval_and_union_operators_work_in_both_orders(self):
        interval = Interval(F(1, 8), F(5, 8))
        union = Union([Interval(F(0), F(1, 4)), Interval(F(1, 2), F(3, 4))])
        for result in (interval | union, union | interval):
            self.assertEqual(result.length, F(3, 4))
        for result in (interval & union, union & interval):
            self.assertEqual(result.length, F(1, 4))
            self.assertTrue(result.containsPoint(F(3, 16)))
            self.assertTrue(result.containsPoint(F(9, 16)))
            self.assertFalse(result.containsPoint(F(3, 8)))

    def test_union_intersection_and_empty_identities(self):
        left = Union([Interval(F(0), F(1, 4)), Interval(F(1, 2), F(3, 4))])
        right = Union([Interval(F(1, 8), F(5, 8))])
        result = left & right
        self.assertEqual(result.length, F(1, 4))
        self.assertEqual((left & Union([])).length, 0)
        self.assertEqual((Union([]) & left).length, 0)
        self.assertEqual((left | Union([])).length, F(1, 2))
        self.assertEqual((Union([]) | left).length, F(1, 2))

    def test_unsupported_operands_raise_type_error(self):
        interval = Interval(F(0), F(1, 2))
        for operand, operation in product((interval, Union([interval])), (operator.and_, operator.or_)):
            with self.subTest(operand=operand, operation=operation):
                with self.assertRaises(TypeError):
                    operation(operand, object())
                with self.assertRaises(TypeError):
                    operation(object(), operand)


class ExactGridSetOperationTests(unittest.TestCase):
    def test_all_pairs_on_small_rational_grid(self):
        # Every boundary is a multiple of 1/5, so testing all boundaries
        # and intervening midpoints determines these sets exactly.
        denominator = 5
        intervals = [
            Interval(F(start, denominator), F(start + length, denominator))
            for start in range(denominator)
            for length in range(denominator + 1)
        ]
        points = [F(i, 2 * denominator) for i in range(2 * denominator)]
        for left, right in product(intervals, repeat=2):
            with self.subTest(left=left, right=right):
                left_members = [0 < (point - left.start) % 1 < left.length for point in points]
                right_members = [0 < (point - right.start) % 1 < right.length for point in points]
                expected_union = [a or b for a, b in zip(left_members, right_members)]
                expected_intersection = [a and b for a, b in zip(left_members, right_members)]
                self.assertEqual(
                    left.containsInterval(right),
                    all(a or not b for a, b in zip(left_members, right_members)),
                )
                for result, expected in (
                    (left | right, expected_union),
                    (left & right, expected_intersection),
                ):
                    self.assertEqual([result.containsPoint(point) for point in points], expected)
                    self.assertEqual(result.length, F(sum(expected[1::2]), denominator))
                    self.assertTrue(result.containsInterval(Interval(F(0), F(0))))

    def test_three_interval_unions_are_independent_of_order(self):
        denominator = 3
        intervals = [
            Interval(F(start, denominator), F(start + length, denominator))
            for start in range(denominator)
            for length in range(denominator + 1)
        ]
        points = [F(i, 2 * denominator) for i in range(2 * denominator)]
        for indices in combinations_with_replacement(range(len(intervals)), 3):
            expected = [
                any(0 < (point - intervals[i].start) % 1 < intervals[i].length for i in indices)
                for point in points
            ]
            for order in set(permutations(indices)):
                with self.subTest(order=order):
                    result = Union([intervals[i] for i in order])
                    self.assertEqual([result.containsPoint(point) for point in points], expected)
                    self.assertEqual(result.length, F(sum(expected[1::2]), denominator))
                    for candidate in intervals:
                        self.assertEqual(
                            result.containsInterval(candidate),
                            all(
                                covered or not (0 < (point - candidate.start) % 1 < candidate.length)
                                for point, covered in zip(points, expected)
                            ),
                        )

    def test_all_union_pairs_on_small_rational_grid(self):
        # Three components suffice for every open set whose boundary lies
        # on this three-point grid. Deduplicate by independently computed
        # membership, then exercise all pairs, including full and empty sets.
        denominator = 3
        intervals = [
            Interval(F(start, denominator), F(start + length, denominator))
            for start in range(denominator)
            for length in range(denominator + 1)
        ]
        points = [F(i, 2 * denominator) for i in range(2 * denominator)]
        unions = {}
        for components in combinations_with_replacement(intervals, 3):
            membership = tuple(
                any(0 < (point - arc.start) % 1 < arc.length for arc in components)
                for point in points
            )
            if membership not in unions:
                unions[membership] = Union(components)
        for (left_members, left), (right_members, right) in product(unions.items(), repeat=2):
            with self.subTest(left=left_members, right=right_members):
                for operation in (operator.and_, operator.or_):
                    expected = [operation(a, b) for a, b in zip(left_members, right_members)]
                    result = operation(left, right)
                    self.assertEqual([result.containsPoint(point) for point in points], expected)
                    self.assertEqual(result.length, F(sum(expected[1::2]), denominator))
                    self.assertEqual(result.is_full, all(expected))


if __name__ == "__main__":
    unittest.main()
