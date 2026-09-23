"""Agent hook handler shared by the pwsh and bash wrappers in scripts/hooks/.

Reads the hook payload (JSON) on stdin and writes a JSON decision on stdout. Accepts both the
Copilot CLI payload shape (toolName, toolArgs) and the snake_case shape (tool_name, tool_input).
Silence means "no opinion": this handler never returns "allow", so it can't bypass a permission prompt.

Output carries both shapes in one object: top-level fields for Copilot CLI and the cloud agent, and
hookSpecificOutput for the VS Code Local harness. Each runtime ignores the fields it doesn't use.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

PATH_KEYS = {
    "path",
    "paths",
    "file",
    "files",
    "file_path",
    "filepath",
    "filePath",
    "filename",
    "target_file",
    "targetFile",
    "uri",
    "dirPath",
    "old_path",
    "new_path",
    "source",
    "destination",
}
COMMAND_KEYS = {"command", "cmd", "script", "commandLine"}

NEVER_EDIT = [
    (
        "data/generated/",
        "Generated data. Change tools/python/pharmacy_demo/datagen.py and run scripts/New-SyntheticData.ps1.",
    ),
    (
        "evaluation/expected/",
        "Expected answers come from the DuckDB oracle. Run scripts/Update-ExpectedResults.ps1.",
    ),
    ("/.pbi/cache.abf", "Power BI Desktop cache file."),
    ("/.pbi/localSettings.json", "Power BI Desktop local settings."),
    (
        ".SemanticModel/Copilot/",
        "Power BI Desktop writes the Copilot folder. Draft in fabric/ai-prep/ and apply through Prep data for AI.",
    ),
]
MAINTAINER_ONLY = [
    ("evaluation/expected/", "Expected answers are hidden from agents so question runs stay honest."),
    (
        "evaluation/questions.yaml",
        "questions.yaml holds reference answers. Use: python -m pharmacy_demo questions.",
    ),
    ("tools/python/pharmacy_demo/modelgen/", "The checkpoint generator contains the lab answers."),
    ("tools/python/pharmacy_demo/samples.py", "Sample runs are generated from the answers."),
    (
        "pharmacy_demo dax-queries",
        "Reference DAX is hidden from agents. Run scripts/Invoke-DaxQuestionTests.ps1 for pass or fail only.",
    ),
]
SHELL_DENY = [
    (
        re.compile(r"\bgit\s+push\b[^\n]*(\s--force\b|\s-f\b|\s--force-with-lease\b)"),
        "Force push is blocked in this repo.",
    ),
    (re.compile(r"\bgh\s+auth\s+token\b"), "Printing GitHub tokens is blocked."),
    (re.compile(r"get-access-token"), "Printing cloud access tokens is blocked."),
    (
        re.compile(r"\bgit\s+config\s+--global\b"),
        "Changing global Git config is blocked; ask the user to do it.",
    ),
]
SHELL_ASK = [
    (re.compile(r"\bgit\s+(reset\s+--hard|clean\s+-[a-z]*f)"), "This discards local work."),
]
EDIT_WORDS = ("edit", "create", "write", "replace", "insert", "patch", "delete", "remove", "move", "rename")
SHELL_WORDS = ("bash", "powershell", "pwsh", "shell", "terminal", "run_in", "execute", "command")


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(root: Path, entry: dict) -> None:
    try:
        folder = root / "out" / "hooks"
        folder.mkdir(parents=True, exist_ok=True)
        with (folder / "session.log").open("a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps({"time": _now(), **entry}) + "\n")
    except OSError:
        pass


def _emit(event_name: str, **fields: str) -> None:
    print(json.dumps({**fields, "hookSpecificOutput": {"hookEventName": event_name, **fields}}))


def _payload() -> dict:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _tool(payload: dict) -> tuple[str, object]:
    name = payload.get("toolName") or payload.get("tool_name") or ""
    args = payload.get("toolArgs", payload.get("tool_input", {}))
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except json.JSONDecodeError:
            args = {"input": args}
    return str(name), args


def _collect(args, keys: set[str]) -> list[str]:
    found: list[str] = []
    if isinstance(args, dict):
        for key, value in args.items():
            if key in keys:
                if isinstance(value, str):
                    found.append(value)
                elif isinstance(value, list):
                    found.extend(v for v in value if isinstance(v, str))
            elif isinstance(value, (dict, list)):
                found.extend(_collect(value, keys))
    elif isinstance(args, list):
        for item in args:
            found.extend(_collect(item, keys))
    return found


def _patch_paths(args) -> list[str]:
    text = json.dumps(args)
    return re.findall(r"\*\*\* (?:Add|Update|Delete) File: ([^\\\"]+)", text)


def normalize(path: str, root: Path) -> str:
    value = path.replace("\\", "/").strip()
    value = re.sub(r"^file://", "", value)
    root_posix = root.as_posix().rstrip("/")
    if value.lower().startswith(root_posix.lower() + "/"):
        value = value[len(root_posix) + 1 :]
    value = re.sub(r"^\./", "", value)
    return "/" + value.lstrip("/")


def _match(path: str, rules: list[tuple[str, str]]) -> str | None:
    lowered = path.lower()
    for fragment, reason in rules:
        if fragment.lower() in lowered:
            return reason
    return None


def decide(payload: dict, root: Path, maintainer: bool) -> tuple[str | None, str]:
    """Return (decision, reason). decision is 'deny', 'ask', or None for no opinion."""
    name, args = _tool(payload)
    lowered = name.lower()
    targets = [normalize(p, root) for p in _collect(args, PATH_KEYS) + _patch_paths(args)]
    is_edit = any(w in lowered for w in EDIT_WORDS) or "apply_patch" in lowered
    is_shell = any(w in lowered for w in SHELL_WORDS)

    if is_edit:
        for target in targets:
            reason = _match(target, NEVER_EDIT)
            if reason:
                return "deny", f"{target.lstrip('/')}: {reason}"
    if not maintainer:
        for target in targets:
            reason = _match(target, MAINTAINER_ONLY)
            if reason:
                return "deny", f"{target.lstrip('/')}: {reason}"
    if is_shell:
        for command in _collect(args, COMMAND_KEYS):
            for pattern, reason in SHELL_DENY:
                if pattern.search(command):
                    return "deny", reason
            if not maintainer:
                normalized = command.replace("\\", "/")
                for fragment, reason in MAINTAINER_ONLY:
                    if fragment in normalized:
                        return "deny", reason
                if re.search(
                    r"(^|[\s;&|])(>|>>|Set-Content|Out-File|tee)\s*[^\n]*data/generated/", normalized
                ):
                    return "deny", NEVER_EDIT[0][1]
            for pattern, reason in SHELL_ASK:
                if pattern.search(command):
                    return "ask", reason
    return None, ""


def _edited_tmdl(payload: dict, root: Path) -> bool:
    _, args = _tool(payload)
    targets = _collect(args, PATH_KEYS) + _patch_paths(args)
    return any(t.lower().endswith(".tmdl") for t in targets)


def main(event: str, root: Path) -> int:
    payload = _payload()
    maintainer = os.environ.get("CPDEMO_MAINTAINER") == "1"
    name, _ = _tool(payload)

    if event == "session-start":
        state = "unknown"
        sm = root / "fabric" / "ContosoPharmacy.SemanticModel" / "definition" / "tables"
        if sm.is_dir():
            state = "baseline names" if (sm / "fact_rx_fill.tmdl").exists() else "renamed model"
        message = (
            "Contoso Pharmacy lab. All data is synthetic; never add real patient, customer, or tenant data. "
            f"Model state: {state}."
        )
        _log(root, {"event": "sessionStart", "state": state})
        _emit("SessionStart", additionalContext=message)
        return 0

    if event == "pre-tool-use":
        decision, reason = decide(payload, root, maintainer)
        _log(root, {"event": "preToolUse", "tool": name, "decision": decision or "none", "reason": reason})
        if decision:
            _emit("PreToolUse", permissionDecision=decision, permissionDecisionReason=reason)
        return 0

    if event == "post-tool-use":
        if not _edited_tmdl(payload, root):
            return 0
        from . import tmdl

        findings = tmdl.errors(tmdl.lint(root / "fabric" / "ContosoPharmacy.SemanticModel"))
        summary = "pass" if not findings else f"{len(findings)} error(s)"
        _log(root, {"event": "postToolUse", "tool": name, "lint": summary})
        if findings:
            lines = [f"{f.file}:{f.line} {f.rule} {f.message}" for f in findings[:10]]
            _emit(
                "PostToolUse",
                additionalContext="TMDL lint found errors after your edit. Fix them before continuing:\n"
                + "\n".join(lines),
            )
        return 0

    if event == "session-end":
        _log(root, {"event": "sessionEnd", "reason": str(payload.get("reason", ""))})
        return 0
    return 0
