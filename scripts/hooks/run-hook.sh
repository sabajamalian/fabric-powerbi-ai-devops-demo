#!/usr/bin/env bash
# Copilot hook entry point on macOS, Linux, and the Copilot cloud agent.
# Forwards the hook payload on stdin to python -m pharmacy_demo hook <event>.
# If .venv doesn't exist yet the hook does nothing, so a fresh clone still works.
set -u
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
python="$root/.venv/bin/python"
if [ ! -x "$python" ]; then
  echo "Lab hooks inactive: run scripts/Initialize-DevEnvironment.ps1 to create .venv." >&2
  exit 0
fi
"$python" -m pharmacy_demo --root "$root" hook "$1"
exit 0
