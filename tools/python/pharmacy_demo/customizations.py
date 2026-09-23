"""Static checks for the Copilot customization files: instructions, skills, agents, prompts, hooks, and MCP."""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from .labcheck.checks import frontmatter, load_jsonc

SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
BUILT_IN_AGENTS = {"agent", "ask", "edit", "plan"}
MAX_AGENT_BODY = 30_000
MAX_SKILL_DESCRIPTION = 1024
SCRIPT_REF = re.compile(r"(?<![\w/.-])\.?/?(scripts/[A-Za-z0-9_./-]+\.(?:ps1|sh))")
MD_LINK = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")


def _rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _body_script_refs(text: str, source: str, root: Path) -> list[str]:
    problems = []
    for ref in sorted(set(SCRIPT_REF.findall(text))):
        if not (root / ref).is_file():
            problems.append(f"{source}: references {ref}, which does not exist.")
    return problems


def _local_links(text: str, path: Path, root: Path) -> list[str]:
    problems = []
    for target in MD_LINK.findall(text):
        if re.match(r"^[a-z]+:", target) or target.startswith("/"):
            continue
        if not (path.parent / target).resolve().exists():
            problems.append(f"{_rel(path, root)}: link {target} does not resolve.")
    return problems


def check_instructions(root: Path) -> list[str]:
    problems = []
    main = root / ".github" / "copilot-instructions.md"
    if not main.is_file():
        problems.append(".github/copilot-instructions.md is missing.")
    else:
        problems += _body_script_refs(main.read_text(encoding="utf-8"), _rel(main, root), root)
    agents_md = root / "AGENTS.md"
    if agents_md.is_file():
        problems += _body_script_refs(agents_md.read_text(encoding="utf-8"), "AGENTS.md", root)
    for path in sorted((root / ".github" / "instructions").glob("*.instructions.md")):
        meta, body = frontmatter(path)
        if not meta or not isinstance(meta.get("applyTo"), str) or not meta["applyTo"].strip():
            problems.append(f"{_rel(path, root)}: frontmatter needs an applyTo glob.")
        problems += _body_script_refs(body, _rel(path, root), root)
    return problems


def check_skills(root: Path) -> list[str]:
    problems = []
    skills_dir = root / ".github" / "skills"
    for folder in sorted(p for p in skills_dir.iterdir() if p.is_dir()) if skills_dir.is_dir() else []:
        path = folder / "SKILL.md"
        rel = _rel(folder, root)
        if not path.is_file():
            problems.append(f"{rel}: SKILL.md is missing.")
            continue
        meta, body = frontmatter(path)
        if not meta:
            problems.append(f"{rel}/SKILL.md: frontmatter is missing or not valid YAML.")
            continue
        name, description = meta.get("name"), meta.get("description")
        if name != folder.name:
            problems.append(f"{rel}/SKILL.md: name '{name}' must match the folder name '{folder.name}'.")
        if not isinstance(name, str) or not SKILL_NAME.match(name) or len(name) > 64:
            problems.append(
                f"{rel}/SKILL.md: name must be lowercase words joined by hyphens, 64 characters max."
            )
        if not isinstance(description, str) or not description.strip():
            problems.append(f"{rel}/SKILL.md: description is required.")
        elif len(description) > MAX_SKILL_DESCRIPTION:
            problems.append(
                f"{rel}/SKILL.md: description is {len(description)} characters; the limit is 1024."
            )
        problems += _local_links(body, path, root)
        for doc in [path, *sorted(folder.rglob("*.md"))]:
            problems += _body_script_refs(doc.read_text(encoding="utf-8"), _rel(doc, root), root)
    return problems


def _agent_names(root: Path) -> dict[str, Path]:
    names = {}
    for path in sorted((root / ".github" / "agents").glob("*.agent.md")):
        meta, _ = frontmatter(path)
        stem = path.name.removesuffix(".agent.md")
        names[stem] = path
        if meta and isinstance(meta.get("name"), str):
            names[meta["name"]] = path
    return names


