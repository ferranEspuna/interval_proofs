"""Check that explicit circle sets open the arbitrary linear-form visualizer."""

import base64
from fractions import Fraction as F
import json
import unittest
from urllib.parse import parse_qs, urlsplit

from construction_visualizer_links import DEFAULT_VISUALIZER_URL
from explicit_construction import CircleOpenInterval, CircleOpenIntervalUnion


def decoded_state(url):
    encoded = parse_qs(urlsplit(url).query)["state"][0]
    padded = encoded + "=" * (-len(encoded) % 4)
    return json.loads(base64.urlsafe_b64decode(padded))


class ExplicitConstructionVisualizerTests(unittest.TestCase):
    def test_wrapping_interval_uses_public_url_and_preserves_width(self):
        interval = CircleOpenInterval(F(-1, 4), F(1, 4))
        url = interval.visualize()
        expected = urlsplit(DEFAULT_VISUALIZER_URL)
        actual = urlsplit(url)
        self.assertEqual(
            (actual.scheme, actual.netloc, actual.path),
            (expected.scheme, expected.netloc, expected.path),
        )
        state = decoded_state(url)
        self.assertEqual(state["mode"], "linear-form")
        self.assertEqual(state["coefficients"], [1, 1, -3])
        self.assertEqual(state["missingPoint"], 0)
        self.assertNotIn("m", state)
        self.assertFalse(state["fixTotalLength"])
        self.assertEqual(state["targetTotalLength"], 0.5)
        self.assertEqual(len(state["intervals"]), 1)
        self.assertEqual(state["intervals"][0]["start"], 0.75)
        self.assertEqual(state["intervals"][0]["width"], 0.5)
        self.assertEqual((interval.start, interval.end), (F(3, 4), F(5, 4)))

    def test_union_link_uses_merged_components_and_exact_total(self):
        union = CircleOpenIntervalUnion([
            CircleOpenInterval(F(0), F(1, 4)),
            CircleOpenInterval(F(1, 8), F(3, 8)),
            CircleOpenInterval(F(3, 4), F(7, 8)),
        ])
        before = [(interval.start, interval.end) for interval in union.intervals]
        coefficients = [10, 10, -19]
        state = decoded_state(union.visualize(coefficients=coefficients))
        self.assertEqual(state["mode"], "linear-form")
        self.assertEqual(state["coefficients"], coefficients)
        self.assertEqual(coefficients, [10, 10, -19])
        self.assertEqual(state["targetTotalLength"], 0.5)
        self.assertEqual(
            sorted((item["start"], item["width"]) for item in state["intervals"]),
            [(0.0, 0.375), (0.75, 0.125)],
        )
        self.assertEqual(
            [(interval.start, interval.end) for interval in union.intervals], before
        )

    def test_empty_interval_and_empty_union_display_empty_set(self):
        for empty in (CircleOpenInterval(F(1, 3), F(1, 3)), CircleOpenIntervalUnion([])):
            with self.subTest(empty=empty):
                state = decoded_state(empty.visualize())
                self.assertEqual(state["intervals"], [])
                self.assertEqual(state["targetTotalLength"], 0)

    def test_length_one_interval_preserves_its_origin(self):
        state = decoded_state(CircleOpenInterval(F(1, 4), F(5, 4)).visualize())
        self.assertEqual(len(state["intervals"]), 1)
        self.assertEqual(state["intervals"][0]["start"], 0.25)
        self.assertEqual(state["intervals"][0]["width"], 1)
        self.assertEqual(state["targetTotalLength"], 1)

    def test_full_circle_export_does_not_trigger_frontend_rescaling(self):
        union = CircleOpenIntervalUnion([
            CircleOpenInterval(F(0), F(3, 4)),
            CircleOpenInterval(F(1, 2), F(5, 4)),
        ])
        self.assertTrue(union.is_full)
        state = decoded_state(union.visualize())
        self.assertEqual(len(state["intervals"]), 1)
        self.assertEqual(state["intervals"][0]["start"], 0)
        self.assertEqual(state["intervals"][0]["width"], 1)
        self.assertEqual(state["targetTotalLength"], 1)

    def test_ids_and_colors_remain_valid_after_palette_wrap(self):
        union = CircleOpenIntervalUnion([
            CircleOpenInterval(F(index, 10), F(2 * index + 1, 20))
            for index in range(8)
        ])
        intervals = decoded_state(union.visualize())["intervals"]
        self.assertEqual(len(intervals), 8)
        self.assertEqual(len({item["id"] for item in intervals}), 8)
        for item in intervals:
            self.assertRegex(item["color"], r"^#[0-9a-fA-F]{6}$")

    def test_custom_url_keeps_query_and_fragment_and_replaces_state(self):
        url = CircleOpenInterval(F(0), F(1, 4)).visualize(
            coefficients=[2, -3, 1, 4],
            missing_point=F(-1, 4),
            base_url="https://example.test/visualizer/?keep=yes&empty=&state=old#circle",
        )
        parsed = urlsplit(url)
        query = parse_qs(parsed.query, keep_blank_values=True)
        self.assertEqual(parsed.netloc, "example.test")
        self.assertEqual(parsed.fragment, "circle")
        self.assertEqual(query["keep"], ["yes"])
        self.assertEqual(query["empty"], [""])
        self.assertEqual(len(query["state"]), 1)
        state = decoded_state(url)
        self.assertEqual(state["mode"], "linear-form")
        self.assertEqual(state["coefficients"], [2, -3, 1, 4])
        self.assertEqual(state["missingPoint"], 0.75)

    def test_arbitrary_coefficients_accept_sequences_and_generators(self):
        interval = CircleOpenInterval(F(0), F(1, 4))
        union = CircleOpenIntervalUnion([interval])
        for obj in (interval, union):
            for coefficients in ((0,), (-2,), (1, -1), (2, 0, -3, 4)):
                with self.subTest(type=type(obj).__name__, coefficients=coefficients):
                    state = decoded_state(obj.visualize(c for c in coefficients))
                    self.assertEqual(state["mode"], "linear-form")
                    self.assertEqual(state["coefficients"], list(coefficients))

    def test_invalid_coefficients_are_rejected(self):
        interval = CircleOpenInterval(F(0), F(1, 4))
        for coefficients in (
            [], [True, -3], [1.5, 2], [1.0, -3], ["1", -3],
            [float("nan")], [float("inf")], [2**53], [-2**53],
        ):
            with self.subTest(coefficients=coefficients):
                with self.assertRaises(ValueError):
                    interval.visualize(coefficients)

    def test_javascript_safe_integer_boundaries_are_preserved(self):
        coefficients = [2**53 - 1, -(2**53 - 1)]
        state = decoded_state(CircleOpenInterval(F(0), F(1, 4)).visualize(coefficients))
        self.assertEqual(state["coefficients"], coefficients)

    def test_missing_point_is_normalized_for_both_classes(self):
        interval = CircleOpenInterval(F(0), F(1, 4))
        for obj in (interval, CircleOpenIntervalUnion([interval])):
            state = decoded_state(obj.visualize([1, -1], missing_point=F(9, 4)))
            self.assertEqual(state["missingPoint"], 0.25)
            self.assertEqual(state["intervals"][0]["start"], 0)

    def test_nonfinite_missing_point_is_rejected(self):
        interval = CircleOpenInterval(F(0), F(1, 4))
        for point in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(point=point):
                with self.assertRaises(ValueError):
                    interval.visualize(missing_point=point)


if __name__ == "__main__":
    unittest.main()
