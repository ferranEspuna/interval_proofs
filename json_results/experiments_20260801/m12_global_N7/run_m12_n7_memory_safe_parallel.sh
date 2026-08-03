#!/usr/bin/env bash
# Run the 30 m=12,N=7 length-order cases with multiple independent workers.
#
# Every worker runs one HiGHS process at a time. Workers coordinate through
# flock locks under OUTPUT_DIR and create a case's log while holding the
# scheduler lock. The existence of that log is therefore a durable claim.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$REPO_ROOT"

CASE_SECONDS="${CASE_SECONDS:-7200}"
NODE_LIMIT="${NODE_LIMIT:-3000000}"
THREADS="${THREADS:-1}"
MAX_WORKERS="${MAX_WORKERS:-2}"
OUTPUT_DIR="${OUTPUT_DIR:-json_results/long_runs/m12_N7_length_order_depth2}"

if ! [[ "$MAX_WORKERS" =~ ^[1-9][0-9]*$ ]]; then
  echo "MAX_WORKERS must be a positive integer; got: $MAX_WORKERS" >&2
  exit 2
fi

if ! command -v flock >/dev/null 2>&1; then
  echo "This runner requires the flock command (normally from util-linux)." >&2
  exit 2
fi

mkdir -p "$OUTPUT_DIR"
STATE_DIR="$OUTPUT_DIR/.m12_n7_parallel_workers"
mkdir -p "$STATE_DIR"

SCHEDULER_LOCK="$STATE_DIR/scheduler.lock"
WORKER_LOCK="$STATE_DIR/worker-$$-${RANDOM}.lock"
WORKER_REGISTERED=0
CURRENT_SOLVER_PID=""
CURRENT_CASE=""

exec {SCHEDULER_FD}>>"$SCHEDULER_LOCK"

# Set by count_active_workers_locked. Call only while SCHEDULER_FD is locked.
ACTIVE_WORKERS=0
count_active_workers_locked() {
  local lock_file
  local -a worker_files=()

  ACTIVE_WORKERS=0
  shopt -s nullglob
  worker_files=("$STATE_DIR"/worker-*.lock)
  shopt -u nullglob

  for lock_file in "${worker_files[@]}"; do
    if [[ "$WORKER_REGISTERED" == 1 && "$lock_file" == "$WORKER_LOCK" ]]; then
      ACTIVE_WORKERS=$((ACTIVE_WORKERS + 1))
    elif flock --exclusive --nonblock "$lock_file" true 2>/dev/null; then
      # No process holds this file: it is debris from a killed worker.
      rm -f -- "$lock_file"
    else
      ACTIVE_WORKERS=$((ACTIVE_WORKERS + 1))
    fi
  done
}

# Call only while SCHEDULER_FD is locked. Removing the registration before
# releasing the scheduler lock ensures that two finishing workers cannot both
# see the other and both leave unresolved work behind.
deregister_worker_locked() {
  if [[ "$WORKER_REGISTERED" == 1 ]]; then
    flock --unlock "$WORKER_FD" || true
    rm -f -- "$WORKER_LOCK"
    WORKER_REGISTERED=0
  fi
}

cleanup() {
  local status=$?
  trap - EXIT INT TERM HUP

  # A signal handler normally waits for this child first. This is a final
  # safeguard against releasing the case claim while its solver still runs.
  if [[ -n "$CURRENT_SOLVER_PID" ]]; then
    if kill -0 "$CURRENT_SOLVER_PID" 2>/dev/null; then
      kill -TERM "$CURRENT_SOLVER_PID" 2>/dev/null || true
    fi
    wait "$CURRENT_SOLVER_PID" 2>/dev/null || true
    wait 2>/dev/null || true
  fi

  if [[ "$WORKER_REGISTERED" == 1 ]]; then
    flock "$SCHEDULER_FD" || true
    deregister_worker_locked
    flock --unlock "$SCHEDULER_FD" || true
  fi

  exit "$status"
}

