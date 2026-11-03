"""Exact open arcs and finite unions on R/Z.

Endpoints are real lifts: a wrapping arc can be specified as (3/4, 5/4).
Length zero is empty; length one excludes the coincident endpoint. A union
can also cover the whole circle, which is recorded by ``is_full``.
"""

from __future__ import annotations

from dataclasses import dataclass
from collections import Counter, defaultdict
from fractions import Fraction
from math import prod
from numbers import Integral
from typing import Iterable, Mapping

from construction_visualizer_links import (
    DEFAULT_VISUALIZER_URL,
    VISUALIZER_BASE_COLORS,
    visualizer_state_url,
)


@dataclass
class CircleOpenInterval:
    """The image of (start, end), with 0 <= end - start <= 1, on R/Z."""

    start: Fraction
    end: Fraction

    def __post_init__(self) -> None:
        start, end = Fraction(self.start), Fraction(self.end)
        length = end - start
        if not 0 <= length <= 1:
            raise ValueError("Length of the interval must be in the range [0, 1].")
        self.start = start % 1
        self.end = self.start + length

    @property
    def length(self) -> Fraction:
        return self.end - self.start

    def containsPoint(self, point: Fraction) -> bool:
        normalized_point = (Fraction(point) - self.start) % 1
        return 0 < normalized_point < self.length

    def containsInterval(self, other: CircleOpenInterval) -> bool:
        """Test set inclusion, allowing equal (excluded) boundary points."""
        if other.length == 0:
            return True
        start_diff = (other.start - self.start) % 1
        return start_diff + other.length <= self.length

    def __and__(
        self, other: CircleOpenInterval | CircleOpenIntervalUnion
    ) -> CircleOpenIntervalUnion:
        if isinstance(other, CircleOpenIntervalUnion):
            return other & self
        if not isinstance(other, CircleOpenInterval):
            return NotImplemented

        # Intersect compatible real lifts. Two long arcs may intersect in
        # two components; merely checking their endpoints misses this case.
        intervals: list[CircleOpenInterval] = []
        for shift in (-1, 0, 1):
            start = max(self.start, other.start + shift)
            end = min(self.end, other.end + shift)
            if start < end:
                intervals.append(CircleOpenInterval(start, end))
        return CircleOpenIntervalUnion(intervals)

    def __or__(
        self, other: CircleOpenInterval | CircleOpenIntervalUnion
    ) -> CircleOpenIntervalUnion:
        if isinstance(other, CircleOpenIntervalUnion):
            return other | self
        if not isinstance(other, CircleOpenInterval):
            return NotImplemented

        return CircleOpenIntervalUnion([self, other])

    def visualize(
        self,
        coefficients: Iterable[int] = (1, 1, -3),
        *,
        missing_point: Fraction = Fraction(0),
        base_url: str = DEFAULT_VISUALIZER_URL,
    ) -> str:
        """Return an arbitrary linear-form visualizer URL with this arc loaded.

        ``coefficients`` selects L(a_1, ..., a_k) = sum(c_i * a_i).
        ``missing_point`` marks a point modulo one. No browser is launched;
        only the display is converted to floating point.
        """
        return CircleOpenIntervalUnion([self]).visualize(
            coefficients, missing_point=missing_point, base_url=base_url
        )


