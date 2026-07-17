#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/../../.." && pwd)"
output_dir="$repo_root/json_results/verification_20260716/tiny_intervals_three_extra"
compressor="$repo_root/json_results/verification_20260716/tiny_intervals_two_extra/compress_problem_and_repair.py"
cd "$repo_root"

run_case() {
    local m="$1"
    local tie_choice="$2"
    local extra_length_bound="$3"
    local bound_label="$4"
    local q
    if [[ "$tie_choice" == "smaller" ]]; then
        q=$((m / 4))
    else
        q=$(((m + 4) / 4))
    fi

    local run_name="m${m}_q${q}_extra3_per_extra_bound_${bound_label}_gap0"
    local problem="$output_dir/${run_name}_problem.json"
    local solution="$output_dir/${run_name}_solution.json"
    local log="$output_dir/$run_name.log"

    /usr/bin/time -v \
        .venv/bin/python equally_spaced_tiny_interval_lp.py \
        --m "$m" \
        --tie-choice "$tie_choice" \
        --anchor 0 \
        --extra-count 3 \
        --extra-length-bound "$extra_length_bound" \
        --mip-rel-gap 0 \
        --require-success \
        --output-dir "$output_dir" \
        --run-name "$run_name" \
        2>&1 | tee "$log"

    .venv/bin/python "$compressor" "$problem" "$solution"
}

run_case 8 larger 0.003125 1over320
run_case 9 larger 0.001122334455667789 1over891
run_case 12 larger 0.000992063492063492 1over1008
run_case 13 larger 0.0003944773175542406 1over2535
run_case 16 larger 0.0004340277777777778 1over2304
run_case 17 larger 0.0001821161901293025 1over5491
run_case 12 smaller 0 zero
run_case 16 smaller 0 zero
