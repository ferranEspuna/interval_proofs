"""Executable checks for the solver visualizer helpers.

Run with:

    python3 test_equally_spaced_tiny_interval_lp.py
"""

from __future__ import annotations

import base64
import json
from urllib.parse import parse_qs, urlsplit

from circle_intervals import solution_visualizer_state
from equally_spaced_tiny_interval_lp import add_visualizer_output, build_parser
from milp_problem import MILPSolution


def sample_solution(*, values: dict[str, float]) -> MILPSolution:
    return MILPSolution(
        problem_name="visualizer_test",
        status=0,
        status_name="optimal",
        success=True,
        message="test solution",
        objective_sense="maximize",
        optimum=sum(
            value for name, value in values.items() if name.startswith("alpha_")
        ),
        values=values,
    )


def decode_state(encoded: str) -> dict[str, object]:
    padded = encoded + "=" * (-len(encoded) % 4)
    return json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))


def main() -> None:
    custom_base_url = "https://example.test/view?theme=dark#intervals"
    args = build_parser().parse_args(
        ["--m", "12", "--visualizer-url", custom_base_url]
    )
    assert args.visualizer_url == custom_base_url

    solution = sample_solution(
        values={
            "x_0": 1.125,
            "alpha_0": 0.25,
            "x_1": 0.5,
            "alpha_1": 0.125,
        }
    )
    state, url = add_visualizer_output(
        solution,
        interval_count=2,
        m=12,
        base_url=custom_base_url,
    )

    assert state is not None
    assert url is not None
    assert state["m"] == 12
    assert state["targetTotalLength"] == 0.375
    intervals = state["intervals"]
    assert isinstance(intervals, list)
    assert intervals[0]["start"] == 0.125
    assert intervals[0]["width"] == 0.25
    assert solution.parameters["visualizer_state"] == state
    assert solution.parameters["visualizer_url"] == url

    split_url = urlsplit(url)
    query = parse_qs(split_url.query)
    assert split_url.fragment == "intervals"
    assert query["theme"] == ["dark"]
    assert decode_state(query["state"][0]) == state

    incomplete = sample_solution(values={"x_0": 0.25})
    assert add_visualizer_output(incomplete, interval_count=1, m=12) == (
        None,
        None,
    )
    assert "visualizer_state" not in incomplete.parameters
    assert "visualizer_url" not in incomplete.parameters

    tiny = sample_solution(values={"x_0": 0.125, "alpha_0": 5 / 12096})
    tiny_state, _ = add_visualizer_output(tiny, interval_count=1, m=12)
    assert tiny_state is not None
    assert tiny_state["intervals"][0]["width"] == round(5 / 12096, 12)

    translated = sample_solution(
        values={
            "t": 23 / 28,
            "x_0": 0.0,
            "alpha_0": 5 / 12096,
            "x_1": 137 / 144,
            "alpha_1": 1 / 1008,
        }
    )
    translated_state = solution_visualizer_state(
        translated,
        N=2,
        m=12,
        translated_missing_point=True,
    )
    translated_starts = [
        interval["start"] for interval in translated_state["intervals"]
    ]
    assert translated_starts == [
        round(float((137 / 144 + 23 / 280) % 1), 12),
        round(float(23 / 280), 12),
    ]

    print("All solver visualizer tests passed.")


if __name__ == "__main__":
    main()