stop_on_signal() {
  local status="$1"
  echo >&2
  echo "Stopping worker $$${CURRENT_CASE:+ while running case $CURRENT_CASE}." >&2
  if [[ -n "$CURRENT_SOLVER_PID" ]]; then
    if kill -0 "$CURRENT_SOLVER_PID" 2>/dev/null; then
      kill -TERM "$CURRENT_SOLVER_PID" 2>/dev/null || true
    fi
    wait "$CURRENT_SOLVER_PID" 2>/dev/null || true
    wait 2>/dev/null || true
    CURRENT_SOLVER_PID=""
  fi
  exit "$status"
}

trap cleanup EXIT
trap 'stop_on_signal 130' INT
trap 'stop_on_signal 143' TERM
trap 'stop_on_signal 129' HUP

# Admit this worker atomically. By default a third simultaneous launch exits
# instead of putting the 16 GiB machine back at risk of OOM.
flock "$SCHEDULER_FD"
count_active_workers_locked
if (( ACTIVE_WORKERS >= MAX_WORKERS )); then
  echo "WARNING: $ACTIVE_WORKERS worker(s) are already active; MAX_WORKERS=$MAX_WORKERS." >&2
  echo "This launch will exit without claiming a case." >&2
  flock --unlock "$SCHEDULER_FD"
  exit 0
fi

exec {WORKER_FD}>>"$WORKER_LOCK"
flock --exclusive "$WORKER_FD"
WORKER_REGISTERED=1
count_active_workers_locked
echo "Registered worker $$ ($ACTIVE_WORKERS/$MAX_WORKERS active)."
flock --unlock "$SCHEDULER_FD"

declare -A ATTEMPTED=()

case_is_closed() {
  local solution_path="$1"
  [[ -f "$solution_path" ]] &&
    grep -Eq '"status_name": "(optimal|infeasible)"' "$solution_path"
}

SELECTED_SECOND=""
SELECTED_THIRD=""
SELECTED_KIND=""
SELECTED_ACTIVE_WORKERS=0
EXIT_REASON=""
EXIT_UNFINISHED=0
EXIT_OTHER_WORKERS=0

select_case_or_exit_reason() {
  local second_index third_index key run_name solution_path log_path
  local unfinished=0

  SELECTED_SECOND=""
  SELECTED_THIRD=""
  SELECTED_KIND=""
  SELECTED_ACTIVE_WORKERS=0
  EXIT_REASON=""
  EXIT_UNFINISHED=0
  EXIT_OTHER_WORKERS=0

  flock "$SCHEDULER_FD"
  count_active_workers_locked

  # First pass: every worker prefers a genuinely new case. Creating its log
  # under this lock is the atomic claim that all other workers will observe.
  for second_index in 1 2 3 4 5 6; do
    for third_index in 1 2 3 4 5 6; do
      if [[ "$third_index" == "$second_index" ]]; then
        continue
      fi

      key="$second_index,$third_index"
      run_name="m12_N7_lengthorder_${second_index}-${third_index}"
      solution_path="$OUTPUT_DIR/${run_name}_solution.json"
      log_path="$OUTPUT_DIR/${run_name}.log"

      if case_is_closed "$solution_path"; then
        continue
      fi
      unfinished=$((unfinished + 1))

      if [[ -z "${ATTEMPTED[$key]+yes}" && ! -e "$log_path" ]]; then
        : >"$log_path"
        SELECTED_SECOND="$second_index"
        SELECTED_THIRD="$third_index"
        SELECTED_KIND="fresh"
        SELECTED_ACTIVE_WORKERS="$ACTIVE_WORKERS"
        ATTEMPTED["$key"]=1
        break 2
      fi
    done
  done

  # Only the final remaining worker may revisit a logged but unresolved case.
  # This recovers interrupted work without allowing concurrent log collisions.
  if [[ -z "$SELECTED_KIND" && "$ACTIVE_WORKERS" == 1 ]]; then
    for second_index in 1 2 3 4 5 6; do
      for third_index in 1 2 3 4 5 6; do
        if [[ "$third_index" == "$second_index" ]]; then
          continue
        fi

        key="$second_index,$third_index"
        run_name="m12_N7_lengthorder_${second_index}-${third_index}"
        solution_path="$OUTPUT_DIR/${run_name}_solution.json"
        log_path="$OUTPUT_DIR/${run_name}.log"

        if case_is_closed "$solution_path"; then
          continue
        fi

        if [[ -z "${ATTEMPTED[$key]+yes}" && -e "$log_path" ]]; then
          SELECTED_SECOND="$second_index"
          SELECTED_THIRD="$third_index"
          SELECTED_KIND="retry"
          SELECTED_ACTIVE_WORKERS=1
          ATTEMPTED["$key"]=1
          break 2
        fi
      done
    done
  fi

  if [[ -z "$SELECTED_KIND" ]]; then
    EXIT_UNFINISHED="$unfinished"
    if (( unfinished == 0 )); then
      EXIT_REASON="closed"
    elif (( ACTIVE_WORKERS > 1 )); then
      EXIT_REASON="other_workers"
      EXIT_OTHER_WORKERS=$((ACTIVE_WORKERS - 1))
      deregister_worker_locked
    else
      EXIT_REASON="unresolved"
    fi
  fi

  flock --unlock "$SCHEDULER_FD"
}