class CircleOpenIntervalUnion:
    """A normalized finite union of open arcs.

    Components are sorted by start and disjoint unless ``is_full`` is true.
    The full circle has no single open-arc representation, so ``intervals``
    then holds two overlapping punctured circles covering all points.
    Use ``length`` for union measure, including in that case.
    """

    def __init__(self, intervals: Iterable[CircleOpenInterval]):
        # Neighboring copies recover components crossing the origin without
        # introducing an artificial hole there. Three copies suffice because
        # each input arc has length at most one and its start is in [0, 1).
        lifted = sorted(
            (interval.start + shift, interval.end + shift)
            for interval in intervals
            if interval.length > 0
            for shift in (-1, 0, 1)
        )
        merged: list[tuple[Fraction, Fraction]] = []
        for start, end in lifted:
            if merged and start < merged[-1][1]:
                previous_start, previous_end = merged[-1]
                merged[-1] = (previous_start, max(previous_end, end))
            else:
                # Touching open intervals must retain the missing endpoint.
                merged.append((start, end))

        # A real component longer than one projects onto the entire circle.
        # Exactly one is instead a circle missing its endpoint.
        self._is_full = any(end - start > 1 for start, end in merged)
        if self._is_full:
            self.intervals = [
                CircleOpenInterval(Fraction(0), Fraction(1)),
                CircleOpenInterval(Fraction(1, 2), Fraction(3, 2)),
            ]
        else:
            self.intervals = [
                CircleOpenInterval(start, end)
                for start, end in merged
                if 0 <= start < 1
            ]

    @property
    def is_full(self) -> bool:
        """Whether every point is present (stronger than length == 1)."""
        return self._is_full

    @property
    def length(self) -> Fraction:
        if self.is_full:
            return Fraction(1)
        return sum((interval.length for interval in self.intervals), Fraction(0))

    def containsInterval(self, other: CircleOpenInterval) -> bool:
        if other.length == 0 or self.is_full:
            return True
        return any(interval.containsInterval(other) for interval in self.intervals)

    def containsPoint(self, point: Fraction) -> bool:
        return self.is_full or any(
            interval.containsPoint(point) for interval in self.intervals
        )

    @classmethod
    def full_circle(cls) -> CircleOpenIntervalUnion:
        """Return the entire circle, including every endpoint."""
        return cls([
            CircleOpenInterval(Fraction(0), Fraction(1)),
            CircleOpenInterval(Fraction(1, 2), Fraction(3, 2)),
        ])

    def missing_point(self) -> Fraction | None:
        """Return a point outside this open set, or None if it is the circle.

        Prefer the midpoint of the largest gap. If the complement consists
        only of excluded endpoints, return one of those endpoints instead.
        """
        if self.is_full:
            return None
        if not self.intervals:
            return Fraction(0)
        gaps = [
            (
                self.intervals[(index + 1) % len(self.intervals)].start
                + (1 if index == len(self.intervals) - 1 else 0)
                - interval.end,
                interval.end,
            )
            for index, interval in enumerate(self.intervals)
        ]
        gap_length, gap_start = max(gaps)
        return (gap_start + gap_length / 2) % 1

    def apply_linear_form(self, coefficients: Iterable[int]) -> CircleLinearFormImage:
        """Return L(A), where each coefficient uses an independent point of A."""
        return apply_linear_form(self, coefficients)

    def __or__(
        self, other: CircleOpenInterval | CircleOpenIntervalUnion
    ) -> CircleOpenIntervalUnion:
        if isinstance(other, CircleOpenInterval):
            return CircleOpenIntervalUnion([*self.intervals, other])
        if not isinstance(other, CircleOpenIntervalUnion):
            return NotImplemented
        return CircleOpenIntervalUnion([*self.intervals, *other.intervals])

    def __and__(
        self, other: CircleOpenInterval | CircleOpenIntervalUnion
    ) -> CircleOpenIntervalUnion:
        if isinstance(other, CircleOpenInterval):
            other = CircleOpenIntervalUnion([other])
        if not isinstance(other, CircleOpenIntervalUnion):
            return NotImplemented
        if self.is_full:
            return CircleOpenIntervalUnion(other.intervals)
        if other.is_full:
            return CircleOpenIntervalUnion(self.intervals)
        return CircleOpenIntervalUnion(
            component
            for left in self.intervals
            for right in other.intervals
            for component in (left & right).intervals
        )

    def visualize(
        self,
        coefficients: Iterable[int] = (1, 1, -3),
        *,
        missing_point: Fraction = Fraction(0),
        base_url: str = DEFAULT_VISUALIZER_URL,
    ) -> str:
        """Return a shareable URL for the arbitrary linear-form visualizer.

        Supply a nonempty iterable of integer coefficients, each within
        JavaScript's exact integer range (abs(c) <= 2**53 - 1). The marked
        ``missing_point`` is normalized modulo one, without shifting the set.

        The website uses floating-point arcs and does not distinguish the
        full circle from a length-one arc with one point missing. Both are
        displayed with width one; Python membership remains exact.
        """
        coefficients = _coefficients(coefficients)
        if any(abs(c) > 2**53 - 1 for c in coefficients):
            raise ValueError("The visualizer coefficients must be JavaScript safe integers.")
        try:
            normalized_missing_point = float(Fraction(missing_point) % 1)
        except (ValueError, OverflowError) as exc:
            raise ValueError("The visualizer missing point must be finite.") from exc
        intervals = self.intervals
        if self.is_full:
            # Sending overlapping arcs would make the website rescale them.
            intervals = [CircleOpenInterval(Fraction(0), Fraction(1))]
        state: dict[str, object] = {
            "v": 1,
            "mode": "linear-form",
            "intervals": [
                {
                    "id": index + 1,
                    "start": float(interval.start),
                    "width": float(interval.length),
                    "color": VISUALIZER_BASE_COLORS[index % len(VISUALIZER_BASE_COLORS)],
                }
                for index, interval in enumerate(intervals)
            ],
            "coefficients": [int(c) for c in coefficients],
            "missingPoint": normalized_missing_point,
            "fixTotalLength": False,
            "targetTotalLength": float(self.length),
            "hiddenMixedComboKeys": [],
        }
        return visualizer_state_url(state, base_url=base_url)



