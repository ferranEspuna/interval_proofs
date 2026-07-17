#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/../../.." && pwd)"
output_dir="$repo_root/json_results/verification_20260716/tiny_intervals_two_extra_unbounded_crosschecks"
solver="$output_dir/solve_with_strict_mip_tolerance.py"
compressor="$repo_root/json_results/verification_20260716/tiny_intervals_two_extra/compress_problem_and_repair.py"
cd "$repo_root"

run_case() {
    local m="$1"
    local run_name="m${m}_extra2_unbounded_nopresolve_mipabsgap0_mipfeastol1e-10"

    /usr/bin/time -v \
        .venv/bin/python "$solver" \
        --m "$m" \
        --run-name "$run_name" \
        --output-dir "$output_dir" \
        2>&1 | tee "$output_dir/$run_name.log"

    .venv/bin/python "$compressor" \
        "$output_dir/${run_name}_problem.json" \
        "$output_dir/${run_name}_solution.json"
}

run_case 34 &
pid_34=$!
run_case 40 &
pid_40=$!
wait "$pid_34"
wait "$pid_40"
