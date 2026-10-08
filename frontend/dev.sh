#!/usr/bin/env bash
# ==============================================================================
# Baseball Simulation Client: Unified Dev Startup Script
# Boots the Python Flask backend and this Expo web client concurrently.
# Cleanly shuts down both processes on Ctrl+C (SIGINT).
#
# This client is vendored inside the backend repo at frontend/, so the Python
# backend lives one directory up (the repository root).
# Override with: BACKEND_DIR=/path/to/baseball ./dev.sh
# ==============================================================================

set -u

CLIENT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$CLIENT_ROOT/assets"
BACKEND_DIR="${BACKEND_DIR:-$(cd "$CLIENT_ROOT/.." && pwd)}"

# Color formatting
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}======================================================================${NC}"
echo -e "${GREEN}⚾  STARTING BASEBALL SIMULATION FULL DEV ENVIRONMENT${NC}"
echo -e "${CYAN}======================================================================${NC}"

# Resolve a Python interpreter from the backend virtualenv
if [ -x "$BACKEND_DIR/.venv/bin/python" ]; then
  PYTHON="$BACKEND_DIR/.venv/bin/python"
elif [ -x "$BACKEND_DIR/venv/bin/python" ]; then
  PYTHON="$BACKEND_DIR/venv/bin/python"
else
  echo -e "${RED}Error: no Python virtualenv found at $BACKEND_DIR/.venv${NC}"
  echo -e "${YELLOW}Set BACKEND_DIR=/path/to/baseball if the backend lives elsewhere.${NC}"
  exit 1
fi

# Node/npx must be available for Expo
if ! command -v node >/dev/null 2>&1 || ! command -v npx >/dev/null 2>&1; then
  if [ -s "$HOME/.nvm/nvm.sh" ]; then
    # shellcheck disable=SC1090
    . "$HOME/.nvm/nvm.sh"
  elif [ -s "$HOME/.var/app/com.visualstudio.code/config/nvm/nvm.sh" ]; then
    # shellcheck disable=SC1090
    . "$HOME/.var/app/com.visualstudio.code/config/nvm/nvm.sh"
  fi
fi

if ! command -v node >/dev/null 2>&1 || ! command -v npx >/dev/null 2>&1; then
  echo -e "${RED}Error: Node.js (node/npx) was not found on PATH.${NC}"
  echo -e "${YELLOW}Install Node.js or load nvm before running this script.${NC}"
  exit 1
fi

kill_tree() {
  local pid="$1"
  for child in $(pgrep -P "$pid" 2>/dev/null); do
    kill_tree "$child"
  done
  kill "$pid" 2>/dev/null
}

cleanup() {
  trap - SIGINT SIGTERM EXIT
  echo -e "\n${YELLOW}🛑 Shutting down backend and frontend dev servers...${NC}"
  # Kill each job's full process tree (npx/expo spawn detached node children)
  for pid in $(jobs -p); do
    kill_tree "$pid"
  done
  wait 2>/dev/null
  echo -e "${GREEN}✅ All dev servers stopped cleanly.${NC}"
  exit 0
}

# Trap exit signals to ensure child processes are terminated
trap cleanup SIGINT SIGTERM EXIT

echo -e "\n${GREEN}[1/2] Launching Python Flask Backend on http://localhost:5000...${NC}"
(
  cd "$BACKEND_DIR" && "$PYTHON" main.py
) &
BACKEND_PID=$!

# Wait briefly for backend to initialize
sleep 1.5

echo -e "${GREEN}[2/2] Launching Expo Web Frontend on http://localhost:8081...${NC}"
echo -e "${YELLOW}👉 In the browser, press Shift+D or tap 'DEV' to toggle live backend.${NC}\n"

(
  cd "$FRONTEND_DIR" && npx expo start --web
) &
FRONTEND_PID=$!

# Wait for both processes
wait
