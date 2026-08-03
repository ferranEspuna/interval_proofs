"""Executable tests for construction_visualizer_links.py.

Run with:

    python3 -m unittest test_construction_visualizer_links.py
"""

from __future__ import annotations

import base64
from fractions import Fraction as F
import json
from pathlib import Path
import re
import unittest
from urllib.parse import parse_qs, urlsplit

from construction_visualizer_links import (
    DEFAULT_VISUALIZER_URL,
    NAMED_CHOICES,
    candela_setup,
    construction_visualizer_url,
    equally_spaced_construction,
    exact_check,
    fixed_base_extra_construction,
    latex_link_inventory,
    latex_package_text,
    mod0_hybrid_construction,
    mod0_tail_construction,
    mod1_tail_construction,
    named_construction,
    status_links_text,
    two_interval_construction,
)


class ConstructionVisualizerLinkTests(unittest.TestCase):
    def test_every_named_construction_has_an_exact_certificate(self) -> None:
        expected_measures = {
            "m3-endpoint": F(1, 5),
            "m3-sum-free": F(1, 5),
            "a4": F(11, 64),
            "a5": F(6, 35),
            "a5-split": F(6, 35),
            "a8": F(49, 320),
            "a9": F(136, 891),
            "m12-six": F(73, 504),
            "a12": F(251, 1728),
            "a13": F(122, 845),
            "m16-three": F(323, 2304),
            "m17-three": F(768, 5491),
        }
        self.assertEqual(set(expected_measures), set(NAMED_CHOICES))
        for name, expected_measure in expected_measures.items():
            with self.subTest(name=name):
                construction = named_construction(name)
                check = exact_check(construction)
                self.assertEqual(construction.measure, expected_measure)
                self.assertGreater(check.lifted_interaction_count, 0)

    def test_general_family_formulas(self) -> None:
        for m in range(3, 101):
            with self.subTest(family="equally-spaced", m=m):
                construction = equally_spaced_construction(m)
                expected = F((m + 2) ** 2 // 8, m * (m + 2))
                self.assertEqual(construction.measure, expected)

        tied_base = equally_spaced_construction(12, tie_choice="smaller")
        self.assertEqual(len(tied_base.intervals), 3)
        self.assertEqual(tied_base.measure, F(1, 7))
        self.assertTrue(tied_base.title.startswith("Optimized "))

        nonoptimal_base = equally_spaced_construction(20, q=2)
        self.assertFalse(nonoptimal_base.title.startswith("Optimized "))

        for m in (4, 20, 100):
            with self.subTest(family="two-interval", m=m):
                construction = two_interval_construction(m)
                self.assertEqual(construction.measure, F(2 * (m - 2), m * (m + 2)))

        for m in (16, 20, 100):
            with self.subTest(family="mod0-tail", m=m):
                construction = mod0_tail_construction(m)
                self.assertEqual(len(construction.intervals), 3 * (m - 4) // 4)
                self.assertEqual(
                    construction.measure,
                    F(m**3 + 4 * m * m + 8 * m - 64, 8 * m * m * (m + 2)),
                )

        for m in (12, 16, 100):
            with self.subTest(family="mod0-hybrid", m=m):
                construction = mod0_hybrid_construction(m)
                base_density = F((m + 2) ** 2 // 8, m * (m + 2))
                hybrid_gain = F(m * m - 2 * m - 4, 2 * m**3 * (m + 2))
                self.assertEqual(construction.measure, base_density + hybrid_gain)
                self.assertEqual(len(construction.intervals), m // 2 + 1)

        for m in (13, 17, 97):
            with self.subTest(family="mod1-tail", m=m):
                construction = mod1_tail_construction(m)
                self.assertEqual(len(construction.intervals), 3 * (m - 5) // 4)
                self.assertEqual(
                    construction.measure,
                    F(m**3 + 4 * m * m + 7 * m - 36, 8 * m * m * (m + 2)),
                )

    def test_fixed_base_prefixes_and_m12_exception(self) -> None:
        self.assertEqual(fixed_base_extra_construction(8, 2).measure, F(49, 320))
        self.assertEqual(fixed_base_extra_construction(9, 2).measure, F(136, 891))
        self.assertEqual(fixed_base_extra_construction(12, 2).measure, F(73, 504))
        self.assertEqual(fixed_base_extra_construction(13, 2).measure, F(122, 845))
        self.assertGreater(
            named_construction("a12").measure,
            fixed_base_extra_construction(12, 2).measure,
        )
        self.assertEqual(len(named_construction("m16-three").intervals), 8)
        self.assertEqual(len(named_construction("m17-three").intervals), 8)

    def test_three_extra_incumbent_endpoints(self) -> None:
        cases = {
            "m16-three": (
                F(1, 2304),
                (F(307, 16128), F(185, 8064), F(433, 16128)),
            ),
            "m17-three": (
                F(1, 5491),
                (F(558, 27455), F(653, 27455), F(2173, 27455)),
            ),
        }
        for name, (expected_length, expected_starts) in cases.items():
            with self.subTest(name=name):
                extras = sorted(
                    (
                        interval
                        for interval in named_construction(name).intervals
                        if interval.label.startswith("extra_")
                    ),
                    key=lambda interval: interval.start,
                )
                self.assertEqual(tuple(interval.start for interval in extras), expected_starts)
                self.assertEqual(
                    tuple(interval.length for interval in extras),
                    (expected_length,) * 3,
                )

    def test_interval_link_round_trip(self) -> None:
        construction = named_construction("a12")
        url = construction_visualizer_url(
            construction,
            base_url="https://example.test/visualizer/?keep=yes#circle",
        )
        split = urlsplit(url)
        query = parse_qs(split.query)
        self.assertEqual(query["keep"], ["yes"])
        encoded = query["state"][0]
        padded = encoded + "=" * (-len(encoded) % 4)
        state = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
        self.assertEqual(state["mode"], "interval")
        self.assertEqual(state["m"], 12)
        self.assertEqual(len(state["intervals"]), 7)
        self.assertAlmostEqual(state["targetTotalLength"], float(F(251, 1728)))
        self.assertEqual(split.fragment, "circle")

    def test_candela_state_and_exact_replay(self) -> None:
        state, metadata = candela_setup(7, 1)
        self.assertEqual(state["mode"], "candela")
        self.assertEqual(metadata["p"], 197)
        self.assertEqual(metadata["size"], 27)
        self.assertEqual(metadata["density"], F(27, 197))

    def test_latex_registry_covers_every_document_key(self) -> None:
        registered = dict(latex_link_inventory(DEFAULT_VISUALIZER_URL))
        used: set[str] = set()
        for path in Path("latex").rglob("*.tex"):
            used.update(re.findall(r"\\Visualizer\{([^}]+)\}", path.read_text()))
        self.assertTrue(used)
        self.assertEqual(used - registered.keys(), set())
        self.assertIn("equally-spaced-m12-q2", registered)
        self.assertIn("two-interval-m87", registered)
        self.assertIn("candela-m7-p197", registered)

    def test_generated_link_catalogs_are_current(self) -> None:
        self.assertEqual(
            Path("latex/visualizer_links.sty").read_text(),
            latex_package_text(DEFAULT_VISUALIZER_URL),
        )
        self.assertEqual(
            Path("VISUALIZER_LINKS.md").read_text(),
            status_links_text(DEFAULT_VISUALIZER_URL),
        )


if __name__ == "__main__":
    unittest.main()
