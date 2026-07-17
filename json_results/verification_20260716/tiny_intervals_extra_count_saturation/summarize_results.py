#!/usr/bin/env python3
"""Summarize the bounded extra-count saturation campaign."""

import csv
import json
from pathlib import Path


ARTIFACT_DIR = Path(__file__).resolve().parent
JSON_PATH = ARTIFACT_DIR / "result_summary.json"
CSV_PATH = ARTIFACT_DIR / "result_summary.csv"
TOLERANCE = 1e-9


def main():
    rows = []
    for path in ARTIFACT_DIR.glob("*_solution.json"):
        solution = json.loads(path.read_text(encoding="utf-8"))
        parameters = solution["parameters"]
        q = int(parameters["q"])
        extra_count = int(parameters["extra_count"])
        extras = [
            float(solution["values"][f"alpha_{q + index}"])
            for index in range(extra_count)
        ]
        bound = float(parameters["extra_length_bound"])
        gain = float(solution["optimum"]) - float(parameters["base_density"])
        options = parameters["solver_options"]
        rows.append(
            {
                "m": int(parameters["m"]),
                "q": q,
                "extra_count": extra_count,
                "ordered_extras": bool(parameters.get("order_extra_intervals", False)),
                "positive_extra_count": sum(value > TOLERANCE for value in extras),
                "full_bound_extra_count": sum(abs(value - bound) <= TOLERANCE for value in extras),
                "base_density": parameters["base_density"],
                "per_extra_bound": bound,
                "gain": gain,
                "gain_in_bound_units": gain / bound,
                "extra_lengths_descending": sorted(extras, reverse=True),
                "success": solution["success"],
                "status_name": solution["status_name"],
                "mip_gap": solution["solver_details"]["mip_gap"],
                "mip_node_count": solution["solver_details"]["mip_node_count"],
                "mip_rel_gap_option": options.get("mip_rel_gap"),
                "mip_abs_gap_option": options.get("mip_abs_gap"),
                "solution": path.name,
            }
        )

    rows.sort(key=lambda row: (row["m"], row["extra_count"], row["ordered_extras"]))
    assert len(rows) == 18, len(rows)
    assert all(row["success"] for row in rows)
    assert all(row["status_name"] == "optimal" for row in rows)
    assert all(row["mip_gap"] == 0 for row in rows)
    assert all(row["mip_rel_gap_option"] == 0 for row in rows)
    assert all(row["mip_abs_gap_option"] == 0 for row in rows)

    report = {
        "solution_count": len(rows),
        "all_success_optimal_zero_stored_gap": True,
        "all_requested_relative_and_absolute_gap_zero": True,
        "reporting_tolerance": TOLERANCE,
        "rows": rows,
    }
    JSON_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    with CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    for row in rows:
        print(
            f"m={row['m']:2} K={row['extra_count']} "
            f"positive={row['positive_extra_count']} "
            f"full={row['full_bound_extra_count']} "
            f"gain/bound={row['gain_in_bound_units']:.12g} "
            f"nodes={row['mip_node_count']}"
        )


if __name__ == "__main__":
    main()