def check_agents(root: Path) -> list[str]:
    problems = []
    names = _agent_names(root)
    for path in sorted((root / ".github" / "agents").glob("*.agent.md")):
        rel = _rel(path, root)
        meta, body = frontmatter(path)
        if not meta:
            problems.append(f"{rel}: frontmatter is missing or not valid YAML.")
            continue
        if not isinstance(meta.get("description"), str) or not meta["description"].strip():
            problems.append(f"{rel}: description is required.")
        tools = meta.get("tools")
        if not isinstance(tools, list) or not tools or not all(isinstance(t, str) for t in tools):
            problems.append(f"{rel}: tools must be a non-empty list so the agent gets only what it needs.")
        if len(body) > MAX_AGENT_BODY:
            problems.append(f"{rel}: body is {len(body)} characters; keep it under {MAX_AGENT_BODY}.")
        for handoff in meta.get("handoffs") or []:
            if not isinstance(handoff, dict) or not handoff.get("label") or not handoff.get("agent"):
                problems.append(f"{rel}: each handoff needs a label and an agent.")
                continue
            if handoff["agent"] not in names and handoff["agent"] not in BUILT_IN_AGENTS:
                problems.append(
                    f"{rel}: handoff target '{handoff['agent']}' is not an agent in .github/agents."
                )
        problems += _body_script_refs(body, rel, root)
    return problems


def check_prompts(root: Path) -> list[str]:
    problems = []
    names = _agent_names(root)
    for path in sorted((root / ".github" / "prompts").glob("*.prompt.md")):
        rel = _rel(path, root)
        meta, body = frontmatter(path)
        if not meta:
            problems.append(f"{rel}: frontmatter is missing or not valid YAML.")
            continue
        if not isinstance(meta.get("description"), str) or not meta["description"].strip():
            problems.append(f"{rel}: description is required.")
        agent = meta.get("agent")
        if agent is not None and agent not in names and agent not in BUILT_IN_AGENTS:
            problems.append(f"{rel}: agent '{agent}' is not a built-in agent or one in .github/agents.")
        problems += _body_script_refs(body, rel, root)
    return problems


def check_hooks(root: Path) -> list[str]:
    problems = []
    for path in sorted((root / ".github" / "hooks").glob("*.json")):
        rel = _rel(path, root)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            problems.append(f"{rel}: not valid JSON ({exc.msg} at line {exc.lineno}).")
            continue
        if data.get("version") != 1 or not isinstance(data.get("hooks"), dict):
            problems.append(f"{rel}: needs version 1 and a hooks object.")
            continue
        for event, entries in data["hooks"].items():
            for entry in entries if isinstance(entries, list) else []:
                if entry.get("type") != "command":
                    problems.append(f"{rel}: {event} entry needs type 'command'.")
                for shell in ("bash", "powershell", "command"):
                    if isinstance(entry.get(shell), str):
                        problems += _body_script_refs(entry[shell], f"{rel} {event}.{shell}", root)
    return problems


def check_mcp(root: Path) -> list[str]:
    problems = []
    for path in (root / ".vscode" / "mcp.json", root / "config" / "cloud-agent-mcp.template.json"):
        if not path.is_file():
            continue
        try:
            data = load_jsonc(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError) as exc:
            problems.append(f"{_rel(path, root)}: not valid JSON with comments ({exc}).")
            continue
        servers = data.get("servers") or data.get("mcpServers")
        if not isinstance(servers, dict) or not servers:
            problems.append(
                f"{_rel(path, root)}: needs a servers (VS Code) or mcpServers (cloud agent) object."
            )
    return problems


def check_shipped(root: Path) -> list[str]:
    contract = yaml.safe_load((root / "lab" / "checks.yaml").read_text(encoding="utf-8"))
    shipped = contract.get("shipped") or {}
    locations = {
        "instructions": lambda n: root / ".github" / "instructions" / f"{n}.instructions.md",
        "skills": lambda n: root / ".github" / "skills" / n / "SKILL.md",
        "agents": lambda n: root / ".github" / "agents" / f"{n}.agent.md",
        "prompts": lambda n: root / ".github" / "prompts" / f"{n}.prompt.md",
    }
    problems = []
    for kind, names in shipped.items():
        for name in names:
            if kind in locations and not locations[kind](name).is_file():
                problems.append(
                    f"lab/checks.yaml lists shipped {kind[:-1]} '{name}', but the file is missing."
                )
    return problems


def check_all(root: Path) -> list[str]:
    return (
        check_instructions(root)
        + check_skills(root)
        + check_agents(root)
        + check_prompts(root)
        + check_hooks(root)
        + check_mcp(root)
        + check_shipped(root)
    )
