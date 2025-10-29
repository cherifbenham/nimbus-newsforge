#!/usr/bin/env bash
# Start local backend (Flask) and frontend (Vite) for development.
# - Uses .venv for Python
# - Binds server on PORT (default 5001)
# - Starts Vite on 5173
# - Writes PIDs to server_backend.pid and client_dev.pid

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
cd "$ROOT_DIR"

echo "[start_dev] Repo root: $ROOT_DIR"

# Load environment variables from .env (tolerant to spaces around '=')
if [[ -f .env ]]; then
  echo "[start_dev] Loading environment from .env"
  set -a
  # Normalize KEY = value -> KEY=value and drop comments/blank lines
  # shellcheck disable=SC1090
  source <(sed -e 's/^[[:space:]]*#.*$//' \
               -e '/^[[:space:]]*$/d' \
               -e 's/[[:space:]]*=[[:space:]]*/=/' .env)
  set +a
fi

# Normalize GOOGLE_APPLICATION_CREDENTIALS to absolute path if set
if [[ -n "${GOOGLE_APPLICATION_CREDENTIALS:-}" ]]; then
  if [[ "${GOOGLE_APPLICATION_CREDENTIALS}" != /* ]]; then
    export GOOGLE_APPLICATION_CREDENTIALS="$ROOT_DIR/${GOOGLE_APPLICATION_CREDENTIALS}"
  fi
  if [[ -f "$GOOGLE_APPLICATION_CREDENTIALS" ]]; then
    echo "[start_dev] Using GOOGLE_APPLICATION_CREDENTIALS=$GOOGLE_APPLICATION_CREDENTIALS"
  else
    echo "[start_dev] Warning: credentials file not found: $GOOGLE_APPLICATION_CREDENTIALS" >&2
  fi
fi

# Propagate project into GOOGLE_CLOUD_PROJECT if missing
if [[ -n "${PROJECT_ID:-}" && -z "${GOOGLE_CLOUD_PROJECT:-}" ]]; then
  export GOOGLE_CLOUD_PROJECT="$PROJECT_ID"
fi

echo "[start_dev] PROJECT_ID=${PROJECT_ID:-} FIRESTORE_DB=${FIRESTORE_DATABASE_ID:-}"

FRESH=0
NO_FALLBACK=0

usage() {
  cat <<USAGE
Usage: scripts/start_dev.sh [options]

Options:
  --fresh          Stop any existing dev processes before starting
  --no-fallback    Do not set COMPOSE_WEEKLY_FALLBACK (use real Gemini)
  -h, --help       Show this help

Environment variables:
  PORT                         Backend port (default: 5001)
  COMPOSE_WEEKLY_FALLBACK      If set to 1, force local heuristic insights
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --fresh) FRESH=1; shift ;;
    --no-fallback) NO_FALLBACK=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1"; usage; exit 1 ;;
  esac
done

if [[ $FRESH -eq 1 ]]; then
  echo "[start_dev] Stopping existing dev processes..."
  scripts/stop_dev.sh || true
fi

VENV_DIR=".venv"
if [[ ! -d "$VENV_DIR" ]]; then
  echo "[start_dev] Missing $VENV_DIR. Create it: python3 -m venv .venv" >&2
  exit 1
fi

echo "[start_dev] Activating $VENV_DIR"
source "$VENV_DIR/bin/activate"

# Resolve Python from the virtualenv explicitly
PYTHON_BIN="$VENV_DIR/bin/python"
if [[ ! -x "$PYTHON_BIN" ]]; then
  # Fallback to discovered python3 if venv shim is missing
  PYTHON_BIN="$(command -v python3 || true)"
fi
if [[ -z "${PYTHON_BIN}" ]]; then
  echo "[start_dev] Could not find a Python interpreter. Ensure Python 3 is installed." >&2
  exit 1
fi

# Default backend port
export PORT="${PORT:-5001}"

# Fallback mode for compose-weekly (optional)
if [[ $NO_FALLBACK -eq 0 ]]; then
  export COMPOSE_WEEKLY_FALLBACK="${COMPOSE_WEEKLY_FALLBACK:-1}"
  echo "[start_dev] COMPOSE_WEEKLY_FALLBACK=$COMPOSE_WEEKLY_FALLBACK"
else
  echo "[start_dev] COMPOSE_WEEKLY_FALLBACK disabled"
fi

# Ensure pip is available in the virtualenv and up-to-date
if ! "$PYTHON_BIN" -m pip --version >/dev/null 2>&1; then
  echo "[start_dev] Bootstrapping pip in .venv"
  "$PYTHON_BIN" -m ensurepip --upgrade >/dev/null 2>&1 || true
fi
"$PYTHON_BIN" -m pip install --upgrade pip setuptools wheel >/dev/null 2>&1 || true

# Quick dependency sanity check for server (robust under `set -e`)
if ! "$PYTHON_BIN" - <<'PY' >/dev/null 2>&1; then
import sys
import importlib.util
mods = ["flask", "google.cloud.aiplatform"]
missing = [m for m in mods if importlib.util.find_spec(m) is None]
raise SystemExit(1 if missing else 0)
PY
  echo "[start_dev] Installing server dependencies..."
  "$PYTHON_BIN" -m pip install -r server/requirements.txt
fi

echo "[start_dev] Starting backend on port $PORT"
nohup "$PYTHON_BIN" server/app.py >> server_backend.log 2>&1 &
echo $! > server_backend.pid

# Frontend
echo "[start_dev] Preparing client dependencies..."
if [[ ! -d client/node_modules ]]; then
  (cd client && npm install)
fi

echo "[start_dev] Starting client on http://localhost:5173"
(
  cd client
  nohup npm run dev -- --host --port 5173 >> ../client_dev.log 2>&1 &
  echo $! > ../client_dev.pid
)

echo "[start_dev] Done. Open the app at http://localhost:5173"
echo "[start_dev] API base (dev): http://localhost:$PORT/api"
echo "[start_dev] To stop: scripts/stop_dev.sh"

# Print the client URL alone (easy to copy/click)
echo "http://localhost:5173"
