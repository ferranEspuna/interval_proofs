#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/../../.." && pwd)"
output_dir="$repo_root/json_results/verification_20260716/tiny_intervals_extra_count_saturation"
compressor="$repo_root/json_results/verification_20260716/tiny_intervals_two_extra/compress_problem_and_repair.py"
cd "$repo_root"

run_case() {
    local m="$1"
    local extra_count="$2"
    local extra_length_bound="$3"
    local bound_label="$4"
    local q=$(((m + 4) / 4))
    local stem=(
        "m${m}_q${q}_extra${extra_count}"
        "per_extra_bound_${bound_label}_ordered1_relgap0_absgap0"
    )
    local run_name="${stem[0]}_${stem[1]}"
    local problem="$output_dir/${run_name}_problem.json"
    local solution="$output_dir/${run_name}_solution.json"

    if [[ -s "$solution" && ( -s "$problem" || -s "$problem.gz" ) ]]; then
        if [[ -s "$problem" ]]; then
            .venv/bin/python "$compressor" "$problem" "$solution"
        fi
        return
    fi

    /usr/bin/time -v \
        .venv/bin/python equally_spaced_tiny_interval_lp.py \
        --m "$m" \
        --tie-choice larger \
        --anchor 0 \
        --extra-count "$extra_count" \
        --extra-length-bound "$extra_length_bound" \
        --ordered-extras \
        --mip-rel-gap 0 \
        --mip-abs-gap 0 \
        --require-success \
        --output-dir "$output_dir" \
        --run-name "$run_name" \
        2>&1 | tee "$output_dir/$run_name.log"

    .venv/bin/python "$compressor" "$problem" "$solution"
}

export repo_root output_dir compressor
export -f run_case

cat <<'CASES' | xargs -n 4 -P 2 bash -c 'run_case "$1" "$2" "$3" "$4"' _
12 5 0.000992063492063492 1over1008
13 5 0.0003944773175542406 1over2535
16 5 0.0004340277777777778 1over2304
17 6 0.0001821161901293025 1over5491
20 7 0.00022727272727272727 1over4400
21 7 0.00009859016070196195 1over10143
CASES
