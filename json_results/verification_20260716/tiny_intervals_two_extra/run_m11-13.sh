#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/../../.." && pwd)"
output_dir="$repo_root/json_results/verification_20260716/tiny_intervals_two_extra"
cd "$repo_root"

run_case() {
    local m="$1"
    local tie_choice="$2"
    local log_name="scan_m${m}_tie_${tie_choice}_anchor0_extra2.log"

    /usr/bin/time -v \
        .venv/bin/python equally_spaced_tiny_interval_lp.py \
        --m "$m" \
        --tie-choice "$tie_choice" \
        --anchor 0 \
        --extra-count 2 \
        --mip-rel-gap 0 \
        --require-success \
        --output-dir "$output_dir" \
        2>&1 | tee "$output_dir/$log_name"
}

run_case 11 larger
run_case 12 larger
run_case 12 smaller
run_case 13 larger
