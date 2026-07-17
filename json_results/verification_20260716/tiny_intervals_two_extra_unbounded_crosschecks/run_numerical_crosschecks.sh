#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/../../.." && pwd)"
output_dir="$repo_root/json_results/verification_20260716/tiny_intervals_two_extra_unbounded_crosschecks"
compressor="$repo_root/json_results/verification_20260716/tiny_intervals_two_extra/compress_problem_and_repair.py"
cd "$repo_root"

run_case() {
    local m="$1"
    local run_name="$2"
    local extra_length_bound="${3:-}"
    local args=(
        --m "$m"
        --tie-choice larger
        --anchor 0
        --extra-count 2
        --mip-rel-gap 0
        --no-presolve
        --require-success
        --output-dir "$output_dir"
        --run-name "$run_name"
    )
    if [[ -n "$extra_length_bound" ]]; then
        args+=(--extra-length-bound "$extra_length_bound")
    fi

    /usr/bin/time -v \
        .venv/bin/python equally_spaced_tiny_interval_lp.py \
        "${args[@]}" \
        2>&1 | tee "$output_dir/$run_name.log"

    .venv/bin/python "$compressor" \
        "$output_dir/${run_name}_problem.json" \
        "$output_dir/${run_name}_solution.json"
}

run_case 34 m34_q9_extra2_unbounded_nopresolve &
pid_34=$!
run_case 40 m40_q11_extra2_unbounded_nopresolve &
pid_40=$!
wait "$pid_34"
wait "$pid_40"

run_case \
    100 \
    m100_q26_extra2_inductive_bound_nopresolve \
    1.96078431372549e-06
