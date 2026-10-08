#!/usr/bin/env python3
"""
Simple Development Setup & Startup Script
===========================================
Boots the Baseball Simulation dev environment.

Usage:
  python frontend/docs/setup.py        # print the commands
  python frontend/docs/setup.py --run  # launch ./dev.sh
"""

import sys
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT
FRONTEND_DIR = REPO_ROOT / "frontend" / "assets"
DEV_SCRIPT = REPO_ROOT / "dev.sh"

BACKEND_CMD = ".venv/bin/python main.py"
FRONTEND_CMD = "npx expo start --web"

UNIFIED_CMD = "./dev.sh"
NPM_CMD = "npm run dev"
COMPOUND_CMD = (
    f"(cd {BACKEND_DIR} && {BACKEND_CMD}) & "
    f"(cd {FRONTEND_DIR} && {FRONTEND_CMD})"
)

DEV_MENU_INSTRUCTION = (
    "In the browser (http://localhost:8081), press Shift+D or tap the DEV button "
    "in the header. Make sure mock mode is toggled off so it communicates live "
    "with http://localhost:5000."
)


def print_setup():
    print("=" * 72)
    print("⚾  BASEBALL SIMULATION: DEV SETUP & STARTUP COMMANDS")
    print("=" * 72)
    print("\n⚡ [UNIFIED ONE-COMMAND STARTUP] (Runs both servers together):")
    print(f"   {UNIFIED_CMD}")
    print(f"   (or `{NPM_CMD}`)")
    print("\n   Compound One-Liner:")
    print(f"   {COMPOUND_CMD}")
    print("\n📁 [MANUAL TWO-TERMINAL SETUP]:")
    print("   Terminal 1 (Backend):")
    print(f"     cd {BACKEND_DIR}")
    print(f"     {BACKEND_CMD}")
    print("\n   Terminal 2 (Frontend):")
    print(f"     cd {FRONTEND_DIR}")
    print(f"     {FRONTEND_CMD}")
    print("\n🌐 [BROWSER & DEV MENU INSTRUCTION]:")
    print(f"   {DEV_MENU_INSTRUCTION}")
    print("=" * 72)


def main():
    print_setup()

    auto_run = "--run" in sys.argv
    if not auto_run and sys.stdin.isatty():
        try:
            choice = input("\n🚀 Would you like to launch the servers now? [Y/n]: ").strip().lower()
            if choice in ("", "y", "yes"):
                auto_run = True
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            return

    if auto_run:
        print("\n🚀 Executing ./dev.sh ... (Press Ctrl+C anytime to stop both servers)")
        try:
            subprocess.run([str(DEV_SCRIPT)], check=True)
        except KeyboardInterrupt:
            print("\nServers shut down.")


if __name__ == "__main__":
    main()