while true; do
  select_case_or_exit_reason

  if [[ -z "$SELECTED_KIND" ]]; then
    case "$EXIT_REASON" in
      closed)
        echo "All 30 cases are closed. Results are under $OUTPUT_DIR."
        exit 0
        ;;
      other_workers)
        echo "WARNING: $EXIT_UNFINISHED unfinished case(s) remain, but this worker has" >&2
        echo "no unlogged case to claim and $EXIT_OTHER_WORKERS other worker(s) are active." >&2
        echo "This worker has unregistered and will exit without touching existing logs." >&2
        exit 0
        ;;
      unresolved)
        echo "WARNING: $EXIT_UNFINISHED case(s) remain unresolved after this sole worker" >&2
        echo "attempted every eligible case once. It will exit rather than loop over them." >&2
        exit 0
        ;;
      *)
        echo "Internal scheduler error: no case and no exit reason." >&2
        exit 3
        ;;
    esac
  fi

  run_name="m12_N7_lengthorder_${SELECTED_SECOND}-${SELECTED_THIRD}"
  log_path="$OUTPUT_DIR/${run_name}.log"
  CURRENT_CASE="$SELECTED_SECOND,$SELECTED_THIRD"

  if [[ "$SELECTED_KIND" == "fresh" ]]; then
    echo "Starting fresh case $CURRENT_CASE ($SELECTED_ACTIVE_WORKERS active worker(s))."
  else
    echo "Retrying logged unresolved case $CURRENT_CASE as the sole worker."
  fi

  {
    printf '\n===== worker %s: %s case %s at %s; active_workers=%s =====\n' \
      "$$" "$SELECTED_KIND" "$CURRENT_CASE" "$(date --iso-8601=seconds)" \
      "$SELECTED_ACTIVE_WORKERS"
  } >>"$log_path"

  set +e
  .venv/bin/python \
    json_results/experiments_20260801/m12_global_N7/solve_translated_length_order_case.py \
    --length-order "$CURRENT_CASE" \
    --time-limit "$CASE_SECONDS" \
    --node-limit "$NODE_LIMIT" \
    --threads "$THREADS" \
    --output-dir "$OUTPUT_DIR" \
    --run-name "$run_name" \
    --disp \
    > >(tee -a "$log_path") 2>&1 &
  CURRENT_SOLVER_PID=$!
  wait "$CURRENT_SOLVER_PID"
  python_status=$?
  wait
  set -e

  CURRENT_SOLVER_PID=""
  if [[ "$python_status" != 0 ]]; then
    echo "Case $CURRENT_CASE exited with status $python_status; continuing." >&2
  fi
  CURRENT_CASE=""
done
