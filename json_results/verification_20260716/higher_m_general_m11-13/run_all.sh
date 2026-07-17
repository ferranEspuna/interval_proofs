#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/../../.." && pwd)"
output_dir="$repo_root/json_results/verification_20260716/higher_m_general_m11-13"
cd "$repo_root"

run_case() {
    local m="$1"
    local n="$2"
    local run_name="m${m}_N${n}_standard_gap0"

    /usr/bin/time -v \
        .venv/bin/python circle_intervals.py \
        -N "$n" \
        --m "$m" \
        --mip-rel-gap 0 \
        --require-success \
        --output-dir "$output_dir" \
        --run-name "$run_name" \
        2>&1 | tee "$output_dir/$run_name.log"
}

run_case 11 3
run_case 11 5
run_case 12 4
run_case 12 5
run_case 13 4
run_case 13 5
