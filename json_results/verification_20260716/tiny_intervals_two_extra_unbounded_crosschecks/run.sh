#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/../../.." && pwd)"
output_dir="$repo_root/json_results/verification_20260716/tiny_intervals_two_extra_unbounded_crosschecks"
compressor="$repo_root/json_results/verification_20260716/tiny_intervals_two_extra/compress_problem_and_repair.py"
cd "$repo_root"

run_case() {
    local m="$1"
    local run_label="m${m}_larger_unbounded_extra2"
    local q=$(((m + 4) / 4))
    local stem="variable_extra_milp_m${m}_q${q}_anchor0_freebase0_extra2"
    local problem="$output_dir/${stem}_problem.json"
    local solution="$output_dir/${stem}_solution.json"

    /usr/bin/time -v \
        .venv/bin/python equally_spaced_tiny_interval_lp.py \
        --m "$m" \
        --tie-choice larger \
        --anchor 0 \
        --extra-count 2 \
        --mip-rel-gap 0 \
        --require-success \
        --output-dir "$output_dir" \
        2>&1 | tee "$output_dir/$run_label.log"

    .venv/bin/python "$compressor" "$problem" "$solution"
}

run_case 44 &
pid_44=$!
run_case 46 &
pid_46=$!
wait "$pid_44"
wait "$pid_46"
