#!/usr/bin/env bash
# ==============================================================================
# Baseball Simulation: Unified Dev Startup Script
# Boots both the Python backend and React Native Expo web frontend concurrently.
# Cleanly shuts down both processes on Ctrl+C (SIGINT).
# ==============================================================================

BACKEND_DIR="/Users/ljmartinez/Downloads/dev-projects/baseball"
FRONTEND_DIR="/Users/ljmartinez/antigravity/Baseball-Simulation-Client/mobile"

# Color formatting
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}======================================================================${NC}"
echo -e "${GREEN}⚾  STARTING BASEBALL SIMULATION FULL DEV ENVIRONMENT${NC}"
echo -e "${CYAN}======================================================================${NC}"

# Check virtual environment
if [ ! -f "$BACKEND_DIR/.venv/bin/python" ]; then
  echo -e "${RED}Error: Python virtual environment not found at $BACKEND_DIR/.venv/bin/python${NC}"
  exit 1
fi

cleanup() {
  echo -e "\n${YELLOW}🛑 Shutting down backend and frontend dev servers...${NC}"
  kill $(jobs -p) 2>/dev/null
  wait 2>/dev/null
  echo -e "${GREEN}✅ All dev servers stopped cleanly.${NC}"
  exit 0
}

# Trap exit signals to ensure child processes are terminated
trap cleanup SIGINT SIGTERM EXIT

echo -e "\n${GREEN}[1/2] Launching Python Flask Backend on http://localhost:5000...${NC}"
(
  cd "$BACKEND_DIR" && "$BACKEND_DIR/.venv/bin/python" main.py
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
