---
applyTo: "tools/python/**/*.py"
description: Conventions for the pharmacy_demo Python tools.
---
# Python tools

- Target Python 3.12 or later. Use `pathlib.Path` for every path and open text files with `encoding="utf-8"`. Write files with `newline="\n"` so output matches on Windows and Linux.
- Never hardcode `/usr`, `/bin`, `/tmp`, drive letters, or a user's home folder. Find the repo root with `pharmacy_demo.paths.repo_root()`.
- The command-line entry point is `pharmacy_demo/cli.py`. Every PowerShell script in `scripts/` wraps one subcommand, so keep flags stable.
- Output meant for other tools goes to stdout as JSON when `--json` is set. Human output is short, one line per finding.
- Exit codes: 0 pass, 1 findings or failure, 2 usage or setup error.
- Dependencies are pinned with hashes in `tools/python/requirements*.txt`. Don't add a package without updating those files.
- Add or update tests in `tools/python/tests/`. Run `.venv/bin/python -m pytest -q tools/python/tests` (on Windows, `.venv\Scripts\python`) and `ruff check tools/python`.
- Modules under `pharmacy_demo/modelgen/` and `samples.py` hold lab answers. They're for maintainers only; agents helping learners shouldn't read them.
