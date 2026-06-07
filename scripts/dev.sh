#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-start}"
if [[ $# -gt 0 ]]; then
  shift
fi

WITH_POSTGRES=0
BACKEND_PORT=8000
FRONTEND_PORT=5173

while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-postgres)
      WITH_POSTGRES=1
      shift
      ;;
    --backend-port)
      BACKEND_PORT="${2:?Missing value for --backend-port}"
      shift 2
      ;;
    --frontend-port)
      FRONTEND_PORT="${2:?Missing value for --frontend-port}"
      shift 2
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 2
      ;;
  esac
done

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
STATE_DIR="$PROJECT_ROOT/.dev"
PID_DIR="$STATE_DIR/pids"
LOG_DIR="$STATE_DIR/logs"
PYTHON_EXE="$BACKEND_DIR/.venv/bin/python"

ensure_state_dirs() {
  mkdir -p "$PID_DIR" "$LOG_DIR"
}

pid_file() {
  printf '%s/%s.pid' "$PID_DIR" "$1"
}

managed_pid() {
  local name="$1"
  local file
  file="$(pid_file "$name")"

  if [[ ! -f "$file" ]]; then
    return 1
  fi

  local pid
  pid="$(tr -d '[:space:]' < "$file")"
  if [[ -z "$pid" ]]; then
    return 1
  fi

  if kill -0 "$pid" >/dev/null 2>&1; then
    printf '%s' "$pid"
    return 0
  fi

  rm -f "$file"
  return 1
}

stop_process_tree() {
  local pid="$1"
  local child

  if command -v pgrep >/dev/null 2>&1; then
    while read -r child; do
      [[ -n "$child" ]] && stop_process_tree "$child"
    done < <(pgrep -P "$pid" || true)
  fi

  kill "$pid" >/dev/null 2>&1 || true
  sleep 1
  kill -9 "$pid" >/dev/null 2>&1 || true
}

start_managed_process() {
  local name="$1"
  local workdir="$2"
  shift 2

  local existing_pid
  if existing_pid="$(managed_pid "$name")"; then
    echo "$name already running (pid $existing_pid)."
    return
  fi

  local stdout="$LOG_DIR/$name.out.log"
  local stderr="$LOG_DIR/$name.err.log"

  (
    cd "$workdir"
    nohup "$@" >"$stdout" 2>"$stderr" &
    echo $! >"$(pid_file "$name")"
  )

  echo "Started $name (pid $(cat "$(pid_file "$name")"))."
}

stop_managed_process() {
  local name="$1"
  local pid

  if ! pid="$(managed_pid "$name")"; then
    echo "$name is not running."
    return
  fi

  stop_process_tree "$pid"
  rm -f "$(pid_file "$name")"
  echo "Stopped $name."
}

show_status() {
  local name="$1"
  local pid

  if pid="$(managed_pid "$name")"; then
    echo "$name: running (pid $pid)"
  else
    echo "$name: stopped"
  fi
}

show_logs() {
  echo "Logs directory: $LOG_DIR"
  find "$LOG_DIR" -maxdepth 1 -type f -name "*.log" | sort | while read -r file; do
    echo
    echo "== $(basename "$file") =="
    tail -n 20 "$file" || true
  done
}

start_dev_services() {
  ensure_state_dirs

  if [[ ! -x "$PYTHON_EXE" ]]; then
    echo "Backend virtualenv not found. Expected: $PYTHON_EXE" >&2
    exit 1
  fi

  if [[ "$WITH_POSTGRES" -eq 1 ]]; then
    (cd "$PROJECT_ROOT" && docker compose up -d postgres)
  fi

  start_managed_process \
    "backend" \
    "$BACKEND_DIR" \
    "$PYTHON_EXE" -m uvicorn app.main:app --reload --host 127.0.0.1 --port "$BACKEND_PORT"

  start_managed_process \
    "worker" \
    "$BACKEND_DIR" \
    "$PYTHON_EXE" -m app.workers.worker_main

  start_managed_process \
    "frontend" \
    "$PROJECT_ROOT" \
    env PORT="$FRONTEND_PORT" node "$FRONTEND_DIR/server.js"

  echo
  echo "Backend:  http://127.0.0.1:$BACKEND_PORT"
  echo "Docs:     http://127.0.0.1:$BACKEND_PORT/docs"
  echo "Frontend: http://127.0.0.1:$FRONTEND_PORT"
}

stop_dev_services() {
  stop_managed_process "frontend"
  stop_managed_process "worker"
  stop_managed_process "backend"
}

case "$ACTION" in
  start)
    start_dev_services
    ;;
  stop)
    ensure_state_dirs
    stop_dev_services
    ;;
  restart)
    ensure_state_dirs
    stop_dev_services
    start_dev_services
    ;;
  status)
    ensure_state_dirs
    show_status "backend"
    show_status "worker"
    show_status "frontend"
    ;;
  logs)
    ensure_state_dirs
    show_logs
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|status|logs} [--with-postgres] [--backend-port PORT] [--frontend-port PORT]" >&2
    exit 2
    ;;
esac
