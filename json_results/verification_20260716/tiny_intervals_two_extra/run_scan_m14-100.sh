#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/../../.." && pwd)"
output_dir="$repo_root/json_results/verification_20260716/tiny_intervals_two_extra"
compressor="$output_dir/compress_problem_and_repair.py"
cd "$repo_root"

run_case() {
    local m="$1"
    local tie_choice="$2"
    local q
    local extra_length_bound
    if [[ "$tie_choice" == "smaller" ]]; then
        q=$((m / 4))
    else
        q=$(((m + 4) / 4))
    fi

    case $((m % 4)) in
        0)
            extra_length_bound=$(
                .venv/bin/python -c \
                    'import sys; m=int(sys.argv[1]); print(2/(m*m*(m+2)))' \
                    "$m"
            )
            ;;
        1)
            extra_length_bound=$(
                .venv/bin/python -c \
                    'import sys; m=int(sys.argv[1]); print(1/(m*m*(m+2)))' \
                    "$m"
            )
            ;;
        *)
            extra_length_bound=0
            ;;
    esac
    if [[ "$tie_choice" == "smaller" ]]; then
        extra_length_bound=0
    fi

    local stem="variable_extra_milp_m${m}_q${q}_anchor0_freebase0_extra2"
    local problem="$output_dir/${stem}_problem.json"
    local solution="$output_dir/${stem}_solution.json"
    local log="$output_dir/scan_m${m}_tie_${tie_choice}_anchor0_extra2.log"

    if [[ -s "$solution" && ( -s "$problem" || -s "$problem.gz" ) ]]; then
        if [[ -s "$problem" ]]; then
            .venv/bin/python "$compressor" "$problem" "$solution"
        fi
        return
    fi

    /usr/bin/time -v \
        .venv/bin/python equally_spaced_tiny_interval_lp.py \
        --m "$m" \
        --tie-choice "$tie_choice" \
        --anchor 0 \
        --extra-count 2 \
        --extra-length-bound "$extra_length_bound" \
        --mip-rel-gap 0 \
        --require-success \
        --output-dir "$output_dir" \
        2>&1 | tee "$log"

    .venv/bin/python "$compressor" "$problem" "$solution"
}

export repo_root output_dir compressor
export -f run_case

{
    for m in $(seq 14 100); do
        echo "$m larger"
    done
    for m in $(seq 16 4 100); do
        echo "$m smaller"
    done
} | xargs -n 2 -P 2 bash -c 'run_case "$1" "$2"' _
