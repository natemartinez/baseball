#!/usr/bin/env bash
# ==============================================================================
# Run All Baseball Simulation Tests Concurrently
# Uses pytest-xdist to distribute test execution across available CPU cores.
# ==============================================================================

set -e

# Detect virtual environment python/pytest or system fallback
if [ -x ".venv/bin/python" ]; then
    PYTEST_CMD=(".venv/bin/python" "-m" "pytest")
elif [ -x ".venv/bin/pytest" ]; then
    PYTEST_CMD=(".venv/bin/pytest")
elif command -v pytest >/dev/null 2>&1; then
    PYTEST_CMD=("pytest")
else
    PYTEST_CMD=("python3" "-m" "pytest")
fi

echo "Running all tests concurrently with: ${PYTEST_CMD[*]} -n auto tests/"
"${PYTEST_CMD[@]}" -n auto tests/ "$@"

