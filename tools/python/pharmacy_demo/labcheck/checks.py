"""Implementations for lab/checks.yaml. Each function returns (status, detail)."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

from .. import conventions, datagen, evaluation, oracle, paths, pbir, repo_checks, tmdl
from . import FAIL, PASS, SKIP

UPSTREAM = "sabajamalian/fabric-powerbi-ai-devops-demo"
REGISTRY: dict = {}


def check(check_id: str):
    def register(func):
        REGISTRY[check_id] = func
        return func

    return register


# ---------- helpers ----------


def _run(args: list[str], cwd: Path | None = None) -> tuple[int, str]:
    try:
        result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, str(exc)
    return result.returncode, (result.stdout + result.stderr).strip()


def _version(text: str) -> tuple[int, ...]:
    match = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", text)
    return tuple(int(g) for g in match.groups() if g is not None) if match else ()


def _tool(name: str, args: list[str], minimum: tuple[int, ...], label: str) -> tuple[str, str]:
    exe = shutil.which(name)
    if not exe:
        return FAIL, f"{label} not found on PATH."
    code, out = _run([exe, *args])
    found = _version(out)
    if code != 0 or not found:
        return FAIL, f"{label} found at {exe} but its version couldn't be read."
    if found < minimum:
        return (
            FAIL,
            f"{label} {'.'.join(map(str, found))} found; need {'.'.join(map(str, minimum))} or later.",
        )
    return PASS, f"{label} {'.'.join(map(str, found))}"


def _git(root: Path, *args: str) -> tuple[int, str]:
    return _run(["git", "-C", str(root), *args])


def frontmatter(path: Path) -> tuple[dict | None, str]:
    text = path.read_text(encoding="utf-8-sig")
    if not text.startswith("---"):
        return None, text
    parts = re.split(r"^---\s*$", text, maxsplit=2, flags=re.MULTILINE)
    if len(parts) < 3:
        return None, text
    try:
        data = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return None, text
    return (data if isinstance(data, dict) else None), parts[2]


def glob_to_regex(pattern: str) -> re.Pattern:
    i, out = 0, []
    while i < len(pattern):
        ch = pattern[i]
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif ch == "*":
            out.append("[^/]*")
            i += 1
        elif ch == "?":
            out.append("[^/]")
            i += 1
        elif ch == "{":
            end = pattern.find("}", i)
            options = pattern[i + 1 : end].split(",")
            out.append("(?:" + "|".join(re.escape(o) for o in options) + ")")
            i = end + 1
        else:
            out.append(re.escape(ch))
            i += 1
    return re.compile("^" + "".join(out) + "$", re.IGNORECASE)


def matching_files(root: Path, apply_to: str) -> list[str]:
    patterns = [glob_to_regex(p.strip()) for p in str(apply_to).split(",") if p.strip()]
    return [f for f in repo_checks.list_files(root) if any(p.match(f) for p in patterns)]


def load_jsonc(text: str):
    out, i, in_string = [], 0, False
    while i < len(text):
        ch = text[i]
        if in_string:
            out.append(ch)
            if ch == "\\":
                out.append(text[i + 1])
                i += 2
                continue
            if ch == '"':
                in_string = False
            i += 1
        elif ch == '"':
            in_string = True
            out.append(ch)
            i += 1
        elif text.startswith("//", i):
            while i < len(text) and text[i] != "\n":
                i += 1
        elif text.startswith("/*", i):
            i = text.find("*/", i) + 2
        else:
            out.append(ch)
            i += 1
    cleaned = re.sub(r",(\s*[}\]])", r"\1", "".join(out))
    return json.loads(cleaned)


def _conventions(root: Path, rules: set[str]) -> tuple[str, str]:
    sm = paths.semantic_model_dir(root)
    issues = [i for i in conventions.assess(sm, root) if i.rule in rules]
    if not issues:
        return PASS, "No findings."
    sample = "; ".join(f"{i.obj}: {i.finding}" for i in issues[:4])
    more = f" (+{len(issues) - 4} more)" if len(issues) > 4 else ""
    return FAIL, f"{len(issues)} finding(s): {sample}{more}"


def _desktop_port_files() -> list[Path]:
    roots = []
    local = os.environ.get("LOCALAPPDATA")
    profile = os.environ.get("USERPROFILE")
    if local:
        roots.append(Path(local) / "Microsoft" / "Power BI Desktop" / "AnalysisServicesWorkspaces")
    if profile:
        roots.append(
            Path(profile) / "Microsoft" / "Power BI Desktop Store App" / "AnalysisServicesWorkspaces"
        )
    return [p for r in roots if r.is_dir() for p in r.glob("*/Data/msmdsrv.port.txt")]


def _desktop_running() -> tuple[str, str]:
    ports = _desktop_port_files()
    if not ports:
        return FAIL, "No running Power BI Desktop model found (no msmdsrv.port.txt)."
    return PASS, f"{len(ports)} Desktop model instance(s) running."


def _run_file(root: Path, label: str) -> tuple[dict | None, str]:
    path = root / "evaluation" / "runs" / f"{label}.json"
    if not path.exists():
        return None, f"{path.relative_to(root).as_posix()} not found."
    run = evaluation.load_run(path)
    problems = evaluation.validate_run(run, root / "evaluation")
    if problems:
        return None, "Schema problems: " + "; ".join(problems[:3])
    if "grade" not in run:
        return None, "Run isn't graded yet."
    return run, ""


def _gh_prs(root: Path) -> tuple[list | None, str]:
    gh = shutil.which("gh")
    if not gh:
        return None, "gh isn't installed."
    code, _ = _run([gh, "auth", "status"])
    if code != 0:
        return None, "gh isn't signed in (gh auth login)."
    code, out = _run(
        [
            gh,
            "pr",
            "list",
            "--state",
            "all",
            "--limit",
            "50",
            "--json",
            "number,headRefName,author,state,reviews,statusCheckRollup",
        ],
        cwd=root,
    )
    if code != 0:
        return None, f"gh pr list failed: {out[:200]}"
    return json.loads(out or "[]"), ""


def _hook_events(root: Path) -> list[dict]:
    log = root / "out" / "hooks" / "session.log"
    if not log.exists():
        return []
    events = []
    for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def _new_assets(root: Path, kind: str, contract: dict) -> list[Path]:
    shipped = set(contract["shipped"][kind])
    if kind == "skills":
        return [
            p
            for p in sorted((root / ".github" / "skills").glob("*/SKILL.md"))
            if p.parent.name not in shipped
        ]
    suffix = {"agents": ".agent.md", "prompts": ".prompt.md", "instructions": ".instructions.md"}[kind]
    folder = root / ".github" / kind
    return [p for p in sorted(folder.glob(f"*{suffix}")) if p.name[: -len(suffix)] not in shipped]


# ---------- Lab 00 ----------


@check("L00-pwsh")
def _(root, contract):
    return _tool(
        "pwsh",
        ["-NoLogo", "-NoProfile", "-Command", "$PSVersionTable.PSVersion.ToString()"],
        (7, 4),
        "PowerShell",
    )


@check("L00-git")
def _(root, contract):
    status, detail = _tool("git", ["--version"], (2, 40), "Git")
    if status == PASS and os.name == "nt":
        _, value = _run(["git", "config", "--global", "core.longpaths"])
        if value.strip().lower() != "true":
            return FAIL, detail + ", but core.longpaths isn't true."
    return status, detail


@check("L00-python")
def _(root, contract):
    found = sys.version_info[:2]
    if found < (3, 12):
        return FAIL, f"Python {found[0]}.{found[1]} is running this check; need 3.12 or later."
    return PASS, f"Python {sys.version.split()[0]}"


@check("L00-node")
def _(root, contract):
    return _tool("node", ["--version"], (20,), "Node.js")


@check("L00-vscode")
def _(root, contract):
    exe = shutil.which("code") or shutil.which("code-insiders")
    return (PASS, f"VS Code at {exe}") if exe else (FAIL, "'code' isn't on PATH.")


@check("L00-desktop")
def _(root, contract):
    candidates = []
    for var in ("ProgramFiles", "ProgramW6432"):
        base = os.environ.get(var)
        if base:
            candidates.append(Path(base) / "Microsoft Power BI Desktop" / "bin" / "PBIDesktop.exe")
    local = os.environ.get("LOCALAPPDATA")
    if local:
        candidates.append(Path(local) / "Microsoft" / "WindowsApps" / "PBIDesktopStore.exe")
    found = [c for c in candidates if c.exists()]
    return (
        (PASS, f"Found {found[0]}")
        if found
        else (FAIL, "Power BI Desktop wasn't found in the usual locations.")
    )


@check("L00-gh")
def _(root, contract):
    return _tool("gh", ["--version"], (2, 40), "GitHub CLI")


@check("L00-copilot-cli")
def _(root, contract):
    exe = shutil.which("copilot")
    return (PASS, f"Copilot CLI at {exe}") if exe else (FAIL, "'copilot' isn't on PATH.")


# ---------- Lab 01 ----------


@check("L01-not-upstream")
def _(root, contract):
    if os.environ.get("CPDEMO_UPSTREAM_CI") == "1":
        return SKIP, "Upstream CI run."
    code, url = _git(root, "remote", "get-url", "origin")
    if code != 0:
        return FAIL, "No 'origin' remote. Clone your own copy of the template."
    if UPSTREAM.lower() in url.lower():
        return FAIL, "origin is the upstream lab repo. Work in a copy created with Use this template."
    return PASS, f"origin is {url}"


@check("L01-upstream-remote")
def _(root, contract):
    if os.environ.get("CPDEMO_UPSTREAM_CI") == "1":
        return SKIP, "Upstream CI run."
    code, url = _git(root, "remote", "get-url", "upstream")
    if code != 0:
        return FAIL, "No 'upstream' remote."
    if UPSTREAM.lower() not in url.lower():
        return FAIL, f"upstream points at {url}."
    return PASS, url


@check("L01-venv")
def _(root, contract):
    venv = root / ".venv"
    if not venv.is_dir():
        return FAIL, ".venv not found at the repo root."
    python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.exists():
        return FAIL, f"{python.relative_to(root).as_posix()} not found."
    code, out = _run(
        [str(python), "-c", "import pharmacy_demo, duckdb, yaml, jsonschema; print('ok')"], cwd=root
    )
    return (PASS, ".venv has pharmacy_demo and its dependencies.") if code == 0 else (FAIL, out[-200:])


@check("L01-data")
def _(root, contract):
    problems = datagen.check(paths.data_dir(root))
    return (PASS, "Data matches seed.") if not problems else (FAIL, "; ".join(problems[:3]))


@check("L01-validation")
def _(root, contract):
    failures = []
    lint_errors = tmdl.errors(tmdl.lint(paths.semantic_model_dir(root)))
    if lint_errors:
        failures.append(f"{len(lint_errors)} TMDL error(s)")
    bindings = pbir.check(paths.report_dir(root), paths.semantic_model_dir(root))
    if bindings:
        failures.append(f"{len(bindings)} report binding problem(s)")
    hygiene = repo_checks.run_all(root)
    if hygiene:
        failures.append(f"{len(hygiene)} hygiene problem(s)")
    stale = oracle.check_expected(root)
    if stale:
        failures.append("expected answers are stale")
    return (
        (FAIL, ", ".join(failures))
        if failures
        else (PASS, "TMDL, bindings, hygiene, and expected answers OK.")
    )


# ---------- Lab 02 ----------


@check("L02-data-link")
def _(root, contract):
    link = Path(r"C:\ContosoPharmacyDemo\data")
    if not link.exists():
        return FAIL, f"{link} doesn't exist."
    target = paths.generated_dir(root).resolve()
    if link.resolve() != target:
        return FAIL, f"{link} points at {link.resolve()}, not {target}."
    return PASS, f"{link} -> {target}"


@check("L02-desktop")
def _(root, contract):
    return _desktop_running()


@check("L02-clean-tree")
def _(root, contract):
    code, out = _git(root, "status", "--porcelain", "--", "fabric")
    if code != 0:
        return FAIL, out[:200]
    if out.strip():
        changed = [line[3:] for line in out.splitlines()]
        return FAIL, f"{len(changed)} changed path(s) under fabric/: {', '.join(changed[:3])}"
    return PASS, "No changes under fabric/."


# ---------- Lab 03 ----------


@check("L03-instructions")
def _(root, contract):
    new = _new_assets(root, "instructions", contract)
    if not new:
        return FAIL, "No new .github/instructions/*.instructions.md file found."
    notes = []
    for path in new:
        meta, body = frontmatter(path)
        if not meta or not meta.get("applyTo"):
            notes.append(f"{path.name}: frontmatter needs applyTo.")
            continue
        if not body.strip():
            notes.append(f"{path.name}: body is empty.")
            continue
        matched = matching_files(root, meta["applyTo"])
        if not matched:
            notes.append(f"{path.name}: applyTo '{meta['applyTo']}' matches no files.")
            continue
        return PASS, f"{path.name} applies to {len(matched)} file(s), for example {matched[0]}."
    return FAIL, " ".join(notes)


# ---------- Lab 04 ----------


@check("L04-mcp-config")
def _(root, contract):
    path = root / ".vscode" / "mcp.json"
    if not path.exists():
        return FAIL, ".vscode/mcp.json not found."
    try:
        config = load_jsonc(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError) as exc:
        return FAIL, f"mcp.json doesn't parse: {exc}"
    servers = config.get("servers", {})
    pbi = [
        name
        for name, s in servers.items()
        if "powerbi-modeling-mcp" in json.dumps(s) or "powerbi" in name.lower()
    ]
    if not pbi:
        return FAIL, "No Power BI Modeling MCP server in mcp.json."
    text = path.read_text(encoding="utf-8")
    for label, pattern in repo_checks.SECRETS:
        if pattern.search(text):
            return FAIL, f"mcp.json contains something that looks like a {label}."
    if repo_checks.GUID.search(text):
        return FAIL, "mcp.json contains a GUID. Use an ${input:...} prompt or an environment variable."
    for match in re.finditer(r'"(?i:[^"]*(?:token|secret|password|apikey|api_key))"\s*:\s*"([^"]*)"', text):
        if match.group(1) and not match.group(1).startswith("${"):
            return FAIL, "mcp.json has a literal credential value. Use ${input:...} or ${env:...}."
    return PASS, f"Server(s): {', '.join(pbi)}"


@check("L04-desktop")
def _(root, contract):
    return _desktop_running()


# ---------- Lab 05 ----------


@check("L05-baseline-run")
def _(root, contract):
    run, problem = _run_file(root, "local-baseline")
    if run is None:
        return FAIL, problem
    return PASS, f"Graded {run['grade']['total']} / {run['grade']['max']}."


# ---------- Lab 06 ----------


@check("L06-assessment")
def _(root, contract):
    path = root / "out" / "assessment.md"
    if not path.exists():
        return FAIL, "out/assessment.md not found."
    rows = [
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.startswith("|") and not re.match(r"^\|\s*-", line)
    ]
    if not rows:
        return FAIL, "No findings table found."
    header = [c.strip().lower() for c in rows[0].strip("|").split("|")]
    needed = {"rule", "severity", "object", "finding", "fix"}
    missing = needed - set(header)
    if missing:
        return FAIL, f"Findings table is missing column(s): {', '.join(sorted(missing))}."
    count = len(rows) - 1
    if count < 8:
        return FAIL, f"{count} finding(s); expected at least 8."
    return PASS, f"{count} findings."


@check("L06-fabric-skill")
def _(root, contract):
    candidates = [
        root / ".agents" / "skills" / "semantic-model-authoring" / "SKILL.md",
        root / ".github" / "skills" / "semantic-model-authoring" / "SKILL.md",
        Path.home() / ".agents" / "skills" / "semantic-model-authoring" / "SKILL.md",
        Path.home() / ".copilot" / "skills" / "semantic-model-authoring" / "SKILL.md",
    ]
    candidates += (
        list((root / "apm_modules").rglob("semantic-model-authoring/SKILL.md"))
        if (root / "apm_modules").is_dir()
        else []
    )
    candidates += (
        list((Path.home() / ".copilot" / "installed-plugins").rglob("semantic-model-authoring/SKILL.md"))
        if (Path.home() / ".copilot" / "installed-plugins").is_dir()
        else []
    )
    found = [c for c in candidates if c.exists()]
    return (PASS, f"Found {found[0]}") if found else (FAIL, "semantic-model-authoring skill not found.")


# ---------- Lab 07 ----------


@check("L07-names")
def _(root, contract):
    return _conventions(root, {"C01"})


@check("L07-descriptions")
def _(root, contract):
    status, detail = _conventions(root, {"C02", "C03"})
    if status == FAIL:
        # Measure descriptions belong to Lab 08; only tables and columns count here.
        sm = paths.semantic_model_dir(root)
        issues = [
            i
            for i in conventions.assess(sm, root)
            if i.rule in {"C02", "C03"} and not i.obj.startswith("measure ")
        ]
        if not issues:
            return PASS, "Tables and visible columns have descriptions."
        return FAIL, f"{len(issues)} finding(s): " + "; ".join(i.obj for i in issues[:5])
    return status, detail


@check("L07-hidden-and-summarize")
def _(root, contract):
    return _conventions(root, {"C04", "C05"})


def _lint(root: Path) -> tuple[str, str]:
    findings = tmdl.errors(tmdl.lint(paths.semantic_model_dir(root)))
    if findings:
        return FAIL, "; ".join(f"{f.file}:{f.line} {f.message}" for f in findings[:3])
    return PASS, "No TMDL errors."


@check("L07-lint")
def _(root, contract):
    return _lint(root)


@check("L07-bindings")
def _(root, contract):
    problems = pbir.check(paths.report_dir(root), paths.semantic_model_dir(root))
    if problems:
        return FAIL, f"{len(problems)} problem(s): " + "; ".join(p.message for p in problems[:3])
    return PASS, "All report fields exist."


# ---------- Lab 08 ----------


@check("L08-relationships")
def _(root, contract):
    return _conventions(root, {"C07", "C08"})


@check("L08-date-table")
def _(root, contract):
    return _conventions(root, {"C09", "C10", "C11"})


@check("L08-measures")
def _(root, contract):
    sm = paths.semantic_model_dir(root)
    issues = [
        i
        for i in conventions.assess(sm, root)
        if i.rule in {"C12", "C13"} or (i.rule in {"C02", "C03"} and i.obj.startswith("measure "))
    ]
    if not issues:
        return PASS, "All required measures are complete."
    return FAIL, f"{len(issues)} finding(s): " + "; ".join(f"{i.obj}: {i.finding}" for i in issues[:4])


@check("L08-fill-type")
def _(root, contract):
    status, detail = _conventions(root, {"C06"})
    if status == FAIL:
        return status, detail
    fill = tmdl.load_model(paths.semantic_model_dir(root)).columns("Prescription Fill")
    column = fill.get("Fill Type")
    if column is None:
        return FAIL, "No 'Fill Type' column on Prescription Fill."
    code = fill.get("Fill Type Code")
    if code is not None and code.props.get("isHidden") is not True:
        return FAIL, "'Fill Type Code' is still visible."
    return PASS, "Fill Type is decoded and the code is hidden."


@check("L08-lint")
def _(root, contract):
    status, detail = _lint(root)
    if status == FAIL:
        return status, detail
    problems = pbir.check(paths.report_dir(root), paths.semantic_model_dir(root))
    if problems:
        return FAIL, f"{len(problems)} binding problem(s): " + "; ".join(p.message for p in problems[:3])
    return PASS, "TMDL lint and report bindings pass."


@check("L08-dax-tests")
def _(root, contract):
    result = root / "out" / "dax-tests.json"
    if not result.exists():
        return FAIL, "No out/dax-tests.json. Run scripts/Invoke-DaxQuestionTests.ps1 first."
    data = json.loads(result.read_text(encoding="utf-8"))
    failed = [r["question_id"] for r in data.get("results", []) if r.get("status") != "PASS"]
    return (FAIL, f"Failed: {', '.join(failed)}") if failed else (PASS, "All reference DAX queries match.")


# ---------- Lab 09 ----------


def _ai_prep(root: Path) -> dict:
    _, required = conventions.load_rules(root)
    return required["ai_prep"]


@check("L09-ai-prep-files")
def _(root, contract):
    spec = _ai_prep(root)
    folder = root / spec["folder"]
    missing = [f for f in spec["files"] if not (folder / f).exists()]
    if missing:
        return FAIL, f"Missing in {spec['folder']}: {', '.join(missing)}"
    for name in spec["files"]:
        if name.endswith(".yaml"):
            try:
                yaml.safe_load((folder / name).read_text(encoding="utf-8"))
            except yaml.YAMLError as exc:
                return FAIL, f"{name} isn't valid YAML: {exc}"
    return PASS, "All draft files present."


@check("L09-ai-instructions")
def _(root, contract):
    spec = _ai_prep(root)
    path = root / spec["folder"] / "ai-instructions.md"
    if not path.exists():
        return FAIL, "ai-instructions.md not found."
    text = path.read_text(encoding="utf-8")
    if len(text) > spec["instructions_max_chars"]:
        return FAIL, f"{len(text)} characters; the limit is {spec['instructions_max_chars']}."
    missing = [term for term in spec["instructions_must_mention"] if term.lower() not in text.lower()]
    if missing:
        return FAIL, "Doesn't mention: " + ", ".join(missing)
    return PASS, f"{len(text)} characters; all required definitions present."


@check("L09-synonyms")
def _(root, contract):
    spec = _ai_prep(root)
    path = root / spec["folder"] / "synonyms.yaml"
    if not path.exists():
        return FAIL, "synonyms.yaml not found."
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    keys = set()
    for section in ("tables", "columns", "measures"):
        for key, values in (data.get(section) or {}).items():
            if values:
                keys.add(key)
    missing = [k for k in spec["synonyms_required_for"] if k not in keys]
    return (
        (FAIL, "No synonyms for: " + ", ".join(missing))
        if missing
        else (PASS, f"{len(keys)} objects have synonyms.")
    )


@check("L09-verified-answers")
def _(root, contract):
    spec = _ai_prep(root)
    path = root / spec["folder"] / "verified-answers.yaml"
    if not path.exists():
        return FAIL, "verified-answers.yaml not found."
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    candidates = [c for c in data.get("candidates", []) if c.get("phrases")]
    ids = {c.get("question_id") for c in candidates}
    if len(candidates) < spec["min_verified_answers"]:
        return FAIL, f"{len(candidates)} candidate(s) with phrases; need {spec['min_verified_answers']}."
    return PASS, f"{len(candidates)} candidates covering {', '.join(sorted(i for i in ids if i))}."


@check("L09-model-flags")
def _(root, contract):
    sm = paths.semantic_model_dir(root)
    if not conventions.qna_enabled(sm):
        return FAIL, "settings.qnaEnabled isn't true in definition.pbism."
    return _conventions(root, {"C14"})


# ---------- Lab 10 ----------


@check("L10-after-run")
def _(root, contract):
    run, problem = _run_file(root, "local-ai-ready")
    return (
        (FAIL, problem) if run is None else (PASS, f"Graded {run['grade']['total']} / {run['grade']['max']}.")
    )


@check("L10-improved")
def _(root, contract):
    before, problem = _run_file(root, "local-baseline")
    if before is None:
        return FAIL, "local-baseline: " + problem
    after, problem = _run_file(root, "local-ai-ready")
    if after is None:
        return FAIL, "local-ai-ready: " + problem
    b, a = before["grade"]["total"], after["grade"]["total"]
    return (
        (PASS, f"{b} -> {a}") if a > b else (FAIL, f"local-ai-ready scored {a}, local-baseline scored {b}.")
    )


@check("L10-comparison")
def _(root, contract):
    path = root / "out" / "question-comparison.md"
    return (PASS, "Found.") if path.exists() else (FAIL, "out/question-comparison.md not found.")


# ---------- Lab 11 ----------


@check("L11-hook-deny")
def _(root, contract):
    events = [e for e in _hook_events(root) if e.get("event") == "preToolUse" and e.get("decision") == "deny"]
    if not events:
        return FAIL, "No denied preToolUse events in out/hooks/session.log."
    return PASS, f"{len(events)} denial(s); latest: {events[-1].get('reason', '')[:80]}"


@check("L11-hook-lint")
def _(root, contract):
    events = [e for e in _hook_events(root) if e.get("event") == "postToolUse" and "lint" in e]
    if not events:
        return FAIL, "No postToolUse lint results in out/hooks/session.log."
    return PASS, f"{len(events)} lint result(s); latest: {events[-1]['lint']}"


# ---------- Lab 12 and 13 ----------


def _checks_green(pr: dict) -> bool:
    rollup = pr.get("statusCheckRollup") or []
    if not rollup:
        return False
    return all(
        (c.get("conclusion") or c.get("state") or "").upper() in {"SUCCESS", "NEUTRAL", "SKIPPED"}
        for c in rollup
    )


def _is_copilot(login: str) -> bool:
    return "copilot" in (login or "").lower()


@check("L12-pull-request")
def _(root, contract):
    prs, problem = _gh_prs(root)
    if prs is None:
        return SKIP, problem
    for pr in prs:
        if pr.get("headRefName") in {"main", "master"} or _is_copilot(pr.get("author", {}).get("login", "")):
            continue
        reviewed = any(_is_copilot(r.get("author", {}).get("login", "")) for r in pr.get("reviews") or [])
        if reviewed and _checks_green(pr):
            return PASS, f"PR #{pr['number']} ({pr['headRefName']})"
    return FAIL, "No PR with green checks and a Copilot review found."


@check("L13-cloud-agent-pr")
def _(root, contract):
    prs, problem = _gh_prs(root)
    if prs is None:
        return SKIP, problem
    mine = [pr for pr in prs if _is_copilot(pr.get("author", {}).get("login", ""))]
    return (
        (PASS, f"PR #{mine[0]['number']} by Copilot") if mine else (FAIL, "No PR authored by Copilot found.")
    )


# ---------- Lab 14 ----------


@check("L14-skill")
def _(root, contract):
    new = _new_assets(root, "skills", contract)
    if not new:
        return FAIL, "No new skill folder under .github/skills."
    notes = []
    for path in new:
        meta, _ = frontmatter(path)
        if not meta:
            notes.append(f"{path.parent.name}: SKILL.md has no frontmatter.")
        elif meta.get("name") != path.parent.name:
            notes.append(f"{path.parent.name}: name '{meta.get('name')}' doesn't match the folder.")
        elif not meta.get("description"):
            notes.append(f"{path.parent.name}: description is empty.")
        else:
            return PASS, f"Skill {path.parent.name}"
    return FAIL, " ".join(notes)


@check("L14-agent")
def _(root, contract):
    new = _new_assets(root, "agents", contract)
    if not new:
        return FAIL, "No new .github/agents/*.agent.md file."
    for path in new:
        meta, _ = frontmatter(path)
        if meta and meta.get("description") and meta.get("tools"):
            return PASS, f"Agent {path.name}"
    return FAIL, "New agent files need description and tools in the frontmatter."


@check("L14-prompt")
def _(root, contract):
    new = _new_assets(root, "prompts", contract)
    if not new:
        return FAIL, "No new .github/prompts/*.prompt.md file."
    for path in new:
        meta, _ = frontmatter(path)
        if meta and meta.get("description"):
            return PASS, f"Prompt {path.name}"
    return FAIL, "New prompt files need a description in the frontmatter."


# ---------- Lab 15 ----------


@check("L15-data-link-removed")
def _(root, contract):
    link = Path(r"C:\ContosoPharmacyDemo\data")
    return (FAIL, f"{link} still exists.") if link.exists() else (PASS, "Junction removed.")


@check("L15-local-outputs")
def _(root, contract):
    leftovers = [p for p in ("out", ".tools", "apm_modules") if (root / p).exists()]
    leftovers += [p.relative_to(root).as_posix() for p in (root / "evaluation" / "runs").glob("local-*.json")]
    return (FAIL, "Still present: " + ", ".join(leftovers)) if leftovers else (PASS, "Nothing left to clean.")