@dataclass(frozen=True)
class CirclePointSet:
    """A finite circle set, used for the image of the all-zero linear form.

    A zero-length open arc is empty, so it cannot represent the singleton
    {0}. This separate type preserves that distinction without changing the
    meaning of CircleOpenIntervalUnion.
    """

    points: tuple[Fraction, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "points", tuple(sorted({Fraction(p) % 1 for p in self.points})))

    @property
    def length(self) -> Fraction:
        return Fraction(0)

    @property
    def is_full(self) -> bool:
        return False

    def containsPoint(self, point: Fraction) -> bool:
        return Fraction(point) % 1 in self.points

    def missing_point(self) -> Fraction:
        for index in range(len(self.points) + 1):
            candidate = Fraction(index, len(self.points) + 1)
            if not self.containsPoint(candidate):
                return candidate
        raise AssertionError("A finite set cannot cover the circle.")


CircleLinearFormImage = CircleOpenIntervalUnion | CirclePointSet


def _integer(value: int, name: str, *, positive: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise ValueError(f"{name} must be an integer.")
    value = int(value)
    if positive and value <= 0:
        raise ValueError(f"{name} must be a positive integer.")
    return value


def _coefficients(values: Iterable[int]) -> tuple[int, ...]:
    result = tuple(_integer(c, "Each coefficient") for c in values)
    if not result:
        raise ValueError("Provide a nonempty list of integer coefficients.")
    return result


def _as_union(value: CircleOpenInterval | CircleOpenIntervalUnion) -> CircleOpenIntervalUnion:
    if isinstance(value, CircleOpenInterval):
        return CircleOpenIntervalUnion([value])
    if not isinstance(value, CircleOpenIntervalUnion):
        raise TypeError("Expected a circle interval or interval union.")
    return value


def _project_open_intervals(
    intervals: Iterable[tuple[Fraction, Fraction]],
) -> CircleOpenIntervalUnion:
    arcs = []
    for left, right in intervals:
        if right - left > 1:
            return CircleOpenIntervalUnion.full_circle()
        if left < right:
            arcs.append(CircleOpenInterval(left, right))
    return CircleOpenIntervalUnion(arcs)


def dilate_interval_union(
    intervals: CircleOpenInterval | CircleOpenIntervalUnion,
    coefficient: int,
) -> CircleLinearFormImage:
    """Return the image under x -> coefficient*x mod 1, with exact endpoints."""
    coefficient = _integer(coefficient, "The coefficient")
    intervals = _as_union(intervals)
    if not intervals.intervals:
        return CircleOpenIntervalUnion([])
    if coefficient == 0:
        return CirclePointSet((Fraction(0),))
    if intervals.is_full:
        return CircleOpenIntervalUnion.full_circle()
    return _project_open_intervals(
        (coefficient * arc.start, coefficient * arc.end)
        if coefficient > 0 else (coefficient * arc.end, coefficient * arc.start)
        for arc in intervals.intervals
    )


def minkowski_sum(
    left: CircleOpenInterval | CircleOpenIntervalUnion,
    right: CircleOpenInterval | CircleOpenIntervalUnion,
) -> CircleOpenIntervalUnion:
    """Return {x+y mod 1 : x in left, y in right} for open circle sets."""
    left, right = _as_union(left), _as_union(right)
    if not left.intervals or not right.intervals:
        return CircleOpenIntervalUnion([])
    if left.is_full or right.is_full:
        return CircleOpenIntervalUnion.full_circle()
    return _project_open_intervals(
        (first.start + second.start, first.end + second.end)
        for first in left.intervals
        for second in right.intervals
    )


def apply_linear_form(
    intervals: CircleOpenInterval | CircleOpenIntervalUnion,
    coefficients: Iterable[int],
) -> CircleLinearFormImage:
    """Return the exact image L(A) = c_1*A + ... + c_k*A on the circle.

    Inputs in different terms are independent. In particular, 2*A is a
    dilation, whereas A+A is a Minkowski sum. All-zero coefficients give
    the singleton {0} for nonempty A, and the empty set for empty A.
    """
    coefficients = _coefficients(coefficients)
    intervals = _as_union(intervals)
    if not intervals.intervals:
        return CircleOpenIntervalUnion([])
    active = [c for c in coefficients if c]
    if not active:
        return CirclePointSet((Fraction(0),))
    dilations: dict[int, CircleOpenIntervalUnion] = {}
    result: CircleOpenIntervalUnion | None = None
    for coefficient in active:
        if coefficient not in dilations:
            dilation = dilate_interval_union(intervals, coefficient)
            # Active coefficients are nonzero, hence their images are open.
            assert isinstance(dilation, CircleOpenIntervalUnion)
            dilations[coefficient] = dilation
        term = dilations[coefficient]
        result = term if result is None else minkowski_sum(result, term)
        if result.is_full:
            return result
    assert result is not None
    return result


def preimage_under_repeated_addition(interval: CircleOpenInterval, n: int) -> CircleOpenIntervalUnion:
    """Return the preimage of an open arc under x -> n*x mod 1, for n > 0."""
    n = _integer(n, "The multiplier", positive=True)
    return CircleOpenIntervalUnion(
        CircleOpenInterval((interval.start + k) / n, (interval.end + k) / n)
        for k in range(n)
    )


def torus_preimage_partition(n_parts: int, m: int) -> Iterable[CircleOpenIntervalUnion]:
    """Pull back the equal open-arc partition; its finitely many boundaries are omitted."""
    n_parts = _integer(n_parts, "The number of parts", positive=True)
    m = _integer(m, "The multiplier", positive=True)
    for k in range(n_parts):
        yield preimage_under_repeated_addition(
            CircleOpenInterval(Fraction(k, n_parts), Fraction(k + 1, n_parts)), m
        )


def optimal_preimage_widths(coefficients: Iterable[int]) -> dict[int, Fraction]:
    """Widths maximizing the averaging bound subject to sum(r_d*w_d) <= 1.

    Group equal absolute nonzero coefficients d with multiplicity r_d.
    With g groups, w_d = 1/(g*r_d), and the best guaranteed density is
    product(w_d). This is optimal for this construction's bound, not a
    claim of global optimality among circle sets.
    """
    counts = Counter(abs(c) for c in _coefficients(coefficients) if c)
    return {d: Fraction(1, len(counts) * counts[d]) for d in sorted(counts)}


@dataclass(frozen=True)
class PreimageTarget:
    coefficient: int
    interval: CircleOpenInterval


@dataclass(frozen=True)
class PreimageConstruction:
    coefficients: tuple[int, ...]
    targets: tuple[PreimageTarget, ...]
    preimages: tuple[CircleOpenIntervalUnion, ...]
    A: CircleOpenIntervalUnion
    image: CircleLinearFormImage
    missing_point: Fraction | None
    bounding_start: Fraction
    bounding_width: Fraction
    guaranteed_density: Fraction | None

    def visualize(self, *, base_url: str = DEFAULT_VISUALIZER_URL) -> str:
        """Open the construction view with editable target intervals and all derived rings."""
        if any(abs(c) > 2**53 - 1 for c in self.coefficients):
            raise ValueError("The visualizer coefficients must be JavaScript safe integers.")
        return visualizer_state_url({
            "v": 1,
            "mode": "preimage-construction",
            "coefficients": list(self.coefficients),
            "targets": [
                {
                    "coefficient": target.coefficient,
                    "start": float(target.interval.start),
                    "width": float(target.interval.length),
                    "color": VISUALIZER_BASE_COLORS[index % len(VISUALIZER_BASE_COLORS)],
                }
                for index, target in enumerate(self.targets)
            ],
        }, base_url=base_url)


def preimage_construction(
    coefficients: Iterable[int],
    targets: Mapping[int, CircleOpenInterval] | None = None,
) -> PreimageConstruction:
    """Intersect one target preimage per distinct absolute coefficient.

    The targets constrain d*A to lie in I_d, for d = abs(c) > 0. Negative
    terms use -I_d in the bounding sum. If its total width is at most one,
    its open endpoint (or a complementary gap) certifies a missing point.
    The density bound refers to some choice of shifts, not every choice.
    With no nonzero coefficients, A is the whole circle and L(A) = {0}.
    """
    coefficients = _coefficients(coefficients)
    widths = optimal_preimage_widths(coefficients)
    if targets is None:
        targets = {d: CircleOpenInterval(Fraction(0), width) for d, width in widths.items()}
    else:
        targets = dict(targets)
        if set(targets) != set(widths):
            raise ValueError("Provide exactly one target for each distinct absolute nonzero coefficient.")
        if any(not isinstance(interval, CircleOpenInterval) for interval in targets.values()):
            raise TypeError("Targets must be CircleOpenInterval objects.")
    ordered_targets = tuple(PreimageTarget(d, targets[d]) for d in widths)
    preimages = tuple(
        preimage_under_repeated_addition(target.interval, target.coefficient)
        for target in ordered_targets
    )
    A = CircleOpenIntervalUnion.full_circle()
    for preimage in preimages:
        A = A & preimage
    image = apply_linear_form(A, coefficients)
    bounding_start = sum(
        (targets[c].start if c > 0 else -targets[-c].end)
        for c in coefficients if c
    )
    bounding_width = sum((targets[abs(c)].length for c in coefficients if c), Fraction(0))
    density = prod((target.interval.length for target in ordered_targets), start=Fraction(1))
    return PreimageConstruction(
        coefficients=coefficients,
        targets=ordered_targets,
        preimages=preimages,
        A=A,
        image=image,
        missing_point=image.missing_point(),
        bounding_start=Fraction(bounding_start) % 1,
        bounding_width=bounding_width,
        guaranteed_density=density if bounding_width <= 1 else None,
    )


def optimized_preimage_construction(
    coefficients: Iterable[int], *, max_partition_cells: int = 250_000,
) -> PreimageConstruction:
    """Select the largest partition cell for the optimal guaranteed widths.

    Sweep the common preimage boundaries and accumulate their lengths by
    target-cell indices. This examines O(sum(d*g*r_d)) elementary cells,
    avoiding the Cartesian product of all partition choices.
    """
    coefficients = _coefficients(coefficients)
    max_partition_cells = _integer(max_partition_cells, "The cell budget", positive=True)
    widths = optimal_preimage_widths(coefficients)
    if not widths:
        return preimage_construction(coefficients)
    groups = [(d, width.denominator) for d, width in widths.items()]
    denominators = {d * parts for d, parts in groups}
    if sum(denominators) > max_partition_cells:
        raise ValueError("The partition exceeds max_partition_cells; increase the budget explicitly.")
    boundaries = sorted({Fraction(k, denominator) for denominator in denominators for k in range(denominator + 1)})
    measures: dict[tuple[int, ...], Fraction] = defaultdict(Fraction)
    for left, right in zip(boundaries, boundaries[1:]):
        midpoint = (left + right) / 2
        key = tuple(int((d * midpoint % 1) * parts) for d, parts in groups)
        measures[key] += right - left
    best_key = max(measures, key=measures.get)
    targets = {
        d: CircleOpenInterval(Fraction(index, parts), Fraction(index + 1, parts))
        for (d, parts), index in zip(groups, best_key)
    }
    return preimage_construction(coefficients, targets)


def ruzsa_optimized_construction(coefficients: Iterable[int]) -> CircleOpenIntervalUnion:
    """Return A for the optimized partition construction (legacy convenience API)."""
    return optimized_preimage_construction(coefficients).A


if __name__ == "__main__":
    construction = optimized_preimage_construction([1, 1, -15])
    print(f"Resulting union of intervals: {construction.A.intervals}")
    print(f"Total length of the union: {construction.A.length}")
    print(f"Missing point of the linear-form image: {construction.missing_point}")
    print(construction.visualize())
