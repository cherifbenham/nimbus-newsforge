#!/usr/bin/env bash
set -euo pipefail

echo "Stopping dev processes (server + client)..."

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
cd "$ROOT_DIR"

kill_pidfile() {
  local file="$1"; local label="$2"
  if [[ -f "$file" ]]; then
    local pid
    pid="$(cat "$file" 2>/dev/null || true)"
    if [[ -n "${pid}" ]] && kill -0 "$pid" 2>/dev/null; then
      echo "- Stopping $label (pid=$pid) via $file"
      kill "$pid" 2>/dev/null || true
      sleep 0.5
      if kill -0 "$pid" 2>/dev/null; then
        echo "  … still running, forcing kill -9"
        kill -9 "$pid" 2>/dev/null || true
      fi
    fi
    rm -f "$file" 2>/dev/null || true
  fi
}

kill_by_port() {
  local port="$1"; local label="$2"
  local pids
  pids="$(lsof -ti tcp:"$port" 2>/dev/null || true)"
  if [[ -n "$pids" ]]; then
    echo "- Stopping $label on port $port (pids: $pids)"
    kill $pids 2>/dev/null || true
    sleep 0.5
    # force if still alive
    for p in $pids; do
      if kill -0 "$p" 2>/dev/null; then
        kill -9 "$p" 2>/dev/null || true
      fi
    done
  fi
}

kill_by_pattern() {
  local pattern="$1"; local label="$2"
  if pkill -f "$pattern" 2>/dev/null; then
    echo "- Stopping $label by pattern: $pattern"
  fi
}

# 1) Use PID files when available
kill_pidfile logs/server_backend.pid "server"
kill_pidfile logs/client_dev.pid "client"

# 2) Kill by known ports
kill_by_port 5001 "server"
kill_by_port 5173 "client"

# 3) Fallback: kill common process patterns (non-fatal if not found)
kill_by_pattern "python .*server/app.py" "server (pattern)"
kill_by_pattern "vite" "vite dev server"
kill_by_pattern "esbuild.*service" "esbuild helper"

echo "Done."

