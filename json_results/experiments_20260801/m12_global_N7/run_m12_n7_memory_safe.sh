#!/usr/bin/env bash
# Exhaustively run the 30 second-/third-shortest length-order cases in series.
# Sequential execution releases each HiGHS tree before starting the next case.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$REPO_ROOT"

CASE_SECONDS="${CASE_SECONDS:-7200}"
NODE_LIMIT="${NODE_LIMIT:-3000000}"
THREADS="${THREADS:-1}"
OUTPUT_DIR="${OUTPUT_DIR:-json_results/long_runs/m12_N7_length_order_depth2}"

mkdir -p "$OUTPUT_DIR"

for second_index in 1 2 3 4 5 6; do
  for third_index in 1 2 3 4 5 6; do
    if [[ "$third_index" == "$second_index" ]]; then
      continue
    fi

    run_name="m12_N7_lengthorder_${second_index}-${third_index}"
    solution_path="$OUTPUT_DIR/${run_name}_solution.json"
    log_path="$OUTPUT_DIR/${run_name}.log"

    if [[ -f "$solution_path" ]] && \
       grep -Eq '"status_name": "(optimal|infeasible)"' "$solution_path"; then
      echo "Skipping completed case $second_index,$third_index"
      continue
    fi

    echo "Starting case $second_index,$third_index"
    set +e
    .venv/bin/python \
      json_results/experiments_20260801/m12_global_N7/solve_translated_length_order_case.py \
      --length-order "$second_index,$third_index" \
      --time-limit "$CASE_SECONDS" \
      --node-limit "$NODE_LIMIT" \
      --threads "$THREADS" \
      --output-dir "$OUTPUT_DIR" \
      --run-name "$run_name" \
      --disp \
      2>&1 | tee "$log_path"
    python_status="${PIPESTATUS[0]}"
    set -e

    if [[ "$python_status" != 0 ]]; then
      echo "Case $second_index,$third_index exited with status $python_status; continuing."
    fi
  done
done

echo "All 30 cases attempted. Results are under $OUTPUT_DIR."
