#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/../../.." && pwd)"
output_dir="$repo_root/json_results/verification_20260716/higher_m_general_m11-13"
cd "$repo_root"

/usr/bin/time -v \
    .venv/bin/python circle_intervals.py \
    -N 6 \
    --m 13 \
    --mip-rel-gap 0 \
    --require-success \
    --output-dir "$output_dir" \
    --run-name m13_N6_standard_gap0 \
    2>&1 | tee "$output_dir/m13_N6_standard_gap0.log"
